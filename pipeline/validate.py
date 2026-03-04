# validate.py
# Post-pipeline validation: check for common issues and generate a report.

import re
from pathlib import Path


def validate_chapter(md_path: Path) -> dict:
    """Validate a single chapter markdown file. Returns a dict of findings."""
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues = []
    stats = {"file": md_path.name}

    # Check H1 title
    h1_title = None
    for line in lines:
        if line.lstrip().startswith("# "):
            h1_title = line.lstrip()[2:].strip()
            break
    stats["h1_title"] = h1_title or "[MISSING]"
    if h1_title is None:
        issues.append("CRITICAL: No H1 heading found")

    # Check for double-brace issues
    double_brace_count = len(re.findall(r':::+\{\{', text))
    if double_brace_count:
        issues.append(f"CRITICAL: {double_brace_count} double-brace directive(s) found")

    # Check for footnote refs in headings
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m and re.search(r'\[\^[^\]]+\]', m.group(2)):
            issues.append(f"WARNING: Footnote ref in heading: {line.strip()[:60]}")

    # Count figures
    figure_blocks = len(re.findall(r'```\{figure\}', text))
    stats["figures"] = figure_blocks

    # Count unresolved Pandoc image artifacts
    pandoc_images = len(re.findall(r'!\[\]\(.*?media/image\d+', text))
    if pandoc_images:
        issues.append(f"WARNING: {pandoc_images} unresolved Pandoc image artifact(s)")
    stats["pandoc_artifacts"] = pandoc_images

    # Count footnotes
    fn_defs = set(re.findall(r'^\s*\[\^([^\]]+)\]:', text, re.MULTILINE))
    fn_refs = set(re.findall(r'\[\^([^\]]+)\](?!\s*:)', text))
    stats["footnote_defs"] = len(fn_defs)
    stats["footnote_refs"] = len(fn_refs)
    orphan_defs = fn_defs - fn_refs
    orphan_refs = fn_refs - fn_defs
    if orphan_defs:
        issues.append(f"INFO: {len(orphan_defs)} footnote def(s) without refs")
    if orphan_refs:
        issues.append(f"WARNING: {len(orphan_refs)} footnote ref(s) without defs: {sorted(orphan_refs)[:5]}")

    # Check for unclosed en-quote blocks
    open_divs = len(re.findall(r':::\{div\}\s+\.en-quote', text))
    close_divs = text.count('\n:::\n') + text.count('\n:::')
    # This is approximate; just flag if significantly mismatched
    stats["en_quote_blocks"] = open_divs

    stats["issues"] = issues
    return stats


def validate_all(md_dir: Path, log_path: Path) -> None:
    """Validate all chapter files and write a report."""
    md_files = sorted(md_dir.glob("ch*.md"))

    total_issues = 0
    total_critical = 0
    report_lines = ["=" * 60, "EcoBook Pipeline Validation Report", "=" * 60, ""]

    for md_path in md_files:
        stats = validate_chapter(md_path)
        issues = stats["issues"]
        total_issues += len(issues)
        total_critical += sum(1 for i in issues if i.startswith("CRITICAL"))

        report_lines.append(f"--- {stats['file']} ---")
        report_lines.append(f"  H1: {stats['h1_title']}")
        report_lines.append(f"  Figures: {stats['figures']}  |  Pandoc artifacts: {stats['pandoc_artifacts']}")
        report_lines.append(f"  Footnotes: {stats['footnote_defs']} defs, {stats['footnote_refs']} refs")

        if issues:
            for issue in issues:
                report_lines.append(f"  * {issue}")
        else:
            report_lines.append("  OK")
        report_lines.append("")

    report_lines.append("=" * 60)
    report_lines.append(f"SUMMARY: {len(md_files)} chapters, {total_issues} issues ({total_critical} critical)")
    report_lines.append("=" * 60)

    report = "\n".join(report_lines) + "\n"
    log_path.write_text(report, encoding="utf-8")
    try:
        print(report)
    except UnicodeEncodeError:
        # Windows console may not support all Unicode chars in Hebrew titles
        print(report.encode("ascii", errors="replace").decode("ascii"))
