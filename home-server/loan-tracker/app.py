#!/usr/bin/env python3
"""Loan payoff tracker - tiny stdlib-only server.
Serves the UI and a dumb JSON store. All loan math lives in the frontend;
this process only persists/returns the ledger so there are zero pip deps.
"""
import json, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_FILE = os.environ.get("DATA_FILE", "/data/loan.json")
PORT = int(os.environ.get("PORT", "8080"))
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
_lock = threading.Lock()

# Seeded once on first run. Editable in the UI.
DEFAULT_STATE = {
    "baseline": {
        "date": "2026-06",
        "balance": 3866438,
        "interest_paid": 729662,
        "principal_obligation": 4523772,  # original 40,00,000 + 5,23,772 capitalised
    },
    "rate_annual": 10.4,
    "planned": 100000,
    "entries": [],  # [{"month":"2026-07","rate":10.4,"emi":48316,"prepayment":50000}]
}

def load_state():
    with _lock:
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _save(DEFAULT_STATE)
            return json.loads(json.dumps(DEFAULT_STATE))

def _save(state):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, DATA_FILE)  # atomic

def save_state(state):
    if not isinstance(state, dict) or "baseline" not in state or not isinstance(state.get("entries"), list):
        raise ValueError("bad state shape")
    with _lock:
        _save(state)

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, (bytes, bytearray)) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(INDEX, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, b"index.html missing", "text/plain")
        elif self.path == "/api/state":
            self._send(200, json.dumps(load_state()))
        elif self.path == "/healthz":
            self._send(200, b"ok", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_PUT(self):
        if self.path != "/api/state":
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", 0))
            state = json.loads(self.rfile.read(n) or b"{}")
            save_state(state)
            self._send(200, json.dumps({"ok": True}))
        except (ValueError, json.JSONDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}))

    def log_message(self, *a):  # quiet
        pass

if __name__ == "__main__":
    print(f"loan-tracker on :{PORT}  data={DATA_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()