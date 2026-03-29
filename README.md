# PhonePe Statement Analyzer

A small Streamlit app that parses PhonePe PDF statements, extracts transaction data, computes daily received totals, and provides cleaned CSV/XLSX downloads.

## Setup Guide

1. Install Python
   - Recommended: Python 3.10 or newer.
   - Verify with:
     ```bash
     python --version
     ```

2. Create and activate a virtual environment (recommended)
   - Windows PowerShell:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - Windows Command Prompt:
     ```cmd
     python -m venv .venv
     .\.venv\Scripts\activate.bat
     ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

## Startup Guide

From the project root (`c:\MySpace\Projects\PhonePay_Statement_Analyzer`):

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal (usually `http://localhost:8501`).

## How to Use

1. Open the app in your browser.
2. Upload a PhonePe PDF statement using the file uploader.
3. Wait while the PDF is parsed.
4. View:
   - total received amount
   - daily credit summary
   - cleaned transaction table
5. Download results as CSV or Excel.

## Notes

- This app relies on `pdfplumber` text extraction and a regex parser in `app.py`.
- If no transactions are found, verify that the uploaded PDF matches the expected PhonePe statement layout.
- Output files are generated from the cleaned data and do not include raw PDF formatting.

## Files

- `app.py` — main Streamlit application
- `requirements.txt` — Python dependencies
- `README.md` — setup and startup guide
