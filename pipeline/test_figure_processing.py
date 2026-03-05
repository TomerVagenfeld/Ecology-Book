#!/usr/bin/env python3
"""Test script to verify figure processing fixes."""

from pathlib import Path
from insert_figures import process_markdown_insert_figures

def test_figure_processing():
    """Test the figure processing on existing markdown files."""

    # Test on ch2_agriculture.md (which had the broken figures)
    md_file = Path("book-source/md/ch2_agriculture.md")
    if not md_file.exists():
        print(f"File not found: {md_file}")
        return

    # Create test output
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)

    test_md = test_dir / "ch2_agriculture_test.md"
    test_media = test_dir / "media"
    test_media.mkdir(exist_ok=True)

    # Copy the source file
    test_md.write_text(md_file.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Testing figure processing on: {test_md}")

    # Process figures
    assets_dir = Path("book-source/raw/_figs ch. 1-14 - 120 figs & tables")
    if not assets_dir.exists():
        print(f"Assets directory not found: {assets_dir}")
        print("Available directories in book-source/raw:")
        raw_dir = Path("book-source/raw")
        if raw_dir.exists():
            for item in raw_dir.iterdir():
                print(f"  {item}")
        else:
            print("  book-source/raw does not exist")
        return

    process_markdown_insert_figures(
        test_md,
        assets_dir=assets_dir,
        media_dir=test_media,
        default_height_px=400,
    )

    # Read and analyze the result
    content = test_md.read_text(encoding="utf-8")
    lines = content.splitlines()

    print("\n--- FIGURE BLOCKS ANALYSIS ---")
    figure_count = 0
    in_figure = False

    for i, line in enumerate(lines, 1):
        if line.startswith("```{figure}"):
            figure_count += 1
            in_figure = True
            print(f"\nFigure {figure_count} at line {i}:")
            print(f"  {line}")
        elif in_figure:
            if line == "```":
                print(f"  {line}")
                in_figure = False
            else:
                print(f"  {line}")

    print(f"\nTotal figures found: {figure_count}")

    # Check for malformed blocks
    print("\n--- CHECKING FOR ISSUES ---")
    issues = 0

    for i, line in enumerate(lines, 1):
        # Look for loose figure metadata
        if line.startswith("name: fig") and not any(lines[j].startswith("```{figure}") for j in range(max(0, i-10), min(len(lines), i+1))):
            print(f"Issue at line {i}: Loose figure name outside block: {line}")
            issues += 1

        # Look for height directives outside blocks
        if line.startswith("height: ") and not any(lines[j].startswith("```{figure}") for j in range(max(0, i-5), min(len(lines), i+1))):
            print(f"Issue at line {i}: Loose height directive: {line}")
            issues += 1

    print(f"Issues found: {issues}")

    if issues == 0:
        print("✅ No structural issues found!")
    else:
        print("❌ Issues detected that need fixing")

if __name__ == "__main__":
    test_figure_processing()