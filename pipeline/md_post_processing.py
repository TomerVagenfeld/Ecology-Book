# md_post_processing.py
# Utilities that post-process Markdown files after Pandoc conversion but before Jupyter-Book.

from pathlib import Path
import re

# --- Regexes / heuristics ---
ALREADY_NUMBERED_RE = re.compile(r'^\d+(?:\.\d+)*\.?\s+')
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
                # Check if the next non-empty line could be part of the same English block
                lookahead = j + 1
                while lookahead < len(lines) and not lines[lookahead].strip():
                    lookahead += 1

                if lookahead < len(lines):
                    next_line = lines[lookahead]
                    # If next line is not a structural element and might be English, continue
                    if not (re.match(r'^\s*(```|~~~)', next_line) or
                           re.match(r'^\s*#(#+)?\s', next_line) or
                           re.match(r'^\s*>\s?', next_line) or
                           FOOTNOTE_DEF_RE.match(next_line) or
                           re.match(r'^\s*[-*+]\s', next_line) or
                           re.match(r'^\s*\d+\.\s', next_line)):
                        # Add empty line and continue to potentially group with next content
                        block.append(L)
                        j += 1
                        continue
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
                out.append(f"{indent}:::{{div}} .en-quote")
                out.append("")
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
                out.append(f"{indent}:::{{div}} .en-quote")
                out.append("")
                # Join the lines into a single paragraph with line breaks to prevent MyST from creating separate containers
                content_lines = [line for line in block if line.strip()]
                if content_lines:
                    # Use <br> tags for line breaks within a single paragraph
                    joined_content = "<br>".join(line.strip() for line in content_lines)
                    out.append(f"{indent}{joined_content}")
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
    fences. Anonymous containers (``:::`` without ``{directive}``) that don't
    provide option lines (``:class:``, ``:name:``, …) are dropped by skipping
    both their opening and closing fence while leaving the enclosed payload
    intact. Nested colon fences are handled correctly so that inner directives
    like ``:::{container}`` survive even when wrapped in an empty anonymous
    block.

    IMPORTANT: This function protects MyST figure blocks from being corrupted.
    """

    lines = md_text.splitlines()
    out: list[str] = []
    stack: list[dict[str, object]] = []
    in_figure_block = False

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

    def _is_in_figure_block(line_idx: int) -> bool:
        """Check if we're currently inside a MyST figure block."""
        # Look backwards to see if we're in a figure block
        for i in range(line_idx - 1, max(0, line_idx - 20), -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith("```{figure}"):
                # Found opening figure block, check if it's still open
                for j in range(i + 1, line_idx):
                    if j >= len(lines):
                        break
                    if lines[j].strip() == "```":
                        return False  # Figure block was closed
                return True  # Still in figure block
            elif line == "```" and not line.startswith("```{"):
                return False  # Found a closing fence
        return False

    for idx, line in enumerate(lines):
        # Check if we're in a figure block
        in_figure_block = _is_in_figure_block(idx)

        # Skip processing colon fences if we're inside a figure block
        if in_figure_block:
            out.append(line)
            continue

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


def fix_malformed_footnote_definitions(md_text: str) -> str:
    """Fix footnote definitions that are missing colons."""
    lines = md_text.splitlines()
    fixed_lines = []

    for line in lines:
        # Look for lines that start with [^number] but are missing the colon
        if re.match(r'^\[\^\d+\][^:]', line):
            # Insert a colon after the footnote number
            fixed_line = re.sub(r'^(\[\^\d+\])', r'\1:', line)
            fixed_lines.append(fixed_line)
            # print(f"Fixed malformed footnote: {line[:50]}... -> {fixed_line[:50]}...")
        # Also fix lines that might have weird formatting like [^1]text instead of [^1]: text
        elif re.match(r'^\[\^\w+\][^\s:]', line):
            # Insert a colon and space after the footnote number
            fixed_line = re.sub(r'^(\[\^\w+\])', r'\1: ', line)
            fixed_lines.append(fixed_line)
            # print(f"Fixed malformed footnote: {line[:50]}... -> {fixed_line[:50]}...")
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def remove_unreferenced_footnotes_file(md_path: str | Path) -> None:
    p = Path(md_path)
    text = p.read_text(encoding="utf-8")

    # First fix malformed footnote definitions
    text = fix_malformed_footnote_definitions(text)

    # Then remove unreferenced footnotes
    fixed = remove_unreferenced_footnotes(text)
    if fixed != text or text != p.read_text(encoding="utf-8"):
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

        # Strip footnote references from heading text (e.g. "[^41]")
        # Footnotes in headings break TOC titles and Sphinx can't resolve them
        rest = FOOTNOTE_REF_RE.sub('', rest).strip()

        if not first_h1 and level == 1:
            first_h1 = True
            # When promoting first heading to H1, strip subsection numbering (e.g., "1.1 " -> "1. ")
            rest_stripped = rest.strip()
            subsection_match = re.match(r'^(\d+)\.\d+\s+(.*)$', rest_stripped)
            if subsection_match:
                # Found subsection number like "1.1 Title" - convert to "1. Title"
                chapter_num, title_text = subsection_match.groups()
                rest_stripped = f"{chapter_num}. {title_text}"
            out.append("# " + rest_stripped)
        else:
            if level == 1:
                level = 2  # demote subsequent H1s to H2
            # Strip subsection numbering from H2 headers as well (e.g., "2.1 " -> "2. ")
            rest_stripped = rest.strip()
            if level == 2:
                subsection_match = re.match(r'^(\d+)\.\d+\s+(.*)$', rest_stripped)
                if subsection_match:
                    chapter_num, title_text = subsection_match.groups()
                    rest_stripped = f"{chapter_num}. {title_text}"
            out.append("#" * level + " " + rest_stripped)

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
                # Add chapter number to H1
                numbered = f"{base}. {text}"
                out_lines.append(f"{hashes} {numbered}\n")
                counters = [0, 0, 0, 0, 0]
            else:
                # Don't add subsection numbers to H2+ headers
                # Just keep the original text
                out_lines.append(line)

    with open(p, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)


def convert_container_to_div_blocks(md_text: str) -> str:
    """
    Convert existing :::{container} blocks to :::{div} blocks.
    This fixes the MyST syntax issue where container directive doesn't support :class: option.
    """
    lines = md_text.splitlines()
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for container block start
        container_match = re.match(r'^(\s*):::?\{container\}', line)
        if container_match:
            indent = container_match.group(1)
            # Replace container with div
            out.append(f"{indent}:::{{div}}")
            i += 1

            # Copy everything until the closing :::
            while i < len(lines):
                line = lines[i]
                if re.match(r'^\s*:::?\s*$', line):
                    # Found closing :::
                    out.append(line)
                    i += 1
                    break
                else:
                    out.append(line)
                    i += 1
        else:
            out.append(line)
            i += 1

    return "\n".join(out)


def convert_container_to_div_blocks_file(file_path: str) -> None:
    """Convert existing :::{container} blocks to :::{div} blocks in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    converted = convert_container_to_div_blocks(content)

    # Clean up orphaned container references that appear in figure captions
    # These are corrupted remnants from broken en_quote processing
    converted = re.sub(r'\s*:::\{container\}[^\n]*', '', converted)

    # Convert old :class: en_quote syntax to proper MyST syntax
    # Pattern: :::{div}\n:class: en_quote -> :::{div} .en-quote
    converted = re.sub(r':::?\{div\}\s*\n\s*:class:\s*en_quote', ':::{div} .en-quote', converted)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(converted)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filenames by removing excessive spaces and problematic characters.

    This handles files from external sources that may have:
    - Multiple consecutive spaces (e.g., "1.3  .jpg" -> "1.3.jpg")
    - Spaces before file extensions
    - Other whitespace issues

    Args:
        filename: The original filename (not a path, just the filename)

    Returns:
        Sanitized filename with cleaned spacing
    """
    # Remove spaces before file extension (e.g., "1.3  .jpg" -> "1.3.jpg")
    filename = re.sub(r'\s+\.', '.', filename)

    # Replace multiple consecutive spaces with a single space
    filename = re.sub(r'\s{2,}', ' ', filename)

    # Remove leading/trailing spaces
    filename = filename.strip()

    return filename


def sanitize_media_references(md_text: str) -> str:
    """
    Sanitize media file references in markdown text by fixing problematic filenames.

    This finds all media references (images, figures) and applies filename sanitization
    to ensure they work correctly with Jupyter Book.

    Handles:
    - Markdown image syntax: ![alt](path/file.jpg)
    - MyST figure blocks: ```{figure} path/file.jpg
    - HTML img tags: <img src="path/file.jpg">

    Args:
        md_text: Markdown content

    Returns:
        Markdown with sanitized media references
    """
    # Pattern to match markdown images: ![alt](path/to/file.ext)
    def fix_md_image(match):
        alt_text = match.group(1)
        full_path = match.group(2)

        # Split path and filename
        path_parts = full_path.rsplit('/', 1)
        if len(path_parts) == 2:
            path, filename = path_parts
            sanitized = sanitize_filename(filename)
            return f'![{alt_text}]({path}/{sanitized})'
        else:
            # No path, just filename
            sanitized = sanitize_filename(full_path)
            return f'![{alt_text}]({sanitized})'

    # Pattern to match MyST figure blocks: ```{figure} path/to/file.ext
    def fix_figure_block(match):
        full_path = match.group(1)

        # Split path and filename
        path_parts = full_path.rsplit('/', 1)
        if len(path_parts) == 2:
            path, filename = path_parts
            sanitized = sanitize_filename(filename)
            return f'```{{figure}} {path}/{sanitized}'
        else:
            # No path, just filename
            sanitized = sanitize_filename(full_path)
            return f'```{{figure}} {sanitized}'

    # Pattern to match HTML img tags: <img src="path/to/file.ext"
    def fix_html_img(match):
        full_path = match.group(1)

        # Split path and filename
        path_parts = full_path.rsplit('/', 1)
        if len(path_parts) == 2:
            path, filename = path_parts
            sanitized = sanitize_filename(filename)
            return f'<img src="{path}/{sanitized}"'
        else:
            # No path, just filename
            sanitized = sanitize_filename(full_path)
            return f'<img src="{sanitized}"'

    # Apply all fixes
    md_text = re.sub(r'!\[(.*?)\]\(([^)]+)\)', fix_md_image, md_text)
    md_text = re.sub(r'```\{figure\}\s+([^\s\n]+)', fix_figure_block, md_text)
    md_text = re.sub(r'<img\s+src="([^"]+)"', fix_html_img, md_text)

    return md_text


def sanitize_media_references_file(md_path: str | Path) -> None:
    """Apply media reference sanitization to a markdown file."""
    p = Path(md_path)
    text = p.read_text(encoding="utf-8")
    fixed = sanitize_media_references(text)
    if fixed != text:
        p.write_text(fixed, encoding="utf-8")
