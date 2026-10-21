#!/usr/bin/env python3
"""ساخت تصویر Open Graph (۱۲۰۰×۶۳۰) با شکل‌دهی درست فارسی.

از Pillow و libraqm استفاده می‌کند تا حروف عربی/فارسی به‌هم بچسبند
و متن راست‌به‌چپ باشد. reshaper جدا لازم نیست.

خروجی: static/og-default.png
اجرا: python scripts/make_og_image.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/vazirmatn-vf-fonts/Vazirmatn[wght].ttf"

NAME = "عباس داورپناه"
SUBTITLE = "برنامه‌نویس و علاقه‌مند به تکنولوژی و جنبش آزادی نرم‌افزار"
DESC = "نوشته‌ها و تجربه‌ها درباره لینوکس، DevOps و نرم‌افزار آزاد"

W, H = 1200, 630
BG = (10, 14, 20)
FG = (230, 237, 243)
MUTED = (196, 206, 216)
ACCENT = (52, 211, 153)
RIGHT = W - 72
MAX_W = W - 144


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font, direction="rtl", language="fa")
    return bbox[2] - bbox[0]


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if text_width(draw, trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_rtl(draw: ImageDraw.ImageDraw, y: int, text: str, font: ImageFont.FreeTypeFont, fill) -> int:
    draw.text(
        (RIGHT, y),
        text,
        font=font,
        fill=fill,
        direction="rtl",
        language="fa",
        anchor="ra",
    )
    bbox = draw.textbbox((RIGHT, y), text, font=font, direction="rtl", language="fa", anchor="ra")
    return bbox[3] - bbox[1]


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    f_title = load_font(84)
    f_sub = load_font(36)
    f_desc = load_font(30)

    y = 150
    y += draw_rtl(draw, y, NAME, f_title, FG) + 28
    for line in wrap(draw, SUBTITLE, f_sub, MAX_W):
        y += draw_rtl(draw, y, line, f_sub, FG) + 14
    y += 8
    for line in wrap(draw, DESC, f_desc, MAX_W):
        y += draw_rtl(draw, y, line, f_desc, MUTED) + 12

    draw.rounded_rectangle([RIGHT - 140, y + 18, RIGHT, y + 26], radius=4, fill=ACCENT)

    out = BASE / "static" / "og-default.png"
    img.save(out, "PNG", optimize=True)
    print("saved", out, img.size)


if __name__ == "__main__":
    main()
