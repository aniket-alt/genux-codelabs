"""Deterministic stand-in for an LLM so every codelab runs offline.

`ask(mode, prompt)` returns what a real model would emit for the same prompt in
each generation mode. To use a real model, set ANTHROPIC_API_KEY and implement
`real_llm` below; the rest of the code does not change.
"""
import json, os

SALES = [["Classic", 120, "$240"], ["Pink", 80, "$200"], ["Mint", 45, "$135"]]
TOTAL, CUPS = "$575", 245

# ---- mode 1: STATIC -- model picks pre-built components via tool calls -----
def static_tool_calls(prompt):
    return [
        {"name": "show_metric", "arguments": {"label": "Revenue", "value": TOTAL}},
        {"name": "show_metric", "arguments": {"label": "Cups sold", "value": str(CUPS)}},
        {"name": "show_table", "arguments": {"columns": ["Flavor", "Cups", "Revenue"], "rows": SALES}},
    ]

# ---- mode 2: DECLARATIVE -- model writes a layout as a JSON tree -----------
def declarative_tree(prompt):
    return {"component": "Card", "props": {"title": "Lemonade stand", "children": [
        {"component": "Row", "props": {"children": [
            {"component": "Metric", "props": {"label": "Revenue", "value": TOTAL}},
            {"component": "Metric", "props": {"label": "Cups sold", "value": str(CUPS)}}]}},
        {"component": "Table", "props": {"columns": ["Flavor", "Cups", "Revenue"], "rows": SALES}},
        {"component": "Button", "props": {"label": "Restock", "action": "restock"}}]}}

# ---- mode 3: OPEN-ENDED -- model writes raw HTML ---------------------------
def open_html(prompt):
    bars = "".join(f"<div style='background:#f5d90a;height:22px;margin:4px 0;width:{c*2}px'>{n} {c}</div>" for n, c, _ in SALES)
    return f"<div style='font-family:sans-serif'><h3>Lemonade stand: {TOTAL}</h3>{bars}<button onclick=\"parent.postMessage({{action:'restock'}},'*')\">Restock</button></div>"

# ---- mode 4: MIXED -- catalog layout + one GeneratedView for the chart -----
def mixed_tree(prompt):
    t = declarative_tree(prompt)
    t["props"]["children"].insert(1, {"component": "GeneratedView", "props": {"html": open_html(prompt)}})
    return t

def stream(text, size=24):
    """Chunk a string like token streaming would."""
    for i in range(0, len(text), size):
        yield text[i:i + size]

def real_llm(prompt):  # pragma: no cover - optional hook
    raise NotImplementedError("wire your provider here; mock is used by default")

def ask(mode, prompt="Dashboard for a lemonade stand"):
    if os.environ.get("USE_REAL_LLM"): return real_llm(prompt)
    return {"static": static_tool_calls, "declarative": declarative_tree,
            "open": open_html, "mixed": mixed_tree}[mode](prompt)
