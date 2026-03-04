from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from insert_figures import process_markdown_insert_figures


def _write_asset(assets_dir: Path, name: str) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / name).write_bytes(b"fake-image-bytes")


def test_inline_source_paragraph_is_folded_into_caption(tmp_path):
    assets = tmp_path / "assets"
    media = tmp_path / "media"
    md_path = tmp_path / "chapter.md"

    _write_asset(assets, "1.2 diagram.png")

    md_path.write_text(
        textwrap.dedent(
            """
            איור 1.2: תחזית דמוגרפית. מקור –
            <https://example.com>; CC BY 4.0; Reprinted with permission.
            ![](media/image42.png)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    process_markdown_insert_figures(md_path, assets, media, default_height_px=300)

    result = md_path.read_text(encoding="utf-8")
    assert "```{figure}" in result
    assert "מקור – <https://example.com>;" in result
    # ensure the original pandoc artefact is removed
    assert "![](media/image42.png)" not in result


def test_detached_source_block_is_attached(tmp_path):
    assets = tmp_path / "assets"
    media = tmp_path / "media"
    md_path = tmp_path / "chapter2.md"

    _write_asset(assets, "3.4.png")

    md_path.write_text(
        textwrap.dedent(
            """
            איור 3.4: תיאור התהליך התעשייתי.

            מקור – משרד האנרגיה.
            CC BY-SA 4.0.
            ![](media/image99.jpeg)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    process_markdown_insert_figures(md_path, assets, media)

    output = md_path.read_text(encoding="utf-8")

    assert "מקור – משרד האנרגיה." in output
    assert "CC BY-SA 4.0." in output
    # The detached source paragraph should be removed
    assert "\nמקור –" not in output
    # No stray pandoc artefacts remain
    assert "![](media/image99.jpeg)" not in output
