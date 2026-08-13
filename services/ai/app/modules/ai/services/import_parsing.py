"""Parsing and formatting helpers for the AI menu-import flow: turns an uploaded file into an
Anthropic content block, and fetches the categories/printers context used to prompt the AI."""

import base64
import io
import zipfile

from defusedxml import ElementTree
from defusedxml import common as defused_common
from fastapi import HTTPException, status

from app.modules.ai.services.menu_client import MenuClient, PrintingClient

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
SUPPORTED_TEXT_TYPES = {"text/plain", "text/csv"}
DOCX_MIME_TYPES = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB
DOCX_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


async def fetch_menu_context(menu: MenuClient, printing: PrintingClient, location_id: str) -> tuple[str, str]:
    categories = await menu.list_categories(location_id)
    printers = await printing.list_printers(location_id)
    cat_names = ", ".join(c["name"] for c in categories) or "(none yet)"
    printer_list = ", ".join(f"{p['name']} ({p['type']})" for p in printers) or "(none yet)"
    return cat_names, printer_list


def extract_docx_text(content: bytes) -> str:
    """Pull plain text out of a .docx's word/document.xml — avoids a python-docx dependency."""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_bytes)
    lines = []
    for para in root.iter(f"{DOCX_WORD_NS}p"):
        line = "".join(node.text or "" for node in para.iter(f"{DOCX_WORD_NS}t"))
        lines.append(line)
    return "\n".join(lines)


def build_content_block(content: bytes, content_type: str, filename: str) -> dict:
    lower_name = filename.lower()
    if content_type in SUPPORTED_IMAGE_TYPES:
        media_type = "image/jpeg" if content_type == "image/jpg" else content_type
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(content).decode()},
        }
    if content_type == "application/pdf" or lower_name.endswith(".pdf"):
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(content).decode()},
        }
    if content_type in SUPPORTED_TEXT_TYPES or lower_name.endswith((".txt", ".csv")):
        text = content.decode("utf-8", errors="ignore")
        return {"type": "text", "text": f"Menu file ({filename}):\n\n{text}"}
    if content_type in DOCX_MIME_TYPES or lower_name.endswith(".docx"):
        try:
            text = extract_docx_text(content)
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, defused_common.DefusedXmlException) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read this .docx file"
            ) from exc
        return {"type": "text", "text": f"Menu file ({filename}):\n\n{text}"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Please upload an image (PNG/JPEG/WEBP), a PDF, a Word (.docx) file, or a text/CSV file.",
    )
