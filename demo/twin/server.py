"""Local web server for the virtual table: the page in ``static/`` talks to ``engine.Twin`` over JSON.

Standard library only (works the same on Windows, macOS and Linux). Runs on the presenting laptop:

    python -m demo.twin                              # newest recording in data/demo_store, opens the browser
    python -m demo.twin --run data/demo_store/runs/S2_bag
    python -m demo.twin --parser rules --port 8600 --no-browser

API (all JSON): GET /api/state, /api/source, /api/sources; POST /api/move {name,x,y}, /api/hide {name},
/api/show {name}, /api/rotate {name,degrees}, /api/wait {frames}, /api/ask {question},
/api/preset {id}, /api/planner {planner}, /api/reset, /api/load {run}.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from demo.twin import engine  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
mimetypes.add_type("application/javascript", ".js")


class App:
    def __init__(self, run=None, parser="auto", planner=None, workdir=None):
        self.parser, self.planner, self.workdir = parser, planner, workdir
        self.twin = engine.Twin(run, parser=parser, planner=planner, workdir=workdir)
        self.swap_lock = threading.Lock()

    def load(self, run: str):
        allowed = {p.as_posix(): p for p in engine.find_runs()}
        if run not in allowed:
            raise ValueError(f"unknown recording {run!r}")
        with self.swap_lock:
            self.twin = engine.Twin(allowed[run], parser=self.parser, planner=self.planner, workdir=self.workdir)
        return self.twin.state()

    def sources(self):
        cur = self.twin.source["run"].resolve()
        return [{"run": p.as_posix(), "name": p.name, "current": p.resolve() == cur} for p in engine.find_runs()]

    def post(self, route: str, body: dict):
        t = self.twin
        if route == "move":
            return t.move(body["name"], float(body["x"]), float(body["y"]))
        if route == "hide":
            return t.hide(body["name"])
        if route == "show":
            return t.show(body["name"])
        if route == "rotate":
            return t.rotate(body["name"], float(body.get("degrees", 45)))
        if route == "wait":
            return t.wait(int(body.get("frames", 1)))
        if route == "ask":
            return t.ask(str(body.get("question", "")))
        if route == "preset":
            return t.run_preset(str(body["id"]))
        if route == "planner":
            return t.set_planner(str(body["planner"]))
        if route == "reset":
            t.reset()
            return t.state()
        if route == "load":
            return self.load(str(body["run"]))
        raise KeyError(route)


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):   # keep the console readable during the demo
            if "/api/" in (args[0] if args else "") and "GET" not in (args[0] if args else ""):
                sys.stderr.write("[twin] " + (fmt % args) + "\n")

        def _send(self, code: int, data, ctype="application/json"):
            body = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?")[0]
            try:
                if path == "/api/state":
                    return self._send(200, app.twin.state())
                if path == "/api/source":
                    return self._send(200, app.twin.source_info())
                if path == "/api/sources":
                    return self._send(200, app.sources())
                rel = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
                f = (STATIC / rel).resolve()
                if STATIC.resolve() not in f.parents or not f.is_file():
                    return self._send(404, {"error": "not found"})
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                if ctype.startswith("text/") or ctype.endswith("javascript"):
                    ctype += "; charset=utf-8"
                return self._send(200, f.read_bytes(), ctype)
            except Exception as e:  # pragma: no cover - shown in the page
                traceback.print_exc()
                return self._send(500, {"error": f"{type(e).__name__}: {e}"})

        def do_POST(self):
            route = self.path.split("?")[0].removeprefix("/api/")
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                return self._send(200, app.post(route, body))
            except (ValueError, KeyError) as e:
                return self._send(400, {"error": str(e).strip("'\"")})
            except Exception as e:
                traceback.print_exc()
                return self._send(500, {"error": f"{type(e).__name__}: {e}"})

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default=None, help="pipeline run folder (default: newest in data/demo_store/runs)")
    ap.add_argument("--parser", choices=["auto", "ollama", "rules"], default="auto")
    ap.add_argument("--planner", choices=["straight", "detour"], default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8600)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--max-frames", type=int, default=40, help="frames replayed per imported bag")
    ap.add_argument("recording", nargs="?", default=None,
                    help="optional: a recording to import first (folder with the bag + S3 output, a .zip or a .db3); "
                         "on Windows, drag the folder onto G1_Twin.bat")
    a = ap.parse_args(argv)
    run = a.run
    if a.recording:
        from demo import runs as store

        src_path = Path(a.recording).expanduser()
        if not src_path.exists():
            sys.exit(f"[twin] not found: {src_path}")
        print(f"[twin] importing {src_path.name}: S1 replay + S3 masks -> S2 -> S6 -> S4 -> S5 -> S6 "
              "(a few minutes for a long bag) ...", flush=True)
        last = [-1]

        def progress(msg, frac):
            pct = int(frac * 100)
            if pct >= last[0] + 5 or frac >= 1:
                last[0] = pct
                print(f"  [{pct:3d}%] {msg}", flush=True)

        try:
            names = store.import_and_run(src_path, parser=a.parser, max_frames=a.max_frames, progress=progress)
        except Exception as e:
            msg = str(e)
            if "Application Control" in msg or "DLL load failed" in msg:
                hint = ("Windows blocked a program library (usually Smart App Control: Windows Security -> "
                        "App & browser control). See docs/demo/TWIN.md, 'Windows blocks a file'.")
            elif "S3" in msg or "observation" in msg:
                hint = ("The recording needs S3's output (observation.json + masks, unzipped) next to the bag; "
                        "see docs/demo/TWIN.md.")
            else:
                hint = "See docs/demo/TWIN.md."
            sys.exit(f"[twin] import failed: {msg}\n       {hint}")
        for warn in store.LAST_ERRORS:
            print(f"[twin] note: {warn}", flush=True)
        run = store.RUNS / names[0]
        print(f"[twin] imported: {', '.join(names)}", flush=True)
    print("[twin] building the virtual table from the recording ...", flush=True)
    app = App(run, a.parser, a.planner)
    src = app.twin.source
    print(f"[twin] recording: {src['name']} ({len(src['objects'])} objects, frame {src['frame']}) - "
          f"S5 parser: {app.twin.pipe.parser}", flush=True)
    server = ThreadingHTTPServer((a.host, a.port), make_handler(app))
    url = f"http://{a.host}:{a.port}/"
    print(f"[twin] open {url}   (Ctrl+C to stop)", flush=True)
    if not a.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[twin] stopped")


if __name__ == "__main__":
    main()
