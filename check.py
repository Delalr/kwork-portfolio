"""Audit every landing against the review checklist. Usage: python check.py [site ...]
Exit code 1 if anything fails. Needs node (validates pattern= attributes the way browsers do, with the v flag)."""
import json, re, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent

MUST_CONTAIN = {
    "viewport meta": 'name="viewport"',
    "meta description": 'name="description"',
    "og:title": 'property="og:title"',
    "og:description": 'property="og:description"',
    "og:image": 'property="og:image"',
    "favicon": 'rel="icon"',
    "schema.org JSON-LD": 'application/ld+json',
    "scroll-margin under sticky header": "scroll-margin-top",
    "reduced motion": "prefers-reduced-motion",
    "content visible without JS": ".js .reveal",
    "js class set in head": "classList.add('js')",
    "burger aria-expanded": "aria-expanded",
    "burger aria-controls": "aria-controls",
    "clickable phone": 'href="tel:',
    "demo disclaimer": "Демо-проект",
    "fonts.gstatic preconnect": "https://fonts.gstatic.com",
}


def check(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    errors = [f"missing {name}" for name, needle in MUST_CONTAIN.items() if needle not in html]

    ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    try:
        ld and json.loads(ld.group(1))
    except ValueError as e:
        errors.append(f"broken JSON-LD: {e}")

    # form controls need an accessible name: aria-label or a wrapping <label>
    body = re.sub(r"<label\b.*?</label>", "", html, flags=re.S)
    for tag in re.findall(r"<(?:input|select|textarea)\b[^>]*>", body):
        if "aria-label" not in tag and 'type="hidden"' not in tag:
            errors.append(f"control without label: {tag[:70]}")

    for tag in re.findall(r"<img\b[^>]*>", html):
        if 'alt="' not in tag:
            errors.append(f"img without alt: {tag[:70]}")
    for tag in re.findall(r'<a\b[^>]*target="_blank"[^>]*>', html):
        if "noopener" not in tag:
            errors.append(f"target=_blank without rel=noopener: {tag[:70]}")

    if 'type="date"' in html and ".min =" not in html:
        errors.append("date input without min (past dates allowed)")
    if "new Date().toISOString()" in html:
        errors.append("date from toISOString() is UTC — yesterday until 03:00 MSK; shift by getTimezoneOffset()")
    if 'role="tab"' in html and "aria-selected" not in html:
        errors.append("tabs without aria-selected")

    # a photo shown as <img> must not repeat anywhere else on the page (hero CSS may repeat its own id)
    # (srcset repeats the id inside the same <img>, so count each id once per tag)
    ids = Counter(pid for tag in re.findall(r"<img\b[^>]*>|url\([^)]*\)", html)
                  for pid in set(re.findall(r"photo-([\w-]+)\?", tag)))
    for pid in {p for tag in re.findall(r"<img\b[^>]*>", html) for p in re.findall(r"photo-([\w-]+)\?", tag)}:
        if ids[pid] > 1:
            errors.append(f"photo used twice: {pid}")

    patterns = re.findall(r'pattern="([^"]+)"', html)
    if patterns:
        js = "for (const p of %s) { try { new RegExp('^(?:' + p + ')$', 'v') } catch (e) { console.log(p) } }" % json.dumps(patterns)
        bad = subprocess.run(["node", "-e", js], capture_output=True, text=True).stdout.split()
        errors += [f"pattern invalid in browsers (v-flag): {p}" for p in bad]
    return errors


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    paths = [Path(a) if a.endswith(".html") else ROOT / a / "index.html" for a in sys.argv[1:]] \
        or sorted(ROOT.glob("*/index.html"))
    failed = False
    for p in paths:
        errs = check(p)
        failed |= bool(errs)
        print(f"{'FAIL' if errs else 'ok  '} {p.parent.name}" + "".join(f"\n     - {e}" for e in errs))
    sys.exit(failed)
