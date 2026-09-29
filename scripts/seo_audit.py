from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re, sys, xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT=Path(__file__).resolve().parents[1]
IGNORE_DIRS={".git","_site"}
PROD="https://gamehelpx.com"

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]; self.title=""; self.in_title=False; self.h1=0
        self.description=None; self.canonical=None; self.robots=""
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href"): self.links.append(a["href"])
        elif tag=="title": self.in_title=True
        elif tag=="h1": self.h1+=1
        elif tag=="meta":
            if a.get("name","").lower()=="description": self.description=a.get("content","")
            if a.get("name","").lower()=="robots": self.robots=a.get("content","")
        elif tag=="link" and a.get("rel")=="canonical": self.canonical=a.get("href")
    def handle_endtag(self, tag):
        if tag=="title": self.in_title=False
    def handle_data(self,data):
        if self.in_title: self.title+=data

def route_for(p):
    rel=p.relative_to(ROOT).as_posix()
    if rel=="index.html": return "/"
    if rel=="404.html": return None
    if rel.endswith("/index.html"): return "/"+rel[:-10]
    return "/"+rel

def target_exists(href):
    if not href.startswith("/"): return True
    path=urlsplit(href).path
    if path=="/": return (ROOT/"index.html").exists()
    rel=path.lstrip("/")
    target=ROOT/rel
    if path.endswith("/"): target=target/"index.html"
    elif not target.suffix:
        target=target/"index.html"
    return target.exists()

pages={}
for p in ROOT.rglob("*.html"):
    if any(part in IGNORE_DIRS for part in p.parts): continue
    route=route_for(p)
    if route is None: continue
    parser=P()
    try: parser.feed(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("ERROR parse",p,e); continue
    pages[route]=(p,parser)

errors=[]; warnings=[]; inbound=Counter(); titles=defaultdict(list)
for route,(p,d) in pages.items():
    if d.title.strip(): titles[d.title.strip()].append(route)
    else: warnings.append(f"{route}: missing title")
    if not d.description: warnings.append(f"{route}: missing meta description (runtime fallback exists)")
    if not d.canonical: warnings.append(f"{route}: missing static canonical (runtime fallback exists)")
    elif not d.canonical.startswith(PROD): warnings.append(f"{route}: canonical is not production domain")
    if d.h1!=1: warnings.append(f"{route}: expected 1 H1, found {d.h1}")
    for href in d.links:
        if href.startswith(("#","mailto:","tel:","javascript:")): continue
        if href.startswith(("http://","https://","//")): continue
        path=urlsplit(href).path
        if path.startswith("/"):
            if not target_exists(href): errors.append(f"{route}: broken internal link -> {href}")
            if path.endswith("/"): inbound[path]+=1

for title,routes in titles.items():
    if len(routes)>1: warnings.append("duplicate title: "+title+" -> "+", ".join(routes))

sitemap=ROOT/"sitemap.xml"
sitemap_routes=set()
if sitemap.exists():
    tree=ET.parse(sitemap)
    ns={"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in tree.findall(".//s:loc",ns):
        u=(loc.text or "").strip()
        if u.startswith(PROD):
            route=u[len(PROD):] or "/"
            sitemap_routes.add(route)
            if route not in pages: errors.append(f"sitemap points to missing page: {route}")
            elif "noindex" in pages[route][1].robots.lower(): errors.append(f"sitemap includes noindex page: {route}")
else:
    errors.append("missing sitemap.xml")

for route,(p,d) in pages.items():
    if "noindex" in d.robots.lower(): continue
    if route not in sitemap_routes: warnings.append(f"{route}: indexable page missing from sitemap")
    if route not in {"/","/upcoming/","/games/","/evergreen/","/guides/","/wiki/","/builds/","/tools/","/database/","/about/"} and inbound[route]==0:
        warnings.append(f"{route}: no static inbound links detected (dynamic related links may still exist)")

print(f"SEO AUDIT: {len(pages)} HTML routes, {len(sitemap_routes)} sitemap URLs")
for w in warnings: print("WARN",w)
for e in errors: print("ERROR",e)
print(f"RESULT: {len(errors)} errors, {len(warnings)} warnings")
sys.exit(1 if errors else 0)
