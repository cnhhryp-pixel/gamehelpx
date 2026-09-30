from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re, sys, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PROD="https://gamehelpx.com"
CORE={
    "/",
    "/games/",
    "/upcoming/",
    "/evergreen/",
    "/guides/",
    "/wiki/",
    "/builds/",
    "/database/",
    "/tools/",
    "/about/",
}
IGNORE={".git","_site"}

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical=None
        self.robots=""
        self.og={}
        self.twitter={}
        self.title=""
        self.in_title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="title": self.in_title=True
        elif tag=="link" and a.get("rel")=="canonical":
            self.canonical=a.get("href")
        elif tag=="meta":
            name=(a.get("name") or "").lower()
            prop=(a.get("property") or "").lower()
            if name=="robots": self.robots=a.get("content","")
            if name.startswith("twitter:"): self.twitter[name]=a.get("content","")
            if prop.startswith("og:"): self.og[prop]=a.get("content","")
    def handle_endtag(self,tag):
        if tag=="title": self.in_title=False
    def handle_data(self,data):
        if self.in_title: self.title+=data

def route_for(p):
    rel=p.relative_to(ROOT).as_posix()
    if rel=="index.html": return "/"
    if rel=="404.html": return None
    if rel.endswith("/index.html"): return "/"+rel[:-10]
    return "/"+rel

pages={}
for p in ROOT.rglob("*.html"):
    if any(x in IGNORE for x in p.parts): continue
    route=route_for(p)
    if route is None: continue
    parser=P()
    parser.feed(p.read_text(encoding="utf-8"))
    pages[route]=(p,parser)

errors=[]; warnings=[]

# Canonicals: every indexable page must use production domain.
for route,(p,d) in pages.items():
    if "noindex" in d.robots.lower():
        continue
    if not d.canonical:
        errors.append(f"{route}: missing canonical")
    elif not d.canonical.startswith(PROD):
        errors.append(f"{route}: non-production canonical -> {d.canonical}")

# Core social metadata.
for route in CORE:
    if route not in pages:
        errors.append(f"missing core route: {route}")
        continue
    d=pages[route][1]
    for key in ("og:title","og:description","og:url"):
        if not d.og.get(key):
            errors.append(f"{route}: missing {key}")
    for key in ("twitter:card","twitter:title","twitter:description"):
        if not d.twitter.get(key):
            errors.append(f"{route}: missing {key}")

# robots.txt
robots=(ROOT/"robots.txt")
if not robots.exists():
    errors.append("missing robots.txt")
else:
    rt=robots.read_text(encoding="utf-8")
    if "User-agent: *" not in rt or "Allow: /" not in rt:
        errors.append("robots.txt does not allow crawling")
    if f"Sitemap: {PROD}/sitemap.xml" not in rt:
        errors.append("robots.txt sitemap is not production sitemap")

# sitemap.xml
sitemap=ROOT/"sitemap.xml"
sitemap_urls=[]
if not sitemap.exists():
    errors.append("missing sitemap.xml")
else:
    tree=ET.parse(sitemap)
    ns={"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in tree.findall(".//s:loc",ns):
        u=(loc.text or "").strip()
        sitemap_urls.append(u)
        if not u.startswith(PROD+"/"):
            errors.append(f"sitemap non-production URL: {u}")
    indexable_routes={r for r,(p,d) in pages.items() if "noindex" not in d.robots.lower()}
    sitemap_routes={u[len(PROD):] or "/" for u in sitemap_urls if u.startswith(PROD)}
    missing=sorted(indexable_routes-sitemap_routes)
    extra=sorted(sitemap_routes-indexable_routes)
    if missing:
        errors.append("indexable routes missing from sitemap: "+", ".join(missing[:20]))
    if extra:
        errors.append("sitemap routes without HTML: "+", ".join(extra[:20]))

# Production path redirects / headers.
# Host-level redirects such as www -> apex are verified by the live smoke test,
# because Cloudflare Pages _redirects does not support domain-level redirects.
redirects=ROOT/"_redirects"
if not redirects.exists():
    errors.append("missing _redirects")
else:
    rd=redirects.read_text(encoding="utf-8")
    for expected in ("/home / 301", "/index.html / 301"):
        if expected not in rd:
            errors.append(f"_redirects missing path rule: {expected}")

headers=ROOT/"_headers"
if not headers.exists():
    errors.append("missing _headers")
else:
    hd=headers.read_text(encoding="utf-8")
    for expected in ("X-Content-Type-Options: nosniff","Referrer-Policy: strict-origin-when-cross-origin","X-Frame-Options: SAMEORIGIN"):
        if expected not in hd:
            errors.append(f"_headers missing: {expected}")

# No production canonicals may point to preview/dev hosts.
for route,(p,d) in pages.items():
    raw=p.read_text(encoding="utf-8")
    if d.canonical and ("github.io" in d.canonical or "pages.dev" in d.canonical or "localhost" in d.canonical):
        errors.append(f"{route}: dev host in canonical")
    if route in CORE and "Search 125+ pages" in raw:
        errors.append(f"{route}: stale page-count copy")

print(f"PRODUCTION READINESS: {len(pages)} HTML routes, {len(sitemap_urls)} sitemap URLs")
for w in warnings: print("WARN",w)
for e in errors: print("ERROR",e)
print(f"RESULT: {len(errors)} errors, {len(warnings)} warnings")
sys.exit(1 if errors else 0)
