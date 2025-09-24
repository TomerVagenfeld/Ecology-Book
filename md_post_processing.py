# md_post_processing.py
# Utilities that post-process Markdown files after Pandoc conversion but before Jupyter-Book.

from pathlib import Path
import re

# --- Regexes / heuristics ---
ALREADY_NUMBERED_RE = re.compile(r'^\d+(?:\.\d+)*\s+')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
HEBREW_RE = re.compile(r'[\u0590-\u05FF]')          # Hebrew Unicode block
LATIN_RE  = re.compile(r'[A-Za-z]')
FOOTNOTE_DEF_RE = re.compile(r'^\s*\[\^[^\]]+\]:')   # [^1]:
FOOTNOTE_DEF_CAPTURE_RE = re.compile(r'^\s*\[\^([^\]]+)\]:')
FOOTNOTE_REF_RE = re.compile(r'\[\^[^\]]+\]')        # inline refs [^1]
FOOTNOTE_REF_CAPTURE_RE = re.compile(r'\[\^([^\]]+)\](?!\s*:)')
FIRST_NONBLANK_HEADING_FORMS = re.compile(r'^\s*(?:[*_]{1,3}\s*)?(.+?)(?:\s*[*_]{1,3})?\s*$')
URL_RE = re.compile(r'(https?://|www\.)', re.IGNORECASE)
ANON_FENCE_LINE_RE = re.compile(r'^[ \t]*:::\s*$')
ANON_FENCE_DIRECTIVE_RE = re.compile(r'^[ \t]*:::\{')
COLON_FENCE_RE = re.compile(r'^([ \t]*):::(\{[^}]+\})?\s*$')

# Old HTML wrapper (kept for backward compat only)
_HTML_EN_QUOTE_BLOCK_RE = re.compile(
    r'(<div[^>]*class="en_quote"[^>]*>)(.*?)(</div>)',
    flags=re.DOTALL | re.IGNORECASE,
)

# New MyST colon-fence wrapper for en_quote blocks
# Captures: indent, directive name, options, payload, and closing fence with same indent
_COLON_EN_QUOTE_BLOCK_RE = re.compile(
    r'(?ms)^([ \t]*):::\{(?P<directive>div|container)\}\s*\n'  # indent + :::{div|container}
    r'(?P<options>(?:[ \t]*:[^\n]+\n)*)'                        # option lines (if any)
    r'\n?'                                                        # optional spacer line
    r'(?P<body>.*?)'                                               # payload content
    r'\n\1:::\s*$'                                              # closing fence at same indent
)

# --- Title promotion ---------------------------------------------------------
def promote_top_title_line_to_h1(md_path: str | Path) -> None:
    p = Path(md_path)
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()

    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return

    L = lines[i]
    # don’t touch if it’s already a heading/blockquote/list/fence/image
    if re.match(r'^\s*(#|>|\- |\* |\+ |\d+\.\s|```|~~~|!\[)', L):
        return

    m = FIRST_NONBLANK_HEADING_FORMS.match(L)
    if not m:
        return
    title = m.group(1).strip()

    if len(title) > 80 or re.match(r'^\s*https?://', title):
        return

    lines[i] = f"# {title}"
    for j in range(i + 1, len(lines)):
        if lines[j].startswith("# "):
            lines[j] = "#" + lines[j]

    new_text = "\n".join(lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    if new_text != text:
        p.write_text(new_text, encoding="utf-8")

# --- English block detection/wrapping ----------------------------------------

def _looks_english_only(text: str, min_latin=8, latin_ratio=0.35) -> bool:
    """Heuristic: treat as English if there are no Hebrew chars, enough Latin letters,
    and a reasonable Latin ratio."""
    if HEBREW_RE.search(text):
        return False
    latin = len(LATIN_RE.findall(text))
    if latin < min_latin:
        return False
    letters = re.findall(r'[A-Za-z\u0590-\u05FF]', text)
    ratio = latin / max(1, len(letters))
    return ratio >= latin_ratio

def _common_indent(block_lines: list[str]) -> str:
    if not block_lines:
        return ""
    indents = []
    for L in block_lines:
        if L.strip():
            m = re.match(r'^\s*', L)
            indents.append(len(m.group(0)))
    return " " * min(indents) if indents else ""

def mark_english_blocks(md_text: str, scope: str = "anywhere") -> str:
    """
    Wrap English-only blockquotes/paragraphs in a MyST container using colon-fences:

        ::: {container}
        :class: en_quote

        > ...
        :::

    Rules:
      • don’t wrap blocks containing footnote defs/refs or URLs
      • preserve the block’s original indentation (so lists/footnotes stay intact)
      • default scope scans entire file (set scope="before_first_h1" if you prefer)
    """
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0
    seen_h1 = False
    in_code = False

    def within_scope() -> bool:
        return scope == "anywhere" or (not seen_h1)

    def collect_blockquote(start: int) -> tuple[int, list[str]]:
        j = start
        block = []
        while j < len(lines) and re.match(r'^\s*>\s?', lines[j]):
            block.append(lines[j])
            j += 1
        return j, block

    def collect_paragraph(start: int) -> tuple[int, list[str]]:
        j = start
        block = []
        while j < len(lines):
            L = lines[j]
            if not L.strip():
                break
            if re.match(r'^\s*(```|~~~)', L):   # fence
                break
            if re.match(r'^\s*#(#+)?\s', L):    # heading
                break
            if re.match(r'^\s*>\s?', L):        # new quote starts
                break
            if FOOTNOTE_DEF_RE.match(L):        # a footnote definition
                break
            block.append(L)
            j += 1
        return j, block

    def text_for_detection(block: list[str], is_quote: bool) -> str:
        if is_quote:
            payload = [re.sub(r'^\s*>\s?', '', L) for L in block]
        else:
            indent = _common_indent(block)
            payload = [L[len(indent):] if indent and L.startswith(indent) else L for L in block]
        return "\n".join(payload)

    while i < len(lines):
        L = lines[i]

        # code fences passthrough
        if re.match(r'^\s*(```|~~~)', L):
            in_code = not in_code
            out.append(L); i += 1
            continue
        if in_code:
            out.append(L); i += 1
            continue

        # H1 bound (for scope="before_first_h1")
        if re.match(r'^\s*#\s+', L):
            seen_h1 = True

        # --- Blockquotes ---
        if within_scope() and re.match(r'^\s*>\s?', L):
            j, block = collect_blockquote(i)
            text = text_for_detection(block, is_quote=True)
            if _looks_english_only(text) and not (FOOTNOTE_DEF_RE.search(text) or FOOTNOTE_REF_RE.search(text) or URL_RE.search(text)):
                indent = _common_indent(block)
                if out and out[-1] is not None and out[-1].strip():
                    out.append(indent if indent else "")
                out.append(f"{indent}:::{{container}}")
                out.append(f"{indent}:class: en_quote")
                if indent:
                    out.append(indent)
                out.extend(block)                               # keep the original '>' lines
                out.append(f"{indent}:::")
            else:
                out.extend(block)
            i = j
            continue

        # --- Plain paragraphs ---
        if within_scope() and L.strip() and not re.match(r'^\s*#', L) \
           and not re.match(r'^\s*[-*+]\s', L) and not re.match(r'^\s*\d+\.\s', L) \
           and not FOOTNOTE_DEF_RE.match(L) and not re.match(r'^\s*>\s?', L) \
           and not re.match(r'^\s*(```|~~~)', L):

            j, block = collect_paragraph(i)
            text = text_for_detection(block, is_quote=False)
            if _looks_english_only(text) and not (FOOTNOTE_DEF_RE.search(text) or FOOTNOTE_REF_RE.search(text) or URL_RE.search(text)):
                indent = _common_indent(block)
                if out and out[-1] is not None and out[-1].strip():
                    out.append(indent if indent else "")
                out.append(f"{indent}:::{{container}}")
                out.append(f"{indent}:class: en_quote")
                if indent:
                    out.append(indent)
                out.extend(block)
                out.append(f"{indent}:::")
            else:
                out.extend(block)
            i = j
            continue

        # default passthrough
        out.append(L); i += 1

    result = "\n".join([L for L in out if L is not None])
    if md_text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def mark_english_blocks_file(md_path: str | Path, scope="anywhere") -> None:
    p = Path(md_path)
    txt = p.read_text(encoding="utf-8")
    new = mark_english_blocks(txt, scope=scope)
    if new != txt:
        p.write_text(new, encoding="utf-8")

# --- Pandoc attribute normalization & en_quote un-escaping --------------------

def _unescape_in_en_quote(text: str) -> str:
    """Release common Pandoc/Word escapes that show up in epigraphs."""
    text = (text
            .replace(r'\"', '"')
            .replace(r"\'", "'"))
    text = text.replace(r'\...', '...')
    text = text.replace(r'\.', '.')
    text = re.sub(r'\\([,:;!?(){}\[\]])', r'\1', text)
    text = text.replace(r'\-', '-').replace(r'\ ', ' ')
    return text

def _fix_html_en_quote_blocks(text: str) -> str:
    def _fix(m: re.Match) -> str:
        open_tag, payload, close_tag = m.groups()
        return open_tag + _unescape_in_en_quote(payload) + close_tag
    return _HTML_EN_QUOTE_BLOCK_RE.sub(_fix, text)

def _fix_colon_en_quote_blocks(text: str) -> str:
    def _fix(m: re.Match) -> str:
        indent = m.group(1)
        payload_fixed = _unescape_in_en_quote(m.group('body'))
        lines = [f"{indent}:::{{container}}", f"{indent}:class: en_quote"]
        if indent:
            lines.append(indent)
        lines.extend(payload_fixed.splitlines())
        lines.append(f"{indent}:::")
        return "\n".join(lines)
    return _COLON_EN_QUOTE_BLOCK_RE.sub(_fix, text)


def strip_anonymous_colon_fences(md_text: str) -> str:
    """Remove bare MyST colon-fence containers that have no directive/options.

    This walks the Markdown line-by-line while keeping a stack of open colon
    fences. Anonymous containers (``:::`` without ``{directive}``) that don’t
    provide option lines (``:class:``, ``:name:``, …) are dropped by skipping
    both their opening and closing fence while leaving the enclosed payload
    intact. Nested colon fences are handled correctly so that inner directives
    like ``:::{container}`` survive even when wrapped in an empty anonymous
    block.
    """

    lines = md_text.splitlines()
    out: list[str] = []
    stack: list[dict[str, object]] = []

    def _has_options(start_index: int, indent: str) -> bool:
        k = start_index
        while k < len(lines):
            nxt = lines[k]
            if not nxt.strip():
                k += 1
                continue
            if nxt.startswith(f"{indent}:") and not nxt.startswith(f"{indent}::"):
                return True
            return False
        return False

    for idx, line in enumerate(lines):
        m = COLON_FENCE_RE.match(line)
        if not m:
            out.append(line)
            continue

        indent, directive = m.groups()
        directive = directive or ""

        if directive:
            stack.append({"indent": indent, "anonymous": False, "drop": False})
            out.append(line)
            continue

        # Anonymous fence – determine whether this is a closing fence for the
        # innermost open entry with matching indent, or the start of a new block
        if stack and stack[-1]["indent"] == indent:
            entry = stack.pop()
            if entry["anonymous"] and entry["drop"]:
                continue
            out.append(line)
            continue

        has_options = _has_options(idx + 1, indent)
        drop = not has_options
        stack.append({"indent": indent, "anonymous": True, "drop": drop})
        if drop:
            continue
        out.append(line)

    result = "\n".join(out)
    if md_text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def strip_anonymous_colon_fences_file(md_path: str | Path) -> None:
    p = Path(md_path)
    text = p.read_text(encoding="utf-8")
    fixed = strip_anonymous_colon_fences(text)
    if fixed != text:
        p.write_text(fixed, encoding="utf-8")


def remove_unreferenced_footnotes(md_text: str) -> str:
    """Strip footnote definitions that are never referenced in the document."""
    if not FOOTNOTE_DEF_RE.search(md_text):
        return md_text

    lines = md_text.splitlines()
    refs: set[str] = set()
    for line in lines:
        if FOOTNOTE_DEF_CAPTURE_RE.match(line):
            continue
        refs.update(m.group(1) for m in FOOTNOTE_REF_CAPTURE_RE.finditer(line))

    cleaned: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        m = FOOTNOTE_DEF_CAPTURE_RE.match(line)
        if not m:
            cleaned.append(line)
            i += 1
            continue

        label = m.group(1)
        block_start = i
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if FOOTNOTE_DEF_CAPTURE_RE.match(nxt):
                break
            if nxt.startswith("    ") or nxt.startswith("\t"):
                i += 1
                continue
            if not nxt.strip() and i + 1 < len(lines) and (
                lines[i + 1].startswith("    ") or lines[i + 1].startswith("\t")
            ):
                i += 1
                continue
            break

        if label in refs:
            cleaned.extend(lines[block_start:i])
        else:
            while cleaned and not cleaned[-1].strip():
                cleaned.pop()

    result = "\n".join(cleaned)
    if md_text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def remove_unreferenced_footnotes_file(md_path: str | Path) -> None:
    p = Path(md_path)
    text = p.read_text(encoding="utf-8")
    fixed = remove_unreferenced_footnotes(text)
    if fixed != text:
        p.write_text(fixed, encoding="utf-8")

def normalize_pandoc_attrs(md_path: Path):
    """Normalize smart quotes, drop Pandoc attribute blocks, remove stray backslash
    lines, and un-escape content inside en_quote blocks (both HTML and MyST forms)."""
    text = md_path.read_text(encoding="utf-8")

    # Normalize curly quotes
    text = (text.replace("”", '"').replace("“", '"').replace("’", "'"))

    # Drop { ... } pandoc attribute blocks
    text = re.sub(r'(?<=>)\s*\{[^{}]*\}', '', text)            # after HTML tags
    text = re.sub(r'(?<=\))\s*\{[^{}]*\}', '', text)           # after (...) links/images
    text = re.sub(r'^\s*\{[^{}]*\}\s*$', '', text, flags=re.MULTILINE)  # whole line
    text = re.sub(r'^\s*\\\s*$', '', text, flags=re.MULTILINE) # lone backslash lines

    # Un-escape inside en_quote wrappers (both kinds)
    text = _fix_html_en_quote_blocks(text)
    text = _fix_colon_en_quote_blocks(text)

    md_path.write_text(text, encoding="utf-8")

# --- Heading normalization & numbering ---------------------------------------

def normalize_markdown_heading_levels(md_text: str) -> str:
    lines = md_text.splitlines()
    if not lines:
        return md_text

    in_yaml = False
    in_code = False
    headings = []
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if i == 0 and line.strip() == "---":
            in_yaml = True
            continue
        if in_yaml:
            if line.strip() == "---":
                in_yaml = False
            continue
        m = HEADING_RE.match(line)
        if m:
            headings.append(len(m.group(1)))

    if not headings:
        return md_text

    min_level = min(headings)
    shift = (min_level - 1) if min_level > 1 else 0

    out, first_h1 = [], False
    in_yaml = in_code = False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append(line); continue
        if in_code:
            out.append(line); continue
        if i == 0 and line.strip() == "---":
            in_yaml = True
            out.append(line); continue
        if in_yaml:
            out.append(line)
            if line.strip() == "---":
                in_yaml = False
            continue

        m = HEADING_RE.match(line)
        if not m:
            out.append(line); continue

        hashes, rest = m.groups()
        level = len(hashes)
        level = max(1, level - shift)  # promote so smallest becomes H1

        if not first_h1 and level == 1:
            first_h1 = True
            out.append("# " + rest.strip())
        else:
            if level == 1:
                level = 2  # demote subsequent H1s to H2
            out.append("#" * level + " " + rest.strip())

    return "\n".join(out) + ("\n" if md_text.endswith("\n") else "")

def normalize_md_file_headings(md_path) -> None:
    p = Path(md_path)
    text = p.read_text(encoding="utf-8")
    fixed = normalize_markdown_heading_levels(text)
    if fixed != text:
        p.write_text(fixed, encoding="utf-8")

def number_md_headings(md_path: str):
    p = Path(md_path)
    m = re.search(r'ch\s*(\d+)', p.stem, re.IGNORECASE)
    if not m:
        return

    base = int(m.group(1))
    counters = [0, 0, 0, 0, 0]  # for H2..H6

    out_lines = []
    with open(p, 'r', encoding='utf-8') as f:
        for line in f:
            m = HEADING_RE.match(line)
            if not m:
                out_lines.append(line)
                continue

            hashes, text = m.groups()
            level = len(hashes)

            if ALREADY_NUMBERED_RE.match(text):
                out_lines.append(line)
                continue

            if level == 1:
                numbered = f"{base}. {text}"
                out_lines.append(f"{hashes} {numbered}\n")
                counters = [0, 0, 0, 0, 0]
            else:
                idx = level - 2
                counters[idx] += 1
                for j in range(idx + 1, len(counters)):
                    counters[j] = 0
                parts = [str(base)] + [str(counters[k]) for k in range(idx + 1)]
                prefix = ".".join(parts)
                numbered = f"{prefix} {text}"
                out_lines.append(f"{hashes} {numbered}\n")

    with open(p, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
