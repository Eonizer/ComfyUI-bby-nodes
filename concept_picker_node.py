"""
Concept Picker for ComfyUI
--------------------------
Code picks the concepts, the LLM only writes the prompt.

  Concept List      one per category; chain them together.
                    seed control:  fixed     = locked (same pick every run)
                                   randomize = new random pick every run
                                   increment = walks the whole list, no repeats
                    min/max count: how many items to pick; the seed picks a count in range
                    pin:           type a value to force it (overrides the list)
                    file:          pick a .txt from the lists/ folder (replaces the items box)
                    file_path:     or type a path to a .txt anywhere (overrides file)
  Prompt Builder    turns the chain into user_prompt + system_prompt strings
                    for any LLM node (e.g. "OpenAI API - Chat Completion").
  Aspect Ratio      reads an [AR:2:3] tag from the LLM reply, outputs the matching
  From Text         "Resolution (CRT)" dropdown value + the reply with the tag removed.
"""

import math
import os
import random
import re
import zlib

LISTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lists")
NO_FILE = "(none)"

DEFAULT_SYSTEM = """You write one image-generation prompt.
Rules:
- Use EVERY element given to you, exactly as given.
- Do NOT add new subjects, characters, settings or styles.
- {extra}
- Output only the prompt, one paragraph, no quotes, no preamble."""


def _parse_items(text):
    items = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            items.append(line)
    return items


def _list_files():
    """All .txt files under lists/ (subfolders included), as forward-slash relative paths."""
    files = []
    for root, _, names in os.walk(LISTS_DIR):
        for fname in names:
            if fname.lower().endswith(".txt"):
                rel = os.path.relpath(os.path.join(root, fname), LISTS_DIR)
                files.append(rel.replace(os.sep, "/"))
    return [NO_FILE] + sorted(files, key=str.lower)


def _file_path(file, file_path=""):
    """file_path (typed by the user, any location) wins over the lists/ dropdown."""
    typed = os.path.expandvars(os.path.expanduser(file_path.strip().strip('"').strip("'")))
    if typed:
        # Relative paths are taken from the lists/ folder.
        return os.path.abspath(os.path.join(LISTS_DIR, typed))
    if not file or file == NO_FILE:
        return None
    path = os.path.abspath(os.path.join(LISTS_DIR, file))
    if os.path.commonpath([path, LISTS_DIR]) != LISTS_DIR:
        raise ValueError(f"Concept List: '{file}' is outside the lists folder.")
    return path


def _read_file(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Concept List: list file not found: {path}")
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def _pick(name, items, seed, min_count, max_count):
    """Deterministic pick: same seed -> same result (so 'fixed' = locked).
    Items are put in a stable shuffled order, and the seed selects a position,
    so 'increment' goes through every item once before repeating.
    The count is drawn from [min_count, max_count] using the seed as well."""
    order = items[:]
    random.Random(zlib.crc32(name.encode("utf-8"))).shuffle(order)
    n = len(order)
    lo, hi = sorted((min_count, max_count))
    hi = max(0, min(hi, n))
    lo = max(0, min(lo, hi))
    count = random.Random(f"{name}:{seed}").randint(lo, hi)
    # Step by max so consecutive seeds never overlap, whatever count was drawn.
    start = (seed * max(hi, 1)) % n
    return [order[(start + i) % n] for i in range(count)]


class ConceptList:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": ("STRING", {"default": "subject"}),
                "items": ("STRING", {
                    "multiline": True,
                    "default": "an old lighthouse keeper\na fox made of paper\na lone astronaut\ntwin dancers",
                }),
                "min_count": ("INT", {"default": 1, "min": 0, "max": 20,
                                      "tooltip": "Fewest different items to pick from this list "
                                                 "(0 = this concept may be left out)."}),
                "max_count": ("INT", {"default": 1, "min": 0, "max": 20,
                                      "tooltip": "Most different items to pick. The count is chosen "
                                                 "by the seed; set min = max for a fixed count."}),
                "enabled": ("BOOLEAN", {"default": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF,
                                 "control_after_generate": True,
                                 "tooltip": "fixed = locked, randomize = new pick each run, increment = no repeats"}),
                "pin": ("STRING", {"default": "",
                                   "tooltip": "Optional: type a value to force it, ignoring the list."}),
                # Kept last so saved workflows' widget values don't shift.
                "file": (_list_files(), {"default": NO_FILE,
                                         "tooltip": "Load items from a .txt file in the node pack's lists/ folder "
                                                    "(one per line, # = comment). Replaces the items box. "
                                                    "Press R in ComfyUI to refresh after adding files."}),
                "file_path": ("STRING", {"default": "",
                                         "tooltip": "Optional: full path to a .txt list anywhere, e.g. a network share "
                                                    "(\\\\server\\share\\subjects.txt). Overrides the file dropdown."}),
            },
            "optional": {
                "concepts": ("CONCEPTS",),
            },
        }

    RETURN_TYPES = ("CONCEPTS", "STRING")
    RETURN_NAMES = ("concepts", "picked")
    FUNCTION = "run"
    CATEGORY = "bbyNodes"

    @classmethod
    def IS_CHANGED(cls, file=NO_FILE, file_path="", **kwargs):
        # Re-run when the selected file is edited on disk.
        path = _file_path(file, file_path)
        if path and os.path.isfile(path):
            return os.path.getmtime(path)
        return ""

    def run(self, name, items, min_count, max_count, enabled, seed, pin, file=NO_FILE, file_path="",
            concepts=None):
        chain = list(concepts) if concepts else []
        if not enabled:
            return (chain, "")
        name = name.strip() or "concept"
        if pin.strip():
            picks = [pin.strip()]
        else:
            path = _file_path(file, file_path)
            if path:
                items = _read_file(path)
            parsed = _parse_items(items)
            if not parsed:
                return (chain, "")
            picks = _pick(name, parsed, seed, min_count, max_count)
            if not picks:
                return (chain, "")
        chain.append((name, picks))
        return (chain, ", ".join(picks))


class ConceptPromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "concepts": ("CONCEPTS",),
                "system_prompt": ("STRING", {"multiline": True, "default": DEFAULT_SYSTEM}),
                "extra_details": ("INT", {"default": 1, "min": 0, "max": 10,
                                          "tooltip": "How many small details the model may add (0 = only your concepts)."}),
                "extra_instruction": ("STRING", {"multiline": True, "default": "",
                                                 "tooltip": "Optional extra instruction, e.g. 'make it rainy'."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("user_prompt", "system_prompt", "picks")
    FUNCTION = "run"
    CATEGORY = "bbyNodes"

    def run(self, concepts, system_prompt, extra_details, extra_instruction):
        if extra_details <= 0:
            extra = "Add nothing of your own."
        else:
            extra = (f"You may add at most {extra_details} small descriptive detail(s) "
                     "(texture, color, composition) that fit the elements.")

        if "{extra}" in system_prompt:
            system = system_prompt.replace("{extra}", extra)
        else:
            system = system_prompt.rstrip() + "\n- " + extra

        lines = [f"- {name}: {', '.join(picks)}" for name, picks in concepts]
        user = "Elements:\n" + "\n".join(lines)
        if extra_instruction.strip():
            user += f"\n\nExtra instruction: {extra_instruction.strip()}"

        summary = " | ".join(f"{name}: {', '.join(picks)}" for name, picks in concepts)
        return (user, system, summary)


# Must match the "Resolution (CRT)" dropdown exactly.
CRT_RATIOS = [
    "1:1 (Square)",
    "2:3 (Portrait)", "3:4 (Portrait)", "4:5 (Portrait)", "5:7 (Portrait)", "5:8 (Portrait)",
    "7:9 (Portrait)", "9:16 (Portrait)", "9:19 (Portrait)", "9:21 (Portrait)",
    "3:2 (Landscape)", "4:3 (Landscape)", "5:3 (Landscape)", "5:4 (Landscape)", "7:5 (Landscape)",
    "8:5 (Landscape)", "9:7 (Landscape)", "16:9 (Landscape)", "19:9 (Landscape)", "21:9 (Landscape)",
]

AR_TAG = re.compile(r"\[\s*AR\s*:\s*(\d+)\s*[:x]\s*(\d+)\s*\]", re.IGNORECASE)


def _ratio_value(label):
    w, h = label.split(" ")[0].split(":")
    return int(w) / int(h)


def _closest_crt(w, h):
    """Snap any ratio (e.g. 1:2) to the nearest one the CRT node offers."""
    target = math.log(w / h)
    return min(CRT_RATIOS, key=lambda r: abs(math.log(_ratio_value(r)) - target))


class AspectRatioFromText:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
                "default_ratio": (CRT_RATIOS, {"default": "1:1 (Square)",
                                               "tooltip": "Used when the text has no [AR:w:h] tag."}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 32.0, "step": 0.1}),
                "divisible_by": ("INT", {"default": 16, "min": 1, "max": 256}),
            },
        }

    RETURN_TYPES = (CRT_RATIOS, "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("aspect_ratio", "clean_text", "ratio", "width", "height")
    FUNCTION = "run"
    CATEGORY = "bbyNodes"

    def run(self, text, default_ratio, megapixels, divisible_by):
        match = AR_TAG.search(text)
        if match and int(match.group(1)) > 0 and int(match.group(2)) > 0:
            label = _closest_crt(int(match.group(1)), int(match.group(2)))
        else:
            label = default_ratio

        # Remove every tag so it never reaches the image model.
        clean = AR_TAG.sub("", text)
        clean = re.sub(r"[ \t]{2,}", " ", clean).strip()

        ratio = _ratio_value(label)
        pixels = megapixels * 1_000_000
        width = round(math.sqrt(pixels * ratio) / divisible_by) * divisible_by
        height = round(math.sqrt(pixels / ratio) / divisible_by) * divisible_by
        return (label, clean, label.split(" ")[0], int(width), int(height))


CONCEPT_PICKER_CLASS_MAPPINGS = {
    "ConceptList": ConceptList,
    "ConceptPromptBuilder": ConceptPromptBuilder,
    "AspectRatioFromText": AspectRatioFromText,
}

CONCEPT_PICKER_DISPLAY_NAME_MAPPINGS = {
    "ConceptList": "Concept List",
    "ConceptPromptBuilder": "Concept Prompt Builder",
    "AspectRatioFromText": "Aspect Ratio From Text",
}
