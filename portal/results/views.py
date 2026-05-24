import json
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView, DetailView

from .models import TestRun, TestCase, TestResult


class DashboardView(TemplateView):
    template_name = "results/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        runs = list(TestRun.objects.order_by("-started_at")[:30])

        trend_labels = [str(r.commit_sha[:7]) for r in reversed(runs)]
        trend_pass_rates = [r.pass_rate for r in reversed(runs)]

        recent_failures = TestResult.objects.filter(
            status="failed",
            run__in=runs[:5],
        ).select_related("test_case", "run").order_by("-run__started_at")[:20]

        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_runs = TestRun.objects.filter(started_at__gte=seven_days_ago)
        total_recent = recent_runs.count()
        passed_recent = recent_runs.filter(status="passed").count()
        pass_rate_7d = round(passed_recent / total_recent * 100, 1) if total_recent else 0.0

        ctx.update({
            "runs": runs,
            "total_runs": TestRun.objects.count(),
            "pass_rate_7d": pass_rate_7d,
            "trend_labels": json.dumps(trend_labels),
            "trend_pass_rates": json.dumps(trend_pass_rates),
            "recent_failures": recent_failures,
        })
        return ctx


class TrendsView(TemplateView):
    template_name = "results/trends.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        since = timezone.now() - timedelta(days=14)
        results = TestResult.objects.filter(run__started_at__gte=since).select_related("run", "test_case")

        daily = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0})
        by_category = defaultdict(lambda: {"passed": 0, "failed": 0})

        for r in results:
            day = r.run.started_at.strftime("%Y-%m-%d")
            daily[day][r.status] += 1
            by_category[r.test_case.category][r.status if r.status in ("passed", "failed") else "failed"] += 1

        sorted_days = sorted(daily.keys())
        ctx.update({
            "trend_days": json.dumps(sorted_days),
            "trend_passed": json.dumps([daily[d]["passed"] for d in sorted_days]),
            "trend_failed": json.dumps([daily[d]["failed"] for d in sorted_days]),
            "trend_skipped": json.dumps([daily[d]["skipped"] for d in sorted_days]),
            "by_category": dict(by_category),
        })
        return ctx


class RegressionView(TemplateView):
    template_name = "results/regression.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        runs = list(TestRun.objects.order_by("-started_at")[:2])

        regressions = []
        if len(runs) >= 2:
            latest_run, prev_run = runs[0], runs[1]
            latest_failed = set(
                TestResult.objects.filter(run=latest_run, status="failed")
                .values_list("test_case_id", flat=True)
            )
            prev_passed = set(
                TestResult.objects.filter(run=prev_run, status="passed")
                .values_list("test_case_id", flat=True)
            )
            regressed_ids = latest_failed & prev_passed
            regressions = TestCase.objects.filter(id__in=regressed_ids)

        ctx.update({
            "regressions": regressions,
            "regression_count": len(regressions),
        })
        return ctx


class RunDetailView(DetailView):
    model = TestRun
    template_name = "results/run_detail.html"
    pk_url_kwarg = "run_id"
    context_object_name = "run"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["results"] = self.object.results.select_related("test_case").order_by("started_at")
        return ctx
