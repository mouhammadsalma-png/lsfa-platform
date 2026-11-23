from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from food_safety.models import (
    AuditLog,
    CitizenComplaint,
    ComplaintStatus,
    FoodEstablishment,
    Governorate,
    InspectionStatus,
    InspectionVisit,
    LabSample,
    OfficialCorrespondence,
    ProductBatchRecall,
    RecallStatus,
    RiskLevel,
    SampleResultStatus,
    SectorFormType,
    ViolationRecord,
    ViolationStatus,
)


class Command(BaseCommand):
    help = "تهيئة المنصة الوطنية لسلامة الغذاء (LSFA) ببيانات رقابية أولية شاملة"

    def handle(self, *args, **options):
        today = timezone.localdate()
        User = get_user_model()
        inspector = User.objects.filter(is_staff=True).first()

        # 1. السجل الوطني للمؤسسات الغذائية
        est1, _ = FoodEstablishment.objects.get_or_create(
            code="LSFA-BEI-001",
            defaults={
                "name": "ملحمة ومشاوي الأرز الحديثة",
                "sector": SectorFormType.MEAT_POULTRY,
                "governorate": Governorate.BEIRUT,
                "district": "بيروت - الحمرا",
                "address": "شارع المقدسي، بناء السلام، طابق أرضي",
                "latitude": Decimal("33.896900"),
                "longitude": Decimal("35.482300"),
                "owner_name": "سامي الحسن",
                "phone": "01-345678",
                "license_number": "LIC-2026-104",
                "workers_count": 14,
                "risk_level": RiskLevel.HIGH,
                "next_inspection_due": today + timedelta(days=15),
                "is_active": True,
            },
        )

        est2, _ = FoodEstablishment.objects.get_or_create(
            code="LSFA-BKA-002",
            defaults={
                "name": "معمل ألبان وأجبان البقاع الأخضر",
                "sector": SectorFormType.DAIRY,
                "governorate": Governorate.BEKAA,
                "district": "زحلة",
                "address": "المنطقة الصناعية، بلوك B",
                "latitude": Decimal("33.846300"),
                "longitude": Decimal("35.902000"),
                "owner_name": "نديم الخوري",
                "phone": "08-812345",
                "license_number": "LIC-2026-219",
                "workers_count": 32,
                "risk_level": RiskLevel.MEDIUM,
                "next_inspection_due": today + timedelta(days=30),
                "is_active": True,
            },
        )

        est3, _ = FoodEstablishment.objects.get_or_create(
            code="LSFA-NOR-003",
            defaults={
                "name": "مخازن التبريد الساحلية",
                "sector": SectorFormType.STORAGE_COLD,
                "governorate": Governorate.NORTH,
                "district": "طرابلس",
                "address": "الميناء، قرب المنطقة الحرة",
                "latitude": Decimal("34.451200"),
                "longitude": Decimal("35.812400"),
                "owner_name": "طارق المقدم",
                "phone": "06-601122",
                "license_number": "LIC-2026-308",
                "workers_count": 21,
                "risk_level": RiskLevel.LOW,
                "next_inspection_due": today + timedelta(days=60),
                "is_active": True,
            },
        )

        est4, _ = FoodEstablishment.objects.get_or_create(
            code="LSFA-MLB-004",
            defaults={
                "name": "أفران وحلويات الجبل الذهبي",
                "sector": SectorFormType.BAKERY_SWEETS,
                "governorate": Governorate.MOUNT_LEBANON,
                "district": "المتن",
                "address": "جل الديب، الطريق العام",
                "latitude": Decimal("33.908500"),
                "longitude": Decimal("35.578100"),
                "owner_name": "رلى عون",
                "phone": "04-712900",
                "license_number": "LIC-2026-412",
                "workers_count": 18,
                "risk_level": RiskLevel.LOW,
                "next_inspection_due": today + timedelta(days=45),
                "is_active": True,
            },
        )

        # 2. زيارات التفتيش والمحاضر (يتم احتساب النسبة والخطورة تلقائياً في save)
        insp1, _ = InspectionVisit.objects.get_or_create(
            reference_code="INSP-2026-0001",
            defaults={
                "establishment": est1,
                "form_type": SectorFormType.MEAT_POULTRY,
                "inspector": inspector,
                "scheduled_date": today - timedelta(days=3),
                "status": InspectionStatus.COMPLETED,
                "hygiene_score": 12,
                "cold_chain_score": 9,
                "cross_contamination_score": 11,
                "traceability_labeling_score": 12,
                "water_pest_waste_score": 11,
                "measured_cold_temp": Decimal("8.40"),
                "findings": "ارتفاع حرارة براد اللحوم النيئة إلى 8.4°C وعدم فصل ألواح التقطيع.",
                "party_acknowledged": True,
            },
        )

        insp2, _ = InspectionVisit.objects.get_or_create(
            reference_code="INSP-2026-0002",
            defaults={
                "establishment": est2,
                "form_type": SectorFormType.DAIRY,
                "inspector": inspector,
                "scheduled_date": today - timedelta(days=1),
                "status": InspectionStatus.COMPLETED,
                "hygiene_score": 17,
                "cold_chain_score": 16,
                "cross_contamination_score": 18,
                "traceability_labeling_score": 14,
                "water_pest_waste_score": 16,
                "measured_cold_temp": Decimal("4.20"),
                "findings": "الالتزام العام جيد مع الحاجة لتحديث سجل تتبع دفعات الحليب الخام.",
                "party_acknowledged": True,
            },
        )

        insp3, _ = InspectionVisit.objects.get_or_create(
            reference_code="INSP-2026-0003",
            defaults={
                "establishment": est3,
                "form_type": SectorFormType.STORAGE_COLD,
                "inspector": inspector,
                "scheduled_date": today + timedelta(days=2),
                "status": InspectionStatus.ASSIGNED,
                "hygiene_score": 20,
                "cold_chain_score": 20,
                "cross_contamination_score": 20,
                "traceability_labeling_score": 20,
                "water_pest_waste_score": 20,
                "measured_cold_temp": Decimal("-18.50"),
                "findings": "زيارة دورية مبرمجة للتحقق من غرف التجميد.",
                "party_acknowledged": False,
            },
        )

        # 3. المخالفات والضبوط والإحالات (CAPA)
        ViolationRecord.objects.get_or_create(
            establishment=est1,
            inspection=insp1,
            legal_reference="المادة 14 و22 من قانون سلامة الغذاء رقم 35/2015",
            defaults={
                "severity": RiskLevel.HIGH,
                "description": "تخزين لحوم مبردة على حرارة 8.4 درجة مئوية متجاوزة الحد الأقصى المسموح به (4°C).",
                "capa_required": "صيانة ضاغط البراد فوراً، إتلاف الكمية المتأثرة، وتركيب مسجل حرارة رقمي.",
                "capa_deadline": today + timedelta(days=5),
                "status": ViolationStatus.IN_PROGRESS,
                "referred_to": "مصلحة حماية المستهلك / النيابة العامة البيئية",
                "created_by": inspector,
            },
        )

        # 4. العينات المخبرية وسلسلة الحيازة
        LabSample.objects.get_or_create(
            sample_code="SMP-2026-0101",
            defaults={
                "establishment": est1,
                "inspection": insp1,
                "product_name": "لحم بقر مفروم طازج",
                "batch_number": "LOT-M26-09",
                "collected_by": "مفتش سلامة الغذاء - فريق بيروت",
                "receiving_lab": "المختبر المركزي للصحة العامة - بيروت",
                "chain_of_custody_notes": "نُقلت بحافظة مبردة معقمة على حرارة 2°C بختم أمني رقم 8841.",
                "status": SampleResultStatus.NON_CONFORMING,
                "lab_report_summary": "تجاوز في التعداد البكتيري العام (E. coli) عن الحدود القياسية اللبنانية.",
            },
        )

        LabSample.objects.get_or_create(
            sample_code="SMP-2026-0102",
            defaults={
                "establishment": est2,
                "inspection": insp2,
                "product_name": "لبنة بلدية مبسترة",
                "batch_number": "LOT-D26-44",
                "collected_by": "مفتش سلامة الغذاء - فريق البقاع",
                "receiving_lab": "مختبر معهد البحوث الصناعية (IRI)",
                "chain_of_custody_notes": "ختم أمني رقم 9012، استلام خلال ساعتين من السحب.",
                "status": SampleResultStatus.CONFORMING,
                "lab_report_summary": "مطابقة جرثومياً وكيميائياً للمواصفات القياسية.",
            },
        )

        # 5. التتبع الغذائي والاستدعاء
        ProductBatchRecall.objects.get_or_create(
            batch_code="RCL-2026-77A",
            defaults={
                "product_name": "لحم بقر مفروم مبرد - عبوة 1 كغ",
                "producer_or_importer": est1,
                "supply_chain_nodes": "نقطة البيع الرئيسية في الحمرا + 3 مطاعم متعاقدة في بيروت",
                "status": RecallStatus.ACTIVE_RECALL,
                "recall_reason": "عدم مطابقة العينة المخبرية SMP-2026-0101 وخلل في سلسلة التبريد.",
                "is_public_alert": True,
            },
        )

        ProductBatchRecall.objects.get_or_create(
            batch_code="TRC-2026-19B",
            defaults={
                "product_name": "لبنة بلدية كاملة الدسم 500 غ",
                "producer_or_importer": est2,
                "supply_chain_nodes": "سوبرماركت البقاع وبيروت الكبرى",
                "status": RecallStatus.MONITORING,
                "recall_reason": "تتبع روتيني للدفعة التشغيلية.",
                "is_public_alert": False,
            },
        )

        # 6. الشكاوى والبلاغات
        if not CitizenComplaint.objects.filter(establishment_name="ملحمة ومشاوي الأرز الحديثة").exists():
            CitizenComplaint.objects.create(
                reporter_name="مواطن - بيروت",
                reporter_phone="70-123456",
                governorate=Governorate.BEIRUT,
                establishment_name="ملحمة ومشاوي الأرز الحديثة",
                linked_establishment=est1,
                severity=RiskLevel.HIGH,
                details="ملاحظة تغير في رائحة اللحوم المعروضة وضعف تبريد واجهة العرض.",
                status=ComplaintStatus.INVESTIGATING,
                resolution_notes="تم تسيير دورية تفتيش فورية وسحب عينة مخبرية وفتح محضر ضبط.",
            )

        if not CitizenComplaint.objects.filter(establishment_name="أفران وحلويات الجبل الذهبي").exists():
            CitizenComplaint.objects.create(
                reporter_name="مواطنة - المتن",
                reporter_phone="71-987654",
                governorate=Governorate.MOUNT_LEBANON,
                establishment_name="أفران وحلويات الجبل الذهبي",
                linked_establishment=est4,
                severity=RiskLevel.LOW,
                details="استفسار حول تاريخ الصلاحية المطبوع على علب الحلويات.",
                status=ComplaintStatus.RESOLVED,
                resolution_notes="تم التحقق الميداني وتبين وضوح التواريخ ومطابقتها.",
            )

        # 7. المراسلات والأرشفة والحوكمة
        OfficialCorrespondence.objects.get_or_create(
            ref_number="LSFA-OUT-2026-055",
            defaults={
                "direction": "OUTGOING",
                "subject": "إنذار خطي وتكليف بتنفيذ إجراءات تصحيحية عاجلة",
                "counterparty": "إدارة ملحمة ومشاوي الأرز الحديثة",
                "related_establishment": est1,
                "summary": "إبلاغ المؤسسة بنتيجة محضر INSP-2026-0001 وضرورة إغلاق المخالفة خلال 5 أيام.",
                "issued_date": today - timedelta(days=2),
            },
        )

        # 8. سجل التدقيق الإلكتروني (Audit Log)
        if not AuditLog.objects.filter(action="SEED_INITIAL_DATA").exists():
            AuditLog.objects.create(
                actor=inspector,
                action="SEED_INITIAL_DATA",
                target_model="FoodEstablishment",
                target_id="LSFA-BEI-001..004",
                details={"source": "manage.py seed_lsfa", "records_seeded": True},
            )

        self.stdout.write(self.style.SUCCESS("تمت تهيئة بيانات المنصة الوطنية لسلامة الغذاء (LSFA) بنجاح!"))