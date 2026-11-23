from rest_framework import serializers
from .models import (
    AuditAxis,
    AuditQuestion,
    CitizenComplaint,
    CorrectiveActionCAPA,
    FoodEstablishment,
    InspectionAnswer,
    InspectionTemplate,
    InspectionVisit,
    LabSample,
    ProductBatchRecall,
    ReferralTarget,
    RegulatoryReferral,
    ReinspectionSchedule,
    ViolationEvidence,
    ViolationRecord,
)
from .scoring_engine import process_inspection_visit


class AuditQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditQuestion
        fields = [
            "id",
            "axis",
            "code",
            "text_ar",
            "text_en",
            "verification_criteria_ar",
            "verification_criteria_en",
            "proof_method",
            "weight",
            "severity",
            "can_be_not_applicable",
            "sort_order",
            "is_active",
        ]


class AuditAxisSerializer(serializers.ModelSerializer):
    questions = AuditQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = AuditAxis
        fields = [
            "id",
            "code",
            "title_ar",
            "title_en",
            "standard_clause",
            "sort_order",
            "is_active",
            "questions",
        ]


class InspectionTemplateSerializer(serializers.ModelSerializer):
    axes = AuditAxisSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionTemplate
        fields = [
            "id",
            "form_code",
            "title_ar",
            "title_en",
            "version",
            "standards_reference",
            "critical_limits_summary",
            "allow_not_applicable",
            "require_na_justification",
            "max_na_ratio_pct",
            "is_active",
            "axes",
        ]


class FoodEstablishmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodEstablishment
        fields = "__all__"


class InspectionAnswerSerializer(serializers.ModelSerializer):
    question_code = serializers.CharField(source="question.code", read_only=True)

    class Meta:
        model = InspectionAnswer
        fields = [
            "id",
            "question",
            "question_code",
            "choice",
            "justification",
            "measured_value",
            "earned_points",
            "max_applicable_points",
        ]


class ViolationEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViolationEvidence
        fields = "__all__"


class CorrectiveActionCAPASerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveActionCAPA
        fields = "__all__"


class ViolationRecordSerializer(serializers.ModelSerializer):
    evidences = ViolationEvidenceSerializer(many=True, read_only=True)
    capa = CorrectiveActionCAPASerializer(read_only=True)

    class Meta:
        model = ViolationRecord
        fields = [
            "id",
            "code",
            "visit",
            "question",
            "severity",
            "description_ar",
            "description_en",
            "status",
            "due_date",
            "created_at",
            "evidences",
            "capa",
        ]


class RegulatoryReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulatoryReferral
        fields = "__all__"


class ReinspectionScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReinspectionSchedule
        fields = "__all__"


class LabSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabSample
        fields = "__all__"


class CitizenComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = CitizenComplaint
        fields = "__all__"


class ProductBatchRecallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductBatchRecall
        fields = "__all__"


class InspectionVisitSerializer(serializers.ModelSerializer):
    answers = InspectionAnswerSerializer(many=True, read_only=True)
    violations = ViolationRecordSerializer(many=True, read_only=True)
    referrals = RegulatoryReferralSerializer(many=True, read_only=True)
    reinspection_schedules = ReinspectionScheduleSerializer(many=True, read_only=True)
    samples = LabSampleSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionVisit
        fields = [
            "id",
            "reference_code",
            "establishment",
            "template",
            "inspector_name",
            "inspector_ministry",
            "parent_visit",
            "inspection_datetime",
            "status",
            "gps_latitude",
            "gps_longitude",
            "gps_accuracy_m",
            "compliance_score_pct",
            "excluded_na_pct",
            "critical_violations_count",
            "has_critical_failure",
            "risk_level",
            "sync_status",
            "offline_uuid",
            "synced_at",
            "general_notes",
            "party_representative",
            "party_acknowledged",
            "answers",
            "violations",
            "referrals",
            "reinspection_schedules",
            "samples",
        ]


class AnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choice = serializers.CharField()
    justification = serializers.CharField(required=False, allow_blank=True, default="")
    measured_value = serializers.CharField(required=False, allow_blank=True, default="")


class InspectionVisitCreateSerializer(serializers.ModelSerializer):
    answers = AnswerInputSerializer(many=True, write_only=True)

    class Meta:
        model = InspectionVisit
        fields = [
            "id",
            "reference_code",
            "establishment",
            "template",
            "inspector_name",
            "inspector_ministry",
            "parent_visit",
            "status",
            "gps_latitude",
            "gps_longitude",
            "gps_accuracy_m",
            "general_notes",
            "party_representative",
            "party_acknowledged",
            "answers",
        ]

    def create(self, validated_data):
        answers_data = validated_data.pop("answers", [])
        visit = InspectionVisit.objects.create(**validated_data)
        process_inspection_visit(visit=visit, answers_payload=answers_data)
        return visit