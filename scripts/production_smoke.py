from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import ssl, sys, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
BASE="https://gamehelpx.com"
TIMEOUT=20

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class CanonicalParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical=None
    def handle_starttag(self,tag,attrs):
        if tag!="link": return
        a=dict(attrs)
        if a.get("rel")=="canonical":
            self.canonical=a.get("href")

def fetch(url, follow=True):
    req=Request(url,headers={"User-Agent":"GameHelpX-Production-Smoke/1.0"})
    opener=build_opener() if follow else build_opener(NoRedirect)
    try:
        r=opener.open(req,timeout=TIMEOUT)
        return r.status, dict(r.headers.items()), r.geturl(), r.read()
    except HTTPError as e:
        return e.code, dict(e.headers.items()), e.geturl(), e.read()
    except URLError as e:
        raise RuntimeError(f"{url}: network error: {e}") from e

errors=[]

# HTTPS homepage.
try:
    status,headers,final,body=fetch(BASE+"/")
    if status!=200:
        errors.append(f"homepage status {status}")
    if not final.startswith(BASE):
        errors.append(f"homepage final URL unexpected: {final}")
    text=body.decode("utf-8","replace")
    p=CanonicalParser(); p.feed(text)
    if p.canonical!=BASE+"/":
        errors.append(f"homepage canonical unexpected: {p.canonical}")
    lower={k.lower():v for k,v in headers.items()}
    expected_headers={
        "x-content-type-options":"nosniff",
        "referrer-policy":"strict-origin-when-cross-origin",
        "x-frame-options":"SAMEORIGIN",
    }
    for k,v in expected_headers.items():
        if lower.get(k,"").lower()!=v.lower():
            errors.append(f"homepage header {k}={lower.get(k)!r}, expected {v!r}")
except Exception as e:
    errors.append(str(e))

# robots.txt
try:
    status,headers,final,body=fetch(BASE+"/robots.txt")
    rt=body.decode("utf-8","replace")
    if status!=200: errors.append(f"robots status {status}")
    if f"Sitemap: {BASE}/sitemap.xml" not in rt:
        errors.append("robots.txt missing production sitemap line")
except Exception as e:
    errors.append(str(e))

# sitemap and exact deployed URL set.
try:
    status,headers,final,body=fetch(BASE+"/sitemap.xml")
    if status!=200:
        errors.append(f"sitemap status {status}")
    live=ET.fromstring(body)
    ns={"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    live_urls={(x.text or "").strip() for x in live.findall(".//s:loc",ns)}
    local=ET.parse(ROOT/"sitemap.xml").getroot()
    local_urls={(x.text or "").strip() for x in local.findall(".//s:loc",ns)}
    if live_urls!=local_urls:
        missing=sorted(local_urls-live_urls)
        extra=sorted(live_urls-local_urls)
        if missing: errors.append("live sitemap missing: "+", ".join(missing[:10]))
        if extra: errors.append("live sitemap has unexpected: "+", ".join(extra[:10]))
    print(f"SMOKE sitemap URLs: live={len(live_urls)} local={len(local_urls)}")
except Exception as e:
    errors.append(str(e))

# Important routes.
for route in (
    "/tools/",
    "/games/elden-ring/",
    "/tools/elden-ring-equipment-load-planner/",
    "/games/baldurs-gate-3/",
):
    try:
        status,headers,final,body=fetch(BASE+route)
        if status!=200:
            errors.append(f"{route} status {status}")
        text=body.decode("utf-8","replace")
        p=CanonicalParser(); p.feed(text)
        expected=BASE+route
        if p.canonical!=expected:
            errors.append(f"{route} canonical {p.canonical!r}, expected {expected!r}")
    except Exception as e:
        errors.append(str(e))

# www -> apex host redirect. Cloudflare host-level redirect must do this.
try:
    status,headers,final,body=fetch("https://www.gamehelpx.com/",follow=False)
    location=headers.get("Location") or headers.get("location")
    if status not in (301,302,307,308):
        errors.append(f"www status {status}, expected redirect")
    elif not location or not location.startswith(BASE):
        errors.append(f"www redirect location unexpected: {location!r}")
except Exception as e:
    errors.append(str(e))

# Homepage internal-link audit: every internal homepage anchor must resolve
# to itself rather than silently redirecting to another route.
try:
    from html.parser import HTMLParser as _HTMLParser
    class _AnchorParser(_HTMLParser):
        def __init__(self):
            super().__init__()
            self.hrefs=[]
        def handle_starttag(self,tag,attrs):
            if tag!="a": return
            a=dict(attrs)
            href=a.get("href")
            if href: self.hrefs.append(href)

    status,headers,final,body=fetch(BASE+"/")
    hp=_AnchorParser()
    hp.feed(body.decode("utf-8","replace"))
    homepage_paths=sorted(set(
        h.split("#",1)[0].split("?",1)[0]
        for h in hp.hrefs
        if h.startswith("/")
    ))
    bad=[]
    redirected=[]
    for path in homepage_paths:
        status,headers,final,body=fetch(BASE+path)
        if status!=200:
            bad.append(f"{path}: status {status}")
            continue
        expected=(BASE+path).rstrip("/")+"/"
        got=final.rstrip("/")+"/"
        if got!=expected:
            redirected.append(f"{path} -> {final}")
    print(f"Homepage link audit: {len(homepage_paths)} unique internal links checked")
    if bad:
        errors.append("homepage links failing: "+", ".join(bad[:10]))
    if redirected:
        errors.append("homepage links redirect unexpectedly: "+", ".join(redirected[:10]))
except Exception as e:
    errors.append(f"homepage link audit failed: {e}")

# Search-index link audit: every dynamic search result must resolve on production.
try:
    import json
    raw=(ROOT/"data/search-index.js").read_text(encoding="utf-8").strip()
    prefix="window.GHX_SEARCH_INDEX="
    if not raw.startswith(prefix):
        errors.append("search index format unexpected")
    else:
        payload=raw[len(prefix):]
        if payload.endswith(";"):
            payload=payload[:-1]
        rows=json.loads(payload)
        bad=[]
        redirected=[]
        for row in rows:
            path=row.get("url","")
            if not path.startswith("/"):
                bad.append(f"{path}: invalid path")
                continue
            status,headers,final,body=fetch(BASE+path)
            if status!=200:
                bad.append(f"{path}: status {status}")
                continue
            expected=(BASE+path).rstrip("/")+"/"
            got=final.rstrip("/")+"/"
            if got!=expected:
                redirected.append(f"{path} -> {final}")
        print(f"Search-index link audit: {len(rows)} links checked")
        if bad:
            errors.append("search links failing: "+", ".join(bad[:10]))
        if redirected:
            errors.append("search links redirect unexpectedly: "+", ".join(redirected[:10]))
except Exception as e:
    errors.append(f"search index audit failed: {e}")


print("PRODUCTION SMOKE")
for e in errors:
    print("ERROR",e)
print(f"RESULT: {len(errors)} errors")
sys.exit(1 if errors else 0)
