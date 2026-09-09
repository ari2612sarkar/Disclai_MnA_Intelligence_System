import logging
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    ComparisonFinding, LegalCategory, CompanyRole
)
from app.llm.provider import get_llm_provider, LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TransactionalImpactEngine:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    def analyze_impact(
        self,
        findings: List[ComparisonFinding],
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ) -> List[ComparisonFinding]:
        for finding in findings:
            if finding.classification in [
                "MATERIAL_ASYMMETRY",
                "POTENTIAL_ASYMMETRY",
                "PRESENCE_ABSENCE",
                "CONFLICT",
            ]:
                self._add_structured_impact(finding, company_a_role, company_b_role)

        return findings

    def _add_structured_impact(
        self,
        finding: ComparisonFinding,
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ):
        category = finding.category
        provision = finding.provision

        pos_a = finding.company_a_position
        pos_b = finding.company_b_position

        if category == LegalCategory.INDEMNIFICATION:
            self._analyze_indemnification_impact(finding, pos_a, pos_b, company_a_role, company_b_role)
        elif category == LegalCategory.REPRESENTATIONS_WARRANTIES:
            self._analyze_rw_impact(finding, pos_a, pos_b, company_a_role, company_b_role)
        elif category == LegalCategory.MATERIAL_ADVERSE_EFFECT:
            self._analyze_mae_impact(finding, pos_a, pos_b, company_a_role, company_b_role)
        elif category == LegalCategory.TERMINATION_RIGHTS:
            self._analyze_termination_impact(finding, pos_a, pos_b, company_a_role, company_b_role)
        elif category == LegalCategory.CLOSING_CONDITIONS:
            self._analyze_closing_impact(finding, pos_a, pos_b, company_a_role, company_b_role)
        elif category == LegalCategory.LITIGATION:
            self._analyze_litigation_impact(finding, pos_a, pos_b, company_a_role, company_b_role)
        elif category == LegalCategory.CHANGE_OF_CONTROL:
            self._analyze_coc_impact(finding, pos_a, pos_b, company_a_role, company_b_role)
        else:
            self._analyze_generic_impact(finding, pos_a, pos_b)

    def _analyze_indemnification_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
        role_a: CompanyRole,
        role_b: CompanyRole,
    ):
        provision = finding.provision.lower()

        if "cap" in provision or "liability" in provision:
            pct_a = pos_a.percentage if pos_a and pos_a.percentage else 0
            pct_b = pos_b.percentage if pos_b and pos_b.percentage else 0

            if pct_a > pct_b:
                finding.legal_impact = f"Company A ({role_a.value}) has higher liability cap ({pct_a}% vs {pct_b}%), limiting seller recovery exposure"
                finding.commercial_impact = f"Company B ({role_b.value}) has stronger recovery protection up to {pct_b}% of purchase price"
                finding.post_closing_impact = "Different maximum exposure following post-closing breaches"
                finding.negotiation_impact = "May require negotiation of general cap or targeted higher caps for specific representations"
            elif pct_b > pct_a:
                finding.legal_impact = f"Company B ({role_b.value}) has higher liability cap ({pct_b}% vs {pct_a}%), limiting seller recovery exposure"
                finding.commercial_impact = f"Company A ({role_a.value}) has stronger recovery protection up to {pct_a}% of purchase price"
                finding.post_closing_impact = "Different maximum exposure following post-closing breaches"
                finding.negotiation_impact = "May require negotiation of general cap or targeted higher caps for specific representations"
            else:
                finding.legal_impact = "Same liability cap percentage"
                finding.commercial_impact = "Equivalent recovery exposure"
                finding.post_closing_impact = "Equivalent post-closing exposure"
                finding.negotiation_impact = "Cap unlikely to be negotiation point"

        elif "basket" in provision or "threshold" in provision:
            amt_a = pos_a.amount if pos_a and pos_a.amount else 0
            amt_b = pos_b.amount if pos_b and pos_b.amount else 0

            if amt_a > amt_b:
                finding.legal_impact = f"Company A ({role_a.value}) has higher basket (${amt_a:,.0f} vs ${amt_b:,.0f}), delaying indemnification obligation"
                finding.commercial_impact = f"Company B ({role_b.value}) can claim indemnification sooner with lower threshold"
                finding.post_closing_impact = "Different threshold for triggering indemnification claims"
                finding.negotiation_impact = "Basket amount often negotiated with cap"
            elif amt_b > amt_a:
                finding.legal_impact = f"Company B ({role_b.value}) has higher basket (${amt_b:,.0f} vs ${amt_a:,.0f}), delaying indemnification obligation"
                finding.commercial_impact = f"Company A ({role_a.value}) can claim indemnification sooner with lower threshold"
                finding.post_closing_impact = "Different threshold for triggering indemnification claims"
                finding.negotiation_impact = "Basket amount often negotiated with cap"

        elif "survival" in provision:
            dur_a = pos_a.duration if pos_a else None
            dur_b = pos_b.duration if pos_b else None
            finding.legal_impact = f"Different survival periods: Company A ({dur_a}), Company B ({dur_b})"
            finding.commercial_impact = "Different claim windows for post-closing breaches"
            finding.post_closing_impact = "Time-limited exposure differs between parties"
            finding.negotiation_impact = "Survival period often a key negotiation point"

    def _analyze_rw_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
        role_a: CompanyRole,
        role_b: CompanyRole,
    ):
        finding.legal_impact = f"Differences in representations & warranties for {finding.provision}"
        finding.commercial_impact = "Affects scope of seller's factual assertions and buyer's due diligence reliance"
        finding.closing_impact = "May affect conditions precedent to closing"
        finding.post_closing_impact = "Different exposure for breaches of representations"
        finding.negotiation_impact = "R&W scope heavily negotiated; differences may require alignment"

    def _analyze_mae_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
        role_a: CompanyRole,
        role_b: CompanyRole,
    ):
        exc_a = set(pos_a.exception) if pos_a and pos_a.exception else set()
        exc_b = set(pos_b.exception) if pos_b and pos_b.exception else set()

        if exc_a != exc_b:
            finding.legal_impact = f"Different MAE carve-outs. Company A exceptions: {list(exc_a)}; Company B exceptions: {list(exc_b)}"
            finding.commercial_impact = "Different allocation of general business risk between parties"
            finding.closing_impact = "May affect whether MAE condition is satisfied at closing"
            finding.post_closing_impact = "Different scope of events constituting MAE"
            finding.negotiation_impact = "MAE definition is heavily negotiated; carve-outs directly affect termination rights"

    def _analyze_termination_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
        role_a: CompanyRole,
        role_b: CompanyRole,
    ):
        finding.legal_impact = f"Different termination rights for {finding.provision}"
        finding.commercial_impact = "Asymmetric walk-away rights affect deal certainty"
        finding.closing_impact = "May allow one party to terminate where the other cannot"
        finding.post_closing_impact = "Pre-closing termination rights affect deal completion probability"
        finding.negotiation_impact = "Termination provisions are critical for deal certainty"

    def _analyze_closing_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
        role_a: CompanyRole,
        role_b: CompanyRole,
    ):
        finding.legal_impact = f"Different closing conditions for {finding.provision}"
        finding.commercial_impact = "Asymmetric conditions precedent affect closing obligations"
        finding.closing_impact = "Directly affects whether each party is obligated to close"
        finding.post_closing_impact = "Conditions not met may prevent closing entirely"
        finding.negotiation_impact = "Closing conditions are fundamental to deal execution"

    def _analyze_litigation_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
        role_a: CompanyRole,
        role_b: CompanyRole,
    ):
        finding.legal_impact = f"Different litigation disclosures for {finding.provision}"
        finding.commercial_impact = "Undisclosed litigation creates indemnification exposure"
        finding.closing_impact = "May affect closing conditions and MAE analysis"
        finding.post_closing_impact = "Post-closing litigation exposure differs"
        finding.negotiation_impact = "Litigation disclosure often requires specific indemnity or price adjustment"

    def _analyze_coc_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
        role_a: CompanyRole,
        role_b: CompanyRole,
    ):
        finding.legal_impact = f"Different change-of-control provisions for {finding.provision}"
        finding.commercial_impact = "Affects ability to assign/transfer contracts without consent"
        finding.closing_impact = "May require third-party consents before closing"
        finding.post_closing_impact = "Post-closing assignment flexibility differs"
        finding.negotiation_impact = "Consent requirements can delay or prevent closing"

    def _analyze_generic_impact(
        self,
        finding: ComparisonFinding,
        pos_a: Optional[Any],
        pos_b: Optional[Any],
    ):
        diffs = finding.differences
        if diffs:
            finding.legal_impact = f"Difference in {provision}: " + "; ".join(
                f"{d.attribute}: {d.company_a_value} vs {d.company_b_value}" for d in diffs
            )
        else:
            finding.legal_impact = f"Structural difference in {provision}"
        finding.commercial_impact = "Commercial impact requires legal assessment"
        finding.closing_impact = "Closing impact requires legal assessment"
        finding.post_closing_impact = "Post-closing impact requires legal assessment"
        finding.negotiation_impact = "Negotiation impact requires legal assessment"

    async def analyze_impact_with_llm(
        self,
        findings: List[ComparisonFinding],
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ) -> List[ComparisonFinding]:
        for finding in findings:
            if finding.classification in [
                "MATERIAL_ASYMMETRY",
                "POTENTIAL_ASYMMETRY",
                "PRESENCE_ABSENCE",
                "CONFLICT",
            ]:
                await self._llm_analyze_impact(finding, company_a_role, company_b_role)
        return findings

    async def _llm_analyze_impact(
        self,
        finding: ComparisonFinding,
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ):
        pos_a = finding.company_a_position
        pos_b = finding.company_b_position

        diff_summary = "\n".join([
            f"- {d.attribute}: A={d.company_a_value}, B={d.company_b_value}"
            for d in finding.differences
        ])

        prompt = f"""Analyze the transactional impact of this legal asymmetry in an M&A deal.

Provision: {finding.provision}
Category: {finding.category.value}
Classification: {finding.classification.value}

Company A Role: {company_a_role.value}
Company B Role: {company_b_role.value}

Company A Position:
- Party: {pos_a.party.value if pos_a else 'N/A'}
- Percentage: {pos_a.percentage if pos_a else 'N/A'}
- Amount: {pos_a.amount if pos_a else 'N/A'}
- Duration: {pos_a.duration if pos_a else 'N/A'}
- Conditions: {pos_a.condition if pos_a else 'N/A'}
- Exceptions: {pos_a.exception if pos_a else 'N/A'}
- Qualifiers: {pos_a.qualifier if pos_a else 'N/A'}
- Consequences: {pos_a.consequence if pos_a else 'N/A'}

Company B Position:
- Party: {pos_b.party.value if pos_b else 'N/A'}
- Percentage: {pos_b.percentage if pos_b else 'N/A'}
- Amount: {pos_b.amount if pos_b else 'N/A'}
- Duration: {pos_b.duration if pos_b else 'N/A'}
- Conditions: {pos_b.condition if pos_b else 'N/A'}
- Exceptions: {pos_b.exception if pos_b else 'N/A'}
- Qualifiers: {pos_b.qualifier if pos_b else 'N/A'}
- Consequences: {pos_b.consequence if pos_b else 'N/A'}

Differences:
{diff_summary}

Provide structured impact analysis as JSON:
{{
    "legal_impact": "...",
    "commercial_impact": "...",
    "closing_impact": "...",
    "post_closing_impact": "...",
    "negotiation_impact": "..."
}}"""

        schema = {
            "type": "object",
            "properties": {
                "legal_impact": {"type": "string"},
                "commercial_impact": {"type": "string"},
                "closing_impact": {"type": "string"},
                "post_closing_impact": {"type": "string"},
                "negotiation_impact": {"type": "string"},
            },
            "required": ["legal_impact", "commercial_impact", "closing_impact", "post_closing_impact", "negotiation_impact"],
        }

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt="You are an M&A lawyer analyzing transactional impact of legal asymmetries. Be precise and legally grounded. Do not invent monetary amounts not in evidence.",
                schema=schema,
                temperature=0.1,
                max_tokens=2048,
            )

            finding.legal_impact = result.get("legal_impact", finding.legal_impact)
            finding.commercial_impact = result.get("commercial_impact", finding.commercial_impact)
            finding.closing_impact = result.get("closing_impact", finding.closing_impact)
            finding.post_closing_impact = result.get("post_closing_impact", finding.post_closing_impact)
            finding.negotiation_impact = result.get("negotiation_impact", finding.negotiation_impact)

        except Exception as e:
            logger.warning(f"LLM impact analysis failed for {finding.provision}: {e}")