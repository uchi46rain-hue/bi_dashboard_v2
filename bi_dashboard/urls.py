from analytics.views import dashboard, download_csv_template
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", dashboard, name="dashboard"),
    path(
        "dashboard/download-template/",
        download_csv_template,
        name="download_csv_template",
    ),
]