import os
import streamlit as st
import uuid


def show():
    _, col2, _ = st.columns([1, 1, 1])

    with col2:
        st.title("Upload PDF")
        st.write("Please upload your PDF file below.")

        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

        if uploaded_file:
            st.success("File uploaded successfully!")
            random_filename = str(uuid.uuid4()) + ".pdf"
            st.session_state.uploaded_file = uploaded_file
            st.session_state.safe_filename = random_filename

            docs_dir = os.path.join(os.path.dirname(__file__), "docs")
            os.makedirs(docs_dir, exist_ok=True)
            file_path = os.path.join(docs_dir, random_filename)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.file_path = file_path
            st.session_state.file_uploaded = True
            st.session_state.menu_selection = "Direct Text Extraction"
            st.session_state.force_menu_update = st.session_state.get('force_menu_update', 0) + 1
            st.info(f"File saved to {file_path}")
            st.success("Redirecting to text extraction page...")
            st.rerun()
