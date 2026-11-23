from decimal import Decimal, ROUND_HALF_UP
from food_safety.models import ChecklistSection, ChecklistVersion

ANSWER_MULTIPLIERS = {
    "COMPLIANT": Decimal("1.0"),
    "PARTIALLY_COMPLIANT": Decimal("0.5"),
    "NON_COMPLIANT": Decimal("0.0"),
}


def get_applicable_items(checklist_version: ChecklistVersion, activity_code: str | None = None):
    """
    يرجع البنود الفعالة المنطبقة على النشاط الفرعي المختار ضمن إصدار الاستمارة.
    """
    sections = (
        ChecklistSection.objects.filter(checklist_version=checklist_version)
        .prefetch_related("items")
        .order_by("sort_order", "code")
    )

    applicable = []
    for section in sections:
        sec_activities = section.applicable_activities or []
        if activity_code and sec_activities and activity_code not in sec_activities:
            continue

        for item in section.items.filter(is_active=True).order_by("item_number", "item_code"):
            item_activities = item.applicable_activities or []
            if activity_code and item_activities and activity_code not in item_activities:
                continue
            applicable.append(item)

    return applicable


def evaluate_checklist_responses(items_with_responses: list[dict]) -> dict:
    """
    يطبّع الأوزان إلى 100 نقطة على البنود المنطبقة الفعالة فقط بعد استبعاد NOT_APPLICABLE،
    ويبقي المخالفات الحرجة (CRITICAL + NON_COMPLIANT) ظاهرة بشكل مستقل.
    """
    active_rows = [
        row for row in items_with_responses
        if row.get("response_status") in ANSWER_MULTIPLIERS
    ]

    if not active_rows:
        return {
            "compliance_score": None,
            "critical_violations": [],
            "non_compliant_items": [],
            "compliant_items": [],
            "partial_items": [],
            "has_critical_finding": False,
            "assessment_status": "NOT_ASSESSED",
            "evaluated_rows": [],
        }

    total_raw = sum(Decimal(str(r.get("raw_weight", 1) or 1)) for r in active_rows)
    if total_raw <= 0:
        total_raw = Decimal(len(active_rows))

    total_earned = Decimal("0.00")
    critical_violations = []
    non_compliant_items = []
    compliant_items = []
    partial_items = []
    evaluated_rows = []

    for row in active_rows:
        raw_w = Decimal(str(row.get("raw_weight", 1) or 1))
        norm_weight = (raw_w * Decimal("100")) / total_raw
        resp = row["response_status"]
        earned = norm_weight * ANSWER_MULTIPLIERS[resp]
        total_earned += earned

        severity = (row.get("severity") or "MAJOR").upper()
        is_critical_violation = resp == "NON_COMPLIANT" and severity == "CRITICAL"

        if resp == "COMPLIANT":
            compliant_items.append(row)
        elif resp == "PARTIALLY_COMPLIANT":
            partial_items.append(row)
        elif resp == "NON_COMPLIANT":
            non_compliant_items.append(row)
            if is_critical_violation:
                critical_violations.append(row)

        evaluated_rows.append({
            **row,
            "severity": severity,
            "normalized_weight": norm_weight.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "earned_points": earned.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "is_critical_violation": is_critical_violation,
        })

    score = total_earned.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if critical_violations:
        assessment_status = "CRITICAL_FINDINGS"
    elif score >= Decimal("90.00"):
        assessment_status = "HIGH_COMPLIANCE"
    elif score >= Decimal("75.00"):
        assessment_status = "ACCEPTABLE_WITH_FINDINGS"
    elif score >= Decimal("50.00"):
        assessment_status = "LOW_COMPLIANCE"
    else:
        assessment_status = "VERY_LOW_COMPLIANCE"

    return {
        "compliance_score": float(score),
        "critical_violations": critical_violations,
        "non_compliant_items": non_compliant_items,
        "compliant_items": compliant_items,
        "partial_items": partial_items,
        "has_critical_finding": len(critical_violations) > 0,
        "assessment_status": assessment_status,
        "evaluated_rows": evaluated_rows,
    }


def calculate_independent_risk_score(
    food_type_score: int,
    process_complexity_score: int,
    population_exposure_score: int,
    cold_chain_score: int,
    history_score: int,
    has_serious_incident: bool = False,
    has_critical_factor: bool = False,
) -> dict:
    """
    محرك مستقل لتقييم مخاطر المؤسسة يستقبل القيم الرقمية (1..4) مباشرة،
    ويراعي الحوادث الجسيمة والعوامل الحرجة دون الاعتماد على المعدل وحده.
    """
    scores = [
        food_type_score,
        process_complexity_score,
        population_exposure_score,
        cold_chain_score,
        history_score,
    ]
    if any(not isinstance(val, int) or val < 1 or val > 4 for val in scores):
        raise ValueError("كل عامل خطورة يجب أن يكون عدداً صحيحاً بين 1 و 4.")

    weights = [
        Decimal("25"),  # طبيعة الغذاء
        Decimal("20"),  # تعقيد العمليات
        Decimal("20"),  # مدى التعرض
        Decimal("15"),  # الاعتماد على سلسلة التبريد
        Decimal("20"),  # السجل الرقابي / المخالفات
    ]

    weighted_score = sum(
        (Decimal(val) / Decimal("4")) * w for val, w in zip(scores, weights)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if has_serious_incident or has_critical_factor or weighted_score >= Decimal("85.00"):
        risk_level = "CRITICAL"
    elif weighted_score >= Decimal("65.00"):
        risk_level = "HIGH"
    elif weighted_score >= Decimal("40.00"):
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_score": float(weighted_score),
        "risk_level": risk_level,
    }