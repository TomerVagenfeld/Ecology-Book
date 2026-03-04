from pathlib import Path
import re
import os
import subprocess
# --- helpers for TOC & book build ---
def _first_h1_title(md_path: Path) -> str | None:
    with md_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.lstrip().startswith("# "):
                title = line.lstrip()[2:].strip()
                # Strip footnote references like [^41] from titles
                title = re.sub(r'\[\^[^\]]+\]', '', title).strip()
                # Normalize whitespace
                title = re.sub(r'\s+', ' ', title)
                return title
    return None

_num_prefix_re = re.compile(r"^ch(\d+)_", re.IGNORECASE)

def _chapter_sort_key(p: Path):
    m = _num_prefix_re.match(p.stem)
    return (0, int(m.group(1))) if m else (1, p.stem.lower())

def create_toc(book_root: str | Path,
               md_dir: str | Path,
               root_md: str = "index.md",
               overwrite: bool = True) -> Path:
    book_root = Path(book_root)
    md_dir = Path(md_dir)
    toc_path = book_root / "_toc.yml"
    if toc_path.exists() and not overwrite:
        return toc_path

    index_path = book_root / "index.md"
    if not index_path.exists():
        raise FileNotFoundError("index.md is missing")

    md_files = sorted([p for p in md_dir.glob("*.md")], key=_chapter_sort_key)

    def toc_entry(p: Path) -> str:
        title = (_first_h1_title(p) or p.stem.replace("_", " ").title()).replace('"', r'\"')
        rel = p.resolve().relative_to(book_root)
        file_key = rel.with_suffix('').as_posix()
        return f'  - file: {file_key}\n    title: "{title}"'

    lines = [
        "format: jb-book",
        "root: index",
        "options:",
        "  numbered: false",
        "chapters:",
    ]
    lines += [toc_entry(p) for p in md_files] if md_files else ["  []"]
    toc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return toc_path

def build_book(book_root: str | Path, clean: bool = False):
    book_root = Path(book_root).resolve()
    os.makedirs(book_root, exist_ok=True)
    cmd = ["jupyter-book", "build", str(book_root)]
    if clean:
        cmd.insert(3, "--all")
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)
