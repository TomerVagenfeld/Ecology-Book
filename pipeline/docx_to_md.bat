
@echo off
set "input_dir=H:\.shortcut-targets-by-id\1_uRJbl4RXVfpqZ9BRM9ZETR6U-6d0YTW\env book w tomer"
set "input_docx=ch2 agriculture 3 25.docx"
set "output_docx=ch2_output.docx"
set "output_md=ch2.md"

set "ATTR=markdown-raw_html-raw_attribute-header_attributes-auto_identifiers-bracketed_spans-native_divs-native_spans"
set "BOOK_ROOT=H:\My Drive\work\EcologyDotCom\test_doc_to_md\Ecology-Book"

echo "convert paragraphs hierarchy to headers"
python test_convert_headers.py "%input_dir%\%input_docx%" "%output_docx%"
echo "convert docx to md"

    
echo "insert image to md"
python insert_img_to_md.py %output_md% "%BOOK_ROOT%\%output_md%"