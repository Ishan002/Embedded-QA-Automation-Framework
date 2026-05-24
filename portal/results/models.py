import uuid
from django.db import models


class TestRun(models.Model):
    TRIGGERED_BY_CHOICES = [
        ("push", "Push"),
        ("pull_request", "Pull Request"),
        ("schedule", "Schedule"),
        ("manual", "Manual"),
    ]
    STATUS_CHOICES = [
        ("running", "Running"),
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("error", "Error"),
    ]

    run_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commit_sha = models.CharField(max_length=40)
    branch = models.CharField(max_length=255)
    pr_number = models.IntegerField(null=True, blank=True)
    triggered_by = models.CharField(max_length=20, choices=TRIGGERED_BY_CHOICES, default="push")
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="running")
    device_firmware = models.CharField(max_length=100, blank=True)
    total_tests = models.IntegerField(default=0)
    passed = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    duration_s = models.FloatField(default=0.0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.branch}@{self.commit_sha[:7]} ({self.status})"

    @property
    def pass_rate(self):
        if self.total_tests == 0:
            return 0.0
        return round(self.passed / self.total_tests * 100, 1)


class TestCase(models.Model):
    CATEGORY_CHOICES = [
        ("boot", "Boot"),
        ("sensor_io", "Sensor I/O"),
        ("data_integrity", "Data Integrity"),
        ("other", "Other"),
    ]

    module = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=512, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")

    class Meta:
        unique_together = [("module", "name")]

    def __str__(self):
        return self.full_name


class TestResult(models.Model):
    STATUS_CHOICES = [
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
        ("error", "Error"),
    ]

    run = models.ForeignKey(TestRun, related_name="results", on_delete=models.CASCADE)
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    duration_ms = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    stdout = models.TextField(blank=True)
    started_at = models.DateTimeField()

    class Meta:
        ordering = ["started_at"]

    def __str__(self):
        return f"{self.test_case.name} — {self.status}"
