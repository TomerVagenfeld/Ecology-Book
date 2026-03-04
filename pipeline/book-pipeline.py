# book-pipeline.py (refactored)
# Orchestrates DOCX -> Pandoc -> MD post-processing -> Jupyter-Book

import os, shutil, subprocess
from glob import glob
from pathlib import Path
from tqdm import tqdm
from settings import PANDOC_ATTR, BOOK_ROOT, SOURCE_RAW_INPUT, SOURCE_DIR, MD_DIR, MEDIA_DIR, ASSETS_DIR
from docx_processing import convert_numbered_to_headings_keep_bullets
from md_post_processing import (
    mark_english_blocks_file,
    normalize_pandoc_attrs,
    promote_top_title_line_to_h1,
    normalize_md_file_headings,
    number_md_headings,
    remove_unreferenced_footnotes_file,
    strip_anonymous_colon_fences_file,
    convert_container_to_div_blocks_file,
    sanitize_media_references_file,
)
from fix_en_quote_blocks import fix_en_quote_blocks_file
from build_book import (
    # _first_h1_title,
    # _chapter_sort_key,
    create_toc,
    build_book
)
from insert_figures import process_markdown_insert_figures
from validate import validate_all



def generate_md_files(input_dir, output_dir, copy_raw=False):
    # folders
    os.makedirs(os.path.join(output_dir, "raw"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "docx"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "md"), exist_ok=True)

    if copy_raw:
        shutil.copytree(
            input_dir, os.path.join(output_dir, "raw"),
            ignore=shutil.ignore_patterns("_figs ch. 1-14 - 120 figs & tables/*"),
            dirs_exist_ok=True
        )

    docx_files = glob(os.path.join(output_dir, "raw", '*.docx'))

    print("converting titles to header in docx files")
    for docx_file in tqdm(docx_files):
        if "front" in docx_file:
            continue
        new_docx_name = Path(docx_file).stem.replace(" ", "_") + "_headers" + Path(docx_file).suffix
        md_output = os.path.join(output_dir, "md", Path(docx_file).stem.replace(" ", "_") + ".md")
        new_docx_name = os.path.join(output_dir, "docx", new_docx_name)

        shutil.copy(docx_file, new_docx_name)
        convert_numbered_to_headings_keep_bullets(new_docx_name, new_docx_name)

        # DOCX -> MD with Pandoc
        args = ["pandoc", "-t", PANDOC_ATTR, "-o", md_output, new_docx_name]
        subprocess.run(args, check=True)

        # Post-process MD
        normalize_pandoc_attrs(Path(md_output))
        remove_unreferenced_footnotes_file(md_output)

        # Convert existing :::{container} blocks to :::{div} blocks to fix MyST syntax
        convert_container_to_div_blocks_file(md_output)

        # Insert figures: extract images from DOCX, fall back to figs directory
        process_markdown_insert_figures(
            md_output,
            assets_dir=ASSETS_DIR,
            media_dir=MEDIA_DIR,
            default_height_px=400,
            raw_dir=SOURCE_RAW_INPUT,
        )

        # Sanitize media references to fix filenames with excessive spaces from external sources
        sanitize_media_references_file(md_output)

        # Strip anonymous colon fences AFTER figure processing
        strip_anonymous_colon_fences_file(md_output)

        # IMPORTANT: Normalize headings BEFORE marking English blocks
        # This ensures H1 headers exist when English block detection runs
        if "ch15" in docx_file:
            promote_top_title_line_to_h1(md_output)

        normalize_md_file_headings(md_output)

        # Now mark English blocks - this can properly detect H1 headers
        mark_english_blocks_file(md_output, scope="before_first_h1")

        # Fix English quote div blocks to ensure they don't wrap H1 titles
        fix_en_quote_blocks_file(Path(md_output))

        # Finally, add chapter numbering
        number_md_headings(md_output)


if __name__ == "__main__":
    # flags
    generate_md = True
    copy_raw = False
    toc = True
    build = True
    clean = True

    if generate_md:
        generate_md_files(SOURCE_RAW_INPUT, SOURCE_DIR, copy_raw=copy_raw)

    # Run validation before building
    print("\n--- Validation ---")
    validate_all(MD_DIR, BOOK_ROOT / "validation.log")

    if toc:
        create_toc(BOOK_ROOT, MD_DIR)
        for p in MD_DIR.glob("*.md"):
            key = (p.resolve().relative_to(BOOK_ROOT).as_posix())[:-3]
            path = BOOK_ROOT / (key + ".md")
            assert path.exists(), f"Missing: {path}"
    if build:
        print("[MD count]", len(list(MD_DIR.glob("*.md"))))
        print("[Index exists]", (BOOK_ROOT / "index.md").exists())
        print("[TOC exists]", (BOOK_ROOT / "_toc.yml").exists())
        print("---- _toc.yml ----")

        if (BOOK_ROOT / "_toc.yml").exists():
            try:
                print((BOOK_ROOT / "_toc.yml").read_text(encoding="utf-8"))
            except UnicodeEncodeError:
                print("[TOC contains unicode characters that cannot be displayed in console]")

        build_book(BOOK_ROOT, clean=clean)
