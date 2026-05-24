from datetime import datetime
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TestRun, TestCase, TestResult
from .serializers import TestRunSerializer, BulkResultItemSerializer


class RunListCreateView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        runs = TestRun.objects.all()[:50]
        serializer = TestRunSerializer(runs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TestRunSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        run = serializer.save()
        return Response(TestRunSerializer(run).data, status=status.HTTP_201_CREATED)


class RunDetailView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, run_id):
        try:
            run = TestRun.objects.get(pk=run_id)
        except TestRun.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(TestRunSerializer(run).data)


class BulkResultsView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request, run_id):
        try:
            run = TestRun.objects.get(pk=run_id)
        except TestRun.DoesNotExist:
            return Response({"error": "Run not found"}, status=status.HTTP_404_NOT_FOUND)

        items = request.data if isinstance(request.data, list) else [request.data]
        serializer = BulkResultItemSerializer(data=items, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        for item in serializer.validated_data:
            full_name = f"{item['module']}::{item['test_name']}"
            test_case, _ = TestCase.objects.get_or_create(
                module=item["module"],
                name=item["test_name"],
                defaults={"full_name": full_name, "category": item.get("category", "other")},
            )
            TestResult.objects.create(
                run=run,
                test_case=test_case,
                status=item["status"],
                duration_ms=item.get("duration_ms", 0),
                error_message=item.get("error_message", ""),
                stdout=item.get("stdout", ""),
                started_at=item["started_at"],
            )
            created += 1

        passed = sum(1 for i in serializer.validated_data if i["status"] == "passed")
        failed = sum(1 for i in serializer.validated_data if i["status"] == "failed")
        skipped = sum(1 for i in serializer.validated_data if i["status"] == "skipped")
        run.total_tests += created
        run.passed += passed
        run.failed += failed
        run.skipped += skipped
        run.save(update_fields=["total_tests", "passed", "failed", "skipped"])

        return Response({"created": created}, status=status.HTTP_201_CREATED)


class CompleteRunView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def patch(self, request, run_id):
        try:
            run = TestRun.objects.get(pk=run_id)
        except TestRun.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        run.status = request.data.get("status", "passed")
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "completed_at"])
        return Response(TestRunSerializer(run).data)
