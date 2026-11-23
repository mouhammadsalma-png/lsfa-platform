from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


# =========================================================================
# 1. النماذج الأساسية الحالية للمنصة (متوافقة مع admin.py و views.py)
# =========================================================================

class FoodEstablishment(models.Model):
    code = models.CharField(max_length=60, unique=True)
    name_ar = models.CharField(max_length=250)
    name_en = models.CharField(max_length=250, blank=True)
    commercial_name = models.CharField(max_length=250, blank=True)
    owner_name = models.CharField(max_length=250, blank=True)
    commercial_reg_no = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    primary_form_code = models.CharField(max_length=30, blank=True)
    governorate = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    risk_level = models.CharField(max_length=30, default="MEDIUM", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.commercial_name and self.name_ar:
            self.commercial_name = self.name_ar
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name_ar}"


class InspectionTemplate(models.Model):
    form_code = models.CharField(max_length=30, unique=True)
    title_ar = models.CharField(max_length=250)
    title_en = models.CharField(max_length=250, blank=True)
    version = models.CharField(max_length=30, default="1.0")
    standards_reference = models.CharField(max_length=255, blank=True)
    allow_not_applicable = models.BooleanField(default=True)
    require_na_justification = models.BooleanField(default=False)
    max_na_ratio_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("50.00"))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.form_code} - {self.title_ar}"


class AuditAxis(models.Model):
    template = models.ForeignKey(InspectionTemplate, on_delete=models.CASCADE, related_name="axes")
    code = models.CharField(max_length=30)
    title_ar = models.CharField(max_length=250)
    title_en = models.CharField(max_length=250, blank=True)
    standard_clause = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.title_ar}"


class AuditQuestion(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "حرجة"
        MAJOR = "MAJOR", "جسيمة"
        MODERATE = "MODERATE", "متوسطة"
        MINOR = "MINOR", "طفيفة"

    axis = models.ForeignKey(AuditAxis, on_delete=models.CASCADE, related_name="questions")
    code = models.CharField(max_length=40)
    text_ar = models.TextField()
    text_en = models.TextField(blank=True)
    verification_criteria_ar = models.TextField(blank=True)
    proof_method = models.CharField(max_length=120, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("5.00"))
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MAJOR)
    can_be_not_applicable = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.text_ar[:60]}"


class InspectionVisit(models.Model):
    reference_code = models.CharField(max_length=80, unique=True)
    establishment = models.ForeignKey(FoodEstablishment, on_delete=models.CASCADE, related_name="visits")
    template = models.ForeignKey(InspectionTemplate, on_delete=models.PROTECT, related_name="visits")
    inspector_name = models.CharField(max_length=200)
    inspector_ministry = models.CharField(max_length=120, blank=True)
    compliance_score_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    critical_violations_count = models.PositiveIntegerField(default=0)
    has_critical_failure = models.BooleanField(default=False)
    risk_level = models.CharField(max_length=30, default="MEDIUM")
    sync_status = models.CharField(max_length=30, default="SYNCED")
    status = models.CharField(max_length=30, default="DRAFT")
    offline_uuid = models.CharField(max_length=100, blank=True, db_index=True)
    inspected_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.reference_code} ({self.establishment.name_ar})"


class InspectionAnswer(models.Model):
    class Choice(models.TextChoices):
        COMPLIANT = "COMPLIANT", "مطابق"
        PARTIAL = "PARTIAL", "مطابق جزئياً"
        NON_COMPLIANT = "NON_COMPLIANT", "غير مطابق"
        NOT_APPLICABLE = "NOT_APPLICABLE", "لا ينطبق"

    visit = models.ForeignKey(InspectionVisit, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(AuditQuestion, on_delete=models.PROTECT, related_name="answers")
    choice = models.CharField(max_length=30, choices=Choice.choices)
    earned_points = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    max_applicable_points = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    justification = models.TextField(blank=True)

    class Meta:
        unique_together = ("visit", "question")

    def __str__(self):
        return f"{self.visit.reference_code} | {self.question.code}: {self.choice}"


class ViolationRecord(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "حرجة"
        MAJOR = "MAJOR", "جسيمة"
        MODERATE = "MODERATE", "متوسطة"
        MINOR = "MINOR", "طفيفة"

    class Status(models.TextChoices):
        OPEN = "OPEN", "مفتوحة"
        IN_PROGRESS = "IN_PROGRESS", "قيد المعالجة"
        RESOLVED = "RESOLVED", "مغلقة"
        REFERRED = "REFERRED", "محالة"

    code = models.CharField(max_length=80, unique=True)
    visit = models.ForeignKey(InspectionVisit, on_delete=models.CASCADE, related_name="violations")
    establishment = models.ForeignKey(
        FoodEstablishment,
        on_delete=models.CASCADE,
        related_name="violations",
        null=True,
        blank=True,
    )
    question = models.ForeignKey(AuditQuestion, on_delete=models.SET_NULL, null=True, blank=True)
    description_ar = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MAJOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    corrective_action = models.TextField(blank=True)
    verification_note = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.establishment_id and self.visit_id:
            self.establishment_id = self.visit.establishment_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.status}"


class ViolationEvidence(models.Model):
    violation = models.ForeignKey(ViolationRecord, on_delete=models.CASCADE, related_name="evidences")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="violations/evidence/", blank=True, null=True)
    reference_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title


class CorrectiveActionCAPA(models.Model):
    violation = models.ForeignKey(ViolationRecord, on_delete=models.CASCADE, related_name="capas")
    root_cause_analysis = models.TextField(blank=True)
    corrective_action_plan = models.TextField()
    target_completion_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    verified_by_inspector = models.BooleanField(default=False)

    def __str__(self):
        return f"CAPA - {self.violation.code}"


class RegulatoryReferral(models.Model):
    referral_number = models.CharField(max_length=80, unique=True)
    visit = models.ForeignKey(InspectionVisit, on_delete=models.CASCADE, related_name="referrals")
    target_entity = models.CharField(max_length=200)
    summary = models.TextField()
    referred_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return self.referral_number


class ReinspectionSchedule(models.Model):
    visit = models.ForeignKey(InspectionVisit, on_delete=models.CASCADE, related_name="reinspections")
    violation = models.ForeignKey(ViolationRecord, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_date = models.DateField()
    assigned_inspector_name = models.CharField(max_length=200)
    completed_visit = models.ForeignKey(
        InspectionVisit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_reinspections",
    )

    def __str__(self):
        return f"Reinspection {self.visit.reference_code} on {self.scheduled_date}"


class LabSample(models.Model):
    sample_code = models.CharField(max_length=80, unique=True)
    product_name = models.CharField(max_length=200)
    batch_number = models.CharField(max_length=100, blank=True)
    establishment = models.ForeignKey(FoodEstablishment, on_delete=models.CASCADE, related_name="samples")
    visit = models.ForeignKey(InspectionVisit, on_delete=models.SET_NULL, null=True, blank=True)
    lab_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=30, default="PENDING")
    collected_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.sample_code


class AuditLogEntry(models.Model):
    action = models.CharField(max_length=60)
    model_name = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    actor_name = models.CharField(max_length=150, blank=True)
    details = models.TextField(blank=True)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.model_name and self.entity_type:
            self.model_name = self.entity_type
        if not self.entity_type and self.model_name:
            self.entity_type = self.model_name
        if not self.object_id and self.entity_id:
            self.object_id = self.entity_id
        if not self.entity_id and self.object_id:
            self.entity_id = self.object_id
        if not self.actor_name and self.actor:
            self.actor_name = self.actor.get_username()
        if not self.details and self.reason:
            self.details = self.reason
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.action}] {self.model_name}:{self.object_id}"


# =========================================================================
# 2. نماذج المكتبة القطاعية الـ 15 وإصداراتها والأنشطة الفرعية
# =========================================================================

class Sector(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name_ar = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name_ar}"


class SectorActivity(models.Model):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="activities")
    code = models.CharField(max_length=50)
    name_ar = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("sector", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.sector.code}:{self.code} - {self.name_ar}"


class ChecklistVersion(models.Model):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="versions")
    version_label = models.CharField(max_length=30)
    effective_from = models.DateField(default=timezone.now)
    is_published = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("sector", "version_label")
        ordering = ["-effective_from"]

    def __str__(self):
        return f"{self.sector.code} v{self.version_label}"


class ChecklistSection(models.Model):
    checklist_version = models.ForeignKey(ChecklistVersion, on_delete=models.CASCADE, related_name="sections")
    code = models.CharField(max_length=30)
    title_ar = models.CharField(max_length=250)
    title_en = models.CharField(max_length=250)
    sort_order = models.PositiveIntegerField(default=1)
    applicable_activities = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ("checklist_version", "code")
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.title_ar}"


class ChecklistItem(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "حرجة"
        MAJOR = "MAJOR", "جسيمة"
        MODERATE = "MODERATE", "متوسطة"
        MINOR = "MINOR", "طفيفة"

    class EvidenceType(models.TextChoices):
        VISUAL = "VISUAL", "مشاهدة"
        MEASUREMENT = "MEASUREMENT", "قياس"
        DOCUMENT = "DOCUMENT", "مستندات"
        INTERVIEW = "INTERVIEW", "مقابلة"
        LABORATORY = "LABORATORY", "تحليل مخبري"
        PHOTOGRAPH = "PHOTOGRAPH", "صورة"
        RECORD = "RECORD", "سجل"

    section = models.ForeignKey(ChecklistSection, on_delete=models.CASCADE, related_name="items")
    item_code = models.CharField(max_length=60, unique=True)
    item_number = models.CharField(max_length=20)
    title_ar = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300)
    verification_criterion = models.TextField(blank=True)
    verification_method = models.CharField(
        max_length=30,
        choices=EvidenceType.choices,
        default=EvidenceType.VISUAL,
    )
    required_evidence = models.TextField(blank=True)
    raw_weight = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("5.00"))
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MAJOR)
    is_critical_item = models.BooleanField(default=False)
    applicable_activities = models.JSONField(default=list, blank=True)
    legal_reference = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["item_number", "item_code"]

    def save(self, *args, **kwargs):
        if self.severity == self.Severity.CRITICAL:
            self.is_critical_item = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_code} - {self.title_ar}"


class InspectionItemResponse(models.Model):
    class ResponseStatus(models.TextChoices):
        COMPLIANT = "COMPLIANT", "مطابق بالكامل"
        PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT", "مطابق جزئياً"
        NON_COMPLIANT = "NON_COMPLIANT", "غير مطابق"
        NOT_APPLICABLE = "NOT_APPLICABLE", "لا ينطبق"

    visit = models.ForeignKey(
        InspectionVisit,
        on_delete=models.CASCADE,
        related_name="item_responses",
    )
    checklist_item = models.ForeignKey(
        ChecklistItem,
        on_delete=models.PROTECT,
        related_name="responses",
    )
    response_status = models.CharField(max_length=30, choices=ResponseStatus.choices)
    normalized_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    earned_points = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    evidence_type_used = models.CharField(max_length=30, blank=True)
    inspector_notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("visit", "checklist_item")

    def __str__(self):
        return f"{self.visit.reference_code} | {self.checklist_item.item_code}: {self.response_status}"