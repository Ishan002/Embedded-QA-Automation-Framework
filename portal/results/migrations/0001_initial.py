import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TestCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=255)),
                ("full_name", models.CharField(max_length=512, unique=True)),
                ("category", models.CharField(
                    choices=[("boot", "Boot"), ("sensor_io", "Sensor I/O"), ("data_integrity", "Data Integrity"), ("other", "Other")],
                    default="other", max_length=20,
                )),
            ],
            options={"unique_together": {("module", "name")}},
        ),
        migrations.CreateModel(
            name="TestRun",
            fields=[
                ("run_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("commit_sha", models.CharField(max_length=40)),
                ("branch", models.CharField(max_length=255)),
                ("pr_number", models.IntegerField(blank=True, null=True)),
                ("triggered_by", models.CharField(
                    choices=[("push", "Push"), ("pull_request", "Pull Request"), ("schedule", "Schedule"), ("manual", "Manual")],
                    default="push", max_length=20,
                )),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[("running", "Running"), ("passed", "Passed"), ("failed", "Failed"), ("error", "Error")],
                    default="running", max_length=10,
                )),
                ("device_firmware", models.CharField(blank=True, max_length=100)),
                ("total_tests", models.IntegerField(default=0)),
                ("passed", models.IntegerField(default=0)),
                ("failed", models.IntegerField(default=0)),
                ("skipped", models.IntegerField(default=0)),
                ("duration_s", models.FloatField(default=0.0)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="TestResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="results.testrun")),
                ("test_case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="results.testcase")),
                ("status", models.CharField(
                    choices=[("passed", "Passed"), ("failed", "Failed"), ("skipped", "Skipped"), ("error", "Error")],
                    max_length=10,
                )),
                ("duration_ms", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("stdout", models.TextField(blank=True)),
                ("started_at", models.DateTimeField()),
            ],
            options={"ordering": ["started_at"]},
        ),
    ]
