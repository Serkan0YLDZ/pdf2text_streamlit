import os
import io
import json
import streamlit as st
import warnings
import logging
import shutil
"""Reduce noisy logs/warnings from PDF tooling"""
logging.getLogger("camelot").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning, module="camelot")
warnings.filterwarnings("ignore", message=r".*does not lie in column range.*")

def _is_ghostscript_available() -> bool:
    """Return True if Ghostscript executable is available on PATH."""
    candidates = [
        "gs",
        "gswin64c",
        "gswin32c",
    ]
    return any(shutil.which(name) is not None for name in candidates)

from streamlit_pdf_viewer import pdf_viewer
from streamlit_option_menu import option_menu
import pymupdf4llm
import pdfplumber
import fitz
import pandas as pd
import camelot

def convert_bytes_to_string(obj):
    """Recursively convert bytes objects to strings for JSON serialization."""
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif isinstance(obj, dict):
        return {key: convert_bytes_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_string(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_bytes_to_string(item) for item in obj)
    else:
        return obj

def clean_table_columns(table_data):
    """Clean and create unique column names for table data."""
    if table_data[0]:
        columns = []
        for j, col in enumerate(table_data[0]):
            if col is None or col == "":
                columns.append(f"Column_{j+1}")
            else:
                columns.append(str(col))

        seen = {}
        unique_columns = []
        for col in columns:
            if col in seen:
                seen[col] += 1
                unique_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                unique_columns.append(col)

        return pd.DataFrame(table_data[1:], columns=unique_columns)
    else:
        num_cols = len(table_data[1]) if len(table_data) > 1 else 1
        columns = [f"Column_{j+1}" for j in range(num_cols)]
        return pd.DataFrame(table_data[1:], columns=columns)

def export_tables_to_csv(dataframes):
    """Export multiple dataframes to CSV format."""
    csv_data = io.StringIO()
    for idx, df in enumerate(dataframes):
        df.to_csv(csv_data, index=False)
        if idx < len(dataframes) - 1:
            csv_data.write("\n")
    return csv_data.getvalue()


def show():
    st.title("Direct Text Extraction")
    col1, col2 = st.columns([1, 1])

    if "file_path" in st.session_state and os.path.exists(st.session_state.file_path):
        file_path = st.session_state.file_path

        with col1:
            pdf_viewer(
                file_path,
                height=1640,
                zoom_level=1,
                viewer_align="center",
                show_page_separator=True,
            )
        with col2:
            fname = os.path.basename(file_path)


            st.markdown(
                """
                <style>
                /* Make option menus (from streamlit-option-menu) wrap nicely */
                ul.nav.nav-pills { flex-wrap: wrap; gap: 6px; }
                ul.nav.nav-pills > li { margin: 0; padding: 0; }
                /* First 4 items take 25% width (4 per row) */
                ul.nav.nav-pills > li:nth-child(-n+4) { flex: 0 0 calc(25% - 6px); }
                /* Remaining items take 20% width (5 per row) */
                ul.nav.nav-pills > li:nth-child(n+5) { flex: 0 0 calc(20% - 6px); }
                /* Center content and keep it tidy */
                ul.nav.nav-pills > li > a { display: flex; align-items: center; justify-content: center; width: 100%; }
                </style>
                """,
                unsafe_allow_html=True,
            )

            tab_pymupdf, tab_plumber, tab_camelot = st.tabs([
                "PyMuPDF (fitz)",
                "PDFplumber",
                "Camelot",
            ])

            with tab_pymupdf:
                st.subheader("PyMuPDF (fitz) Text, Layout, Tables, Images")

                st.markdown("**Select extraction mode:**")
                pymupdf_option = option_menu(
                    None,
                    [
                        "All Text",
                        "Specific Page",
                        "Markdown/JSON Output",
                        "Search Text",
                        "Table Detection",
                        "Image Extraction",
                    ],
                    icons=[
                        "file-text",
                        "file-earmark",
                        "markdown",
                        "search",
                        "table",
                        "image",
                    ],
                    orientation="horizontal",
                    key="pymupdf_mode",
                )

                doc = fitz.open(file_path)

                if pymupdf_option == "All Text":
                    all_text = ""
                    for page_num in range(doc.page_count):
                        page = doc[page_num]
                        all_text += (
                            f"\n--- Page {page_num + 1} ---\n{page.get_text()}\n"
                        )
                    st.text_area("Full Document Text:", all_text, height=400)
                    st.download_button("Export .txt", all_text, file_name=f"{os.path.splitext(fname)[0]}_all_text.txt")

                elif pymupdf_option == "Specific Page":
                    page_number = st.number_input(
                        "Enter page number:",
                        min_value=1,
                        max_value=doc.page_count,
                        step=1,
                        value=1,
                    )
                    page = doc[page_number - 1]
                    page_text = page.get_text()
                    st.text_area(f"Page {page_number} Text:", page_text, height=400)
                    st.download_button(
                        "Export page .txt",
                        page_text or "",
                        file_name=f"{os.path.splitext(fname)[0]}_page_{page_number}.txt",
                        key="export_specific_page_txt",
                    )

                elif pymupdf_option == "Markdown/JSON Output":
                    output_format = st.selectbox("Output Format:", ["Markdown", "JSON"])
                    if output_format == "Markdown":
                        combined_md = []
                        for page_num in range(doc.page_count):
                            md_text = pymupdf4llm.to_markdown(
                                file_path, pages=[page_num]
                            )
                            st.markdown("---")
                            st.markdown(f"### Page {page_num + 1}\n{md_text}")
                            combined_md.append(f"\n\n## Page {page_num + 1}\n\n" + md_text)
                        st.download_button(
                            "Export .md",
                            "\n".join(combined_md),
                            file_name=f"{os.path.splitext(fname)[0]}_fitz.md",
                            key="export_md_all",
                        )
                    elif output_format == "JSON":
                        export_obj = {}
                        for page_num in range(doc.page_count):
                            page = doc[page_num]
                            json_text = page.get_text("dict")
                            json_text_clean = convert_bytes_to_string(json_text)
                            st.json({f"Page {page_num + 1}": json_text_clean})
                            export_obj[f"page_{page_num + 1}"] = json_text_clean
                        st.download_button(
                            "Export .json",
                            json.dumps(export_obj, ensure_ascii=False, indent=2),
                            file_name=f"{os.path.splitext(fname)[0]}_fitz.json",
                            key="export_json_all",
                        )

                elif pymupdf_option == "Search Text":
                    search_term = st.text_input("Enter text to search:")
                    if search_term:
                        results = []
                        for page_num in range(doc.page_count):
                            page = doc[page_num]
                            text_instances = page.search_for(search_term)
                            if text_instances:
                                results.append(
                                    {
                                        "page": page_num + 1,
                                        "occurrences": len(text_instances),
                                        "coordinates": text_instances,
                                    }
                                )

                        if results:
                            st.success(
                                f"Found '{search_term}' in {len(results)} page(s)"
                            )
                            for result in results:
                                st.write(
                                    f"**Page {result['page']}:** {result['occurrences']} occurrence(s)"
                                )
                                for i, rect in enumerate(result["coordinates"]):
                                    st.write(
                                        f"  Position {i+1}: ({rect.x0:.1f}, {rect.y0:.1f}) to ({rect.x1:.1f}, {rect.y1:.1f})"
                                    )
                        else:
                            st.warning(f"Text '{search_term}' not found in document")

                elif pymupdf_option == "Table Detection":
                    found_any_table = False
                    csv_buffers = []
                    for page_num in range(doc.page_count):
                        page = doc[page_num]
                        table_finder = page.find_tables()
                        tables = table_finder.tables if table_finder else []
                        if tables:
                            found_any_table = True
                            st.success(
                                f"Found {len(tables)} table(s) on page {page_num + 1}"
                            )
                            for i, table in enumerate(tables):
                                st.write(f"**Page {page_num + 1} - Table {i + 1}:**")
                                table_data = table.extract()
                                if table_data:
                                    df = clean_table_columns(table_data)

                                    st.dataframe(df)
                                    csv_buffers.append(df)
                        else:
                            st.warning(f"No tables found on page {page_num + 1}")
                    if not found_any_table:
                        st.warning("No tables found in the document.")
                    if csv_buffers:
                        csv_content = export_tables_to_csv(csv_buffers)
                        st.download_button(
                            "Export tables .csv",
                            csv_content,
                            file_name=f"{os.path.splitext(fname)[0]}_tables.csv",
                            key="export_tables_csv",
                        )

                elif pymupdf_option == "Image Extraction":
                    for page_num in range(doc.page_count):
                        page = doc[page_num]
                        image_list = page.get_images()
                        if image_list:
                            st.success(
                                f"Page {page_num + 1}: {len(image_list)} embedded image(s) found"
                            )
                            for i, img in enumerate(image_list):
                                xref = img[0]
                                base_image = doc.extract_image(xref)
                                image_bytes = base_image["image"]
                                image_ext = base_image["ext"]
                                st.image(
                                    image_bytes,
                                    caption=f"Page {page_num + 1} - Image {i+1} (.{image_ext})",
                                )
                
                doc.close()

            with tab_plumber:
                st.subheader("PDFplumber Text & Table Extraction")

                st.markdown("**Select extraction mode:**")
                plumber_option = option_menu(
                    None,
                    [
                        "All Text",
                        "Specific Page",
                        "Table Extraction",
                        "Image Extraction",
                    ],
                    icons=[
                        "file-text",
                        "file-earmark",
                        "table",
                        "image",
                    ],
                    orientation="horizontal",
                    key="plumber_mode",
                )

                with pdfplumber.open(file_path) as pdf:

                    if plumber_option == "All Text":
                        all_text = ""
                        for page_num, page in enumerate(pdf.pages):
                            page_text = page.extract_text()
                            if page_text:
                                all_text += (
                                    f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                                )
                        st.text_area("Full Document Text:", all_text, height=400)
                        st.download_button(
                            "Export .txt",
                            all_text,
                            file_name=f"{os.path.splitext(fname)[0]}_plumber.txt",
                            key="export_plumber_txt",
                        )

                    elif plumber_option == "Specific Page":
                        page_number = st.number_input(
                            "Enter page number:",
                            min_value=1,
                            max_value=len(pdf.pages),
                            step=1,
                            value=1,
                        )
                        page = pdf.pages[page_number - 1]
                        page_text = page.extract_text()
                        st.text_area(
                            f"Page {page_number} Text:",
                            page_text or "No text found",
                            height=400,
                        )
                        st.download_button(
                            "Export page .txt",
                            page_text or "",
                            file_name=f"{os.path.splitext(fname)[0]}_plumber_page_{page_number}.txt",
                            key="export_plumber_page_txt",
                        )

                    elif plumber_option == "Table Extraction":
                        found_tables = False
                        csv_buffers = []
                        for page_num, page in enumerate(pdf.pages):
                            tables = page.extract_tables()
                            if tables:
                                found_tables = True
                                st.success(
                                    f"Page {page_num + 1}: {len(tables)} table(s) found"
                                )
                                for i, table in enumerate(tables):
                                    if table and len(table) > 0:
                                        st.write(
                                            f"**Page {page_num + 1} - Table {i + 1}:**"
                                        )
                                        df = clean_table_columns(table)

                                        st.dataframe(df)
                                        csv_buffers.append(df)

                        if not found_tables:
                            st.warning("No tables found in the document")
                        if csv_buffers:
                            csv_content = export_tables_to_csv(csv_buffers)
                            st.download_button(
                                "Export tables .csv",
                                csv_content,
                                file_name=f"{os.path.splitext(fname)[0]}_plumber_tables.csv",
                                key="export_plumber_tables_csv",
                            )

                    elif plumber_option == "Image Extraction":
                        found_images = False
                        for page_num, page in enumerate(pdf.pages):
                            if hasattr(page, "images") and page.images:
                                found_images = True
                                st.success(
                                    f"Page {page_num + 1}: {len(page.images)} image(s) found"
                                )
                                for i, img in enumerate(page.images):
                                    st.write(f"**Image {i + 1}:**")
                                    st.write(
                                        f"Position: ({img['x0']:.1f}, {img['y0']:.1f}) to ({img['x1']:.1f}, {img['y1']:.1f})"
                                    )
                                    size_width = img["x1"] - img["x0"]
                                    size_height = img["y1"] - img["y0"]
                                    st.write(f"Size: {size_width} x {size_height}")

                                    page_width = page.width
                                    page_height = page.height

                                    x0 = float(img["x0"]) if img.get("x0") is not None else 0.0
                                    y0 = float(img["y0"]) if img.get("y0") is not None else 0.0
                                    x1 = float(img["x1"]) if img.get("x1") is not None else page_width
                                    y1 = float(img["y1"]) if img.get("y1") is not None else page_height

                                    x0 = max(0.0, min(x0, page_width))
                                    x1 = max(0.0, min(x1, page_width))
                                    y0 = max(0.0, min(y0, page_height))
                                    y1 = max(0.0, min(y1, page_height))

                                    left = min(x0, x1)
                                    right = max(x0, x1)
                                    top = min(y0, y1)
                                    bottom = max(y0, y1)

                                    bbox = (left, top, right, bottom)
                                    cropped_page = page.crop(bbox, strict=False)

                                    try:
                                        cropped_image = cropped_page.to_image(
                                            resolution=150
                                        )
                                        st.image(
                                            cropped_image.original,
                                            caption=f"Page {page_num + 1} - Image {i + 1} (Cropped)",
                                        )
                                    except Exception as e:
                                        st.warning(
                                            f"Could not display cropped image: {str(e)}"
                                        )

                                    if "object" in img:
                                        st.write(f"Object ID: {img['object']}")
                                    st.write("---")

            with tab_camelot:
                st.subheader("Camelot Advanced Table Extraction")
                col1, col2 = st.columns(2)
                with col1:
                    camelot_mode = st.selectbox(
                        "Table Algorithm:",
                        ["lattice", "stream"],
                        help="Lattice: Detects cell boundaries. Stream: Uses whitespace patterns."
                    )
                with col2:
                    pages_input = st.text_input(
                        "Pages (e.g., '1,2,3' or 'all'):",
                        value="all",
                        help="Specify page numbers separated by commas or 'all' for all pages"
                    )
                with st.expander("Advanced Options"):
                    col3, col4 = st.columns(2)
                    with col3:
                        password = st.text_input("PDF Password (if needed):", type="password")
                    with col4:
                        if camelot_mode == "lattice":
                            line_scale = st.slider("Line Scale", min_value=10, max_value=50, value=15, help="Only available for lattice algorithm")
                        else:
                            line_scale = None
                            st.info("Line Scale only available for lattice algorithm")
                show_debug = st.checkbox("Show Visual Debugging", help="Display detected table boundaries")
                try:
                    if pages_input.lower() == "all":
                        pages_param = "all"
                    else:
                        try:
                            pages_param = [int(p.strip()) for p in pages_input.split(",")]
                        except ValueError:
                            st.error("Invalid page format. Use comma-separated numbers or 'all'")
                            pages_param = "all"
                    gs_available = _is_ghostscript_available()
                    effective_mode = camelot_mode.lower()
                    if effective_mode == "lattice" and not gs_available:
                        st.warning("Ghostscript not found. 'lattice' mode requires Ghostscript; automatically switching to 'stream' mode.")
                        effective_mode = "stream"

                    camelot_params = {
                        "filepath": file_path,
                        "flavor": effective_mode,
                        "pages": pages_param
                    }
                    if effective_mode == "lattice" and line_scale is not None:
                        camelot_params["line_scale"] = line_scale
                    if password:
                        camelot_params["password"] = password
                    with st.spinner("Extracting tables with Camelot..."):
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", UserWarning)
                            try:
                                tables = camelot.read_pdf(**camelot_params)
                            except ZeroDivisionError as zde:
                                st.error(f"Camelot encountered a division by zero error: {str(zde)}")
                                st.warning("⚠️ This PDF cannot be processed by Camelot.")
                                st.info("💡 **Please try these alternatives:**")
                                st.info("1. **PDFplumber** - Switch to the 'PDFplumber' tab (recommended)")
                                st.info("2. **PyMuPDF** - Use 'Table Detection' in the PyMuPDF tab")
                                raise
                            except Exception as camelot_exc:
                                err_text = str(camelot_exc).lower()
                                if ("ghostscript" in err_text or "image conversion failed" in err_text) and effective_mode == "lattice":
                                    st.info("An error occurred in 'lattice' mode (Ghostscript missing/not working). Falling back to 'stream' mode…")
                                    fallback_params = dict(camelot_params)
                                    fallback_params["flavor"] = "stream"
                                    try:
                                        tables = camelot.read_pdf(**fallback_params)
                                        effective_mode = "stream"
                                    except ZeroDivisionError:
                                        st.error("Stream mode also failed with division by zero error.")
                                        st.info("💡 This PDF is not compatible with Camelot. Please use PDFplumber or PyMuPDF instead.")
                                        raise
                                else:
                                    raise

                    if len(tables) > 0:
                        st.success(f"Found {len(tables)} table(s) using {effective_mode} algorithm")

                        for i, table in enumerate(tables):
                            st.write(f"**Table {i + 1} (Page {table.page}):**")

                            report = table.parsing_report
                            col_report1, col_report2, col_report3 = st.columns(3)
                            with col_report1:
                                st.metric("Accuracy", f"{report['accuracy']:.1f}%")
                            with col_report2:
                                st.metric("Whitespace", f"{report['whitespace']:.1f}%")
                            with col_report3:
                                st.metric("Order", f"{report['order']:.1f}%")

                            df = table.df
                            st.dataframe(df, width='stretch')

                            if show_debug:
                                try:
                                    import matplotlib.pyplot as plt
                                    fig, ax = plt.subplots(figsize=(10, 6))
                                    camelot.plot(table, kind='contour', ax=ax)
                                    st.pyplot(fig)
                                    plt.close(fig)
                                except Exception as e:
                                    st.warning(f"Could not display visual debugging: {str(e)}")

                            st.write("---")

                        st.subheader("Export Options")
                        export_col1, export_col2, export_col3 = st.columns(3)

                        with export_col1:
                            csv_content = export_tables_to_csv([table.df for table in tables])
                            st.download_button(
                                "Download CSV",
                                csv_content,
                                file_name=f"{os.path.splitext(fname)[0]}_camelot_{effective_mode}.csv",
                                key="export_camelot_csv",
                            )

                        with export_col2:
                            excel_io = io.BytesIO()
                            with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
                                for idx, table in enumerate(tables):
                                    table.df.to_excel(writer, sheet_name=f'Table_{idx+1}_Page_{table.page}', index=False)
                            st.download_button(
                                "Download Excel",
                                excel_io.getvalue(),
                                file_name=f"{os.path.splitext(fname)[0]}_camelot_{effective_mode}.xlsx",
                                key="export_camelot_excel",
                            )

                        with export_col3:
                            json_data = []
                            for table in tables:
                                json_data.append({
                                    "page": table.page,
                                    "accuracy": table.parsing_report["accuracy"],
                                    "data": table.df.to_dict('records')
                                })
                            st.download_button(
                                "Download JSON",
                                json.dumps(json_data, indent=2),
                                file_name=f"{os.path.splitext(fname)[0]}_camelot_{effective_mode}.json",
                                key="export_camelot_json",
                            )
                        
                    
                    else:
                        st.warning("No tables found in the document")
                        st.info("Try switching between 'lattice' and 'stream' algorithms or adjusting the line scale")

                except Exception as e:
                    error_msg = str(e)
                    st.error(f"Error extracting tables: {error_msg}")
                    
                    if "ghostscript" in error_msg.lower():
                        st.warning("⚠️ Ghostscript is not installed. Camelot requires Ghostscript for table extraction.")
                        st.info("💡 **Alternative Solutions:**")
                        st.info("1. **Use PDFplumber instead** - Switch to the 'PDFplumber' tab above for table extraction")
                        st.info("2. **Use PyMuPDF** - Try the 'Table Detection' option in the PyMuPDF tab")
                        st.info("3. **Install Ghostscript** - Follow the instructions at: https://camelot-py.readthedocs.io/en/latest/user/install-deps.html")
                    elif "password" in error_msg.lower():
                        st.info("If the PDF is password-protected, enter the password above")
                    elif "division by zero" in error_msg.lower() or "float division" in error_msg.lower():
                        st.warning("⚠️ Camelot encountered an error processing this PDF (division by zero).")
                        st.info("💡 **This usually happens when:**")
                        st.info("• The PDF has unusual formatting or dimensions")
                        st.info("• The PDF is scanned (image-based) rather than text-based")
                        st.info("• The table structure is too complex for Camelot to detect")
                        st.markdown("---")
                        st.success("✅ **Recommended Solutions:**")
                        st.info("1. **Use PDFplumber** - Switch to the 'PDFplumber' tab above (works better with complex PDFs)")
                        st.info("2. **Use PyMuPDF** - Try the 'Table Detection' option in the PyMuPDF tab")
                        st.info("3. **Try different algorithm** - Switch between 'lattice' and 'stream' modes above")
                    else:
                        st.info("Note: Camelot only works with text-based PDFs, not scanned images")
                        st.info("💡 Try using PDFplumber or PyMuPDF tabs instead")

    else:
        st.error("PDF file not found. Please upload again.")