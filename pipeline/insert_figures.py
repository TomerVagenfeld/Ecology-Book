# insert_figures.py
# Find Hebrew figure/table captions in Markdown, match to asset files,
# and replace with MyST figure blocks.

from __future__ import annotations
import re, shutil, os
from pathlib import Path
from typing import Optional

from figure_catalog import build_catalog_for_chapter, save_catalog_images, FigureInfo

# --- caption/figure detection -------------------------------------------------

# Hebrew figure/table keywords - colon/punctuation REQUIRED
_CAPTION_START_RE = re.compile(
    r'^\s*(איור|טבלה)\s+(\d+)\.(\d+)([a-zA-Z]*)\s*[:：－–—-]\s*(.*)$'
)

# Pandoc image artifact
_IMG_LINE_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

# Block terminators
_STOP_BLOCK_RE = re.compile(r'^\s*($|#{1,6}\s|```|~~~|:::\s|> |\[\^|\!\[)')

# Source attribution patterns
_SOURCE_SUFFIX_RE = re.compile(r'(מקור)\s*[:：－–—-]*\s*$', re.UNICODE)
_SOURCE_LINE_RE = re.compile(
    r'^(?:מקור|מקורות|קרדיט|צילום|מקורן|Source|Credit|Photo)[\s:：־–—-]',
    re.IGNORECASE,
)
_LOOSE_SOURCE_LINE_RE = re.compile(
    r'(מקור|מקורות|קרדיט|צילום|מקורן|Source|Credit|Photo|Reprinted|permission|OECD|FAO|IPCC)',
    re.IGNORECASE,
)

# Extensions preference
_PREFERRED_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".svg"]


def _clean_caption_lines(lines: list[str]) -> str:
    txt = " ".join(s.strip() for s in lines if s.strip())
    return re.sub(r'\s{2,}', ' ', txt).strip()


def _figure_key(ch: str, n: str, suffix: str) -> str:
    return f"{int(ch)}.{int(n)}{suffix or ''}"


def _slug_output_filename(ch: str, n: str, suffix: str, ext: str) -> str:
    core = f"{int(ch)}_{int(n)}{suffix or ''}"
    return f"{core}{ext.lower()}"


def _best_asset_for_figure(fig_key: str, assets_dir: Path) -> Optional[Path]:
    """Find best matching asset file for a figure key like '7.1' or '7.1a'.

    Searches by numeric prefix, handling edge cases like:
    - "7.1 description.jpg"
    - "1.3  .jpg" (extra spaces)
    - "9.3download.jpg" (no space)
    - "9.1.download.jpg" (dot separator)
    - "11.1 TABLE.jpg" vs "11.1.jpg" (same number, different files)
    """
    cand: list[Path] = []

    # Build patterns from most specific to least
    escaped = re.escape(fig_key)
    patterns = [
        # Exact stem match: "7.1.jpg" -> stem "7.1"
        re.compile(rf'^{escaped}$', re.IGNORECASE),
        # Key + space + anything: "7.1 description.jpg"
        re.compile(rf'^{escaped}\s', re.IGNORECASE),
        # Key + non-alphanumeric separator: "7.1_x.jpg", "7.1-x.jpg"
        re.compile(rf'^{escaped}[^\w\s]', re.IGNORECASE),
        # Key directly followed by alpha (no separator): "9.3download.jpg"
        re.compile(rf'^{escaped}[a-zA-Z]', re.IGNORECASE),
        # Key with dot separator: "9.1.download.jpg"
        re.compile(rf'^{escaped}\.(?!\d)', re.IGNORECASE),
    ]

    # Also try underscore variant: "7_1" instead of "7.1"
    underscore_key = fig_key.replace('.', '_')
    escaped_u = re.escape(underscore_key)
    patterns.extend([
        re.compile(rf'^{escaped_u}$', re.IGNORECASE),
        re.compile(rf'^{escaped_u}[\s\W]', re.IGNORECASE),
    ])

    for p in assets_dir.iterdir():
        if not p.is_file():
            continue
        # Skip non-image files (docx, pdf) unless no image alternative
        stem = p.stem.strip()
        for pattern in patterns:
            if pattern.search(stem):
                cand.append(p)
                break

    if not cand:
        return None

    # Prefer images over documents; among images prefer by extension order; then shortest name
    def pref_score(p: Path) -> tuple[int, int, int]:
        ext = p.suffix.lower()
        # Strongly prefer image formats over documents
        if ext in ('.docx', '.pdf', '.xlsx'):
            type_rank = 100
        else:
            type_rank = 0
        try:
            ext_rank = _PREFERRED_EXTS.index(ext)
        except ValueError:
            ext_rank = 50
        return (type_rank, ext_rank, len(p.name))

    cand.sort(key=pref_score)
    return cand[0]


def _collect_block(lines: list[str], start: int) -> tuple[int, list[str]]:
    """Collect a multi-line caption block."""
    out = [lines[start]]
    i = start + 1
    while i < len(lines):
        L = lines[i]
        if _STOP_BLOCK_RE.match(L):
            break
        if _CAPTION_START_RE.match(L):
            break
        out.append(L)
        i += 1
    return i, out


def _collect_source_lines(
    lines: list[str], start: int, *, force: bool = False
) -> tuple[int, int, list[str]]:
    """Collect source/credit lines after a caption block."""
    cursor = start
    remove_start = start

    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1

    if cursor >= len(lines):
        return start, start, []

    first = lines[cursor].strip()
    has_strict_source = _SOURCE_LINE_RE.match(first)
    has_loose_source = _LOOSE_SOURCE_LINE_RE.search(first)

    if not force and not has_strict_source and not has_loose_source:
        return start, start, []

    src_lines: list[str] = [first]
    cursor += 1

    while cursor < len(lines):
        L = lines[cursor]
        if not L.strip():
            if cursor + 1 < len(lines) and not lines[cursor + 1].strip():
                break
            cursor += 1
            continue
        if _CAPTION_START_RE.match(L) or _STOP_BLOCK_RE.match(L):
            break
        if _LOOSE_SOURCE_LINE_RE.search(L.strip()) or len(src_lines) < 3:
            src_lines.append(L.strip())
            cursor += 1
        else:
            break

    return remove_start, cursor, src_lines


def _merge_caption_with_source(caption: str, source_lines: list[str]) -> str:
    if not source_lines:
        return caption
    source_text = " ".join(s.strip() for s in source_lines if s.strip())
    if not source_text:
        return caption

    new_caption = _SOURCE_SUFFIX_RE.sub(lambda m: f"{m.group(1)} – ", caption)
    if new_caption == caption:
        return caption + " " + source_text if not caption.endswith(" ") else caption + source_text

    if not new_caption.endswith(" "):
        new_caption += " "
    return new_caption + source_text


def _find_nearby_image_below(lines: list[str], start: int, max_distance: int = 8) -> tuple[Optional[int], Optional[str]]:
    """Search ONLY BELOW for a Pandoc image artifact (prevents mis-matching)."""
    for j in range(start, min(len(lines), start + 1 + max_distance)):
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
        "",
    ]


def process_markdown_insert_figures(
    md_path: str | Path,
    assets_dir: str | Path,
    media_dir: str | Path,
    default_height_px: int = 400,
    raw_dir: Optional[Path] = None,
) -> None:
    """Find captions, match to assets, replace with MyST figure blocks.

    Optionally uses a DOCX-based catalog (from raw_dir) for richer caption info.
    """
    md_path = Path(md_path)
    assets_dir = Path(assets_dir)
    media_dir = Path(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)

    # Try to determine chapter number from filename
    ch_match = re.search(r'ch\s*(\d+)', md_path.stem, re.IGNORECASE)
    chapter_num = int(ch_match.group(1)) if ch_match else None

    # Build DOCX catalog and extract embedded images
    catalog: dict[str, FigureInfo] = {}
    docx_images: dict[str, Path] = {}  # key -> saved image path
    if raw_dir and chapter_num is not None:
        try:
            catalog = build_catalog_for_chapter(raw_dir, chapter_num)
            if catalog:
                docx_images = save_catalog_images(catalog, media_dir)
                extracted = sum(1 for v in docx_images.values() if v)
                print(f"  [catalog] {len(catalog)} figures in DOCX, {extracted} images extracted for ch{chapter_num}")
        except Exception as e:
            print(f"  [catalog] Warning: Could not build catalog for ch{chapter_num}: {e}")

    lines = md_path.read_text(encoding="utf-8").splitlines()
    patches: list[tuple[int, int, list[str]]] = []

    i = 0
    while i < len(lines):
        L = lines[i]
        m = _CAPTION_START_RE.match(L)
        if not m:
            i += 1
            continue

        kind, ch, num, suffix, first_rest = m.groups()
        key = _figure_key(ch, num, suffix or "")
        block_end, cap_block = _collect_block(lines, i)

        # Use DOCX catalog caption if available (richer info), else use MD
        if key in catalog:
            caption_text = f"{catalog[key].kind} {key}: {catalog[key].caption}"
        else:
            caption_text = _clean_caption_lines(cap_block)

        # Collect source attribution
        want_source = bool(_SOURCE_SUFFIX_RE.search(caption_text))
        src_remove_start, src_end, src_lines = _collect_source_lines(
            lines, block_end, force=want_source
        )
        if src_lines:
            caption_text = _merge_caption_with_source(caption_text, src_lines)

        # Find nearby Pandoc image artifact (ONLY search below)
        img_idx, img_href = _find_nearby_image_below(lines, i, max_distance=8)

        # Resolve image: prefer DOCX-extracted, then fall back to figs directory
        if key in docx_images and docx_images[key].exists():
            # Image was extracted directly from DOCX — perfect match guaranteed
            target = docx_images[key]
            out_name = target.name
        else:
            # Fall back to asset files in figs directory
            asset = _best_asset_for_figure(key, assets_dir)
            if asset is None:
                print(f"  [WARN] No asset found for {key} in {md_path.name}")
                out_name = _slug_output_filename(ch, num, suffix or "", ".jpg")
            else:
                out_ext = (asset.suffix or ".jpg").lower()
                out_name = _slug_output_filename(ch, num, suffix or "", out_ext)
                target = media_dir / out_name
                if asset.resolve() != target.resolve():
                    shutil.copy2(asset, target)

        rel_media_dir = os.path.relpath(media_dir, md_path.parent).replace("\\", "/")
        rel_media = f"{rel_media_dir}/{out_name}"

        fig_name = f"fig {int(ch)}-{int(num)}{suffix or ''}"
        figure_block = _emit_figure_block(rel_media, default_height_px, fig_name, caption_text)

        # Determine patch range
        source_start = src_remove_start if src_lines else block_end
        source_end = src_end if src_lines else block_end

        if img_idx is not None:
            start = min(i, img_idx, source_start)
            end = max(block_end, img_idx + 1, source_end)
        else:
            start = min(i, source_start)
            end = max(block_end, source_end)

        # Expand to swallow adjacent Pandoc image artifacts (forward only)
        scan = end
        while scan < len(lines) and scan <= end + 3:
            line = lines[scan]
            if _CAPTION_START_RE.match(line):
                break
            if _IMG_LINE_RE.search(line) or not line.strip():
                end = max(end, scan + 1)
                scan += 1
            else:
                break

        patches.append((start, end, figure_block))
        i = max(block_end, source_end)

    # Apply patches bottom-to-top
    if patches:
        out = lines[:]
        patches.sort(key=lambda t: t[0], reverse=True)
        for start, end, repl in patches:
            out[start:end] = repl

        result = "\n".join(out)
        if not result.endswith("\n"):
            result += "\n"
        md_path.write_text(result, encoding="utf-8")
        print(f"  [figures] {len(patches)} figures inserted in {md_path.name}")
    else:
        print(f"  [figures] No captions found in {md_path.name}")
