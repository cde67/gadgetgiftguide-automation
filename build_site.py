"""
Builds the Gadget Gift Guide static site - real HTML pages with genuine
descriptive text (not just graphics), since organic search traffic is the
whole point of this business and that's what search engines actually index
and rank. Hosted free on GitHub Pages.

Each guide gets its own page (docs/guides/<slug>.html) with proper SEO meta
tags, plus a homepage (docs/index.html) listing every guide, a sitemap.xml,
and robots.txt. Run this any time GUIDES changes.
"""
import os
import shutil
import urllib.parse

import guides as g
import fetch_images as fimg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(SCRIPT_DIR, "docs")
IMG_DIR = os.path.join(DOCS_DIR, "images")

SITE_NAME = "Gadget Gift Guide"
SITE_TAGLINE = "Practical, no-nonsense gift picks - the ones that actually get used"
SITE_URL = "https://gadgetgiftguide.pages.dev"
PLACEHOLDER_TAG = "PLACEHOLDER-20"

STYLE = """
  :root {
    --ink: #1a1a2e; --accent: #4361ee; --accent-dark: #2f3fb8;
    --bg: #f7f8fc; --card: #ffffff; --muted: #5a5f73; --border: #e3e5ee;
  }
  * { box-sizing: border-box; }
  body { font-family: 'Inter', -apple-system, sans-serif; margin: 0; background: var(--bg); color: var(--ink); line-height: 1.6; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 32px 20px 80px; }
  header.site { border-bottom: 3px solid var(--ink); padding: 28px 20px; background: var(--card); }
  header.site .wrap { padding: 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
  .brand { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.4rem; text-decoration: none; color: var(--ink); }
  .tagline { color: var(--muted); font-size: 0.95rem; }
  h1 { font-family: 'Space Grotesk', sans-serif; font-size: 2rem; line-height: 1.2; margin: 0 0 12px; }
  h2 { font-family: 'Space Grotesk', sans-serif; font-size: 1.3rem; margin: 0 0 4px; }
  .intro { font-size: 1.08rem; color: var(--muted); margin-bottom: 36px; }
  .item { display: flex; gap: 18px; padding: 22px 0; border-bottom: 1px solid var(--border); align-items: flex-start; }
  .item img { width: 110px; height: 110px; border-radius: 12px; object-fit: cover; flex-shrink: 0; background: var(--border); }
  .item-body { flex: 1; }
  .item-num { display: inline-block; background: var(--accent); color: #fff; font-weight: 700; font-size: 0.8rem;
              width: 24px; height: 24px; border-radius: 50%; text-align: center; line-height: 24px; margin-right: 8px; }
  .item h3 { display: inline; font-size: 1.08rem; margin: 0; }
  .item p { margin: 8px 0 10px; color: var(--muted); }
  .item a.shop { display: inline-block; background: var(--accent); color: #fff; text-decoration: none;
                 padding: 7px 16px; border-radius: 20px; font-size: 0.88rem; font-weight: 600; }
  .item a.shop:hover { background: var(--accent-dark); }
  .guide-card { display: block; background: var(--card); border: 1px solid var(--border); border-radius: 14px;
                padding: 20px; margin-bottom: 16px; text-decoration: none; color: var(--ink); transition: border-color .15s; }
  .guide-card:hover { border-color: var(--accent); }
  .guide-card p { color: var(--muted); margin: 6px 0 0; font-size: 0.95rem; }
  .disclosure { background: #fff8e6; border: 1px solid #f0dca0; border-radius: 10px; padding: 12px 16px; font-size: 0.88rem; color: #6b5a1e; margin: 24px 0; }
  footer { text-align: center; color: var(--muted); font-size: 0.85rem; padding: 30px 20px; }
"""

HEAD_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">'
)


def load_env():
    env = {}
    path = os.path.join(SCRIPT_DIR, ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v
    return env


def amazon_url(item, tag):
    return f"https://www.amazon.com/s?k={urllib.parse.quote_plus(item)}&tag={tag}"


def site_header():
    return f"""<header class="site"><div class="wrap">
      <a class="brand" href="{SITE_URL}/">{SITE_NAME}</a>
      <span class="tagline">{SITE_TAGLINE}</span>
    </div></header>"""


def disclosure_html():
    return '<div class="disclosure">As an Amazon Associate, we earn from qualifying purchases. Prices and availability are subject to change.</div>'


def build_guide_page(guide, tag):
    rows = []
    for i, item in enumerate(guide["items"], start=1):
        photo_path, _credit = fimg.get_item_image(item["name"])
        img_html = ""
        if photo_path:
            fname = os.path.basename(photo_path)
            shutil.copyfile(photo_path, os.path.join(IMG_DIR, fname))
            img_html = f'<img src="{SITE_URL}/images/{fname}" alt="{item["name"]}" loading="lazy">'
        rows.append(f"""
        <div class="item">
          {img_html}
          <div class="item-body">
            <h3><span class="item-num">{i}</span>{item['name']}</h3>
            <p>{item['blurb']}</p>
            <a class="shop" href="{amazon_url(item['name'], tag)}" target="_blank" rel="noopener sponsored">Check price on Amazon</a>
          </div>
        </div>""")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{guide['title']} | {SITE_NAME}</title>
<meta name="description" content="{guide['meta_description']}">
<link rel="canonical" href="{SITE_URL}/guides/{guide['slug']}.html">
<meta property="og:title" content="{guide['title']}">
<meta property="og:description" content="{guide['meta_description']}">
<meta property="og:type" content="article">
{HEAD_FONTS}
<style>{STYLE}</style>
</head>
<body>
{site_header()}
<main class="wrap">
  <h1>{guide['title']}</h1>
  <p class="intro">{guide['intro']}</p>
  {disclosure_html()}
  {"".join(rows)}
</main>
<footer>{SITE_NAME} &middot; <a href="{SITE_URL}/">More gift guides</a></footer>
</body>
</html>
"""


def build_home_page():
    cards = "\n".join(
        f'<a class="guide-card" href="{SITE_URL}/guides/{gu["slug"]}.html"><h2>{gu["title"]}</h2><p>{gu["meta_description"]}</p></a>'
        for gu in g.GUIDES
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_NAME} - {SITE_TAGLINE}</title>
<meta name="description" content="Practical gift guides for tech, gadgets, and everyday upgrades - no filler, just picks that actually get used.">
<link rel="canonical" href="{SITE_URL}/">
{HEAD_FONTS}
<style>{STYLE}</style>
</head>
<body>
{site_header()}
<main class="wrap">
  <h1>All Gift Guides</h1>
  <p class="intro">Practical picks, organized by occasion and budget - no filler, just things worth actually buying.</p>
  {cards}
</main>
<footer>{SITE_NAME}</footer>
</body>
</html>
"""


def build_sitemap():
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/guides/{gu['slug']}.html" for gu in g.GUIDES]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'


def main():
    env = load_env()
    tag = env.get("AMAZON_ASSOCIATE_TAG", "").strip() or PLACEHOLDER_TAG

    os.makedirs(os.path.join(DOCS_DIR, "guides"), exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)

    with open(os.path.join(DOCS_DIR, "index.html"), "w") as f:
        f.write(build_home_page())

    for guide in g.GUIDES:
        with open(os.path.join(DOCS_DIR, "guides", f"{guide['slug']}.html"), "w") as f:
            f.write(build_guide_page(guide, tag))

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w") as f:
        f.write(build_sitemap())

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    print(f"Built {len(g.GUIDES)} guide pages + homepage + sitemap in {DOCS_DIR}")


if __name__ == "__main__":
    main()
