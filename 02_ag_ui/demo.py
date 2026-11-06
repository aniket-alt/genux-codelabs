"""Codelab 02 - AG-UI: the agent<->user *transport* protocol.

AG-UI is an event stream (SSE) between agent backend and frontend. Events used
here are the real AG-UI names: RUN_STARTED, TEXT_MESSAGE_START/CONTENT/END,
TOOL_CALL_START/ARGS/END, STATE_SNAPSHOT, STATE_DELTA (JSON Patch), RUN_FINISHED.

Run: python 02_ag_ui/demo.py   (starts a local SSE server, consumes it with a client)
"""
import sys, json, pathlib, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog, mock_llm

def sse(ev): return f"data: {json.dumps(ev)}\n\n".encode()

# ---------------- agent: yields AG-UI events for each mode ------------------
def agent_run(mode):
    yield {"type": "RUN_STARTED", "threadId": "t1", "runId": "r1"}
    yield {"type": "TEXT_MESSAGE_START", "messageId": "m1", "role": "assistant"}
    for c in mock_llm.stream("Building your lemonade dashboard...", 12):
        yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m1", "delta": c}
    yield {"type": "TEXT_MESSAGE_END", "messageId": "m1"}
    if mode == "static":              # UI via TOOL CALLS -> frontend renders pre-built components
        for i, call in enumerate(mock_llm.ask("static")):
            yield {"type": "TOOL_CALL_START", "toolCallId": f"c{i}", "toolCallName": call["name"]}
            yield {"type": "TOOL_CALL_ARGS", "toolCallId": f"c{i}", "delta": json.dumps(call["arguments"])}
            yield {"type": "TOOL_CALL_END", "toolCallId": f"c{i}"}
    elif mode in ("declarative", "mixed"):   # UI via SHARED STATE: snapshot then JSON-Patch deltas
        tree = mock_llm.ask(mode)
        yield {"type": "STATE_SNAPSHOT", "snapshot": {"ui": None}}
        yield {"type": "STATE_DELTA", "delta": [{"op": "replace", "path": "/ui", "value": tree}]}
    elif mode == "open":              # UI via an HTML message the host sandboxes
        yield {"type": "STATE_DELTA", "delta": [{"op": "add", "path": "/html", "value": mock_llm.ask("open")}]}
    yield {"type": "RUN_FINISHED", "threadId": "t1", "runId": "r1"}

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        mode = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["mode"]
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
        for ev in agent_run(mode): self.wfile.write(sse(ev)); self.wfile.flush()
    def log_message(self, *a): pass

# ---------------- client: folds events into UI -----------------------------
def apply_patch(state, ops):
    for op in ops:           # minimal RFC-6902: add/replace at top-level key
        state[op["path"].lstrip("/")] = op["value"]

def run_client(port, mode):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/", json.dumps({"mode": mode}).encode(),
                                 {"Content-Type": "application/json"})
    state, html, text, kinds = {}, "", "", []
    with urllib.request.urlopen(req) as r:
        for line in r:
            if not line.startswith(b"data: "): continue
            ev = json.loads(line[6:]); kinds.append(ev["type"]); t = ev["type"]
            if t == "TEXT_MESSAGE_CONTENT": text += ev["delta"]
            elif t == "TOOL_CALL_ARGS":
                args = json.loads(ev["delta"])
                node = {"component": "Metric" if "value" in args else "Table", "props": args}
                html += catalog.render(node)
            elif t in ("STATE_SNAPSHOT",): state = dict(ev["snapshot"])
            elif t == "STATE_DELTA": apply_patch(state, ev["delta"])
    if state.get("ui"): html = catalog.render(state["ui"])
    if state.get("html"): html = catalog.sandbox_iframe(state["html"])
    return text, html, kinds

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    out = pathlib.Path(__file__).parent.parent / "out"; out.mkdir(exist_ok=True)
    for mode in ["static", "declarative", "open", "mixed"]:
        text, html, kinds = run_client(port, mode)
        (out / f"02_{mode}.html").write_text(catalog.page(html, mode), encoding="utf-8")
        print(f"[{mode:11}] chat='{text}'\n              events={len(kinds)}: {' '.join(dict.fromkeys(kinds))}")
    srv.shutdown()
