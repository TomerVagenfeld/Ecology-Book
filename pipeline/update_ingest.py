"""
update_ingest.py - Phase 1 of the author update workflow.

Reads from the author's H: drive source (read-only), compares against the
local pipeline/book-source/raw/, copies only changed/new files to a timestamped
staging directory, and generates a human-readable diff report.

Usage:
    python pipeline/update_ingest.py
    python pipeline/update_ingest.py --source "H:\\some\\other\\path"
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from settings import (
    ASSETS_DIR,
    BOOK_ROOT,
    REPO_ROOT,
    SOURCE_AUTHOR,
    SOURCE_RAW_INPUT,
)

STAGING_ROOT = BOOK_ROOT / "staging"
FIGS_SUBDIR = "_figs ch. 1-14 - 120 figs & tables"
KNOWN_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".docx", ".webp"}
MANUAL_CONVERT_EXTENSIONS = {".pptx", ".xlsx"}


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# DOCX analysis
# ---------------------------------------------------------------------------

def analyze_docx(source_root: Path, local_raw: Path) -> list[dict]:
    source_files = {p.name: p for p in source_root.glob("*.docx")}
    local_files = {p.name: p for p in local_raw.glob("*.docx")}

    results = []
    all_names = sorted(set(source_files) | set(local_files))

    for name in all_names:
        if name not in source_files:
            results.append({"name": name, "status": "REMOVED", "staged": False})
            continue

        src = source_files[name]
        src_size = src.stat().st_size

        if name not in local_files:
            results.append({
                "name": name,
                "status": "NEW",
                "source_path": str(src),
                "src_size": src_size,
                "local_size": None,
                "hash_match": False,
                "staged": False,
            })
            continue

        loc = local_files[name]
        loc_size = loc.stat().st_size

        try:
            src_hash = hash_file(src)
            loc_hash = hash_file(loc)
            match = src_hash == loc_hash
        except OSError as e:
            results.append({
                "name": name,
                "status": "ERROR",
                "error": str(e),
                "staged": False,
            })
            continue

        results.append({
            "name": name,
            "status": "UNCHANGED" if match else "CHANGED",
            "source_path": str(src),
            "src_size": src_size,
            "local_size": loc_size,
            "hash_match": match,
            "staged": False,
        })

    return results


# ---------------------------------------------------------------------------
# Figure analysis
# ---------------------------------------------------------------------------

def _canonical_slug(filename: str) -> str:
    """Convert author figure name to canonical pipeline slug.

    E.g. '2.1 Planetary Boundaries.jpg' -> '2_1.jpg'
         '11.7.pdf' -> '11_7.pdf'
    """
    stem = Path(filename).stem
    ext = Path(filename).suffix.lower()
    m = re.match(r'^(\d+)\.(\d+)', stem)
    if m:
        return f"{int(m.group(1))}_{int(m.group(2))}{ext}"
    return filename.lower().replace(" ", "_").replace(".", "_") + ext


def analyze_figs(source_figs: Path, local_figs: Path) -> list[dict]:
    if not source_figs.exists():
        return [{"error": f"Source figs dir not found: {source_figs}"}]

    source_files = {p.name: p for p in source_figs.iterdir() if p.is_file() and p.name != "desktop.ini"}
    local_files: dict[str, Path] = {}
    if local_figs.exists():
        local_files = {p.name: p for p in local_figs.iterdir() if p.is_file()}

    results = []
    all_names = sorted(set(source_files) | set(local_files))

    for name in all_names:
        ext = Path(name).suffix.lower()
        is_new_format = ext not in KNOWN_EXTENSIONS and ext not in MANUAL_CONVERT_EXTENSIONS
        needs_manual_convert = ext in MANUAL_CONVERT_EXTENSIONS

        if name not in source_files:
            results.append({"name": name, "status": "REMOVED", "staged": False})
            continue

        src = source_files[name]
        slug = _canonical_slug(name)

        if name not in local_files:
            results.append({
                "name": name,
                "status": "NEW",
                "canonical_slug": slug,
                "ext": ext,
                "is_new_format": is_new_format,
                "needs_manual_convert": needs_manual_convert,
                "source_path": str(src),
                "staged": False,
            })
            continue

        loc = local_files[name]
        try:
            match = hash_file(src) == hash_file(loc)
        except OSError as e:
            results.append({"name": name, "status": "ERROR", "error": str(e), "staged": False})
            continue

        results.append({
            "name": name,
            "status": "UNCHANGED" if match else "CHANGED",
            "canonical_slug": slug,
            "ext": ext,
            "is_new_format": is_new_format,
            "needs_manual_convert": needs_manual_convert,
            "source_path": str(src),
            "staged": False,
        })

    return results


# ---------------------------------------------------------------------------
# Manual edit detection
# ---------------------------------------------------------------------------

def _run_git(args: list[str], cwd: str) -> str:
    """Run a git command and return stdout as UTF-8 string, ignoring decode errors."""
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def get_manual_edit_info(repo_root: Path) -> dict[str, int]:
    """Return {md_filename: changed_line_count} for any .md with uncommitted changes."""
    try:
        stdout = _run_git(
            ["git", "diff", "HEAD", "--name-only", "--", "*.md"],
            cwd=str(repo_root),
        )
        changed: dict[str, int] = {}
        for line in stdout.splitlines():
            md_path = repo_root / line.strip()
            if md_path.exists():
                try:
                    diff_out = _run_git(
                        ["git", "diff", "HEAD", "--", line.strip()],
                        cwd=str(repo_root),
                    )
                    # Count +/- lines (excluding diff headers)
                    count = sum(
                        1 for l in diff_out.splitlines()
                        if (l.startswith("+") or l.startswith("-"))
                        and not l.startswith("+++")
                        and not l.startswith("---")
                    )
                    changed[line.strip()] = count
                except subprocess.CalledProcessError:
                    changed[line.strip()] = -1
        return changed
    except subprocess.CalledProcessError:
        return {}


def _chapter_md_for_docx(docx_name: str) -> str | None:
    """Map 'ch3 energy.docx' -> 'ch3_energy.md'."""
    stem = Path(docx_name).stem.replace(" ", "_")
    return stem + ".md"


# ---------------------------------------------------------------------------
# Staging
# ---------------------------------------------------------------------------

def stage_files(staging_dir: Path, docx_diffs: list[dict], fig_diffs: list[dict],
                source_root: Path, source_figs: Path) -> None:
    docx_dir = staging_dir / "docx"
    figs_dir = staging_dir / "figs"
    docx_dir.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)

    for d in docx_diffs:
        if d["status"] in ("CHANGED", "NEW") and "source_path" in d:
            try:
                shutil.copy2(d["source_path"], docx_dir / d["name"])
                d["staged"] = True
            except OSError as e:
                d["stage_error"] = str(e)

    for f in fig_diffs:
        if f["status"] in ("CHANGED", "NEW") and "source_path" in f:
            try:
                shutil.copy2(f["source_path"], figs_dir / f["name"])
                f["staged"] = True
            except OSError as e:
                f["stage_error"] = str(e)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _fmt_size(n: int | None) -> str:
    if n is None:
        return "N/A"
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 / 1024:.1f} MB"


def generate_report(
    docx_diffs: list[dict],
    fig_diffs: list[dict],
    manual_edits: dict[str, int],
    staging_dir: Path,
    source_root: Path,
) -> str:
    lines = []
    sep = "=" * 80

    lines.append(sep)
    lines.append("EcoBook Author Update Diff Report")
    lines.append(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Source    : {source_root}")
    lines.append(f"Local raw : {SOURCE_RAW_INPUT}")
    lines.append(sep)

    # --- DOCX ---
    lines.append("")
    lines.append("DOCX FILES")
    lines.append("-" * 40)
    changed_chapters = []
    for d in docx_diffs:
        status = d["status"]
        name = d["name"]
        if status == "UNCHANGED":
            lines.append(f"  [UNCHANGED] {name}")
        elif status == "CHANGED":
            lines.append(f"  [CHANGED]   {name}  ({_fmt_size(d['local_size'])} → {_fmt_size(d['src_size'])})")
            md = _chapter_md_for_docx(name)
            if md and md in manual_edits:
                n = manual_edits[md]
                lines.append(f"              *** {md} has {n} uncommitted edit lines ***")
                lines.append(f"              *** Re-running pipeline WILL OVERWRITE those edits ***")
            changed_chapters.append(name)
            if "stage_error" in d:
                lines.append(f"              !!! STAGING FAILED: {d['stage_error']}")
            elif d.get("staged"):
                lines.append(f"              -> staged")
        elif status == "NEW":
            lines.append(f"  [NEW]       {name}  ({_fmt_size(d['src_size'])})")
            changed_chapters.append(name)
            if "stage_error" in d:
                lines.append(f"              !!! STAGING FAILED: {d['stage_error']}")
            elif d.get("staged"):
                lines.append(f"              -> staged")
        elif status == "REMOVED":
            lines.append(f"  [REMOVED]   {name}  (exists locally, not in source)")
        elif status == "ERROR":
            lines.append(f"  [ERROR]     {name}: {d.get('error')}")

    n_changed = sum(1 for d in docx_diffs if d["status"] in ("CHANGED", "NEW"))
    lines.append(f"\n  Summary: {n_changed} changed/new, "
                 f"{sum(1 for d in docx_diffs if d['status'] == 'UNCHANGED')} unchanged, "
                 f"{sum(1 for d in docx_diffs if d['status'] == 'REMOVED')} removed")

    # --- Figures ---
    lines.append("")
    lines.append("FIGURE FILES")
    lines.append("-" * 40)

    new_figs = [f for f in fig_diffs if f["status"] == "NEW"]
    changed_figs = [f for f in fig_diffs if f["status"] == "CHANGED"]
    removed_figs = [f for f in fig_diffs if f["status"] == "REMOVED"]
    manual_convert = [f for f in fig_diffs if f.get("needs_manual_convert")]
    unknown_format = [f for f in fig_diffs if f.get("is_new_format")]

    lines.append(f"  New figures    : {len(new_figs)}")
    lines.append(f"  Modified       : {len(changed_figs)}")
    lines.append(f"  Removed        : {len(removed_figs)}")

    if new_figs:
        lines.append("\n  New figures:")
        for f in new_figs:
            slug_info = f"  -> canonical slug: {f.get('canonical_slug', '?')}"
            staged = "  -> staged" if f.get("staged") else ""
            err = f"  !!! STAGING FAILED: {f['stage_error']}" if "stage_error" in f else ""
            lines.append(f"    {f['name']}")
            lines.append(f"      {slug_info.strip()}{('  ' + staged.strip()) if staged else ''}")
            if err:
                lines.append(f"      {err.strip()}")

    if changed_figs:
        lines.append("\n  Modified figures:")
        for f in changed_figs:
            staged = "  -> staged" if f.get("staged") else ""
            lines.append(f"    {f['name']}{staged}")

    if removed_figs:
        lines.append("\n  Removed figures (local only, not in source):")
        for f in removed_figs:
            lines.append(f"    {f['name']}")

    if manual_convert:
        lines.append("")
        lines.append("  !! MANUAL CONVERSION REQUIRED (PPTX/XLSX — pipeline cannot embed these directly):")
        for f in manual_convert:
            lines.append(f"    {f['name']}  -> export as PNG or JPG before running pipeline")

    if unknown_format:
        lines.append("")
        lines.append("  !! UNKNOWN FORMAT (not in known extension set):")
        for f in unknown_format:
            lines.append(f"    {f['name']}  ext={f['ext']}")

    # --- Manual edit risk ---
    lines.append("")
    lines.append("MANUAL EDIT RISK")
    lines.append("-" * 40)
    if manual_edits:
        lines.append("  Uncommitted changes detected in .md files:")
        for md_file, count in manual_edits.items():
            label = f"{count} edit lines" if count >= 0 else "(could not count)"
            lines.append(f"    {md_file}: {label}")
        lines.append("")
        high_risk = []
        for d in docx_diffs:
            if d["status"] in ("CHANGED", "NEW"):
                md = _chapter_md_for_docx(d["name"])
                if md and md in manual_edits:
                    high_risk.append((d["name"], md))
        if high_risk:
            lines.append("  !! HIGH RISK — DOCX changed AND .md has uncommitted edits:")
            for docx, md in high_risk:
                lines.append(f"    {docx}  <->  {md}")
            lines.append("")
            lines.append("  ACTION REQUIRED: commit your .md edits before running update_apply.py")
            lines.append("  Example:")
            for _, md in high_risk:
                lines.append(f"    git add {md}")
            lines.append("    git commit -m 'Manual fixes before author update'")
    else:
        lines.append("  No uncommitted .md changes — safe to proceed.")

    # --- Footer ---
    lines.append("")
    lines.append(sep)
    timestamp = staging_dir.name
    lines.append(f"Staging dir: {staging_dir}")
    lines.append("")
    if n_changed > 0:
        lines.append("NEXT STEP: Review this report, then run:")
        lines.append(f"  python pipeline/update_apply.py --staging {timestamp}")
        lines.append("")
        lines.append("Optional flags:")
        lines.append("  --dry-run          preview without changing anything")
        lines.append("  --figs-only        copy figures only, skip DOCX + pipeline")
        lines.append("  --skip-pipeline    copy files only, do not re-run pipeline")
        lines.append("  --chapters ch3,ch7 limit to specific chapters")
    else:
        lines.append("No changes detected — nothing to apply.")
    lines.append(sep)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze author source and stage changed files.")
    parser.add_argument("--source", default=str(SOURCE_AUTHOR),
                        help="Path to author's source folder (default: SOURCE_AUTHOR in settings.py)")
    args = parser.parse_args()

    source_root = Path(args.source)
    source_figs = source_root / FIGS_SUBDIR

    if not source_root.exists():
        print(f"ERROR: Source directory not found: {source_root}")
        print("Check that the H: drive is mounted and SOURCE_AUTHOR in settings.py is correct.")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_dir = STAGING_ROOT / timestamp
    staging_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing source: {source_root}")
    print(f"Local raw      : {SOURCE_RAW_INPUT}")
    print(f"Staging dir    : {staging_dir}")
    print()

    print("Comparing DOCX files (SHA-256)...")
    docx_diffs = analyze_docx(source_root, SOURCE_RAW_INPUT)

    print("Comparing figure files...")
    fig_diffs = analyze_figs(source_figs, ASSETS_DIR)

    print("Checking for uncommitted .md edits...")
    manual_edits = get_manual_edit_info(REPO_ROOT)

    print("Staging changed files...")
    stage_files(staging_dir, docx_diffs, fig_diffs, source_root, source_figs)

    # Save manifest
    manifest = {
        "timestamp": timestamp,
        "source_root": str(source_root),
        "docx_diffs": docx_diffs,
        "fig_diffs": [
            {k: v for k, v in f.items() if k != "source_path"}  # omit H: paths from manifest
            for f in fig_diffs
            if not f.get("error")
        ],
        "manual_edits": manual_edits,
    }
    manifest_path = staging_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate and save report
    report = generate_report(docx_diffs, fig_diffs, manual_edits, staging_dir, source_root)
    report_path = staging_dir / "report.txt"
    report_path.write_text(report, encoding="utf-8")

    print()
    print(report)
    print(f"\nReport saved: {report_path}")
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    main()
