import json
import logging
import asyncio
from typing import List, Optional
from app.llm.provider import get_llm_provider, LLMProvider
from app.models.schemas import Provision, Chunk, LegalCategory, PartyRole, DocumentType
from prompts import PROVISION_IDENTIFICATION_SYSTEM_PROMPT, PROVISION_IDENTIFICATION_USER_PROMPT

logger = logging.getLogger(__name__)


class ProvisionIdentificationService:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()

    async def identify_provisions(
        self,
        chunks: List[Chunk],
        document_type: DocumentType,
    ) -> List[Provision]:
        if not chunks:
            return []

        chunks_by_page = {}
        for chunk in chunks:
            if chunk.page_number not in chunks_by_page:
                chunks_by_page[chunk.page_number] = []
            chunks_by_page[chunk.page_number].append(chunk)

        all_provisions = []

        for page_num in sorted(chunks_by_page.keys()):
            page_chunks = chunks_by_page[page_num]
            chunks_text = []

            for chunk in page_chunks:
                chunks_text.append(f"Chunk {chunk.id} (Page {chunk.page_number}, Section: {chunk.heading}):\n{chunk.text}\n")

            prompt = PROVISION_IDENTIFICATION_USER_PROMPT.format(
                document_type=document_type.value,
                chunks="\n".join(chunks_text),
            )

            schema = {
                "type": "object",
                "properties": {
                    "provisions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "subcategory": {"type": ["string", "null"]},
                                "provision_name": {"type": "string"},
                                "section_number": {"type": ["string", "null"]},
                                "heading": {"type": "string"},
                                "text": {"type": "string"},
                                "page_number": {"type": "integer"},
                                "party_mentioned": {"type": "array", "items": {"type": "string"}},
                                "keywords": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["category", "provision_name", "text", "page_number"],
                        },
                    }
                },
                "required": ["provisions"],
            }

            try:
                result = await self.llm.generate_structured(
                    prompt=prompt,
                    system_prompt=PROVISION_IDENTIFICATION_SYSTEM_PROMPT,
                    schema=schema,
                    temperature=0.1,
                    max_tokens=4096,
                )

                raw_provisions = result.get("provisions", [])
                for rp in raw_provisions:
                    try:
                        category_str = rp.get("category", "Indemnification")
                        try:
                            category = LegalCategory(category_str)
                        except ValueError:
                            category = LegalCategory.INDEMNIFICATION

                        party_mentioned = []
                        for p in rp.get("party_mentioned", []):
                            try:
                                party_mentioned.append(PartyRole(p))
                            except ValueError:
                                pass

                        provision = Provision(
                            document_id=chunks[0].document_id if chunks else "",
                            category=category,
                            subcategory=rp.get("subcategory"),
                            provision_name=rp.get("provision_name", ""),
                            heading=rp.get("heading", ""),
                            text=rp.get("text", ""),
                            page_number=rp.get("page_number", page_num),
                            char_start=0,
                            char_end=len(rp.get("text", "")),
                            party_mentioned=party_mentioned,
                            keywords=rp.get("keywords", []),
                        )
                        all_provisions.append(provision)
                    except Exception as e:
                        logger.warning(f"Failed to parse provision: {e}")
                        continue

            except Exception as e:
                logger.error(f"Provision identification failed for page {page_num}: {e}")


        # Deterministic recovery for high-value SPA provisions. LLMs occasionally
        # omit short sections or mislabel Survival because it sits in Article 3.
        # We recover only when the source text itself contains the signal.
        required = [
            ("survival", LegalCategory.REPRESENTATIONS_WARRANTIES, "Survival Period", "Survival Period"),
            ("material adverse effect", LegalCategory.MATERIAL_ADVERSE_EFFECT, "MAE Definition", "Material Adverse Effect Definition"),
            ("termination", LegalCategory.TERMINATION_RIGHTS, "Termination", "Termination Rights"),
            ("conditions to obligations of buyer", LegalCategory.CLOSING_CONDITIONS, "Closing Conditions", "Closing Conditions"),
        ]
        existing = {(p.category, p.provision_name.lower()) for p in all_provisions}
        for chunk in chunks:
            low = chunk.text.lower()
            for signal, category, subcategory, name in required:
                if signal not in low:
                    continue
                if signal == "survival" and "representation" not in low and "warrant" not in low:
                    continue
                if signal == "termination" and "terminate" not in low and "termination" not in low:
                    continue
                key = (category, name.lower())
                if key in existing:
                    continue
                start = chunk.char_start
                end = chunk.char_end
                party = []
                if "seller" in low: party.append(PartyRole.SELLER)
                if "buyer" in low: party.append(PartyRole.BUYER)
                if "target" in low: party.append(PartyRole.TARGET)
                all_provisions.append(Provision(
                    document_id=chunk.document_id,
                    category=category,
                    subcategory=subcategory,
                    provision_name=name,
                    section_id=chunk.section_id,
                    heading=chunk.heading,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    char_start=start,
                    char_end=end,
                    party_mentioned=party,
                    keywords=[signal, name.lower()],
                ))
                existing.add(key)

        # Stable ordering keeps downstream matching/reports deterministic.
        all_provisions.sort(key=lambda p: (p.page_number, p.char_start, p.provision_name))
        return all_provisions

    def identify_provisions_sync(
        self,
        chunks: List[Chunk],
        document_type: DocumentType,
    ) -> List[Provision]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.identify_provisions(chunks, document_type))
                return future.result()
        else:
            return asyncio.run(self.identify_provisions(chunks, document_type))