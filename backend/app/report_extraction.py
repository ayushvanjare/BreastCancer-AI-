import io

import fitz
from PIL import Image, UnidentifiedImageError
import pytesseract

MAX_PDF_PAGES = 20
MAX_IMAGE_PIXELS = 40_000_000


class ReportExtractionError(ValueError):
    pass


class OCRUnavailableError(RuntimeError):
    pass


def extract_report(filename: str, content: bytes) -> dict:
    """Extract text from a PDF or raster image without retaining the input."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "pdf":
        return _extract_pdf(content)
    if suffix in {"png", "jpg", "jpeg", "tif", "tiff", "bmp"}:
        return _extract_image(content)
    raise ReportExtractionError("Upload a PDF, PNG, JPG, JPEG, TIFF, or BMP file.")


def _extract_pdf(content: bytes) -> dict:
    if not content.startswith(b"%PDF-"):
        raise ReportExtractionError("The file does not appear to be a valid PDF.")
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ReportExtractionError("Could not read this PDF. It may be damaged or password-protected.") from exc
    with document:
        if document.is_encrypted:
            raise ReportExtractionError("Password-protected PDFs are not supported.")
        if document.page_count == 0:
            raise ReportExtractionError("The PDF contains no pages.")
        if document.page_count > MAX_PDF_PAGES:
            raise ReportExtractionError(f"PDFs are limited to {MAX_PDF_PAGES} pages.")
        extracted = [page.get_text("text") for page in document]
        text = "\n\n".join(part.strip() for part in extracted if part.strip())
        if text:
            return {"text": text, "method": "embedded_text", "pages": document.page_count}
        if any(page.rect.width * page.rect.height * 2.25 > MAX_IMAGE_PIXELS for page in document):
            raise ReportExtractionError("A rendered PDF page would exceed 40 megapixels. Reduce the page dimensions and retry.")
        try:
            ocr_pages = []
            for page in document:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_pages.append(pytesseract.image_to_string(image))
        except pytesseract.TesseractNotFoundError as exc:
            raise OCRUnavailableError("Tesseract OCR is not installed or is not on PATH. Install Tesseract, restart the backend, and retry.") from exc
        except Exception as exc:
            raise ReportExtractionError("Could not OCR this scanned PDF. Check that Tesseract OCR is installed and retry.") from exc
        return {"text": "\n\n".join(part.strip() for part in ocr_pages), "method": "ocr", "pages": document.page_count}


def _extract_image(content: bytes) -> dict:
    try:
        image = Image.open(io.BytesIO(content))
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ReportExtractionError("Images must be 40 megapixels or smaller.")
        image.load()
        if getattr(image, "n_frames", 1) > 1:
            raise ReportExtractionError("Upload a single-frame image; multi-page TIFF files are not supported.")
        text = pytesseract.image_to_string(image)
    except ReportExtractionError:
        raise
    except UnidentifiedImageError as exc:
        raise ReportExtractionError("The file is not a supported or valid image.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError("Tesseract OCR is not installed or is not on PATH. Install Tesseract, restart the backend, and retry.") from exc
    except Exception as exc:
        raise ReportExtractionError("Could not OCR this image. Check the image and Tesseract installation, then retry.") from exc
    return {"text": text.strip(), "method": "ocr", "pages": 1}
