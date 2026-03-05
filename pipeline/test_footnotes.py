#!/usr/bin/env python3
"""Test footnote processing to identify the issue."""

import re
from md_post_processing import FOOTNOTE_REF_CAPTURE_RE, FOOTNOTE_DEF_CAPTURE_RE, remove_unreferenced_footnotes

def test_footnote_patterns():
    """Test footnote regex patterns."""

    # Test footnote references
    test_refs = [
        "text with [^1] simple ref",
        "text with [^4] another ref",
        "text with [^42] number ref",
    ]

    print("=== Testing Footnote References ===")
    for text in test_refs:
        matches = FOOTNOTE_REF_CAPTURE_RE.findall(text)
        print(f"Text: {text}")
        print(f"Found refs: {matches}")
        print()

    # Test footnote definitions
    test_defs = [
        "[^1]: Simple definition",
        "[^4]: Definition with 3^rd^ superscript",
        "[^42]: Definition with 10^15^ scientific notation",
    ]

    print("=== Testing Footnote Definitions ===")
    for text in test_defs:
        match = FOOTNOTE_DEF_CAPTURE_RE.match(text)
        if match:
            print(f"Text: {text}")
            print(f"Found def: {match.group(1)}")
        else:
            print(f"NO MATCH: {text}")
        print()

def test_remove_unreferenced():
    """Test the remove_unreferenced_footnotes function."""

    test_markdown = """Some text with footnote[^4] reference.

[^4]: Definition with 3^rd^ superscript text.

Some more text with another footnote[^5] reference.

[^5]: Normal footnote definition.

Text with unreferenced footnote.

[^6]: This should be removed.
"""

    print("=== Testing remove_unreferenced_footnotes ===")
    print("Original:")
    print(test_markdown)
    print()

    result = remove_unreferenced_footnotes(test_markdown)
    print("After processing:")
    print(result)
    print()

if __name__ == "__main__":
    test_footnote_patterns()
    test_remove_unreferenced()