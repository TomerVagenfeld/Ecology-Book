from pathlib import Path

MEDIA_REL_PATH = "media"
figure_label_pattern = r'(איור\s*\d+\.\d+:.*?)(?=\nאיור\s*\d+\.\d+:|\n!\[\]|$)'
desc_block_pattern = r'^איור\s*\d+\.\d+:\s*'
figure_pattern = r"(איור\s*\d+\.\d+):"
img_bloc_and_height_pattern = r'\n!\[\]\(.*?\)\{[^}]*?height="([^"]+)"[^}]*\}'
image_file_pattern = '*.jpg'
PANDOC_ATTR = "markdown-raw_html-raw_attribute-header_attributes-auto_identifiers-bracketed_spans-native_divs-native_spans"

BOOK_ROOT = Path(__file__).parent.resolve()
SOURCE_DIR = BOOK_ROOT / "book-source"
SOURCE_RAW_INPUT = SOURCE_DIR / "raw"
MD_DIR = SOURCE_DIR / "md"
MEDIA_DIR = SOURCE_DIR / MEDIA_REL_PATH
ASSETS_DIR = SOURCE_RAW_INPUT / "_figs ch. 1-14 - 120 figs & tables"
