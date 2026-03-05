# Pipeline Debugging Summary - 2025-11-15

## Issues Reported by User

1. **Missing page titles** - Some chapters weren't showing in TOC
2. **Sidebar on wrong side** - TOC appears on LEFT but should be on RIGHT for Hebrew
3. **Footnotes not rendering** - `[^39]` shows as literal text instead of clickable links
4. **Weird headers** - "height: 400px name: fig 2-3" appearing as H2 headers
5. **Images not showing** - Figures display as artifacts or don't show at all
6. **Section 2.9 in gray box** - Headers appearing with gray background
7. **Header numbering wrong** - Chapters starting with X.1 instead of X
8. **Inconsistent RTL** - Some pages have RTL, some don't

## Root Causes Identified

### 1. Missing Page Titles (FIXED ✅)
**Cause:** English quote div blocks (`:::{div} .en-quote`) were not being closed before H1 titles, causing Sphinx to not detect the title.

**Fix Applied:**
- Created `fix_en_quote_blocks.py` to properly close div blocks before H1
- Integrated into pipeline in `book-pipeline.py` line 87

**Files Modified:**
- `fix_en_quote_blocks.py` (new file)
- `book-pipeline.py`

### 2. Header Numbering (FIXED ✅)
**Cause:** When promoting `## 1.1 Title` to H1, the subsection number was kept, resulting in `# 1.1 Title` instead of `# 1. Title`

**Fix Applied:**
- Modified `normalize_markdown_heading_levels()` in `md_post_processing.py` lines 551-558
- Added regex to strip subsection numbers when promoting to H1

**Files Modified:**
- `md_post_processing.py` lines 551-558

### 3. Malformed Figure Blocks (PARTIALLY FIXED ⚠️)
**Cause:** Multiple issues in `insert_figures.py`:
1. Caption regex was too permissive - matched "איור 2.6)" in text, not just "איור 2.6:" captions
2. `_cleanup_malformed_figures()` was corrupting valid figure blocks
3. `_find_nearby_image()` searches backward AND forward, matching wrong images when figures are close together

**Fixes Applied:**
- Made colon REQUIRED in `_CAPTION_START_RE` regex (line 10)
- Added stop condition in `_collect_block()` when hitting another caption (lines 112-114)
- Disabled `_cleanup_malformed_figures()` call (line 288 commented out)

**Files Modified:**
- `insert_figures.py` lines 10, 112-114, 288

**STILL BROKEN:**
Figures are STILL malformed. Example from ch2_agriculture.md lines 185-215:
```markdown
```{figure} ../media/2_2.jpg    ← CORRECT
---
height: 400px
name: fig 2-2
---
Caption...
```

name: fig 2-3    ← MISSING ```{figure} line!
---
Caption...
```
```

**Why:** The `_find_nearby_image()` function (lines 193-205) searches up to 8 lines backward and forward. When figures are close together:
- Figure 2.2 finds image2.jpeg (correct)
- Figure 2.3 finds image2.jpeg BACKWARD (wrong! should find image3.jpeg forward)
- This causes incorrect patch ranges to be created

**Suggested Fix Options:**
1. Rewrite `insert_figures.py` from scratch with simpler logic
2. Check out earlier working commit and identify what changed
3. Fix `_find_nearby_image()` to only search FORWARD, not backward

### 4. Sidebar Position (NOT FIXED ❌)
**Issue:** TOC sidebar appears on LEFT but should be on RIGHT for Hebrew RTL pages

**Current CSS (_static/style.css lines ~30-40):**
```css
#pst-secondary-sidebar { order: 0; }  /* LEFT */
.bd-main { order: 1; }                /* MIDDLE */
#pst-primary-sidebar { order: 2; }    /* RIGHT */
```

**Which sidebar is which:**
- Primary sidebar = Main book TOC (chapter list)
- Secondary sidebar = Page TOC ("On this page" / section headers)

**Last working commit:** 466ab72 "fixed the primary and secondary sidebars positions"

**To Fix:** Need to swap order values so TOC appears on right

### 5. Footnotes Not Rendering (NOT FIXED ❌)
**Issue:** Footnote references like `[^39]` show as literal text

**Investigation:**
- Markdown syntax is correct
- Footnote definitions exist in files
- MyST should handle `[^39]` → clickable link automatically
- May be related to encoding or processing order

**Needs Investigation:**
- Check if footnotes work in chapter 1 but not chapter 2 (user reported inconsistency)
- Check MyST extensions in _config.yml
- May be corrupted during one of the post-processing steps

### 6. Section 2.9 Gray Box (NOT INVESTIGATED ❌)
Screenshot shows section 2.9 header appearing in a gray box. Likely related to blockquote styling or malformed markdown structure.

## Files Modified (Summary)

1. **book-pipeline.py**
   - Line 21: Added import for `fix_en_quote_blocks_file`
   - Line 72-88: Reordered pipeline steps
   - Line 120-123: Fixed Unicode error when printing TOC

2. **insert_figures.py**
   - Line 10-13: Made colon required in caption regex + added comment
   - Line 112-114: Added stop condition in `_collect_block()`
   - Line 288: Commented out `_cleanup_malformed_figures()` call

3. **md_post_processing.py**
   - Lines 551-558: Strip subsection numbers when promoting to H1

4. **fix_en_quote_blocks.py** (NEW FILE)
   - Full file created to fix English quote div blocks wrapping titles

## Pipeline Order (Current)

From `book-pipeline.py` lines 58-93:
1. Pandoc: DOCX → Markdown
2. `mark_english_blocks_file()` - Wrap English text in div blocks
3. `normalize_pandoc_attrs()` - Remove Pandoc attributes
4. `remove_unreferenced_footnotes_file()` - Clean unused footnotes
5. `convert_container_to_div_blocks_file()` - Convert old syntax
6. `process_markdown_insert_figures()` - **BROKEN - Creates malformed figures**
7. `sanitize_media_references_file()` - Fix media paths
8. `strip_anonymous_colon_fences_file()` - Remove empty containers
9. `fix_en_quote_blocks_file()` - **NEW - Fixes title wrapping**
10. `normalize_md_file_headings()` - Promote headings
11. `number_md_headings()` - Add chapter numbers

## Next Steps / Recommendations

### High Priority
1. **Fix figures** - Choose one:
   - Option A: Rewrite `insert_figures.py` with simpler logic
   - Option B: Checkout commit 466ab72 and compare
   - Option C: Fix `_find_nearby_image()` to only search forward

2. **Fix sidebar** - Swap CSS order values in `_static/style.css`

### Medium Priority
3. **Fix footnotes** - Investigate why `[^39]` isn't being processed
4. **Fix section 2.9 gray box** - Check markdown structure

## Test Commands

```bash
# Full pipeline from DOCX
python book-pipeline.py

# Just rebuild book (doesn't regenerate markdown)
jupyter-book build .

# Check specific chapter
sed -n '185,215p' book-source/md/ch2_agriculture.md

# Check HTML output
grep -A10 "fig 2-3" _build/html/book-source/md/ch2_agriculture.html
```

## Important Git Commits

- **466ab72** - "fixed the primary and secondary sidebars positions" (last working sidebar?)
- **a1a458b** - "Refine figure processing and captions" (may have broken figures)
- **c3c4dfe** - "changed blockquote color"
- **6f8cabd** - "better handling of file with spaces. added convert_container_to_div_blocks_file"

## Known Working Features

✅ All chapter titles now show in TOC
✅ Build completes without errors
✅ Header numbering correct (1, 2, 3 not 1.1, 2.1, 3.1)
✅ English quote blocks don't wrap titles
✅ Images are copied to media folder

## Known Broken Features

❌ Figures 2-3+ missing `{figure}` opening lines
❌ Sidebar TOC on wrong side (left vs right)
❌ Footnotes showing as literal text
❌ Some section headers in gray boxes

## Suggested Approach for Next Developer

1. Start with sidebar fix (quick CSS change)
2. Then tackle figure insertion (biggest issue)
3. Finally debug footnotes and section formatting

Good luck! 🍀
