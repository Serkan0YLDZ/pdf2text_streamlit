import streamlit as st
from streamlit_option_menu import option_menu
from pages import upload, directTextExtraction, ocrExtraction


st.set_page_config(page_title="PDF to Text Converter", layout="wide")

st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
""",
    unsafe_allow_html=True,
)

if "menu_selection" not in st.session_state:
    st.session_state.menu_selection = "Upload"

if "file_uploaded" in st.session_state and st.session_state.file_uploaded:
    if st.session_state.menu_selection != "Direct Text Extraction":
        st.session_state.menu_selection = "Direct Text Extraction"

default_index = 1 if st.session_state.menu_selection == "Direct Text Extraction" else 0
menu_key = f"menu_{st.session_state.get('force_menu_update', 0)}"

selected = option_menu(
    None,
    ["Upload", "Direct Text Extraction", "OCR Extraction"],
    icons=["cloud-upload", "list-task", "body-text"],
    key=menu_key,
    orientation="horizontal",
    default_index=default_index,
)

st.session_state.menu_selection = selected

if selected == "Upload":
    upload.show()
elif selected == "Direct Text Extraction":
    directTextExtraction.show()
elif selected == "OCR Extraction":
    ocrExtraction.show()
