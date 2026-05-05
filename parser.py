import os

def extract_text_from_file(filepath):
    """Extract text from PDF, DOC, or DOCX files."""
    ext = filepath.rsplit('.', 1)[-1].lower()
    try:
        if ext == 'pdf':
            return extract_from_pdf(filepath)
        elif ext == 'docx':
            return extract_from_docx(filepath)
        elif ext == 'doc':
            return extract_from_doc(filepath)
    except Exception as e:
        return f"[Text extraction failed: {e}]"
    return ""

def extract_from_pdf(filepath):
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text.strip()
    except ImportError:
        pass
    # Fallback: pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        return f"[PDF extraction error: {e}]"

def extract_from_docx(filepath):
    try:
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return f"[DOCX extraction error: {e}]"

def extract_from_doc(filepath):
    try:
        import subprocess
        result = subprocess.run(['antiword', filepath], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"[DOC extraction error: {e}]"
