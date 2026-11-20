"""PDF text extraction with clear errors for bad PDFs and optional OCR."""
import io
from pypdf import PdfReader
from pypdf.errors import PyPdfError


class PdfProblem(Exception):
    """Raised for PDFs we cannot use. `.message` is safe to show to users."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _ocr_page_images(reader):
    """Optional OCR: needs `pip install pytesseract pillow` and the Tesseract program.
    Returns extracted text, or "" if OCR is not available."""
    try:
        import pytesseract
        from PIL import Image
        pytesseract.get_tesseract_version()
    except Exception:
        return ""
    text = ""
    for page in reader.pages:
        try:
            for img in page.images:
                text += pytesseract.image_to_string(Image.open(io.BytesIO(img.data))) + "\n"
        except Exception:
            continue
    return text


def extract_text(path):
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            # Many PDFs are "encrypted" with an empty user password.
            if not reader.decrypt(""):
                raise PdfProblem("This PDF is password-protected. Remove the password and upload again.")
        pages = reader.pages
        if len(pages) == 0:
            raise PdfProblem("This PDF has no pages.")
        text = "".join((p.extract_text() or "") for p in pages)
    except PdfProblem:
        raise
    except (PyPdfError, ValueError, OSError, KeyError, AttributeError, TypeError, NotImplementedError):
        raise PdfProblem("This file is not a valid PDF or is corrupted.")

    if not text.strip():
        text = _ocr_page_images(reader)
    if not text.strip():
        raise PdfProblem(
            "No text could be extracted - this looks like a scanned/image-only PDF. "
            "Install optional OCR (pytesseract + Tesseract) or upload a text-based PDF."
        )
    return text
