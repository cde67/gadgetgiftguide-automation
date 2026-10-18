"""
Pinterest pins for every gift guide: a tall 1000x1500 image per guide in
docs/pins/ (served by the site, so Pinterest can fetch it) plus a Bulk Create
Pins CSV the owner uploads by hand (Pinterest doesn't allow automated posting
for accounts like this one).

Pins are scheduled two per day so a new account doesn't dump 14 at once.

  python3 make_pins.py                    images + CSV (first pin in 2 days)
  python3 make_pins.py --start 2026-10-25 first pin on that date
"""
import csv
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site as bs

PIN_W, PIN_H, M = 1000, 1500, 64
PIN_DIR = os.path.join(bs.DOCS_DIR, "pins")
CSV_PATH = os.path.join(bs.SCRIPT_DIR, "pinterest_gift_pins.csv")
BOARD = "Tech Gift Ideas"
PIN_TIMES_UTC = ("13:00:00", "23:00:00")   # ~9am and ~7pm US Eastern
INK, MUTED, LINE, BG = (22, 24, 29), (95, 101, 115), (229, 224, 214), (250, 248, 244)


def _photo(name):
    m = bs.json.load(open(os.path.join(bs.SCRIPT_DIR, "images", "manifest.json")))
    rel = (m.get(name) or {}).get("path")
    p = os.path.join(bs.SCRIPT_DIR, rel) if rel else None
    return p if p and os.path.exists(p) else None


def _cover(img, w, h):
    from PIL import Image
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def make_pin(guide, dates, path):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (PIN_W, PIN_H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, PIN_W, 14], fill=bs.BRAND_RED)
    bs._draw_gift(d, M, 52, 50)
    d.text((M + 66, 58), bs.SITE_NAME, font=bs._font(34), fill=INK)

    d.text((M, 150), bs.guide_label(guide).upper(), font=bs._font(30, serif=False), fill=bs.BRAND_RED)
    title = bs.guide_title(guide, dates)
    size = 84
    while size > 48:
        f = bs._font(size)
        lines = bs._wrap(d, title, f, PIN_W - 2 * M)
        if len(lines) <= 3:
            break
        size -= 6
    y = 200
    for line in lines[:4]:
        d.text((M, y), line, font=f, fill=INK)
        y += int(size * 1.16)

    # the guide's first picks as a numbered list on a white card: concrete
    # product names tell a scroller exactly what's inside
    top = max(y + 40, 470)
    card_bottom = PIN_H - 170
    d.rounded_rectangle([M, top, PIN_W - M, card_bottom], radius=26, fill=(255, 255, 255), outline=LINE, width=2)
    names = [bs.item_label(it) for it in guide["items"]]
    row_h = 108
    n = min(len(names), (card_bottom - top - 90) // row_h, 7)   # leave room for "+ N more"
    fy = top + 34
    for i, name in enumerate(names[:n]):
        nf = bs._font(40, serif=False)
        d.ellipse([M + 32, fy + 6, M + 32 + 60, fy + 66], fill=bs.BRAND_RED)
        d.text((M + 62, fy + 36), str(i + 1), font=bs._font(32, serif=False), fill=(255, 255, 255), anchor="mm")
        size = 40
        while size > 28 and d.textlength(name, font=bs._font(size, serif=False)) > PIN_W - 2 * M - 150:
            size -= 2
        d.text((M + 116, fy + 36), name, font=bs._font(size, serif=False), fill=INK, anchor="lm")
        fy += row_h
    if len(names) > n:
        d.text((M + 116, fy + 20), f"+ {len(names) - n} more", font=bs._font(32, bold=False, serif=False), fill=MUTED, anchor="lm")

    d.line([M, PIN_H - 132, PIN_W - M, PIN_H - 132], fill=LINE, width=2)
    d.text((M, PIN_H - 104), f"See all {len(guide['items'])} picks", font=bs._font(36), fill=INK)
    d.text((M, PIN_H - 56), "gadgetgiftguide.pages.dev", font=bs._font(28, bold=False, serif=False), fill=MUTED)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)


def main():
    start = datetime.date.today() + datetime.timedelta(days=2)  # room to upload first
    if "--start" in sys.argv:
        start = datetime.date.fromisoformat(sys.argv[sys.argv.index("--start") + 1])
    dates = bs.resolve_dates(datetime.date.today())
    rows = []
    for i, gu in enumerate(bs.g.GUIDES):
        make_pin(gu, dates, os.path.join(PIN_DIR, f"{gu['slug']}.png"))
        day = start + datetime.timedelta(days=i // 2)
        hh = PIN_TIMES_UTC[i % 2]
        rows.append({
            "Title": bs.guide_title(gu, dates)[:100],
            "Media URL": f"{bs.SITE_URL}/pins/{gu['slug']}.png",
            "Pinterest board": BOARD,
            "Thumbnail": "",
            "Description": bs.guide_desc(gu, dates)[:500],
            "Link": f"{bs.SITE_URL}{bs.guide_path(gu)}",
            "Publish date": f"{day.isoformat()}T{hh}",
            "Keywords": ", ".join(["gift ideas", "tech gifts", bs.guide_label(gu).lower(), "christmas gifts"]),
        })
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} pins -> docs/pins/, CSV -> {os.path.basename(CSV_PATH)}")


if __name__ == "__main__":
    main()
