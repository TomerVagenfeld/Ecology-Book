# book-pipeline.py (refactored)
# Orchestrates DOCX -> Pandoc -> MD post-processing -> Jupyter-Book

import os, shutil, subprocess, re
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
)
from build_book import (
    _first_h1_title,
    _chapter_sort_key,
    create_toc,
    build_book
)
from insert_figures import process_markdown_insert_figures



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
        # If you ever want the old behavior, call: mark_english_blocks_file(md_output, scope="before_first_h1", mode="paragraphs_and_blockquotes")
        mark_english_blocks_file(md_output, scope="before_first_h1")
        normalize_pandoc_attrs(Path(md_output))
        remove_unreferenced_footnotes_file(md_output)

        # Insert figures from the external assets directory into MyST figure blocks
        process_markdown_insert_figures(
            md_output,
            assets_dir=ASSETS_DIR,
            media_dir=MEDIA_DIR,
            default_height_px=400,
        )

        if "ch15" in docx_file:
            promote_top_title_line_to_h1(md_output)

        normalize_md_file_headings(md_output)
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
            print((BOOK_ROOT / "_toc.yml").read_text(encoding="utf-8"))
        build_book(BOOK_ROOT, clean=clean)
