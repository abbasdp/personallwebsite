"""عباس — وب‌سایت شخصی و فضای انتشار نوشته‌ها.

یک برنامه کوچک Flask که یک سایت شخصی فارسی (راست‌به‌چپ) را سرو می‌کند و
هسته اصلی آن، بخش «نوشته‌ها» است: مقاله‌ها به‌صورت فایل‌های Markdown در
``content/posts`` نگه‌داری می‌شوند و در زمان اجرا خوانده، تجزیه و رندر می‌شوند.
افزودن یک نوشته جدید یعنی افزودن یک فایل ``.md`` تازه — همین.
"""

from __future__ import annotations

import functools
import html as html_lib
import json
import os
import re
import secrets
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
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
    send_file,
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
PGP_ASC = BASE_DIR / "static" / "abbasdp.asc"
PGP_FINGERPRINT = "35A4 5081 4284 D496 F578  7C54 3ADE 104D A1AF BF4E"


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


def body_looks_like_html(body: str) -> bool:
    snippet = (body or "").lstrip()[:4000]
    return snippet.startswith("<") and "</" in snippet


def parse_editor_data(body: str) -> dict | None:
    text = (body or "").strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if isinstance(data, dict) and isinstance(data.get("blocks"), list):
        return data
    return None


def editor_data_to_html(data: dict) -> str:
    parts: list[str] = []
    for block in data.get("blocks") or []:
        kind = block.get("type")
        payload = block.get("data") or {}
        if kind == "paragraph":
            parts.append(f"<p>{payload.get('text') or ''}</p>")
        elif kind == "header":
            level = payload.get("level") or 2
            try:
                level = min(max(int(level), 2), 4)
            except (TypeError, ValueError):
                level = 2
            parts.append(f"<h{level}>{payload.get('text') or ''}</h{level}>")
        elif kind == "list":
            tag = "ol" if payload.get("style") == "ordered" else "ul"
            items = []
            for item in payload.get("items") or []:
                if isinstance(item, dict):
                    items.append(f"<li>{item.get('content') or ''}</li>")
                else:
                    items.append(f"<li>{item}</li>")
            parts.append(f"<{tag}>{''.join(items)}</{tag}>")
        elif kind == "quote":
            caption = payload.get("caption") or ""
            quote = payload.get("text") or ""
            cap = f"<cite>{caption}</cite>" if caption else ""
            parts.append(f"<blockquote><p>{quote}</p>{cap}</blockquote>")
        elif kind == "delimiter":
            parts.append("<hr>")
        elif kind == "image":
            url = (payload.get("file") or {}).get("url") or payload.get("url") or ""
            cap = payload.get("caption") or ""
            if not url:
                continue
            img = f'<img src="{html_lib.escape(url, quote=True)}" alt="">'
            if cap:
                parts.append(f"<figure>{img}<figcaption>{cap}</figcaption></figure>")
            else:
                parts.append(img)
        elif kind == "code":
            code = html_lib.escape(payload.get("code") or "")
            parts.append(f"<pre><code>{code}</code></pre>")
    return "\n".join(parts)


class _BlockParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self._tag = ""
        self._buf: list[str] = []
        self._list_items: list[str] = []
        self._list_style = "unordered"

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"p", "h1", "h2", "h3", "h4", "blockquote", "pre"}:
            self._flush()
            self._tag = tag
            self._buf = []
        elif tag in {"ul", "ol"}:
            self._flush()
            self._tag = tag
            self._list_items = []
            self._list_style = "ordered" if tag == "ol" else "unordered"
        elif tag == "li":
            self._buf = []
        elif tag == "br" and self._tag:
            self._buf.append("<br>")
        elif tag == "img":
            src = attrs.get("src") or ""
            if src:
                self.blocks.append({
                    "type": "image",
                    "data": {"file": {"url": src}, "caption": attrs.get("alt") or ""},
                })
        elif tag == "hr":
            self._flush()
            self.blocks.append({"type": "delimiter", "data": {}})
        elif tag in {"strong", "b"}:
            self._buf.append("<b>")
        elif tag in {"em", "i"}:
            self._buf.append("<i>")
        elif tag == "a":
            href = html_lib.escape(attrs.get("href") or "", quote=True)
            self._buf.append(f'<a href="{href}">')

    def handle_endtag(self, tag):
        if tag in {"strong", "b"}:
            self._buf.append("</b>")
        elif tag in {"em", "i"}:
            self._buf.append("</i>")
        elif tag == "a":
            self._buf.append("</a>")
        elif tag == "li":
            self._list_items.append("".join(self._buf).strip())
            self._buf = []
        elif tag in {"ul", "ol"}:
            self.blocks.append({
                "type": "list",
                "data": {"style": self._list_style, "items": self._list_items},
            })
            self._tag = ""
            self._list_items = []
        elif tag == self._tag:
            text = "".join(self._buf).strip()
            if tag == "p" and text:
                self.blocks.append({"type": "paragraph", "data": {"text": text}})
            elif tag in {"h1", "h2", "h3", "h4"} and text:
                level = int(tag[1])
                self.blocks.append({"type": "header", "data": {"text": text, "level": min(max(level, 2), 3)}})
            elif tag == "blockquote" and text:
                self.blocks.append({"type": "quote", "data": {"text": text, "caption": ""}})
            elif tag == "pre" and text:
                self.blocks.append({"type": "code", "data": {"code": text}})
            self._tag = ""
            self._buf = []

    def handle_data(self, data):
        if self._tag:
            self._buf.append(data)

    def _flush(self):
        if self._tag in {"p", "h1", "h2", "h3", "h4", "blockquote", "pre"}:
            self.handle_endtag(self._tag)

    def close(self):
        self._flush()
        super().close()


def html_to_editor_data(html: str) -> dict:
    parser = _BlockParser()
    parser.feed(html or "")
    parser.close()
    blocks = parser.blocks or [{"type": "paragraph", "data": {"text": ""}}]
    return {"time": 0, "blocks": blocks, "version": "2.30.7"}


def body_to_editor_data(body: str) -> dict:
    data = parse_editor_data(body)
    if data:
        return data
    html = render_body(body)
    return html_to_editor_data(html)


def render_body(body: str) -> str:
    """بدنه را به HTML تبدیل می‌کند (JSON بلاک‌ادیتور، HTML، یا Markdown)."""
    data = parse_editor_data(body)
    if data:
        return editor_data_to_html(data)
    if body_looks_like_html(body):
        return body
    return md.markdown(body or "", extensions=["fenced_code", "tables", "toc"])


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
    html = render_body(body)
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


def _umami_settings() -> tuple[str, str]:
    """شناسه سایت Umami و میزبان API. اسکریپت ردیاب از خود سایت سرو می‌شود."""
    website_id = (os.environ.get("UMAMI_WEBSITE_ID") or "").strip()
    if website_id in ("", "-"):
        return "", ""
    host = (os.environ.get("UMAMI_HOST") or "").strip()
    src = (os.environ.get("UMAMI_SRC") or "").strip()
    if not host and src not in ("", "-"):
        parts = urlsplit(src)
        if parts.scheme and parts.netloc:
            host = f"{parts.scheme}://{parts.netloc}"
    if not host:
        host = "https://umami.sudoshz.ir"
    return website_id, host


@app.context_processor
def inject_globals():
    """در دسترس همه قالب‌ها: پایه آدرس canonical، ساعت، و تنظیمات Umami."""
    base = request.url_root[:-1] if request else ""
    website_id, host = _umami_settings()
    pgp_pubkey = ""
    if PGP_ASC.exists():
        pgp_pubkey = PGP_ASC.read_text(encoding="utf-8").strip()
    return {
        "canonical_base": base,
        "umami_website_id": website_id,
        "umami_host": host,
        "clock_time": datetime.now(ZoneInfo("Asia/Tehran")).strftime("%H:%M:%S"),
        "pgp_pubkey": pgp_pubkey,
        "pgp_fingerprint": PGP_FINGERPRINT,
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


@app.route("/abbasdp.asc")
def pgp_key():
    if not PGP_ASC.exists():
        abort(404)
    return send_file(
        PGP_ASC,
        mimetype="application/pgp-keys",
        as_attachment=False,
        download_name="abbasdp.asc",
    )


@app.route("/javascript")
def javascript_licenses():
    """جدول برچسب مجوز جاوااسکریپت برای GNU LibreJS."""
    profile = load_profile()
    return render_template(
        "javascript.html",
        profile=profile,
        year=to_persian_digits(datetime.now().year),
        seo={"description": "مجوز و نشانی منبع جاوااسکریپت این سایت برای GNU LibreJS."},
    )


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
        {"loc": f"{base}/javascript", "priority": "0.3"},
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
        "admin/edit.html",
        profile=load_profile(),
        post=None,
        default_date=today,
        editor_data=body_to_editor_data(""),
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
        "admin/edit.html",
        profile=load_profile(),
        post=post,
        default_date=post["date"],
        editor_data=body_to_editor_data(post.get("body") or ""),
    )


@app.route("/admin/upload", methods=["POST"])
@login_required
def admin_upload():
    """آپلود تصویر از داخل ویرایشگر بصری."""
    file_storage = request.files.get("file") or request.files.get("image")
    if not file_storage or not file_storage.filename:
        return jsonify({"error": "فایلی فرستاده نشد."}), 400
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"error": "فقط تصویر مجاز است."}), 400
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = secure_filename(f"{secrets.token_hex(8)}{ext}") or f"img{ext}"
    dest = UPLOAD_DIR / name
    file_storage.save(dest)
    url = f"/static/media/uploads/{name}"
    return jsonify({"success": 1, "file": {"url": url}, "location": url})


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
        profile.pop("communities", None)

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
