import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from app.models.schemas import (
    LegalPosition, LegalPositionMatch, ComparisonFinding, DifferenceDetail,
    AsymmetryClassification, LegalCategory, CompanyRole, Evidence,
    DurationNormalized, parse_duration, compare_durations
)
from app.llm.provider import get_llm_provider, LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ComparisonContext:
    company_a_role: CompanyRole
    company_b_role: CompanyRole


class ComparisonEngine:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()
        self.settings = get_settings()

    def compare_matched_positions(
        self,
        matches: List[LegalPositionMatch],
        context: ComparisonContext,
        comparison_id: str,
    ) -> List[ComparisonFinding]:
        findings = []

        for match in matches:
            if match.match_status in [MatchStatus.MATCHED, MatchStatus.PARTIAL, MatchStatus.REQUIRES_REVIEW]:
                finding = self._compare_positions(match, context, comparison_id)
                findings.append(finding)
            elif match.match_status == MatchStatus.UNMATCHED:
                if match.company_a_position and not match.company_b_position:
                    finding = self._create_presence_absence_finding(
                        match.company_a_position, None, "company_a_only", context, comparison_id
                    )
                    findings.append(finding)
                elif match.company_b_position and not match.company_a_position:
                    finding = self._create_presence_absence_finding(
                        None, match.company_b_position, "company_b_only", context, comparison_id
                    )
                    findings.append(finding)

        return findings

    def _compare_positions(
        self,
        match: LegalPositionMatch,
        context: ComparisonContext,
        comparison_id: str,
    ) -> ComparisonFinding:
        pos_a = match.company_a_position
        pos_b = match.company_b_position

        differences = self._compute_differences(pos_a, pos_b)
        classification, reason = self._classify_asymmetry(pos_a, pos_b, differences, context)
        beneficiary, dimension, adv_conf, adv_expl = self._determine_advantage(pos_a, pos_b, differences, context)

        finding = ComparisonFinding(
            comparison_id=comparison_id,
            category=pos_a.category if pos_a else pos_b.category,
            provision=pos_a.provision_name if pos_a else pos_b.provision_name,
            subcategory=pos_a.subcategory if pos_a else pos_b.subcategory,
            company_a_position=pos_a,
            company_b_position=pos_b,
            differences=differences,
            classification=classification,
            classification_reason=reason,
            beneficiary=beneficiary,
            affected_dimension=dimension,
            advantage_confidence=adv_conf,
            advantage_explanation=adv_expl,
            evidence_a=[pos_a.evidence] if pos_a else [],
            evidence_b=[pos_b.evidence] if pos_b else [],
            comparison_confidence=match.match_confidence,
            materiality_confidence=self._compute_materiality_confidence(classification, differences),
        )

        return finding

    def _compute_differences(
        self,
        pos_a: Optional[LegalPosition],
        pos_b: Optional[LegalPosition],
    ) -> List[DifferenceDetail]:
        differences = []

        if not pos_a and not pos_b:
            return differences

        if not pos_a:
            return [DifferenceDetail(
                attribute="presence",
                company_a_value=None,
                company_b_value="present",
                difference="absent vs present",
                direction="company_b_only",
            )]

        if not pos_b:
            return [DifferenceDetail(
                attribute="presence",
                company_a_value="present",
                company_b_value=None,
                difference="present vs absent",
                direction="company_a_only",
            )]

        attrs_to_compare = [
            ("percentage", "percentage", lambda x: x.percentage),
            ("amount", "amount", lambda x: x.amount),
            ("unit", "unit", lambda x: x.unit),
            ("threshold", "threshold", lambda x: x.threshold),
            ("obligation_right", "obligation_right", lambda x: x.obligation_right),
        ]

        for attr_name, display_name, getter in attrs_to_compare:
            val_a = getter(pos_a)
            val_b = getter(pos_b)

            if val_a != val_b:
                diff = DifferenceDetail(
                    attribute=display_name,
                    company_a_value=val_a,
                    company_b_value=val_b,
                )

                if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                    diff.difference = abs(val_a - val_b)
                    diff.absolute_difference = abs(val_a - val_b)
                    diff.direction = "company_a_higher" if val_a > val_b else "company_b_higher"

                differences.append(diff)

        dur_a = parse_duration(pos_a.duration) if pos_a.duration else DurationNormalized(parse_status="NOT_PROVIDED")
        dur_b = parse_duration(pos_b.duration) if pos_b.duration else DurationNormalized(parse_status="NOT_PROVIDED")
        
        if pos_a.duration != pos_b.duration:
            dur_comparison = compare_durations(dur_a, dur_b)
            diff = DifferenceDetail(
                attribute="duration",
                company_a_value=pos_a.duration,
                company_b_value=pos_b.duration,
                difference=dur_comparison,
            )
            if dur_comparison and dur_comparison.get("difference_months") is not None:
                diff.absolute_difference = abs(dur_comparison["difference_months"])
                diff.direction = "company_a_higher" if dur_comparison["difference_months"] < 0 else "company_b_higher"
            differences.append(diff)

        list_attrs = [
            ("condition", "conditions", lambda x: x.condition),
            ("exception", "exceptions", lambda x: x.exception),
            ("qualifier", "qualifiers", lambda x: x.qualifier),
            ("consequence", "consequences", lambda x: x.consequence),
        ]

        for attr_name, display_name, getter in list_attrs:
            list_a = set(getter(pos_a) or [])
            list_b = set(getter(pos_b) or [])

            if list_a != list_b:
                diff = DifferenceDetail(
                    attribute=display_name,
                    company_a_value=list(list_a),
                    company_b_value=list(list_b),
                    difference=f"Only in A: {list_a - list_b}; Only in B: {list_b - list_a}",
                    direction="different_sets",
                )
                differences.append(diff)

        return differences

    def _classify_asymmetry(
        self,
        pos_a: Optional[LegalPosition],
        pos_b: Optional[LegalPosition],
        differences: List[DifferenceDetail],
        context: ComparisonContext,
    ) -> Tuple[AsymmetryClassification, str]:
        if not pos_a and not pos_b:
            return AsymmetryClassification.REQUIRES_REVIEW, "No positions to compare"

        if not pos_a or not pos_b:
            return AsymmetryClassification.PRESENCE_ABSENCE, "Provision exists in only one party's documents"

        if not differences:
            return AsymmetryClassification.NO_MATERIAL_DIFFERENCE, "No material differences detected"

        high_priority_categories = {
            LegalCategory.INDEMNIFICATION,
            LegalCategory.MATERIAL_ADVERSE_EFFECT,
            LegalCategory.TERMINATION_RIGHTS,
            LegalCategory.CLOSING_CONDITIONS,
            LegalCategory.REPRESENTATIONS_WARRANTIES,
            LegalCategory.MATERIAL_CONTRACTS,
            LegalCategory.LITIGATION,
            LegalCategory.CHANGE_OF_CONTROL,
            LegalCategory.DISCLOSURE_EXCEPTIONS,
        }

        is_high_priority = pos_a.category in high_priority_categories or pos_b.category in high_priority_categories

        has_numerical_diff = any(
            d.absolute_difference is not None and d.absolute_difference > 0
            for d in differences
        )

        has_list_diff = any(
            d.attribute in ["conditions", "exceptions", "qualifiers", "consequences"]
            for d in differences
        )

        has_presence_absence = any(
            d.attribute == "presence"
            for d in differences
        )

        if has_presence_absence:
            return AsymmetryClassification.PRESENCE_ABSENCE, "Provision present in only one party's documents"

        if is_high_priority and has_numerical_diff:
            max_diff = max(d.absolute_difference or 0 for d in differences)
            if max_diff > 5:
                return AsymmetryClassification.MATERIAL_ASYMMETRY, f"Significant numerical difference in high-priority category: {max_diff}"
            elif max_diff > 1:
                return AsymmetryClassification.POTENTIAL_ASYMMETRY, f"Moderate numerical difference in high-priority category: {max_diff}"
            else:
                return AsymmetryClassification.MINOR_DIFFERENCE, f"Minor numerical difference in high-priority category: {max_diff}"

        if is_high_priority and has_list_diff:
            return AsymmetryClassification.MATERIAL_ASYMMETRY, "Difference in conditions/exceptions/qualifiers in high-priority category"

        if has_numerical_diff:
            return AsymmetryClassification.POTENTIAL_ASYMMETRY, "Numerical difference in standard category"

        if has_list_diff:
            return AsymmetryClassification.MINOR_DIFFERENCE, "Difference in conditions/exceptions/qualifiers"

        return AsymmetryClassification.INFORMATIONAL, "Minor structural difference"

    def _determine_advantage(
        self,
        pos_a: Optional[LegalPosition],
        pos_b: Optional[LegalPosition],
        differences: List[DifferenceDetail],
        context: ComparisonContext,
    ) -> Tuple[Optional[CompanyRole], Optional[str], float, str]:
        if not pos_a or not pos_b:
            return None, None, 0.0, "Cannot determine advantage without both positions"

        if not differences:
            return None, None, 0.0, "No differences to assess advantage"

        category = pos_a.category
        conf = 0.5
        explanation = ""

        if category == LegalCategory.INDEMNIFICATION:
            cap_diff = next((d for d in differences if d.attribute == "percentage" and "cap" in (pos_a.provision_name + pos_b.provision_name).lower()), None)
            if cap_diff and cap_diff.absolute_difference is not None:
                # For a seller/target indemnity cap, a higher cap generally
                # increases the claimant's recovery ceiling; a lower cap generally
                # protects the obligor. Determine those roles from the transaction,
                # not from whether A or B has the larger number.
                claimant_roles = [r for r in [context.company_a_role, context.company_b_role]
                                  if r in [CompanyRole.BUYER, CompanyRole.ACQUIRER]]
                obligor_roles = [r for r in [context.company_a_role, context.company_b_role]
                                 if r in [CompanyRole.SELLER, CompanyRole.TARGET]]
                higher_company = "A" if cap_diff.direction == "company_a_higher" else "B"
                higher_value = cap_diff.company_a_value if higher_company == "A" else cap_diff.company_b_value
                lower_value = cap_diff.company_b_value if higher_company == "A" else cap_diff.company_a_value
                if claimant_roles and obligor_roles:
                    beneficiary = claimant_roles[0]
                    return beneficiary, "recovery_protection", 0.8, (
                        f"Company {higher_company} has the higher liability cap "
                        f"({higher_value}% vs {lower_value}%). A higher cap generally "
                        f"increases the {beneficiary.value}'s potential recovery ceiling "
                        f"and correspondingly increases seller/target exposure."
                    )
                return None, "recovery_protection", 0.3, "Liability-cap direction requires identifiable buyer/acquirer and seller/target roles"

                return None, "recovery_protection", 0.3, "Liability-cap direction requires identifiable obligor and claimant roles"

            basket_diff = next((d for d in differences if d.attribute == "amount" and "basket" in (pos_a.provision_name + pos_b.provision_name).lower()), None)
            if basket_diff and basket_diff.absolute_difference is not None:
                higher_company = "A" if basket_diff.direction == "company_a_higher" else "B"
                higher_value = basket_diff.company_a_value if higher_company == "A" else basket_diff.company_b_value
                lower_value = basket_diff.company_b_value if higher_company == "A" else basket_diff.company_a_value
                seller_roles = [r for r in [context.company_a_role, context.company_b_role]
                                if r in [CompanyRole.SELLER, CompanyRole.TARGET]]
                buyer_roles = [r for r in [context.company_a_role, context.company_b_role]
                               if r in [CompanyRole.BUYER, CompanyRole.ACQUIRER]]
                if seller_roles:
                    beneficiary = seller_roles[0]
                    return beneficiary, "indemnification_threshold", 0.7, (
                        f"Company {higher_company} has the higher basket threshold "
                        f"(${higher_value:,.0f} vs ${lower_value:,.0f}). A higher basket "
                        f"generally delays recovery and favors the {beneficiary.value}/obligor."
                    )
                if buyer_roles:
                    beneficiary = buyer_roles[0]
                    return beneficiary, "indemnification_threshold", 0.5, (
                        f"Company {higher_company} has the higher basket threshold "
                        f"(${higher_value:,.0f} vs ${lower_value:,.0f}); without an identified "
                        f"seller/target obligor, buyer-side impact requires review."
                    )
                return None, "indemnification_threshold", 0.3, "Basket direction requires identifiable transaction roles"

        if category == LegalCategory.REPRESENTATIONS_WARRANTIES:
            duration_diff = next((d for d in differences if d.attribute == "duration"), None)
            if duration_diff and duration_diff.difference and isinstance(duration_diff.difference, dict):
                diff_months = duration_diff.difference.get("difference_months")
                if diff_months is not None:
                    claimant_roles = [r for r in [context.company_a_role, context.company_b_role]
                                      if r in [CompanyRole.BUYER, CompanyRole.ACQUIRER]]
                    obligor_roles = [r for r in [context.company_a_role, context.company_b_role]
                                     if r in [CompanyRole.SELLER, CompanyRole.TARGET]]
                    beneficiary = claimant_roles[0] if claimant_roles else None
                    if diff_months > 0:
                        longer = f"Company B ({duration_diff.difference.get('company_b_months'):.1f} months)"
                    else:
                        longer = f"Company A ({duration_diff.difference.get('company_a_months'):.1f} months)"
                    if beneficiary:
                        return beneficiary, "survival_period", 0.7, (
                            f"{longer} has the longer survival period; a longer claim window "
                            f"generally favors the {beneficiary.value} and increases seller/target exposure."
                        )
                    if obligor_roles:
                        return obligor_roles[0], "survival_period", 0.4, (
                            f"{longer} has the longer survival period; claimant-side impact "
                            f"should be confirmed against the underlying indemnity structure."
                        )
                    return None, "survival_period", 0.3, "Survival-period direction requires identifiable transaction roles"
            elif duration_diff:
                return None, "survival_period", 0.5, "Different survival periods affect claim windows"

        if category == LegalCategory.MATERIAL_ADVERSE_EFFECT:
            exception_diff = next((d for d in differences if d.attribute == "exceptions"), None)
            if exception_diff:
                return None, "mae_scope", 0.6, "Different MAE carve-outs affect termination risk"

        if category == LegalCategory.TERMINATION_RIGHTS:
            condition_diff = next((d for d in differences if d.attribute == "conditions"), None)
            if condition_diff:
                return None, "termination_flexibility", 0.6, "Different termination conditions affect deal certainty"

        return None, None, 0.3, "Advantage not clearly determinable from structured data"

    def _compute_materiality_confidence(self, classification: AsymmetryClassification, differences: List[DifferenceDetail]) -> float:
        base_confidence = {
            AsymmetryClassification.MATERIAL_ASYMMETRY: 0.8,
            AsymmetryClassification.POTENTIAL_ASYMMETRY: 0.6,
            AsymmetryClassification.PRESENCE_ABSENCE: 0.7,
            AsymmetryClassification.MINOR_DIFFERENCE: 0.5,
            AsymmetryClassification.INFORMATIONAL: 0.4,
            AsymmetryClassification.NO_MATERIAL_DIFFERENCE: 0.9,
            AsymmetryClassification.CONFLICT: 0.7,
            AsymmetryClassification.REQUIRES_REVIEW: 0.3,
        }.get(classification, 0.5)

        has_numerical = any(d.absolute_difference is not None for d in differences)
        has_lists = any(d.attribute in ["conditions", "exceptions", "qualifiers", "consequences"] for d in differences)

        if has_numerical:
            base_confidence += 0.1
        if has_lists:
            base_confidence += 0.05

        return min(base_confidence, 1.0)

    def _create_presence_absence_finding(
        self,
        pos_a: Optional[LegalPosition],
        pos_b: Optional[LegalPosition],
        direction: str,
        context: ComparisonContext,
        comparison_id: str,
    ) -> ComparisonFinding:
        pos = pos_a if pos_a else pos_b

        return ComparisonFinding(
            comparison_id=comparison_id,
            category=pos.category if pos else LegalCategory.INDEMNIFICATION,
            provision=pos.provision_name if pos else "Unknown",
            subcategory=pos.subcategory if pos else None,
            company_a_position=pos_a,
            company_b_position=pos_b,
            differences=[DifferenceDetail(
                attribute="presence",
                company_a_value="present" if pos_a else None,
                company_b_value="present" if pos_b else None,
                difference=f"Only present in {'Company A' if pos_a else 'Company B'}",
                direction=direction,
            )],
            classification=AsymmetryClassification.PRESENCE_ABSENCE,
            classification_reason=f"Provision exists only in {'Company A' if pos_a else 'Company B'} documents",
            evidence_a=[pos_a.evidence] if pos_a else [],
            evidence_b=[pos_b.evidence] if pos_b else [],
            comparison_confidence=0.9,
            materiality_confidence=0.7,
            requires_lawyer_review=True,
        )


class MatchStatus:
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    UNMATCHED = "UNMATCHED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"