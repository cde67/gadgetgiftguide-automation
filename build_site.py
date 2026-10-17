"""
Builds the Gadget Gift Guide static site - real HTML pages with genuine
descriptive text, since organic search traffic is the whole point of this
business and that's what search engines actually index and rank. Hosted
free on Cloudflare Pages (gadgetgiftguide.pages.dev) from the docs/ folder.

Outputs (all inside docs/):
  index.html                 homepage (seasonal hero + guides by budget /
                             recipient / interest)
  guides/<slug>.html         one page per guide in guides.GUIDES
  about.html                 how we pick + affiliate disclosure + privacy
  404.html                   real 404 page (without it Cloudflare Pages
                             serves the homepage with a 200 for every bad URL)
  sitemap.xml, robots.txt    absolute https://gadgetgiftguide.pages.dev URLs
  og/<slug>.png              1200x630 social share cards (generated w/ Pillow)
  favicon.svg/.ico, apple-touch-icon.png
  _headers                   Cloudflare Pages response headers

URLs: Cloudflare Pages 308-redirects "/guides/x.html" to "/guides/x", so
canonical tags, the sitemap and every internal link use the extensionless
form. The files themselves stay at guides/<slug>.html.

Never deletes anything in docs/, and never writes the search-console
verification files (docs/google*.html, docs/BingSiteAuth.xml).

Run any time guides.py changes:  python3 build_site.py
"""
import datetime
import fnmatch
import hashlib
import html
import json
import os
import urllib.parse

import guides as g

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(SCRIPT_DIR, "docs")
DATES_PATH = os.path.join(SCRIPT_DIR, "content_dates.json")

SITE_NAME = "Gadget Gift Guide"
SITE_TAGLINE = "Practical tech gifts, sorted by budget and recipient"
SITE_URL = "https://gadgetgiftguide.pages.dev"
PLACEHOLDER_TAG = "PLACEHOLDER-20"

# Files in docs/ that other processes own (search-console verification).
# The build must never overwrite or remove these.
PROTECTED_PATTERNS = ("google*.html", "BingSiteAuth.xml")

GROUP_TITLES = {
    "budget": ("Gifts by budget", "Useful picks that stay under a set price."),
    "recipient": ("Gifts by recipient", "Ideas organized around who you're shopping for."),
    "interest": ("Gifts by interest", "For the home cook, the gamer and the smart home tinkerer."),
}

HEAD_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap" rel="stylesheet">'
)

# Cloudflare Web Analytics (privacy-respecting, no cookies) - added because
# there was previously no way to tell whether this site gets any traffic at
# all. Token is tied to the gadgetgiftguide.pages.dev site in the Cloudflare
# dashboard, not a secret (it only identifies where beacons should count,
# same as a GA measurement ID).
ANALYTICS_SNIPPET = (
    '<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" '
    'data-cf-beacon=\'{"token": "9b1ee8138c594a00ab9b87528af2d08d"}\'></script>'
)

BRAND_RED = (179, 38, 30)
BRAND_RED_DARK = (143, 29, 23)

GIFT_SVG = (
    '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
    '<rect x="6" y="20" width="52" height="40" rx="7" fill="#b3261e"/>'
    '<rect x="2" y="14" width="60" height="14" rx="5" fill="#8f1d17"/>'
    '<rect x="27" y="14" width="10" height="46" fill="#fff"/>'
    '<path d="M32 14c-4-9-15-11-15-4 0 4 7 5 15 4zm0 0c4-9 15-11 15-4 0 4-7 5-15 4z" '
    'fill="none" stroke="#b3261e" stroke-width="4" stroke-linejoin="round"/>'
    '</svg>'
)

STYLE = """
:root{--bg:#faf8f4;--surface:#fff;--ink:#16181d;--ink-2:#3b404c;--muted:#5f6573;--line:#e5e0d6;
--accent:#b3261e;--accent-ink:#8f1d17;--accent-soft:#fbeceb;--cta:#16181d;--cta-ink:#fff;--cta-hover:#b3261e;
--note:#f2eee6;--r:14px;--serif:"Source Serif 4",Georgia,"Times New Roman",serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#121317;--surface:#1a1c22;--ink:#f2f0ea;--ink-2:#d2d5dc;--muted:#a4a9b5;
--line:#2d3038;--accent:#ff8a7e;--accent-ink:#ffa59b;--accent-soft:#2b1c1c;--cta:#f2f0ea;--cta-ink:#121317;--cta-hover:#ff8a7e;--note:#1f2128}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 var(--sans)}
a{color:inherit;text-underline-offset:3px}
a:focus-visible{outline:3px solid var(--accent);outline-offset:2px;border-radius:4px}
h1,h2,h3{font-family:var(--serif);font-weight:700;line-height:1.15;letter-spacing:-.015em;margin:0}
.sr{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.skip{position:absolute;left:-9999px;top:8px}.skip:focus{left:16px;z-index:9;background:var(--surface);padding:8px 12px}
.container{max-width:1120px;margin:0 auto;padding:0 20px}
.narrow{max-width:760px;margin:0 auto;padding:0 20px}
.season{background:var(--ink);color:var(--bg);font-size:.86rem;text-align:center;padding:8px 16px}
.season a{color:inherit;font-weight:600}
header.site{background:var(--surface);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;justify-content:space-between;gap:18px;min-height:66px}
.brand{display:flex;align-items:center;gap:10px;font:700 1.3rem/1 var(--serif);text-decoration:none;letter-spacing:-.01em;white-space:nowrap}
.brand svg{width:30px;height:30px;flex:none}
nav.main{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
nav.main::-webkit-scrollbar{display:none}
nav.main a{white-space:nowrap;text-decoration:none;font-size:.9rem;font-weight:600;color:var(--ink-2);padding:8px 11px;border-radius:999px}
nav.main a:hover{background:var(--accent-soft);color:var(--accent-ink)}
@media (max-width:900px){.bar{flex-direction:column;align-items:flex-start;gap:8px;padding:14px 20px 10px}
nav.main{width:calc(100% + 40px);margin:0 -20px;padding:0 20px 2px}
nav.main a{border:1px solid var(--line);background:var(--bg);padding:6px 12px}}
.kicker{display:inline-block;font-size:.76rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--accent)}
.crumbs{font-size:.84rem;color:var(--muted);margin:26px 0 14px}
.crumbs a{color:var(--muted)}
.crumbs span{margin:0 6px}
article.guide h1{font-size:clamp(2rem,5.4vw,3.05rem);margin:8px 0 14px}
.dek{font-size:1.16rem;line-height:1.6;color:var(--ink-2);margin:0 0 18px}
.byline{font-size:.88rem;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 16px;margin:0 0 18px;padding:12px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.byline b{color:var(--ink);font-weight:600}
.disclosure{font-size:.86rem;line-height:1.55;color:var(--ink-2);background:var(--note);border-left:3px solid var(--accent);padding:10px 14px;border-radius:0 8px 8px 0;margin:0 0 28px}
.disclosure a{font-weight:600}
.glance{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px 22px 12px;margin:0 0 12px}
.glance h2{font-size:1.2rem;margin:0 0 8px}
.glance ol{margin:0;padding:0;list-style:none}
.glance li{display:flex;justify-content:space-between;align-items:baseline;gap:14px;padding:9px 0;border-top:1px solid var(--line)}
.glance li:first-child{border-top:0}
.glance .n{color:var(--accent);font-weight:700;margin-right:8px;font-variant-numeric:tabular-nums}
.glance a.jump{text-decoration:none;font-weight:600}
.glance a.jump:hover{text-decoration:underline}
.glance .go{font-size:.84rem;font-weight:600;color:var(--accent-ink);white-space:nowrap}
.price-note{font-size:.84rem;color:var(--muted);margin:0 0 32px}
.pick{display:grid;grid-template-columns:58px 1fr;gap:0 18px;padding:30px 0;border-top:1px solid var(--line);scroll-margin-top:12px}
.pick-num{font:700 2.3rem/1 var(--serif);color:var(--accent);font-variant-numeric:tabular-nums}
.pick h2{font-size:1.5rem;margin:2px 0 10px}
.best{display:inline-block;font-size:.78rem;font-weight:700;color:var(--accent-ink);background:var(--accent-soft);padding:3px 10px;border-radius:999px;margin:0 0 10px}
.why{margin:0 0 12px;color:var(--ink-2)}
.why strong{color:var(--ink)}
.note{font-size:.92rem;color:var(--muted);margin:0 0 16px;padding-left:12px;border-left:2px solid var(--line)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:46px;background:var(--cta);color:var(--cta-ink);text-decoration:none;font-weight:700;font-size:.96rem;padding:11px 20px;border-radius:10px;transition:background .15s}
.btn:hover{background:var(--cta-hover);color:#fff}
.btn svg{width:16px;height:16px}
.box{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:22px 24px;margin:34px 0}
.box h2{font-size:1.3rem;margin:0 0 10px}
.box p,.box li{color:var(--ink-2)}
.box ul{padding-left:20px;margin:0}
.box li{margin:6px 0}
.related{margin:40px 0 0}
.related h2{font-size:1.4rem;margin:0 0 14px}
.related .grid{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px}
.card{display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px 20px 18px;text-decoration:none;transition:border-color .15s,transform .15s}
.card:hover{border-color:var(--ink);transform:translateY(-2px)}
.card h3{font-size:1.2rem;margin:8px 0 8px}
.card p{color:var(--muted);font-size:.94rem;line-height:1.55;margin:0 0 14px;flex:1}
.card .meta{font-size:.8rem;color:var(--muted);font-weight:600}
.card.feat{border-top:4px solid var(--accent)}
.card.feat h3{font-size:1.4rem}
.hero{padding:48px 0 30px;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:48px;align-items:center}
.hero-aside{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:22px 24px}
.hero-aside h2{font-size:1.15rem;margin:0 0 6px}
.hero-aside ul{list-style:none;margin:0;padding:0}
.hero-aside li a{display:flex;justify-content:space-between;gap:12px;padding:11px 0;border-top:1px solid var(--line);text-decoration:none;font-weight:600}
.hero-aside li:first-child a{border-top:0}
.hero-aside li a span{color:var(--muted);font-weight:400;font-size:.9rem;white-space:nowrap}
.hero-aside li a:hover{color:var(--accent-ink)}
@media (max-width:900px){.hero{grid-template-columns:1fr;gap:24px}}
.hero h1{font-size:clamp(2.3rem,6.4vw,3.9rem);max-width:16ch;margin:10px 0 16px}
.hero .dek{max-width:60ch;font-size:1.2rem}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 0;padding:0;list-style:none}
.chips a{display:inline-block;text-decoration:none;font-weight:600;font-size:.92rem;padding:8px 14px;border:1px solid var(--line);border-radius:999px;background:var(--surface)}
.chips a:hover{border-color:var(--accent);color:var(--accent-ink)}
.home .disclosure{margin:22px 0 0;max-width:760px}
.section{padding:30px 0}
.section-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:0 0 16px;flex-wrap:wrap}
.section-head h2{font-size:clamp(1.5rem,3.4vw,2rem)}
.section-head p{margin:0;color:var(--muted)}
.trust{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:22px;padding:28px 0 6px;border-top:1px solid var(--line)}
.trust h3{font-size:1.1rem;margin:0 0 6px}
.trust p{margin:0;color:var(--muted);font-size:.95rem}
.prose h1{font-size:clamp(2rem,5vw,2.8rem);margin:8px 0 16px}
.prose h2{font-size:1.45rem;margin:34px 0 10px}
.prose p,.prose li{color:var(--ink-2)}
footer.site{margin-top:56px;background:var(--surface);border-top:1px solid var(--line);font-size:.9rem;color:var(--muted)}
.foot{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:28px;padding:36px 0 22px}
.foot h2{font-size:.78rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink);margin:0 0 10px;font-family:var(--sans)}
.foot ul{list-style:none;margin:0;padding:0}
.foot li{margin:5px 0}
.foot a{text-decoration:none}
.foot a:hover{text-decoration:underline;color:var(--ink)}
.legal{border-top:1px solid var(--line);padding:16px 0 26px;font-size:.8rem}
@media (max-width:760px){.foot{grid-template-columns:1fr}}
@media (max-width:560px){body{font-size:16.5px}.pick{grid-template-columns:30px 1fr;gap:0 12px}.pick-num{font-size:1.55rem;padding-top:4px}.pick h2{font-size:1.32rem}
.btn{width:100%}.glance .go{display:none}.box{padding:18px}.hero{padding:30px 0 18px}}
@media print{.season,nav.main,.btn,footer.site{display:none}}
"""

ARROW_SVG = (
    '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M5 3h8v8M13 3 3 13" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


# ----------------------------------------------------------------------------
# Config / data loading
# ----------------------------------------------------------------------------

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


def load_product_links():
    path = os.path.join(SCRIPT_DIR, "product_links.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


PRODUCT_LINKS = load_product_links()


def esc(text):
    return html.escape(str(text), quote=True)


def amazon_url(item, tag):
    """Returns (url, is_direct). An explicit item["search"] wins (used when
    the auto-resolved listing in product_links.json doesn't fit the guide,
    e.g. it's over budget). Otherwise a resolved product page when
    product_links.json has one for item["name"], else an Amazon search for
    the item's name. Every link carries the Associates tag."""
    q_tag = urllib.parse.quote(tag, safe="-")
    if item.get("search"):
        return f"https://www.amazon.com/s?k={urllib.parse.quote_plus(item['search'])}&tag={q_tag}", False
    link = PRODUCT_LINKS.get(item["name"])
    if link and link.get("url"):
        return f"{link['url']}?tag={q_tag}", True
    return f"https://www.amazon.com/s?k={urllib.parse.quote_plus(item['name'])}&tag={q_tag}", False


# ----------------------------------------------------------------------------
# Content dates (drive "Updated" bylines, JSON-LD dates and sitemap lastmod)
# ----------------------------------------------------------------------------

def _hash(obj):
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def resolve_dates(today):
    """Tracks when each guide's content last changed, so the visible
    "Updated" date and sitemap lastmod stay honest across weekly rebuilds
    (they only move when the guide text actually changes)."""
    state = {}
    if os.path.exists(DATES_PATH):
        try:
            with open(DATES_PATH) as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
    today_s = today.isoformat()
    out = {}
    for guide in g.GUIDES:
        content = {k: v for k, v in guide.items() if k != "published"}
        h = _hash(content)
        prev = state.get(guide["slug"], {})
        published = guide.get("published") or prev.get("published") or today_s
        updated = prev.get("updated") if prev.get("hash") == h else today_s
        updated = max(updated or today_s, published)
        out[guide["slug"]] = {"hash": h, "published": published, "updated": updated}
    about_h = _hash(ABOUT_BODY)
    prev = state.get("_about", {})
    out["_about"] = {"hash": about_h, "updated": prev.get("updated") if prev.get("hash") == about_h else today_s}
    try:
        with open(DATES_PATH, "w") as f:
            json.dump(out, f, indent=2, sort_keys=True)
            f.write("\n")
    except OSError:
        pass
    return out


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# ----------------------------------------------------------------------------
# Guide helpers (all optional fields have defaults so new guides added by the
# monthly content task with only the basic fields still render correctly)
# ----------------------------------------------------------------------------

def fill(text, guide, dates):
    year = dates[guide["slug"]]["updated"][:4]
    return text.replace("{count}", str(len(guide["items"]))).replace("{year}", year)


def guide_title(guide, dates):
    return fill(guide["title"], guide, dates)


def guide_desc(guide, dates):
    return fill(guide["meta_description"], guide, dates)


def guide_path(guide):
    return f"/guides/{guide['slug']}"


def guide_groups(guide):
    groups = [x for x in (guide.get("groups") or []) if x in GROUP_TITLES]
    return groups or ["interest"]


def guide_label(guide):
    if guide.get("nav_label"):
        return guide["nav_label"]
    return GROUP_TITLES[guide_groups(guide)[0]][0].replace("Gifts by ", "").capitalize()


def item_label(item):
    return item.get("label") or item["name"]


def season(today):
    """Holiday framing Sept-Dec; neutral the rest of the year."""
    if today.month >= 9:
        return f"Holiday {today.year}"
    return None


# ----------------------------------------------------------------------------
# Shared page chrome
# ----------------------------------------------------------------------------

def nav_html():
    links = [(guide_label(gu), guide_path(gu)) for gu in g.GUIDES if gu.get("nav")]
    links.append(("All guides", "/#all-guides"))
    links.append(("How we pick", "/about"))
    return "".join(f'<a href="{esc(href)}">{esc(label)}</a>' for label, href in links)


def header_html(today):
    s = season(today)
    banner = ""
    if s and today.month >= 11:
        banner = (
            '<div class="season">Shopping for December 25? Check the delivery estimate on each Amazon listing '
            'before you order. <a href="/#all-guides">Browse all gift guides</a></div>'
        )
    return f"""{banner}<header class="site"><div class="container bar">
<a class="brand" href="/">{GIFT_SVG}<span>{SITE_NAME}</span></a>
<nav class="main" aria-label="Gift guides">{nav_html()}</nav>
</div></header>"""


def footer_html(today, dates):
    budget_only = [gu for gu in g.GUIDES if guide_groups(gu) == ["budget"]]
    everything_else = [gu for gu in g.GUIDES if gu not in budget_only]
    def col(title, guides):
        lis = "".join(f'<li><a href="{guide_path(gu)}">{esc(guide_label(gu))}</a></li>' for gu in guides)
        return f"<div><h2>{title}</h2><ul>{lis}</ul></div>"
    return f"""<footer class="site"><div class="container">
<div class="foot">
<div><h2>{SITE_NAME}</h2><p>Independent, practical gift guides for tech and everyday gadgets. We explain why each pick made the list and never publish made-up ratings or reviews.</p>
<ul><li><a href="/about">About &amp; how we pick</a></li><li><a href="/about#disclosure">Affiliate disclosure</a></li><li><a href="/about#privacy">Privacy</a></li></ul></div>
{col("By budget &amp; occasion", budget_only)}
{col("By recipient &amp; interest", everything_else)}
</div>
<div class="legal">As an Amazon Associate, {SITE_NAME} earns from qualifying purchases. Amazon and the Amazon logo are trademarks of Amazon.com, Inc. or its affiliates. Prices and availability are set by the retailer and change often. &copy; {today.year} {SITE_NAME}.</div>
</div></footer>"""


def disclosure_html():
    return (
        '<aside class="disclosure" aria-label="Affiliate disclosure"><strong>Affiliate disclosure:</strong> '
        "We may earn a commission when you buy through links on this page, at no extra cost to you. "
        "As an Amazon Associate we earn from qualifying purchases. This never affects which products we pick. "
        '<a href="/about#disclosure">How we make money</a></aside>'
    )


def jsonld(obj):
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{data}</script>'


def page(*, title, desc, path, body, today, dates, og_image=None, og_type="website",
         extra_head="", ld=None, robots="index,follow,max-image-preview:large", canonical=True):
    url = SITE_URL + path
    og_img = f"{SITE_URL}{og_image}" if og_image else None
    meta = [
        f'<title>{esc(title)}</title>',
        f'<meta name="description" content="{esc(desc)}">',
        f'<meta name="robots" content="{robots}">',
    ]
    if canonical:
        meta.append(f'<link rel="canonical" href="{esc(url)}">')
    meta += [
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{esc(url)}">',
    ]
    if og_img:
        meta += [
            f'<meta property="og:image" content="{esc(og_img)}">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{esc(title)}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{esc(og_img)}">',
        ]
    else:
        meta.append('<meta name="twitter:card" content="summary">')
    meta += [
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        '<link rel="icon" href="/favicon.ico" sizes="32x32">',
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<meta name="theme-color" content="#faf8f4" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#121317" media="(prefers-color-scheme: dark)">',
    ]
    ld_html = jsonld(ld) if ld else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{chr(10).join(meta)}
{extra_head}{HEAD_FONTS}
<style>{STYLE}</style>
{ld_html}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{header_html(today)}
{body}
{footer_html(today, dates)}
{ANALYTICS_SNIPPET}
</body>
</html>
"""


def org_ld():
    return {
        "@type": "Organization",
        "@id": f"{SITE_URL}/#org",
        "name": SITE_NAME,
        "url": f"{SITE_URL}/",
        "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/apple-touch-icon.png", "width": 180, "height": 180},
    }


def guide_card(gu, dates, featured=False):
    d = dates[gu["slug"]]["updated"]
    month = datetime.date.fromisoformat(d).strftime("%b %Y")
    cls = "card feat" if featured else "card"
    return (
        f'<a class="{cls}" href="{guide_path(gu)}"><span class="kicker">{esc(guide_label(gu))}</span>'
        f'<h3>{esc(guide_title(gu, dates))}</h3><p>{esc(guide_desc(gu, dates))}</p>'
        f'<span class="meta">{len(gu["items"])} picks &middot; Updated {month}</span></a>'
    )


# ----------------------------------------------------------------------------
# Guide page
# ----------------------------------------------------------------------------

def related_guides(guide, n=3):
    mine = set(guide_groups(guide))
    others = [gu for gu in g.GUIDES if gu["slug"] != guide["slug"]]
    same = [gu for gu in others if mine & set(guide_groups(gu))]
    rest = [gu for gu in others if gu not in same]
    # Mix: up to 2 from the same section, then featured/others for breadth.
    picks = same[:2]
    for gu in sorted(rest, key=lambda x: not x.get("featured")):
        if len(picks) >= n:
            break
        picks.append(gu)
    for gu in same[2:]:
        if len(picks) >= n:
            break
        picks.append(gu)
    return picks[:n]


def build_guide_page(guide, tag, today, dates, has_og):
    title = guide_title(guide, dates)
    desc = guide_desc(guide, dates)
    path = guide_path(guide)
    url = SITE_URL + path
    d = dates[guide["slug"]]
    label = guide_label(guide)
    s = season(today)

    glance, picks, list_ld = [], [], []
    for i, item in enumerate(guide["items"], start=1):
        name = item_label(item)
        href, direct = amazon_url(item, tag)
        cta = "Check price on Amazon" if direct else "See options on Amazon"
        anchor = f"pick-{i}"
        glance.append(
            f'<li><span><span class="n">{i}</span><a class="jump" href="#{anchor}">{esc(name)}</a></span>'
            f'<a class="go" href="{esc(href)}" target="_blank" rel="sponsored noopener">Amazon<span class="sr"> (opens in a new tab)</span></a></li>'
        )
        best = f'<p class="best">Best for: {esc(item["best_for"])}</p>' if item.get("best_for") else ""
        note = f'<p class="note"><strong>Good to know:</strong> {esc(item["note"])}</p>' if item.get("note") else ""
        picks.append(f"""<section class="pick" id="{anchor}">
<div class="pick-num" aria-hidden="true">{i}</div>
<div>
<h2><span class="sr">{i}. </span>{esc(name)}</h2>
{best}<p class="why"><strong>Why we picked it:</strong> {esc(item['blurb'])}</p>
{note}<a class="btn" href="{esc(href)}" target="_blank" rel="sponsored noopener">{cta} {ARROW_SVG}<span class="sr"> (opens in a new tab)</span></a>
</div>
</section>""")
        list_ld.append({"@type": "ListItem", "position": i, "name": name, "url": f"{url}#{anchor}"})

    price_note = ""
    if guide.get("budget"):
        price_note = (
            f'<p class="price-note">Budget note: we chose product types that usually sell for under ${guide["budget"]}. '
            "Amazon prices change often and vary by seller, size and pack count, so check the current price before you buy.</p>"
        )
    else:
        price_note = '<p class="price-note">Prices change often, so check the current price on Amazon before you buy.</p>'

    tips = ""
    if guide.get("tips"):
        lis = "".join(f"<li>{esc(t)}</li>" for t in guide["tips"])
        tips = f'<section class="box"><h2>Gift-buying tips</h2><ul>{lis}</ul></section>'

    related = "".join(guide_card(gu, dates) for gu in related_guides(guide))
    kicker = f"{s} &middot; {esc(label)}" if s else esc(label)

    body = f"""<main id="main" class="narrow">
<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/#{guide_groups(guide)[0]}">{esc(GROUP_TITLES[guide_groups(guide)[0]][0])}</a><span aria-hidden="true">/</span>{esc(label)}</nav>
<article class="guide">
<span class="kicker">{kicker}</span>
<h1>{esc(title)}</h1>
<p class="dek">{esc(guide['intro'])}</p>
<div class="byline"><span>By <b>The {SITE_NAME} editors</b></span><span>Updated <time datetime="{d['updated']}">{nice_date(d['updated'])}</time></span><span>{len(guide['items'])} picks</span></div>
{disclosure_html()}
<section class="glance" aria-labelledby="glance-h"><h2 id="glance-h">The picks at a glance</h2><ol>{''.join(glance)}</ol></section>
{price_note}
{''.join(picks)}
{tips}
<section class="box"><h2>How we picked</h2>
<p>We look for widely available products that solve a specific, everyday problem, and skip novelty items that tend to end up in a drawer. We don't accept payment for placement, and we don't publish star ratings, review counts or prices we can't keep current. We haven't hands-on tested every product here, so we describe what each one does and who it suits rather than inventing scores. <a href="/about">More about how we pick</a>.</p>
</section>
</article>
<section class="related" aria-labelledby="rel-h"><h2 id="rel-h">More gift guides</h2><div class="grid">{related}</div></section>
</main>"""

    og_path = f"/og/{guide['slug']}.png" if has_og else None
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": f"{url}#article",
                "headline": title,
                "description": desc,
                "datePublished": d["published"],
                "dateModified": d["updated"],
                "mainEntityOfPage": url,
                "author": {"@type": "Organization", "name": f"The {SITE_NAME} editors", "url": f"{SITE_URL}/about"},
                "publisher": {"@id": f"{SITE_URL}/#org"},
                **({"image": [SITE_URL + og_path]} if og_path else {}),
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
                    {"@type": "ListItem", "position": 2, "name": label, "item": url},
                ],
            },
            {"@type": "ItemList", "name": title, "numberOfItems": len(list_ld), "itemListElement": list_ld},
            org_ld(),
        ],
    }
    extra = (
        f'<meta property="article:published_time" content="{d["published"]}">\n'
        f'<meta property="article:modified_time" content="{d["updated"]}">\n'
    )
    # Keep the brand suffix only when the whole title stays short enough not
    # to be truncated in search results (the guide title matters more).
    full_title = f"{title} | {SITE_NAME}" if len(title) + len(SITE_NAME) + 3 <= 70 else title
    return page(title=full_title, desc=desc, path=path, body=body, today=today, dates=dates,
                og_image=og_path, og_type="article", extra_head=extra, ld=ld)


# ----------------------------------------------------------------------------
# Homepage
# ----------------------------------------------------------------------------

def build_home_page(today, dates, has_og):
    s = season(today)
    year = today.year
    if s:
        h1 = f"The best tech gifts for the {year} holidays"
        title = f"Best Tech Gifts {year} by Budget & Recipient | {SITE_NAME}"
        kicker = f"Holiday Gift Guide {year}"
    else:
        h1 = "Practical tech gifts people actually use"
        title = f"{SITE_NAME}: Practical Tech Gift Ideas by Budget & Recipient"
        kicker = "Gift guides"
    desc = (
        f"Practical tech gift guides for {year}: gifts under $25 and $50, ideas for dad, teens and "
        "grandparents, and stocking stuffers, with honest notes on every pick."
    )

    chips = "".join(
        f'<li><a href="{guide_path(gu)}">{esc(guide_label(gu))}</a></li>' for gu in g.GUIDES if gu.get("nav")
    )
    budget_guides = sorted([gu for gu in g.GUIDES if gu.get("budget")], key=lambda gu: gu["budget"])
    budget_links = "".join(
        f'<li><a href="{guide_path(gu)}">{esc(guide_title(gu, dates).split(" (")[0])}<span>{len(gu["items"])} picks</span></a></li>'
        for gu in budget_guides
    )
    featured = [gu for gu in g.GUIDES if gu.get("featured")][:4]
    feat_html = "".join(guide_card(gu, dates, featured=True) for gu in featured)

    sections = []
    for key, (stitle, sdesc) in GROUP_TITLES.items():
        members = [gu for gu in g.GUIDES if key in guide_groups(gu)]
        if key == "budget":
            members.sort(key=lambda gu: gu.get("budget") or 10**6)
        if not members:
            continue
        cards = "".join(guide_card(gu, dates) for gu in members)
        sections.append(
            f'<section class="section" id="{key}" aria-labelledby="{key}-h"><div class="section-head">'
            f'<h2 id="{key}-h">{stitle}</h2><p>{sdesc}</p></div><div class="grid">{cards}</div></section>'
        )

    body = f"""<main id="main" class="container home">
<section class="hero">
<div>
<span class="kicker">{kicker}</span>
<h1>{esc(h1)}</h1>
<p class="dek">Gift guides sorted by budget and by who you're shopping for. Every pick comes with a plain-English reason it made the list, and a link to check the current price on Amazon.</p>
<ul class="chips" aria-label="Popular guides">{chips}</ul>
{disclosure_html()}
</div>
<aside class="hero-aside" aria-labelledby="budget-h"><h2 id="budget-h">Shop by budget</h2><ul>{budget_links}</ul></aside>
</section>
<section class="section" aria-labelledby="feat-h"><div class="section-head"><h2 id="feat-h">Start here</h2><p>Our most useful guides for this season.</p></div>
<div class="grid">{feat_html}</div></section>
<div id="all-guides">{''.join(sections)}</div>
<section class="trust" aria-label="How we work">
<div><h3>Picked for usefulness</h3><p>We favor widely available products that solve a real, everyday problem over novelty gadgets.</p></div>
<div><h3>No fake reviews or ratings</h3><p>We don't publish star ratings, review counts or prices we can't verify and keep current.</p></div>
<div><h3>Clear about how we earn</h3><p>We earn a commission from qualifying Amazon purchases. It never decides what makes a list. <a href="/about#disclosure">Details</a></p></div>
</section>
</main>"""

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": f"{SITE_URL}/#website", "name": SITE_NAME, "url": f"{SITE_URL}/",
             "description": SITE_TAGLINE, "publisher": {"@id": f"{SITE_URL}/#org"}},
            org_ld(),
            {"@type": "ItemList", "name": "Gift guides", "itemListElement": [
                {"@type": "ListItem", "position": i, "url": SITE_URL + guide_path(gu)}
                for i, gu in enumerate(g.GUIDES, start=1)]},
        ],
    }
    return page(title=title, desc=desc, path="/", body=body, today=today, dates=dates,
                og_image="/og/home.png" if has_og else None, ld=ld)


# ----------------------------------------------------------------------------
# About + 404
# ----------------------------------------------------------------------------

ABOUT_BODY = f"""
<h2 id="how-we-pick">How we pick</h2>
<p>{SITE_NAME} publishes practical gift guides for tech and everyday gadgets. Each guide starts from a real buying situation - a budget, a person or a hobby - and lists products that solve a specific everyday problem for that situation.</p>
<ul>
<li>We favor widely available products and well-established product categories over novelty items.</li>
<li>Every pick comes with a short, plain-English explanation of why it made the list and, where it matters, a compatibility note (for example, whether a gadget needs an iPhone).</li>
<li>We haven't hands-on tested every product we list. Rather than inventing scores, we describe what a product does and who it suits.</li>
<li>We don't publish star ratings, review counts, testimonials or prices, because those change constantly and we can't verify them. Check the current details on the retailer's page before buying.</li>
<li>We update guides when products change or better options become widely available. Each guide shows the date it was last updated.</li>
</ul>
<h2 id="disclosure">Affiliate disclosure</h2>
<p>{SITE_NAME} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. As an Amazon Associate we earn from qualifying purchases.</p>
<p>That means if you click a link on this site and buy something, we may earn a small commission at no extra cost to you. Links to Amazon are marked as sponsored links. Commissions help keep the site running; they never determine which products we include, and no brand pays to be listed.</p>
<h2 id="privacy">Privacy</h2>
<p>We use Cloudflare Web Analytics to count page views. It doesn't use cookies or track you across other sites. When you click through to Amazon, Amazon's own privacy policy applies on their site.</p>
"""


def build_about_page(today, dates, has_og):
    upd = dates["_about"]["updated"]
    body = f"""<main id="main" class="narrow prose">
<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span>About</nav>
<span class="kicker">About</span>
<h1>About {SITE_NAME}</h1>
<p class="dek">Who we are, how we choose what goes in our gift guides, and how the site makes money.</p>
<div class="byline"><span>Updated <time datetime="{upd}">{nice_date(upd)}</time></span></div>
{ABOUT_BODY}
</main>"""
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "AboutPage", "url": f"{SITE_URL}/about", "name": f"About {SITE_NAME}", "dateModified": upd,
             "publisher": {"@id": f"{SITE_URL}/#org"}},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
                {"@type": "ListItem", "position": 2, "name": "About", "item": f"{SITE_URL}/about"}]},
            org_ld(),
        ],
    }
    return page(title=f"About & How We Pick | {SITE_NAME}",
                desc=f"How {SITE_NAME} chooses the products in its gift guides, how the site earns money through the Amazon Associates program, and our privacy approach.",
                path="/about", body=body, today=today, dates=dates,
                og_image="/og/home.png" if has_og else None, ld=ld)


def build_404_page(today, dates):
    featured = [gu for gu in g.GUIDES if gu.get("featured")][:3] or g.GUIDES[:3]
    cards = "".join(guide_card(gu, dates) for gu in featured)
    body = f"""<main id="main" class="narrow prose">
<span class="kicker">Error 404</span>
<h1>We couldn't find that page</h1>
<p class="dek">The link may be old or mistyped. These guides are a good place to start, or head to the <a href="/">homepage</a> for every guide.</p>
<div class="grid">{cards}</div>
</main>"""
    return page(title=f"Page not found | {SITE_NAME}", desc="This page doesn't exist.", path="/404",
                body=body, today=today, dates=dates, robots="noindex", canonical=False)


# ----------------------------------------------------------------------------
# Sitemap, robots, headers
# ----------------------------------------------------------------------------

def build_sitemap(dates):
    guide_dates = [dates[gu["slug"]]["updated"] for gu in g.GUIDES]
    entries = [(f"{SITE_URL}/", max(guide_dates + [dates["_about"]["updated"]]))]
    entries += [(SITE_URL + guide_path(gu), dates[gu["slug"]]["updated"]) for gu in g.GUIDES]
    entries.append((f"{SITE_URL}/about", dates["_about"]["updated"]))
    body = "\n".join(f"  <url><loc>{esc(u)}</loc><lastmod>{d}</lastmod></url>" for u, d in entries)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'


ROBOTS_TXT = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"

HEADERS_FILE = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
/og/*
  Cache-Control: public, max-age=86400
/favicon.ico
  Cache-Control: public, max-age=604800
/favicon.svg
  Cache-Control: public, max-age=604800
/apple-touch-icon.png
  Cache-Control: public, max-age=604800
"""

FAVICON_SVG = GIFT_SVG.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1).replace(
    ' aria-hidden="true" focusable="false"', "")


# ----------------------------------------------------------------------------
# Images (favicons + social cards). Pillow is optional: if it's missing or a
# font can't load, the build still succeeds, just without og:image.
# ----------------------------------------------------------------------------

def _font(size, bold=True, serif=True):
    from PIL import ImageFont
    candidates = []
    if serif:
        candidates += ["/System/Library/Fonts/Supplemental/Georgia Bold.ttf" if bold else
                       "/System/Library/Fonts/Supplemental/Georgia.ttf", "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"]
    candidates += ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
                   "/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _draw_gift(draw, x, y, s):
    """Gift-box mark drawn with primitives (matches GIFT_SVG), s = size px."""
    k = s / 64.0
    def R(a, b, c, d):
        return [x + a * k, y + b * k, x + c * k, y + d * k]
    draw.rounded_rectangle(R(6, 20, 58, 60), radius=7 * k, fill=BRAND_RED)
    draw.rounded_rectangle(R(2, 14, 62, 28), radius=5 * k, fill=BRAND_RED_DARK)
    draw.rectangle(R(27, 14, 37, 60), fill=(255, 255, 255))
    w = max(1, round(4 * k))
    draw.ellipse(R(15, 3, 32, 15), outline=BRAND_RED, width=w)
    draw.ellipse(R(32, 3, 49, 15), outline=BRAND_RED, width=w)


def _save_if_changed(img, path, fmt, **kw):
    import io
    buf = io.BytesIO()
    img.save(buf, fmt, **kw)
    data = buf.getvalue()
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return
    safe_write(path, data, binary=True)


def build_icons():
    try:
        from PIL import Image, ImageDraw
        big = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        _draw_gift(ImageDraw.Draw(big), 0, 0, 512)
        _save_if_changed(big, os.path.join(DOCS_DIR, "favicon.ico"), "ICO", sizes=[(16, 16), (32, 32), (48, 48)])
        touch = Image.new("RGB", (180, 180), (250, 248, 244))
        _draw_gift(ImageDraw.Draw(touch), 22, 22, 136)
        _save_if_changed(touch, os.path.join(DOCS_DIR, "apple-touch-icon.png"), "PNG", optimize=True)
        return True
    except Exception as e:  # never fail the build over an icon
        print(f"  (icons skipped: {e})")
        return False


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_og(path, kicker, title, footer):
    from PIL import Image, ImageDraw
    W, H, M = 1200, 630, 80
    img = Image.new("RGB", (W, H), (250, 248, 244))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 12], fill=BRAND_RED)
    _draw_gift(d, M, 62, 54)
    d.text((M + 72, 70), SITE_NAME, font=_font(36), fill=(22, 24, 29))
    d.text((M, 168), kicker.upper(), font=_font(28, serif=False), fill=BRAND_RED)
    size = 76
    while size > 40:
        f = _font(size)
        lines = _wrap(d, title, f, W - 2 * M)
        if len(lines) <= 3:
            break
        size -= 6
    y = 220
    for line in lines[:4]:
        d.text((M, y), line, font=f, fill=(22, 24, 29))
        y += int(size * 1.18)
    d.line([M, H - 104, W - M, H - 104], fill=(229, 224, 214), width=2)
    d.text((M, H - 80), footer, font=_font(28, bold=False, serif=False), fill=(95, 101, 115))
    _save_if_changed(img, path, "PNG", optimize=True)


def build_og_images(today, dates):
    try:
        og_dir = os.path.join(DOCS_DIR, "og")
        os.makedirs(og_dir, exist_ok=True)
        s = season(today)
        make_og(os.path.join(og_dir, "home.png"), s and f"{s} gift guides" or "Gift guides",
                "Practical tech gifts, sorted by budget and by who you're shopping for",
                "Gift ideas under $25 and $50, for dad, teens, grandparents and more")
        for gu in g.GUIDES:
            upd = datetime.date.fromisoformat(dates[gu["slug"]]["updated"])
            make_og(os.path.join(og_dir, f"{gu['slug']}.png"), guide_label(gu), guide_title(gu, dates),
                    f"{len(gu['items'])} picks  ·  Updated {upd.strftime('%B')} {upd.year}")
        return True
    except Exception as e:  # never fail the build over social images
        print(f"  (social images skipped: {e})")
        return False


# ----------------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------------

def is_protected(path):
    rel = os.path.relpath(path, DOCS_DIR)
    if os.sep in rel:
        return False
    return any(fnmatch.fnmatch(rel, pat) for pat in PROTECTED_PATTERNS)


def safe_write(path, content, binary=False):
    if is_protected(path):
        raise RuntimeError(f"Refusing to overwrite protected verification file: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as f:
        f.write(content)


def main():
    env = load_env()
    tag = env.get("AMAZON_ASSOCIATE_TAG", "").strip() or PLACEHOLDER_TAG
    today = datetime.date.today()

    slugs = [gu["slug"] for gu in g.GUIDES]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Duplicate guide slug in guides.py")

    dates = resolve_dates(today)
    os.makedirs(os.path.join(DOCS_DIR, "guides"), exist_ok=True)

    build_icons()
    safe_write(os.path.join(DOCS_DIR, "favicon.svg"), FAVICON_SVG + "\n")
    has_og = build_og_images(today, dates)

    safe_write(os.path.join(DOCS_DIR, "index.html"), build_home_page(today, dates, has_og))
    for guide in g.GUIDES:
        safe_write(os.path.join(DOCS_DIR, "guides", f"{guide['slug']}.html"),
                   build_guide_page(guide, tag, today, dates, has_og))
    safe_write(os.path.join(DOCS_DIR, "about.html"), build_about_page(today, dates, has_og))
    safe_write(os.path.join(DOCS_DIR, "404.html"), build_404_page(today, dates))
    safe_write(os.path.join(DOCS_DIR, "sitemap.xml"), build_sitemap(dates))
    safe_write(os.path.join(DOCS_DIR, "robots.txt"), ROBOTS_TXT)
    safe_write(os.path.join(DOCS_DIR, "_headers"), HEADERS_FILE)

    print(f"Built {len(g.GUIDES)} guide pages + homepage + about + 404 + sitemap in {DOCS_DIR}")


if __name__ == "__main__":
    main()
