"""Codelab 04 - OpenUI Lang: a compact, line-oriented UI language for LLMs.

Idea: JSON is token-heavy and brittle when streamed. OpenUI Lang is a terse
assignment-style language -- one statement per line, `id = Component(args)`
-- where references to later ids are allowed, so the UI can stream top-down.

    root = Card("Lemonade stand", [row, tbl])
    row  = Row([m1, m2])
    m1   = Metric("Revenue", "$575")

We write the parser and renderer from scratch (this file) to show the mechanism.
Run: python 04_openui_lang/demo.py
"""
import sys, json, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common import catalog, mock_llm

LINE = re.compile(r"^(\w+)\s*=\s*(\w+)\((.*)\)\s*$")

TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[A-Za-z_]\w*|.', re.S)

def quote_refs(raw):
    """Copy string literals verbatim; turn bare identifiers (refs) into "@id" strings."""
    out = []
    for t in TOKEN.findall(raw):
        out.append(f'"@{t}"' if re.fullmatch(r"[A-Za-z_]\w*", t) and t not in ("true", "false", "null") else t)
    return "".join(out)

def parse(src):
    """Lines -> {id: (Component, [args])}. Args are JSON values or bare identifiers."""
    stmts = {}
    for n, line in enumerate(src.strip().splitlines(), 1):
        m = LINE.match(line.strip())
        if not m: raise SyntaxError(f"line {n}: cannot parse {line!r}")
        ident, comp, raw = m.groups()
        raw = quote_refs(raw)
        stmts[ident] = (comp, json.loads(f"[{raw}]"))
    return stmts

SIGS = {"Heading": ["text"], "Text": ["text"], "Metric": ["label", "value"],
        "Card": ["title", "children"], "Row": ["children"], "Table": ["columns", "rows"],
        "Button": ["label", "action"], "GeneratedView": ["html"]}

def to_tree(stmts, ident="root"):
    comp, args = stmts[ident]
    props = dict(zip(SIGS[comp], args))
    if "children" in props:
        props["children"] = [to_tree(stmts, r.lstrip("@")) for r in props["children"]]
    return {"component": comp, "props": props}

def partial_render(src):
    """Streaming: render whatever complete lines exist so far (unresolved refs skipped)."""
    ok = []
    for line in src.splitlines():
        if LINE.match(line.strip()): ok.append(line)
    return "\n".join(ok)

# ---- the model's output in each mode, expressed in OpenUI Lang ------------
STATIC = '''root = Row([m1, m2])
m1 = Metric("Revenue", "$575")
m2 = Metric("Cups sold", "245")'''
DECLARATIVE = '''root = Card("Lemonade stand", [row, tbl, go])
row = Row([m1, m2])
m1 = Metric("Revenue", "$575")
m2 = Metric("Cups sold", "245")
tbl = Table(["Flavor", "Cups", "Revenue"], [["Classic", 120, "$240"], ["Pink", 80, "$200"], ["Mint", 45, "$135"]])
go = Button("Restock", "restock")'''
OPEN = f'root = GeneratedView({json.dumps(mock_llm.ask("open"))})'
MIXED = DECLARATIVE.replace("[row, tbl, go]", "[row, viz, tbl, go]") + f'\nviz = GeneratedView({json.dumps(mock_llm.ask("open"))})'

if __name__ == "__main__":
    out = pathlib.Path(__file__).parent.parent / "out"; out.mkdir(exist_ok=True)
    for name, src in [("static", STATIC), ("declarative", DECLARATIVE), ("open", OPEN), ("mixed", MIXED)]:
        tree = to_tree(parse(src))
        (out / f"04_{name}.html").write_text(catalog.page(catalog.render(tree), name), encoding="utf-8")
        j = len(json.dumps(tree))
        print(f"[{name:11}] OpenUI Lang {len(src):4} chars vs equivalent JSON tree {j:4} chars ({100*len(src)//j}%)")
    # streaming demo: UI grows line by line
    lines = DECLARATIVE.splitlines()
    print("\nstreaming (root is declared first, children arrive later):")
    for i in range(1, len(lines) + 1):
        known = len(parse(partial_render("\n".join(lines[:i]))))
        print(f"  after line {i}: {known} statement(s) parsed")
