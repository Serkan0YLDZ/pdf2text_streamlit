# PDF to Text & Table Extraction Tool

This is a text-based Streamlit project for extracting text, tables, and visual content from your PDF files. You can see which of the three text extraction libraries works better for your PDF files.

![Demo Video](pdf2text-ezgif.com-video-to-gif-converter.gif)

## Features

### Multiple PDF Processing Libraries
This project uses three different powerful libraries for PDF processing:

#### 1. **PyMuPDF (fitz)**
<img src="https://pymupdf.readthedocs.io/en/latest/_static/sidebar-logo-dark.svg" width="200" alt="PyMuPDF Logo">

### PyMuPDF Modes
- **All Text**: Extract all document text
- **Specific Page**: Process a specific page
- **Markdown/JSON Output**: Structured data format
- **Search Text**: Text search and location finding
- **Table Detection**: Automatic table detection
- **Image Extraction**: Extract embedded images

#### 2. **PDFplumber**
<img src="https://pypi-camo.freetls.fastly.net/2629777effa9ef41cbc96c8122352b9450a95385/68747470733a2f2f7365637572652e67726176617461722e636f6d2f6176617461722f39376534636162633362393334666533313930333530613566313634613463393f73697a653d323235" width="200" alt="PDFplumber">

### PDFplumber Modes
- **All Text**: Full text extraction
- **Specific Page**: Page-based processing
- **Table Extraction**: Advanced table extraction
- **Image Extraction**: Image detection and cropping

#### 3. **Camelot**
<img src="https://camelot-py.readthedocs.io/en/master/_static/camelot.png" width="200" alt="Camelot Logo">

### Camelot Modes
- **Lattice**: Table detection based on cell boundaries
- **Stream**: Detection based on whitespace patterns
- **Advanced Options**: Line scale, page selection, password support
- **Visual Debugging**: Visualize detected table boundaries

## Installation

### Steps

1. **Clone the repository:**
```bash
git clone https://github.com/Serkan0YLDZ/pdf2text_streamlit.git
cd pdf2text_streamlit
```

2. **Create a virtual environment:**
```bash
python -m venv myenv
source myenv/bin/activate  # Linux/Mac
# or
myenv\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

### Start the Application
```bash
streamlit run main.py
```

## Project Structure

```
pdf2text_streamlit/
├── main.py                     # Main application file
├── pages/
│   ├── upload.py               # PDF upload page
│   ├── directTextExtraction.py # Text/table extraction page
│   └── docs/                   # Folder where uploaded PDFs are stored
├── requirements.txt            # Python dependencies
├── packages.txt                # System dependencies (Ghostscript)
├── pdf2text.mp4                # Demo video
└── README.md                   # This file
```

## Project Limitations

- Cannot extract very complex tables and scanned (image-based) tables 