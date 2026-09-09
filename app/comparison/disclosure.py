import logging
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    DisclosureIssue, LegalPosition, Evidence, LegalCategory, CompanyRole, Priority
)
from app.llm.provider import get_llm_provider, LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DisclosureReconciliationService:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    def reconcile_disclosures(
        self,
        spa_positions: List[LegalPosition],
        disclosure_schedule_positions: List[LegalPosition],
        data_room_positions: List[LegalPosition],
        comparison_id: str,
    ) -> List[DisclosureIssue]:
        issues = []

        rw_positions = [p for p in spa_positions if p.category == LegalCategory.REPRESENTATIONS_WARRANTIES]
        disc_exceptions = [p for p in spa_positions if p.category == LegalCategory.DISCLOSURE_EXCEPTIONS]

        for rw_pos in rw_positions:
            issue = self._check_representation_disclosure(rw_pos, disclosure_schedule_positions, data_room_positions, comparison_id)
            if issue:
                issues.append(issue)

        for exc_pos in disc_exceptions:
            issue = self._check_exception_disclosure(exc_pos, disclosure_schedule_positions, data_room_positions, comparison_id)
            if issue:
                issues.append(issue)

        issues.extend(self._check_missing_disclosures(spa_positions, disclosure_schedule_positions, data_room_positions, comparison_id))

        return issues

    def _check_representation_disclosure(
        self,
        rw_position: LegalPosition,
        disc_positions: List[LegalPosition],
        data_room_positions: List[LegalPosition],
        comparison_id: str,
    ) -> Optional[DisclosureIssue]:
        rw_text = rw_position.evidence.text.lower()
        rw_provision = rw_position.provision_name.lower()

        keywords = self._extract_keywords(rw_text, rw_provision)

        disc_evidence = self._find_matching_disclosure(keywords, disc_positions)
        data_evidence = self._find_matching_data_room(keywords, data_room_positions)

        if not disc_evidence and data_evidence:
            return DisclosureIssue(
                comparison_id=comparison_id,
                issue_type="POTENTIAL_MISSING_DISCLOSURE",
                description=f"SPA representation '{rw_position.provision_name}' references matters found in data room but not in disclosure schedule",
                spa_requirement=rw_position,
                disclosure_schedule_evidence=None,
                data_room_evidence=data_evidence,
                severity=Priority.HIGH,
                confidence=0.7,
                status="POTENTIAL_MISSING_DISCLOSURE",
            )

        if disc_evidence and data_evidence:
            if self._is_inconsistent(disc_evidence, data_evidence):
                return DisclosureIssue(
                    comparison_id=comparison_id,
                    issue_type="INCONSISTENT_DISCLOSURE",
                    description=f"Disclosure schedule and data room contain inconsistent information for '{rw_position.provision_name}'",
                    spa_requirement=rw_position,
                    disclosure_schedule_evidence=disc_evidence,
                    data_room_evidence=data_evidence,
                    severity=Priority.MEDIUM,
                    confidence=0.6,
                    status="INCONSISTENT_DISCLOSURE",
                )

        return None

    def _check_exception_disclosure(
        self,
        exc_position: LegalPosition,
        disc_positions: List[LegalPosition],
        data_room_positions: List[LegalPosition],
        comparison_id: str,
    ) -> Optional[DisclosureIssue]:
        exc_text = exc_position.evidence.text.lower()
        keywords = self._extract_keywords(exc_text, exc_position.provision_name.lower())

        disc_evidence = self._find_matching_disclosure(keywords, disc_positions)
        data_evidence = self._find_matching_data_room(keywords, data_room_positions)

        if data_evidence and not disc_evidence:
            return DisclosureIssue(
                comparison_id=comparison_id,
                issue_type="POTENTIAL_MISSING_EXCEPTION_DISCLOSURE",
                description=f"Exception carve-out '{exc_position.provision_name}' references matters in data room not disclosed",
                spa_requirement=exc_position,
                disclosure_schedule_evidence=None,
                data_room_evidence=data_evidence,
                severity=Priority.HIGH,
                confidence=0.7,
                status="POTENTIAL_MISSING_DISCLOSURE",
            )

        return None

    def _check_missing_disclosures(
        self,
        spa_positions: List[LegalPosition],
        disc_positions: List[LegalPosition],
        data_room_positions: List[LegalPosition],
        comparison_id: str,
    ) -> List[DisclosureIssue]:
        issues = []

        litigations = [p for p in data_room_positions if p.category == LegalCategory.LITIGATION]
        material_contracts = [p for p in data_room_positions if p.category == LegalCategory.MATERIAL_CONTRACTS]

        for lit in litigations:
            if not self._has_corresponding_disclosure(lit, disc_positions):
                issues.append(DisclosureIssue(
                    comparison_id=comparison_id,
                    issue_type="POTENTIAL_MISSING_LITIGATION_DISCLOSURE",
                    description=f"Litigation matter in data room ({lit.provision_name}) not found in disclosure schedule",
                    spa_requirement=None,
                    disclosure_schedule_evidence=None,
                    data_room_evidence=lit.evidence,
                    severity=Priority.HIGH,
                    confidence=0.75,
                    status="POTENTIAL_MISSING_DISCLOSURE",
                ))

        for contract in material_contracts:
            if not self._has_corresponding_disclosure(contract, disc_positions):
                issues.append(DisclosureIssue(
                    comparison_id=comparison_id,
                    issue_type="POTENTIAL_MISSING_CONTRACT_DISCLOSURE",
                    description=f"Material contract in data room ({contract.provision_name}) not found in disclosure schedule",
                    spa_requirement=None,
                    disclosure_schedule_evidence=None,
                    data_room_evidence=contract.evidence,
                    severity=Priority.MEDIUM,
                    confidence=0.65,
                    status="POTENTIAL_MISSING_DISCLOSURE",
                ))

        return issues

    def _extract_keywords(self, text: str, provision: str) -> List[str]:
        keywords = set()

        for word in provision.split():
            if len(word) > 3:
                keywords.add(word.lower())

        legal_terms = [
            "litigation", "lawsuit", "claim", "dispute", "arbitration", "mediation",
            "contract", "agreement", "license", "lease", "employment", "ip", "patent",
            "trademark", "copyright", "trade secret", "confidential", "material",
            "adverse", "effect", "change", "breach", "default", "termination",
            "indemnif", "liability", "damage", "loss", "penalty", "fine",
            "regulatory", "compliance", "permit", "license", "approval",
            "employee", "benefit", "pension", "compensation", "bonus",
            "intellectual property", "infringement", "violation",
        ]

        for term in legal_terms:
            if term in text:
                keywords.add(term)

        return list(keywords)

    def _find_matching_disclosure(self, keywords: List[str], disc_positions: List[LegalPosition]) -> Optional[Evidence]:
        for pos in disc_positions:
            text = pos.evidence.text.lower()
            matches = sum(1 for kw in keywords if kw in text)
            if matches >= 2 or (matches >= 1 and len(keywords) <= 3):
                return pos.evidence
        return None

    def _find_matching_data_room(self, keywords: List[str], data_positions: List[LegalPosition]) -> Optional[Evidence]:
        for pos in data_positions:
            text = pos.evidence.text.lower()
            matches = sum(1 for kw in keywords if kw in text)
            if matches >= 2 or (matches >= 1 and len(keywords) <= 3):
                return pos.evidence
        return None

    def _is_inconsistent(self, disc_evidence: Evidence, data_evidence: Evidence) -> bool:
        disc_text = disc_evidence.text.lower()
        data_text = data_evidence.text.lower()

        disc_parties = set(self._extract_parties(disc_text))
        data_parties = set(self._extract_parties(data_text))

        if disc_parties and data_parties and disc_parties != data_parties:
            return True

        disc_amounts = self._extract_amounts(disc_text)
        data_amounts = self._extract_amounts(data_text)

        if disc_amounts and data_amounts and disc_amounts != data_amounts:
            return True

        return False

    def _extract_parties(self, text: str) -> List[str]:
        import re
        parties = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|LLC|Corp|Corporation|Ltd|Limited))?)\b', text)
        return [p for p in parties if len(p) > 3]

    def _extract_amounts(self, text: str) -> List[str]:
        import re
        amounts = re.findall(r'\$[\d,]+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:million|billion|thousand|M|B|K)', text, re.IGNORECASE)
        return amounts

    def _has_corresponding_disclosure(self, data_position: LegalPosition, disc_positions: List[LegalPosition]) -> bool:
        keywords = self._extract_keywords(data_position.evidence.text, data_position.provision_name)
        return self._find_matching_disclosure(keywords, disc_positions) is not None

    async def reconcile_with_llm(
        self,
        spa_positions: List[LegalPosition],
        disclosure_schedule_positions: List[LegalPosition],
        data_room_positions: List[LegalPosition],
        comparison_id: str,
    ) -> List[DisclosureIssue]:
        det_issues = self.reconcile_disclosures(spa_positions, disclosure_schedule_positions, data_room_positions, comparison_id)

        if not det_issues:
            return []

        return det_issues