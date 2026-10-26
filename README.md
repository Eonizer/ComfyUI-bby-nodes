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

### Concept Picker

Code picks the concepts, the LLM only writes the prompt.

- **Concept List** — one per category (subject, setting, style…); chain them together via the `concepts` socket. Picks between `min_count` and `max_count` items (the seed picks the count) from a newline-separated list (`#` lines are comments).
  - Seed control: `fixed` = same pick every run, `randomize` = new pick every run, `increment` = walks the whole list with no repeats.
  - `pin` — type a value to force it, ignoring the list.
  - `file` — load the list from a `.txt` file in the pack's `lists/` folder (subfolders allowed) instead of the `items` box. Press `R` in ComfyUI to refresh the dropdown after adding files; editing a selected file re-runs the node.
  - `file_path` — or type a path to a `.txt` list anywhere the ComfyUI machine can read, e.g. `D:\lists\subjects.txt` or a network share `\\server\share\subjects.txt` (surrounding quotes, `~` and `%VARS%` are fine; relative paths start in `lists/`). Overrides `file`.
- **Concept Prompt Builder** — turns the chain into `user_prompt` + `system_prompt` strings for any LLM node (e.g. "OpenAI API - Chat Completion"). `extra_details` limits how many details the model may add; `{extra}` in the system prompt is replaced with that rule.
- **Aspect Ratio From Text** — reads an `[AR:2:3]` tag from the LLM reply and outputs the nearest "Resolution (CRT)" dropdown value, the reply with the tag removed, and width/height for the given megapixels.
