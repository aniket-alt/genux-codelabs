"""Codelab 01 - Foundations: static, declarative, open-ended, mixed.
Run:  python 01_foundations/demo.py      -> writes out/01_*.html
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog, mock_llm

OUT = pathlib.Path(__file__).parent.parent / "out"
OUT.mkdir(exist_ok=True)

# ---- Step 1: STATIC. Components pre-exist; model only selects + fills. ----
TOOLS = {  # tool name -> component node builder
    "show_metric": lambda a: {"component": "Metric", "props": a},
    "show_table":  lambda a: {"component": "Table", "props": a},
}
def static_mode():
    calls = mock_llm.ask("static")
    nodes = [TOOLS[c["name"]](c["arguments"]) for c in calls]   # no layout choice!
    return "".join(catalog.render(n) for n in nodes), len(str(calls))

# ---- Step 2: DECLARATIVE. Model writes the whole tree; we validate. -------
def declarative_mode():
    tree = mock_llm.ask("declarative")
    return catalog.render(tree), len(str(tree))      # render() validates first

# ---- Step 3: OPEN-ENDED. Model writes HTML; host sandboxes it. ------------
def open_mode():
    html = mock_llm.ask("open")
    return catalog.sandbox_iframe(html), len(html)

# ---- Step 4: MIXED. Catalog + a GeneratedView escape hatch. ---------------
def mixed_mode():
    tree = mock_llm.ask("mixed")
    return catalog.render(tree), len(str(tree))

if __name__ == "__main__":
    for name, fn in [("static", static_mode), ("declarative", declarative_mode),
                     ("open", open_mode), ("mixed", mixed_mode)]:
        html, size = fn()
        (OUT / f"01_{name}.html").write_text(catalog.page(html, name), encoding="utf-8")
        print(f"[{name:11}] agent output = {size:5} chars -> out/01_{name}.html")
    # Safety demo: the catalog rejects hallucinated components.
    try:
        catalog.render({"component": "EvilWidget", "props": {}})
    except catalog.CatalogError as e:
        print("[safety     ] rejected:", e)
