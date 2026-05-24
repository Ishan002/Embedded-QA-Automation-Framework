from django.urls import path
from . import api

urlpatterns = [
    path("runs/", api.RunListCreateView.as_view(), name="api_runs"),
    path("runs/<uuid:run_id>/", api.RunDetailView.as_view(), name="api_run_detail"),
    path("runs/<uuid:run_id>/results/", api.BulkResultsView.as_view(), name="api_bulk_results"),
    path("runs/<uuid:run_id>/complete/", api.CompleteRunView.as_view(), name="api_complete_run"),
]
