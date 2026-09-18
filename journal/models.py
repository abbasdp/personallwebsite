from django.db import models
from django.urls import reverse


class Tag(models.Model):
    name = models.CharField("نام", max_length=80)
    slug = models.SlugField("نامک", unique=True, allow_unicode=True)

    class Meta:
        verbose_name = "برچسب"
        verbose_name_plural = "برچسب‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tag", args=[self.slug])


class Post(models.Model):
    title = models.CharField("عنوان", max_length=200)
    slug = models.SlugField("نامک", unique=True, allow_unicode=True, max_length=200)
    excerpt = models.TextField("خلاصه", blank=True)
    body = models.TextField("متن HTML")
    cover = models.ImageField("تصویر شاخص", upload_to="covers/", blank=True)
    cover_alt = models.CharField("متن جایگزین تصویر", max_length=250, blank=True)
    cover_caption = models.CharField("شرح تصویر", max_length=250, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="برچسب‌ها")
    published = models.BooleanField("منتشر شده", default=False)
    featured = models.BooleanField("برگزیده", default=False)
    published_at = models.DateTimeField("تاریخ انتشار")
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "نوشته"
        verbose_name_plural = "نوشته‌ها"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("post", args=[self.slug])


class SiteSettings(models.Model):
    name = models.CharField("نام", max_length=80, default="عباس داورپناه")
    kicker = models.CharField(
        "خط بالا", max_length=120, default="ترویج فلسفه نرم‌افزار آزاد"
    )
    intro = models.TextField(
        "معرفی",
        default=(
            "برگزارکننده و نویسنده. از شیرازلاگ و فینگرکدر تا گفتگو با کسانی که "
            "آزادی کاربر را جدی می‌گیرند — متن‌ها از دل کار جمعی می‌آیند، نه از روی کاتالوگ ابزار."
        ),
    )
    mastodon = models.URLField(blank=True, default="https://techhub.social/@abbas_dp")
    pixelfed = models.URLField(blank=True, default="https://pixelfed.social/davarpanah")
    codeberg = models.URLField(blank=True, default="https://codeberg.org/abbasdp")
    matrix = models.URLField(blank=True, default="https://matrix.to/#/@abbas_dp:matrix.org")
    gnu_url = models.URLField(
        blank=True, default="https://www.gnu.org/philosophy/free-sw.fa.html"
    )
    shirazlinux = models.URLField(blank=True, default="https://sudoshz.ir")

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
