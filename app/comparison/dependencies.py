import logging
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from app.models.schemas import (
    ComparisonFinding, CrossDocumentRisk, LegalCategory, CompanyRole, Priority, Evidence
)
from app.llm.provider import get_llm_provider, LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RiskComponent:
    finding_id: str
    category: LegalCategory
    provision: str
    key_attribute: str
    value: Any


class CrossDocumentDependencyAnalyzer:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    def analyze_dependencies(
        self,
        findings: List[ComparisonFinding],
        comparison_id: str,
        deal_value: Optional[float] = None,
    ) -> List[CrossDocumentRisk]:
        risks = []

        indemnity_findings = [f for f in findings if f.category == LegalCategory.INDEMNIFICATION]
        litigation_findings = [f for f in findings if f.category == LegalCategory.LITIGATION]
        disclosure_findings = [f for f in findings if f.category == LegalCategory.DISCLOSURE_EXCEPTIONS]
        mae_findings = [f for f in findings if f.category == LegalCategory.MATERIAL_ADVERSE_EFFECT]
        rw_findings = [f for f in findings if f.category == LegalCategory.REPRESENTATIONS_WARRANTIES]

        risks.extend(self._analyze_indemnity_litigation_link(indemnity_findings, litigation_findings, comparison_id))
        risks.extend(self._analyze_indemnity_disclosure_link(indemnity_findings, disclosure_findings, comparison_id))
        risks.extend(self._analyze_rw_mae_link(rw_findings, mae_findings, comparison_id))
        risks.extend(self._analyze_cap_basket_link(indemnity_findings, comparison_id, deal_value))
        risks.extend(self._analyze_survival_claims_link(rw_findings, indemnity_findings, comparison_id))

        return risks

    def _analyze_indemnity_litigation_link(
        self,
        indemnity_findings: List[ComparisonFinding],
        litigation_findings: List[ComparisonFinding],
        comparison_id: str,
    ) -> List[CrossDocumentRisk]:
        risks = []

        cap_findings = [f for f in indemnity_findings if "cap" in f.provision.lower() or "liability" in f.provision.lower()]
        basket_findings = [f for f in indemnity_findings if "basket" in f.provision.lower()]

        for lit_finding in litigation_findings:
            lit_exposure = self._estimate_litigation_exposure(lit_finding)

            for cap_finding in cap_findings:
                cap_pct = self._get_cap_percentage(cap_finding)
                if cap_pct and lit_exposure:
                    risk = CrossDocumentRisk(
                        comparison_id=comparison_id,
                        risk_type="INDEMNITY_CAP_VS_LITIGATION_EXPOSURE",
                        severity=Priority.HIGH if lit_exposure > cap_pct else Priority.MEDIUM,
                        component_findings=[cap_finding.id, lit_finding.id],
                        description=f"Litigation exposure (${lit_exposure:,.0f}) may exceed indemnity cap ({cap_pct}% of purchase price)",
                        impact="If litigation exposure exceeds cap, uncovered losses fall on the indemnified party",
                        evidence_references=lit_finding.evidence_a + lit_finding.evidence_b + cap_finding.evidence_a + cap_finding.evidence_b,
                        confidence=0.7,
                    )
                    risks.append(risk)

        return risks

    def _analyze_indemnity_disclosure_link(
        self,
        indemnity_findings: List[ComparisonFinding],
        disclosure_findings: List[ComparisonFinding],
        comparison_id: str,
    ) -> List[CrossDocumentRisk]:
        risks = []

        for disc_finding in disclosure_findings:
            for ind_finding in indemnity_findings:
                if "exception" in str(ind_finding.differences).lower() or "carve" in str(ind_finding.differences).lower():
                    risk = CrossDocumentRisk(
                        comparison_id=comparison_id,
                        risk_type="INDEMNITY_EXCEPTION_VS_DISCLOSURE",
                        severity=Priority.HIGH,
                        component_findings=[ind_finding.id, disc_finding.id],
                        description="Indemnity exceptions may be qualified by disclosure schedule, creating coverage gaps",
                        impact="Disclosed matters excluded from indemnification may leave buyer unprotected for known risks",
                        evidence_references=ind_finding.evidence_a + ind_finding.evidence_b + disc_finding.evidence_a + disc_finding.evidence_b,
                        confidence=0.6,
                    )
                    risks.append(risk)

        return risks

    def _analyze_rw_mae_link(
        self,
        rw_findings: List[ComparisonFinding],
        mae_findings: List[ComparisonFinding],
        comparison_id: str,
    ) -> List[CrossDocumentRisk]:
        risks = []

        for rw_finding in rw_findings:
            for mae_finding in mae_findings:
                rw_exceptions = set()
                mae_exceptions = set()

                if rw_finding.company_a_position:
                    rw_exceptions.update(rw_finding.company_a_position.exception)
                if rw_finding.company_b_position:
                    rw_exceptions.update(rw_finding.company_b_position.exception)

                if mae_finding.company_a_position:
                    mae_exceptions.update(mae_finding.company_a_position.exception)
                if mae_finding.company_b_position:
                    mae_exceptions.update(mae_finding.company_b_position.exception)

                overlap = rw_exceptions & mae_exceptions
                if overlap:
                    risk = CrossDocumentRisk(
                        comparison_id=comparison_id,
                        risk_type="RW_EXCEPTION_OVERLAPS_MAE_CARVEOUT",
                        severity=Priority.MEDIUM,
                        component_findings=[rw_finding.id, mae_finding.id],
                        description=f"R&W exceptions overlap with MAE carve-outs: {list(overlap)}",
                        impact="Same exceptions apply to both R&W breaches and MAE determination, potentially narrowing both protections",
                        evidence_references=rw_finding.evidence_a + rw_finding.evidence_b + mae_finding.evidence_a + mae_finding.evidence_b,
                        confidence=0.65,
                    )
                    risks.append(risk)

        return risks

    def _analyze_cap_basket_link(
        self,
        indemnity_findings: List[ComparisonFinding],
        comparison_id: str,
        deal_value: Optional[float] = None,
    ) -> List[CrossDocumentRisk]:
        risks = []

        cap_findings = [f for f in indemnity_findings if "cap" in f.provision.lower()]
        basket_findings = [f for f in indemnity_findings if "basket" in f.provision.lower()]

        for cap_finding in cap_findings:
            for basket_finding in basket_findings:
                cap_pct = self._get_cap_percentage(cap_finding)
                basket_amt = self._get_basket_amount(basket_finding)

                if cap_pct and basket_amt:
                    if deal_value and deal_value > 0:
                        cap_amount = deal_value * (cap_pct / 100)
                        ratio = basket_amt / cap_amount if cap_amount > 0 else 0
                        description = (
                            f"Basket (${basket_amt:,.0f}) to Cap ({cap_pct}% of ${deal_value:,.0f} = "
                            f"${cap_amount:,.0f}) ratio: {ratio:.1%}"
                        )
                        impact = (
                            f"Basket represents {ratio:.1%} of maximum indemnity cap. "
                            f"Gap between basket and cap: ${cap_amount - basket_amt:,.0f}."
                        )
                        severity = Priority.MEDIUM if ratio < 0.05 else Priority.LOW
                        confidence = 0.8
                    else:
                        ratio = None
                        description = (
                            f"Basket (${basket_amt:,.0f}) to Cap ({cap_pct}%) - "
                            f"Purchase price context unavailable for ratio calculation"
                        )
                        impact = (
                            "Cannot compute basket-to-cap ratio without purchase price. "
                            "Ratio would be: basket / (cap% × purchase_price). "
                            "Provide deal value to enable this analysis."
                        )
                        severity = Priority.LOW
                        confidence = 0.3

                    risk = CrossDocumentRisk(
                        comparison_id=comparison_id,
                        risk_type="CAP_BASKET_RATIO",
                        severity=severity,
                        component_findings=[cap_finding.id, basket_finding.id],
                        description=description,
                        impact=impact,
                        evidence_references=cap_finding.evidence_a + cap_finding.evidence_b + basket_finding.evidence_a + basket_finding.evidence_b,
                        confidence=confidence,
                    )
                    risks.append(risk)

        return risks

    def _analyze_survival_claims_link(
        self,
        rw_findings: List[ComparisonFinding],
        indemnity_findings: List[ComparisonFinding],
        comparison_id: str,
    ) -> List[CrossDocumentRisk]:
        risks = []

        survival_findings = [f for f in rw_findings if "survival" in f.provision.lower()]

        for surv_finding in survival_findings:
            dur_a = surv_finding.company_a_position.duration if surv_finding.company_a_position else None
            dur_b = surv_finding.company_b_position.duration if surv_finding.company_b_position else None

            for ind_finding in indemnity_findings:
                risk = CrossDocumentRisk(
                    comparison_id=comparison_id,
                    risk_type="SURVIVAL_PERIOD_VS_INDEMNITY_CLAIMS",
                    severity=Priority.MEDIUM,
                    component_findings=[surv_finding.id, ind_finding.id],
                    description=f"Survival period ({dur_a or dur_b or 'unknown'}) limits window for indemnity claims under {ind_finding.provision}",
                    impact="Claims arising after survival period expires may be barred even if indemnity cap would otherwise cover them",
                    evidence_references=surv_finding.evidence_a + surv_finding.evidence_b + ind_finding.evidence_a + ind_finding.evidence_b,
                    confidence=0.7,
                )
                risks.append(risk)

        return risks

    def _estimate_litigation_exposure(self, finding: ComparisonFinding) -> Optional[float]:
        if finding.company_a_position and finding.company_a_position.amount:
            return finding.company_a_position.amount
        if finding.company_b_position and finding.company_b_position.amount:
            return finding.company_b_position.amount
        return None

    def _get_cap_percentage(self, finding: ComparisonFinding) -> Optional[float]:
        if finding.company_a_position and finding.company_a_position.percentage:
            return finding.company_a_position.percentage
        if finding.company_b_position and finding.company_b_position.percentage:
            return finding.company_b_position.percentage
        return None

    def _get_basket_amount(self, finding: ComparisonFinding) -> Optional[float]:
        if finding.company_a_position and finding.company_a_position.amount:
            return finding.company_a_position.amount
        if finding.company_b_position and finding.company_b_position.amount:
            return finding.company_b_position.amount
        return None

    async def analyze_dependencies_with_llm(
        self,
        findings: List[ComparisonFinding],
    ) -> List[CrossDocumentRisk]:
        risk_findings = [f for f in findings if f.classification in ["MATERIAL_ASYMMETRY", "POTENTIAL_ASYMMETRY", "PRESENCE_ABSENCE", "CONFLICT"]]

        if len(risk_findings) < 2:
            return []

        prompt = f"""Identify interconnected legal risks across these M&A findings. Look for cross-document dependencies where multiple provisions interact to create compound risk.

Findings:
{self._format_findings_for_prompt(risk_findings)}

Identify risks of these types:
- INDEMNITY_CAP_VS_LITIGATION_EXPOSURE
- INDEMNITY_EXCEPTION_VS_DISCLOSURE
- RW_EXCEPTION_OVERLAPS_MAE_CARVEOUT
- CAP_BASKET_RATIO
- SURVIVAL_PERIOD_VS_INDEMNITY_CLAIMS
- INTERCONNECTED_EXPOSURE (custom)

Respond with JSON array of risks:
[
  {{
    "risk_type": "...",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "component_finding_ids": ["finding_id1", "finding_id2"],
    "description": "...",
    "impact": "...",
    "confidence": 0.0-1.0
  }}
]"""

        schema = {
            "type": "object",
            "properties": {
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "risk_type": {"type": "string"},
                            "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                            "component_finding_ids": {"type": "array", "items": {"type": "string"}},
                            "description": {"type": "string"},
                            "impact": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["risk_type", "severity", "component_finding_ids", "description", "impact", "confidence"],
                    },
                }
            },
            "required": ["risks"],
        }

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt="You are an M&A lawyer identifying interconnected legal risks across contract provisions. Find compound risks where multiple provisions interact.",
                schema=schema,
                temperature=0.1,
                max_tokens=2048,
            )

            llm_risks = []
            for r in result.get("risks", []):
                finding_map = {f.id: f for f in risk_findings}
                evidence = []
                for fid in r.get("component_finding_ids", []):
                    if fid in finding_map:
                        f = finding_map[fid]
                        evidence.extend(f.evidence_a)
                        evidence.extend(f.evidence_b)

                llm_risks.append(CrossDocumentRisk(
                    risk_type=r["risk_type"],
                    severity=Priority(r["severity"]),
                    component_findings=r["component_finding_ids"],
                    description=r["description"],
                    impact=r["impact"],
                    evidence_references=evidence,
                    confidence=r["confidence"],
                ))

            return llm_risks

        except Exception as e:
            logger.warning(f"LLM dependency analysis failed: {e}")
            return []

    def _format_findings_for_prompt(self, findings: List[ComparisonFinding]) -> str:
        lines = []
        for f in findings:
            pos_a = f.company_a_position
            pos_b = f.company_b_position
            lines.append(f"Finding {f.id}: {f.provision} ({f.category.value})")
            lines.append(f"  Classification: {f.classification.value}")
            if pos_a:
                lines.append(f"  Company A: {pos_a.percentage}% {pos_a.unit or ''} | {pos_a.amount} | {pos_a.duration} | Exceptions: {pos_a.exception}")
            if pos_b:
                lines.append(f"  Company B: {pos_b.percentage}% {pos_b.unit or ''} | {pos_b.amount} | {pos_b.duration} | Exceptions: {pos_b.exception}")
            lines.append("")
        return "\n".join(lines)