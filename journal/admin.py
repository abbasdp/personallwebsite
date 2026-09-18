from django import forms
from django.contrib import admin

from .models import Post, SiteSettings, Tag


class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = "__all__"
        widgets = {
            "excerpt": forms.Textarea(attrs={"rows": 3}),
            "body": forms.Textarea(attrs={"rows": 28, "dir": "rtl", "style": "font-family: Vazirmatn, Tahoma, sans-serif; font-size: 15px;"}),
        }


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ("title", "published", "featured", "published_at")
    list_filter = ("published", "featured", "tags")
    search_fields = ("title", "excerpt", "body")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"
    fieldsets = (
        (None, {"fields": ("title", "slug", "excerpt", "body")}),
        ("تصویر", {"fields": ("cover", "cover_alt", "cover_caption")}),
        ("انتشار", {"fields": ("tags", "published", "featured", "published_at")}),
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
