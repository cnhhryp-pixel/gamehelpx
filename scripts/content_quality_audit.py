from pathlib import Path
from html.parser import HTMLParser
import re

ROOT=Path(__file__).resolve().parents[1]
SKIP={".git","_site"}

class MainTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main=False
        self.skip=0
        self.text=[]
        self.p=0; self.li=0; self.h2=0; self.h3=0; self.internal=0
        self.inputs=0; self.buttons=0; self.selects=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="main": self.in_main=True
        if tag in {"script","style","nav","footer"} and self.in_main: self.skip+=1
        if not self.in_main or self.skip: return
        if tag=="p": self.p+=1
        elif tag=="li": self.li+=1
        elif tag=="h2": self.h2+=1
        elif tag=="h3": self.h3+=1
        elif tag=="a" and a.get("href","").startswith("/"): self.internal+=1
        elif tag=="input": self.inputs+=1
        elif tag=="button": self.buttons+=1
        elif tag=="select": self.selects+=1
    def handle_endtag(self,tag):
        if tag in {"script","style","nav","footer"} and self.in_main and self.skip: self.skip-=1
        if tag=="main": self.in_main=False
    def handle_data(self,data):
        if self.in_main and not self.skip:
            t=" ".join(data.split())
            if t:self.text.append(t)

def route_for(p):
    rel=p.relative_to(ROOT).as_posix()
    if rel=="index.html": return "/"
    if rel=="404.html": return None
    if rel.endswith("/index.html"): return "/"+rel[:-10]
    return "/"+rel

rows=[]
for p in ROOT.rglob("*.html"):
    if any(x in SKIP for x in p.parts): continue
    route=route_for(p)
    if route is None or route=="/search/": continue
    parser=MainTextParser()
    try: parser.feed(p.read_text(encoding="utf-8"))
    except Exception: continue
    body=" ".join(parser.text)
    words=re.findall(r"[A-Za-z0-9][A-Za-z0-9'’:-]*",body)
    word_count=len(words)
    interactive=parser.inputs+parser.buttons+parser.selects
    is_tool=route.startswith("/tools/")
    # Simple quality score: depth + structure + navigability + utility.
    score=min(word_count/3,50)
    score+=min((parser.p+parser.li)*2,18)
    score+=min((parser.h2+parser.h3)*4,16)
    score+=min(parser.internal*2,10)
    score+=min(interactive*3,12)
    score=round(score)
    threshold=120 if is_tool else 180
    rows.append({
        "route":route,"words":word_count,"p":parser.p,"li":parser.li,
        "heads":parser.h2+parser.h3,"links":parser.internal,
        "interactive":interactive,"score":score,
        "thin": word_count<threshold and score<70
    })

rows.sort(key=lambda x:(x["score"],x["words"]))
thin=[r for r in rows if r["thin"]]
print(f"CONTENT AUDIT: {len(rows)} pages reviewed; {len(thin)} flagged for strengthening")
print("THINNEST PAGES")
for r in rows[:35]:
    flag="THIN" if r["thin"] else "OK"
    print(f"{flag:4} score={r['score']:3} words={r['words']:3} heads={r['heads']:2} links={r['links']:2} ui={r['interactive']:2} {r['route']}")
print("SUMMARY BY BAND")
bands=[(0,49),(50,69),(70,84),(85,1000)]
for lo,hi in bands:
    n=sum(1 for r in rows if lo<=r["score"]<=hi)
    print(f"{lo:02}-{hi if hi<1000 else '100+'}: {n}")
