"""
update_apply.py - Phase 2 of the author update workflow.

Reads a staging manifest produced by update_ingest.py, promotes changed files
to pipeline/book-source/raw/, and re-runs the pipeline selectively for only
the affected chapters.

Usage:
    python pipeline/update_apply.py --staging 20260319_143201
    python pipeline/update_apply.py --staging 20260319_143201 --dry-run
    python pipeline/update_apply.py --staging 20260319_143201 --figs-only
    python pipeline/update_apply.py --staging 20260319_143201 --skip-pipeline
    python pipeline/update_apply.py --staging 20260319_143201 --chapters ch3,ch7
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from settings import (
    ASSETS_DIR,
    BOOK_ROOT,
    MD_DIR,
    MEDIA_DIR,
    PANDOC_ATTR,
    REPO_ROOT,
    SOURCE_DIR,
    SOURCE_RAW_INPUT,
)

STAGING_ROOT = BOOK_ROOT / "staging"
FIGS_SUBDIR = "_figs ch. 1-14 - 120 figs & tables"


# ---------------------------------------------------------------------------
# Git safety check
# ---------------------------------------------------------------------------

def check_uncommitted_md(repo_root: Path, chapter_stems: list[str]) -> list[str]:
    """Return list of uncommitted .md files that overlap with chapters being updated."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--name-only", "--", "*.md"],
            cwd=str(repo_root),
            capture_output=True,
            check=True,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        dirty = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not chapter_stems:
            return dirty
        # Filter to only those chapters we're about to overwrite
        affected = []
        for md_file in dirty:
            for stem in chapter_stems:
                if stem in md_file:
                    affected.append(md_file)
                    break
        return affected
    except subprocess.CalledProcessError:
        return []


# ---------------------------------------------------------------------------
# Chapter name helpers
# ---------------------------------------------------------------------------

def _docx_stem_to_md(docx_name: str) -> str:
    """'ch3 energy.docx' -> 'ch3_energy'"""
    return Path(docx_name).stem.replace(" ", "_")


def _chapter_number(docx_name: str) -> str | None:
    """'ch3 energy.docx' -> 'ch3'"""
    m = re.match(r'(ch\d+)', Path(docx_name).stem, re.IGNORECASE)
    return m.group(1).lower() if m else None


# ---------------------------------------------------------------------------
# Pipeline steps (mirrors generate_md_files() in book-pipeline.py)
# ---------------------------------------------------------------------------

def run_pipeline_for_chapter(docx_name: str, dry_run: bool = False) -> None:
    """Re-run the full DOCX -> MD pipeline for one chapter."""
    from docx_processing import convert_numbered_to_headings_keep_bullets
    from fix_en_quote_blocks import fix_en_quote_blocks_file
    from insert_figures import process_markdown_insert_figures
    from md_post_processing import (
        convert_container_to_div_blocks_file,
        mark_english_blocks_file,
        normalize_md_file_headings,
        normalize_pandoc_attrs,
        number_md_headings,
        promote_top_title_line_to_h1,
        remove_unreferenced_footnotes_file,
        sanitize_media_references_file,
        strip_anonymous_colon_fences_file,
    )

    raw_path = SOURCE_RAW_INPUT / docx_name
    stem = Path(docx_name).stem.replace(" ", "_")
    new_docx_name = SOURCE_DIR / "docx" / (stem + "_headers" + Path(docx_name).suffix)
    md_output = REPO_ROOT / (stem + ".md")

    print(f"  Processing {docx_name} -> {md_output.name}")
    if dry_run:
        print(f"    [DRY RUN] would run pipeline for {docx_name}")
        return

    os.makedirs(SOURCE_DIR / "docx", exist_ok=True)

    shutil.copy(raw_path, new_docx_name)
    convert_numbered_to_headings_keep_bullets(str(new_docx_name), str(new_docx_name))

    args = ["pandoc", "-t", PANDOC_ATTR, "-o", str(md_output), str(new_docx_name)]
    subprocess.run(args, check=True)

    normalize_pandoc_attrs(md_output)
    remove_unreferenced_footnotes_file(str(md_output))
    convert_container_to_div_blocks_file(str(md_output))

    process_markdown_insert_figures(
        str(md_output),
        assets_dir=ASSETS_DIR,
        media_dir=MEDIA_DIR,
        default_height_px=400,
        raw_dir=SOURCE_RAW_INPUT,
    )

    sanitize_media_references_file(str(md_output))
    strip_anonymous_colon_fences_file(str(md_output))

    if "ch15" in docx_name:
        promote_top_title_line_to_h1(str(md_output))

    normalize_md_file_headings(str(md_output))
    mark_english_blocks_file(str(md_output), scope="before_first_h1")
    fix_en_quote_blocks_file(md_output)
    number_md_headings(str(md_output))


# ---------------------------------------------------------------------------
# Main apply logic
# ---------------------------------------------------------------------------

def apply(args: argparse.Namespace) -> None:
    staging_dir = STAGING_ROOT / args.staging
    if not staging_dir.exists():
        print(f"ERROR: Staging directory not found: {staging_dir}")
        print(f"Run update_ingest.py first to create a staging run.")
        sys.exit(1)

    manifest_path = staging_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found in {staging_dir}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dry_run = args.dry_run

    # Determine which DOCX chapters to process
    changed_docx = [d for d in manifest["docx_diffs"] if d["status"] in ("CHANGED", "NEW") and d.get("staged")]

    if args.chapters:
        filters = [c.strip().lower() for c in args.chapters.split(",")]
        changed_docx = [d for d in changed_docx if any(f in d["name"].lower() for f in filters)]

    if args.figs_only:
        changed_docx = []

    chapter_stems = [_docx_stem_to_md(d["name"]) for d in changed_docx]

    # --- Git safety check ---
    if not args.figs_only and not args.skip_pipeline and changed_docx:
        dirty = check_uncommitted_md(REPO_ROOT, chapter_stems)
        if dirty:
            print("=" * 70)
            print("ABORT: Uncommitted .md edits detected for chapters being updated.")
            print("These edits WILL BE LOST if the pipeline re-runs.")
            print()
            print("Affected files:")
            for f in dirty:
                print(f"  {f}")
            print()
            print("ACTION: Commit your edits first, then re-run update_apply.py:")
            print()
            for f in dirty:
                print(f"  git add {f}")
            print(f"  git commit -m 'Manual fixes before author update ({args.staging})'")
            print("=" * 70)
            sys.exit(1)

    # --- Preview what will happen ---
    print("=" * 70)
    print(f"Staging run : {args.staging}")
    print(f"Dry run     : {dry_run}")
    print()

    changed_figs = [f for f in manifest["fig_diffs"] if f["status"] in ("CHANGED", "NEW") and f.get("staged")]
    if args.chapters:
        filters = [c.strip().lower() for c in args.chapters.split(",")]
        changed_figs = [f for f in changed_figs
                        if any(f["name"].lower().startswith(filt.replace("ch", "")) for filt in filters)]

    print(f"DOCX to apply   : {len(changed_docx)} files")
    for d in changed_docx:
        print(f"  {d['name']}  [{d['status']}]")
    print()
    print(f"Figures to apply: {len(changed_figs)} files")
    for f in changed_figs[:10]:
        print(f"  {f['name']}  [{f['status']}]")
    if len(changed_figs) > 10:
        print(f"  ... and {len(changed_figs) - 10} more")
    print()

    if not changed_docx and not changed_figs:
        print("Nothing to apply.")
        return

    if dry_run:
        print("[DRY RUN] No files will be changed.")
        return

    # --- Backup directory ---
    backup_dir = staging_dir / "backup"
    backup_dir.mkdir(exist_ok=True)

    # --- Apply DOCX files ---
    if changed_docx:
        print("Copying DOCX files to pipeline/book-source/raw/ ...")
        SOURCE_RAW_INPUT.mkdir(parents=True, exist_ok=True)
        for d in changed_docx:
            src = staging_dir / "docx" / d["name"]
            dest = SOURCE_RAW_INPUT / d["name"]
            # Backup existing
            if dest.exists():
                shutil.copy2(dest, backup_dir / d["name"])
                print(f"  Backed up: {d['name']}")
            shutil.copy2(src, dest)
            print(f"  Copied: {d['name']}")

    # --- Apply figure files ---
    if changed_figs:
        print("Copying figure files to assets dir ...")
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        for f in changed_figs:
            src = staging_dir / "figs" / f["name"]
            dest = ASSETS_DIR / f["name"]
            if dest.exists():
                shutil.copy2(dest, backup_dir / ("figs_" + f["name"]))
            shutil.copy2(src, dest)
            print(f"  Copied: {f['name']}")

    # --- Re-run pipeline for changed chapters ---
    if not args.skip_pipeline and not args.figs_only and changed_docx:
        print()
        print("Re-running pipeline for changed chapters...")
        for d in changed_docx:
            if "front" in d["name"].lower():
                print(f"  Skipping _front.docx (not a chapter)")
                continue
            run_pipeline_for_chapter(d["name"], dry_run=dry_run)

    # --- Validate ---
    if not args.skip_pipeline:
        print()
        print("Running validation...")
        from validate import validate_all
        validate_all(MD_DIR, REPO_ROOT / "validation.log")
        print(f"Validation log: {REPO_ROOT / 'validation.log'}")

    print()
    print("Done. Review the output .md files, then build with:")
    print("  python pipeline/book-pipeline.py  (or run jupyter-book build .)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply staged author updates to the pipeline.")
    parser.add_argument("--staging", required=True,
                        help="Timestamp of the staging run to apply (e.g. 20260319_143201)")
    parser.add_argument("--chapters",
                        help="Comma-separated chapter filters (e.g. ch3,ch7). Default: all changed chapters.")
    parser.add_argument("--figs-only", action="store_true",
                        help="Copy figures only, skip DOCX and pipeline re-run.")
    parser.add_argument("--skip-pipeline", action="store_true",
                        help="Copy files only, do not re-run the pipeline.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without changing anything.")
    args = parser.parse_args()
    apply(args)


if __name__ == "__main__":
    main()
