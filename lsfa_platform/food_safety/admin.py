from django.contrib import admin
from .models import (
    AuditAxis,
    AuditLogEntry,
    AuditQuestion,
    ChecklistItem,
    ChecklistSection,
    ChecklistVersion,
    CorrectiveActionCAPA,
    FoodEstablishment,
    InspectionAnswer,
    InspectionItemResponse,
    InspectionTemplate,
    InspectionVisit,
    LabSample,
    RegulatoryReferral,
    ReinspectionSchedule,
    Sector,
    SectorActivity,
    ViolationEvidence,
    ViolationRecord,
)


class AuditAxisInline(admin.TabularInline):
    model = AuditAxis
    extra = 1
    fields = ("code", "title_ar", "title_en", "standard_clause", "sort_order", "is_active")


class AuditQuestionInline(admin.TabularInline):
    model = AuditQuestion
    extra = 1
    fields = (
        "code",
        "text_ar",
        "weight",
        "severity",
        "proof_method",
        "can_be_not_applicable",
        "sort_order",
        "is_active",
    )


class ViolationEvidenceInline(admin.TabularInline):
    model = ViolationEvidence
    extra = 1
    fields = ("title", "file", "reference_note")


@admin.register(FoodEstablishment)
class FoodEstablishmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ar", "primary_form_code", "governorate", "risk_level", "is_active")
    list_filter = ("primary_form_code", "governorate", "risk_level", "is_active")
    search_fields = ("code", "name_ar", "name_en", "license_number")


@admin.register(InspectionTemplate)
class InspectionTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "form_code",
        "title_ar",
        "version",
        "allow_not_applicable",
        "require_na_justification",
        "max_na_ratio_pct",
        "is_active",
    )
    list_filter = ("is_active", "allow_not_applicable", "require_na_justification")
    search_fields = ("form_code", "title_ar", "title_en", "standards_reference")
    inlines = [AuditAxisInline]


@admin.register(AuditAxis)
class AuditAxisAdmin(admin.ModelAdmin):
    list_display = ("code", "title_ar", "template", "standard_clause", "sort_order", "is_active")
    list_filter = ("template__form_code", "is_active")
    search_fields = ("code", "title_ar", "title_en", "standard_clause")
    inlines = [AuditQuestionInline]


@admin.register(AuditQuestion)
class AuditQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "axis",
        "weight",
        "severity",
        "can_be_not_applicable",
        "sort_order",
        "is_active",
    )
    list_filter = ("axis__template__form_code", "severity", "can_be_not_applicable", "is_active")
    search_fields = ("code", "text_ar", "text_en", "verification_criteria_ar", "proof_method")


@admin.register(InspectionVisit)
class InspectionVisitAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "establishment",
        "template",
        "inspector_name",
        "inspector_ministry",
        "compliance_score_pct",
        "critical_violations_count",
        "risk_level",
        "sync_status",
        "status",
    )
    list_filter = ("template__form_code", "inspector_ministry", "risk_level", "has_critical_failure", "sync_status", "status")
    search_fields = ("reference_code", "establishment__name_ar", "inspector_name", "offline_uuid")


@admin.register(InspectionAnswer)
class InspectionAnswerAdmin(admin.ModelAdmin):
    list_display = ("visit", "question", "choice", "earned_points", "max_applicable_points")
    list_filter = ("choice", "question__severity", "visit__template__form_code")
    search_fields = ("visit__reference_code", "question__code", "justification")


@admin.register(ViolationRecord)
class ViolationRecordAdmin(admin.ModelAdmin):
    list_display = ("code", "visit", "question", "severity", "status", "due_date")
    list_filter = ("severity", "status", "visit__template__form_code")
    search_fields = ("code", "visit__reference_code", "description_ar")
    inlines = [ViolationEvidenceInline]


@admin.register(CorrectiveActionCAPA)
class CorrectiveActionCAPAAdmin(admin.ModelAdmin):
    list_display = ("violation", "target_completion_date", "is_completed", "verified_by_inspector")
    list_filter = ("is_completed", "verified_by_inspector")
    search_fields = ("violation__code", "root_cause_analysis", "corrective_action_plan")


@admin.register(RegulatoryReferral)
class RegulatoryReferralAdmin(admin.ModelAdmin):
    list_display = ("referral_number", "visit", "target_entity", "referred_at", "is_resolved")
    list_filter = ("target_entity", "is_resolved")
    search_fields = ("referral_number", "visit__reference_code", "summary")


@admin.register(ReinspectionSchedule)
class ReinspectionScheduleAdmin(admin.ModelAdmin):
    list_display = ("visit", "violation", "scheduled_date", "assigned_inspector_name", "completed_visit")
    list_filter = ("scheduled_date",)
    search_fields = ("visit__reference_code", "assigned_inspector_name")


@admin.register(LabSample)
class LabSampleAdmin(admin.ModelAdmin):
    list_display = ("sample_code", "product_name", "establishment", "lab_name", "status", "collected_at")
    list_filter = ("status", "lab_name")
    search_fields = ("sample_code", "product_name", "batch_number", "establishment__name_ar")


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "model_name", "object_id", "actor_name")
    list_filter = ("action", "model_name")
    search_fields = ("actor_name", "model_name", "object_id", "details")


# =========================================================================
# تسجيل نماذج المكتبة القطاعية الـ 15 وإصداراتها والأنشطة الفرعية
# =========================================================================

@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ar", "name_en", "is_active")
    search_fields = ("code", "name_ar", "name_en")


@admin.register(SectorActivity)
class SectorActivityAdmin(admin.ModelAdmin):
    list_display = ("sector", "code", "name_ar", "name_en", "is_active")
    list_filter = ("sector", "is_active")
    search_fields = ("code", "name_ar", "name_en")


@admin.register(ChecklistVersion)
class ChecklistVersionAdmin(admin.ModelAdmin):
    list_display = ("sector", "version_label", "effective_from", "is_published")
    list_filter = ("sector", "is_published")


@admin.register(ChecklistSection)
class ChecklistSectionAdmin(admin.ModelAdmin):
    list_display = ("code", "title_ar", "checklist_version", "sort_order")
    list_filter = ("checklist_version__sector__code",)


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "title_ar", "section", "severity", "raw_weight", "is_active")
    list_filter = ("severity", "verification_method", "is_active", "section__checklist_version__sector__code")
    search_fields = ("item_code", "title_ar", "title_en")


@admin.register(InspectionItemResponse)
class InspectionItemResponseAdmin(admin.ModelAdmin):
    list_display = ("visit", "checklist_item", "response_status", "normalized_weight", "earned_points")
    list_filter = ("response_status",)