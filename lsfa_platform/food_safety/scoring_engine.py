from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from .models import (
    AnswerChoice,
    AuditLogEntry,
    AuditQuestion,
    CorrectiveActionCAPA,
    InspectionAnswer,
    InspectionVisit,
    QuestionSeverity,
    ReinspectionSchedule,
    RiskLevel,
    ViolationRecord,
    ViolationStatus,
)

HUNDRED = Decimal("100.00")
ZERO = Decimal("0.00")
HALF = Decimal("0.50")


class InspectionRuleError(Exception):
    """استثناء يُرفع عند مخالفة ضوابط التقييم (مثل غياب تبرير غير المنطبق)"""


def _round2(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def evaluate_answer_choice(question: AuditQuestion, choice: str, justification: str = ""):
    """
    يحسب (earned_points, max_applicable_points, is_na_excluded, is_critical_issue)
    وفق ضوابط LSFA:
    - COMPLIANT: يأخذ كامل الوزن، ويُضاف للوزن المحتسب.
    - PARTIALLY_COMPLIANT: يأخذ 50% من الوزن، ويُضاف للوزن المحتسب.
    - NON_COMPLIANT: يأخذ 0، ويُضاف للوزن المحتسب.
    - NOT_APPLICABLE: يُستبعد من الحساب إذا سمح القالب والسؤال وتوفر التبرير عند اللزوم.
    - NOT_VERIFIED: لا يُعتبر مطابقاً أبداً (0 نقاط) ويُبقى في المقام حتى لا يُحسب مطابقاً.
    """
    template = question.axis.template
    weight = Decimal(question.weight)
    clean_just = (justification or "").strip()

    if choice == AnswerChoice.NOT_APPLICABLE:
        if not template.allow_not_applicable or not question.can_be_not_applicable:
            raise InspectionRuleError(
                f"البند {question.code} لا يسمح بتصنيفه كـ (غير منطبق) وفق ضوابط الاستمارة."
            )
        if template.require_na_justification and not clean_just:
            raise InspectionRuleError(
                f"يجب إدخال تبرير واضح للبند {question.code} عند اختيار (غير منطبق)."
            )
        return ZERO, ZERO, True, False

    if choice == AnswerChoice.COMPLIANT:
        return _round2(weight), _round2(weight), False, False

    if choice == AnswerChoice.PARTIALLY_COMPLIANT:
        is_crit = question.severity == QuestionSeverity.CRITICAL
        return _round2(weight * HALF), _round2(weight), False, is_crit

    if choice == AnswerChoice.NON_COMPLIANT:
        is_crit = question.severity == QuestionSeverity.CRITICAL
        return ZERO, _round2(weight), False, is_crit

    # NOT_VERIFIED أو أي حالة غير مؤكدة: لا يُحتسب مطابقاً أبداً
    is_crit = question.severity == QuestionSeverity.CRITICAL
    return ZERO, _round2(weight), False, is_crit


def compute_independent_risk_level(
    compliance_score_pct: Decimal,
    critical_violations_count: int,
    major_violations_count: int,
    excluded_na_pct: Decimal,
    max_na_ratio_pct: Decimal,
) -> str:
    """
    نظام مستقل لتقييم المخاطر:
    - CRITICAL: أي مخالفة حرجة أو درجة التزام أقل من 50%.
    - HIGH: درجة التزام أقل من 70% أو وجود مخالفات جسيمة متعددة أو تجاوز ضوابط غير المنطبق بشكل كبير.
    - MEDIUM: درجة التزام أقل من 85% أو وجود مخالفة جسيمة واحدة.
    - LOW: التزام مرتفع بدون مخالفات حرجة.
    """
    if critical_violations_count > 0 or compliance_score_pct < Decimal("50.00"):
        return RiskLevel.CRITICAL
    if compliance_score_pct < Decimal("70.00") or major_violations_count >= 2:
        return RiskLevel.HIGH
    if excluded_na_pct > max_na_ratio_pct and compliance_score_pct < Decimal("80.00"):
        return RiskLevel.HIGH
    if compliance_score_pct < Decimal("85.00") or major_violations_count == 1:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


@transaction.atomic
def process_inspection_visit(
    visit: InspectionVisit,
    answers_payload: list[dict],
    auto_create_violations: bool = True,
    auto_create_capa_and_reinspection: bool = True,
    default_due_days: int = 14,
    actor=None,
) -> InspectionVisit:
    """
    يعالج كامل إجابات زيارة التفتيش:
    1. يتحقق من ضوابط الإجابات (خصوصاً غير المنطبق وغير المتحقق منه).
    2. يحسب درجة الالتزام من 100 ونسبة غير المنطبق.
    3. يفصل المخالفات الحرجة عن النتيجة الإجمالية.
    4. يحدد مستوى المخاطر المستقل ويحدّث المؤسسة.
    5. ينشئ سجلات المخالفات والـ CAPA وجدولة إعادة التفتيش وسجل التدقيق.
    """
    questions_by_id = {
        q.id: q
        for q in AuditQuestion.objects.select_related("axis__template").filter(
            axis__template=visit.template, is_active=True
        )
    }

    total_questions = len(questions_by_id)
    na_count = 0
    total_earned = ZERO
    total_applicable_weight = ZERO
    critical_count = 0
    major_count = 0

    # مسح الإجابات السابقة لإعادة الحساب النظيف عند التحديث
    visit.answers.all().delete()

    for item in answers_payload:
        qid = int(item["question_id"])
        question = questions_by_id.get(qid)
        if not question:
            continue

        choice = item.get("choice", AnswerChoice.NOT_VERIFIED)
        justification = item.get("justification", "")
        measured_value = item.get("measured_value", "")

        earned, max_pts, is_na, is_crit_issue = evaluate_answer_choice(
            question=question,
            choice=choice,
            justification=justification,
        )

        InspectionAnswer.objects.create(
            visit=visit,
            question=question,
            choice=choice,
            justification=justification,
            measured_value=measured_value,
            earned_points=earned,
            max_applicable_points=max_pts,
        )

        if is_na:
            na_count += 1
        else:
            total_earned += earned
            total_applicable_weight += max_pts

        if choice in (AnswerChoice.NON_COMPLIANT, AnswerChoice.PARTIALLY_COMPLIANT):
            if question.severity == QuestionSeverity.CRITICAL:
                critical_count += 1
            elif question.severity == QuestionSeverity.MAJOR:
                major_count += 1
        elif choice == AnswerChoice.NOT_VERIFIED and question.severity == QuestionSeverity.CRITICAL:
            # غير المتحقق منه على بند حرج يُبرز كتنبيه حرج مستقل
            critical_count += 1

    if total_applicable_weight > ZERO:
        compliance_pct = _round2((total_earned / total_applicable_weight) * HUNDRED)
    else:
        compliance_pct = ZERO

    if total_questions > 0:
        na_pct = _round2((Decimal(na_count) / Decimal(total_questions)) * HUNDRED)
    else:
        na_pct = ZERO

    risk_level = compute_independent_risk_level(
        compliance_score_pct=compliance_pct,
        critical_violations_count=critical_count,
        major_violations_count=major_count,
        excluded_na_pct=na_pct,
        max_na_ratio_pct=visit.template.max_na_ratio_pct,
    )

    visit.compliance_score_pct = compliance_pct
    visit.excluded_na_pct = na_pct
    visit.critical_violations_count = critical_count
    visit.has_critical_failure = critical_count > 0
    visit.risk_level = risk_level
    visit.save()

    # تحديث مستوى خطورة المؤسسة بناءً على التقييم المستقل
    establishment = visit.establishment
    establishment.risk_level = risk_level
    establishment.save(update_fields=["risk_level", "updated_at"])

    if auto_create_violations:
        due_date = (timezone.now() + timedelta(days=default_due_days)).date()
        created_violations = []

        for ans in visit.answers.select_related("question").filter(
            choice__in=[AnswerChoice.NON_COMPLIANT, AnswerChoice.PARTIALLY_COMPLIANT]
        ):
            q = ans.question
            v_code = f"VIO-{visit.reference_code}-{q.code}"
            violation, created = ViolationRecord.objects.get_or_create(
                code=v_code,
                defaults={
                    "visit": visit,
                    "question": q,
                    "severity": q.severity,
                    "description_ar": (
                        f"عدم التزام بالبند ({q.code}) - {q.text_ar}. "
                        f"الحالة: {ans.get_choice_display()}. "
                        f"{ans.justification or ''}"
                    ).strip(),
                    "description_en": (
                        f"Non-compliance with item ({q.code}) - {q.text_en}. "
                        f"Status: {ans.get_choice_display()}."
                    ).strip(),
                    "status": ViolationStatus.OPEN,
                    "due_date": due_date,
                },
            )
            if created:
                created_violations.append(violation)

            if auto_create_capa_and_reinspection:
                CorrectiveActionCAPA.objects.get_or_create(
                    violation=violation,
                    defaults={
                        "root_cause_analysis": "بانتظار تحليل السبب الجذري من إدارة المؤسسة.",
                        "corrective_action_plan": f"معالجة عدم المطابقة للبند {q.code} وفق معيار التحقق المعتمد.",
                        "preventive_action_plan": "تحديث إجراءات الرقابة الذاتية وHACCP لمنع تكرار المخالفة.",
                        "target_completion_date": due_date,
                    },
                )

        if auto_create_capa_and_reinspection and created_violations:
            ReinspectionSchedule.objects.get_or_create(
                visit=visit,
                scheduled_date=due_date,
                defaults={
                    "violation": created_violations[0],
                    "assigned_inspector_name": visit.inspector_name,
                    "notes": "إعادة تفتيش مجدولة تلقائياً للتحقق من تنفيذ الإجراءات التصحيحية (CAPA).",
                },
            )

    AuditLogEntry.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else visit.inspector_user,
        actor_name=visit.inspector_name,
        action="PROCESS_INSPECTION_VISIT",
        model_name="InspectionVisit",
        object_id=str(visit.id),
        details=(
            f"المحضر {visit.reference_code} | درجة الالتزام: {visit.compliance_score_pct}% | "
            f"مخالفات حرجة: {visit.critical_violations_count} | المخاطر: {visit.risk_level}"
        ),
    )

    return visit