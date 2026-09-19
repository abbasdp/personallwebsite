#!/usr/bin/env python3
"""ساخت تصویر Open Graph (۱۲۰۰×۶۳۰) برای اشتراک‌گذاری در شبکه‌های اجتماعی.

خروجی: static/og-default.png
نیازمندی‌ها (فقط برای اجرای این اسکریپت، نه اجرای سایت):
    pip install pillow arabic-reshaper python-bidi
    و فونت Vazirmatn به‌صورت سیستمی نصب باشد.
اجرا: python scripts/make_og_image.py
"""

from __future__ import annotations

import math
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
REG = "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Regular.ttf"
BLD = "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Bold.ttf"

NAME = "عباس داورپناه"
SUBTITLE = "برنامه‌نویس و علاقه‌مند به تکنولوژی و جنبش آزادی نرم‌افزار"
DESC = "نوشته‌ها و تجربه‌ها درباره لینوکس، DevOps و نرم‌افزار آزاد"


def fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def main() -> None:
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (10, 14, 20))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(10 + t * 5), int(14 + t * 6), int(20 + t * 9)))

    f_title = ImageFont.truetype(BLD, 92)
    f_sub = ImageFont.truetype(BLD, 40)
    f_desc = ImageFont.truetype(REG, 30)
    right = W - 90

    def draw_rtl(y, text, font, fill):
        t = fa(text)
        w = d.textlength(t, font=font)
        d.text((right - w, y), t, font=font, fill=fill)

    title = fa(NAME)
    tw = int(d.textlength(title, font=f_title))
    th = 120
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).text((0, 0), title, font=f_title, fill=255)
    grad = Image.new("RGB", (tw, th))
    gd = ImageDraw.Draw(grad)
    c0, c1, c2 = (52, 211, 153), (34, 211, 238), (167, 139, 250)
    for x in range(tw):
        p = x / max(tw - 1, 1)
        if p < 0.5:
            q = p / 0.5
            col = tuple(int(c0[i] + (c1[i] - c0[i]) * q) for i in range(3))
        else:
            q = (p - 0.5) / 0.5
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * q) for i in range(3))
        gd.line([(x, 0), (x, th)], fill=col)
    img.paste(grad, (right - tw, 170), mask)

    draw_rtl(305, SUBTITLE, f_sub, (230, 237, 243))
    draw_rtl(365, DESC, f_desc, (139, 152, 169))
    d.rounded_rectangle([right - 150, 432, right, 441], radius=4, fill=(52, 211, 153))

    ox, oy, col = 70, 300, (38, 92, 74)
    tiers = [(0, 286, 150, 300), (12, 272, 138, 286), (24, 258, 126, 272),
             (36, 244, 114, 258), (46, 232, 104, 244)]
    for (x1, yt, x2, yb) in tiers:
        d.rectangle([ox + x1, oy + yt, ox + x2, oy + yb], outline=col, width=2)
    d.line([(ox + 52, oy + 232), (ox + 52, oy + 206)], fill=col, width=2)
    d.line([(ox + 98, oy + 232), (ox + 98, oy + 206)], fill=col, width=2)
    d.line([(ox + 52, oy + 206), (ox + 75, oy + 190), (ox + 98, oy + 206)], fill=col, width=2)
    d.rectangle([ox + 68, oy + 214, ox + 82, oy + 232], outline=col, width=2)
    cx = ox + 240
    d.line([(cx, oy + 150), (cx, oy + 300)], fill=col, width=2)
    pts = [(cx + 18 * math.sin((i / 100) * math.pi), oy + 126 + 174 * (i / 100)) for i in range(101)]
    d.line(pts, fill=col, width=2)
    d.line([(2 * cx - x, y) for (x, y) in pts], fill=col, width=2)

    out = BASE / "static" / "og-default.png"
    img.save(out)
    print("saved", out, img.size)


if __name__ == "__main__":
    main()
