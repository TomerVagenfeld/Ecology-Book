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

        # Fix double-dollar from nested conversions: $$...$ → $...$
        new_line = re.sub(r'\$\$([^$]+)\$\$', r'$\1$', new_line)
        # Fix adjacent dollars: $X$$Y$ → merge them
        # Pattern: $A$$B$ → $AB$
        new_line = re.sub(r'\$([^$]+)\$\$([^$]+)\$', r'$\1\2$', new_line)
        # Clean any remaining double $
        new_line = re.sub(r'(?<!\$)\$\$(?!\$)', '', new_line)

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
                # Wrap in display math
                out.append(f'$${latex}$$')
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


# ── Main ──────────────────────────────────────────────────────────────────

def cleanup_chapter(md_path: Path) -> bool:
    """Apply all cleanup passes to a chapter file. Returns True if modified."""
    text = md_path.read_text(encoding='utf-8')
    original = text

    # Apply passes in order
    text = remove_duplicate_figures(text)
    text = clean_broken_image_refs(text)
    text = convert_tilde_subscripts(text)
    text = convert_standalone_formulas_to_latex(text)

    if text != original:
        md_path.write_text(text, encoding='utf-8')
        return True
    return False


def main():
    md_dir = Path('book-source/md')
    files = sorted(md_dir.glob('ch*.md'))

    print(f"Cleaning up {len(files)} chapter files...")
    for f in files:
        changed = cleanup_chapter(f)
        status = "[FIXED]" if changed else "[OK]"
        print(f"  {status} {f.name}")

    print("\nDone!")


if __name__ == '__main__':
    main()
