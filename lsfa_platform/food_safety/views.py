from collections import defaultdict
import csv
import json
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from food_safety.models import (
    AuditLogEntry,
    ChecklistVersion,
    FoodEstablishment,
    InspectionTemplate,
    InspectionVisit,
    Sector,
    SectorActivity,
    ViolationRecord,
)

SECTOR_GROUPS_ORDER = [
    ("اللحوم والدواجن والمسالخ", ["SLA", "BUT", "SEA"]),
    ("المخابز والحلويات والحبوب", ["BAK", "MIL"]),
    ("الخدمات الغذائية والتموين", ["RST", "CAT"]),
    ("الألبان والزيوت والمشروبات", ["DAI", "OIL", "BEV", "WAT"]),
    ("التخزين والنقل والتغليف والتجزئة", ["SUP", "FRZ", "TRN", "HON", "PKG"]),
]

LEBANON_GOVERNORATE_COORDS = {
    "بيروت": {"lat": 33.8938, "lng": 35.5018},
    "جبل لبنان": {"lat": 33.8360, "lng": 35.6100},
    "الشمال": {"lat": 34.4367, "lng": 35.8497},
    "عكار": {"lat": 34.5450, "lng": 36.0790},
    "البقاع": {"lat": 33.8463, "lng": 35.9020},
    "بعلبك الهرمل": {"lat": 34.0058, "lng": 36.2181},
    "الجنوب": {"lat": 33.2721, "lng": 35.2033},
    "النبطية": {"lat": 33.3789, "lng": 35.4839},
}


def _model_field_names(model_cls):
    return {f.name for f in model_cls._meta.get_fields() if hasattr(f, "attname")}


def _resolve_role_url(role_choice, user):
    role = (role_choice or "").strip().lower()
    if role == "inspector":
        return "/field/"
    if role == "admin":
        return "/admin-dashboard/"
    if user.is_superuser or user.is_staff:
        return "/admin-dashboard/"
    return "/field/"


def home_view(request):
    active_role = request.session.get("active_role") or (
        "admin"
        if (request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff))
        else "inspector"
    )
    current_user_display = (
        request.user.get_full_name() or request.user.get_username()
        if request.user.is_authenticated
        else "زائر / غير مسجل"
    )

    visit_fields = _model_field_names(InspectionVisit)
    visits_qs = InspectionVisit.objects.all()
    if "establishment" in visit_fields:
        visits_qs = visits_qs.select_related("establishment")
    if "inspected_at" in visit_fields:
        visits_qs = visits_qs.order_by("-inspected_at", "-pk")
    else:
        visits_qs = visits_qs.order_by("-pk")

    total_visits = visits_qs.count()
    recent_visits = list(visits_qs[:5])

    vio_fields = _model_field_names(ViolationRecord)
    violations_qs = ViolationRecord.objects.all()
    total_violations = violations_qs.count()
    unclosed_violations = (
        violations_qs.exclude(status="RESOLVED").count()
        if "status" in vio_fields
        else total_violations
    )
    critical_violations = (
        violations_qs.filter(severity="CRITICAL").count()
        if "severity" in vio_fields
        else 0
    )

    context = {
        "is_authenticated": request.user.is_authenticated,
        "current_user_display": current_user_display,
        "active_role": active_role,
        "now_display": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M"),
        "total_visits": total_visits,
        "total_violations": total_violations,
        "unclosed_violations": unclosed_violations,
        "critical_violations": critical_violations,
        "recent_visits": recent_visits,
    }
    return render(request, "food_safety/home.html", context)


def inspector_login(request):
    selected_role = (request.POST.get("role") or request.GET.get("role") or "inspector").strip().lower()
    if selected_role not in {"inspector", "admin"}:
        selected_role = "inspector"

    if request.user.is_authenticated:
        if request.GET.get("role"):
            request.session["active_role"] = selected_role
            next_url = request.GET.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(_resolve_role_url(selected_role, request.user))
        active_role = request.session.get("active_role") or (
            "admin" if (request.user.is_superuser or request.user.is_staff) else "inspector"
        )
        return redirect(_resolve_role_url(active_role, request.user))

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "هذا الحساب غير نشط. يرجى مراجعة الإدارة.")
                return render(request, "food_safety/login.html", {
                    "username": username,
                    "selected_role": selected_role,
                    "next": request.POST.get("next", ""),
                })

            login(request, user)
            request.session["active_role"] = selected_role
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(_resolve_role_url(selected_role, user))

        messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
        return render(request, "food_safety/login.html", {
            "username": username,
            "selected_role": selected_role,
            "next": request.POST.get("next", ""),
        })

    return render(request, "food_safety/login.html", {
        "next": request.GET.get("next", ""),
        "selected_role": selected_role,
    })


@login_required
def inspector_logout(request):
    request.session.pop("active_role", None)
    logout(request)
    return redirect("/")


def _filtered_violations_queryset(request):
    valid_fields = _model_field_names(ViolationRecord)
    related_fields = [f for f in ("establishment", "visit") if f in valid_fields]

    qs = ViolationRecord.objects.all()
    if related_fields:
        qs = qs.select_related(*related_fields)
    if "created_at" in valid_fields:
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("-pk")

    severity = request.GET.get("severity", "").strip().upper()
    status = request.GET.get("status", "").strip().upper()
    query = request.GET.get("q", "").strip()

    if severity in {"CRITICAL", "MAJOR", "MODERATE", "MINOR"} and "severity" in valid_fields:
        qs = qs.filter(severity=severity)
    if status in {"OPEN", "IN_PROGRESS", "RESOLVED", "REFERRED"} and "status" in valid_fields:
        qs = qs.filter(status=status)
    if query and "establishment" in valid_fields:
        est_fields = _model_field_names(FoodEstablishment)
        if "name_ar" in est_fields and "code" in est_fields:
            qs = qs.filter(establishment__name_ar__icontains=query) | qs.filter(
                establishment__code__icontains=query
            )
        elif "name_ar" in est_fields:
            qs = qs.filter(establishment__name_ar__icontains=query)
        elif "code" in est_fields:
            qs = qs.filter(establishment__code__icontains=query)

    return qs


def _matches_activity(applicable_list, activity_code):
    if not activity_code:
        return True
    if not applicable_list:
        return True
    normalized = [str(x).strip().upper() for x in applicable_list]
    return activity_code.upper() in normalized


def _grouped_sectors(sectors_qs):
    by_code = {s.code.upper(): s for s in sectors_qs}
    used_codes = set()
    grouped = []

    for group_label, codes in SECTOR_GROUPS_ORDER:
        group_sectors = []
        for c in codes:
            sec = by_code.get(c.upper())
            if sec:
                group_sectors.append(sec)
                used_codes.add(sec.code.upper())
        if group_sectors:
            grouped.append({"label": group_label, "sectors": group_sectors})

    remaining = [s for s in sectors_qs if s.code.upper() not in used_codes]
    if remaining:
        grouped.append({"label": "قطاعات إضافية", "sectors": remaining})

    return grouped


def _generate_stable_establishment_code(sector_code, now_dt):
    prefix_sector = (sector_code or "GEN").strip().upper()
    seq = FoodEstablishment.objects.count() + 1
    return f"LSFA-{prefix_sector}-{now_dt.strftime('%Y%m%d')}-{seq:04d}"


def _set_if_field_exists(model_cls, target_dict, field_name, value):
    model_fields = _model_field_names(model_cls)
    if field_name in model_fields and value not in (None, ""):
        target_dict[field_name] = value


def _create_or_update_establishment_from_post(request, sector, now_dt):
    mode = request.POST.get("establishment_mode", "existing").strip()
    governorate = request.POST.get("governorate", "").strip()
    district = request.POST.get("district", "").strip()
    address_detail = request.POST.get("address_detail", "").strip()
    owner_or_manager = request.POST.get("owner_or_manager", "").strip()
    phone = request.POST.get("phone", "").strip()
    license_number = request.POST.get("license_number", "").strip()
    gps_lat = request.POST.get("gps_lat", "").strip()
    gps_lng = request.POST.get("gps_lng", "").strip()

    if mode == "new":
        new_name_ar = request.POST.get("new_name_ar", "").strip()
        new_name_en = request.POST.get("new_name_en", "").strip() or new_name_ar
        if not new_name_ar:
            raise ValueError("يرجى إدخال اسم المؤسسة الجديدة باللغة العربية.")

        stable_code = _generate_stable_establishment_code(sector.code if sector else "GEN", now_dt)
        est_kwargs = {
            "code": stable_code,
            "name_ar": new_name_ar,
        }
        _set_if_field_exists(FoodEstablishment, est_kwargs, "name_en", new_name_en)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "sector", sector)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "governorate", governorate)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "district", district)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "address", address_detail)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "address_detail", address_detail)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "owner_name", owner_or_manager)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "manager_name", owner_or_manager)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "phone", phone)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "license_number", license_number)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "latitude", gps_lat)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "longitude", gps_lng)
        _set_if_field_exists(FoodEstablishment, est_kwargs, "is_active", True)

        establishment = FoodEstablishment.objects.create(**est_kwargs)
        AuditLogEntry.objects.create(
            entity_type="FoodEstablishment",
            entity_id=str(establishment.pk),
            action="CREATE",
            actor=request.user,
            after_state={
                "code": stable_code,
                "name_ar": new_name_ar,
                "governorate": governorate,
                "district": district,
                "address_detail": address_detail,
                "gps_lat": gps_lat,
                "gps_lng": gps_lng,
            },
            reason="إنشاء مؤسسة جديدة مع رقم ثابت من شاشة الكشف الميداني",
        )
        return establishment, True

    est_id = request.POST.get("establishment_id")
    establishment = get_object_or_404(FoodEstablishment, pk=est_id)
    est_update_kwargs = {}
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "governorate", governorate)
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "district", district)
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "address", address_detail)
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "address_detail", address_detail)
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "phone", phone)
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "license_number", license_number)
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "latitude", gps_lat)
    _set_if_field_exists(FoodEstablishment, est_update_kwargs, "longitude", gps_lng)
    if est_update_kwargs:
        for k, v in est_update_kwargs.items():
            setattr(establishment, k, v)
        establishment.save(update_fields=list(est_update_kwargs.keys()))
    return establishment, False


def _build_visit_kwargs(establishment, template, user, reference_code, inspected_at, extra_data):
    kwargs = {}

    _set_if_field_exists(InspectionVisit, kwargs, "reference_code", reference_code)
    _set_if_field_exists(InspectionVisit, kwargs, "establishment", establishment)
    if template is not None:
        _set_if_field_exists(InspectionVisit, kwargs, "template", template)
    _set_if_field_exists(InspectionVisit, kwargs, "inspector", user)
    _set_if_field_exists(InspectionVisit, kwargs, "inspector_name", user.get_full_name() or user.get_username())
    _set_if_field_exists(InspectionVisit, kwargs, "inspector_ministry", "LSFA")
    _set_if_field_exists(InspectionVisit, kwargs, "status", "SUBMITTED")
    _set_if_field_exists(InspectionVisit, kwargs, "inspected_at", inspected_at)
    _set_if_field_exists(InspectionVisit, kwargs, "compliance_score", extra_data.get("compliance_score"))
    _set_if_field_exists(InspectionVisit, kwargs, "risk_score", extra_data.get("risk_score"))
    _set_if_field_exists(InspectionVisit, kwargs, "summary_notes", extra_data.get("executive_summary"))
    _set_if_field_exists(InspectionVisit, kwargs, "inspector_signature", extra_data.get("inspector_signature"))
    _set_if_field_exists(InspectionVisit, kwargs, "representative_signature", extra_data.get("representative_signature"))
    _set_if_field_exists(InspectionVisit, kwargs, "representative_name", extra_data.get("representative_name"))
    _set_if_field_exists(InspectionVisit, kwargs, "latitude", extra_data.get("gps_lat"))
    _set_if_field_exists(InspectionVisit, kwargs, "longitude", extra_data.get("gps_lng"))
    _set_if_field_exists(InspectionVisit, kwargs, "gps_lat", extra_data.get("gps_lat"))
    _set_if_field_exists(InspectionVisit, kwargs, "gps_lng", extra_data.get("gps_lng"))

    return kwargs


def _compute_result_and_risk(compliance_score, critical_violations, major_violations, non_compliant_count):
    if critical_violations > 0 or compliance_score < 50:
        outcome = "غير مطابق — إيقاف/إنذار فوري وإحالة مشددة"
        risk_level = "CRITICAL"
        risk_score = min(100, 75 + critical_violations * 10 + non_compliant_count * 2)
    elif compliance_score < 75 or major_violations > 0:
        outcome = "مطابق جزئياً مشروط — مهلة تصحيحية (CAPA)"
        risk_level = "HIGH"
        risk_score = min(74, 45 + major_violations * 8 + non_compliant_count * 3)
    elif compliance_score < 90:
        outcome = "مطابق بملحوظات — متابعة دورية"
        risk_level = "MEDIUM"
        risk_score = min(44, 20 + non_compliant_count * 4)
    else:
        outcome = "مطابق — استيفاء المتطلبات الصحية المعتمدة"
        risk_level = "LOW"
        risk_score = max(5, non_compliant_count * 3)

    return outcome, risk_level, risk_score


@login_required
def field_inspection_view(request):
    request.session["active_role"] = "inspector"
    sectors = Sector.objects.filter(is_active=True).prefetch_related("activities").order_by("code")
    establishments = FoodEstablishment.objects.filter(is_active=True).order_by("name_ar")

    selected_sector_code = request.GET.get("sector", "").strip().upper()
    selected_activity_code = request.GET.get("activity", "").strip().upper()

    selected_sector = None
    if selected_sector_code:
        selected_sector = sectors.filter(code__iexact=selected_sector_code).first()
    if not selected_sector:
        selected_sector = sectors.first()

    activities = (
        SectorActivity.objects.filter(sector=selected_sector, is_active=True).order_by("code")
        if selected_sector
        else SectorActivity.objects.none()
    )

    selected_activity = None
    if selected_activity_code:
        selected_activity = activities.filter(code__iexact=selected_activity_code).first()
    if not selected_activity:
        selected_activity = activities.first()

    version = (
        ChecklistVersion.objects.filter(sector=selected_sector, is_published=True)
        .prefetch_related("sections__items")
        .order_by("-effective_from", "-id")
        .first()
        if selected_sector
        else None
    )
    if not version and selected_sector:
        version = (
            ChecklistVersion.objects.filter(sector=selected_sector)
            .prefetch_related("sections__items")
            .order_by("-effective_from", "-id")
            .first()
        )

    active_act_code = selected_activity.code if selected_activity else ""
    sections_with_items = []
    total_items_count = 0
    critical_items_count = 0

    if version:
        sections_qs = version.sections.prefetch_related("items").order_by("sort_order", "id")
        for sec in sections_qs:
            if not _matches_activity(sec.applicable_activities, active_act_code):
                continue
            items = sorted(
                [
                    item
                    for item in sec.items.filter(is_active=True)
                    if _matches_activity(item.applicable_activities, active_act_code)
                ],
                key=lambda x: (str(x.item_number or ""), str(x.item_code or ""), x.id),
            )
            if items:
                sections_with_items.append({"section": sec, "items": items})
                total_items_count += len(items)
                critical_items_count += sum(1 for i in items if i.severity == "CRITICAL")

    current_user_display = request.user.get_full_name() or request.user.get_username()
    governorates = [
        "بيروت",
        "جبل لبنان",
        "الشمال",
        "عكار",
        "البقاع",
        "بعلبك الهرمل",
        "الجنوب",
        "النبطية",
    ]

    if request.method == "POST":
        inspected_at = timezone.now()
        reference_code = f"VIS-{inspected_at.strftime('%Y%m%d%H%M%S')}"

        try:
            establishment, est_created = _create_or_update_establishment_from_post(
                request, selected_sector, inspected_at
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(request.get_full_path())

        template = InspectionTemplate.objects.filter(is_active=True).first()

        created_violations = 0
        critical_violations = 0
        major_violations = 0
        non_compliant_count = 0
        partially_compliant_count = 0
        compliant_count = 0
        not_applicable_count = 0
        compliant_points = 0.0
        total_weight = 0.0

        for group in sections_with_items:
            for item in group["items"]:
                status_val = request.POST.get(f"status_{item.id}", "COMPLIANT").strip().upper()
                note_val = request.POST.get(f"note_{item.id}", "").strip()
                weight = float(getattr(item, "raw_weight", 0) or 0)

                if status_val == "NOT_APPLICABLE":
                    not_applicable_count += 1
                    continue

                total_weight += weight
                if status_val == "COMPLIANT":
                    compliant_count += 1
                    compliant_points += weight
                elif status_val == "PARTIALLY_COMPLIANT":
                    partially_compliant_count += 1
                    compliant_points += weight * 0.5
                elif status_val == "NON_COMPLIANT":
                    non_compliant_count += 1
                    if item.severity == "CRITICAL":
                        critical_violations += 1
                    elif item.severity == "MAJOR":
                        major_violations += 1

                    legal_ref = getattr(item, "legal_reference", "") or ""
                    ref_suffix = f" [المرجع: {legal_ref}]" if legal_ref else ""
                    note_suffix = f" — ملاحظة: {note_val}" if note_val else ""

                    ViolationRecord.objects.create(
                        code=f"VIO-{reference_code}-{item.item_number}",
                        visit=None,
                        establishment=establishment,
                        description_ar=f"[{item.item_code}] {item.title_ar}{ref_suffix}{note_suffix}",
                        severity=item.severity,
                        status="OPEN",
                    )
                    created_violations += 1

        compliance_score = round((compliant_points / total_weight) * 100, 2) if total_weight > 0 else 100.0
        outcome, risk_level, risk_score = _compute_result_and_risk(
            compliance_score, critical_violations, major_violations, non_compliant_count
        )

        executive_summary = request.POST.get("executive_summary", "").strip()
        representative_name = request.POST.get("representative_name", "").strip()
        inspector_signature = request.POST.get("inspector_signature", "").strip()
        representative_signature = request.POST.get("representative_signature", "").strip()
        governorate = request.POST.get("governorate", "").strip()
        district = request.POST.get("district", "").strip()
        address_detail = request.POST.get("address_detail", "").strip()
        gps_lat = request.POST.get("gps_lat", "").strip()
        gps_lng = request.POST.get("gps_lng", "").strip()
        gps_accuracy = request.POST.get("gps_accuracy", "").strip()
        evidence_caption = request.POST.get("evidence_caption", "").strip()
        uploaded_photos = request.FILES.getlist("evidence_photos")
        photo_names = [f.name for f in uploaded_photos[:15]]

        visit_kwargs = _build_visit_kwargs(
            establishment,
            template,
            request.user,
            reference_code,
            inspected_at,
            {
                "compliance_score": compliance_score,
                "risk_score": risk_score,
                "executive_summary": executive_summary or outcome,
                "inspector_signature": inspector_signature or current_user_display,
                "representative_signature": representative_signature,
                "representative_name": representative_name,
                "gps_lat": gps_lat,
                "gps_lng": gps_lng,
            },
        )
        visit = InspectionVisit.objects.create(**visit_kwargs)

        if created_violations > 0:
            ViolationRecord.objects.filter(
                establishment=establishment,
                visit__isnull=True,
                code__startswith=f"VIO-{reference_code}-",
            ).update(visit=visit)

        AuditLogEntry.objects.create(
            entity_type="InspectionVisit",
            entity_id=str(visit.pk),
            action="CREATE",
            actor=request.user,
            after_state={
                "reference_code": reference_code,
                "establishment_id": establishment.pk,
                "establishment_code": getattr(establishment, "code", ""),
                "establishment_created": est_created,
                "governorate": governorate,
                "district": district,
                "address_detail": address_detail,
                "gps": {
                    "lat": gps_lat,
                    "lng": gps_lng,
                    "accuracy_m": gps_accuracy,
                },
                "evidence_photos_count": len(photo_names),
                "evidence_photos": photo_names,
                "evidence_caption": evidence_caption,
                "sector": selected_sector.code if selected_sector else "",
                "activity": active_act_code,
                "compliance_score": compliance_score,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "outcome": outcome,
                "compliant_count": compliant_count,
                "partially_compliant_count": partially_compliant_count,
                "non_compliant_count": non_compliant_count,
                "not_applicable_count": not_applicable_count,
                "critical_violations": critical_violations,
                "violations_created": created_violations,
                "executive_summary": executive_summary,
                "representative_name": representative_name,
                "inspector_signed": bool(inspector_signature or current_user_display),
                "representative_signed": bool(representative_signature),
            },
            reason="إرسال كشف ميداني متكامل مع GPS والصور والملخص والنتيجة والإمضاء من شاشة /field/",
        )

        est_label = f"{getattr(establishment, 'code', '')} - {establishment.name_ar}".strip(" -")
        gps_label = f" | GPS: {gps_lat}, {gps_lng}" if gps_lat and gps_lng else ""
        photos_label = f" | الصور: {len(photo_names)}" if photo_names else ""
        messages.success(
            request,
            f"تم حفظ الكشف ({reference_code}) للمؤسسة [{est_label}]{gps_label}{photos_label} | النتيجة: {outcome} | الامتثال: {compliance_score}% | الخطورة: {risk_score}/100 ({risk_level}) | المخالفات: {created_violations}."
        )
        return redirect("/followups/")

    context = {
        "sectors": sectors,
        "grouped_sectors": _grouped_sectors(sectors),
        "selected_sector": selected_sector,
        "activities": activities,
        "selected_activity": selected_activity,
        "establishments": establishments,
        "governorates": governorates,
        "version": version,
        "sections_with_items": sections_with_items,
        "total_items_count": total_items_count,
        "critical_items_count": critical_items_count,
        "current_user_display": current_user_display,
        "now_display": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M"),
    }
    return render(request, "food_safety/field.html", context)


@login_required
def followups_view(request):
    if request.method == "POST":
        violation_id = request.POST.get("violation_id")
        new_status = request.POST.get("status", "").strip().upper()
        verification_note = request.POST.get("verification_note", "").strip()
        corrective_action = request.POST.get("corrective_action", "").strip()

        violation = get_object_or_404(ViolationRecord, pk=violation_id)
        old_status = violation.status
        old_note = getattr(violation, "verification_note", "")

        if new_status == "RESOLVED" and not verification_note:
            messages.error(
                request,
                "لا يمكن إغلاق المخالفة (RESOLVED) دون إدخال ملاحظة أو إثبات التحقق التصحيحي."
            )
            return redirect(request.get_full_path())

        before_state = {
            "status": old_status,
            "verification_note": old_note,
            "corrective_action": getattr(violation, "corrective_action", ""),
        }

        if new_status in {"OPEN", "IN_PROGRESS", "RESOLVED", "REFERRED"}:
            violation.status = new_status
        if corrective_action and hasattr(violation, "corrective_action"):
            violation.corrective_action = corrective_action
        if hasattr(violation, "verification_note") and verification_note:
            violation.verification_note = verification_note
        if new_status == "RESOLVED" and hasattr(violation, "closed_at"):
            violation.closed_at = timezone.now()

        violation.save()

        AuditLogEntry.objects.create(
            entity_type="ViolationRecord",
            entity_id=str(violation.pk),
            action="STATUS_UPDATE",
            actor=request.user,
            before_state=before_state,
            after_state={
                "status": violation.status,
                "verification_note": verification_note or old_note,
                "corrective_action": getattr(violation, "corrective_action", ""),
            },
            reason=verification_note or f"تحديث الحالة من {old_status} إلى {violation.status}",
        )

        messages.success(request, f"تم تحديث المخالفة #{violation.pk} وتسجيل العملية في سجل التدقيق.")
        return redirect(request.get_full_path())

    base_violations = _filtered_violations_queryset(request)
    all_vio_list = list(base_violations)

    severity_counts = {"CRITICAL": 0, "MAJOR": 0, "MODERATE": 0, "MINOR": 0}
    open_unclosed_total = 0
    resolved_total = 0

    est_buckets = defaultdict(lambda: {
        "key": "",
        "est_id": None,
        "name": "مؤسسة غير محددة",
        "code": "",
        "governorate": "",
        "total_count": 0,
        "unclosed_count": 0,
        "critical_count": 0,
        "resolved_count": 0,
        "violations": [],
    })

    for v in all_vio_list:
        sev = (getattr(v, "severity", "") or "").upper()
        st = (getattr(v, "status", "") or "").upper()
        if sev in severity_counts:
            severity_counts[sev] += 1

        is_closed = (st == "RESOLVED")
        if is_closed:
            resolved_total += 1
        else:
            open_unclosed_total += 1

        est = getattr(v, "establishment", None)
        if est is not None:
            bucket_key = f"est_{est.pk}"
            est_name = getattr(est, "name_ar", "") or str(est)
            est_code = getattr(est, "code", "") or ""
            est_gov = getattr(est, "governorate", "") or ""
            est_id = est.pk
        else:
            bucket_key = "est_none"
            est_name = "مؤسسة غير محددة"
            est_code = ""
            est_gov = ""
            est_id = None

        b = est_buckets[bucket_key]
        b["key"] = bucket_key
        b["est_id"] = est_id
        b["name"] = est_name
        b["code"] = est_code
        b["governorate"] = est_gov
        b["total_count"] += 1
        b["critical_count"] += 1 if sev == "CRITICAL" else 0
        if is_closed:
            b["resolved_count"] += 1
        else:
            b["unclosed_count"] += 1
        b["violations"].append(v)

    establishments_summary = sorted(
        est_buckets.values(),
        key=lambda x: (-x["unclosed_count"], -x["critical_count"], -x["total_count"], x["name"]),
    )

    selected_est_key = request.GET.get("est", "").strip()
    selected_establishment_group = None
    if selected_est_key:
        for grp in establishments_summary:
            if grp["key"] == selected_est_key:
                selected_establishment_group = grp
                break

    displayed_violations = (
        selected_establishment_group["violations"]
        if selected_establishment_group
        else all_vio_list
    )

    recent_audits = AuditLogEntry.objects.filter(entity_type="ViolationRecord")[:20]

    visit_fields = _model_field_names(InspectionVisit)
    recent_visits_qs = InspectionVisit.objects.all()
    if "establishment" in visit_fields:
        recent_visits_qs = recent_visits_qs.select_related("establishment")
    if "inspected_at" in visit_fields:
        recent_visits_qs = recent_visits_qs.order_by("-inspected_at", "-pk")
    else:
        recent_visits_qs = recent_visits_qs.order_by("-pk")
    recent_visits = recent_visits_qs[:10]

    context = {
        "violations": displayed_violations,
        "establishments_summary": establishments_summary,
        "selected_est_key": selected_est_key,
        "selected_establishment_group": selected_establishment_group,
        "severity_counts": severity_counts,
        "open_unclosed_total": open_unclosed_total,
        "resolved_total": resolved_total,
        "recent_audits": recent_audits,
        "recent_visits": recent_visits,
        "selected_severity": request.GET.get("severity", "").upper(),
        "selected_status": request.GET.get("status", "").upper(),
        "search_query": request.GET.get("q", ""),
    }
    return render(request, "food_safety/followups.html", context)


@login_required
def admin_dashboard_view(request):
    request.session["active_role"] = "admin"

    gov_filter = request.GET.get("governorate", "").strip()
    dist_filter = request.GET.get("district", "").strip()

    visit_fields = _model_field_names(InspectionVisit)
    visits_qs = InspectionVisit.objects.all()
    if "establishment" in visit_fields:
        visits_qs = visits_qs.select_related("establishment")
    if "inspected_at" in visit_fields:
        visits_qs = visits_qs.order_by("-inspected_at", "-pk")
    else:
        visits_qs = visits_qs.order_by("-pk")

    vio_fields = _model_field_names(ViolationRecord)
    vio_rel = [f for f in ("establishment", "visit") if f in vio_fields]
    violations_qs = ViolationRecord.objects.all()
    if vio_rel:
        violations_qs = violations_qs.select_related(*vio_rel)

    est_fields = _model_field_names(FoodEstablishment)
    est_by_id = {e.pk: e for e in FoodEstablishment.objects.all()}

    geo_stats = defaultdict(lambda: {
        "governorate": "غير محدد",
        "district": "غير محدد",
        "visits_count": 0,
        "violations_count": 0,
        "unclosed_count": 0,
        "critical_count": 0,
        "compliance_sum": 0.0,
        "compliance_n": 0,
        "lat": None,
        "lng": None,
    })

    visits_list = list(visits_qs)
    visit_by_id = {v.pk: v for v in visits_list}

    for vis in visits_list:
        est = getattr(vis, "establishment", None) or (
            est_by_id.get(getattr(vis, "establishment_id", None))
        )
        gov = ((getattr(est, "governorate", "") if est and "governorate" in est_fields else "") or "غير محدد").strip()
        dist = ((getattr(est, "district", "") if est and "district" in est_fields else "") or "غير محدد").strip()

        if gov_filter and gov != gov_filter:
            continue
        if dist_filter and dist != dist_filter:
            continue

        row = geo_stats[(gov, dist)]
        row["governorate"] = gov
        row["district"] = dist
        row["visits_count"] += 1

        comp = getattr(vis, "compliance_score", None)
        if comp is not None:
            try:
                row["compliance_sum"] += float(comp)
                row["compliance_n"] += 1
            except (TypeError, ValueError):
                pass

        v_lat = getattr(vis, "gps_lat", None) or getattr(vis, "latitude", None) or (getattr(est, "latitude", None) if est else None)
        v_lng = getattr(vis, "gps_lng", None) or getattr(vis, "longitude", None) or (getattr(est, "longitude", None) if est else None)
        try:
            if v_lat and v_lng:
                plat, plng = float(v_lat), float(v_lng)
                row["lat"] = row["lat"] or plat
                row["lng"] = row["lng"] or plng
        except (TypeError, ValueError):
            pass

    violations_list = list(violations_qs)
    severity_totals = {"CRITICAL": 0, "MAJOR": 0, "MODERATE": 0, "MINOR": 0}

    for v in violations_list:
        est = getattr(v, "establishment", None)
        if not est and getattr(v, "visit_id", None):
            parent_vis = visit_by_id.get(v.visit_id)
            est = getattr(parent_vis, "establishment", None) if parent_vis else None

        gov = ((getattr(est, "governorate", "") if est and "governorate" in est_fields else "") or "غير محدد").strip()
        dist = ((getattr(est, "district", "") if est and "district" in est_fields else "") or "غير محدد").strip()

        if gov_filter and gov != gov_filter:
            continue
        if dist_filter and dist != dist_filter:
            continue

        sev = (getattr(v, "severity", "") or "").upper()
        st = (getattr(v, "status", "") or "").upper()
        if sev in severity_totals:
            severity_totals[sev] += 1
        is_unclosed = (st != "RESOLVED")

        row = geo_stats[(gov, dist)]
        row["governorate"] = gov
        row["district"] = dist
        row["violations_count"] += 1
        if is_unclosed:
            row["unclosed_count"] += 1
        if sev == "CRITICAL":
            row["critical_count"] += 1

    geo_rows = []
    governorate_chart = defaultdict(lambda: {"visits": 0, "violations": 0, "unclosed": 0})
    map_points = []

    for (gov, dist), data in geo_stats.items():
        avg_comp = round(data["compliance_sum"] / data["compliance_n"], 1) if data["compliance_n"] > 0 else None
        fallback_coords = LEBANON_GOVERNORATE_COORDS.get(gov)
        lat = data["lat"] if data["lat"] is not None else (fallback_coords["lat"] if fallback_coords else None)
        lng = data["lng"] if data["lng"] is not None else (fallback_coords["lng"] if fallback_coords else None)

        geo_rows.append({
            "governorate": gov,
            "district": dist,
            "visits_count": data["visits_count"],
            "violations_count": data["violations_count"],
            "unclosed_count": data["unclosed_count"],
            "critical_count": data["critical_count"],
            "avg_compliance": avg_comp,
            "lat": lat,
            "lng": lng,
        })

        governorate_chart[gov]["visits"] += data["visits_count"]
        governorate_chart[gov]["violations"] += data["violations_count"]
        governorate_chart[gov]["unclosed"] += data["unclosed_count"]

        if lat is not None and lng is not None:
            map_points.append({
                "governorate": gov,
                "district": dist,
                "visits": data["visits_count"],
                "violations": data["violations_count"],
                "unclosed": data["unclosed_count"],
                "lat": lat,
                "lng": lng,
            })

    geo_rows.sort(key=lambda r: (-r["violations_count"], -r["visits_count"], r["governorate"], r["district"]))

    all_governorates = sorted({r["governorate"] for r in geo_rows} | set(LEBANON_GOVERNORATE_COORDS.keys()))
    all_districts = sorted({
        r["district"] for r in geo_rows
        if (not gov_filter or r["governorate"] == gov_filter) and r["district"] != "غير محدد"
    })

    gov_labels = sorted(governorate_chart.keys())
    chart_payload = {
        "gov_labels": gov_labels,
        "gov_visits": [governorate_chart[g]["visits"] for g in gov_labels],
        "gov_violations": [governorate_chart[g]["violations"] for g in gov_labels],
        "gov_unclosed": [governorate_chart[g]["unclosed"] for g in gov_labels],
        "severity_labels": ["CRITICAL", "MAJOR", "MODERATE", "MINOR"],
        "severity_values": [
            severity_totals["CRITICAL"],
            severity_totals["MAJOR"],
            severity_totals["MODERATE"],
            severity_totals["MINOR"],
        ],
        "map_points": map_points,
    }

    context = {
        "current_user_display": request.user.get_full_name() or request.user.get_username(),
        "now_display": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M"),
        "gov_filter": gov_filter,
        "dist_filter": dist_filter,
        "all_governorates": all_governorates,
        "all_districts": all_districts,
        "geo_rows": geo_rows,
        "total_filtered_visits": sum(r["visits_count"] for r in geo_rows),
        "total_filtered_violations": sum(r["violations_count"] for r in geo_rows),
        "total_filtered_unclosed": sum(r["unclosed_count"] for r in geo_rows),
        "severity_totals": severity_totals,
        "chart_payload_json": json.dumps(chart_payload, ensure_ascii=False),
        "recent_visits": visits_list[:8],
    }
    return render(request, "food_safety/admin_dashboard.html", context)


@login_required
def visit_detail_view(request, visit_id):
    visit_fields = _model_field_names(InspectionVisit)
    rel_fields = [f for f in ("establishment", "inspector", "template") if f in visit_fields]
    qs = InspectionVisit.objects.all()
    if rel_fields:
        qs = qs.select_related(*rel_fields)
    visit = get_object_or_404(qs, pk=visit_id)

    establishment = getattr(visit, "establishment", None)
    est_fields = _model_field_names(FoodEstablishment) if establishment else set()

    est_details = {
        "code": getattr(establishment, "code", "") if establishment else "",
        "name": (
            (getattr(establishment, "name_ar", "") or str(establishment))
            if establishment
            else "—"
        ),
        "governorate": getattr(establishment, "governorate", "") if "governorate" in est_fields else "",
        "district": getattr(establishment, "district", "") if "district" in est_fields else "",
        "address": (
            (getattr(establishment, "address_detail", "") or getattr(establishment, "address", ""))
            if establishment
            else ""
        ),
        "owner": (
            (getattr(establishment, "owner_name", "") or getattr(establishment, "manager_name", ""))
            if establishment
            else ""
        ),
        "phone": getattr(establishment, "phone", "") if "phone" in est_fields else "",
        "license": getattr(establishment, "license_number", "") if "license_number" in est_fields else "",
    }

    gps_lat = (
        getattr(visit, "gps_lat", "")
        or getattr(visit, "latitude", "")
        or (getattr(establishment, "latitude", "") if establishment else "")
    )
    gps_lng = (
        getattr(visit, "gps_lng", "")
        or getattr(visit, "longitude", "")
        or (getattr(establishment, "longitude", "") if establishment else "")
    )

    vio_fields = _model_field_names(ViolationRecord)
    violations_qs = ViolationRecord.objects.none()
    if "visit" in vio_fields:
        violations_qs = ViolationRecord.objects.filter(visit=visit)
        if "created_at" in vio_fields:
            violations_qs = violations_qs.order_by("-created_at")
        else:
            violations_qs = violations_qs.order_by("-pk")

    audit_entry = (
        AuditLogEntry.objects.filter(entity_type="InspectionVisit", entity_id=str(visit.pk))
        .order_by("-id")
        .first()
    )
    audit_state = audit_entry.after_state if (audit_entry and isinstance(audit_entry.after_state, dict)) else {}

    context = {
        "visit": visit,
        "est_details": est_details,
        "gps_lat": gps_lat,
        "gps_lng": gps_lng,
        "violations": violations_qs,
        "audit_entry": audit_entry,
        "audit_state": audit_state,
        "reference_code": getattr(visit, "reference_code", "") or f"VIS-{visit.pk}",
        "inspector_display": (
            getattr(visit, "inspector_name", "")
            or (str(getattr(visit, "inspector", "")) if getattr(visit, "inspector", None) else "—")
        ),
        "inspected_at": getattr(visit, "inspected_at", None) or getattr(visit, "created_at", None),
        "compliance_score": getattr(visit, "compliance_score", None) or audit_state.get("compliance_score"),
        "risk_score": getattr(visit, "risk_score", None) or audit_state.get("risk_score"),
        "summary_notes": getattr(visit, "summary_notes", "") or audit_state.get("executive_summary", ""),
        "inspector_signature": getattr(visit, "inspector_signature", ""),
        "representative_name": getattr(visit, "representative_name", "") or audit_state.get("representative_name", ""),
        "representative_signature": getattr(visit, "representative_signature", ""),
    }
    return render(request, "food_safety/visit_detail.html", context)


@login_required
def export_violations_csv(request):
    violations = _filtered_violations_queryset(request)

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="lsfa_violations_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "رقم المخالفة",
        "المؤسسة",
        "الخطورة",
        "الحالة",
        "الإجراء التصحيحي",
        "ملاحظة التحقق",
        "تاريخ الإنشاء",
    ])

    for v in violations:
        est = getattr(v, "establishment", None)
        est_name = getattr(est, "name_ar", "") or (str(est) if est else "")
        created = getattr(v, "created_at", None)
        writer.writerow([
            v.pk,
            est_name,
            getattr(v, "severity", ""),
            getattr(v, "status", ""),
            getattr(v, "corrective_action", ""),
            getattr(v, "verification_note", ""),
            created.strftime("%Y-%m-%d %H:%M") if created else "",
        ])

    return response