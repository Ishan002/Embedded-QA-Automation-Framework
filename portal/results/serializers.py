from rest_framework import serializers
from .models import TestRun, TestCase, TestResult


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ["id", "module", "name", "full_name", "category"]


class TestResultSerializer(serializers.ModelSerializer):
    test_case = TestCaseSerializer(read_only=True)

    class Meta:
        model = TestResult
        fields = ["id", "test_case", "status", "duration_ms", "error_message", "started_at"]


class TestRunSerializer(serializers.ModelSerializer):
    pass_rate = serializers.ReadOnlyField()

    class Meta:
        model = TestRun
        fields = [
            "run_id", "commit_sha", "branch", "pr_number", "triggered_by",
            "started_at", "completed_at", "status", "device_firmware",
            "total_tests", "passed", "failed", "skipped", "duration_s", "pass_rate",
        ]


class BulkResultItemSerializer(serializers.Serializer):
    test_name = serializers.CharField(max_length=255)
    module = serializers.CharField(max_length=255)
    category = serializers.ChoiceField(
        choices=["boot", "sensor_io", "data_integrity", "other"],
        default="other",
    )
    status = serializers.ChoiceField(choices=["passed", "failed", "skipped", "error"])
    duration_ms = serializers.IntegerField(default=0)
    error_message = serializers.CharField(allow_blank=True, default="")
    stdout = serializers.CharField(allow_blank=True, default="")
    started_at = serializers.DateTimeField()
