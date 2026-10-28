# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a ComfyUI custom node pack (`bby_nodes`) living at `custom_nodes/ComfyUI-bby-nodes/` inside a ComfyUI installation. ComfyUI loads it automatically on startup by scanning for `NODE_CLASS_MAPPINGS` in Python files.

## ComfyUI Custom Node Conventions

Every node module must export at the module level:
- `NODE_CLASS_MAPPINGS` — dict mapping internal name → class
- `NODE_DISPLAY_NAME_MAPPINGS` — dict mapping internal name → UI label

Each node class must define:
- `INPUT_TYPES(s)` — classmethod returning `{"required": {...}, "optional": {...}}`
- `RETURN_TYPES` — tuple of type strings (e.g. `("STRING", "IMAGE",)`)
- `RETURN_NAMES` — tuple of output socket names
- `FUNCTION` — string name of the method ComfyUI calls
- `CATEGORY` — UI category path (e.g. `"utils/text"`)
- The method named by `FUNCTION`, whose positional args match `INPUT_TYPES` keys

Common type strings: `"STRING"`, `"INT"`, `"FLOAT"`, `"BOOLEAN"`, `"IMAGE"`, `"MASK"`, `"MODEL"`, `"CLIP"`, `"VAE"`, `"CONDITIONING"`, `"LATENT"`

Widget options for `STRING`: `{"multiline": True/False, "default": "..."}`

## File Structure

```
ComfyUI-bby-nodes/
  __init__.py          # Entry point: aggregates all node mappings, exports NODE_CLASS_MAPPINGS / NODE_DISPLAY_NAME_MAPPINGS / __all__
  pyproject.toml       # Project metadata + [tool.comfy] section for Comfy Registry
  tag_filter_node.py   # Node class + per-module TAG_FILTER_CLASS_MAPPINGS / TAG_FILTER_DISPLAY_NAME_MAPPINGS
  concept_picker_node.py  # ConceptList / ConceptPromptBuilder / AspectRatioFromText + CONCEPT_PICKER_* mappings
  lists/               # .txt item lists offered in ConceptList's `file` dropdown
  web/                 # Frontend JS (WEB_DIRECTORY); concept_list.js = Concept List preview box
  phone_ui.py          # Registers GET /phone (no nodes)
  phone/index.html     # Mobile "pick a saved workflow + Run" page; kept out of web/ so it isn't loaded as an extension
```

**Pattern for adding a new node:** create a new `<name>_node.py` with the class and `<NAME>_CLASS_MAPPINGS` / `<NAME>_DISPLAY_NAME_MAPPINGS` dicts, then import and merge them in `__init__.py`.

## Running / Testing

There is no test runner. To test a node change, restart ComfyUI (or use ComfyUI-Manager's "Reload Custom Nodes" if available) and exercise the node in the UI.

ComfyUI is launched from `/c/sd/comfy_dr/` (see `start.bat` / `start_m.bat`).

## Current Nodes

- **`TagFilterNode`** (`tag_filter_node.py`) — Filters a comma/newline-separated list of input tags against a reference tag list. Outputs `filtered_tags` (matched) and `missing_tags` (unmatched). Supports `exact` and `partial` match modes, case sensitivity toggle, and underscore-stripping.
- **`ConceptList`** (`concept_picker_node.py`) — Deterministically picks between `min_count` and `max_count` items from a list (count and picks both seed-driven; `increment` cycles without repeats) and appends `(name, picks)` to a chainable `CONCEPTS` list. `pin` forces a value. `file` loads items from `lists/*.txt` instead of the `items` box; `file_path` (any path, e.g. a UNC share) overrides `file`. `chance` (0–100, default 100) is a seed-driven roll for whether the concept is added at all (applies to `pin` too). New widgets go at the end of the required inputs so saved workflows' positional widget values don't shift. A read-only `preview` box (added by `web/concept_list.js`, not serialized) shows the selected file's items live via `GET /bby_nodes/concept_list/preview`, and the picks after each run (`run` returns `ui.picked` and `ui.status`: `pinned` / `skipped` (chance) / `empty` / `disabled`). The JS also hides rows that have no effect (`items` when a file is used, `file` when `file_path` is set, `control_after_generate` when seed is wired; never `seed`, whose row positions its input socket) via `widget.hidden`, and draws a gold outline + 📌 on pinned nodes. `enabled` is kept in Python only for positional compatibility: it is always hidden, and a loaded `enabled = false` becomes bypass mode. `repairShifted` fixes workflows saved before `min_count`/`max_count` existed (values shifted one slot: seed = `"randomize"` → NaN).
- **`ConceptPromptBuilder`** (`concept_picker_node.py`) — Turns a `CONCEPTS` chain into `user_prompt` / `system_prompt` strings for an LLM node.
- **`AspectRatioFromText`** (`concept_picker_node.py`) — Parses an `[AR:w:h]` tag from text, snaps to the nearest "Resolution (CRT)" ratio, strips the tag, and outputs width/height. `CRT_RATIOS` must match that node's dropdown exactly.

## Phone page (`/phone`)

`phone/index.html` is a self-contained mobile page. It lists `user/<user>/workflows/*.json` via `/api/userdata` and loads the real ComfyUI frontend (`/`) in a hidden iframe; the selected workflow goes through `app.loadGraphData(data, true, true, path)` and Run calls `app.queuePrompt(0, 1)`, so custom-node `graphToPrompt` hooks, subgraphs and seed controls behave exactly as on desktop. It wraps the frame's `app.graphToPrompt` / `api.queuePrompt` to surface errors (the frontend only shows them in dialogs, which are hidden), follows progress/results through the frame's `api` events, and steps `control_after_generate` widgets once after each load (incl. `comfyAPI.promotedWidgetControl` for subgraph-promoted seeds) so the first Run doesn't hit the cache. Nodes whose title contains `[phone]` (or 📱) are the only results shown; on a subgraph node it marks every output inside it. Without marks it shows saved outputs, falling back to previews. To test without restarting ComfyUI, copy it into `web/` temporarily and open `/extensions/ComfyUI-bby-nodes/<file>.html`.
