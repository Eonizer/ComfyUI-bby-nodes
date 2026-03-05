class TagFilterNode:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "tag_list": ("STRING", {"multiline": True, "default": ""}),
                "input_tags": ("STRING", {"multiline": True, "default": ""}),
                "match_mode": (["exact", "partial"],),
                "case_sensitive": ("BOOLEAN", {"default": False}),
                "strip_underscores": ("BOOLEAN", {"default": True}),
            }
        }

    CATEGORY = "bbyNodes"
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("filtered_tags", "missing_tags",)
    FUNCTION = "filter_tags"
    DESCRIPTION = """
Filters input tags against a reference tag list.

Modes:
  exact   - tag must match exactly (e.g. "looking at viewer" == "looking at viewer")
  partial - list tag found inside input tag (e.g. "looking at viewer" inside "woman looking at viewer")
            returns the list tag (canonical/shorter form)
"""

    def filter_tags(self, tag_list, input_tags, match_mode, case_sensitive, strip_underscores):

        do_case  = case_sensitive
        do_under = strip_underscores

        def normalize(tag):
            tag = tag.strip()
            if do_under:
                tag = tag.replace("_", " ")
            if not do_case:
                tag = tag.lower()
            return tag

        # Parse tag_list — supports newline and/or comma separated
        list_tags = []
        seen = set()
        for line in tag_list.splitlines():
            for part in line.split(","):
                n = normalize(part)
                if n and n not in seen:
                    list_tags.append((n, part.strip()))
                    seen.add(n)

        # Parse input_tags — supports newline and/or comma separated
        raw_input = []
        for line in input_tags.splitlines():
            for part in line.split(","):
                p = part.strip()
                if p:
                    raw_input.append(p)

        matched = []
        missing = []

        if match_mode == "exact":
            list_set = {n: orig for n, orig in list_tags}
            for tag in raw_input:
                if normalize(tag) in list_set:
                    matched.append(list_set[normalize(tag)])
                else:
                    missing.append(tag)

        elif match_mode == "partial":
            matched_set = set()
            for tag in raw_input:
                n_input = normalize(tag)
                found_any = False
                for n_list, orig_list in list_tags:
                    if n_list in n_input:
                        if orig_list not in matched_set:
                            matched_set.add(orig_list)
                            matched.append(orig_list)
                        found_any = True
                if not found_any:
                    missing.append(tag)

        return (", ".join(matched), ", ".join(missing),)


TAG_FILTER_CLASS_MAPPINGS = {
    "TagFilterNode": TagFilterNode,
}

TAG_FILTER_DISPLAY_NAME_MAPPINGS = {
    "TagFilterNode": "Tag Filter (from list)",
}
