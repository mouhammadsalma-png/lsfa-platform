from decimal import Decimal
from django.core.management.base import BaseCommand
from food_safety.models import (
    AuditAxis,
    AuditQuestion,
    FoodEstablishment,
    Governorate,
    InspectionFormCode,
    InspectionTemplate,
    QuestionSeverity,
    RiskLevel,
)


SECTOR_DEFINITIONS = [
    (
        InspectionFormCode.SMI_01,
        "استمارة تفتيش المسالخ",
        "Slaughterhouses Inspection Form",
        "ISO 22000:2018 | Codex CXC 58-2005 | HACCP",
        "حرارة التبريد ≤ 4°C | التجميد ≤ -18°C | فحص ما قبل وبعد الذبح",
    ),
    (
        InspectionFormCode.BMI_02,
        "استمارة تفتيش الملاحم ومحلات بيع اللحوم",
        "Butcheries & Meat Shops Inspection Form",
        "ISO 22000:2018 | Codex CXC 58-2005 | HACCP",
        "عرض اللحوم المبردة ≤ 4°C | المجمدة ≤ -18°C | فصل كامل للنيء عن الجاهز",
    ),
    (
        InspectionFormCode.FPM_03,
        "استمارة تفتيش مصانع ومعامل الصناعات الغذائية",
        "Food Processing Plants Inspection Form",
        "ISO 22000:2018 | Codex CXC 1-1969 | HACCP",
        "التحقق من نقاط التحكم الحرجة (CCPs) والمعايرة الموثقة لأجهزة القياس",
    ),
    (
        InspectionFormCode.WHD_04,
        "استمارة تفتيش المستودعات والتخزين والنقل الغذائي",
        "Warehousing, Storage & Food Transport Inspection Form",
        "ISO 22000:2018 | ISO/TS 22002-5 | Codex GPFH",
        "التبريد 0–4°C | التجميد ≤ -18°C | التخزين الجاف < 25°C ورطوبة < 60%",
    ),
    (
        InspectionFormCode.RES_05,
        "استمارة تفتيش المطاعم والمطابخ والمؤسسات الغذائية",
        "Restaurants, Kitchens & Food Services Inspection Form",
        "ISO 22000:2018 | Codex CXC 39-1993 | HACCP",
        "الطهي ≥ 75°C | الحفظ الساخن ≥ 63°C | التبريد السريع والتخزين البارد ≤ 4°C",
    ),
    (
        InspectionFormCode.RET_06,
        "استمارة تفتيش السوبرماركت ومحلات بيع المواد الغذائية",
        "Supermarkets & Food Retail Inspection Form",
        "ISO 22000:2018 | Codex CXC 1-1969 | HACCP",
        "برادات العرض ≤ 4°C | المجمدات ≤ -18°C | سلامة بطاقات البيان والصلاحية",
    ),
    (
        InspectionFormCode.PRI_07,
        "استمارة تفتيش المخابز والأفران",
        "Bakeries & Ovens Inspection Form",
        "ISO 22000:2018 | Codex GPFH | HACCP (Allergens & Mycotoxins)",
        "حفظ القشدة والكريما ≤ 4°C | ضبط الرطوبة والآفات في مخازن الدقيق والمكسرات",
    ),
]


AXES_AND_QUESTIONS = [
    (
        "AX-01",
        "النظافة الشخصية والمنشأة والجاهزية الصحية",
        "Personal Hygiene, Premises & Sanitation Readiness",
        "Codex GPFH / ISO 22000 (7.2)",
        1,
        [
            (
                "Q-01",
                "سلامة البنية التحتية والأسطح الملامسة للغذاء وسهولة تنظيفها وتعقيمها",
                "Infrastructure, food-contact surfaces & cleanability",
                "أسطح ملساء غير ماصة وخالية من التشقق أو الصدأ أو التقشّر",
                "Smooth, non-absorbent surfaces free from cracks, rust, or peeling",
                "معاينة بصرية مباشرة + سجل الصيانة والتعقيم",
                Decimal("20.00"),
                QuestionSeverity.MAJOR,
                1,
            ),
            (
                "Q-02",
                "النظافة الشخصية للعاملين والملابس الواقية ومرافق غسل اليدين",
                "Staff personal hygiene, protective gear & handwashing facilities",
                "توفر مغاسل بماء وصابون ومجففات صحية والتزام العاملين بالزي الرسمي",
                "Handwashing stations with soap/sanitizers and staff compliance with PPE",
                "معاينة بصرية أثناء العمل + سجلات اللياقة الصحية",
                Decimal("15.00"),
                QuestionSeverity.MAJOR,
                1,
            ),
        ],
    ),
    (
        "AX-02",
        "التحكم الحراري وسلسلة التبريد (HACCP CCPs)",
        "Thermal Control & Cold Chain (HACCP CCPs)",
        "HACCP Principle 3 (Critical Limits)",
        2,
        [
            (
                "Q-03",
                "الالتزام بالحدود الحرارية الحرجة في التبريد أو التجميد أو الطهي أو البسترة",
                "Compliance with critical temperature limits (chilling, freezing, cooking, pasteurization)",
                "مطابقة القراءات الفعلية وسجلات المراقبة للحدود الحرجة المعتمدة للقطاع",
                "Actual readings and monitoring logs match approved sector critical limits",
                "قياس مباشر بميزان حرارة معاير + مراجعة سجلات الرصد",
                Decimal("25.00"),
                QuestionSeverity.CRITICAL,
                2,
            ),
        ],
    ),
    (
        "AX-03",
        "منع التلوث المتبادل وإدارة مسببات الحساسية والتتبع",
        "Cross-Contamination Control, Allergens & Traceability",
        "ISO 22000 (8.3, 8.5) / Codex",
        3,
        [
            (
                "Q-04",
                "منع التلوث المتبادل والفصل الفعلي بين المواد الخام والمنتجات الجاهزة ومسببات الحساسية",
                "Cross-contamination prevention, segregation of raw/ready foods & allergens",
                "فصل الأدوات والمناطق والتخزين ومنع اختلاط الملوثات الفيزيائية والكيميائية والبيولوجية",
                "Physical segregation of raw/ready items, tools, and allergen controls",
                "معاينة ميدانية + صور توثيقية عند وجود أي تداخل",
                Decimal("20.00"),
                QuestionSeverity.CRITICAL,
                3,
            ),
            (
                "Q-05",
                "توافر التتبع وسجلات التشغيل وبطاقات البيان وصلاحية المواد الغذائية",
                "Traceability, batch records, labeling & shelf-life compliance",
                "إمكانية تتبع الدفعة/التشغيلة وسلامة بيانات البطاقة وغياب المنتجات المنتهية الصلاحية",
                "Batch traceability, accurate labeling, and no expired products on site",
                "فحص سجلات التتبع والملصقات وبطاقات البيان",
                Decimal("20.00"),
                QuestionSeverity.MAJOR,
                4,
            ),
        ],
    ),
]


class Command(BaseCommand):
    help = "تهيئة الاستمارات القطاعية السبع (SMI-01 إلى PRI-07) والمحاور والأسئلة ومؤسسات نموذجية"

    def handle(self, *args, **options):
        for form_code, title_ar, title_en, standards, limits in SECTOR_DEFINITIONS:
            template, _ = InspectionTemplate.objects.update_or_create(
                form_code=form_code,
                defaults={
                    "title_ar": title_ar,
                    "title_en": title_en,
                    "version": "1.0",
                    "standards_reference": standards,
                    "critical_limits_summary": limits,
                    "allow_not_applicable": True,
                    "require_na_justification": True,
                    "max_na_ratio_pct": Decimal("30.00"),
                    "is_active": True,
                },
            )

            for ax_code, ax_ar, ax_en, clause, ax_order, questions in AXES_AND_QUESTIONS:
                axis, _ = AuditAxis.objects.update_or_create(
                    template=template,
                    code=ax_code,
                    defaults={
                        "title_ar": ax_ar,
                        "title_en": ax_en,
                        "standard_clause": clause,
                        "sort_order": ax_order,
                        "is_active": True,
                    },
                )

                for (
                    q_code,
                    q_ar,
                    q_en,
                    crit_ar,
                    crit_en,
                    proof,
                    weight,
                    severity,
                    q_order,
                ) in questions:
                    AuditQuestion.objects.update_or_create(
                        axis=axis,
                        code=f"{form_code}-{q_code}",
                        defaults={
                            "text_ar": q_ar,
                            "text_en": q_en,
                            "verification_criteria_ar": crit_ar,
                            "verification_criteria_en": crit_en,
                            "proof_method": proof,
                            "weight": weight,
                            "severity": severity,
                            "can_be_not_applicable": True,
                            "sort_order": q_order,
                            "is_active": True,
                        },
                    )

            est_code = f"EST-{form_code}"
            FoodEstablishment.objects.get_or_create(
                code=est_code,
                defaults={
                    "name_ar": f"منشأة نموذجية - {title_ar}",
                    "name_en": f"Sample Facility - {title_en}",
                    "primary_form_code": form_code,
                    "governorate": Governorate.BEIRUT,
                    "district": "بيروت",
                    "risk_level": RiskLevel.MEDIUM,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS("تمت تهيئة الاستمارات القطاعية السبع (SMI-01 إلى PRI-07) والأسئلة والمؤسسات النموذجية بنجاح.")
        )