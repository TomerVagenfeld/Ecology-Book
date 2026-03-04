import sys
import textwrap
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from md_post_processing import mark_english_blocks, strip_anonymous_colon_fences


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

    assert ":::{container}" in rendered
    assert "::{{}}" not in rendered
    assert "::: {" not in rendered

    expected_paragraph = textwrap.dedent(
        """
        :::{container}
        :class: en_quote
        An English paragraph that should be wrapped.
        :::
        """
    ).strip("\n")
    assert expected_paragraph in rendered

    expected_top_level = textwrap.dedent(
        """
        :::{container}
        :class: en_quote
        > Energy is the only universal currency.
        > One of its many forms must be transformed to get anything done.
        :::
        """
    ).strip("\n")
    assert expected_top_level in rendered

    lines = rendered.splitlines()
    list_index = lines.index("- רשומה ברשימה")
    assert lines[list_index + 1].strip() == ""
    assert lines[list_index + 2] == "  :::{container}"
    assert lines[list_index + 3] == "  :class: en_quote"
    assert lines[list_index + 4].strip() == ""
    assert lines[list_index + 5] == "  > This is an English quote inside a list."
    assert lines[list_index + 6] == "  > It should keep its indentation."
    assert lines[list_index + 7] == "  :::"

    assert "Another paragraph" in rendered
    assert "עם קצת Hebrew" in rendered


def test_strip_anonymous_colon_fences_removes_bare_blocks():
    source = textwrap.dedent(
        """
        :::

        ## 1.3 Heading inside anonymous container
        Some paragraph text.

        :::
        """
    ).strip("\n")

    cleaned = strip_anonymous_colon_fences(source)

    assert ":::" not in cleaned
    assert "## 1.3 Heading" in cleaned


def test_strip_anonymous_colon_fences_preserves_directives():
    source = textwrap.dedent(
        """
        :::{container}
        :class: en_quote

        > English quote stays wrapped.
        :::
        """
    ).strip("\n")

    cleaned = strip_anonymous_colon_fences(source)

    assert cleaned.strip("\n") == source


def test_strip_anonymous_colon_fences_drops_outer_wrapper_but_keeps_inner():
    source = textwrap.dedent(
        """
        :::
        :::{container}
        :class: en_quote

        > Nested quote survives.
        :::
        :::
        """
    ).strip("\n")

    cleaned = strip_anonymous_colon_fences(source)

    expected = textwrap.dedent(
        """
        :::{container}
        :class: en_quote

        > Nested quote survives.
        :::
        """
    ).strip("\n")

    assert cleaned.strip("\n") == expected
