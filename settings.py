
# media_location = r"H:\.shortcut-targets-by-id\1_uRJbl4RXVfpqZ9BRM9ZETR6U-6d0YTW\env book w tomer\figs ch. 1-14 - 120 figs 3 25"
# media_location = r"H:\My Drive\work\EcologyDotCom\test_doc_to_md\Ecology-Book\media"
MEDIA_SOURCE_DIR = r"H:\My Drive\work\EcologyDotCom\test_doc_to_md\Ecology-Book\extra\media"
MEDIA_REL_PATH   = "media"
# figure_label_pattern = r'(איור\s*\d+\.\d+:.*?(?:\n(?!\!\[\]).*?)*)'
figure_label_pattern = r'(איור\s*\d+\.\d+:.*?)(?=\nאיור\s*\d+\.\d+:|\n!\[\]|$)'
desc_block_pattern = r'^איור\s*\d+\.\d+:\s*'
figure_pattern = r"(איור\s*\d+\.\d+):"
img_bloc_and_height_pattern = r'\n!\[\]\(.*?\)\{[^}]*?height="([^"]+)"[^}]*\}'
image_file_pattern = '*.jpg'
