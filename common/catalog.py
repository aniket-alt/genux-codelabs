"""Shared component catalog + renderer used by every codelab.

The catalog is the contract between agent and application: the agent may only
name components listed here, with props of the declared types. The renderer is
the ONLY code that turns agent output into HTML -- "the agent chooses, the
application renders".
"""
from html import escape

# name -> {prop: type}.  "children" is special: a list of child nodes.
CATALOG = {
    "Heading": {"text": str},
    "Text":    {"text": str},
    "Metric":  {"label": str, "value": str},
    "Card":    {"title": str, "children": list},
    "Row":     {"children": list},
    "Table":   {"columns": list, "rows": list},
    "Button":  {"label": str, "action": str},
    "GeneratedView": {"html": str},   # the escape hatch (hybrid mode)
}

CSS = """
body{font-family:system-ui,sans-serif;margin:24px;background:#fafafa;color:#222}
.card{background:#fff;border:1px solid #ddd;border-radius:10px;padding:14px;margin:10px 0}
.row{display:flex;gap:12px;flex-wrap:wrap}.row>*{flex:1;min-width:140px}
.metric b{display:block;font-size:1.8em}.metric span{color:#666}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #eee;padding:6px;text-align:left}
button{padding:8px 14px;border-radius:6px;border:0;background:#f5a623;cursor:pointer}
iframe{width:100%;height:180px;border:1px dashed #999;border-radius:8px}
"""


class CatalogError(ValueError):
    pass


def validate(node, path="root"):
    """Reject unknown components / wrong prop types. Raises CatalogError."""
    if not isinstance(node, dict) or "component" not in node:
        raise CatalogError(f"{path}: node needs a 'component' key")
    name = node["component"]
    if name not in CATALOG:
        raise CatalogError(f"{path}: unknown component {name!r}")
    props = node.get("props", {})
    for key, typ in CATALOG[name].items():
        if key not in props:
            raise CatalogError(f"{path}: {name} missing prop {key!r}")
        if not isinstance(props[key], typ):
            raise CatalogError(f"{path}: {name}.{key} must be {typ.__name__}")
    for extra in set(props) - set(CATALOG[name]):
        raise CatalogError(f"{path}: {name} has unexpected prop {extra!r}")
    for i, child in enumerate(props.get("children", [])):
        validate(child, f"{path}.{name}[{i}]")
    return True


def sandbox_iframe(html):
    """Open-ended HTML is never inlined: it goes in a sandboxed iframe
    (no scripts-same-origin, no network via CSP)."""
    csp = "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'\">"
    return f"<iframe sandbox='allow-scripts' srcdoc=\"{escape(csp + html, quote=True)}\"></iframe>"


def render(node):
    """Nested tree {'component','props'} -> HTML string."""
    validate(node)
    c, p = node["component"], node.get("props", {})
    kids = "".join(render(k) for k in p.get("children", []))
    if c == "Heading": return f"<h2>{escape(p['text'])}</h2>"
    if c == "Text":    return f"<p>{escape(p['text'])}</p>"
    if c == "Metric":  return f"<div class='card metric'><span>{escape(p['label'])}</span><b>{escape(p['value'])}</b></div>"
    if c == "Card":    return f"<div class='card'><h3>{escape(p['title'])}</h3>{kids}</div>"
    if c == "Row":     return f"<div class='row'>{kids}</div>"
    if c == "Table":
        head = "".join(f"<th>{escape(str(h))}</th>" for h in p["columns"])
        body = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in r) + "</tr>" for r in p["rows"])
        return f"<table><tr>{head}</tr>{body}</table>"
    if c == "Button":  return f"<button data-action='{escape(p['action'], quote=True)}'>{escape(p['label'])}</button>"
    if c == "GeneratedView": return sandbox_iframe(p["html"])
    raise CatalogError(c)


def page(body, title="GenUX codelab"):
    return f"<!doctype html><meta charset=utf-8><title>{escape(title)}</title><style>{CSS}</style>{body}"
