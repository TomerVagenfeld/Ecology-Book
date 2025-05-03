import pathlib
import glob
import os
import regex as re
from settings import *
import posixpath
import pdb

def find_img_names_in_dir(dir_path: str) -> dict:
    for f in os.listdir(dir_path):
        new = f.replace(" ", "_")
        if new != f:
            os.rename(os.path.join(dir_path, f), os.path.join(dir_path, new))

    files = glob.glob(os.path.join(dir_path, image_file_pattern))
    filename_map = {}
    for full_path in files:
        # basename() gives e.g. "7.1 download.jpg"
        name = os.path.basename(full_path)
        m = re.match(r'^(\d+\.\d+[a-zA-Z]?)', name)
        if m:
            filename_map[m.group(1)] = full_path
    return filename_map

def make_figure_md_format(filename, media_location, height_unit, fig_name, desc):
    print("DEBUG EMIT FIGURE:", media_location, filename)

    return (
        f"\n```{{figure}} media/{filename}\n"
        f"---\n"
        f"height: {height_unit}\n"
        f"name: fig-{fig_name}\n"
        f"---\n"
        f"{desc}\n"
        f"```\n\n"
    )


def get_fig_text_matches_in_md(md_file: str):
    text = open(md_file, encoding='utf-8').read().replace('\r\n','\n')
    pattern = re.compile(
        r'\[?איור\s*(\d+\.\d+)\]?[^\n]*?:\s*'      # fig_num
        r'(.*?)\n+'                                # desc
        r'!\[\]\((.*?)\)\{[^}]*?height="([^"]+)"[^}]*\}',  # img_path, height
        re.DOTALL
    )

    matches = []
    for m in pattern.finditer(text):
        full = m.group(0)
        num  = m.group(1)
        desc = m.group(2).strip()
        img  = m.group(3)
        h    = m.group(4)
        matches.append((full, num, desc, img, h))
    return text, matches

def get_clean_fig_block(desc_block, height):

    fig_name_match = re.match(figure_pattern, desc_block.strip())
    fig_name = fig_name_match.group(1) if fig_name_match else "Unknown"

    # Remove the label prefix like "איור 7.2:"
    desc_block_clean = re.sub(r'^איור\s*\d+\.\d+:\s*', '', desc_block.strip(), flags=re.MULTILINE)

    print(f"Figure: {fig_name}")
    print(f"Height: {height}")
    print(f"Description:\n{desc_block_clean.strip()}\n{'-' * 50}") # TODO: why 50?

    return fig_name, desc_block_clean, height

def replace_fig_pattern(repl_text, file):

    with open(file, encoding='utf-8') as f:
        text = f.read()
        pattern = re.compile( r'\[?איור\s*(\d+\.\d+)\]?[^\n]*?:\s*(.*?)\n+!\[\]\((.*?)\)\{[^}]*?height="([^"]+)"[^}]*\}')
        new_text = pattern.sub(repl_text, text)

    return new_text


def replace_all_fig_blocks(
    md_path: str,
    filename_map: dict,
    media_location: str,
    make_figure_md_format
):
    text, matches = get_fig_text_matches_in_md(md_path)

    for full_block, fig_num, desc, img_path, height in matches:
        # 1) clean the description
        desc_clean = re.sub(r'^איור\s*\d+\.\d+:\s*', '', desc, flags=re.MULTILINE)
        # 2) pick the right filename
        filename = os.path.basename(filename_map.get(fig_num, img_path))

        # 3) build new block
        new_block = make_figure_md_format(
            filename=filename,
            media_location=media_location,
            height_unit=height,
            fig_name=fig_num,
            desc=desc_clean
        )

        # 4) replace **that exact** chunk of text
        text = text.replace(full_block, new_block)

    # scrub stray backslashes
    text = re.sub(r'(?m)^[ \t]*\\\s*$', '', text)

    return text



# TODO: make procedure to copy files to the media folder before build. if nothing changed, don't copy
def main(md_file, output):
    # **Use** MEDIA_SOURCE_DIR to find the files on disk…
    filename_map = find_img_names_in_dir(dir_path=MEDIA_SOURCE_DIR)
    # …but pass MEDIA_REL_PATH into the replacer so it emits “media/…”
    new_text = replace_all_fig_blocks(
        md_path=md_file,
        filename_map=filename_map,
        media_location=MEDIA_REL_PATH,       # <-- this must be "media"
        make_figure_md_format=make_figure_md_format
    )
    with open(output, 'w', encoding='utf-8') as f:
        f.write(new_text)


if __name__ == "__main__":
    input = r"H:\My Drive\work\EcologyDotCom\test_doc_to_md\word_header_python\output.md"
    output_after = r"H:\My Drive\work\EcologyDotCom\test_doc_to_md\Ecology-Book\output_after.md"
    main(input, output_after)
