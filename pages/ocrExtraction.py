import os
import io
import json
import pandas as pd
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from streamlit_option_menu import option_menu
import pypdfium2 as pdfium

from img2table.document import Image as Img2TableImage
from img2table.ocr import TesseractOCR
import deepdoctection as dd


def get_ocr_config(ocr_engine):
    """
    Generate OCR configuration based on selected engine
    """
    config_overwrite = []
    
    if ocr_engine == "Tesseract":
        config_overwrite.extend([
            "OCR.USE_TESSERACT=True",
            "OCR.USE_DOCTR=False",
            "OCR.USE_TEXTRACT=False"
        ])
    elif ocr_engine == "DocTr":
        config_overwrite.extend([
            "OCR.USE_TESSERACT=False",
            "OCR.USE_DOCTR=True",
            "OCR.USE_TEXTRACT=False",
            "OCR.WEIGHTS.DOCTR_RECOGNITION.PT=doctr/crnn_vgg16_bn/pt/master-fde31e4a.pt"
        ])
    
    # Common settings
    config_overwrite.extend([
        "USE_TABLE_SEGMENTATION=True",
        # Cache configuration to prevent repeated downloads - use project directory
        f"CACHE_DIR={os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'deepdoctection')}"
    ])
    
    return config_overwrite


def check_model_exists():
    """
    Check if DocTr model already exists in cache
    """
    # Use project directory for cache
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(project_dir, "cache", "deepdoctection", "weights", "doctr", "crnn_vgg16_bn", "pt", "master-fde31e4a.pt")
    return os.path.exists(model_path)


def show_doctr_error(error_msg):
    """
    Display DocTr model vocabulary mismatch error message
    """
    st.error(f"""
    **DocTr Model Vocabulary Mismatch Error:**
    
    {error_msg}
    
    **Solution:** The system is already using the 'master' DocTr model for best compatibility.
    If this error persists, please try using Tesseract instead.
    """)


def show():
    st.title("OCR Extraction")
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
            

            tab_img2table, tab_deepdoctection = st.tabs([
                "img2table",
                "DeepDoctection",
            ])

            with tab_img2table:
                st.subheader("img2table")
                page_num = st.number_input("Page", min_value=1, max_value=len(pdfium.PdfDocument(file_path)), value=1, key="img2table_page")
                scale = st.slider("Render scale", 1.0, 3.0, 2.0, 0.5, key="img2table_scale")
                lang = st.text_input("OCR language", value="eng", key="img2table_lang")

                if st.button("Extract tables (img2table)", key="btn_img2table_extract"):
                    with st.spinner("Extracting tables…"):
                        try:
                            doc = pdfium.PdfDocument(file_path)
                            pg = doc[page_num - 1]
                            pil_img = pg.render(scale=scale).to_pil()

                            ocr_engine = TesseractOCR(lang=lang)
                            _buf = io.BytesIO()
                            pil_img.save(_buf, format="PNG")
                            _bytes = _buf.getvalue()
                            doc = Img2TableImage(src=_bytes)
                            tables = doc.extract_tables(ocr=ocr_engine, implicit_rows=True, borderless_tables=True)
                            frames = [tbl.df for tbl in tables if hasattr(tbl, 'df')]

                            if frames:
                                st.success(f"{len(frames)} table(s) found")

                                csv_accum = io.StringIO()
                                excel_io = io.BytesIO()
                                excel_sheets = {}

                                for idx, df in enumerate(frames, 1):
                                    with st.expander(f"Table {idx}"):
                                        st.dataframe(df, use_container_width=True)
                                    csv_accum.write(f"# Table {idx}\n")
                                    df.to_csv(csv_accum, index=False)
                                    csv_accum.write("\n\n")
                                    excel_sheets[f"Table_{idx}"] = df

                                with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
                                    for sheet_name, df in excel_sheets.items():
                                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.download_button(
                                        "Download CSV",
                                        csv_accum.getvalue(),
                                        file_name=f"{os.path.splitext(fname)[0]}_tables.csv",
                                        key="dl_csv",
                                    )
                                with col2:
                                    st.download_button(
                                        "Download Excel",
                                        excel_io.getvalue(),
                                        file_name=f"{os.path.splitext(fname)[0]}_tables.xlsx",
                                        key="dl_xlsx",
                                    )
                                with col3:
                                    json_payload = [
                                        {
                                            "table_id": idx + 1,
                                            "data": df.to_dict('records'),
                                        }
                                        for idx, df in enumerate(frames)
                                    ]
                                    st.download_button(
                                        "Download JSON",
                                        json.dumps(json_payload, ensure_ascii=False, indent=2),
                                        file_name=f"{os.path.splitext(fname)[0]}_tables.json",
                                        key="dl_json",
                                    )
                            else:
                                st.warning("No tables detected")
                        except Exception as e:
                            error_msg = str(e)
                            if "size mismatch" in error_msg and "RecognitionPredictor" in error_msg:
                                show_doctr_error(error_msg)
                            else:
                                st.error(f"Error: {error_msg}")

            with tab_deepdoctection:
                st.subheader("DeepDoctection")
                
                # OCR Engine Selection
                st.markdown("**OCR Engine Configuration:**")
                col_ocr1, col_ocr2 = st.columns(2)
                
                with col_ocr1:
                    ocr_engine = st.selectbox(
                        "OCR Engine",
                        ["Tesseract", "DocTr"],
                        index=0,
                        key="ocr_engine_select",
                        help="Choose between Tesseract (stable) or DocTr (faster, more accurate)"
                    )
                    
                with col_ocr2:
                    # OCR Engine Information
                    if ocr_engine == "Tesseract":
                        st.info("Tesseract: Stable and reliable OCR engine")
                    elif ocr_engine == "DocTr":
                        model_exists = check_model_exists()
                        if model_exists:
                            st.success("✅ DocTr: Model cached and ready")
                        else:
                            st.warning("⚠️ DocTr: Model will be downloaded on first use")
                
                st.markdown("**Select extraction mode:**")
                deepdoctection_option = option_menu(
                    None,
                    [
                        "Document Analysis",
                        "Table Detection & Structure",
                        "Text Extraction",
                    ],
                    icons=[
                        "file-text",
                        "table",
                        "file-earmark-text",
                    ],
                    orientation="horizontal",
                    key="deepdoctection_mode",
                )

                if deepdoctection_option == "Document Analysis":
                    if st.button("Analyze Document", key="btn_deepdoctection_analyze"):
                        try:
                            # Get OCR configuration based on selected engine
                            config_overwrite = get_ocr_config(ocr_engine)
                            
                            
                            with st.spinner(f"Initializing analyzer with {ocr_engine}..."):
                                analyzer = dd.get_dd_analyzer(config_overwrite=config_overwrite)
                            
                            with st.spinner("Analyzing document..."):
                                df = analyzer.analyze(path=file_path)
                                df.reset_state()
                                
                                doc = iter(df)
                                pages_data = []
                                
                                try:
                                    while True:
                                        page = next(doc)
                                        pages_data.append(page)
                                except StopIteration:
                                    pass

                                if pages_data:
                                    st.success(f"Successfully analyzed {len(pages_data)} page(s)")
                                    
                                    st.subheader("Document Summary")
                                    for i, page in enumerate(pages_data):
                                        with st.expander(f"Page {i+1}"):
                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.metric("Width", f"{page.width}px")
                                                st.metric("Height", f"{page.height}px")
                                            with col2:
                                                st.metric("Layouts", len(page.layouts) if hasattr(page, 'layouts') else 0)
                                                st.metric("Tables", len(page.tables) if hasattr(page, 'tables') else 0)
                                            with col3:
                                                st.metric("Figures", len(page.figures) if hasattr(page, 'figures') else 0)
                                                st.metric("Words", len(page.words) if hasattr(page, 'words') else 0)
                                            try:
                                                viz_image = page.viz(show_figures=True, show_tables=True, show_layouts=True, interactive=False)
                                                st.image(viz_image, caption=f"Page {i+1}", use_container_width=True)
                                            except Exception:
                                                pass


                                    st.subheader("Export Options")
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        json_data = []
                                        for i, page in enumerate(pages_data):
                                            page_dict = {
                                                "page_number": i + 1,
                                                "width": page.width,
                                                "height": page.height,
                                                "text": page.text if hasattr(page, 'text') else "",
                                                "layouts": [{"category": layout.category_name, "score": layout.score} for layout in page.layouts] if hasattr(page, 'layouts') else [],
                                                "tables": [{"rows": table.number_of_rows, "columns": table.number_of_columns} for table in page.tables] if hasattr(page, 'tables') else []
                                            }
                                            json_data.append(page_dict)
                                        
                                        st.download_button(
                                            "Download JSON",
                                            json.dumps(json_data, indent=2, ensure_ascii=False),
                                            file_name=f"{os.path.splitext(fname)[0]}_deepdoctection.json",
                                            key="export_deepdoctection_json",
                                        )

                                    with col2:
                                        all_text = ""
                                        for i, page in enumerate(pages_data):
                                            if hasattr(page, 'text') and page.text:
                                                all_text += f"\n--- Page {i+1} ---\n{page.text}\n"
                                        
                                        st.download_button(
                                            "Download Text",
                                            all_text,
                                            file_name=f"{os.path.splitext(fname)[0]}_deepdoctection.txt",
                                            key="export_deepdoctection_txt",
                                        )
                        except Exception as e:
                            error_msg = str(e)
                            if "size mismatch" in error_msg and "RecognitionPredictor" in error_msg:
                                show_doctr_error(error_msg)
                            else:
                                st.error(f"Error: {error_msg}")

                elif deepdoctection_option == "Table Detection & Structure":
                    if st.button("Detect Tables", key="btn_deepdoctection_tables"):
                        try:
                            # Get OCR configuration based on selected engine
                            config_overwrite = get_ocr_config(ocr_engine)
                            
                            
                            with st.spinner(f"Initializing analyzer with {ocr_engine}..."):
                                analyzer = dd.get_dd_analyzer(config_overwrite=config_overwrite)
                            
                            with st.spinner("Detecting tables..."):
                                df = analyzer.analyze(path=file_path)
                                df.reset_state()
                                
                                doc = iter(df)
                                all_tables = []
                                
                                try:
                                    while True:
                                        page = next(doc)
                                        if hasattr(page, 'tables') and page.tables:
                                            for table in page.tables:
                                                all_tables.append((page, table))
                                except StopIteration:
                                    pass

                            if all_tables:
                                st.success(f"Found {len(all_tables)} table(s)")
                                
                                for i, (page, table) in enumerate(all_tables):
                                    with st.expander(f"Table {i+1} (Page {getattr(page, 'page_number', 'Unknown')})"): 
                                        col_table1, col_table2 = st.columns(2)
                                        
                                        with col_table1:
                                            st.metric("Rows", table.number_of_rows)
                                            st.metric("Columns", table.number_of_columns)
                                            st.metric("Score", f"{table.score:.3f}")
                                        
                                        with col_table2:
                                            if hasattr(table, 'max_row_span'):
                                                st.metric("Max Row Span", table.max_row_span)
                                            if hasattr(table, 'max_col_span'):
                                                st.metric("Max Col Span", table.max_col_span)
                                            if hasattr(table, 'reading_order'):
                                                st.metric("Reading Order", table.reading_order or "N/A")

                                        if hasattr(table, 'html') and table.html:
                                            st.subheader("Table Structure")
                                            st.markdown(table.html, unsafe_allow_html=True)

                                        if hasattr(table, 'csv') and table.csv:
                                            st.subheader("Table Data")
                                            if table.csv and len(table.csv) > 0:
                                                columns = table.csv[0] if table.csv[0] else []
                                                seen = {}
                                                unique_columns = []
                                                for col in columns:
                                                    if not col:
                                                        col = 'Column'
                                                    base_name = col.strip()
                                                    if base_name in seen:
                                                        seen[base_name] += 1
                                                        unique_columns.append(f"{base_name}_{seen[base_name]}")
                                                    else:
                                                        seen[base_name] = 0
                                                        unique_columns.append(base_name)
                                                df_table = pd.DataFrame(table.csv[1:], columns=unique_columns)
                                                st.dataframe(df_table)

                                        # Display table text
                                        if hasattr(table, 'text') and table.text:
                                            st.subheader("Table Text")
                                            st.text_area("Table Content", table.text, height=200, key=f"table_text_{i}")

                                if all_tables:
                                    st.subheader("Export All Tables")
                                    col1, col2, col3 = st.columns(3)
                                    
                                    with col1:
                                        csv_content = io.StringIO()
                                        for i, (page, table) in enumerate(all_tables):
                                            csv_content.write(f"# Table {i+1} (Page {getattr(page, 'page_number', 'Unknown')})\n")
                                            if hasattr(table, 'csv') and table.csv:
                                                df_table = pd.DataFrame(table.csv[1:], columns=table.csv[0] if table.csv else [])
                                                df_table.to_csv(csv_content, index=False)
                                            csv_content.write("\n")
                                        
                                        st.download_button(
                                            "Download CSV",
                                            csv_content.getvalue(),
                                            file_name=f"{os.path.splitext(fname)[0]}_tables.csv",
                                            key="export_tables_csv",
                                        )

                                    with col2:
                                        excel_io = io.BytesIO()
                                        with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
                                            for i, (page, table) in enumerate(all_tables):
                                                if hasattr(table, 'csv') and table.csv:
                                                    df_table = pd.DataFrame(table.csv[1:], columns=table.csv[0] if table.csv else [])
                                                    df_table.to_excel(writer, sheet_name=f'Table_{i+1}', index=False)
                                        
                                        st.download_button(
                                            "Download Excel",
                                            excel_io.getvalue(),
                                            file_name=f"{os.path.splitext(fname)[0]}_tables.xlsx",
                                            key="export_tables_excel",
                                        )

                                    with col3:
                                        json_data = []
                                        for i, (page, table) in enumerate(all_tables):
                                            table_data = {
                                                "table_number": i + 1,
                                                "page_number": getattr(page, 'page_number', 'Unknown'),
                                                "rows": table.number_of_rows,
                                                "columns": table.number_of_columns,
                                                "score": table.score,
                                                "csv": table.csv if hasattr(table, 'csv') else None
                                            }
                                            json_data.append(table_data)
                                        
                                        st.download_button(
                                            "Download JSON",
                                            json.dumps(json_data, indent=2, ensure_ascii=False),
                                            file_name=f"{os.path.splitext(fname)[0]}_tables.json",
                                            key="export_tables_json",
                                        )

                            else:
                                st.warning("No tables found in the document")
                        except Exception as e:
                            error_msg = str(e)
                            if "size mismatch" in error_msg and "RecognitionPredictor" in error_msg:
                                show_doctr_error(error_msg)
                            else:
                                st.error(f"Error: {error_msg}")

                elif deepdoctection_option == "Text Extraction":
                    if st.button("Extract Text", key="btn_deepdoctection_text"):
                        try:
                            # Get OCR configuration based on selected engine
                            config_overwrite = get_ocr_config(ocr_engine)
                            
                            
                            with st.spinner(f"Initializing analyzer with {ocr_engine}..."):
                                analyzer = dd.get_dd_analyzer(config_overwrite=config_overwrite)
                            
                            with st.spinner("Extracting text..."):
                                df = analyzer.analyze(path=file_path)
                                df.reset_state()
                                
                                doc = iter(df)
                                pages_data = []
                                
                                try:
                                    while True:
                                        page = next(doc)
                                        pages_data.append(page)
                                except StopIteration:
                                    pass

                            if pages_data:
                                st.success(f"Extracted text from {len(pages_data)} page(s)")
                                
                                for i, page in enumerate(pages_data):
                                    with st.expander(f"Page {i+1} Text"):
                                        if hasattr(page, 'text') and page.text:
                                            st.text_area(f"Page {i+1} Text", page.text, height=300, key=f"page_text_{i}")
                                        else:
                                            st.warning("No text found on this page")

                                all_text = ""
                                for i, page in enumerate(pages_data):
                                    if hasattr(page, 'text') and page.text:
                                        all_text += f"\n--- Page {i+1} ---\n{page.text}\n"
                                
                                if all_text:
                                    st.download_button(
                                        "Download Text",
                                        all_text,
                                        file_name=f"{os.path.splitext(fname)[0]}_text.txt",
                                        key="export_text",
                                    )
                        except Exception as e:
                            error_msg = str(e)
                            if "size mismatch" in error_msg and "RecognitionPredictor" in error_msg:
                                show_doctr_error(error_msg)
                            else:
                                st.error(f"Error: {error_msg}")

    else:
        st.error("PDF file not found. Please upload again.")