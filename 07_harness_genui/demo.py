"""Codelab 07 - Harness integration: GenUI as a tool of a coding/agent harness.

A harness is the loop  model -> tool calls -> results -> model ...  plus
permissions and a UI channel. Generative UI plugs in as ONE MORE TOOL:
`render_ui(mode, payload)`. The harness validates the payload (catalog / sandbox
rules), then emits a UI event for the frontend; the model gets a short ack, not the HTML.

Run: python 07_harness_genui/demo.py
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog, mock_llm

# ---------------- harness tools ---------------------------------------------
def tool_read_sales(_args):
    return json.dumps({"total": mock_llm.TOTAL, "cups": mock_llm.CUPS, "by_flavor": mock_llm.SALES})

UI_EVENTS = []          # what the frontend (AG-UI stream) would receive

def tool_render_ui(args):
    mode, payload = args["mode"], args["payload"]
    if mode == "declarative":   html = catalog.render(payload)                  # validated tree
    elif mode == "open":        html = catalog.sandbox_iframe(payload)          # sandboxed
    elif mode == "mixed":       html = catalog.render(payload)                  # tree w/ GeneratedView
    else: raise ValueError(f"unknown mode {mode}")
    UI_EVENTS.append({"type": "CUSTOM", "name": "render_ui", "mode": mode, "html": html})
    return f"rendered {mode} UI ({len(html)} bytes)"      # tiny ack keeps context small

TOOLS = {"read_sales": tool_read_sales, "render_ui": tool_render_ui}
PERMISSIONS = {"read_sales": "allow", "render_ui": "allow"}     # a real harness would ask the user

# ---------------- scripted "model": decides tool calls per turn -------------
def model(mode, history):
    """Stands in for the LLM. Turn 1: gather data. Turn 2: render. Turn 3: answer."""
    tool_msgs = [h for h in history if h["role"] == "tool"]
    if not tool_msgs:
        return {"tool": "read_sales", "args": {}}
    if len(tool_msgs) == 1:
        payload = mock_llm.ask(mode)
        return {"tool": "render_ui", "args": {"mode": mode, "payload": payload}}
    return {"text": "I've drawn the dashboard above."}

def run_agent(mode, user="Show me today's lemonade sales"):
    history, UI_EVENTS[:] = [{"role": "user", "content": user}], []
    for step in range(5):                                     # step budget
        act = model(mode, history)
        if "text" in act:
            history.append({"role": "assistant", "content": act["text"]}); break
        if PERMISSIONS.get(act["tool"]) != "allow": raise PermissionError(act["tool"])
        result = TOOLS[act["tool"]](act["args"])
        history.append({"role": "tool", "name": act["tool"], "content": result})
        print(f"   step {step+1}: {act['tool']:10} -> {result[:60]}")
    return history

if __name__ == "__main__":
    out = pathlib.Path(__file__).parent.parent / "out"; out.mkdir(exist_ok=True)
    for mode in ["declarative", "open", "mixed"]:
        print(f"[{mode}]")
        h = run_agent(mode)
        (out / f"07_{mode}.html").write_text(catalog.page(UI_EVENTS[-1]["html"], mode), encoding="utf-8")
        print(f"   final: {h[-1]['content']}  -> out/07_{mode}.html")
    # static mode in a harness = fixed components behind separate tools (no render_ui needed)
    print("[static]\n   step 1: show_metric/show_table tools (see 01_foundations static_mode)")
    # safety: a hallucinated component never reaches the screen
    try: tool_render_ui({"mode": "declarative", "payload": {"component": "Script", "props": {}}})
    except catalog.CatalogError as e: print("[safety] blocked:", e)
