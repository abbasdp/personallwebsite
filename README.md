# abbasdp.ir

سایت شخصی عباس داورپناه. جنگو، پنل مدیریت آنلاین، فرانت راست‌چین.

## اجرا روی همین ماشین

```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev
python manage.py migrate
python manage.py import_seed
python manage.py createsuperuser
python manage.py runserver
```

- سایت: http://127.0.0.1:8000/
- میز کار: http://127.0.0.1:8000/admin/

## استقرار Paasta

`paasta deploy . -n abbasdp` سپس متغیرهای `DJANGO_SECRET_KEY` و `DJANGO_SUPERUSER_*` و یک volume روی `/data`.
