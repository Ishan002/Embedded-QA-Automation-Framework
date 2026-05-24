from django.contrib import admin
from .models import TestRun, TestCase, TestResult


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ["run_id", "branch", "commit_sha", "status", "pass_rate", "total_tests", "started_at"]
    list_filter = ["status", "triggered_by", "branch"]
    search_fields = ["commit_sha", "branch"]
    readonly_fields = ["run_id", "pass_rate"]


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ["full_name", "module", "category"]
    list_filter = ["category"]
    search_fields = ["name", "module"]


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ["test_case", "run", "status", "duration_ms", "started_at"]
    list_filter = ["status", "test_case__category"]
    search_fields = ["test_case__name"]
