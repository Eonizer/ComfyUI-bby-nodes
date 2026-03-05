# ComfyUI-bby-nodes

A custom node pack for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

## Installation

Clone into your ComfyUI `custom_nodes` directory:

```bash
cd custom_nodes
git clone https://github.com/Eonizer/ComfyUI-bby-nodes
```

Restart ComfyUI.

## Nodes

### TagFilterNode

Filters a comma/newline-separated list of tags against a reference tag list.

**Outputs:**
- `filtered_tags` — tags that matched the reference list
- `missing_tags` — tags from the reference list not found in the input

**Options:**
- Match mode: `exact` or `partial`
- Case sensitivity toggle
- Underscore-stripping
