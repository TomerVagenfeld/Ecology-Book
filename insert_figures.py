# insert_figures.py
from __future__ import annotations
import re, shutil, os
from pathlib import Path
from typing import Optional

# --- caption/figure detection -------------------------------------------------

# Hebrew figure/table keywords
_CAPTION_START_RE = re.compile(r'^\s*(איור|טבלה)\s+(\d+)\.(\d+)([a-zA-Z]*)\s*[:：־-]?\s*(.*)$')
# Matches a bare caption line like: "איור 7.1: some text"
# groups: (kind, chap, num, suffix, rest_of_line)

# Pandoc image artifact (very permissive)
_IMG_LINE_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

# If the caption continues on following lines, we gather until a blank line or another block starts.
_STOP_BLOCK_RE = re.compile(r'^\s*($|#{1,6}\s|```|~~~|> |\[\^|\!\[)')

# Caption tails that indicate a missing source
_SOURCE_SUFFIX_RE = re.compile(r'(מקור)\s*[:：־–—-]*\s*$', re.UNICODE)

# Extensions preference
_PREFERRED_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".svg", ".pdf"]

def _clean_caption_lines(lines: list[str]) -> str:
    """Join caption lines, normalize whitespace, keep Hebrew and footnotes intact."""
    txt = " ".join(s.strip() for s in lines if s.strip())
    # collapse double spaces
    txt = re.sub(r'\s{2,}', ' ', txt)
    return txt.strip()

def _figure_key(ch: str, n: str, suffix: str) -> str:
    """Canonical key used to search assets (e.g., '7.1a' or '7.1')."""
    return f"{int(ch)}.{int(n)}{suffix or ''}"

def _slug_output_filename(ch: str, n: str, suffix: str, ext: str) -> str:
    # 7.1 → 7_1 ; 7.1a → 7_1a
    core = f"{int(ch)}_{int(n)}{suffix or ''}"
    return f"{core}{ext.lower()}"

def _best_asset_for_figure(fig_key: str, assets_dir: Path) -> Optional[Path]:
    """Find best matching asset for the figure key (like '7.1' or '7.1a')."""
    cand: list[Path] = []
    key_escaped = re.escape(fig_key)
    # accept filenames that *start with* key or contain it delimited by non-word
    pat = re.compile(rf'(^|[^\d]){key_escaped}([^\d]|$)', re.IGNORECASE)
    for p in assets_dir.iterdir():
        if not p.is_file():
            continue
        if pat.search(p.name):
            cand.append(p)

    if not cand:
        # fallback: accept filenames where digits are separated by non-digits, e.g., '7_1'
        alt = re.compile(rf'(^|[^\d]){re.escape(fig_key.replace(".", "_"))}([^\d]|$)', re.IGNORECASE)
        for p in assets_dir.iterdir():
            if p.is_file() and alt.search(p.name):
                cand.append(p)

    if not cand:
        return None

    # pick by extension preference; if multiple of same ext, choose shortest filename
    def pref_score(p: Path) -> tuple[int, int]:
        ext = p.suffix.lower()
        try:
            rank = _PREFERRED_EXTS.index(ext)
        except ValueError:
            rank = 999
        return (rank, len(p.name))

    cand.sort(key=pref_score)
    return cand[0]

def _collect_block(lines: list[str], start: int) -> tuple[int, list[str]]:
    """Collect a multi-line caption block starting at `start` (inclusive)."""
    out = [lines[start]]
    i = start + 1
    while i < len(lines):
        L = lines[i]
        if _STOP_BLOCK_RE.match(L):
            break
        out.append(L)
        i += 1
    return i, out

def _collect_source_lines(lines: list[str], start: int) -> tuple[int, int, list[str]]:
    """Collect source/credit lines that immediately follow a caption block."""
    cursor = start
    remove_start = start

    # consume blank lines immediately after the caption block
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1

    src_lines: list[str] = []
    while cursor < len(lines):
        L = lines[cursor]
        if not L.strip():
            break
        if _CAPTION_START_RE.match(L):
            break
        if _STOP_BLOCK_RE.match(L):
            break
        src_lines.append(L.strip())
        cursor += 1

    if not src_lines:
        return start, start, []

    return remove_start, cursor, src_lines

def _merge_caption_with_source(caption: str, source_lines: list[str]) -> str:
    if not source_lines:
        return caption

    source_text = " ".join(s.strip() for s in source_lines if s.strip())
    if not source_text:
        return caption

    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)} – "

    new_caption = _SOURCE_SUFFIX_RE.sub(repl, caption)
    if new_caption == caption:
        # fallback: append with spacing
        if caption.endswith(" "):
            return caption + source_text
        return caption + " " + source_text

    if not new_caption.endswith(" "):
        new_caption += " "
    return new_caption + source_text

def _find_nearby_image(lines: list[str], start: int, max_distance: int = 6) -> tuple[Optional[int], Optional[str]]:
    """Search up to `max_distance` lines below AND above for a pandoc image artifact."""
    # below
    for j in range(start, min(len(lines), start + 1 + max_distance)):
        m = _IMG_LINE_RE.search(lines[j])
        if m:
            return j, m.group(1).strip()
    # above (in case image appeared first)
    for j in range(max(0, start - max_distance), start):
        m = _IMG_LINE_RE.search(lines[j])
        if m:
            return j, m.group(1).strip()
    return None, None

def _emit_figure_block(media_rel_path: str, height_px: int, name: str, caption: str) -> list[str]:
    return [
        f"```{{figure}} {media_rel_path}",
        "---",
        f"height: {height_px}px",
        f"name: {name}",
        "---",
        caption,
        "```",
        "",  # blank line after block
    ]

def process_markdown_insert_figures(
    md_path: str | Path,
    assets_dir: str | Path,
    media_dir: str | Path,
    default_height_px: int = 400,
) -> None:
    """
    Find captions (איור/טבלה), match a nearby pandoc image artifact, replace both
    with a MyST figure block that points to a copied asset under media_dir.
    """
    md_path = Path(md_path)
    assets_dir = Path(assets_dir)
    media_dir = Path(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)

    lines = md_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = lines[:]  # we will edit in-place using indices we compute

    i = 0
    # We’ll collect replacements as (start_idx, end_idx_exclusive, replacement_lines)
    patches: list[tuple[int, int, list[str]]] = []

    while i < len(lines):
        L = lines[i]
        m = _CAPTION_START_RE.match(L)
        if not m:
            i += 1
            continue

        kind, ch, num, suffix, first_rest = m.groups()
        block_end, cap_block = _collect_block(lines, i)

        # Find image near the caption
        img_idx, img_href = _find_nearby_image(lines, i, max_distance=8)
        if img_idx is None or not img_href:
            # no artifact found near this caption; skip
            i = block_end
            continue

        # Build caption text (caption lines + any inline text after the artifact line)
        caption_text = _clean_caption_lines(cap_block)

        source_start = block_end
        source_end = block_end
        if _SOURCE_SUFFIX_RE.search(caption_text):
            src_remove_start, src_end, src_lines = _collect_source_lines(lines, block_end)
            if src_lines:
                caption_text = _merge_caption_with_source(caption_text, src_lines)
                source_start = src_remove_start
                source_end = src_end

        # Best asset selection
        key = _figure_key(ch, num, suffix or "")
        asset = _best_asset_for_figure(key, assets_dir)
        if asset is None:
            # fallback: keep original artifact, but still place caption underneath as plain text
            i = block_end
            continue

        # Copy to media with canonical name
        out_ext = (asset.suffix or ".jpg").lower()
        out_name = _slug_output_filename(ch, num, suffix or "", out_ext)
        target = media_dir / out_name
        if asset.resolve() != target.resolve():
            shutil.copy2(asset, target)

        # Prepare figure MyST block (path relative to the MD file’s folder)
        fig_name = f"fig {int(ch)}-{int(num)}{suffix or ''}"
        rel_media_dir = os.path.relpath(media_dir, md_path.parent).replace("\\", "/")
        rel_media = f"{rel_media_dir}/{out_name}"
        figure_block = _emit_figure_block(rel_media, default_height_px, fig_name, caption_text)

        # Decide patch range: remove caption block and the artifact line (wherever it is)
        start = min(i, img_idx, source_start)
        end = max(block_end, img_idx + 1, source_end)
        patches.append((start, end, figure_block))

        i = max(block_end, source_end)  # continue scan after caption/source block

    # Apply patches from bottom to top to keep indices valid
    if patches:
        patches.sort(key=lambda t: t[0], reverse=True)
        for start, end, repl in patches:
            out[start:end] = repl

        md_path.write_text("\n".join(out) + ("\n" if out and not out[-1].endswith("\n") else ""), encoding="utf-8")
