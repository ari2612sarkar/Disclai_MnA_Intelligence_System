import fitz
import re
import logging
import os
import uuid
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from app.models.schemas import Document, Page, Section, Chunk
from app.core.config import get_settings

logger = logging.getLogger(__name__)

HEADING_PATTERNS = [
    r"^\s*(\d+(?:\.\d+)+)\s+(.+)$",          
    r"^\s*([A-Z][A-Z\s]{2,})\s*$",          
    r"^\s*(Article|Section|Clause)\s+(\d+[A-Z]?)\s*[:\-]?\s*(.+)?$",  
    r"^\s*(\d+)\.\s+([A-Z][^.]{5,})\s*$",   
    r"^\s*\(([a-z])\)\s+(.+)$",             
    r"^\s*\((\d+)\)\s+(.+)$",               
]


@dataclass
class ParsedPage:
    page_number: int
    text: str
    char_start: int
    char_end: int
    blocks: List[dict]


@dataclass
class ParsedSection:
    id: str
    section_number: Optional[str]
    heading: str
    level: int
    page_number: int
    char_start: int
    char_end: int


def extract_pdf_pages(pdf_path: str) -> List[ParsedPage]:
    doc = fitz.open(pdf_path)
    pages = []
    global_char_offset = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        blocks = page.get_text("dict")["blocks"]

        page_text = text.strip()
        char_start = global_char_offset
        char_end = global_char_offset + len(page_text)
        global_char_offset = char_end + 1

        pages.append(ParsedPage(
            page_number=page_num + 1,
            text=page_text,
            char_start=char_start,
            char_end=char_end,
            blocks=blocks,
        ))

    doc.close()
    return pages


def detect_sections(pages: List[ParsedPage]) -> List[ParsedSection]:
    sections = []
    current_section = None

    for page in pages:
        lines = page.text.split("\n")
        line_char_offset = page.char_start

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                line_char_offset += len(line) + 1
                continue

            matched = False
            for pattern in HEADING_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        section_number = groups[0]
                        heading = groups[1] if len(groups) > 1 else line_stripped
                    else:
                        section_number = None
                        heading = groups[0] if groups else line_stripped

                    level = section_number.count(".") + 1 if section_number else 1

                    if current_section:
                        current_section.char_end = line_char_offset - 1
                        sections.append(current_section)

                    current_section = ParsedSection(
                        id=str(uuid.uuid4()),
                        section_number=section_number,
                        heading=heading.strip(),
                        level=level,
                        page_number=page.page_number,
                        char_start=line_char_offset,
                        char_end=page.char_end,
                    )
                    matched = True
                    break

            line_char_offset += len(line) + 1

            if not matched and current_section:
                current_section.char_end = line_char_offset - 1

    if current_section:
        current_section.char_end = pages[-1].char_end if pages else current_section.char_start
        sections.append(current_section)

    return sections


def assign_sections_to_pages(pages: List[ParsedPage], sections: List[ParsedSection]) -> List[Page]:
    page_objects = []
    for page in pages:
        page_sections = [s for s in sections if s.page_number == page.page_number]
        page_obj = Page(
            document_id="",
            page_number=page.page_number,
            text=page.text,
            char_start=page.char_start,
            char_end=page.char_end,
        )
        page_objects.append(page_obj)
    return page_objects


def chunk_text_semantic(
    text: str,
    page_number: int,
    section: Optional[ParsedSection],
    document_id: str,
    max_tokens: int = 512,
    overlap: int = 50,
) -> List[Chunk]:
    chunks = []
    paragraphs = re.split(r"\n\s*\n", text)
    current_chunk = ""
    current_start = 0
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_tokens = len(para.split()) * 1.3

        if len(current_chunk.split()) * 1.3 + para_tokens > max_tokens and current_chunk:
            chunk = Chunk(
                document_id=document_id,
                page_number=page_number,
                section_id=section.id if section else None,
                heading=section.heading if section else "",
                text=current_chunk.strip(),
                char_start=current_start,
                char_end=current_start + len(current_chunk),
                token_count=int(len(current_chunk.split()) * 1.3),
            )
            chunks.append(chunk)

            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + para
            current_start = current_start + len(current_chunk) - len(overlap_text) - len(para) - 2
            chunk_index += 1
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
                current_start = section.char_start if section else 0

    if current_chunk.strip():
        chunk = Chunk(
            document_id=document_id,
            page_number=page_number,
            section_id=section.id if section else None,
            heading=section.heading if section else "",
            text=current_chunk.strip(),
            char_start=current_start,
            char_end=current_start + len(current_chunk),
            token_count=int(len(current_chunk.split()) * 1.3),
        )
        chunks.append(chunk)

    return chunks


def ingest_document(pdf_path: str, document_id: str, filename: str) -> Tuple[Document, List[Page], List[Section], List[Chunk]]:
    logger.info(f"Ingesting document: {filename}")

    pages = extract_pdf_pages(pdf_path)
    sections = detect_sections(pages)
    file_size = os.path.getsize(pdf_path)

    doc = Document(
        id=document_id,
        filename=filename,
        size_bytes=file_size,
        page_count=len(pages),
    )

    page_objects = []
    section_objects = []
    chunk_objects = []

    global_char = 0
    for page in pages:
        page_obj = Page(
            document_id=document_id,
            page_number=page.page_number,
            text=page.text,
            char_start=page.char_start,
            char_end=page.char_end,
        )
        page_objects.append(page_obj)

    for section in sections:
        section_obj = Section(
            document_id=document_id,
            page_number=section.page_number,
            section_number=section.section_number,
            heading=section.heading,
            level=section.level,
            char_start=section.char_start,
            char_end=section.char_end,
        )
        section_objects.append(section_obj)

    for page in pages:
        page_sections = [s for s in sections if s.page_number == page.page_number]
        page_sections.sort(key=lambda x: x.char_start)

        if not page_sections:
            chunks = chunk_text_semantic(
                page.text, page.page_number, None, document_id,
                max_tokens=get_settings().chunk_max_tokens,
                overlap=get_settings().chunk_overlap_tokens,
            )
            chunk_objects.extend(chunks)
        else:
            for i, section in enumerate(page_sections):
                next_start = page_sections[i + 1].char_start if i + 1 < len(page_sections) else page.char_end
                section_text_start = max(section.char_start, page.char_start)
                section_text_end = min(next_start, page.char_end)

                if section_text_end > section_text_start:
                    section_text = page.text[section_text_start - page.char_start:section_text_end - page.char_start]
                    chunks = chunk_text_semantic(
                        section_text, page.page_number, section, document_id,
                        max_tokens=get_settings().chunk_max_tokens,
                        overlap=get_settings().chunk_overlap_tokens,
                    )
                    chunk_objects.extend(chunks)

    logger.info(f"Document ingested: {len(page_objects)} pages, {len(section_objects)} sections, {len(chunk_objects)} chunks")
    return doc, page_objects, section_objects, chunk_objects