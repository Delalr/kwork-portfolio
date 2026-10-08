"""Run tests/behavior.html for each landing in headless Edge. Usage: python tests/run.py [site ...]
The page POSTs its PASS/FAIL lines to /result (msedge.exe detaches, so stdout can't be used)."""
import http.server, queue, subprocess, sys, threading
from pathlib import Path

ROOT = Path(__file__).parent.parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
results = queue.Queue()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def do_POST(self):
        results.put(self.rfile.read(int(self.headers["Content-Length"])).decode())
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
port = server.server_address[1]

sys.stdout.reconfigure(encoding="utf-8")
sites = sys.argv[1:] or sorted(p.parent.name for p in ROOT.glob("*/index.html"))
failed = False
for s in sites:
    # own profile per site: a second launch on a busy profile hands off to the running instance and never loads
    subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", f"--user-data-dir={ROOT / '.edge' / ('test-' + s)}",
                      "--virtual-time-budget=15000", "--dump-dom",
                      f"http://127.0.0.1:{port}/tests/behavior.html?site={s}"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        lines = results.get(timeout=60).splitlines()
    except queue.Empty:
        lines = [f"FAIL {s}: no result in 60s"]
    failed |= not lines or any(l.startswith("FAIL") for l in lines)
    print("\n".join(lines))
sys.exit(failed)
