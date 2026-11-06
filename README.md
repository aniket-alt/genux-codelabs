# GenUX Codelabs: A2UI, AG-UI, MCP Apps, json-render, OpenUI, harness integration

Assignment 4 (GenUX). Every technology is shown in **all four generation modes**:

| Mode | Who decides the UI? | Pros | Cons |
|---|---|---|---|
| **Static** | Developer pre-builds components; model only selects/fills them (tool calls, or data into a fixed layout) | safest, cheapest, on-brand | model cannot do layout |
| **Declarative** | Model writes a *description* (JSON / flat messages / DSL) of a layout from a catalog; app renders it | safe + flexible, streamable | limited to the catalog |
| **Open-ended** | Model writes raw HTML; host sandboxes it (`iframe sandbox` + CSP) | unlimited | 5-10x tokens, harder to secure/brand |
| **Mixed** | Catalog layout + a `GeneratedView` escape hatch for the one thing the catalog can't express | best of both | two code paths |

Key idea in every codelab: **the agent chooses, the application renders.**

## Run it (Python 3.10+, no installs, no API key)

```bash
python run_all.py            # all 7 codelabs + 14 unit tests
python 03_a2ui/demo.py       # or any single codelab
python -m unittest test_all -v
```
Each demo writes `out/NN_<mode>.html` -- open them in a browser to *see* the UI.
The "LLM" is a deterministic mock (`common/mock_llm.py`) so runs are reproducible;
hook a real model into `real_llm()` and set `USE_REAL_LLM=1`.

## Layout and what each part teaches

| Part | Folder | Concept | Video |
|---|---|---|---|
| 1 | `01_foundations/` | the 4 modes from scratch, catalog validation, sandbox |  |
| 2 | `02_ag_ui/` | **AG-UI**: SSE event stream (text, tool-call, state snapshot/JSON-Patch events) | [Watch](https://drive.google.com/file/d/1fAB0OZ6NpBmuHAl0iJhd3IBuhIJYx-cH/view?usp=sharing) |
| 3 | `03_a2ui/` | **A2UI**: flat component list + separate data model + `beginRendering`, JSONL | _add link_ |
| 4 | `04_openui_lang/` | **OpenUI Lang**: token-light DSL, parser + streaming | _add link_ |
| 5 | `05_json_render/` | **json-render**: catalog -> JSON Schema, flat spec, JSON-Patch streaming, action allow-list | _add link_ |
| 6 | `06_mcp_apps/` | **MCP Apps**: real JSON-RPC stdio server, `ui://` resource, sandboxed host | _add link_ |
| 7 | `07_harness_genui/` | **Harness**: agent loop where `render_ui` is just another tool | _add link_ |

`common/catalog.py` = component catalog, validator, renderer, sandbox. `common/mock_llm.py` = what the model emits per mode.

## How the protocols relate (say this in the videos)

```
 Model --(generation: static | declarative | open)--> UI payload
 Payload shapes:  A2UI messages | json-render spec | OpenUI Lang | raw HTML | MCP App resource
 Transport to the screen:  AG-UI (agent<->frontend events)  |  MCP (tool server -> host)
 Harness: the loop that calls the model, tools, permissions, and emits the UI events
```
AG-UI is *transport*, A2UI / json-render / OpenUI are *generation formats*, MCP Apps is *delivery of
a server-provided UI into a host*. They compose: e.g. an A2UI surface can ride inside AG-UI events.

## Honest scope note
These are from-scratch, dependency-free implementations that follow each spec's *mechanism* and
message names (simplified: e.g. JSON-Patch supports top-level add/replace only, A2UI is a subset of
v0.8). They are for learning; for production use the official SDKs (`@ag-ui/client`, `@a2ui/*`,
`@modelcontextprotocol/ext-apps`, `@json-render/*`, `@openuidev/*`). Reference course repo:
https://github.com/dlmastery/simple-coding-harness/tree/main/genui

## Recording checklist (each video)
1. 20s: the concept and the diagram above. 2. Open `demo.py`, walk top to bottom (script in `VIDEO_SCRIPTS.md`).
3. Run `python NN_*/demo.py` and read the output aloud. 4. Open `out/NN_*.html` in the browser, compare the 4 modes.
5. Show the safety/failure case. 6. Upload to YouTube, paste link in the table above.
