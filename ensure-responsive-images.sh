#!/usr/bin/bash
# Generate any responsive WebP files that HTML srcset points to
# but Publii did not write. Prevents invisible images on deploy.
set -euo pipefail

SITE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="$SITE_ROOT/output"
INPUT_MEDIA="$SITE_ROOT/input/media"
WIDTHS_XS=320
WIDTHS_SM=480
WIDTHS_MD=768
WIDTHS_XL=1024

if ! command -v convert >/dev/null 2>&1; then
    echo "ImageMagick convert not found; skip responsive generate"
    exit 0
fi

generated=0
missing=0

while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    dest="$OUTPUT/$rel"
    if [ -f "$dest" ]; then
        continue
    fi
    missing=$((missing + 1))

    dir=$(dirname "$rel")       # media/posts/17/responsive
    file=$(basename "$rel")     # first-session-cake-xs.webp
    stem=${file%-*}             # first-session-cake-xs  OR first-session-cake
    size=${file##*-}            # xs.webp
    size=${size%.webp}          # xs
    name=${file%-$size.webp}    # first-session-cake
    parent=$(dirname "$dir")    # media/posts/17

    case "$size" in
        xs) w=$WIDTHS_XS ;;
        sm) w=$WIDTHS_SM ;;
        md) w=$WIDTHS_MD ;;
        xl) w=$WIDTHS_XL ;;
        *) echo "unknown size in $rel"; continue ;;
    esac

    src=""
    for ext in jpg jpeg png JPG JPEG PNG webp; do
        if [ -f "$OUTPUT/$parent/$name.$ext" ]; then
            src="$OUTPUT/$parent/$name.$ext"
            break
        fi
        if [ -f "$INPUT_MEDIA/${parent#media/}/$name.$ext" ]; then
            src="$INPUT_MEDIA/${parent#media/}/$name.$ext"
            break
        fi
    done

    if [ -z "$src" ]; then
        echo "no source for $rel"
        continue
    fi

    mkdir -p "$(dirname "$dest")"
    convert "$src" -resize "${w}x>" -quality 70 "$dest"
    # keep a copy in input so the next Publii build ships it
    in_dest="$INPUT_MEDIA/${dir#media/}/$file"
    mkdir -p "$(dirname "$in_dest")"
    cp -f "$dest" "$in_dest"
    echo "generated $rel"
    generated=$((generated + 1))
done < <(
    python3 - "$OUTPUT" << 'PY'
import re, sys
from pathlib import Path
out = Path(sys.argv[1])
seen = set()
for html in out.rglob("*.html"):
    if ".git" in html.parts:
        continue
    text = html.read_text(encoding="utf-8", errors="ignore")
    for raw in re.findall(r'(?:src|srcset)="([^"]+)"', text):
        for part in raw.split(","):
            url = part.strip().split(" ")[0]
            if "/media/" not in url or ".webp" not in url.lower():
                continue
            rel = url.split("/media/", 1)[1]
            rel = "media/" + rel.split("?")[0]
            if rel not in seen:
                seen.add(rel)
                print(rel)
PY
)

echo "responsive check: generated=$generated still-missing-candidates=$missing"
