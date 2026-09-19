#!/usr/bin/env python3
"""وارد کردن نوشته‌ها از فید JSON سایت abbasdp.ir به فایل‌های Markdown محلی.

این اسکریپت:
  - ``feed.json`` را از سایت می‌خواند،
  - تصویرها را در ``static/media`` دانلود و مسیرشان را محلی می‌کند،
  - محتوای HTML هر نوشته را به Markdown تمیز تبدیل می‌کند،
  - و برای هر نوشته یک فایل ``content/posts/<slug>.md`` می‌سازد.

اجرا: ``python scripts/import_from_feed.py``  (به html2text نیاز دارد)
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import html2text

FEED_URL = "https://abbasdp.ir/feed.json"
SITE = "https://abbasdp.ir"
BASE = Path(__file__).resolve().parent.parent
POSTS_DIR = BASE / "content" / "posts"
MEDIA_DIR = BASE / "static" / "media"

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def fa_to_en_digits(s: str) -> str:
    return s.translate(_FA_DIGITS)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = text.replace("&hellip;", "…").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def download_media(remote: str) -> str:
    """تصویر را دانلود و مسیر محلی (نسبت به static) را برمی‌گرداند."""
    if remote.startswith("/"):
        remote = SITE + remote
    rel = remote.split("/media/", 1)[-1]
    dest = MEDIA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        try:
            dest.write_bytes(fetch(remote))
            print(f"  ↓ {rel}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! failed {remote}: {exc}")
            return remote
    return f"/static/media/{rel}"


def localize_images(html: str) -> str:
    def repl(match: re.Match) -> str:
        src = match.group(1)
        if "/media/" in src:
            local = download_media(src)
            return match.group(0).replace(src, local)
        return match.group(0)

    return re.sub(r'<img[^>]*src="([^"]+)"', repl, html)


def to_markdown(html: str) -> str:
    conv = html2text.HTML2Text()
    conv.body_width = 0
    conv.ignore_emphasis = False
    conv.protect_links = True
    conv.mark_code = False
    md = conv.handle(html)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def main() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    feed = json.loads(fetch(FEED_URL))
    for item in feed.get("items", []):
        slug = item["url"].rstrip("/").split("/")[-1]
        title = item["title"]
        date = fa_to_en_digits(item.get("date_published", ""))[:10]
        tags = "، ".join(item.get("tags", []))
        summary = strip_html(item.get("summary", ""))
        cover = ""
        if item.get("image"):
            cover = download_media(item["image"])
        body_html = localize_images(item["content_html"])
        body_md = to_markdown(body_html)

        front = [
            "---",
            f"title: {title}",
            f"date: {date}",
            f"summary: {summary}",
            f"tags: {tags}",
        ]
        if cover:
            front.append(f"cover: {cover}")
        front.append(f"source: {item['url']}")
        front.append("---")
        (POSTS_DIR / f"{slug}.md").write_text(
            "\n".join(front) + "\n\n" + body_md + "\n", encoding="utf-8"
        )
        print(f"✓ {slug}  ({date})")


if __name__ == "__main__":
    main()
