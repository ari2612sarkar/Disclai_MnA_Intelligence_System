import logging
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter
from app.models.schemas import (
    DealVerdict, ComparisonFinding, CrossDocumentRisk, DisclosureIssue,
    PartySpecificRecommendation, CompanyRole, Priority, LegalCategory,
    RecommendationSet
)
from app.llm.provider import get_llm_provider, LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DealVerdictEngine:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    def generate_verdict(
        self,
        comparison_id: str,
        transaction_id: str,
        findings: List[ComparisonFinding],
        cross_doc_risks: List[CrossDocumentRisk],
        disclosure_issues: List[DisclosureIssue],
        recommendations: Dict[str, RecommendationSet],
        company_a_name: str,
        company_b_name: str,
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ) -> DealVerdict:
        material_findings = [f for f in findings if f.classification in [
            "MATERIAL_ASYMMETRY", "POTENTIAL_ASYMMETRY", "PRESENCE_ABSENCE", "CONFLICT"
        ]]

        critical_risks = [r for r in cross_doc_risks if r.severity in [Priority.CRITICAL, Priority.HIGH]]
        high_disclosures = [d for d in disclosure_issues if d.severity in [Priority.CRITICAL, Priority.HIGH]]

        overall_risk = self._determine_overall_risk(material_findings, critical_risks, high_disclosures)
        overall_assessment = self._generate_overall_assessment(overall_risk, material_findings, critical_risks)

        company_a_adv, company_a_weak = self._analyze_party_position(
            material_findings, cross_doc_risks, disclosure_issues, company_a_role, company_b_role
        )
        company_b_adv, company_b_weak = self._analyze_party_position(
            material_findings, cross_doc_risks, disclosure_issues, company_b_role, company_a_role
        )

        critical_finding_ids = [f.id for f in material_findings if f.classification == "MATERIAL_ASYMMETRY"]
        critical_finding_ids.extend([r.id for r in critical_risks])
        critical_finding_ids.extend([d.id for d in high_disclosures])

        all_recs = []
        for rec_set in recommendations.values():
            if rec_set.company_a_recommendation:
                all_recs.append(rec_set.company_a_recommendation)
            if rec_set.company_b_recommendation:
                all_recs.append(rec_set.company_b_recommendation)

        recommended_actions = self._extract_key_actions(all_recs)
        unresolved = self._identify_unresolved_questions(findings, cross_doc_risks, disclosure_issues)

        score, methodology = self._calculate_score(material_findings, cross_doc_risks, disclosure_issues)

        company_a_recs = [rec_set.company_a_recommendation for rec_set in recommendations.values() if rec_set.company_a_recommendation]
        company_b_recs = [rec_set.company_b_recommendation for rec_set in recommendations.values() if rec_set.company_b_recommendation]

        confidence = self._compute_verdict_confidence(findings, cross_doc_risks, disclosure_issues)

        return DealVerdict(
            comparison_id=comparison_id,
            transaction_id=transaction_id,
            overall_assessment=overall_assessment,
            overall_risk_level=overall_risk,
            key_asymmetries=len([f for f in findings if f.classification != "NO_MATERIAL_DIFFERENCE"]),
            critical_issues=len(critical_risks) + len(high_disclosures),
            material_asymmetries=len([f for f in findings if f.classification == "MATERIAL_ASYMMETRY"]),
            evidence_backed_findings=len([f for f in findings if f.evidence_a or f.evidence_b]),
            company_a_advantages=company_a_adv,
            company_a_weaknesses=company_a_weak,
            company_b_advantages=company_b_adv,
            company_b_weaknesses=company_b_weak,
            critical_findings=critical_finding_ids[:10],
            recommended_actions=recommended_actions,
            unresolved_questions=unresolved,
            score=score,
            score_methodology=methodology,
            company_a_recommendations=company_a_recs,
            company_b_recommendations=company_b_recs,
            confidence=confidence,
        )

    def _determine_overall_risk(
        self,
        material_findings: List[ComparisonFinding],
        critical_risks: List[CrossDocumentRisk],
        high_disclosures: List[DisclosureIssue],
    ) -> Priority:
        critical_count = len([f for f in material_findings if f.classification == "MATERIAL_ASYMMETRY"])
        critical_count += len(critical_risks)
        critical_count += len(high_disclosures)

        high_count = len([f for f in material_findings if f.classification == "POTENTIAL_ASYMMETRY"])
        high_count += len([r for r in critical_risks if r.severity == Priority.HIGH])
        high_count += len([d for d in high_disclosures if d.severity == Priority.HIGH])

        if critical_count >= 3 or (critical_count >= 1 and high_count >= 3):
            return Priority.CRITICAL
        elif critical_count >= 1 or high_count >= 2:
            return Priority.HIGH
        elif high_count >= 1 or len(material_findings) >= 3:
            return Priority.MEDIUM
        else:
            return Priority.LOW

    def _generate_overall_assessment(
        self,
        risk_level: Priority,
        material_findings: List[ComparisonFinding],
        critical_risks: List[CrossDocumentRisk],
    ) -> str:
        assessments = {
            Priority.CRITICAL: "CRITICAL RISK - Significant legal asymmetries and interconnected risks threaten transaction viability. Immediate legal attention required.",
            Priority.HIGH: "HIGH RISK - Material legal differences present substantial negotiation challenges and potential exposure. Legal counsel should prioritize resolution.",
            Priority.MEDIUM: "MODERATE RISK - Notable asymmetries exist but are manageable through targeted negotiation. Standard legal review recommended.",
            Priority.LOW: "LOW RISK - Minor differences only. Transaction terms are substantially aligned. Routine legal review sufficient.",
        }
        return assessments.get(risk_level, "UNKNOWN RISK LEVEL")

    def _analyze_party_position(
        self,
        findings: List[ComparisonFinding],
        cross_doc_risks: List[CrossDocumentRisk],
        disclosure_issues: List[DisclosureIssue],
        own_role: CompanyRole,
        other_role: CompanyRole,
    ) -> Tuple[List[str], List[str]]:
        advantages = []
        weaknesses = []

        for finding in findings:
            if finding.beneficiary == own_role:
                advantages.append(f"{finding.provision}: {finding.advantage_explanation}")
            elif finding.beneficiary == other_role:
                weaknesses.append(f"{finding.provision}: {finding.advantage_explanation}")

        for risk in cross_doc_risks:
            if own_role in [CompanyRole.BUYER, CompanyRole.ACQUIRER]:
                if "CAP" in risk.risk_type and risk.severity in [Priority.CRITICAL, Priority.HIGH]:
                    weaknesses.append(f"Cross-document risk: {risk.description}")
                if "DISCLOSURE" in risk.risk_type and risk.severity in [Priority.CRITICAL, Priority.HIGH]:
                    weaknesses.append(f"Disclosure risk: {risk.description}")

        for issue in disclosure_issues:
            if own_role in [CompanyRole.BUYER, CompanyRole.ACQUIRER] and issue.severity in [Priority.CRITICAL, Priority.HIGH]:
                weaknesses.append(f"Disclosure issue: {issue.description}")
            elif own_role in [CompanyRole.SELLER, CompanyRole.TARGET] and issue.severity in [Priority.CRITICAL, Priority.HIGH]:
                weaknesses.append(f"Disclosure gap: {issue.description}")

        return advantages, weaknesses

    def _extract_key_actions(self, recommendations: List[PartySpecificRecommendation]) -> List[str]:
        critical_recs = [r for r in recommendations if r.priority == Priority.CRITICAL]
        high_recs = [r for r in recommendations if r.priority == Priority.HIGH]

        actions = []
        for rec in critical_recs[:5]:
            actions.append(f"[{rec.priority.value}] {rec.title}: {rec.proposed_adjustment}")
        for rec in high_recs[:5]:
            actions.append(f"[{rec.priority.value}] {rec.title}: {rec.proposed_adjustment}")

        return actions[:10]

    def _identify_unresolved_questions(
        self,
        findings: List[ComparisonFinding],
        cross_doc_risks: List[CrossDocumentRisk],
        disclosure_issues: List[DisclosureIssue],
    ) -> List[str]:
        questions = []

        unmatched = [f for f in findings if f.classification == "REQUIRES_REVIEW"]
        for f in unmatched[:3]:
            questions.append(f"Classification uncertain for {f.provision}: {f.classification_reason}")

        for risk in cross_doc_risks:
            if risk.confidence < 0.6:
                questions.append(f"Cross-document risk '{risk.risk_type}' has low confidence ({risk.confidence:.0%}): {risk.description}")

        for issue in disclosure_issues:
            if issue.confidence < 0.6:
                questions.append(f"Disclosure issue '{issue.issue_type}' has low confidence ({issue.confidence:.0%}): {issue.description}")

        review_findings = [f for f in findings if f.requires_lawyer_review]
        if review_findings:
            questions.append(f"{len(review_findings)} findings require lawyer review before final assessment")

        return questions[:10]

    def _calculate_score(
        self,
        material_findings: List[ComparisonFinding],
        cross_doc_risks: List[CrossDocumentRisk],
        disclosure_issues: List[DisclosureIssue],
    ) -> Tuple[Optional[float], str]:
        if not material_findings and not cross_doc_risks and not disclosure_issues:
            return 100.0, "No material issues identified - perfect alignment"

        base_score = 100.0
        deductions = []

        for f in material_findings:
            if f.classification == "MATERIAL_ASYMMETRY":
                deduction = 12
                base_score -= deduction
                deductions.append(f"MATERIAL_ASYMMETRY ({f.provision}): -{deduction}")
            elif f.classification == "POTENTIAL_ASYMMETRY":
                deduction = 6
                base_score -= deduction
                deductions.append(f"POTENTIAL_ASYMMETRY ({f.provision}): -{deduction}")
            elif f.classification == "PRESENCE_ABSENCE":
                deduction = 8
                base_score -= deduction
                deductions.append(f"PRESENCE_ABSENCE ({f.provision}): -{deduction}")
            elif f.classification == "CONFLICT":
                deduction = 10
                base_score -= deduction
                deductions.append(f"CONFLICT ({f.provision}): -{deduction}")
            elif f.classification == "MINOR_DIFFERENCE":
                deduction = 2
                base_score -= deduction
                deductions.append(f"MINOR_DIFFERENCE ({f.provision}): -{deduction}")
            elif f.classification == "INFORMATIONAL":
                deduction = 1
                base_score -= deduction
                deductions.append(f"INFORMATIONAL ({f.provision}): -{deduction}")

        for risk in cross_doc_risks:
            if risk.severity == Priority.CRITICAL:
                deduction = 15
                base_score -= deduction
                deductions.append(f"Cross-document CRITICAL ({risk.risk_type}): -{deduction}")
            elif risk.severity == Priority.HIGH:
                deduction = 8
                base_score -= deduction
                deductions.append(f"Cross-document HIGH ({risk.risk_type}): -{deduction}")
            elif risk.severity == Priority.MEDIUM:
                deduction = 4
                base_score -= deduction
                deductions.append(f"Cross-document MEDIUM ({risk.risk_type}): -{deduction}")
            elif risk.severity == Priority.LOW:
                deduction = 1
                base_score -= deduction
                deductions.append(f"Cross-document LOW ({risk.risk_type}): -{deduction}")

        for issue in disclosure_issues:
            if issue.severity == Priority.CRITICAL:
                deduction = 12
                base_score -= deduction
                deductions.append(f"Disclosure CRITICAL ({issue.issue_type}): -{deduction}")
            elif issue.severity == Priority.HIGH:
                deduction = 7
                base_score -= deduction
                deductions.append(f"Disclosure HIGH ({issue.issue_type}): -{deduction}")
            elif issue.severity == Priority.MEDIUM:
                deduction = 3
                base_score -= deduction
                deductions.append(f"Disclosure MEDIUM ({issue.issue_type}): -{deduction}")
            elif issue.severity == Priority.LOW:
                deduction = 1
                base_score -= deduction
                deductions.append(f"Disclosure LOW ({issue.issue_type}): -{deduction}")

        base_score = max(0, min(100, base_score))

        methodology = (
            "Deal Risk Score Methodology:\n"
            "  Base: 100 (perfect alignment)\n"
            "  Deductions per finding:\n"
            "    MATERIAL_ASYMMETRY: -12\n"
            "    POTENTIAL_ASYMMETRY: -6\n"
            "    PRESENCE_ABSENCE: -8\n"
            "    CONFLICT: -10\n"
            "    MINOR_DIFFERENCE: -2\n"
            "    INFORMATIONAL: -1\n"
            "  Deductions per cross-document risk:\n"
            "    CRITICAL: -15, HIGH: -8, MEDIUM: -4, LOW: -1\n"
            "  Deductions per disclosure issue:\n"
            "    CRITICAL: -12, HIGH: -7, MEDIUM: -3, LOW: -1\n"
            "  Floor: 0, Ceiling: 100\n\n"
            "Applied Deductions:\n" + "\n".join(f"  {d}" for d in deductions)
        )

        return round(base_score, 1), methodology

    def _compute_verdict_confidence(
        self,
        findings: List[ComparisonFinding],
        cross_doc_risks: List[CrossDocumentRisk],
        disclosure_issues: List[DisclosureIssue],
    ) -> float:
        if not findings:
            return 0.5

        avg_comp_conf = sum(f.comparison_confidence for f in findings) / len(findings)
        avg_mat_conf = sum(f.materiality_confidence for f in findings) / len(findings)

        risk_conf = sum(r.confidence for r in cross_doc_risks) / len(cross_doc_risks) if cross_doc_risks else 0.5
        disc_conf = sum(d.confidence for d in disclosure_issues) / len(disclosure_issues) if disclosure_issues else 0.5

        return round((avg_comp_conf * 0.4 + avg_mat_conf * 0.3 + risk_conf * 0.15 + disc_conf * 0.15), 2)

    async def generate_verdict_with_llm(
        self,
        verdict: DealVerdict,
        findings: List[ComparisonFinding],
        cross_doc_risks: List[CrossDocumentRisk],
        disclosure_issues: List[DisclosureIssue],
        company_a_name: str,
        company_b_name: str,
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ) -> DealVerdict:
        material_findings = [f for f in findings if f.classification in [
            "MATERIAL_ASYMMETRY", "POTENTIAL_ASYMMETRY", "PRESENCE_ABSENCE", "CONFLICT"
        ]]

        prompt = f"""Generate executive deal verdict summary for M&A transaction.

Transaction: {company_a_name} ({company_a_role.value}) vs {company_b_name} ({company_b_role.value})

Overall Risk: {verdict.overall_risk_level.value}
Score: {verdict.score}/100

Material Findings ({len(material_findings)}):
{self._format_findings_for_verdict(material_findings)}

Cross-Document Risks ({len(cross_doc_risks)}):
{self._format_risks_for_verdict(cross_doc_risks)}

Disclosure Issues ({len(disclosure_issues)}):
{self._format_disclosures_for_verdict(disclosure_issues)}

Provide enhanced verdict as JSON:
{{
    "overall_assessment": "...",
    "key_narrative": "...",
    "additional_unresolved_questions": ["...", "..."]
}}"""

        schema = {
            "type": "object",
            "properties": {
                "overall_assessment": {"type": "string"},
                "key_narrative": {"type": "string"},
                "additional_unresolved_questions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["overall_assessment", "key_narrative", "additional_unresolved_questions"],
        }

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt="You are an M&A partner writing a deal verdict memo. Synthesize findings into actionable executive summary. Be precise, legally grounded, and transparent about uncertainty.",
                schema=schema,
                temperature=0.1,
                max_tokens=2048,
            )

            verdict.overall_assessment = result.get("overall_assessment", verdict.overall_assessment)
            verdict.unresolved_questions.extend(result.get("additional_unresolved_questions", []))

        except Exception as e:
            logger.warning(f"LLM verdict enhancement failed: {e}")

        return verdict

    def _format_findings_for_verdict(self, findings: List[ComparisonFinding]) -> str:
        lines = []
        for f in findings[:10]:
            lines.append(f"- {f.provision} ({f.category.value}): {f.classification.value} - {f.classification_reason}")
        return "\n".join(lines) if lines else "None"

    def _format_risks_for_verdict(self, risks: List[CrossDocumentRisk]) -> str:
        lines = []
        for r in risks[:5]:
            lines.append(f"- {r.risk_type} ({r.severity.value}): {r.description}")
        return "\n".join(lines) if lines else "None"

    def _format_disclosures_for_verdict(self, issues: List[DisclosureIssue]) -> str:
        lines = []
        for d in issues[:5]:
            lines.append(f"- {d.issue_type} ({d.severity.value}): {d.description}")
        return "\n".join(lines) if lines else "None"


from typing import Tuple