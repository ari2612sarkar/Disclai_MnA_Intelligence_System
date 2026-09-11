import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from app.llm.provider import get_llm_provider, LLMProvider
from app.models.schemas import (
    LegalPosition, LegalPositionMatch, MatchStatus, LegalCategory, PartyRole
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class MatchCandidate:
    position: LegalPosition
    score: float
    reason: str


class ProvisionMatcher:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    def match_positions(
        self,
        positions_a: List[LegalPosition],
        positions_b: List[LegalPosition],
    ) -> List[LegalPositionMatch]:
        matches = []
        matched_b_indices = set()

        for pos_a in positions_a:
            best_match = self._find_best_match(pos_a, positions_b, matched_b_indices)

            if best_match:
                matched_b_indices.add(best_match.position_idx)
                match = LegalPositionMatch(
                    company_a_position=pos_a,
                    company_b_position=best_match.position,
                    match_status=best_match.match_status,
                    match_confidence=best_match.confidence,
                    match_reason=best_match.reason,
                    matched_attributes=best_match.matched_attributes,
                )
            else:
                match = LegalPositionMatch(
                    company_a_position=pos_a,
                    company_b_position=None,
                    match_status=MatchStatus.UNMATCHED,
                    match_confidence=0.0,
                    match_reason="No equivalent provision found in Company B documents",
                    matched_attributes=[],
                )

            matches.append(match)

        for idx, pos_b in enumerate(positions_b):
            if idx not in matched_b_indices:
                match = LegalPositionMatch(
                    company_a_position=None,
                    company_b_position=pos_b,
                    match_status=MatchStatus.UNMATCHED,
                    match_confidence=0.0,
                    match_reason="No equivalent provision found in Company A documents",
                    matched_attributes=[],
                )
                matches.append(match)

        return matches

    def _find_best_match(
        self,
        pos_a: LegalPosition,
        positions_b: List[LegalPosition],
        matched_indices: set,
    ) -> Optional[MatchCandidate]:
        best_candidate = None
        best_score = 0.0

        for idx, pos_b in enumerate(positions_b):
            if idx in matched_indices:
                continue

            score, reason, attrs = self._compute_match_score(pos_a, pos_b)

            if score > best_score:
                best_score = score
                match_status = self._determine_match_status(score)
                best_candidate = MatchCandidate(
                    position=pos_b,
                    score=score,
                    reason=reason,
                )
                best_candidate.match_status = match_status
                best_candidate.confidence = score
                best_candidate.matched_attributes = attrs
                best_candidate.position_idx = idx

        return best_candidate

    def _compute_match_score(
        self,
        pos_a: LegalPosition,
        pos_b: LegalPosition,
    ) -> Tuple[float, str, List[str]]:
        score = 0.0
        matched_attrs = []
        reasons = []

        if pos_a.category == pos_b.category:
            score += 0.3
            matched_attrs.append("category")
            reasons.append(f"Same category: {pos_a.category.value}")

        if pos_a.subcategory and pos_b.subcategory and pos_a.subcategory.lower() == pos_b.subcategory.lower():
            score += 0.2
            matched_attrs.append("subcategory")
            reasons.append(f"Same subcategory: {pos_a.subcategory}")

        if pos_a.provision_name.lower() == pos_b.provision_name.lower():
            score += 0.2
            matched_attrs.append("provision_name")
            reasons.append(f"Same provision name: {pos_a.provision_name}")

        name_similarity = self._compute_name_similarity(pos_a.provision_name, pos_b.provision_name)
        if name_similarity > 0.7:
            score += 0.15 * name_similarity
            matched_attrs.append("provision_name_similar")
            reasons.append(f"Similar provision names (similarity: {name_similarity:.2f})")

        if pos_a.party == pos_b.party:
            score += 0.1
            matched_attrs.append("party")
            reasons.append(f"Same party: {pos_a.party.value}")

        if pos_a.unit and pos_b.unit and pos_a.unit.lower() == pos_b.unit.lower():
            score += 0.05
            matched_attrs.append("unit")
            reasons.append(f"Same unit: {pos_a.unit}")

        if pos_a.duration and pos_b.duration and pos_a.duration.lower() == pos_b.duration.lower():
            score += 0.05
            matched_attrs.append("duration")
            reasons.append(f"Same duration: {pos_a.duration}")

        return score, "; ".join(reasons), matched_attrs

    def _compute_name_similarity(self, name_a: str, name_b: str) -> float:
        a_words = set(name_a.lower().split())
        b_words = set(name_b.lower().split())

        if not a_words or not b_words:
            return 0.0

        intersection = a_words & b_words
        union = a_words | b_words

        return len(intersection) / len(union) if union else 0.0

    def _determine_match_status(self, score: float) -> MatchStatus:
        if score >= 0.7:
            return MatchStatus.MATCHED
        elif score >= 0.4:
            return MatchStatus.PARTIAL
        elif score >= 0.2:
            return MatchStatus.REQUIRES_REVIEW
        else:
            return MatchStatus.UNMATCHED

    async def match_positions_with_llm(
        self,
        positions_a: List[LegalPosition],
        positions_b: List[LegalPosition],
    ) -> List[LegalPositionMatch]:
        deterministic_matches = self.match_positions(positions_a, positions_b)

        uncertain_matches = [
            m for m in deterministic_matches
            if m.match_status in [MatchStatus.PARTIAL, MatchStatus.REQUIRES_REVIEW]
        ]

        if not uncertain_matches:
            return deterministic_matches

        for match in uncertain_matches:
            if match.company_a_position and match.company_b_position:
                llm_match = await self._llm_semantic_match(
                    match.company_a_position,
                    match.company_b_position,
                )
                if llm_match:
                    match.match_status = llm_match.match_status
                    match.match_confidence = llm_match.match_confidence
                    match.match_reason = llm_match.match_reason
                    match.matched_attributes = llm_match.matched_attributes

        return deterministic_matches

    async def _llm_semantic_match(
        self,
        pos_a: LegalPosition,
        pos_b: LegalPosition,
    ) -> Optional[LegalPositionMatch]:
        prompt = f"""Compare these two legal positions and determine if they represent the same legal concept.

Position A:
- Category: {pos_a.category.value}
- Subcategory: {pos_a.subcategory or 'N/A'}
- Provision: {pos_a.provision_name}
- Party: {pos_a.party.value}
- Percentage: {pos_a.percentage}
- Unit: {pos_a.unit or 'N/A'}
- Duration: {pos_a.duration or 'N/A'}
- Qualifiers: {pos_a.qualifier}
- Exceptions: {pos_a.exception}
- Evidence: {pos_a.evidence.text[:500]}

Position B:
- Category: {pos_b.category.value}
- Subcategory: {pos_b.subcategory or 'N/A'}
- Provision: {pos_b.provision_name}
- Party: {pos_b.party.value}
- Percentage: {pos_b.percentage}
- Unit: {pos_b.unit or 'N/A'}
- Duration: {pos_b.duration or 'N/A'}
- Qualifiers: {pos_b.qualifier}
- Exceptions: {pos_b.exception}
- Evidence: {pos_b.evidence.text[:500]}

Respond with JSON:
{{
    "match_status": "MATCHED|PARTIAL|UNMATCHED|REQUIRES_REVIEW",
    "confidence": 0.0-1.0,
    "reason": "explanation",
    "matched_attributes": ["attribute1", "attribute2"]
}}"""

        schema = {
            "type": "object",
            "properties": {
                "match_status": {"type": "string", "enum": ["MATCHED", "PARTIAL", "UNMATCHED", "REQUIRES_REVIEW"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reason": {"type": "string"},
                "matched_attributes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["match_status", "confidence", "reason", "matched_attributes"],
        }

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt="You are a legal expert comparing M&A contract provisions. Determine if two provisions represent the same legal concept.",
                schema=schema,
                temperature=0.1,
                max_tokens=1024,
            )

            return LegalPositionMatch(
                company_a_position=pos_a,
                company_b_position=pos_b,
                match_status=MatchStatus(result["match_status"]),
                match_confidence=result["confidence"],
                match_reason=result["reason"],
                matched_attributes=result["matched_attributes"],
            )
        except Exception as e:
            logger.warning(f"LLM semantic matching failed: {e}")
            return None