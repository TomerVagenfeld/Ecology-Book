#!/usr/bin/env python3
"""Test script to process a single chapter and verify figure processing."""

import os
import shutil
import subprocess
from pathlib import Path
from settings import PANDOC_ATTR, ASSETS_DIR
from docx_processing import convert_numbered_to_headings_keep_bullets
from md_post_processing import (
    mark_english_blocks_file,
    normalize_pandoc_attrs,
    remove_unreferenced_footnotes_file,
    strip_anonymous_colon_fences_file,
)
from insert_figures import process_markdown_insert_figures

def test_chapter_processing(chapter_name="ch2_agriculture"):
    """Test processing of a single chapter."""

    # Create test directories
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)

    docx_dir = test_dir / "docx"
    md_dir = test_dir / "md"
    media_dir = test_dir / "media"

    docx_dir.mkdir(exist_ok=True)
    md_dir.mkdir(exist_ok=True)
    media_dir.mkdir(exist_ok=True)

    # Find source DOCX file
    source_raw_dir = Path("book-source/raw")
    source_docx = None
    for file_path in source_raw_dir.glob("*.docx"):
        if "ch2" in file_path.name.lower() and "agriculture" in file_path.name.lower():
            source_docx = file_path
            break

    if not source_docx or not source_docx.exists():
        print(f"Source file not found in {source_raw_dir}")
        print(f"Available files: {list(source_raw_dir.glob('*.docx'))}")
        return

    # Process DOCX
    processed_docx = docx_dir / f"{chapter_name}_headers.docx"
    md_output = md_dir / f"{chapter_name}.md"

    print(f"Processing {source_docx} -> {md_output}")

    # Copy and convert DOCX
    shutil.copy(source_docx, processed_docx)
    convert_numbered_to_headings_keep_bullets(processed_docx, processed_docx)

    # DOCX -> MD with Pandoc
    args = ["pandoc", "-t", PANDOC_ATTR, "-o", str(md_output), str(processed_docx)]
    subprocess.run(args, check=True)

    # Post-process MD
    print("Post-processing markdown...")
    mark_english_blocks_file(md_output, scope="before_first_h1")
    normalize_pandoc_attrs(md_output)
    remove_unreferenced_footnotes_file(md_output)

    # Insert figures
    print("Processing figures...")
    process_markdown_insert_figures(
        md_output,
        assets_dir=ASSETS_DIR,
        media_dir=media_dir,
        default_height_px=400,
    )

    strip_anonymous_colon_fences_file(md_output)

    print(f"Processing complete. Check output in: {md_output}")

    # Read and print a sample of the output
    content = md_output.read_text(encoding="utf-8")
    lines = content.splitlines()

    print("\n--- SAMPLE OUTPUT (first 50 lines) ---")
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3d}: {line}")

    # Look for figure blocks
    print("\n--- FIGURE BLOCKS FOUND ---")
    in_figure = False
    for i, line in enumerate(lines, 1):
        if line.startswith("```{figure}"):
            in_figure = True
            print(f"{i:3d}: {line}")
        elif in_figure and line == "```":
            print(f"{i:3d}: {line}")
            in_figure = False
            print()
        elif in_figure:
            print(f"{i:3d}: {line}")

if __name__ == "__main__":
    test_chapter_processing()