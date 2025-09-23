
# media_location = r"H:\.shortcut-targets-by-id\1_uRJbl4RXVfpqZ9BRM9ZETR6U-6d0YTW\env book w tomer\figs ch. 1-14 - 120 figs 3 25"
# media_location = r"H:\My Drive\work\EcologyDotCom\test_doc_to_md\Ecology-Book\media"
from pathlib import Path
MEDIA_REL_PATH   = "media"
# figure_label_pattern = r'(איור\s*\d+\.\d+:.*?(?:\n(?!\!\[\]).*?)*)'
figure_label_pattern = r'(איור\s*\d+\.\d+:.*?)(?=\nאיור\s*\d+\.\d+:|\n!\[\]|$)'
desc_block_pattern = r'^איור\s*\d+\.\d+:\s*'
figure_pattern = r"(איור\s*\d+\.\d+):"
img_bloc_and_height_pattern = r'\n!\[\]\(.*?\)\{[^}]*?height="([^"]+)"[^}]*\}'
image_file_pattern = '*.jpg'
PANDOC_ATTR = "markdown-raw_html-raw_attribute-header_attributes-auto_identifiers-bracketed_spans-native_divs-native_spans"
BOOK_ROOT = Path(__file__).parent.resolve()
SOURCE_RAW_INPUT = r"H:\.shortcut-targets-by-id\1_uRJbl4RXVfpqZ9BRM9ZETR6U-6d0YTW\env book w tomer"
SOURCE_DIR = BOOK_ROOT / "book-source"
MD_DIR = BOOK_ROOT / "book-source" / "md"
MEDIA_DIR = BOOK_ROOT / "book-source" / "media"
ASSETS_DIR = Path(SOURCE_RAW_INPUT) / "_figs ch. 1-14 - 120 figs & tables"