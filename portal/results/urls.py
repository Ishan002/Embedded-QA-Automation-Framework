from django.urls import path
from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("trends/", views.TrendsView.as_view(), name="trends"),
    path("regressions/", views.RegressionView.as_view(), name="regressions"),
    path("runs/<uuid:run_id>/", views.RunDetailView.as_view(), name="run_detail"),
]
