"""Codelab 05 - json-render: guardrailed generative UI from a typed catalog.

Mechanism (as in Vercel's json-render):
  1. Developer defines a CATALOG: component name -> prop schema + allowed actions.
  2. The catalog is turned into a JSON Schema / prompt for the model.
  3. Model emits a flat SPEC  {root, elements:{id:{type, props, children}}}
     -- either whole, or as a stream of JSON-Patch ops that build it up.
  4. Client validates each element against the catalog, renders, and routes
     button presses to developer-registered ACTION handlers (model can't invent code).

Run: python 05_json_render/demo.py
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog, mock_llm

# ---- 1. catalog: types + allowed actions ----------------------------------
ACTIONS = {"restock": lambda state: state.update(stock=state["stock"] + 50) or "stock +50"}

def catalog_json_schema():
    """Step 2: what you would paste into the system prompt / structured-output API."""
    return {"type": "object", "properties": {"root": {"type": "string"}, "elements": {"type": "object",
            "additionalProperties": {"type": "object", "properties": {
                "type": {"enum": [c for c in catalog.CATALOG if c != "GeneratedView"]},
                "props": {"type": "object"}, "children": {"type": "array", "items": {"type": "string"}}},
                "required": ["type"]}}}}

# ---- 3. spec <-> tree ------------------------------------------------------
def tree_to_spec(tree):
    """Flatten the nested mock tree into json-render's flat element map."""
    elements, n = {}, [0]
    def walk(node):
        n[0] += 1; eid = f"el{n[0]}"
        props = dict(node["props"]); kids = [walk(k) for k in props.pop("children", [])]
        elements[eid] = {"type": node["component"], "props": props, "children": kids}
        return eid
    return {"root": walk(tree), "elements": elements}

def spec_to_tree(spec, eid=None):
    el = spec["elements"][eid or spec["root"]]
    props = dict(el["props"])
    if el["children"] or el["type"] in ("Card", "Row"):
        props["children"] = [spec_to_tree(spec, c) for c in el["children"]]
    return {"component": el["type"], "props": props}

def spec_to_patches(spec):
    """Streaming form: JSON-Patch ops, root first so the client can start immediately."""
    yield {"op": "add", "path": "/root", "value": spec["root"]}
    yield {"op": "add", "path": "/elements", "value": {}}
    for eid, el in spec["elements"].items():
        yield {"op": "add", "path": f"/elements/{eid}", "value": el}

def apply(spec, op):
    parts = [p for p in op["path"].split("/") if p]
    tgt = spec
    for p in parts[:-1]: tgt = tgt[p]
    tgt[parts[-1]] = op["value"]

def renderable(spec):
    """Elements whose children have all arrived (what a streaming client can draw)."""
    try: spec_to_tree(spec); return True
    except KeyError: return False

if __name__ == "__main__":
    out = pathlib.Path(__file__).parent.parent / "out"; out.mkdir(exist_ok=True)
    print("catalog schema keys:", list(catalog_json_schema()["properties"]["elements"]["additionalProperties"]["properties"]["type"]["enum"]))

    # MODE static: fixed spec skeleton, model fills props only
    static = {"root": "r", "elements": {"r": {"type": "Row", "props": {}, "children": ["a", "b"]},
        "a": {"type": "Metric", "props": {"label": "Revenue", "value": mock_llm.TOTAL}, "children": []},
        "b": {"type": "Metric", "props": {"label": "Cups sold", "value": str(mock_llm.CUPS)}, "children": []}}}
    # MODE declarative / mixed: model writes the spec
    declarative = tree_to_spec(mock_llm.ask("declarative"))
    mixed = tree_to_spec(mock_llm.ask("mixed"))
    # MODE open-ended: single GeneratedView element
    openm = tree_to_spec({"component": "GeneratedView", "props": {"html": mock_llm.ask("open")}})

    for name, spec in [("static", static), ("declarative", declarative), ("open", openm), ("mixed", mixed)]:
        (out / f"05_{name}.html").write_text(catalog.page(catalog.render(spec_to_tree(spec)), name), encoding="utf-8")
        print(f"[{name:11}] {len(spec['elements'])} elements -> out/05_{name}.html")

    # streaming patches: show when the client can first paint
    spec, first = {}, None
    ops = list(spec_to_patches(declarative))
    for i, op in enumerate(ops, 1):
        apply(spec, op)
        if first is None and "elements" in spec and renderable(spec) and len(spec["elements"]) == len(declarative["elements"]):
            first = i
    print(f"streamed {len(ops)} patch ops; full tree paintable after op {first}")

    # actions: button click -> developer handler, never model code
    state = {"stock": 10}
    btn = next(e for e in declarative["elements"].values() if e["type"] == "Button")
    print("click Button ->", btn["props"]["action"], "=>", ACTIONS[btn["props"]["action"]](state), state)
    try: ACTIONS["rm_rf"](state)
    except KeyError: print("model-invented action 'rm_rf' -> blocked (not in catalog actions)")
