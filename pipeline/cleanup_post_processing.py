#!/usr/bin/env python3
"""
Cross-chapter cleanup: LaTeX conversion, orphaned text removal, duplicate figure removal.
Run AFTER the main pipeline (on the md files in book-source/md/).
"""

import re
from pathlib import Path


# ── 1. Convert Pandoc subscript/superscript notation to LaTeX ──────────────

# Pattern: X~2~ → subscript, X^2^ → superscript (Pandoc markdown extensions)
# We convert these to inline $...$ LaTeX math when they appear in chemical/math contexts

# Common chemical formulas with subscripts/superscripts
CHEM_FORMULA_RE = re.compile(
    r'(?<!\[)'                    # not inside a footnote ref
    r'(?:'
    r'[A-Z][a-z]?'               # element symbol (1-2 chars)
    r'(?:~\d+~)?'                # optional subscript
    r'(?:\^[\d+\-]+\^)?'         # optional charge superscript
    r')+'
    r'(?:'                        # optional trailing group
    r'\([A-Za-z/]+\)'            # parenthesized group
    r'(?:~\d+~)?'
    r')*'
)

def convert_tilde_subscripts(text: str) -> str:
    """Convert Pandoc ~N~ subscript notation to LaTeX $_{N}$ in chemical contexts."""

    # Don't process inside code blocks
    lines = text.split('\n')
    out = []
    in_code = False
    in_figure = False

    for line in lines:
        # Track code blocks
        if re.match(r'^\s*```', line):
            if line.strip().startswith('```{figure}'):
                in_figure = True
            elif in_figure and line.strip() == '```':
                in_figure = False
            else:
                in_code = not in_code
            out.append(line)
            continue

        if in_code or in_figure:
            out.append(line)
            continue

        # Skip heading lines (footnotes are processed for chemical formulas)
        if re.match(r'^\s*#', line):
            out.append(line)
            continue

        # Convert inline chemical formulas with tilde subscripts
        # Pattern: CO~2~, CH~4~, N~2~O, H~2~CO~3~, SO~4~^2-^, etc.
        # We wrap the whole formula in $..$ and convert ~ to _ and ^ to ^

        # First pass: convert simple chemical subscripts like CO~2~ → $CO_2$
        # Match patterns like: ELEMENT~NUMBER~ (possibly chained)
        def replace_chem_formula(m):
            formula = m.group(0)
            # Convert tilde subscripts to LaTeX subscripts
            formula = re.sub(r'~(\d+)~', r'_{\1}', formula)
            # Convert caret superscripts to LaTeX
            formula = re.sub(r'\^([^~^]+?)\^', r'^{\1}', formula)
            # Handle special notation like ^-^ or ^2-^ or ^3-^
            return f'${formula}$'

        # Match chemical formulas containing tilde notation
        # This regex finds sequences that contain at least one ~N~ pattern
        # surrounded by chemical element-like context
        new_line = re.sub(
            r'(?<![`\[α-ωΑ-Ω])'  # not after code or footnote
            r'('
            r'(?:[A-Z][a-z]?(?:~\d+~)?(?:\^\d*[+\-]*\^)?){1,}'  # element + optional sub/super
            r'(?:\([A-Za-z/]+\)(?:~\d+~)?)*'  # optional parenthesized groups
            r')'
            r'(?=[\s,;.\)\]\}:ה-ת]|$)',  # followed by space, punct, Hebrew, or EOL
            lambda m: replace_chem_formula(m) if '~' in m.group(0) or '^' in m.group(0) else m.group(0),
            line
        )

        # Second pass: convert standalone scientific notation like 10^12^
        new_line = re.sub(
            r'(\d+)\^(\d+)\^',
            r'$\1^{\2}$',
            new_line
        )

        # Pass 2b: convert isotope mass numbers like ^239^Pu → $^{239}Pu$
        # Pattern: ^MASS^ELEMENT (isotope notation in nuclear physics)
        def replace_isotope(m):
            mass = m.group(1)
            elem = m.group(2)
            if elem.startswith('$'):
                # Already LaTeX: ^239^$U_{92}$ → $^{239}$$U_{92}$ → merge later
                return f'$^{{{mass}}}${elem}'
            else:
                return f'$^{{{mass}}}{elem}$'

        new_line = re.sub(
            r'\^(\d+)\^(\$?[A-Za-z]{1,2})',
            replace_isotope,
            new_line
        )

        # Pass 2c: convert unit exponents like m^3^, m^2^ → m$^{3}$
        new_line = re.sub(
            r'([a-zA-Z])\^(\d+)\^',
            r'\1$^{\2}$',
            new_line
        )

        # Third pass: convert remaining isolated ~N~ patterns in chemical context
        # like "N~2\ ~" → "$N_2$"
        new_line = re.sub(
            r'([A-Z][a-z]?)~(\d+)(?:\\?\s*)~',
            r'$\1_{\2}$',
            new_line
        )

        # Fourth pass: handle RTL-reversed patterns like ~3~O → $O_3$, ~2~SO → $SO_2$
        # These appear in Hebrew RTL text where Pandoc reverses the subscript order
        new_line = re.sub(
            r'~(\d+)~([A-Z][a-z]?)',
            r'$\2_{\1}$',
            new_line
        )

        # Fifth pass: handle ion charges like ^2-^ or ^-^ or ^+^ or ^3-^
        new_line = re.sub(
            r'\^(\d*[+\-]+)\^',
            lambda m: f'$^{{{m.group(1)}}}$',
            new_line
        )

        # Sixth pass: handle superscript dot like ^.^OH → $^\\cdot OH$
        new_line = re.sub(
            r'\^\.\^([A-Z])',
            r'$^{\\cdot}\1$',
            new_line
        )

        # Seventh pass: handle remaining ~N~ in footnote lines too
        # Match chemical context: element followed by tilde subscript
        # Also handle patterns like NO~X~ or NO~x~
        new_line = re.sub(
            r'([A-Z][a-z]?)~([A-Za-z\d]+)~',
            r'$\1_{\2}$',
            new_line
        )

        # Handle parenthesized subscript groups like (~3~(Cl/F/OH))
        new_line = re.sub(
            r'~(\d+)~(\()',
            r'$_{\1}$\2',
            new_line
        )

        # Fix adjacent dollars from nested conversions: $X$$Y$ → $XY$ (merge)
        new_line = re.sub(r'\$([^$]+)\$\$([^$]+)\$', r'$\1\2$', new_line)

        out.append(new_line)

    return '\n'.join(out)


def convert_standalone_formulas_to_latex(text: str) -> str:
    """Convert standalone formula lines (like 20TW = ...) to LaTeX display math."""
    lines = text.split('\n')
    out = []
    in_code = False
    in_figure = False

    for line in lines:
        if re.match(r'^\s*```', line):
            if '```{figure}' in line:
                in_figure = True
            elif in_figure and line.strip() == '```':
                in_figure = False
            else:
                in_code = not in_code
            out.append(line)
            continue

        if in_code or in_figure:
            out.append(line)
            continue

        # Convert blockquoted chemical equations to LaTeX display math
        # Pattern: > 2C(s) + O~2~(g) ↔ 2CO(g) + heat
        bq_match = re.match(r'^>\s*(.+)', line)
        if bq_match:
            content = bq_match.group(1).strip()
            # Check if it looks like a chemical equation (has ↔ or → and chemical elements)
            if ('↔' in content or '→' in content) and re.search(r'[A-Z][a-z]?(?:~\d|_\{?\d)', content):
                # Convert to LaTeX
                latex = content
                latex = re.sub(r'~(\d+)~', r'_{\1}', latex)
                latex = re.sub(r'\^([^~^]+?)\^', r'^{\1}', latex)
                latex = latex.replace('↔', r'\leftrightarrow')
                latex = latex.replace('→', r'\rightarrow')
                # Wrap in display math (delimiters must be on own lines for MyST)
                out.append('$$')
                out.append(latex)
                out.append('$$')
                continue

        out.append(line)

    return '\n'.join(out)


# ── 2. Remove orphaned text after figure blocks ──────────────────────────

def remove_orphaned_figure_text(text: str) -> str:
    """
    After a ```{figure}...``` block, remove duplicate text that repeats the caption.
    Also remove orphaned ![](media/...) image references.
    """
    lines = text.split('\n')
    out = []
    i = 0

    while i < len(lines):
        # Detect end of a figure block
        if (i > 0 and lines[i].strip() == '```' and
            any('```{figure}' in lines[j] for j in range(max(0, i-10), i))):
            out.append(lines[i])
            i += 1

            # Now scan ahead for orphaned text
            # Collect lines until we hit real content (a heading, another figure, or Hebrew paragraph)
            orphan_lines = []
            j = i
            while j < len(lines):
                line = lines[j].strip()

                # Empty line - might be between orphans
                if not line:
                    orphan_lines.append(j)
                    j += 1
                    continue

                # Orphaned image reference like ![](media/imageN.xxx)
                if re.match(r'^!\[\]\(media/', line):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # Single Hebrew letter (א, ב, etc.) used as figure part labels
                if re.match(r'^[אבגדהוזחט]$', line):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # Source/citation line that's a duplicate of caption
                # Check if it starts with typical citation patterns
                if (line.startswith('Source:') or
                    line.startswith('Documentation:') or
                    line.startswith('This data is subject') or
                    re.match(r'^Reprinted with permission', line) or
                    re.match(r'^<https?://', line) or
                    re.match(r'^https?://', line)):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # English citation/reference text that duplicates caption content
                # e.g., "Scheringer, M. et al. (2022) Stories of..."
                # or "Dutton A. et al. (2015). https://..."
                if re.match(r'^[A-Z][a-z]+ [A-Z].*(?:et al\.|https?://|\(\d{4}\))', line):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # Blockquoted sub-figure labels like "> ב."
                if re.match(r'^>\s*[אבגדהוזחט]\.$', line):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # Standalone "מקור" (source) lines
                if re.match(r'^מקור\s*[-–:—]?\s*$', line):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # Citation lines like "IPCC (2019)," or "IEA (2018) The Future..."
                if re.match(r'^(?:IPCC|IEA|FAO|UNEP|WHO|WMO|NOAA)\s*\(\d{4}\)', line):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # Copyright/permission lines
                if re.match(r'^Copyright\s*\{?\d{4}\}?', line) or line.startswith('CC BY'):
                    orphan_lines.append(j)
                    j += 1
                    continue

                # If it's a real content line (heading, figure, Hebrew paragraph, etc.), stop
                break

            # Only remove orphans if they're ALL non-content
            # Don't remove if we'd be removing real paragraphs
            if orphan_lines:
                # Keep lines that are NOT orphans
                for k in range(i, j):
                    if k not in orphan_lines:
                        out.append(lines[k])
                # Add back a blank line
                if out and out[-1].strip():
                    out.append('')
                i = j
            continue

        out.append(lines[i])
        i += 1

    return '\n'.join(out)


# ── 2b. Remove standalone orphaned source blocks ─────────────────────────

def remove_standalone_source_blocks(text: str) -> str:
    """
    Remove standalone 'מקור' (source) attribution blocks that appear outside
    figure blocks. These are Pandoc artifacts where source text got separated
    from the figure caption.
    """
    lines = text.split('\n')
    out = []
    in_figure = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Track figure blocks
        if '```{figure}' in stripped:
            in_figure = True
        elif in_figure and stripped == '```':
            in_figure = False

        if in_figure:
            out.append(line)
            i += 1
            continue

        # Detect standalone "מקור" block: "מקור:" or "מקור -" or "מקור --"
        # followed by URL/citation and/or "Reprinted with permission"
        if re.match(r'^מקור\s*[-–:—]*\s*$', stripped):
            # Scan ahead to find the extent of this source block
            block_lines = [i]
            j = i + 1
            while j < len(lines):
                s = lines[j].strip()
                if not s:
                    block_lines.append(j)
                    j += 1
                    continue
                if (re.match(r'^<https?://', s) or
                    re.match(r'^https?://', s) or
                    s.startswith('Reprinted with permission') or
                    re.match(r'^(?:IPCC|IEA|FAO|UNEP|WHO|WMO|NOAA)\s*\(\d{4}\)', s) or
                    s.startswith(';') or
                    s.startswith('CC BY')):
                    block_lines.append(j)
                    j += 1
                    continue
                break

            # Only remove if we found at least one citation/URL line (not just "מקור:")
            if len(block_lines) > 1:
                i = j
                # Ensure we don't leave extra blank lines
                if out and out[-1].strip() == '' and j < len(lines) and lines[j].strip() == '':
                    i = j + 1
                continue

        out.append(line)
        i += 1

    return '\n'.join(out)


# ── 2c. Deduplicate caption attributions ─────────────────────────────────

def deduplicate_captions(text: str) -> str:
    """
    Fix captions where source/attribution text appears twice in the same line.
    Example: "...FAO (2021) (FIG 20); CC BY...; Reprinted with permission. FAO (2021) (FIG 20)[^34]; CC BY...; Reprinted with permission."
    → Keep only the first occurrence (or the one with footnote ref).
    """
    lines = text.split('\n')
    out = []

    for line in lines:
        stripped = line.strip()

        # Only process caption lines inside figure blocks
        # Caption lines start with "איור X.Y:" or "טבלה X.Y:"
        if re.match(r'^(?:איור|טבלה)\s+\d+\.\d+', stripped):
            # Check for "Reprinted with permission" appearing twice
            rp_count = stripped.count('Reprinted with permission')
            if rp_count >= 2:
                # Find the pattern that's duplicated
                # Strategy: find "Reprinted with permission." and split there
                # Keep from start to first "Reprinted with permission." inclusive
                parts = stripped.split('Reprinted with permission')
                if len(parts) >= 3:
                    # Keep first part + "Reprinted with permission" + period
                    # The second occurrence and beyond are duplicates
                    first_part = parts[0] + 'Reprinted with permission.'
                    # Clean up trailing/leading artifacts
                    first_part = re.sub(r'\.\s*$', '.', first_part.strip())
                    out.append(first_part)
                    continue

            # Also check for other duplication patterns: same citation appearing twice
            # Find if a substantial segment (>40 chars) appears twice
            if len(stripped) > 100:
                # Try to find repeated segments
                half_len = len(stripped) // 2
                for seg_len in range(min(60, half_len), 30, -1):
                    for start in range(0, half_len):
                        segment = stripped[start:start + seg_len]
                        second_pos = stripped.find(segment, start + seg_len)
                        if second_pos != -1:
                            # Found a duplicate segment - remove from second occurrence
                            cleaned = stripped[:second_pos].rstrip()
                            # Make sure it ends properly
                            if not cleaned.endswith('.'):
                                cleaned += '.'
                            out.append(cleaned)
                            break
                    else:
                        continue
                    break
                else:
                    out.append(line)
                continue

        out.append(line)

    return '\n'.join(out)


# ── 2d. Clean Pandoc image artifacts in footnotes ────────────────────────

def clean_pandoc_image_artifacts(text: str) -> str:
    """
    Fix Pandoc artifacts where LaTeX formulas are embedded as image alt text
    with broken paths like ![FORMULA](media/imageN.png).
    Convert these to proper inline or display math.
    """
    # Pattern: ![LATEX_FORMULA](media/imageN.ext)
    # where the alt text contains LaTeX-like commands
    def replace_artifact(m):
        alt_text = m.group(1)
        # Check if the alt text looks like a LaTeX formula
        if any(cmd in alt_text for cmd in ['\\frac', '\\mathrm', '\\text{', '\\sum', '\\int']):
            # Clean up the LaTeX: remove double backslashes, fix escaped chars
            formula = alt_text.strip()
            formula = formula.replace('\\\\', '\\')
            formula = formula.replace('\\_{', '_{')
            formula = formula.replace('\\^{', '^{')
            formula = formula.replace('\\_', '_')
            formula = formula.replace('\\^', '^')
            return f'${formula}$'
        return ''  # remove non-formula image artifacts

    text = re.sub(
        r'!\[\s*((?:[^]]*\\(?:frac|mathrm|text|sum|int)[^]]*)?)\]\(media/image\d+\.\w+\)',
        replace_artifact,
        text
    )
    return text


# ── 3. Remove duplicate figure blocks ────────────────────────────────────

def remove_duplicate_figures(text: str) -> str:
    """Remove duplicate figure blocks (same name: fig X-N appearing twice)."""
    lines = text.split('\n')
    out = []
    seen_fig_names = set()
    i = 0

    while i < len(lines):
        # Check for figure block start
        if lines[i].strip().startswith('```{figure}'):
            # Find the name and end of this block
            block_start = i
            fig_name = None
            block_end = i

            for j in range(i+1, min(i+20, len(lines))):
                if lines[j].strip() == '```':
                    block_end = j
                    break
                name_match = re.match(r'^name:\s*(.+)', lines[j].strip())
                if name_match:
                    fig_name = name_match.group(1).strip()

            if fig_name and fig_name in seen_fig_names:
                # Skip this duplicate block
                i = block_end + 1
                continue

            if fig_name:
                seen_fig_names.add(fig_name)

            # Output the block
            for j in range(block_start, block_end + 1):
                out.append(lines[j])
            i = block_end + 1
            continue

        out.append(lines[i])
        i += 1

    return '\n'.join(out)


# ── 4. Clean broken image references ─────────────────────────────────────

def clean_broken_image_refs(text: str) -> str:
    """Remove orphaned ![](media/imageN.xxx) references that aren't inside figure blocks."""
    lines = text.split('\n')
    out = []
    in_figure = False

    for line in lines:
        if '```{figure}' in line:
            in_figure = True
        elif in_figure and line.strip() == '```':
            in_figure = False

        if in_figure:
            # Inside figure block - clean broken image refs from captions
            # Pattern: ![](media/imageN.ext) in caption → remove it
            line = re.sub(r'\s*!\[\]\(media/image\d+\.\w+\)\s*', ' ', line).strip()
            if '---' == line or line.startswith('height:') or line.startswith('name:'):
                pass  # keep metadata lines
            out.append(line)
            continue

        # Outside figure block - remove standalone broken image refs
        if re.match(r'^\s*!\[\]\(media/image\d+\.\w+\)\s*$', line):
            continue  # skip orphaned image refs

        # Also clean inline broken image refs (inside text, not standalone)
        line = re.sub(r'!\[\]\(media/image\d+\.\w+\)', '', line)

        out.append(line)

    return '\n'.join(out)


# ── 5. Convert standalone inline math to display math ─────────────────────

def convert_inline_to_display_math(text: str) -> str:
    """
    Convert standalone single-dollar formula lines to double-dollar display math.
    A line is standalone if the entire line (after stripping) is $formula$.
    Also merges fragmented inline math like $A$ + $B$ → $A + B$ on standalone lines.
    """
    lines = text.split('\n')
    out = []
    in_code = False
    in_figure = False

    for line in lines:
        stripped = line.strip()

        if re.match(r'^\s*```', line):
            if '```{figure}' in stripped:
                in_figure = True
            elif in_figure and stripped == '```':
                in_figure = False
            else:
                in_code = not in_code
            out.append(line)
            continue

        if in_code or in_figure:
            out.append(line)
            continue

        # Skip lines that are already display math
        if stripped.startswith('$$'):
            out.append(line)
            continue

        # Skip footnote definitions
        if stripped.startswith('[^'):
            out.append(line)
            continue

        # Pattern 1: Entire line is a single $formula$
        m = re.match(r'^\$([^$]+)\$$', stripped)
        if m:
            out.append('$$')
            out.append(m.group(1))
            out.append('$$')
            continue

        # Pattern 2: Fragmented formulas like "$A$ + $B$ ↔ $C$"
        # where the line contains only math fragments and operators
        # Check if the line is composed entirely of $...$, operators, numbers, parens, etc.
        if stripped.startswith('$') and '$' in stripped:
            # Remove all $...$ fragments and see what's left
            remaining = re.sub(r'\$[^$]+\$', '', stripped)
            remaining = remaining.strip()
            # If what's left is only operators, numbers, element symbols, parens, arrows, spaces
            if remaining and re.match(r'^[\s+\-↔→←=\d()A-Za-z,.\\\\/]*$', remaining):
                # Check it has at least one arrow/operator suggesting it's a formula
                if '↔' in stripped or '→' in stripped or '←' in stripped or '\\leftrightarrow' in stripped or '\\rightarrow' in stripped:
                    # Merge into single display math
                    merged = stripped
                    # Remove internal dollar signs to merge
                    merged = re.sub(r'\$\s*\$', ' ', merged)  # $..$ $..$ → merge
                    merged = merged.strip('$').strip()
                    # Convert text arrows to LaTeX
                    merged = merged.replace('↔', r'\leftrightarrow')
                    merged = merged.replace('→', r'\rightarrow')
                    merged = merged.replace('←', r'\leftarrow')
                    out.append('$$')
                    out.append(merged)
                    out.append('$$')
                    continue

        out.append(line)

    return '\n'.join(out)


# ── 6. Fix display math delimiters ────────────────────────────────────────

def fix_display_math_delimiters(text: str) -> str:
    """
    MyST dollarmath requires $$ on their own lines for display math.
    Fix cases where $$content$$ is on a single line → split to 3 lines.
    Also fix broken mixed formulas like $$A$ + $B$$ → proper display math.
    """
    lines = text.split('\n')
    out = []
    in_code = False
    in_figure = False

    for line in lines:
        stripped = line.strip()

        if re.match(r'^\s*```', line):
            if '```{figure}' in stripped:
                in_figure = True
            elif in_figure and stripped == '```':
                in_figure = False
            else:
                in_code = not in_code
            out.append(line)
            continue

        if in_code or in_figure:
            out.append(line)
            continue

        # Match $$content$$ on single line (content between $$ markers)
        m = re.match(r'^(\s*)\$\$(.+)\$\$\s*$', line)
        if m:
            indent = m.group(1)
            content = m.group(2).strip()
            # Clean internal $ signs (broken formulas like $$A$ + $B$$)
            content = re.sub(r'\$\s*\$', ' ', content)
            content = content.strip('$').strip()
            out.append(f'{indent}$$')
            out.append(f'{indent}{content}')
            out.append(f'{indent}$$')
            continue

        out.append(line)

    return '\n'.join(out)


# ── 7. Fix EMF image references ──────────────────────────────────────────

def fix_emf_references(text: str, media_dir: Path) -> str:
    """Replace .emf figure references with .jpg or .png alternatives."""
    def replace_emf(m):
        emf_path = m.group(1)
        base = emf_path.rsplit('.', 1)[0]
        # Check for jpg/png alternatives
        for ext in ('.jpg', '.png', '.jpeg'):
            alt_path = media_dir / (Path(base).name + ext)
            if alt_path.exists():
                return f'```{{figure}} {base}{ext}'
        return m.group(0)  # keep original if no alternative

    return re.sub(r'```\{figure\}\s*(.*?\.emf)', replace_emf, text)


# ── Main ──────────────────────────────────────────────────────────────────

def cleanup_chapter(md_path: Path) -> bool:
    """Apply all cleanup passes to a chapter file. Returns True if modified."""
    text = md_path.read_text(encoding='utf-8')
    original = text

    # Determine media directory for EMF lookup
    media_dir = md_path.parent / 'media'

    # Apply passes in order
    text = remove_duplicate_figures(text)
    text = remove_orphaned_figure_text(text)
    text = remove_standalone_source_blocks(text)
    text = deduplicate_captions(text)
    text = clean_broken_image_refs(text)
    text = clean_pandoc_image_artifacts(text)
    text = convert_tilde_subscripts(text)
    text = convert_standalone_formulas_to_latex(text)
    text = convert_inline_to_display_math(text)
    text = fix_display_math_delimiters(text)
    text = fix_emf_references(text, media_dir)

    if text != original:
        md_path.write_text(text, encoding='utf-8')
        return True
    return False


def main():
    from settings import MD_DIR
    files = sorted(MD_DIR.glob('ch*.md'))

    print(f"Cleaning up {len(files)} chapter files...")
    for f in files:
        changed = cleanup_chapter(f)
        status = "[FIXED]" if changed else "[OK]"
        print(f"  {status} {f.name}")

    print("\nDone!")


if __name__ == '__main__':
    main()
