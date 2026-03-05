# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a ComfyUI custom node pack (`bby_nodes`) living at `custom_nodes/bby_nodes/` inside a ComfyUI installation. ComfyUI loads it automatically on startup by scanning for `NODE_CLASS_MAPPINGS` in Python files.

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
bby_nodes/
  __init__.py          # Entry point: aggregates all node mappings, exports NODE_CLASS_MAPPINGS / NODE_DISPLAY_NAME_MAPPINGS / __all__
  pyproject.toml       # Project metadata + [tool.comfy] section for Comfy Registry
  tag_filter_node.py   # Node class + per-module TAG_FILTER_CLASS_MAPPINGS / TAG_FILTER_DISPLAY_NAME_MAPPINGS
```

**Pattern for adding a new node:** create a new `<name>_node.py` with the class and `<NAME>_CLASS_MAPPINGS` / `<NAME>_DISPLAY_NAME_MAPPINGS` dicts, then import and merge them in `__init__.py`.

## Running / Testing

There is no test runner. To test a node change, restart ComfyUI (or use ComfyUI-Manager's "Reload Custom Nodes" if available) and exercise the node in the UI.

ComfyUI is launched from `/c/sd/comfy_dr/` (see `start.bat` / `start_m.bat`).

## Current Nodes

- **`TagFilterNode`** (`tag_filter_node.py`) — Filters a comma/newline-separated list of input tags against a reference tag list. Outputs `filtered_tags` (matched) and `missing_tags` (unmatched). Supports `exact` and `partial` match modes, case sensitivity toggle, and underscore-stripping.
