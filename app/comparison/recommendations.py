import logging
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    ComparisonFinding, PartySpecificRecommendation, RecommendationSet,
    RecommendationType, Priority, CompanyRole, LegalPosition, LegalCategory
)
from app.llm.provider import get_llm_provider, LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OptimizationEngine:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    def generate_recommendations(
        self,
        findings: List[ComparisonFinding],
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ) -> Dict[str, RecommendationSet]:
        recommendations = {}

        for finding in findings:
            if finding.classification in [
                "MATERIAL_ASYMMETRY",
                "POTENTIAL_ASYMMETRY",
                "PRESENCE_ABSENCE",
                "CONFLICT",
            ]:
                rec_set = self._generate_for_finding(finding, company_a_role, company_b_role)
                recommendations[finding.id] = rec_set

        return recommendations

    def _generate_for_finding(
        self,
        finding: ComparisonFinding,
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ) -> RecommendationSet:
        pos_a = finding.company_a_position
        pos_b = finding.company_b_position

        rec_a = self._generate_company_recommendation(
            finding, pos_a, pos_b, company_a_role, company_b_role, "company_a"
        )
        rec_b = self._generate_company_recommendation(
            finding, pos_b, pos_a, company_b_role, company_a_role, "company_b"
        )

        return RecommendationSet(
            finding_id=finding.id,
            company_a_recommendation=rec_a,
            company_b_recommendation=rec_b,
        )

    def _generate_company_recommendation(
        self,
        finding: ComparisonFinding,
        own_pos: Optional[LegalPosition],
        counterparty_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        counterparty_role: CompanyRole,
        company_key: str,
    ) -> Optional[PartySpecificRecommendation]:
        if not own_pos:
            return self._recommend_add_provision(finding, counterparty_pos, own_role, counterparty_role, company_key)

        category = finding.category
        provision = finding.provision.lower()

        if category == LegalCategory.INDEMNIFICATION:
            return self._recommend_indemnity(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)
        elif category == LegalCategory.REPRESENTATIONS_WARRANTIES:
            return self._recommend_rw(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)
        elif category == LegalCategory.MATERIAL_ADVERSE_EFFECT:
            return self._recommend_mae(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)
        elif category == LegalCategory.TERMINATION_RIGHTS:
            return self._recommend_termination(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)
        elif category == LegalCategory.CLOSING_CONDITIONS:
            return self._recommend_closing(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)
        elif category == LegalCategory.LITIGATION:
            return self._recommend_litigation(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)
        elif category == LegalCategory.DISCLOSURE_EXCEPTIONS:
            return self._recommend_disclosure(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)
        else:
            return self._recommend_generic(finding, own_pos, counterparty_pos, own_role, counterparty_role, company_key)

    def _recommend_indemnity(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        provision = finding.provision.lower()

        if "cap" in provision or "liability" in provision:
            own_pct = own_pos.percentage or 0
            cp_pct = cp_pos.percentage if cp_pos and cp_pos.percentage else 0

            if own_role in [CompanyRole.SELLER, CompanyRole.TARGET]:
                if own_pct > cp_pct:
                    return PartySpecificRecommendation(
                        company_id=company_key,
                        company_role=own_role,
                        recommendation_type=RecommendationType.LIABILITY_CAP_ADJUSTMENT,
                        title="Reduce General Liability Cap",
                        description=f"Current cap ({own_pct}%) exceeds counterparty ({cp_pct}%). Consider reducing to match market or counterparty position.",
                        rationale="Lower cap reduces maximum exposure while maintaining negotiation credibility",
                        current_position=f"{own_pct}% of purchase price",
                        proposed_adjustment=f"Reduce to {cp_pct}% or negotiate targeted higher caps for fundamental reps only",
                        legal_basis="General cap applies to all breaches; fundamental reps warrant separate treatment",
                        commercial_tradeoff="Lower cap improves deal attractiveness but reduces seller protection",
                        negotiation_objective="Align cap with counterparty or market standard; carve out fundamental reps",
                        priority=Priority.HIGH,
                        confidence=0.8,
                        finding_id=finding.id,
                    )
                else:
                    return PartySpecificRecommendation(
                        company_id=company_key,
                        company_role=own_role,
                        recommendation_type=RecommendationType.LIABILITY_CAP_ADJUSTMENT,
                        title="Maintain or Reduce Liability Cap",
                        description=f"Current seller-side cap ({own_pct}%) is at or below counterparty reference ({cp_pct}%). Preserve the lower exposure position where commercially defensible.",
                        rationale="A lower seller liability cap limits maximum post-closing exposure; exceptions can be negotiated separately for fundamental matters.",
                        current_position=f"{own_pct}% of purchase price",
                        proposed_adjustment=f"Maintain {own_pct}% or seek a lower cap where justified; use targeted higher caps only for specifically negotiated fundamental reps.",
                        legal_basis="General indemnity caps allocate post-closing liability and should be distinguished from negotiated fundamental-representation exceptions.",
                        commercial_tradeoff="A lower cap protects seller exposure but may reduce buyer recovery and increase negotiation friction.",
                        negotiation_objective="Preserve a defensible general cap while separating fundamental-representation risk.",
                        priority=Priority.MEDIUM,
                        confidence=0.8,
                        finding_id=finding.id,
                    )
            else:
                if own_pct < cp_pct:
                    return PartySpecificRecommendation(
                        company_id=company_key,
                        company_role=own_role,
                        recommendation_type=RecommendationType.LIABILITY_CAP_ADJUSTMENT,
                        title="Increase Liability Cap",
                        description=f"Current cap ({own_pct}%) is below counterparty ({cp_pct}%). Seek increase for better recovery protection.",
                        rationale="Buyer needs adequate recovery for potential breaches",
                        current_position=f"{own_pct}% of purchase price",
                        proposed_adjustment=f"Increase to {cp_pct}% or negotiate targeted higher caps for fundamental reps",
                        legal_basis="Fundamental representations (title, authority, capitalization) warrant higher recovery",
                        commercial_tradeoff="Higher cap improves recovery but may face seller resistance",
                        negotiation_objective="Achieve parity with counterparty or market standard",
                        priority=Priority.HIGH,
                        confidence=0.8,
                        finding_id=finding.id,
                    )
                else:
                    return PartySpecificRecommendation(
                        company_id=company_key,
                        company_role=own_role,
                        recommendation_type=RecommendationType.LIABILITY_CAP_ADJUSTMENT,
                        title="Maintain Current Cap Position",
                        description=f"Current cap ({own_pct}%) meets or exceeds counterparty ({cp_pct}%).",
                        rationale="Strong recovery protection already in place",
                        current_position=f"{own_pct}% of purchase price",
                        proposed_adjustment="Maintain; consider targeted exceptions for fraud/willful misconduct",
                        legal_basis="Current cap provides adequate recovery protection",
                        commercial_tradeoff="No change needed; focus negotiation on other terms",
                        negotiation_objective="Preserve current cap; resist reductions",
                        priority=Priority.LOW,
                        confidence=0.6,
                        finding_id=finding.id,
                    )

        elif "basket" in provision or "threshold" in provision:
            own_amt = own_pos.amount or 0
            cp_amt = cp_pos.amount if cp_pos and cp_pos.amount else 0

            if own_role in [CompanyRole.SELLER, CompanyRole.TARGET]:
                if own_amt > cp_amt:
                    return PartySpecificRecommendation(
                        company_id=company_key,
                        company_role=own_role,
                        recommendation_type=RecommendationType.INDEMNITY,
                        title="Reduce Basket Threshold",
                        description=f"Current basket (${own_amt:,.0f}) exceeds counterparty (${cp_amt:,.0f}). Consider reducing.",
                        rationale="Lower basket allows earlier indemnification claims but reduces de minimis protection",
                        current_position=f"${own_amt:,.0f}",
                        proposed_adjustment=f"Reduce to ${cp_amt:,.0f} or negotiate deductible vs. threshold structure",
                        legal_basis="Basket type (deductible vs threshold) significantly affects economics",
                        commercial_tradeoff="Lower basket improves buyer recovery but increases seller claim frequency",
                        negotiation_objective="Align with counterparty; consider hybrid structure",
                        priority=Priority.MEDIUM,
                        confidence=0.7,
                        finding_id=finding.id,
                    )
                else:
                    return PartySpecificRecommendation(
                        company_id=company_key,
                        company_role=own_role,
                        recommendation_type=RecommendationType.INDEMNITY,
                        title="Maintain or Increase Basket",
                        description=f"Current basket (${own_amt:,.0f}) is at or below counterparty (${cp_amt:,.0f}).",
                        rationale="Higher basket reduces claim frequency and administrative burden",
                        current_position=f"${own_amt:,.0f}",
                        proposed_adjustment=f"Maintain or increase to ${max(cp_amt, own_amt * 1.5):,.0f}",
                        legal_basis="Basket serves as de minimis filter; should reflect deal size",
                        commercial_tradeoff="Higher basket delays buyer recovery but reduces noise claims",
                        negotiation_objective="Achieve market-standard basket relative to deal value",
                        priority=Priority.MEDIUM,
                        confidence=0.6,
                        finding_id=finding.id,
                    )
            else:
                if own_amt < cp_amt:
                    return PartySpecificRecommendation(
                        company_id=company_key,
                        company_role=own_role,
                        recommendation_type=RecommendationType.INDEMNITY,
                        title="Reduce Basket for Earlier Recovery",
                        description=f"Current basket (${own_amt:,.0f}) is below counterparty (${cp_amt:,.0f}). Consider seeking reduction.",
                        rationale="Lower basket enables recovery for smaller claims",
                        current_position=f"${own_amt:,.0f}",
                        proposed_adjustment=f"Reduce to ${cp_amt:,.0f} or propose tiered basket structure",
                        legal_basis="Basket should not exceed materiality threshold for the business",
                        commercial_tradeoff="Lower basket improves recovery but may increase negotiation friction",
                        negotiation_objective="Align basket with materiality threshold",
                        priority=Priority.MEDIUM,
                        confidence=0.7,
                        finding_id=finding.id,
                    )

        return self._recommend_generic(finding, own_pos, cp_pos, own_role, cp_role, company_key)

    def _recommend_rw(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        if own_role in [CompanyRole.SELLER, CompanyRole.TARGET]:
            return PartySpecificRecommendation(
                company_id=company_key,
                company_role=own_role,
                recommendation_type=RecommendationType.REPRESENTATION_WARRANTY_QUALIFICATION,
                title="Qualify Representations with Knowledge/Disclosure",
                description=f"Add knowledge qualifiers and disclosure schedule references to {finding.provision}",
                rationale="Reduces risk of unintentional breaches for matters outside seller's knowledge",
                current_position=own_pos.obligation_right or "Absolute representation",
                proposed_adjustment="Add 'to Seller's knowledge' qualifier; reference disclosure schedule",
                legal_basis="Knowledge qualifiers are standard for non-fundamental representations",
                commercial_tradeoff="Qualified reps reduce seller exposure but may face buyer resistance",
                negotiation_objective="Qualify non-fundamental reps; keep fundamental reps absolute",
                priority=Priority.MEDIUM,
                confidence=0.75,
                finding_id=finding.id,
            )
        else:
            return PartySpecificRecommendation(
                company_id=company_key,
                company_role=own_role,
                recommendation_type=RecommendationType.REPRESENTATION_WARRANTY_QUALIFICATION,
                title="Resist Over-Qualification of Representations",
                description=f"Push back on knowledge qualifiers and disclosure qualifications for {finding.provision}",
                rationale="Absolute representations provide stronger recovery basis",
                current_position=own_pos.obligation_right or "Qualified representation",
                proposed_adjustment="Seek absolute representations for fundamental matters; limit knowledge qualifiers",
                legal_basis="Fundamental reps (title, authority, capitalization) should be absolute",
                commercial_tradeoff="Absolute reps increase seller exposure but improve buyer protection",
                negotiation_objective="Maintain absolute reps for fundamental matters; accept qualified for others",
                priority=Priority.MEDIUM,
                confidence=0.7,
                finding_id=finding.id,
            )

    def _recommend_mae(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        if own_role in [CompanyRole.SELLER, CompanyRole.TARGET]:
            return PartySpecificRecommendation(
                company_id=company_key,
                company_role=own_role,
                recommendation_type=RecommendationType.SPA_AMENDMENT,
                title="Broaden MAE Carve-Outs",
                description=f"Expand MAE exceptions in {finding.provision} to include additional carve-outs",
                rationale="Broader carve-outs reduce risk of MAE being triggered by general market conditions",
                current_position=f"Current exceptions: {own_pos.exception}",
                proposed_adjustment="Add carve-outs for: pandemic, regulatory changes, cyber incidents, supply chain disruptions",
                legal_basis="MAE carve-outs allocate systematic risk to buyer",
                commercial_tradeoff="Broader carve-outs protect seller but reduce buyer's termination right",
                negotiation_objective="Achieve balanced MAE definition with specific, enumerated carve-outs",
                priority=Priority.MEDIUM,
                confidence=0.7,
                finding_id=finding.id,
            )
        else:
            return PartySpecificRecommendation(
                company_id=company_key,
                company_role=own_role,
                recommendation_type=RecommendationType.SPA_AMENDMENT,
                title="Narrow MAE Carve-Outs",
                description=f"Resist expansion of MAE exceptions in {finding.provision}",
                rationale="Narrower carve-outs preserve buyer's termination right for material adverse changes",
                current_position=f"Current exceptions: {own_pos.exception}",
                proposed_adjustment="Limit carve-outs to truly systematic risks; require disproportionate impact on target",
                legal_basis="MAE should protect buyer from target-specific material adversity",
                commercial_tradeoff="Narrower carve-outs increase buyer protection but may face seller resistance",
                negotiation_objective="Maintain targeted carve-outs; resist catch-all exceptions",
                priority=Priority.MEDIUM,
                confidence=0.7,
                finding_id=finding.id,
            )

    def _recommend_termination(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        return PartySpecificRecommendation(
            company_id=company_key,
            company_role=own_role,
            recommendation_type=RecommendationType.TERMINATION_PROTECTION,
            title="Align Termination Rights",
            description=f"Negotiate mutual termination rights for {finding.provision}",
            rationale="Asymmetric termination rights create deal certainty imbalance",
            current_position=f"Own conditions: {own_pos.condition}; Counterparty: {cp_pos.condition if cp_pos else 'N/A'}",
            proposed_adjustment="Seek mutual termination rights with equivalent cure periods and materiality standards",
            legal_basis="Mutual termination rights are standard in balanced agreements",
            commercial_tradeoff="Mutual rights increase deal certainty for both parties",
            negotiation_objective="Achieve symmetry in termination provisions",
            priority=Priority.HIGH,
            confidence=0.8,
            finding_id=finding.id,
        )

    def _recommend_closing(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        return PartySpecificRecommendation(
            company_id=company_key,
            company_role=own_role,
            recommendation_type=RecommendationType.SPA_AMENDMENT,
            title="Align Closing Conditions",
            description=f"Negotiate mutual closing conditions for {finding.provision}",
            rationale="Asymmetric closing conditions create unequal closing obligations",
            current_position=f"Own conditions: {own_pos.condition}; Counterparty: {cp_pos.condition if cp_pos else 'N/A'}",
            proposed_adjustment="Seek substantially equivalent closing conditions for both parties",
            legal_basis="Mutual conditions precedent are standard for simultaneous signing/closing",
            commercial_tradeoff="Aligned conditions reduce risk of failed closing",
            negotiation_objective="Achieve symmetry in closing conditions",
            priority=Priority.HIGH,
            confidence=0.8,
            finding_id=finding.id,
        )

    def _recommend_litigation(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        if own_role in [CompanyRole.SELLER, CompanyRole.TARGET]:
            return PartySpecificRecommendation(
                company_id=company_key,
                company_role=own_role,
                recommendation_type=RecommendationType.DISCLOSURE,
                title="Ensure Full Litigation Disclosure",
                description=f"Disclose all litigation matters in disclosure schedule for {finding.provision}",
                rationale="Undisclosed litigation creates indemnification exposure and potential fraud claims",
                current_position=f"Known matters: {own_pos.exception}",
                proposed_adjustment="Complete disclosure schedule; consider specific indemnity for known matters",
                legal_basis="Disclosure qualifies representations; specific indemnity allocates known risk",
                commercial_tradeoff="Full disclosure reduces post-closing risk but may affect purchase price",
                negotiation_objective="Disclose all material matters; negotiate specific indemnities",
                priority=Priority.CRITICAL,
                confidence=0.9,
                finding_id=finding.id,
            )
        else:
            return PartySpecificRecommendation(
                company_id=company_key,
                company_role=own_role,
                recommendation_type=RecommendationType.FURTHER_DILIGENCE,
                title="Conduct Further Litigation Diligence",
                description=f"Investigate potential undisclosed litigation for {finding.provision}",
                rationale="Data room may contain litigation not reflected in disclosure schedule",
                current_position="Disclosure schedule may be incomplete",
                proposed_adjustment="Request supplemental disclosure; review court records; seek specific indemnity",
                legal_basis="Buyer entitled to complete disclosure for reliance on representations",
                commercial_tradeoff="Additional diligence costs vs. risk of undisclosed liability",
                negotiation_objective="Obtain complete litigation picture; price or indemnify known risks",
                priority=Priority.HIGH,
                confidence=0.8,
                finding_id=finding.id,
            )

    def _recommend_disclosure(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        return PartySpecificRecommendation(
            company_id=company_key,
            company_role=own_role,
            recommendation_type=RecommendationType.DISCLOSURE,
            title="Reconcile Disclosure Schedule with Data Room",
            description=f"Ensure disclosure schedule for {finding.provision} matches data room contents",
            rationale="Inconsistencies create ambiguity about what is disclosed vs. excepted",
            current_position=f"Disclosure exceptions: {own_pos.exception}",
            proposed_adjustment="Cross-reference disclosure schedule with data room; update as needed",
            legal_basis="Disclosure schedule qualifies representations; must be accurate and complete",
            commercial_tradeoff="Accuracy reduces post-closing disputes",
            negotiation_objective="Achieve complete and accurate disclosure schedule",
            priority=Priority.HIGH,
            confidence=0.85,
            finding_id=finding.id,
        )

    def _recommend_generic(
        self,
        finding: ComparisonFinding,
        own_pos: LegalPosition,
        cp_pos: Optional[LegalPosition],
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        return PartySpecificRecommendation(
            company_id=company_key,
            company_role=own_role,
            recommendation_type=RecommendationType.INFORMATION_REQUEST,
            title=f"Address Asymmetry in {finding.provision}",
            description=f"Review and negotiate {finding.provision} to address identified differences",
            rationale=f"Asymmetry classified as {finding.classification.value}",
            current_position=str(own_pos.obligation_right) if own_pos else "No provision",
            proposed_adjustment="Negotiate alignment with counterparty position or market standard",
            legal_basis="Contract terms should reflect negotiated risk allocation",
            commercial_tradeoff="Depends on specific provision and commercial context",
            negotiation_objective="Achieve commercially reasonable alignment",
            priority=Priority.MEDIUM,
            confidence=0.5,
            finding_id=finding.id,
        )

    def _recommend_add_provision(
        self,
        finding: ComparisonFinding,
        cp_pos: LegalPosition,
        own_role: CompanyRole,
        cp_role: CompanyRole,
        company_key: str,
    ) -> PartySpecificRecommendation:
        return PartySpecificRecommendation(
            company_id=company_key,
            company_role=own_role,
            recommendation_type=RecommendationType.SPA_AMENDMENT,
            title=f"Add Missing Provision: {finding.provision}",
            description=f"Counterparty has {finding.provision} but Company {company_key[-1].upper()} does not. Consider adding equivalent protection.",
            rationale="Missing provision creates unallocated risk",
            current_position="No equivalent provision",
            proposed_adjustment=f"Add provision mirroring counterparty's {finding.provision} with appropriate party alignment",
            legal_basis="Risk allocation should be addressed for all material provisions",
            commercial_tradeoff="Adding provision may require concession elsewhere",
            negotiation_objective="Achieve comprehensive risk allocation",
            priority=Priority.HIGH,
            confidence=0.8,
            finding_id=finding.id,
        )

    async def generate_recommendations_with_llm(
        self,
        findings: List[ComparisonFinding],
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ) -> Dict[str, RecommendationSet]:
        det_recs = self.generate_recommendations(findings, company_a_role, company_b_role)

        for finding in findings:
            if finding.classification in [
                "MATERIAL_ASYMMETRY",
                "POTENTIAL_ASYMMETRY",
                "PRESENCE_ABSENCE",
                "CONFLICT",
            ]:
                await self._llm_enhance_recommendations(finding, det_recs.get(finding.id), company_a_role, company_b_role)

        return det_recs

    async def _llm_enhance_recommendations(
        self,
        finding: ComparisonFinding,
        rec_set: Optional[RecommendationSet],
        company_a_role: CompanyRole,
        company_b_role: CompanyRole,
    ):
        if not rec_set:
            return

        pos_a = finding.company_a_position
        pos_b = finding.company_b_position

        prompt = f"""Generate party-specific recommendations for this M&A legal asymmetry.

Finding: {finding.provision} ({finding.category.value})
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

Company B Position:
- Party: {pos_b.party.value if pos_b else 'N/A'}
- Percentage: {pos_b.percentage if pos_b else 'N/A'}
- Amount: {pos_b.amount if pos_b else 'N/A'}
- Duration: {pos_b.duration if pos_b else 'N/A'}
- Conditions: {pos_b.condition if pos_b else 'N/A'}
- Exceptions: {pos_b.exception if pos_b else 'N/A'}

Current Recommendations:
Company A: {rec_set.company_a_recommendation.title if rec_set.company_a_recommendation else 'None'}
Company B: {rec_set.company_b_recommendation.title if rec_set.company_b_recommendation else 'None'}

Enhance with legally grounded, commercially sensible, transaction-aware recommendations.
Respond with JSON:
{{
    "company_a": {{
        "recommendation_type": "...",
        "title": "...",
        "description": "...",
        "rationale": "...",
        "proposed_adjustment": "...",
        "legal_basis": "...",
        "commercial_tradeoff": "...",
        "negotiation_objective": "...",
        "priority": "CRITICAL|HIGH|MEDIUM|LOW",
        "confidence": 0.0-1.0
    }},
    "company_b": {{
        "recommendation_type": "...",
        "title": "...",
        "description": "...",
        "rationale": "...",
        "proposed_adjustment": "...",
        "legal_basis": "...",
        "commercial_tradeoff": "...",
        "negotiation_objective": "...",
        "priority": "CRITICAL|HIGH|MEDIUM|LOW",
        "confidence": 0.0-1.0
    }}
}}"""

        schema = {
            "type": "object",
            "properties": {
                "company_a": {
                    "type": "object",
                    "properties": {
                        "recommendation_type": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "rationale": {"type": "string"},
                        "proposed_adjustment": {"type": "string"},
                        "legal_basis": {"type": "string"},
                        "commercial_tradeoff": {"type": "string"},
                        "negotiation_objective": {"type": "string"},
                        "priority": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["recommendation_type", "title", "description", "rationale", "proposed_adjustment", "legal_basis", "commercial_tradeoff", "negotiation_objective", "priority", "confidence"],
                },
                "company_b": {
                    "type": "object",
                    "properties": {
                        "recommendation_type": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "rationale": {"type": "string"},
                        "proposed_adjustment": {"type": "string"},
                        "legal_basis": {"type": "string"},
                        "commercial_tradeoff": {"type": "string"},
                        "negotiation_objective": {"type": "string"},
                        "priority": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["recommendation_type", "title", "description", "rationale", "proposed_adjustment", "legal_basis", "commercial_tradeoff", "negotiation_objective", "priority", "confidence"],
                },
            },
            "required": ["company_a", "company_b"],
        }

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt="You are an M&A lawyer generating party-specific deal optimization recommendations. Be legally defensible, commercially sensible, and transaction-aware. Do not recommend actions merely because they sound protective.",
                schema=schema,
                temperature=0.1,
                max_tokens=3072,
            )

            if rec_set.company_a_recommendation and "company_a" in result:
                r = result["company_a"]
                for key, val in r.items():
                    if hasattr(rec_set.company_a_recommendation, key):
                        setattr(rec_set.company_a_recommendation, key, val)

            if rec_set.company_b_recommendation and "company_b" in result:
                r = result["company_b"]
                for key, val in r.items():
                    if hasattr(rec_set.company_b_recommendation, key):
                        setattr(rec_set.company_b_recommendation, key, val)

        except Exception as e:
            logger.warning(f"LLM recommendation enhancement failed for {finding.provision}: {e}")