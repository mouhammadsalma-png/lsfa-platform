from django.db.models import Avg, Count
from .models import (
    InspectionFormCode,
    InspectionTemplate,
    InspectionVisit,
)


def get_sector_audit_template(form_code):
    template = InspectionTemplate.objects.filter(form_code=form_code, is_active=True).first()
    if template:
        return {
            "title": template.title_ar,
            "title_en": template.title_en,
            "standards": template.standards_reference,
            "critical_limits": template.critical_limits_summary,
            "version": template.version,
        }
    return {
        "title": "استمارة التفتيش القطاعية",
        "title_en": "Sector Inspection Form",
        "standards": "ISO 22000:2018 | Codex Alimentarius | HACCP",
        "critical_limits": "الالتزام بالحدود الحرارية والصحية المعتمدة للقطاع",
        "version": "1.0",
    }


def get_inspections_queryset(sector=None, form_type=None, status=None):
    qs = InspectionVisit.objects.select_related("establishment", "template", "inspector_user").all()
    code = form_type or sector
    if code:
        qs = qs.filter(template__form_code=code)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_inspections_by_sector_summary():
    summary = []
    for form_code, form_label in InspectionFormCode.choices:
        qs = InspectionVisit.objects.filter(template__form_code=form_code)
        agg = qs.aggregate(
            total_visits=Count("id"),
            avg_compliance=Avg("compliance_score_pct"),
        )
        info = get_sector_audit_template(form_code)
        summary.append({
            "sector_code": form_code,
            "sector_label": form_label,
            "standards": info["standards"],
            "total_visits": agg["total_visits"] or 0,
            "avg_compliance_pct": round(float(agg["avg_compliance"] or 0), 1),
        })
    return summary