from django.contrib import admin
from django.urls import path, include

admin.site.site_header = "الهيئة اللبنانية لسلامة الغذاء (LSFA)"
admin.site.site_title = "المنصة الوطنية الرقمية لسلامة الغذاء"
admin.site.index_title = "لوحة القيادة والإدارة المركزية"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("food_safety.urls")),
]
