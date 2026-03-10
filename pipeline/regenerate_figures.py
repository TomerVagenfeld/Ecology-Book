#!/usr/bin/env python3
"""
Regenerate figure blocks for all chapter markdown files.
"""

from pathlib import Path
from insert_figures import process_markdown_insert_figures
from settings import ASSETS_DIR, MEDIA_DIR, MD_DIR

def main():
    md_files = list(MD_DIR.glob("ch*.md"))

    print(f"Regenerating figures for {len(md_files)} files...")

    for md_path in md_files:
        print(f"Processing: {md_path}")
        try:
            process_markdown_insert_figures(
                md_path,
                assets_dir=ASSETS_DIR,
                media_dir=MEDIA_DIR,
                default_height_px=400,
            )
            print(f"  [OK] {md_path.name}")
        except Exception as e:
            print(f"  [ERROR] {md_path.name}: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
