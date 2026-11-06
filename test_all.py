"""Run: python -m unittest test_all -v   (no dependencies)"""
import sys, pathlib, importlib.util, unittest, json
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
from common import catalog, mock_llm

def load(rel):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_"), ROOT / rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

class Catalog(unittest.TestCase):
    def test_rejects_unknown_component(self):
        with self.assertRaises(catalog.CatalogError): catalog.render({"component": "X", "props": {}})
    def test_rejects_bad_prop_type(self):
        with self.assertRaises(catalog.CatalogError): catalog.render({"component": "Metric", "props": {"label": 1, "value": "a"}})
    def test_escapes_text(self):
        h = catalog.render({"component": "Text", "props": {"text": "<script>x</script>"}})
        self.assertNotIn("<script>", h)
    def test_open_html_is_sandboxed(self):
        self.assertIn("sandbox=", catalog.sandbox_iframe("<script>alert(1)</script>"))
    def test_all_modes_render(self):
        for m in ("declarative", "mixed"): catalog.render(mock_llm.ask(m))

class A2UI(unittest.TestCase):
    def test_surfaces(self):
        a = load("03_a2ui/demo.py")
        for gen in (a.static_stream, a.declarative_stream, a.open_stream, a.mixed_stream):
            s = a.Surface()
            for m in gen(): s.handle(json.loads(json.dumps(m)))
            self.assertTrue(s.render())
    def test_data_binding(self):
        a = load("03_a2ui/demo.py"); s = a.Surface()
        for m in a.declarative_stream(): s.handle(m)
        self.assertIn("$575", s.render())

class OpenUI(unittest.TestCase):
    def test_roundtrip_matches_json_tree(self):
        o = load("04_openui_lang/demo.py")
        self.assertEqual(o.to_tree(o.parse(o.DECLARATIVE)), mock_llm.ask("declarative"))
    def test_bad_line(self):
        o = load("04_openui_lang/demo.py")
        with self.assertRaises(SyntaxError): o.parse("nonsense")

class JsonRender(unittest.TestCase):
    def test_flatten_roundtrip(self):
        j = load("05_json_render/demo.py"); t = mock_llm.ask("mixed")
        self.assertEqual(j.spec_to_tree(j.tree_to_spec(t)), t)
    def test_patches_rebuild_spec(self):
        j = load("05_json_render/demo.py"); spec = j.tree_to_spec(mock_llm.ask("declarative")); built = {}
        for op in j.spec_to_patches(spec): j.apply(built, op)
        self.assertEqual(built, spec)

class MCP(unittest.TestCase):
    def test_handshake_and_ui_resource(self):
        d = load("06_mcp_apps/demo.py"); c = d.McpClient()
        try:
            c.rpc("initialize")
            tools = c.rpc("tools/list")["tools"]
            self.assertEqual(len(tools), 4)
            r = c.rpc("resources/read", {"uri": tools[0]["_meta"]["ui"]["resourceUri"]})["contents"][0]
            self.assertEqual(r["mimeType"], "text/html;profile=mcp-app")
        finally: c.close()

class Harness(unittest.TestCase):
    def test_agent_loop_emits_ui(self):
        h = load("07_harness_genui/demo.py"); hist = h.run_agent("declarative")
        self.assertEqual(h.UI_EVENTS[-1]["name"], "render_ui")
        self.assertEqual(hist[-1]["role"], "assistant")
    def test_bad_ui_blocked(self):
        h = load("07_harness_genui/demo.py")
        with self.assertRaises(catalog.CatalogError):
            h.tool_render_ui({"mode": "declarative", "payload": {"component": "Script", "props": {}}})

if __name__ == "__main__": unittest.main()
