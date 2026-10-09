from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PUB_ID = "ca-pub-4228902685584187"
SNIPPET = '''<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4228902685584187"
     crossorigin="anonymous"></script>'''

changed = []
skipped = 0
missing_head = []

for path in ROOT.rglob("*.html"):
    if ".git" in path.parts or "_site" in path.parts:
        continue
    text = path.read_text(encoding="utf-8")
    if PUB_ID in text:
        skipped += 1
        continue
    m = re.search(r"<head(?:\s[^>]*)?>", text, flags=re.I)
    if not m:
        missing_head.append(path.relative_to(ROOT).as_posix())
        continue
    text = text[:m.end()] + "\n" + SNIPPET + text[m.end():]
    path.write_text(text, encoding="utf-8")
    changed.append(path.relative_to(ROOT).as_posix())

ads = ROOT / "ads.txt"
ads_text = "google.com, pub-4228902685584187, DIRECT, f08c47fec0942fa0\n"
if not ads.exists() or ads.read_text(encoding="utf-8") != ads_text:
    ads.write_text(ads_text, encoding="utf-8")
    changed.append("ads.txt")

print(f"AdSense rollout: {len(changed)} files changed, {skipped} HTML files already contained the publisher ID")
if missing_head:
    print("HTML files without <head>:")
    for item in missing_head:
        print(" -", item)
    raise SystemExit(1)
