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

print("PRODUCTION SMOKE")
for e in errors: print("ERROR",e)
print(f"RESULT: {len(errors)} errors")
sys.exit(1 if errors else 0)
