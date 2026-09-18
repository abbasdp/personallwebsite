from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

from journal.views import health

admin.site.site_header = "میز کار — عباس داورپناه"
admin.site.site_title = "میز کار"
admin.site.index_title = "نوشته‌ها و تنظیمات"

urlpatterns = [
    path("health", health),
    path("admin/", admin.site.urls),
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    path("", include("journal.urls")),
]
