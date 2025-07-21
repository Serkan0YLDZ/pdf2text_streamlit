# PDF to Text Streamlit Project

Streamlit based web application for extracting text from PDF files.

<video controls src="pdf2text.mp4" title="Title"></video>

## Supported Methods

**PyMuPDF (fitz)**
- All Text
- Specific Page
- Markdown/JSON Output
- Search Text
- Table Detection
- Image Extraction
- Blocks (layout)
- Words with positions
- HTML export

**PDFplumber**
- All Text
- Specific Page
- Table Extraction
- Image Extraction

**Camelot (Tables Only)**
- Lattice algorithm for table extraction

**Unstructured (Fast Strategy)**
- Fast text extraction with optional page breaks
- Also selectable: hi_res (if installed)

## Installation

```bash
git clone https://github.com/Serkan0YLDZ/pdf2text-streamlit.git
cd pdf2text-streamlit
pip install -r requirements.txt
streamlit run main.py
```

## OCR Models Cache

The application uses local cache for OCR models to avoid repeated downloads:

- **DocTr Model**: Cached in `cache/deepdoctection/weights/doctr/crnn_vgg16_bn/pt/`
- **Model Size**: ~244MB (downloaded once)
- **Cache Directory**: Automatically created in project root
- **Git Ignored**: Cache directory is excluded from version control

The first time you use DocTr OCR, the model will be downloaded. Subsequent uses will be instant.

## UI Overview

- Left: PDF preview.
- Right: Modern tabbed interface per method (PyMuPDF, PDFplumber, Camelot, Unstructured).
- Top of the right panel shows file name, page count, size, and a quick Download PDF button.
- Each method offers appropriate export buttons (.txt / .md / .json / .csv / .html).

## Alternative Usage Patterns and Tips

These reflect common patterns seen in community examples and docs for the same libraries:

- PyMuPDF (fitz)
  - Use `page.get_text("blocks")` for layout-aware chunks (now exposed under “Blocks (layout)”).
  - Use `page.get_text("words")` for token-level coordinates (now exposed under “Words with positions”).
  - Use `page.get_text("html")` for a quick HTML rendition (now exportable as .html).
  - Combine search coordinates with drawing overlays (e.g., highlight boxes) if you want a visual layer (requires additional code to render overlays).

- PDFplumber
  - `page.extract_words()` and `page.extract_tables()` are commonly used together to reconcile structure; tables are now exported to CSV.
  - Images can be located via `page.images` and cropped regions exported; this app previews cropped images for convenience.

- Camelot
  - Try both `flavor="lattice"` and `flavor="stream"` depending on the presence of ruling lines. This app defaults to `stream` but you can modify easily.
  - Export multiple tables by concatenating to a single CSV (app provides a consolidated CSV export).

- Unstructured
  - Strategies differ: `fast` is quick; `hi_res` can yield higher fidelity if dependencies are available. This app provides a strategy selector.
  - You can filter elements by `category` (e.g., `Title`, `NarrativeText`) before exporting; the app already filters for text-like elements.

### Notes
- If you need OCR for scanned PDFs, consider integrating Tesseract or `ocr` strategy via Unstructured (requires extra dependencies not bundled here).
- For heavy documents, batch processing or limiting to selected pages improves performance.
- CSV exports concatenate multiple tables one below another; include a page/table identifier column if you need provenance tracking.