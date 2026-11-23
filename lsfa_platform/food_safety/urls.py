from django.contrib import admin
from django.urls import path
from food_safety import views as fs_views

urlpatterns = [
    path("", fs_views.home_view, name="home"),
    path("admin/", admin.site.urls),
    path("login/", fs_views.inspector_login, name="inspector_login"),
    path("logout/", fs_views.inspector_logout, name="inspector_logout"),
    path("field/", fs_views.field_inspection_view, name="field_inspection"),
    path("followups/", fs_views.followups_view, name="followups"),
    path("followups/export/csv/", fs_views.export_violations_csv, name="export_violations_csv"),
    path("visits/<int:visit_id>/", fs_views.visit_detail_view, name="visit_detail"),
    path("admin-dashboard/", fs_views.admin_dashboard_view, name="admin_dashboard"),
]