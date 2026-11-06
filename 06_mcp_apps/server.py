"""A minimal MCP server (JSON-RPC 2.0 over stdio, newline-delimited) with MCP Apps.

MCP Apps = tools that declare `_meta.ui.resourceUri` pointing to a `ui://` resource
whose mimeType is `text/html;profile=mcp-app`. The host fetches that resource via
`resources/read` and renders it in a sandboxed iframe, then pushes the tool result in.
No SDK needed: the protocol is just JSON-RPC.
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog, mock_llm

MIME = "text/html;profile=mcp-app"

# The generic app shell used for STATIC and DECLARATIVE modes. It receives the
# tool result from the host via postMessage and fills itself in.
SHELL = """<div id=app style='font-family:sans-serif'>loading...</div>
<script>
addEventListener('message', e => {
  const m = e.data; if (m.method !== 'ui/notifications/tool-result') return;
  const d = m.params.structuredContent;
  document.getElementById('app').innerHTML =
    '<h3>'+d.title+'</h3><p>Revenue: <b>'+d.revenue+'</b> &middot; Cups: <b>'+d.cups+'</b></p>' +
    '<button onclick="parent.postMessage({jsonrpc:\\'2.0\\',method:\\'tools/call\\',params:{name:\\'restock\\'}},\\'*\\')">Restock</button>';
});
</script>"""

TOOLS = [
    {"name": "lemonade_static", "description": "Static: fixed HTML app, tool returns data only",
     "inputSchema": {"type": "object", "properties": {}}, "_meta": {"ui": {"resourceUri": "ui://lemonade/static.html"}}},
    {"name": "lemonade_declarative", "description": "Declarative: tool returns a catalog spec; host-side renderer draws it",
     "inputSchema": {"type": "object", "properties": {}}, "_meta": {"ui": {"resourceUri": "ui://lemonade/declarative.html"}}},
    {"name": "lemonade_open", "description": "Open-ended: the app HTML itself is model-generated",
     "inputSchema": {"type": "object", "properties": {}}, "_meta": {"ui": {"resourceUri": "ui://lemonade/open.html"}}},
    {"name": "lemonade_mixed", "description": "Mixed: catalog layout with a generated view embedded",
     "inputSchema": {"type": "object", "properties": {}}, "_meta": {"ui": {"resourceUri": "ui://lemonade/mixed.html"}}},
]

def resource_html(uri):
    mode = uri.rsplit("/", 1)[1].removesuffix(".html")
    if mode == "static": return SHELL
    if mode == "declarative": return catalog.render(mock_llm.ask("declarative"))
    if mode == "open": return mock_llm.ask("open")
    if mode == "mixed": return catalog.render(mock_llm.ask("mixed"))
    raise KeyError(uri)

def call_tool(name):
    data = {"title": "Lemonade stand", "revenue": mock_llm.TOTAL, "cups": mock_llm.CUPS}
    return {"content": [{"type": "text", "text": f"Revenue {mock_llm.TOTAL}, {mock_llm.CUPS} cups"}],
            "structuredContent": data}

def handle(req):
    m, p = req.get("method"), req.get("params", {})
    if m == "initialize":
        return {"protocolVersion": "2025-06-18", "serverInfo": {"name": "lemonade-apps", "version": "1.0"},
                "capabilities": {"tools": {}, "resources": {}}}
    if m == "tools/list": return {"tools": TOOLS}
    if m == "tools/call": return call_tool(p["name"])
    if m == "resources/list":
        return {"resources": [{"uri": t["_meta"]["ui"]["resourceUri"], "name": t["name"], "mimeType": MIME} for t in TOOLS]}
    if m == "resources/read":
        return {"contents": [{"uri": p["uri"], "mimeType": MIME, "text": resource_html(p["uri"])}]}
    raise KeyError(m)

if __name__ == "__main__":
    for line in sys.stdin:
        req = json.loads(line)
        if "id" not in req: continue          # notifications need no reply
        try: resp = {"jsonrpc": "2.0", "id": req["id"], "result": handle(req)}
        except Exception as e: resp = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": str(e)}}
        sys.stdout.write(json.dumps(resp) + "\n"); sys.stdout.flush()
