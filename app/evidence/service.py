import json
import logging
import asyncio
from typing import List, Dict, Any
from app.llm.provider import get_llm_provider, LLMProvider
from app.models.schemas import LegalPosition, ExtractionStatus
from prompts import EVIDENCE_VERIFICATION_SYSTEM_PROMPT, EVIDENCE_VERIFICATION_USER_PROMPT

logger = logging.getLogger(__name__)


class EvidenceVerificationService:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()

    async def verify_positions(self, positions: List[LegalPosition]) -> List[LegalPosition]:
        if not positions:
            return positions

        positions_text = []
        for i, pos in enumerate(positions):
            positions_text.append(f"--- Position {i} ---\n"
                                  f"Category: {pos.category.value}\n"
                                  f"Provision: {pos.provision_name}\n"
                                  f"Party: {pos.party.value}\n"
                                  f"Percentage: {pos.percentage}\n"
                                  f"Unit: {pos.unit}\n"
                                  f"Qualifiers: {pos.qualifier}\n"
                                  f"Consequences: {pos.consequence}\n"
                                  f"Evidence Text: {pos.evidence.text}\n"
                                  f"Evidence Page: {pos.evidence.page_number}\n"
                                  f"Evidence Section: {pos.evidence.section_number or 'N/A'}\n")

        prompt = EVIDENCE_VERIFICATION_USER_PROMPT.format(positions="\n".join(positions_text))

        schema = {
            "type": "object",
            "properties": {
                "verifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "position_index": {"type": "integer"},
                            "status": {"type": "string", "enum": ["VERIFIED", "PARTIAL", "UNVERIFIED", "FAILED"]},
                            "field_verifications": {"type": "object"},
                            "discrepancies": {"type": "array", "items": {"type": "string"}},
                            "notes": {"type": "string"},
                        },
                        "required": ["position_index", "status", "field_verifications", "discrepancies", "notes"],
                    },
                }
            },
            "required": ["verifications"],
        }

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=EVIDENCE_VERIFICATION_SYSTEM_PROMPT,
                schema=schema,
                temperature=0.1,
                max_tokens=2048,
            )

            verifications = result.get("verifications", [])
            verified_positions = []

            for i, pos in enumerate(positions):
                verification = next((v for v in verifications if v.get("position_index") == i), None)

                if verification:
                    new_status_str = verification.get("status", "UNVERIFIED")
                    try:
                        new_status = ExtractionStatus(new_status_str)
                    except ValueError:
                        new_status = ExtractionStatus.UNVERIFIED

                    discrepancies = verification.get("discrepancies", [])
                    if discrepancies:
                        logger.warning(f"Position {i} discrepancies: {discrepancies}")

                    pos.status = new_status
                    pos.raw_extraction = pos.raw_extraction or {}
                    pos.raw_extraction["verification"] = verification

                verified_positions.append(pos)

            return verified_positions

        except Exception as e:
            logger.error(f"Evidence verification failed: {e}")
            for pos in positions:
                pos.status = ExtractionStatus.UNVERIFIED
            return positions

    def verify_positions_sync(self, positions: List[LegalPosition]) -> List[LegalPosition]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.verify_positions(positions))
                return future.result()
        else:
            return asyncio.run(self.verify_positions(positions))