#!/usr/bin/env python
"""
DISCLAI Evaluation Framework - Gold Test Cases
Tests the 10 deterministic test cases defined in Phase 3 requirements.
"""
import os
import sys
import tempfile
import fitz
from typing import List, Dict, Any
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import (
    LegalPosition, Evidence, LegalCategory, PartyRole, ExtractionStatus,
    AsymmetryClassification, DifferenceDetail, CompanyRole
)
from app.comparison.engine import ComparisonEngine, ComparisonContext
from app.comparison.matcher import ProvisionMatcher
from app.comparison.dependencies import CrossDocumentDependencyAnalyzer
from app.comparison.disclosure import DisclosureReconciliationService
from app.models.schemas import DurationNormalized, parse_duration, compare_durations
from app.llm.provider import MockLLMProvider


@dataclass
class TestCase:
    name: str
    description: str
    expected: Dict[str, Any]


def create_position(
    category: LegalCategory,
    provision_name: str,
    party: PartyRole,
    percentage: float = None,
    amount: float = None,
    duration: str = None,
    exceptions: List[str] = None,
    conditions: List[str] = None,
    evidence_text: str = "Evidence text",
) -> LegalPosition:
    return LegalPosition(
        category=category,
        provision_name=provision_name,
        party=party,
        obligation_right="test",
        percentage=percentage,
        amount=amount,
        duration=duration,
        exception=exceptions or [],
        condition=conditions or [],
        evidence=Evidence(
            document_id="doc-test",
            page_number=1,
            section_number="1.1",
            heading="Test",
            text=evidence_text,
            char_start=0,
            char_end=len(evidence_text),
        ),
        confidence=0.9,
        status=ExtractionStatus.VERIFIED,
    )


def run_gold_tests():
    print("=" * 70)
    print("DISCLAI Gold Test Cases - Evaluation Framework")
    print("=" * 70)
    
    engine = ComparisonEngine(llm=MockLLMProvider())
    matcher = ProvisionMatcher(llm=MockLLMProvider())
    dep_analyzer = CrossDocumentDependencyAnalyzer(llm=MockLLMProvider())
    disc_service = DisclosureReconciliationService(llm=MockLLMProvider())
    
    context = ComparisonContext(
        company_a_role=CompanyRole.SELLER,
        company_b_role=CompanyRole.BUYER,
    )
    
    results = []
    
    # CASE 1: A = 10%, B = 20% -> numerical asymmetry
    print("\n[CASE 1] Numerical Asymmetry: Cap 10% vs 20%")
    pos_a = create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=10.0)
    pos_b = create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=20.0)
    
    match = matcher._compute_match_score(pos_a, pos_b)
    finding = engine._compare_positions(
        type('Match', (), {'company_a_position': pos_a, 'company_b_position': pos_b, 
                          'match_status': 'MATCHED', 'match_confidence': 1.0, 'match_reason': '', 'matched_attributes': []})(),
        context, "test"
    )
    
    passed = finding.classification == AsymmetryClassification.MATERIAL_ASYMMETRY or finding.classification == AsymmetryClassification.POTENTIAL_ASYMMETRY
    diff = next((d for d in finding.differences if d.attribute == "percentage"), None)
    passed = passed and diff and abs(diff.absolute_difference - 10.0) < 0.01
    
    results.append(("CASE 1: Numerical asymmetry (10% vs 20%)", passed))
    print(f"  Classification: {finding.classification.value}")
    print(f"  Difference: {diff.absolute_difference if diff else 'N/A'}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    
    # CASE 2: A = 10%, B = 10% -> no material numerical asymmetry
    print("\n[CASE 2] No Material Numerical Asymmetry: Cap 10% vs 10%")
    pos_a2 = create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=10.0)
    pos_b2 = create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=10.0)
    
    finding2 = engine._compare_positions(
        type('Match', (), {'company_a_position': pos_a2, 'company_b_position': pos_b2,
                          'match_status': 'MATCHED', 'match_confidence': 1.0, 'match_reason': '', 'matched_attributes': []})(),
        context, "test"
    )
    
    passed2 = finding2.classification == AsymmetryClassification.NO_MATERIAL_DIFFERENCE
    results.append(("CASE 2: No material asymmetry (10% vs 10%)", passed2))
    print(f"  Classification: {finding2.classification.value}")
    print(f"  Result: {'PASS' if passed2 else 'FAIL'}")
    
    # CASE 3: A has provision, B lacks provision -> presence/absence asymmetry
    print("\n[CASE 3] Presence/Absence Asymmetry")
    pos_a3 = create_position(LegalCategory.INDEMNIFICATION, "Basket", PartyRole.SELLER, amount=500000)
    pos_b3 = None
    
    finding3 = engine._create_presence_absence_finding(pos_a3, None, "company_a_only", context, "test")
    
    passed3 = finding3.classification == AsymmetryClassification.PRESENCE_ABSENCE
    results.append(("CASE 3: Presence/absence asymmetry", passed3))
    print(f"  Classification: {finding3.classification.value}")
    print(f"  Result: {'PASS' if passed3 else 'FAIL'}")
    
    # CASE 4: Duration 18 months vs 24 months -> 6 month difference
    print("\n[CASE 4] Duration Normalization: 18 months vs 24 months")
    dur_a = parse_duration("18 months")
    dur_b = parse_duration("24 months")
    comparison = compare_durations(dur_a, dur_b)
    
    passed4 = comparison and comparison["difference_months"] == 6.0
    results.append(("CASE 4: Duration normalization (18mo vs 24mo = 6mo diff)", passed4))
    print(f"  A: {dur_a.normalized_months} months, B: {dur_b.normalized_months} months")
    print(f"  Difference: {comparison['difference_months'] if comparison else 'N/A'} months")
    print(f"  Result: {'PASS' if passed4 else 'FAIL'}")
    
    # CASE 5: Same legal meaning, different wording -> equivalent provision match
    print("\n[CASE 5] Equivalent Provision Match (different wording)")
    pos_a5 = create_position(LegalCategory.INDEMNIFICATION, "Liability Cap", PartyRole.SELLER, percentage=15.0,
                              evidence_text="Seller's aggregate liability shall not exceed 15% of Purchase Price")
    pos_b5 = create_position(LegalCategory.INDEMNIFICATION, "Limitation of Liability", PartyRole.SELLER, percentage=15.0,
                              evidence_text="The total liability of Seller is capped at 15% of the Purchase Price")
    
    score, reason, attrs = matcher._compute_match_score(pos_a5, pos_b5)
    status = matcher._determine_match_status(score)
    
    passed5 = status.value in ["MATCHED", "PARTIAL"] and score >= 0.4
    results.append(("CASE 5: Equivalent provision match (different wording)", passed5))
    print(f"  Match Score: {score:.2f}, Status: {status.value}")
    print(f"  Result: {'PASS' if passed5 else 'FAIL'}")
    
    # CASE 6: Different exceptions -> material difference
    print("\n[CASE 6] Different Exceptions")
    pos_a6 = create_position(LegalCategory.MATERIAL_ADVERSE_EFFECT, "MAE Definition", PartyRole.UNKNOWN,
                              exceptions=["general economic conditions", "industry changes"])
    pos_b6 = create_position(LegalCategory.MATERIAL_ADVERSE_EFFECT, "MAE Definition", PartyRole.UNKNOWN,
                              exceptions=["general economic conditions", "industry changes", "pandemics", "regulatory changes"])
    
    finding6 = engine._compare_positions(
        type('Match', (), {'company_a_position': pos_a6, 'company_b_position': pos_b6,
                          'match_status': 'MATCHED', 'match_confidence': 1.0, 'match_reason': '', 'matched_attributes': []})(),
        context, "test"
    )
    
    exception_diff = next((d for d in finding6.differences if d.attribute == "exceptions"), None)
    passed6 = finding6.classification in [AsymmetryClassification.MATERIAL_ASYMMETRY, AsymmetryClassification.POTENTIAL_ASYMMETRY] and exception_diff is not None
    results.append(("CASE 6: Different exceptions -> material difference", passed6))
    print(f"  Classification: {finding6.classification.value}")
    print(f"  Exception diff: {exception_diff.difference if exception_diff else 'N/A'}")
    print(f"  Result: {'PASS' if passed6 else 'FAIL'}")
    
    # CASE 7: Litigation + Indemnity Cap + Disclosure -> cross-document dependency
    print("\n[CASE 7] Cross-Document Dependency: Litigation + Cap + Disclosure")
    findings = [
        engine._compare_positions(
            type('Match', (), {'company_a_position': create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=10.0),
                              'company_b_position': create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=10.0),
                              'match_status': 'MATCHED', 'match_confidence': 1.0, 'match_reason': '', 'matched_attributes': []})(),
            context, "test"
        ),
        engine._compare_positions(
            type('Match', (), {'company_a_position': create_position(LegalCategory.LITIGATION, "Pending Litigation", PartyRole.TARGET, amount=5000000),
                              'company_b_position': create_position(LegalCategory.LITIGATION, "Pending Litigation", PartyRole.TARGET, amount=5000000),
                              'match_status': 'MATCHED', 'match_confidence': 1.0, 'match_reason': '', 'matched_attributes': []})(),
            context, "test"
        ),
    ]
    
    risks = dep_analyzer.analyze_dependencies(findings, "test", deal_value=50000000)
    cap_lit_risks = [r for r in risks if r.risk_type == "INDEMNITY_CAP_VS_LITIGATION_EXPOSURE"]
    
    passed7 = len(cap_lit_risks) > 0
    results.append(("CASE 7: Cross-document dependency (Litigation + Cap)", passed7))
    print(f"  Risks found: {len(risks)}")
    for r in cap_lit_risks:
        print(f"    - {r.risk_type} ({r.severity.value}): {r.description}")
    print(f"  Result: {'PASS' if passed7 else 'FAIL'}")
    
    # CASE 8: Disclosure Schedule contradicts source evidence
    print("\n[CASE 8] Disclosure Inconsistency")
    spa_pos = create_position(LegalCategory.REPRESENTATIONS_WARRANTIES, "No Undisclosed Liabilities", PartyRole.SELLER,
                               evidence_text="Target has no liabilities except as disclosed in Schedule 2.1(c)")
    disc_pos = create_position(LegalCategory.DISCLOSURE_EXCEPTIONS, "Schedule 2.1(c)", PartyRole.SELLER,
                                evidence_text="Schedule 2.1(c): None.")
    data_pos = create_position(LegalCategory.LITIGATION, "ABC v. Target", PartyRole.TARGET,
                                evidence_text="Pending litigation: ABC Corp v. Target Inc. for $2M breach of contract")
    
    issues = disc_service.reconcile_disclosures([spa_pos], [disc_pos], [data_pos], "test")
    
    passed8 = len(issues) > 0 and any(i.issue_type == "POTENTIAL_MISSING_LITIGATION_DISCLOSURE" for i in issues)
    results.append(("CASE 8: Disclosure inconsistency (Schedule says None, Data Room has Litigation)", passed8))
    print(f"  Issues found: {len(issues)}")
    for i in issues:
        print(f"    - {i.issue_type} ({i.severity.value}): {i.description}")
    print(f"  Result: {'PASS' if passed8 else 'FAIL'}")
    
    # CASE 9: Insufficient evidence -> REQUIRES_REVIEW
    print("\n[CASE 9] Insufficient Evidence -> REQUIRES_REVIEW")
    dur_a9 = parse_duration("unknown period")
    dur_b9 = parse_duration("some time")
    comparison9 = compare_durations(dur_a9, dur_b9)
    
    passed9 = comparison9 and comparison9["status"] == "REQUIRES_REVIEW"
    results.append(("CASE 9: Insufficient evidence -> REQUIRES_REVIEW", passed9))
    print(f"  A parse status: {dur_a9.parse_status}, B parse status: {dur_b9.parse_status}")
    print(f"  Comparison status: {comparison9['status'] if comparison9 else 'N/A'}")
    print(f"  Result: {'PASS' if passed9 else 'FAIL'}")
    
    # CASE 10: Missing purchase price -> no fabricated cap/basket ratio
    print("\n[CASE 10] Missing Purchase Price -> No Fabricated Ratio")
    findings10 = [
        engine._compare_positions(
            type('Match', (), {'company_a_position': create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=10.0),
                              'company_b_position': create_position(LegalCategory.INDEMNIFICATION, "General Liability Cap", PartyRole.SELLER, percentage=10.0),
                              'match_status': 'MATCHED', 'match_confidence': 1.0, 'match_reason': '', 'matched_attributes': []})(),
            context, "test"
        ),
        engine._compare_positions(
            type('Match', (), {'company_a_position': create_position(LegalCategory.INDEMNIFICATION, "Basket", PartyRole.SELLER, amount=500000),
                              'company_b_position': create_position(LegalCategory.INDEMNIFICATION, "Basket", PartyRole.SELLER, amount=500000),
                              'match_status': 'MATCHED', 'match_confidence': 1.0, 'match_reason': '', 'matched_attributes': []})(),
            context, "test"
        ),
    ]
    
    risks10 = dep_analyzer.analyze_dependencies(findings10, "test", deal_value=None)
    cap_basket_risks = [r for r in risks10 if r.risk_type == "CAP_BASKET_RATIO"]
    
    passed10 = len(cap_basket_risks) > 0 and "unavailable" in cap_basket_risks[0].description.lower()
    results.append(("CASE 10: Missing purchase price -> no fabricated ratio", passed10))
    print(f"  Risks found: {len(cap_basket_risks)}")
    for r in cap_basket_risks:
        print(f"    - {r.risk_type}: {r.description}")
        print(f"    - Impact: {r.impact}")
    print(f"  Result: {'PASS' if passed10 else 'FAIL'}")
    
    # Summary
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\nTotal: {passed_count}/{total_count} passed ({passed_count/total_count*100:.0f}%)")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = run_gold_tests()
    sys.exit(0 if success else 1)