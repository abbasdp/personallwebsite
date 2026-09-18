import jdatetime
from django import template
from django.utils import timezone

register = template.Library()

_MONTHS = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)


def _fa_digits(value: str) -> str:
    table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return value.translate(table)


@register.filter
def jalali(dt):
    if not dt:
        return ""
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    j = jdatetime.datetime.fromgregorian(datetime=dt)
    return _fa_digits(f"{j.day} {_MONTHS[j.month - 1]} {j.year}")
