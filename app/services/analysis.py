import logging
import time
import uuid
from typing import List, Optional
from datetime import datetime
from app.models.schemas import (
    Document, Page, Section, Chunk, LegalPosition, ClassificationResult,
    AnalysisRun, AnalysisResult, DocumentType
)
from app.models.database import (
    DocumentDB, PageDB, SectionDB, ChunkDB, ProvisionDB, LegalPositionDB, AnalysisRunDB
)
from app.models.session import get_db
from app.classification.service import ClassificationService
from app.services.provision_identification import ProvisionIdentificationService
from app.extraction.service import ExtractionService
from app.evidence.service import EvidenceVerificationService
from app.retrieval.service import RetrievalService
from app.ingestion.parser import ingest_document
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self):
        self.classification = ClassificationService()
        self.provision_id = ProvisionIdentificationService()
        self.extraction = ExtractionService()
        self.verification = EvidenceVerificationService()
        self.retrieval = RetrievalService()
        self.settings = get_settings()

    def _run_async(self, coro):
        """Run async coroutine in sync context, handling existing event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # Running in existing event loop, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    def run_analysis(self, document_id: str, pdf_path: str, filename: str) -> AnalysisResult:
        start_time = time.time()
        run_id = str(uuid.uuid4())

        logger.info(f"Starting analysis run {run_id} for document {document_id}")

        with get_db() as db:
            run_db = AnalysisRunDB(
                id=run_id,
                model_id=self.settings.hf_model_id if self.settings.hf_api_key else "mock",
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(run_db)
            db.commit()

        try:
            doc, pages, sections, chunks = ingest_document(pdf_path, document_id, filename)

            with get_db() as db:
                # Check if document already exists
                existing_doc = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()
                if not existing_doc:
                    doc_db = DocumentDB(
                        id=doc.id,
                        filename=doc.filename,
                        content_type=doc.content_type,
                        size_bytes=doc.size_bytes,
                        page_count=doc.page_count,
                    )
                    db.add(doc_db)

                    for page in pages:
                        page_db = PageDB(
                            id=page.id,
                            document_id=document_id,
                            page_number=page.page_number,
                            text=page.text,
                            char_start=page.char_start,
                            char_end=page.char_end,
                        )
                        db.add(page_db)

                    for section in sections:
                        section_db = SectionDB(
                            id=section.id,
                            document_id=document_id,
                            page_number=section.page_number,
                            section_number=section.section_number,
                            heading=section.heading,
                            level=section.level,
                            char_start=section.char_start,
                            char_end=section.char_end,
                        )
                        db.add(section_db)

                    for chunk in chunks:
                        chunk_db = ChunkDB(
                            id=chunk.id,
                            document_id=document_id,
                            page_number=chunk.page_number,
                            section_id=chunk.section_id,
                            heading=chunk.heading,
                            text=chunk.text,
                            char_start=chunk.char_start,
                            char_end=chunk.char_end,
                            token_count=chunk.token_count,
                        )
                        db.add(chunk_db)

                    db.commit()
                else:
                    # Document exists, just update page_count and add pages/sections/chunks if needed
                    existing_doc.page_count = doc.page_count
                    db.commit()

            self.retrieval.index_chunks(chunks)

            classification = self.classification.classify_sync(doc.filename + "\n" + "\n".join(c.text for c in chunks[:5]))
            doc.document_type = classification.document_type

            with get_db() as db:
                doc_db = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()
                if doc_db:
                    doc_db.document_type = classification.document_type.value
                    doc_db.classification_confidence = classification.confidence
                    doc_db.classification_reason = classification.reason
                    doc_db.governing_entities = classification.governing_entities
                    doc_db.source_metadata = classification.source_metadata
                    db.commit()

            provisions = self.provision_id.identify_provisions_sync(chunks, classification.document_type)

            with get_db() as db:
                for prov in provisions:
                    prov_db = ProvisionDB(
                        id=prov.id,
                        document_id=document_id,
                        category=prov.category.value,
                        subcategory=prov.subcategory,
                        provision_name=prov.provision_name,
                        section_id=prov.section_id,
                        heading=prov.heading,
                        text=prov.text,
                        page_number=prov.page_number,
                        char_start=prov.char_start,
                        char_end=prov.char_end,
                        party_mentioned=[p.value for p in prov.party_mentioned],
                        keywords=prov.keywords,
                    )
                    db.add(prov_db)
                db.commit()

            positions = self.extraction.extract_positions_sync(provisions, document_id)
            positions = self.verification.verify_positions_sync(positions)

            with get_db() as db:
                verified = sum(1 for p in positions if p.status.value == "VERIFIED")
                unverified = sum(1 for p in positions if p.status.value != "VERIFIED")

                for pos in positions:
                    pos_db = LegalPositionDB(
                        id=pos.id if hasattr(pos, 'id') else str(uuid.uuid4()),
                        document_id=document_id,
                        run_id=run_id,
                        category=pos.category.value,
                        subcategory=pos.subcategory,
                        provision_name=pos.provision_name,
                        party=pos.party.value,
                        obligation_right=pos.obligation_right,
                        threshold=pos.threshold,
                        amount=pos.amount,
                        percentage=pos.percentage,
                        unit=pos.unit,
                        duration=pos.duration,
                        condition=pos.condition,
                        exception=pos.exception,
                        qualifier=pos.qualifier,
                        consequence=pos.consequence,
                        evidence_document_id=pos.evidence.document_id,
                        evidence_page=pos.evidence.page_number,
                        evidence_section_id=pos.evidence.section_id,
                        evidence_section_number=pos.evidence.section_number,
                        evidence_heading=pos.evidence.heading,
                        evidence_text=pos.evidence.text,
                        evidence_char_start=pos.evidence.char_start,
                        evidence_char_end=pos.evidence.char_end,
                        evidence_chunk_id=pos.evidence.chunk_id,
                        confidence=pos.confidence,
                        status=pos.status.value,
                        raw_extraction=pos.raw_extraction,
                    )
                    db.add(pos_db)

                run_db = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == run_id).first()
                if run_db:
                    run_db.documents_processed = 1
                    run_db.provisions_extracted = len(provisions)
                    run_db.verified_findings = verified
                    run_db.unverified_findings = unverified
                    run_db.errors = 0
                    run_db.status = "completed"
                    run_db.completed_at = datetime.utcnow()
                    run_db.document_ids = [document_id]
                    db.commit()

            processing_time = int((time.time() - start_time) * 1000)

            result = AnalysisResult(
                run_id=run_id,
                document_id=document_id,
                positions=positions,
                classification=classification,
                processing_time_ms=processing_time,
            )

            logger.info(f"Analysis run {run_id} completed: {len(positions)} positions extracted")
            return result

        except Exception as e:
            logger.error(f"Analysis run {run_id} failed: {e}")
            with get_db() as db:
                run_db = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == run_id).first()
                if run_db:
                    run_db.status = "failed"
                    run_db.errors = 1
                    run_db.error_details = [str(e)]
                    run_db.completed_at = datetime.utcnow()
                    db.commit()
            raise

    def get_run(self, run_id: str) -> Optional[AnalysisRun]:
        with get_db() as db:
            run_db = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == run_id).first()
            if not run_db:
                return None

            return AnalysisRun(
                id=run_db.id,
                model_id=run_db.model_id,
                documents_processed=run_db.documents_processed,
                provisions_extracted=run_db.provisions_extracted,
                verified_findings=run_db.verified_findings,
                unverified_findings=run_db.unverified_findings,
                errors=run_db.errors,
                status=run_db.status,
                started_at=run_db.started_at,
                completed_at=run_db.completed_at,
                document_ids=run_db.document_ids,
                error_details=run_db.error_details,
            )

    def get_findings(self, run_id: str) -> List[LegalPosition]:
        with get_db() as db:
            positions_db = db.query(LegalPositionDB).filter(LegalPositionDB.run_id == run_id).all()
            positions = []
            for p in positions_db:
                from app.models.schemas import Evidence
                evidence = Evidence(
                    document_id=p.evidence_document_id,
                    page_number=p.evidence_page,
                    section_id=p.evidence_section_id,
                    section_number=p.evidence_section_number,
                    heading=p.evidence_heading,
                    text=p.evidence_text,
                    char_start=p.evidence_char_start,
                    char_end=p.evidence_char_end,
                    chunk_id=p.evidence_chunk_id,
                )
                pos = LegalPosition(
                    id=p.id,
                    category=p.category,
                    subcategory=p.subcategory,
                    provision_name=p.provision_name,
                    party=p.party,
                    obligation_right=p.obligation_right,
                    threshold=p.threshold,
                    amount=p.amount,
                    percentage=p.percentage,
                    unit=p.unit,
                    duration=p.duration,
                    condition=p.condition or [],
                    exception=p.exception or [],
                    qualifier=p.qualifier or [],
                    consequence=p.consequence or [],
                    evidence=evidence,
                    confidence=p.confidence,
                    status=p.status,
                    raw_extraction=p.raw_extraction,
                )
                positions.append(pos)
            return positions

    def get_document(self, document_id: str) -> Optional[Document]:
        with get_db() as db:
            doc_db = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()
            if not doc_db:
                return None
            return Document(
                id=doc_db.id,
                filename=doc_db.filename,
                content_type=doc_db.content_type,
                size_bytes=doc_db.size_bytes,
                document_type=DocumentType(doc_db.document_type),
                classification_confidence=doc_db.classification_confidence,
                classification_reason=doc_db.classification_reason,
                governing_entities=doc_db.governing_entities or [],
                source_metadata=doc_db.source_metadata or {},
                page_count=doc_db.page_count,
                created_at=doc_db.created_at,
                updated_at=doc_db.updated_at,
            )