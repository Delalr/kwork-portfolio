"""Screenshot each landing (desktop + mobile) with headless Edge and build a portfolio image.
Usage: python shots.py [site ...]   (default: every folder with index.html)
Output: shots/<site>-desktop.png, shots/<site>-mobile.png, shots/<site>-portfolio.png
"""
import subprocess, sys, time
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = ROOT / "shots"
BG = (236, 239, 243)


def shoot(page: Path, out: Path, width: int, height: int, scale: int):
    out.unlink(missing_ok=True)
    subprocess.run([
        EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--user-data-dir={ROOT / '.edge'}",  # keep Edge profile on E:
        f"--window-size={width},{height}", f"--force-device-scale-factor={scale}",
        "--virtual-time-budget=10000", f"--screenshot={out}", page.as_uri(),
    ], check=True, capture_output=True)
    # msedge.exe hands off to a background process and returns before the file is written
    for _ in range(60):
        if out.exists() and out.stat().st_size:
            time.sleep(1)
            break
        time.sleep(1)
    trim(out)


def trim(path: Path):
    # ponytail: window is taller than the page; cut the uniform background below the footer
    img = Image.open(path).convert("RGB")
    px, (w, h) = img.load(), img.size
    last = px[w // 2, h - 1]
    y = h - 1
    while y > 0 and all(px[x, y] == last for x in range(0, w, 7)):
        y -= 1
    img.crop((0, 0, w, min(h, y + 40))).save(path)


def compose(desktop: Path, mobile: Path, out: Path):
    d, m = Image.open(desktop), Image.open(mobile)
    d = d.resize((1100, round(d.height * 1100 / d.width)), Image.LANCZOS)
    m = m.resize((300, round(m.height * 300 / m.width)), Image.LANCZOS)
    m = m.crop((0, 0, 300, min(m.height, d.height)))
    pad = 40
    canvas = Image.new("RGB", (pad * 3 + d.width + m.width, pad * 2 + d.height), BG)
    canvas.paste(d, (pad, pad))
    canvas.paste(m, (pad * 2 + d.width, pad))
    canvas.save(out, optimize=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    sites = sys.argv[1:] or sorted(p.parent.name for p in ROOT.glob("*/index.html"))
    for s in sites:
        page = ROOT / s / "index.html"
        d, m = OUT / f"{s}-desktop.png", OUT / f"{s}-mobile.png"
        shoot(page, d, 1440, 7000, 1)
        shoot(page, m, 500, 9000, 2)  # headless Edge won't go narrower than ~500px
        compose(d, m, OUT / f"{s}-portfolio.png")
        # link preview (og:image): top of the desktop shot at 1200×630
        Image.open(d).crop((0, 0, 1440, 756)).resize((1200, 630), Image.LANCZOS).convert("RGB").save(OUT / f"{s}-og.jpg", quality=85, optimize=True)
        print("ok", s)
