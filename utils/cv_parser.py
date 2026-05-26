"""Extraction de texte depuis CV : TXT, PDF ou image (OCR)."""

from __future__ import annotations

import io
from pathlib import Path

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
_PDF_EXT = {".pdf"}
_TEXT_EXT = {".txt", ".text", ".md"}


def _read_txt(raw: bytes) -> str:
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encodage du fichier texte non reconnu.")


def _read_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("Support PDF indisponible (pip install pypdf).") from exc

    reader = PdfReader(io.BytesIO(raw))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    combined = "\n".join(parts).strip()
    if len(combined) < 40:
        raise ValueError(
            "PDF sans texte extractible (scan/image). Envoyez une image (PNG/JPG) pour l'OCR."
        )
    return combined


def _read_image(raw: bytes) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Support image indisponible (pip install pillow).") from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise ValueError("OCR indisponible (pip install pytesseract).") from exc

    image = Image.open(io.BytesIO(raw))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    try:
        text = pytesseract.image_to_string(image, lang="eng+fra")
    except pytesseract.TesseractNotFoundError:
        raise ValueError(
            "Tesseract OCR n'est pas installé sur ce PC. "
            "Installez-le : https://github.com/tesseract-ocr/tesseract "
            "ou utilisez un CV en .txt / PDF texte."
        ) from None
    except Exception as exc:
        raise ValueError(f"Échec OCR sur l'image : {exc}") from exc

    cleaned = text.strip()
    if len(cleaned) < 20:
        raise ValueError("OCR : texte trop court. Vérifiez la qualité de l'image.")
    return cleaned


def extract_text_from_cv(filename: str, raw: bytes) -> str:
    """
    Extrait le texte d'un CV selon l'extension du fichier.
    Formats : .txt, .pdf, .png, .jpg, .jpeg, .webp, .bmp, .tiff
    """
    if not raw:
        raise ValueError("Fichier vide.")
    ext = Path(filename).suffix.lower()
    if ext in _TEXT_EXT:
        return _read_txt(raw)
    if ext in _PDF_EXT:
        return _read_pdf(raw)
    if ext in _IMAGE_EXT:
        return _read_image(raw)
    allowed = ", ".join(sorted(_TEXT_EXT | _PDF_EXT | _IMAGE_EXT))
    raise ValueError(f"Format non supporté ({ext}). Formats acceptés : {allowed}")
