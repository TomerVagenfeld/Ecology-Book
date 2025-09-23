import sys
import textwrap
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from md_post_processing import mark_english_blocks


def test_mark_english_blocks_emits_valid_colon_fences():
    source = textwrap.dedent(
        """
        פתיח בעברית בלבד.

        An English paragraph that should be wrapped.

        > Energy is the only universal currency.
        > One of its many forms must be transformed to get anything done.

        - רשומה ברשימה
          > This is an English quote inside a list.
          > It should keep its indentation.

        Another paragraph עם קצת Hebrew שלא אמור להיות עטוף.
        """
    ).strip("\n")

    rendered = mark_english_blocks(source)

    assert ":::{div}" in rendered
    assert "::{{}}" not in rendered
    assert "::: {" not in rendered

    expected_paragraph = textwrap.dedent(
        """
        :::{div}
        :class: en_quote
        :dir: ltr

        An English paragraph that should be wrapped.
        :::
        """
    ).strip("\n")
    assert expected_paragraph in rendered

    expected_top_level = textwrap.dedent(
        """
        :::{div}
        :class: en_quote
        :dir: ltr

        > Energy is the only universal currency.
        > One of its many forms must be transformed to get anything done.
        :::
        """
    ).strip("\n")
    assert expected_top_level in rendered

    lines = rendered.splitlines()
    list_index = lines.index("- רשומה ברשימה")
    assert lines[list_index + 1].strip() == ""
    assert lines[list_index + 2] == "  :::{div}"
    assert lines[list_index + 3] == "  :class: en_quote"
    assert lines[list_index + 4] == "  :dir: ltr"
    assert lines[list_index + 5].strip() == ""
    assert lines[list_index + 6] == "  > This is an English quote inside a list."
    assert lines[list_index + 7] == "  > It should keep its indentation."
    assert lines[list_index + 8] == "  :::"

    assert "Another paragraph" in rendered
    assert "עם קצת Hebrew" in rendered
