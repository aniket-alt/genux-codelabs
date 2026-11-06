"""Codelab 06 - MCP Apps host.  The host:
  1. spawns the MCP server (stdio) and runs the MCP handshake
  2. lists tools, sees `_meta.ui.resourceUri`
  3. calls the tool, reads the ui:// resource (text/html;profile=mcp-app)
  4. renders resource in a sandboxed iframe and forwards the tool result with
     a `ui/notifications/tool-result` postMessage  (what a real host like Claude/VS Code does)
Run: python 06_mcp_apps/demo.py
"""
import sys, json, subprocess, pathlib, html as H
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog

class McpClient:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, str(pathlib.Path(__file__).parent / "server.py")],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
        self.n = 0
    def rpc(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}) + "\n")
        self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline())
        if "error" in r: raise RuntimeError(r["error"])
        return r["result"]
    def close(self): self.p.stdin.close(); self.p.wait(timeout=5)

def host_iframe(app_html, tool_result):
    """Sandboxed iframe + bootstrap script that delivers the tool result to the app."""
    boot = ("<script>window.addEventListener('load',()=>postMessage("
            + json.dumps({"jsonrpc": "2.0", "method": "ui/notifications/tool-result", "params": tool_result})
            + ",'*'))</script>")
    csp = "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'\">"
    doc = csp + "<style>" + catalog.CSS + "</style>" + app_html + boot
    return f"<iframe sandbox='allow-scripts' srcdoc=\"{H.escape(doc, quote=True)}\" style='height:260px'></iframe>"

if __name__ == "__main__":
    out = pathlib.Path(__file__).parent.parent / "out"; out.mkdir(exist_ok=True)
    c = McpClient()
    info = c.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "demo-host", "version": "1"}})
    print("connected to", info["serverInfo"]["name"])
    for tool in c.rpc("tools/list")["tools"]:
        uri = tool["_meta"]["ui"]["resourceUri"]
        res = c.rpc("tools/call", {"name": tool["name"], "arguments": {}})
        rsrc = c.rpc("resources/read", {"uri": uri})["contents"][0]
        assert rsrc["mimeType"] == "text/html;profile=mcp-app"
        mode = tool["name"].split("_")[1]
        (out / f"06_{mode}.html").write_text(catalog.page(host_iframe(rsrc["text"], res), mode), encoding="utf-8")
        print(f"[{mode:11}] tool={tool['name']:22} ui={uri:30} html={len(rsrc['text']):4} chars -> out/06_{mode}.html")
    c.close()
