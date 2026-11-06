# Video scripts (one per part, ~6-8 min each)

Each: **Concept (1 min) -> Code walkthrough (3-4 min) -> Run + browser (2 min) -> Takeaway (30s).**

## 1. Foundations (`01_foundations/demo.py`)
- Show `common/catalog.py`: `CATALOG` dict = the contract; `validate()`; `render()` escapes text; `sandbox_iframe()`.
- Walk the four functions `static_mode / declarative_mode / open_mode / mixed_mode`.
- Run; compare the printed agent-output sizes (316 / 501 / 397 / 965 chars) and open `out/01_*.html`.
- Show the `EvilWidget` rejection. Takeaway: validate -> render; never inline model HTML.

## 2. AG-UI (`02_ag_ui/demo.py`)
- Explain AG-UI = event stream between agent and frontend. Show `agent_run()`: lifecycle, text, tool-call, state events.
- Static = TOOL_CALL_* events; declarative = STATE_SNAPSHOT + STATE_DELTA (JSON Patch); open = HTML in state.
- Show the SSE server (`H`) and client (`run_client`) folding events. Run, read event list per mode.

## 3. A2UI (`03_a2ui/demo.py`)
- Explain flat adjacency list + ids, data model separate from layout, `beginRendering`.
- Walk `Surface.handle/render`; show `{"path": "/revenue"}` binding.
- Run; open `out/03_declarative.jsonl` to show the wire format. Point out: render started before data arrived.
- Mixed: re-sending `root` patches the surface in place; `Html` is a custom catalog entry.

## 4. OpenUI Lang (`04_openui_lang/demo.py`)
- Show the language (`id = Component(args)`), `quote_refs` tokenizer, `parse`, `to_tree`.
- Run; explain the % size vs JSON and the streaming table (root first, children later).
- Be upfront: this is a teaching implementation of the idea.

## 5. json-render (`05_json_render/demo.py`)
- Catalog -> `catalog_json_schema()` -> model; flat spec; `tree_to_spec`; JSON-Patch stream; `ACTIONS` allow-list.
- Run; show the blocked `rm_rf` action. Takeaway: guardrails = catalog + action registry.

## 6. MCP Apps (`06_mcp_apps/server.py` then `demo.py`)
- `server.py`: JSON-RPC methods; `_meta.ui.resourceUri`; MIME `text/html;profile=mcp-app`.
- `demo.py`: initialize -> tools/list -> tools/call -> resources/read -> sandboxed iframe + postMessage tool-result.
- Open `out/06_static.html` (app fills itself from the tool result) vs `06_open.html`.

## 7. Harness (`07_harness_genui/demo.py`)
- Agent loop, permissions, `render_ui` tool, tiny ack to the model, UI event to the frontend.
- Run; show 2-step trace per mode and the blocked `Script` component. Tie back to AG-UI (UI_EVENTS = what streams out).
- Wrap-up slide: when to pick static vs declarative vs open vs mixed.
