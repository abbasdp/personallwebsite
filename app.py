"""عباس — وب‌سایت شخصی و فضای انتشار نوشته‌ها.

یک برنامه کوچک Flask که یک سایت شخصی فارسی (راست‌به‌چپ) را سرو می‌کند و
هسته اصلی آن، بخش «نوشته‌ها» است: مقاله‌ها به‌صورت فایل‌های Markdown در
``content/posts`` نگه‌داری می‌شوند و در زمان اجرا خوانده، تجزیه و رندر می‌شوند.
افزودن یک نوشته جدید یعنی افزودن یک فایل ``.md`` تازه — همین.
"""

from __future__ import annotations

import functools
import json
import os
import re
import secrets
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import jdatetime
import markdown as md
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Never hardcode secrets. Both are read from the environment; if missing, a random
# value is generated at startup so nothing sensitive is committed to the repo.
# Set SECRET_KEY and ADMIN_PASSWORD via environment/secret in any real deployment.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# Cache static assets (fonts, css, images) for a year — they are content-stable.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 365

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(18)
    app.logger.warning(
        "ADMIN_PASSWORD is not set — generated a random one for this run. "
        "Set the ADMIN_PASSWORD environment variable to log in to /admin."
    )

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "content" / "posts"
UPLOAD_DIR = BASE_DIR / "static" / "media" / "uploads"
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}

DEFAULT_PROFILE = {
    "name": "عباس داورپناه",
    "handle": "abbasdp",
    "role": "برنامه‌نویس و ترویج‌دهنده فلسفه نرم‌افزار آزاد",
    "location": "شیراز، ایران",
    "timezone": "Asia/Tehran",
    "tagline": "اینجا جای نوشتن و خواندن است: تجربه، فلسفه و فرهنگ نرم‌افزار آزاد.",
    "about": "برنامه‌نویس و علاقه‌مند به تکنولوژی و جنبش آزادی نرم‌افزار",
    "communities": [
        {"label": "فینگرکدر", "href": "https://fingercoder.abbasdp.ir/"},
        {"label": "شیرازلاگ", "href": "https://shirazlug.ir"},
        {"label": "sudoshz", "href": "https://sudoshz.ir"},
    ],
    "socials": [
        {"id": "mastodon", "label": "ماستودون", "value": "@abbas_dp@techhub.social",
         "href": "https://techhub.social/@abbas_dp", "icon": "mastodon"},
        {"id": "matrix", "label": "ماتریکس", "value": "@abbas_dp:matrix.org",
         "href": "https://matrix.to/#/@abbas_dp:matrix.org", "icon": "matrix"},
        {"id": "codeberg", "label": "کدبرگ", "value": "@abbasdp",
         "href": "https://codeberg.org/abbasdp", "icon": "codeberg"},
        {"id": "pixelfed", "label": "پیکسل‌فد", "value": "@davarpanah",
         "href": "https://pixelfed.social/davarpanah", "icon": "pixelfed"},
        {"id": "github", "label": "گیت‌هاب", "value": "@abbasdp",
         "href": "https://github.com/abbasdp", "icon": "github"},
        {"id": "email", "label": "ایمیل", "value": "abbasdp@proton.me",
         "href": "mailto:abbasdp@proton.me", "icon": "mail"},
    ],
    "funding": {
        "label": "از کارم حمایت کنید",
        "href": "https://payping.ir/@fingercoder",
        "handle": "@fingercoder",
    },
}

SITE_JSON = BASE_DIR / "content" / "site.json"


def load_profile() -> dict:
    """پروفایل سایت را از content/site.json می‌خواند و روی پیش‌فرض‌ها می‌نشاند."""
    data = json.loads(json.dumps(DEFAULT_PROFILE))  # deep copy
    if SITE_JSON.exists():
        try:
            data.update(json.loads(SITE_JSON.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            pass
    return data


def save_profile(data: dict) -> None:
    SITE_JSON.parent.mkdir(parents=True, exist_ok=True)
    SITE_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]
_DIGIT_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_digits(value) -> str:
    return str(value).translate(_DIGIT_MAP)


def jalali_date(gregorian: date) -> str:
    """تبدیل تاریخ میلادی به رشته شمسی فارسی، مثل «۲۸ شهریور ۱۴۰۵»."""
    j = jdatetime.date.fromgregorian(date=gregorian)
    return f"{to_persian_digits(j.day)} {PERSIAN_MONTHS[j.month - 1]} {to_persian_digits(j.year)}"


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """تجزیه یک بلوک ساده front-matter بین دو خط ``---`` در ابتدای فایل."""
    meta: dict = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            raw, body = parts[1], parts[2]
            for line in raw.strip().splitlines():
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()
    return meta, body.strip()


def _reading_time(body: str) -> str:
    words = len(re.findall(r"\S+", body))
    minutes = max(1, round(words / 200))
    return f"{to_persian_digits(minutes)} دقیقه مطالعه"


def _load_post(path: Path) -> dict:
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    try:
        gdate = datetime.strptime(meta.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        gdate = date.today()
    tags = [t.strip() for t in meta.get("tags", "").split("،") if t.strip()]
    if not tags:
        tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    html = md.markdown(body, extensions=["fenced_code", "tables", "toc"])
    return {
        "slug": path.stem,
        "title": meta.get("title", path.stem),
        "summary": meta.get("summary", ""),
        "tags": tags,
        "date": gdate,
        "date_fa": jalali_date(gdate),
        "reading_time": _reading_time(body),
        "cover": meta.get("cover", ""),
        "source": meta.get("source", ""),
        "html": html,
    }


def load_posts() -> list[dict]:
    if not POSTS_DIR.exists():
        return []
    posts = [_load_post(p) for p in POSTS_DIR.glob("*.md")]
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def read_post_raw(slug: str) -> dict | None:
    """خواندن فایل خام یک نوشته (front-matter + متن) برای فرم ویرایش."""
    path = POSTS_DIR / f"{slug}.md"
    if not path.exists():
        return None
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    return {
        "slug": slug,
        "title": meta.get("title", ""),
        "date": meta.get("date", ""),
        "summary": meta.get("summary", ""),
        "tags": meta.get("tags", ""),
        "cover": meta.get("cover", ""),
        "source": meta.get("source", ""),
        "body": body,
    }


def slugify(text: str) -> str:
    """ساخت نامک (slug) از عنوان؛ حروف فارسی/انگلیسی و عدد را نگه می‌دارد."""
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-z\u0600-\u06ff\-_]", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    return text or "post"


def unique_slug(base: str) -> str:
    slug, i = base, 2
    while (POSTS_DIR / f"{slug}.md").exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def save_post_file(slug, title, date_str, summary, tags, cover, body, source=""):
    """نوشتن نوشته به‌صورت فایل Markdown با همان قالب front-matter سایت."""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    front = ["---", f"title: {title}", f"date: {date_str}"]
    if summary:
        front.append(f"summary: {summary}")
    if tags:
        front.append(f"tags: {tags}")
    if cover:
        front.append(f"cover: {cover}")
    if source:
        front.append(f"source: {source}")
    front.append("---")
    (POSTS_DIR / f"{slug}.md").write_text(
        "\n".join(front) + "\n\n" + (body or "").strip() + "\n", encoding="utf-8"
    )


def _save_cover_upload(file_storage, slug: str) -> str | None:
    """ذخیره تصویر کاور آپلودشده و بازگرداندن مسیر عمومی آن."""
    if not file_storage or not file_storage.filename:
        return None
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return None
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe = secure_filename(f"{slug}{ext}") or f"cover{ext}"
    dest = UPLOAD_DIR / safe
    file_storage.save(dest)
    return f"/static/media/uploads/{safe}"


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    """در دسترس همه قالب‌ها: پایه آدرس canonical و تنظیمات Umami."""
    base = request.url_root[:-1] if request else ""
    return {
        "canonical_base": base,
        "umami_src": os.environ.get("UMAMI_SRC", ""),
        "umami_website_id": os.environ.get("UMAMI_WEBSITE_ID", ""),
    }


@app.route("/")
def index():
    posts = load_posts()
    profile = load_profile()
    seo = {"description": f"{profile['role']} — {profile['tagline']}", "type": "website"}
    return render_template(
        "index.html",
        profile=profile,
        posts=posts[:3],
        total_posts=len(posts),
        year=to_persian_digits(datetime.now().year),
        seo=seo,
    )


@app.route("/posts")
def posts_index():
    posts = load_posts()
    return render_template(
        "posts.html",
        profile=load_profile(),
        posts=posts,
        year=to_persian_digits(datetime.now().year),
        seo={"description": "یادداشت‌ها و مقاله‌ها درباره لینوکس، DevOps و نرم‌افزار آزاد."},
    )


@app.route("/posts/<slug>")
def post_detail(slug: str):
    path = POSTS_DIR / f"{slug}.md"
    if not path.exists():
        abort(404)
    post = _load_post(path)
    seo = {
        "description": post["summary"] or post["title"],
        "type": "article",
        "image": post["cover"] or "",
        "published": post["date"].isoformat(),
    }
    return render_template(
        "post.html",
        profile=load_profile(),
        post=post,
        year=to_persian_digits(datetime.now().year),
        seo=seo,
    )


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", profile=load_profile(), year=to_persian_digits(datetime.now().year)), 404


@app.route("/api/posts")
def api_posts():
    posts = load_posts()
    return jsonify([
        {k: v for k, v in p.items() if k != "html"} | {"date": p["date"].isoformat()}
        for p in posts
    ])


@app.route("/api/now")
def api_now():
    profile = load_profile()
    tz = ZoneInfo(profile["timezone"])
    now = datetime.now(tz)
    j = jdatetime.date.fromgregorian(date=now.date())
    return jsonify({
        "timezone": profile["timezone"],
        "iso": now.isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "date_fa": jalali_date(now.date()),
    })


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


# --------------------------- SEO endpoints ---------------------------

@app.route("/robots.txt")
def robots():
    base = request.url_root[:-1]
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    return app.response_class(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    base = request.url_root[:-1]
    posts = load_posts()
    urls = [
        {"loc": f"{base}/", "priority": "1.0"},
        {"loc": f"{base}/posts", "priority": "0.8"},
    ]
    for p in posts:
        urls.append({
            "loc": f"{base}/posts/{p['slug']}",
            "lastmod": p["date"].isoformat(),
            "priority": "0.7",
        })
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append("<url>")
        xml.append(f"<loc>{u['loc']}</loc>")
        if "lastmod" in u:
            xml.append(f"<lastmod>{u['lastmod']}</lastmod>")
        xml.append(f"<priority>{u['priority']}</priority>")
        xml.append("</url>")
    xml.append("</urlset>")
    return app.response_class("\n".join(xml), mimetype="application/xml")


def _rss_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


@app.route("/feed.xml")
def feed():
    base = request.url_root[:-1]
    profile = load_profile()
    posts = load_posts()
    items = []
    for p in posts:
        link = f"{base}/posts/{p['slug']}"
        pub = datetime(p["date"].year, p["date"].month, p["date"].day)
        items.append(
            "<item>"
            f"<title>{_rss_escape(p['title'])}</title>"
            f"<link>{link}</link>"
            f"<guid>{link}</guid>"
            f"<pubDate>{pub.strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>"
            f"<description>{_rss_escape(p['summary'])}</description>"
            "</item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        f"<title>{_rss_escape(profile['name'])} — نوشته‌ها</title>"
        f"<link>{base}/</link>"
        f"<description>{_rss_escape(profile['tagline'])}</description>"
        "<language>fa-IR</language>"
        + "".join(items)
        + "</channel></rss>"
    )
    return app.response_class(xml, mimetype="application/rss+xml")


# --------------------------- Admin panel ---------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            dest = request.args.get("next") or url_for("admin_dashboard")
            return redirect(dest)
        flash("رمز عبور نادرست است.", "error")
    return render_template("admin/login.html", profile=load_profile())


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    return render_template("admin/dashboard.html", profile=load_profile(), posts=load_posts())


@app.route("/admin/new", methods=["GET", "POST"])
@login_required
def admin_new():
    if request.method == "POST":
        return _handle_post_form(existing_slug=None)
    today = date.today().isoformat()
    return render_template(
        "admin/edit.html", profile=load_profile(), post=None, default_date=today
    )


@app.route("/admin/edit/<slug>", methods=["GET", "POST"])
@login_required
def admin_edit(slug):
    if request.method == "POST":
        return _handle_post_form(existing_slug=slug)
    post = read_post_raw(slug)
    if not post:
        abort(404)
    return render_template(
        "admin/edit.html", profile=load_profile(), post=post, default_date=post["date"]
    )


@app.route("/admin/delete/<slug>", methods=["POST"])
@login_required
def admin_delete(slug):
    path = POSTS_DIR / f"{slug}.md"
    if path.exists():
        path.unlink()
        flash("نوشته حذف شد.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/site", methods=["GET", "POST"])
@login_required
def admin_site():
    profile = load_profile()
    if request.method == "POST":
        for key in ("name", "handle", "role", "location", "tagline", "about"):
            profile[key] = (request.form.get(key) or "").strip()

        communities = []
        for label, href in zip(
            request.form.getlist("community_label"),
            request.form.getlist("community_href"),
        ):
            if label.strip():
                communities.append({"label": label.strip(), "href": href.strip()})
        profile["communities"] = communities

        socials = []
        for icon, label, value, href in zip(
            request.form.getlist("social_icon"),
            request.form.getlist("social_label"),
            request.form.getlist("social_value"),
            request.form.getlist("social_href"),
        ):
            if not label.strip():
                continue
            icon = (icon or "link").strip()
            socials.append({
                "id": icon,
                "icon": icon,
                "label": label.strip(),
                "value": value.strip(),
                "href": href.strip(),
            })
        profile["socials"] = socials

        save_profile(profile)
        flash("محتوای سایت ذخیره شد.", "success")
        return redirect(url_for("admin_site"))

    icon_options = ["mastodon", "matrix", "github", "codeberg", "pixelfed", "mail", "link"]
    return render_template("admin/site.html", profile=profile, icon_options=icon_options)


def _handle_post_form(existing_slug):
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("عنوان الزامی است.", "error")
        return redirect(request.url)

    date_str = (request.form.get("date") or date.today().isoformat()).strip()
    summary = (request.form.get("summary") or "").strip()
    tags = (request.form.get("tags") or "").strip()
    body = request.form.get("body") or ""
    source = (request.form.get("source") or "").strip()

    if existing_slug:
        slug = existing_slug
        existing = read_post_raw(slug) or {}
        cover = existing.get("cover", "")
    else:
        slug = slugify(request.form.get("slug") or title)
        slug = unique_slug(slug)
        cover = ""

    uploaded = _save_cover_upload(request.files.get("cover_file"), slug)
    if uploaded:
        cover = uploaded
    cover_url = (request.form.get("cover_url") or "").strip()
    if cover_url:
        cover = cover_url

    save_post_file(slug, title, date_str, summary, tags, cover, body, source)
    flash("نوشته ذخیره شد.", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
