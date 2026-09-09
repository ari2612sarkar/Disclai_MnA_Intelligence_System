import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from app.llm.provider import get_llm_provider, LLMProvider
from app.models.schemas import (
    LegalPosition, Provision, Evidence, LegalCategory, PartyRole, ExtractionStatus
)
from prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from app.core.config import get_settings

logger = logging.getLogger(__name__)

def _normalize_position(raw: Dict[str, Any], provision: Provision) -> Dict[str, Any]:
    """Deterministically normalize high-value SPA provisions after LLM extraction.
    This does not invent legal substance; it only aligns labels with the supplied
    provision/text and preserves the model's extracted values.
    """
    out = dict(raw)
    text = " ".join([
        str(provision.provision_name or ""),
        str(provision.heading or ""),
        str(provision.text or ""),
        str(out.get("provision_name") or ""),
        str(out.get("evidence", {}).get("text") or ""),
    ]).lower()

    if "survival" in text and ("representation" in text or "warrant" in text):
        out["category"] = LegalCategory.REPRESENTATIONS_WARRANTIES.value
        out["subcategory"] = "Survival Period"
        out["provision_name"] = "Survival Period"
        if out.get("party") in (None, "", "Unknown"):
            if re.search(r"\b(?:of|by)\s+seller\b", text):
                out["party"] = "Seller"

    elif "material adverse effect" in text or re.search(r"\bmae\b", text):
        out["category"] = LegalCategory.MATERIAL_ADVERSE_EFFECT.value
        out["subcategory"] = "MAE Definition"
        out["provision_name"] = "Material Adverse Effect Definition"

    elif "termination" in text and ("terminate" in text or "termination rights" in text):
        out["category"] = LegalCategory.TERMINATION_RIGHTS.value
        out["subcategory"] = "Termination"
        out["provision_name"] = "Termination Rights"

    elif ("conditions to obligations of buyer" in text or
          "condition precedent" in text or
          ("closing" in text and "subject to the satisfaction" in text)):
        out["category"] = LegalCategory.CLOSING_CONDITIONS.value
        out["subcategory"] = "Closing Conditions"
        out["provision_name"] = "Closing Conditions"
        if out.get("party") in (None, "", "Unknown"):
            if "obligation of buyer" in text:
                out["party"] = "Buyer"

    # Evidence location is allowed to be unavailable from an LLM. Preserve the
    # exact text/page and use safe sentinel offsets rather than rejecting a finding.
    ev = dict(out.get("evidence") or {})
    ev["document_id"] = ev.get("document_id") or provision.document_id or ""
    ev["page_number"] = ev.get("page_number") or provision.page_number
    ev["heading"] = ev.get("heading") or provision.heading or ""
    ev["text"] = ev.get("text") or provision.text or ""
    ev["char_start"] = ev.get("char_start") or provision.char_start or 0
    ev["char_end"] = ev.get("char_end") or provision.char_end or len(ev["text"])
    out["evidence"] = ev
    return out


class ExtractionService:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    async def extract_positions(
        self,
        provisions: List[Provision],
        document_id: str,
    ) -> List[LegalPosition]:
        if not provisions:
            return []

        provisions_text = []
        for i, prov in enumerate(provisions):
            provisions_text.append(f"--- Provision {i} ---\n"
                                   f"Category: {prov.category.value}\n"
                                   f"Subcategory: {prov.subcategory or 'N/A'}\n"
                                   f"Provision: {prov.provision_name}\n"
                                   f"Section: {prov.section_id or 'N/A'}\n"
                                   f"Heading: {prov.heading}\n"
                                   f"Page: {prov.page_number}\n"
                                   f"Text: {prov.text}\n")

        prompt = EXTRACTION_USER_PROMPT.format(provisions="\n".join(provisions_text))

        schema = {
            "type": "object",
            "properties": {
                "positions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "subcategory": {"type": ["string", "null"]},
                            "provision_name": {"type": "string"},
                            "party": {"type": "string"},
                            "obligation_right": {"type": "string"},
                            "threshold": {"type": ["string", "null"]},
                            "amount": {"type": ["number", "null"]},
                            "percentage": {"type": ["number", "null"]},
                            "unit": {"type": ["string", "null"]},
                            "duration": {"type": ["string", "null"]},
                            "condition": {"type": "array", "items": {"type": "string"}},
                            "exception": {"type": "array", "items": {"type": "string"}},
                            "qualifier": {"type": "array", "items": {"type": "string"}},
                            "consequence": {"type": "array", "items": {"type": "string"}},
                            "evidence": {
                                "type": "object",
                                "properties": {
                                    "document_id": {"type": "string"},
                                    "page_number": {"type": "integer"},
                                    "section_number": {"type": ["string", "null"]},
                                    "heading": {"type": "string"},
                                    "text": {"type": "string"},
                                    "char_start": {"type": ["integer", "null"]},
                                    "char_end": {"type": ["integer", "null"]},
                                },
                                "required": ["document_id", "page_number", "heading", "text", "char_start", "char_end"],
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "status": {"type": "string", "enum": ["VERIFIED", "UNVERIFIED", "PARTIAL", "FAILED"]},
                        },
                        "required": ["category", "provision_name", "party", "evidence", "confidence", "status"],
                    },
                }
            },
            "required": ["positions"],
        }

        positions = []
        for attempt in range(self.settings.extraction_max_retries):
            try:
                result = await self.llm.generate_structured(
                    prompt=prompt,
                    system_prompt=EXTRACTION_SYSTEM_PROMPT,
                    schema=schema,
                    temperature=self.settings.extraction_temperature,
                    max_tokens=4096,
                )

                raw_positions = result.get("positions", [])
                for rp in raw_positions:
                    try:
                        evidence_data = rp.get("evidence", {})
                        evidence = Evidence(
                            document_id=evidence_data.get("document_id", document_id),
                            page_number=evidence_data.get("page_number", 1),
                            section_number=evidence_data.get("section_number"),
                            heading=evidence_data.get("heading", ""),
                            text=evidence_data.get("text", ""),
                            char_start=evidence_data.get("char_start") or 0,
                            char_end=evidence_data.get("char_end") or 0,
                        )

                        party_str = rp.get("party", "Unknown")
                        try:
                            party = PartyRole(party_str)
                        except ValueError:
                            party = PartyRole.UNKNOWN

                        category_str = rp.get("category", "Indemnification")
                        try:
                            category = LegalCategory(category_str)
                        except ValueError:
                            category = LegalCategory.INDEMNIFICATION

                        status_str = rp.get("status", "UNVERIFIED")
                        try:
                            status = ExtractionStatus(status_str)
                        except ValueError:
                            status = ExtractionStatus.UNVERIFIED

                        position = LegalPosition(
                            category=category,
                            subcategory=rp.get("subcategory"),
                            provision_name=rp.get("provision_name", ""),
                            party=party,
                            obligation_right=rp.get("obligation_right", ""),
                            threshold=rp.get("threshold"),
                            amount=rp.get("amount"),
                            percentage=rp.get("percentage"),
                            unit=rp.get("unit"),
                            duration=rp.get("duration"),
                            condition=rp.get("condition", []),
                            exception=rp.get("exception", []),
                            qualifier=rp.get("qualifier", []),
                            consequence=rp.get("consequence", []),
                            evidence=evidence,
                            confidence=float(rp.get("confidence", 0.0)),
                            status=status,
                            raw_extraction=rp,
                        )
                        positions.append(position)
                    except Exception as e:
                        logger.warning(f"Failed to parse position: {e}")
                        continue

                if positions:
                    break

            except Exception as e:
                logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
                if attempt == self.settings.extraction_max_retries - 1:
                    logger.error(f"All extraction attempts failed: {e}")

        return positions

    def extract_positions_sync(
        self,
        provisions: List[Provision],
        document_id: str,
    ) -> List[LegalPosition]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.extract_positions(provisions, document_id))
                return future.result()
        else:
            return asyncio.run(self.extract_positions(provisions, document_id))