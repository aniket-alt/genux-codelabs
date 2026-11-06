"""Codelab 03 - A2UI: declarative UI *as data* sent agent -> client.

A2UI messages (JSONL stream), modelled on the A2UI v0.8 spec:
  surfaceUpdate    {surfaceId, components:[{id, component:{Type:{props}}}]}   flat list, refs by id
  dataModelUpdate  {surfaceId, contents:[{key,valueString|valueMap...}]}      data separate from layout
  beginRendering   {surfaceId, root}                                          go signal
Props may be literal ({"literalString":..}) or bound ({"path":"/revenue"}).
Flat + ids => the client can render as chunks arrive and the LLM can patch one component.

Run: python 03_a2ui/demo.py
"""
import sys, json, pathlib
from html import escape
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog, mock_llm

# ---------------- the A2UI client: a surface = components + data -----------
class Surface:
    def __init__(self): self.components, self.data, self.root = {}, {}, None
    def handle(self, msg):
        if "surfaceUpdate" in msg:
            for c in msg["surfaceUpdate"]["components"]: self.components[c["id"]] = c["component"]
        elif "dataModelUpdate" in msg:
            for kv in msg["dataModelUpdate"]["contents"]: self.data[kv["key"]] = kv["value"]
        elif "beginRendering" in msg: self.root = msg["beginRendering"]["root"]
    def val(self, v):                       # resolve literal or bound value
        if "literalString" in v: return v["literalString"]
        return str(self.data.get(v["path"].lstrip("/"), ""))
    def render(self, cid=None):
        cid = cid or self.root
        (kind, p), = self.components[cid].items()
        kids = "".join(self.render(k) for k in p.get("children", {}).get("explicitList", []))
        if kind == "Text":   return f"<p>{escape(self.val(p['text']))}</p>"
        if kind == "Metric": return f"<div class='card metric'><span>{escape(self.val(p['label']))}</span><b>{escape(self.val(p['value']))}</b></div>"
        if kind == "Column": return f"<div>{kids}</div>"
        if kind == "Row":    return f"<div class='row'>{kids}</div>"
        if kind == "Card":   return f"<div class='card'>{kids}</div>"
        if kind == "Button": return f"<button data-action='{escape(p['action'])}'>{escape(self.val(p['label']))}</button>"
        if kind == "Html":   return catalog.sandbox_iframe(p["html"])        # custom catalog entry
        raise ValueError(f"component {kind!r} not in negotiated catalog")

def lit(s): return {"literalString": s}
def comp(i, kind, **p): return {"surfaceUpdate": {"surfaceId": "s1", "components": [{"id": i, "component": {kind: p}}]}}

# ---------------- agent side: produce the message stream -------------------
def static_stream():
    """Static: template surface fixed in advance; agent only sends DATA."""
    yield from template_layout()
    yield {"dataModelUpdate": {"surfaceId": "s1", "contents": [
        {"key": "revenue", "value": mock_llm.TOTAL}, {"key": "cups", "value": str(mock_llm.CUPS)}]}}
    yield {"beginRendering": {"surfaceId": "s1", "root": "root"}}

def template_layout():
    yield comp("rev", "Metric", label=lit("Revenue"), value={"path": "/revenue"})
    yield comp("cup", "Metric", label=lit("Cups sold"), value={"path": "/cups"})
    yield comp("row", "Row", children={"explicitList": ["rev", "cup"]})
    yield comp("root", "Column", children={"explicitList": ["row"]})

def declarative_stream():
    """Declarative: the model designs the layout AND sends data; order is free."""
    yield comp("t", "Text", text=lit("Lemonade stand, today"))
    yield comp("rev", "Metric", label=lit("Revenue"), value={"path": "/revenue"})
    yield comp("cup", "Metric", label=lit("Cups sold"), value={"path": "/cups"})
    yield comp("go", "Button", label=lit("Restock"), action="restock")
    yield comp("row", "Row", children={"explicitList": ["rev", "cup"]})
    yield comp("root", "Card", children={"explicitList": ["t", "row", "go"]})
    yield {"beginRendering": {"surfaceId": "s1", "root": "root"}}       # render early; data follows!
    yield {"dataModelUpdate": {"surfaceId": "s1", "contents": [
        {"key": "revenue", "value": mock_llm.TOTAL}, {"key": "cups", "value": str(mock_llm.CUPS)}]}}

def open_stream():
    """Open-ended: a custom 'Html' component the client opted into (sandboxed)."""
    yield comp("v", "Html", html=mock_llm.ask("open"))
    yield {"beginRendering": {"surfaceId": "s1", "root": "v"}}

def mixed_stream():
    yield from declarative_stream()
    yield comp("chart", "Html", html=mock_llm.ask("open"))
    yield comp("root", "Card", children={"explicitList": ["t", "row", "chart", "go"]})  # re-send root = in-place patch

if __name__ == "__main__":
    out = pathlib.Path(__file__).parent.parent / "out"; out.mkdir(exist_ok=True)
    for name, gen in [("static", static_stream), ("declarative", declarative_stream),
                      ("open", open_stream), ("mixed", mixed_stream)]:
        s, n = Surface(), 0
        lines = [json.dumps(m) for m in gen()]          # JSONL on the wire
        for line in lines: s.handle(json.loads(line)); n += 1
        (out / f"03_{name}.html").write_text(catalog.page(s.render(), name), encoding="utf-8")
        (out / f"03_{name}.jsonl").write_text("\n".join(lines), encoding="utf-8")
        print(f"[{name:11}] {n} messages, {sum(map(len, lines))} bytes -> out/03_{name}.html (+ .jsonl)")
