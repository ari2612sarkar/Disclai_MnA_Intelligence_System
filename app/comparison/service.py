import logging
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    LegalPosition, ComparisonRun, ComparisonResult, Company, Transaction,
    CompanyRole, LegalPositionMatch, ComparisonFinding, CrossDocumentRisk,
    DisclosureIssue, DealVerdict, RecommendationSet, LegalCategory, Evidence
)
from app.models.database import (
    ComparisonRunDB, CompanyDB, TransactionDB, LegalPositionMatchDB,
    ComparisonFindingDB, RecommendationDB, CrossDocumentRiskDB,
    DisclosureIssueDB, DealVerdictDB, LegalPositionDB, AnalysisRunDB
)
from app.models.session import get_db
from app.services.analysis import AnalysisService
from app.comparison.matcher import ProvisionMatcher
from app.comparison.engine import ComparisonEngine
from app.comparison.impact import TransactionalImpactEngine
from app.comparison.dependencies import CrossDocumentDependencyAnalyzer
from app.comparison.disclosure import DisclosureReconciliationService
from app.comparison.recommendations import OptimizationEngine
from app.comparison.verdict import DealVerdictEngine

logger = logging.getLogger(__name__)


class ComparisonService:
    def __init__(self):
        self.matcher = ProvisionMatcher()
        self.engine = ComparisonEngine()
        self.impact_engine = TransactionalImpactEngine()
        self.dependency_analyzer = CrossDocumentDependencyAnalyzer()
        self.disclosure_service = DisclosureReconciliationService()
        self.optimization_engine = OptimizationEngine()
        self.verdict_engine = DealVerdictEngine()
        self.analysis_service = AnalysisService()

    def run_comparison(
        self,
        transaction_id: str,
        company_a_run_id: str,
        company_b_run_id: str,
    ) -> ComparisonResult:
        start_time = time.time()
        comparison_id = str(uuid.uuid4())

        logger.info(f"Starting comparison {comparison_id} for transaction {transaction_id}")

        with get_db() as db:
            run_db = ComparisonRunDB(
                id=comparison_id,
                transaction_id=transaction_id,
                company_a_run_id=company_a_run_id,
                company_b_run_id=company_b_run_id,
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(run_db)
            db.commit()

        try:
            positions_a = self.analysis_service.get_findings(company_a_run_id)
            positions_b = self.analysis_service.get_findings(company_b_run_id)

            run_a = self.analysis_service.get_run(company_a_run_id)
            run_b = self.analysis_service.get_run(company_b_run_id)

            transaction = self._get_transaction(transaction_id)
            company_a = self._get_company(transaction.company_a_id)
            company_b = self._get_company(transaction.company_b_id)

            logger.info(f"Company A: {len(positions_a)} positions, Company B: {len(positions_b)} positions")

            matches = self.matcher.match_positions(positions_a, positions_b)
            matches = self._save_matches(comparison_id, matches)

            context = ComparisonContext(
                company_a_role=transaction.company_a_role,
                company_b_role=transaction.company_b_role,
            )

            findings = self.engine.compare_matched_positions(matches, context, comparison_id)
            findings = self._save_findings(comparison_id, findings)

            findings = self.impact_engine.analyze_impact(
                findings, transaction.company_a_role, transaction.company_b_role
            )
            findings = self._update_findings(findings)

            cross_doc_risks = self.dependency_analyzer.analyze_dependencies(findings, comparison_id, transaction.deal_value)
            cross_doc_risks = self._save_cross_doc_risks(comparison_id, cross_doc_risks)

            disclosure_issues = self._run_disclosure_reconciliation(
                comparison_id, transaction_id, positions_a, positions_b
            )
            disclosure_issues = self._save_disclosure_issues(comparison_id, disclosure_issues)

            recommendations = self.optimization_engine.generate_recommendations(
                findings, transaction.company_a_role, transaction.company_b_role
            )
            recommendations = self._bind_recommendation_company_ids(
                recommendations, transaction.company_a_id, transaction.company_b_id
            )
            recommendations = self._save_recommendations(recommendations)

            verdict = self.verdict_engine.generate_verdict(
                comparison_id=comparison_id,
                transaction_id=transaction_id,
                findings=findings,
                cross_doc_risks=cross_doc_risks,
                disclosure_issues=disclosure_issues,
                recommendations=recommendations,
                company_a_name=company_a.name,
                company_b_name=company_b.name,
                company_a_role=transaction.company_a_role,
                company_b_role=transaction.company_b_role,
            )
            verdict = self._save_verdict(verdict)

            self._update_comparison_run(comparison_id, len(positions_a), len(positions_b), matches, findings, cross_doc_risks, disclosure_issues, int((time.time() - start_time) * 1000))

            result = ComparisonResult(
                comparison_id=comparison_id,
                transaction_id=transaction_id,
                company_a_name=company_a.name,
                company_b_name=company_b.name,
                company_a_role=transaction.company_a_role,
                company_b_role=transaction.company_b_role,
                matches=matches,
                findings=findings,
                cross_document_risks=cross_doc_risks,
                disclosure_issues=disclosure_issues,
                verdict=verdict,
                processing_time_ms=int((time.time() - start_time) * 1000),
                total_llm_calls=0,
            )

            logger.info(f"Comparison {comparison_id} completed in {result.processing_time_ms}ms")
            return result

        except Exception as e:
            logger.error(f"Comparison {comparison_id} failed: {e}")
            with get_db() as db:
                run_db = db.query(ComparisonRunDB).filter(ComparisonRunDB.id == comparison_id).first()
                if run_db:
                    run_db.status = "failed"
                    run_db.error_details = [str(e)]
                    run_db.completed_at = datetime.utcnow()
                    db.commit()
            raise

    async def run_comparison_async(
        self,
        transaction_id: str,
        company_a_run_id: str,
        company_b_run_id: str,
    ) -> ComparisonResult:
        start_time = time.time()
        comparison_id = str(uuid.uuid4())

        logger.info(f"Starting async comparison {comparison_id} for transaction {transaction_id}")

        with get_db() as db:
            run_db = ComparisonRunDB(
                id=comparison_id,
                transaction_id=transaction_id,
                company_a_run_id=company_a_run_id,
                company_b_run_id=company_b_run_id,
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(run_db)
            db.commit()

        try:
            positions_a = self.analysis_service.get_findings(company_a_run_id)
            positions_b = self.analysis_service.get_findings(company_b_run_id)

            transaction = self._get_transaction(transaction_id)
            company_a = self._get_company(transaction.company_a_id)
            company_b = self._get_company(transaction.company_b_id)

            logger.info(f"Company A: {len(positions_a)} positions, Company B: {len(positions_b)} positions")

            matches = await self.matcher.match_positions_with_llm(positions_a, positions_b)
            matches = self._save_matches(comparison_id, matches)

            context = ComparisonContext(
                company_a_role=transaction.company_a_role,
                company_b_role=transaction.company_b_role,
            )

            findings = self.engine.compare_matched_positions(matches, context)
            findings = self._save_findings(comparison_id, findings)

            findings = await self.impact_engine.analyze_impact_with_llm(
                findings, transaction.company_a_role, transaction.company_b_role
            )
            findings = self._update_findings(findings)

            cross_doc_risks = self.dependency_analyzer.analyze_dependencies(
                findings, comparison_id, transaction.deal_value
            )
            # Keep deterministic dependency detection authoritative; optional LLM
            # enhancement should not erase already-detected risks.
            try:
                enhanced_risks = await self.dependency_analyzer.analyze_dependencies_with_llm(findings)
                if enhanced_risks:
                    existing = {r.risk_type + "|" + r.description for r in cross_doc_risks}
                    for risk in enhanced_risks:
                        key = risk.risk_type + "|" + risk.description
                        if key not in existing:
                            cross_doc_risks.append(risk)
            except Exception as e:
                logger.warning(f"Dependency LLM enhancement failed; keeping deterministic risks: {e}")
            cross_doc_risks = self._save_cross_doc_risks(comparison_id, cross_doc_risks)

            disclosure_issues = self._run_disclosure_reconciliation(
                comparison_id, transaction_id, positions_a, positions_b
            )
            disclosure_issues = self._save_disclosure_issues(comparison_id, disclosure_issues)

            recommendations = await self.optimization_engine.generate_recommendations_with_llm(
                findings, transaction.company_a_role, transaction.company_b_role
            )
            recommendations = self._bind_recommendation_company_ids(
                recommendations, transaction.company_a_id, transaction.company_b_id
            )
            recommendations = self._save_recommendations(recommendations)

            verdict = self.verdict_engine.generate_verdict(
                comparison_id=comparison_id,
                transaction_id=transaction_id,
                findings=findings,
                cross_doc_risks=cross_doc_risks,
                disclosure_issues=disclosure_issues,
                recommendations=recommendations,
                company_a_name=company_a.name,
                company_b_name=company_b.name,
                company_a_role=transaction.company_a_role,
                company_b_role=transaction.company_b_role,
            )
            verdict = await self.verdict_engine.generate_verdict_with_llm(
                verdict, findings, cross_doc_risks, disclosure_issues,
                company_a.name, company_b.name,
                transaction.company_a_role, transaction.company_b_role
            )
            verdict = self._save_verdict(verdict)

            self._update_comparison_run(comparison_id, len(positions_a), len(positions_b), matches, findings, cross_doc_risks, disclosure_issues, int((time.time() - start_time) * 1000))

            result = ComparisonResult(
                comparison_id=comparison_id,
                transaction_id=transaction_id,
                company_a_name=company_a.name,
                company_b_name=company_b.name,
                company_a_role=transaction.company_a_role,
                company_b_role=transaction.company_b_role,
                matches=matches,
                findings=findings,
                cross_document_risks=cross_doc_risks,
                disclosure_issues=disclosure_issues,
                verdict=verdict,
                processing_time_ms=int((time.time() - start_time) * 1000),
                total_llm_calls=0,
            )

            logger.info(f"Async comparison {comparison_id} completed in {result.processing_time_ms}ms")
            return result

        except Exception as e:
            logger.error(f"Async comparison {comparison_id} failed: {e}")
            with get_db() as db:
                run_db = db.query(ComparisonRunDB).filter(ComparisonRunDB.id == comparison_id).first()
                if run_db:
                    run_db.status = "failed"
                    run_db.error_details = [str(e)]
                    run_db.completed_at = datetime.utcnow()
                    db.commit()
            raise

    def _get_transaction(self, transaction_id: str) -> Transaction:
        with get_db() as db:
            txn_db = db.query(TransactionDB).filter(TransactionDB.id == transaction_id).first()
            if not txn_db:
                raise ValueError(f"Transaction {transaction_id} not found")
            return Transaction(
                id=txn_db.id,
                name=txn_db.name,
                description=txn_db.description,
                status=txn_db.status,
                company_a_id=txn_db.company_a_id,
                company_b_id=txn_db.company_b_id,
                company_a_role=CompanyRole(txn_db.company_a_role.value),
                company_b_role=CompanyRole(txn_db.company_b_role.value),
                deal_value=txn_db.deal_value,
                currency=txn_db.currency,
                created_at=txn_db.created_at,
                updated_at=txn_db.updated_at,
            )

    def _get_company(self, company_id: str) -> Company:
        with get_db() as db:
            comp_db = db.query(CompanyDB).filter(CompanyDB.id == company_id).first()
            if not comp_db:
                raise ValueError(f"Company {company_id} not found")
            return Company(
                id=comp_db.id,
                name=comp_db.name,
                role=CompanyRole(comp_db.role.value),
                description=comp_db.description,
                company_metadata=comp_db.company_metadata or {},
                created_at=comp_db.created_at,
                updated_at=comp_db.updated_at,
            )

    def _run_disclosure_reconciliation(
        self,
        comparison_id: str,
        transaction_id: str,
        positions_a: List[LegalPosition],
        positions_b: List[LegalPosition],
    ) -> List[DisclosureIssue]:
        all_positions = positions_a + positions_b

        spa_positions = [p for p in all_positions if p.category in [
            LegalCategory.REPRESENTATIONS_WARRANTIES,
            LegalCategory.DISCLOSURE_EXCEPTIONS,
            LegalCategory.INDEMNIFICATION,
        ]]

        disc_positions = [p for p in all_positions if p.category == LegalCategory.DISCLOSURE_EXCEPTIONS]
        data_room_positions = [p for p in all_positions if p.category in [
            LegalCategory.LITIGATION,
            LegalCategory.MATERIAL_CONTRACTS,
        ]]

        return self.disclosure_service.reconcile_disclosures(
            spa_positions, disc_positions, data_room_positions, comparison_id
        )

    def _save_matches(
        self,
        comparison_id: str,
        matches: List[LegalPositionMatch],
    ) -> List[LegalPositionMatch]:
        with get_db() as db:
            for match in matches:
                match_db = LegalPositionMatchDB(
                    comparison_id=comparison_id,
                    company_a_position_id=match.company_a_position.id if match.company_a_position else None,
                    company_b_position_id=match.company_b_position.id if match.company_b_position else None,
                    match_status=match.match_status,
                    match_confidence=match.match_confidence,
                    match_reason=match.match_reason,
                    matched_attributes=match.matched_attributes,
                )
                db.add(match_db)
            db.commit()
        return matches

    def _save_findings(
        self,
        comparison_id: str,
        findings: List[ComparisonFinding],
    ) -> List[ComparisonFinding]:
        with get_db() as db:
            for finding in findings:
                finding_db = ComparisonFindingDB(
                    id=finding.id,
                    comparison_id=comparison_id,
                    category=finding.category,
                    provision=finding.provision,
                    subcategory=finding.subcategory,
                    company_a_position_id=finding.company_a_position.id if finding.company_a_position else None,
                    company_b_position_id=finding.company_b_position.id if finding.company_b_position else None,
                    differences=[d.model_dump() for d in finding.differences],
                    classification=finding.classification,
                    classification_reason=finding.classification_reason,
                    beneficiary=finding.beneficiary,
                    affected_dimension=finding.affected_dimension,
                    advantage_confidence=finding.advantage_confidence,
                    advantage_explanation=finding.advantage_explanation,
                    legal_impact=finding.legal_impact,
                    commercial_impact=finding.commercial_impact,
                    closing_impact=finding.closing_impact,
                    post_closing_impact=finding.post_closing_impact,
                    negotiation_impact=finding.negotiation_impact,
                    comparison_confidence=finding.comparison_confidence,
                    materiality_confidence=finding.materiality_confidence,
                    requires_lawyer_review=finding.requires_lawyer_review,
                    evidence_a=[e.model_dump() for e in finding.evidence_a],
                    evidence_b=[e.model_dump() for e in finding.evidence_b],
                    cross_document_dependencies=finding.cross_document_dependencies,
                    disclosure_issues=finding.disclosure_issues,
                )
                db.add(finding_db)
            db.commit()
        return findings

    def _update_findings(self, findings: List[ComparisonFinding]) -> List[ComparisonFinding]:
        with get_db() as db:
            for finding in findings:
                finding_db = db.query(ComparisonFindingDB).filter(ComparisonFindingDB.id == finding.id).first()
                if finding_db:
                    finding_db.legal_impact = finding.legal_impact
                    finding_db.commercial_impact = finding.commercial_impact
                    finding_db.closing_impact = finding.closing_impact
                    finding_db.post_closing_impact = finding.post_closing_impact
                    finding_db.negotiation_impact = finding.negotiation_impact
            db.commit()
        return findings

    def _save_disclosure_issues(
        self,
        comparison_id: str,
        issues: List[DisclosureIssue],
    ) -> List[DisclosureIssue]:
        with get_db() as db:
            for issue in issues:
                db_issue = DisclosureIssueDB(
                    id=issue.id,
                    comparison_id=comparison_id,
                    issue_type=issue.issue_type,
                    description=issue.description,
                    spa_requirement_position_id=issue.spa_requirement.id if issue.spa_requirement else None,
                    disclosure_schedule_evidence=issue.disclosure_schedule_evidence.model_dump() if issue.disclosure_schedule_evidence else None,
                    data_room_evidence=issue.data_room_evidence.model_dump() if issue.data_room_evidence else None,
                    severity=issue.severity,
                    confidence=issue.confidence,
                    status=issue.status,
                )
                db.add(db_issue)
            db.commit()
        return issues

    def _save_cross_doc_risks(
        self,
        comparison_id: str,
        risks: List[CrossDocumentRisk],
    ) -> List[CrossDocumentRisk]:
        with get_db() as db:
            for risk in risks:
                risk_db = CrossDocumentRiskDB(
                    id=risk.id,
                    comparison_id=comparison_id,
                    risk_type=risk.risk_type,
                    severity=risk.severity,
                    component_findings=risk.component_findings,
                    description=risk.description,
                    impact=risk.impact,
                    evidence_references=[e.model_dump() for e in risk.evidence_references],
                    confidence=risk.confidence,
                )
                db.add(risk_db)
            db.commit()
        return risks

    def _bind_recommendation_company_ids(
        self,
        recommendations: Dict[str, RecommendationSet],
        company_a_id: str,
        company_b_id: str,
    ) -> Dict[str, RecommendationSet]:
        """Replace internal A/B placeholders with real persisted company IDs."""
        for rec_set in recommendations.values():
            if rec_set.company_a_recommendation:
                rec_set.company_a_recommendation.company_id = company_a_id
            if rec_set.company_b_recommendation:
                rec_set.company_b_recommendation.company_id = company_b_id
        return recommendations

    def _save_recommendations(
        self,
        recommendations: Dict[str, RecommendationSet],
    ) -> Dict[str, RecommendationSet]:
        with get_db() as db:
            for finding_id, rec_set in recommendations.items():
                if rec_set.company_a_recommendation:
                    rec_db = RecommendationDB(
                        finding_id=finding_id,
                        company_id=rec_set.company_a_recommendation.company_id,
                        company_role=rec_set.company_a_recommendation.company_role,
                        recommendation_type=rec_set.company_a_recommendation.recommendation_type,
                        title=rec_set.company_a_recommendation.title,
                        description=rec_set.company_a_recommendation.description,
                        rationale=rec_set.company_a_recommendation.rationale,
                        current_position=rec_set.company_a_recommendation.current_position,
                        proposed_adjustment=rec_set.company_a_recommendation.proposed_adjustment,
                        legal_basis=rec_set.company_a_recommendation.legal_basis,
                        commercial_tradeoff=rec_set.company_a_recommendation.commercial_tradeoff,
                        negotiation_objective=rec_set.company_a_recommendation.negotiation_objective,
                        priority=rec_set.company_a_recommendation.priority,
                        confidence=rec_set.company_a_recommendation.confidence,
                        depends_on=rec_set.company_a_recommendation.depends_on,
                    )
                    db.add(rec_db)
                if rec_set.company_b_recommendation:
                    rec_db = RecommendationDB(
                        finding_id=finding_id,
                        company_id=rec_set.company_b_recommendation.company_id,
                        company_role=rec_set.company_b_recommendation.company_role,
                        recommendation_type=rec_set.company_b_recommendation.recommendation_type,
                        title=rec_set.company_b_recommendation.title,
                        description=rec_set.company_b_recommendation.description,
                        rationale=rec_set.company_b_recommendation.rationale,
                        current_position=rec_set.company_b_recommendation.current_position,
                        proposed_adjustment=rec_set.company_b_recommendation.proposed_adjustment,
                        legal_basis=rec_set.company_b_recommendation.legal_basis,
                        commercial_tradeoff=rec_set.company_b_recommendation.commercial_tradeoff,
                        negotiation_objective=rec_set.company_b_recommendation.negotiation_objective,
                        priority=rec_set.company_b_recommendation.priority,
                        confidence=rec_set.company_b_recommendation.confidence,
                        depends_on=rec_set.company_b_recommendation.depends_on,
                    )
                    db.add(rec_db)
            db.commit()
        return recommendations

    def _save_verdict(self, verdict: DealVerdict) -> DealVerdict:
        with get_db() as db:
            verdict_db = DealVerdictDB(
                id=verdict.id,
                comparison_id=verdict.comparison_id,
                transaction_id=verdict.transaction_id,
                overall_assessment=verdict.overall_assessment,
                overall_risk_level=verdict.overall_risk_level,
                key_asymmetries=verdict.key_asymmetries,
                critical_issues=verdict.critical_issues,
                material_asymmetries=verdict.material_asymmetries,
                evidence_backed_findings=verdict.evidence_backed_findings,
                company_a_advantages=verdict.company_a_advantages,
                company_a_weaknesses=verdict.company_a_weaknesses,
                company_b_advantages=verdict.company_b_advantages,
                company_b_weaknesses=verdict.company_b_weaknesses,
                critical_findings=verdict.critical_findings,
                recommended_actions=verdict.recommended_actions,
                unresolved_questions=verdict.unresolved_questions,
                score=verdict.score,
                score_methodology=verdict.score_methodology,
                confidence=verdict.confidence,
            )
            db.add(verdict_db)
            db.commit()
        return verdict

    def _update_comparison_run(
        self,
        comparison_id: str,
        total_a: int,
        total_b: int,
        matches: List[LegalPositionMatch],
        findings: List[ComparisonFinding],
        cross_doc_risks: List[CrossDocumentRisk],
        disclosure_issues: List[DisclosureIssue],
        processing_time: int,
    ):
        with get_db() as db:
            run_db = db.query(ComparisonRunDB).filter(ComparisonRunDB.id == comparison_id).first()
            if run_db:
                run_db.status = "completed"
                run_db.completed_at = datetime.utcnow()
                run_db.total_positions_a = total_a
                run_db.total_positions_b = total_b
                run_db.matched_provisions = len([m for m in matches if m.match_status.value == "MATCHED"])
                run_db.unmatched_provisions = len([m for m in matches if m.match_status.value == "UNMATCHED"])
                run_db.findings_count = len(findings)
                run_db.material_asymmetries_count = len([f for f in findings if f.classification.value == "MATERIAL_ASYMMETRY"])
                run_db.cross_document_risks_count = len(cross_doc_risks)
                run_db.disclosure_issues_count = len(disclosure_issues)
                run_db.processing_time_ms = processing_time
                db.commit()

    def get_comparison(self, comparison_id: str) -> Optional[ComparisonResult]:
        with get_db() as db:
            run_db = db.query(ComparisonRunDB).filter(ComparisonRunDB.id == comparison_id).first()
            if not run_db:
                return None

            matches_db = db.query(LegalPositionMatchDB).filter(LegalPositionMatchDB.comparison_id == comparison_id).all()
            findings_db = db.query(ComparisonFindingDB).filter(ComparisonFindingDB.comparison_id == comparison_id).all()
            risks_db = db.query(CrossDocumentRiskDB).filter(CrossDocumentRiskDB.comparison_id == comparison_id).all()
            disc_db = db.query(DisclosureIssueDB).filter(DisclosureIssueDB.comparison_id == comparison_id).all()
            verdict_db = db.query(DealVerdictDB).filter(DealVerdictDB.comparison_id == comparison_id).first()
            recommendations_db = (
                db.query(RecommendationDB)
                .join(ComparisonFindingDB, RecommendationDB.finding_id == ComparisonFindingDB.id)
                .filter(ComparisonFindingDB.comparison_id == comparison_id)
                .all()
            )

            transaction = self._get_transaction(run_db.transaction_id)
            company_a = self._get_company(transaction.company_a_id)
            company_b = self._get_company(transaction.company_b_id)

            rec_a = []
            rec_b = []
            for rec in recommendations_db:
                rec_schema = self._recommendation_db_to_schema(rec)
                if rec.company_id == transaction.company_a_id:
                    rec_a.append(rec_schema)
                elif rec.company_id == transaction.company_b_id:
                    rec_b.append(rec_schema)

            return ComparisonResult(
                comparison_id=comparison_id,
                transaction_id=run_db.transaction_id,
                company_a_name=company_a.name,
                company_b_name=company_b.name,
                company_a_role=transaction.company_a_role,
                company_b_role=transaction.company_b_role,
                matches=[self._match_db_to_schema(m) for m in matches_db],
                findings=[self._finding_db_to_schema(f) for f in findings_db],
                cross_document_risks=[self._risk_db_to_schema(r) for r in risks_db],
                disclosure_issues=[self._disclosure_db_to_schema(d) for d in disc_db],
                verdict=self._verdict_db_to_schema(verdict_db) if verdict_db else None,
                processing_time_ms=run_db.processing_time_ms or 0,
                total_llm_calls=run_db.llm_calls or 0,
            )

    def _position_db_to_schema(self, p: Optional[LegalPositionDB]) -> Optional[LegalPosition]:
        if not p:
            return None
        return LegalPosition(
            id=p.id,
            category=p.category,
            subcategory=p.subcategory,
            provision_name=p.provision_name,
            party=p.party,
            obligation_right=p.obligation_right or "",
            threshold=p.threshold,
            amount=p.amount,
            percentage=p.percentage,
            unit=p.unit,
            duration=p.duration,
            condition=p.condition or [],
            exception=p.exception or [],
            qualifier=p.qualifier or [],
            consequence=p.consequence or [],
            evidence=Evidence(
                document_id=p.evidence_document_id,
                page_number=p.evidence_page,
                section_id=p.evidence_section_id,
                section_number=p.evidence_section_number,
                heading=p.evidence_heading or "",
                text=p.evidence_text,
                char_start=p.evidence_char_start,
                char_end=p.evidence_char_end,
                chunk_id=p.evidence_chunk_id,
            ),
            confidence=p.confidence or 0.0,
            status=p.status,
            raw_extraction=p.raw_extraction,
        )

    def _match_db_to_schema(self, m: LegalPositionMatchDB) -> LegalPositionMatch:
        return LegalPositionMatch(
            company_a_position=self._position_db_to_schema(m.company_a_position),
            company_b_position=self._position_db_to_schema(m.company_b_position),
            match_status=m.match_status,
            match_confidence=m.match_confidence,
            match_reason=m.match_reason,
            matched_attributes=m.matched_attributes or [],
        )

    def _finding_db_to_schema(self, f: ComparisonFindingDB) -> ComparisonFinding:
        return ComparisonFinding(
            id=f.id,
            comparison_id=f.comparison_id,
            category=f.category,
            provision=f.provision,
            subcategory=f.subcategory,
            company_a_position=self._position_db_to_schema(f.company_a_position),
            company_b_position=self._position_db_to_schema(f.company_b_position),
            differences=[DifferenceDetail(**d) for d in (f.differences or [])],
            classification=f.classification,
            classification_reason=f.classification_reason,
            beneficiary=f.beneficiary,
            affected_dimension=f.affected_dimension,
            advantage_confidence=f.advantage_confidence,
            advantage_explanation=f.advantage_explanation,
            legal_impact=f.legal_impact,
            commercial_impact=f.commercial_impact,
            closing_impact=f.closing_impact,
            post_closing_impact=f.post_closing_impact,
            negotiation_impact=f.negotiation_impact,
            comparison_confidence=f.comparison_confidence,
            materiality_confidence=f.materiality_confidence,
            requires_lawyer_review=f.requires_lawyer_review,
            evidence_a=[Evidence(**e) for e in (f.evidence_a or [])],
            evidence_b=[Evidence(**e) for e in (f.evidence_b or [])],
            cross_document_dependencies=f.cross_document_dependencies or [],
            disclosure_issues=f.disclosure_issues or [],
        )

    def _risk_db_to_schema(self, r: CrossDocumentRiskDB) -> CrossDocumentRisk:
        return CrossDocumentRisk(
            id=r.id,
            comparison_id=r.comparison_id,
            risk_type=r.risk_type,
            severity=r.severity,
            component_findings=r.component_findings or [],
            description=r.description,
            impact=r.impact,
            evidence_references=[Evidence(**e) for e in (r.evidence_references or [])],
            confidence=r.confidence,
        )

    def _disclosure_db_to_schema(self, d: DisclosureIssueDB) -> DisclosureIssue:
        return DisclosureIssue(
            id=d.id,
            comparison_id=d.comparison_id,
            issue_type=d.issue_type,
            description=d.description,
            spa_requirement=self._position_db_to_schema(d.spa_requirement_position),
            disclosure_schedule_evidence=Evidence(**d.disclosure_schedule_evidence) if d.disclosure_schedule_evidence else None,
            data_room_evidence=Evidence(**d.data_room_evidence) if d.data_room_evidence else None,
            severity=d.severity,
            confidence=d.confidence,
            status=d.status,
        )

    def _recommendation_db_to_schema(self, r: RecommendationDB) -> "PartySpecificRecommendation":
        from app.models.schemas import PartySpecificRecommendation
        return PartySpecificRecommendation(
            company_id=r.company_id,
            company_role=r.company_role,
            recommendation_type=r.recommendation_type,
            title=r.title,
            description=r.description,
            rationale=r.rationale,
            current_position=r.current_position,
            proposed_adjustment=r.proposed_adjustment,
            legal_basis=r.legal_basis,
            commercial_tradeoff=r.commercial_tradeoff,
            negotiation_objective=r.negotiation_objective,
            priority=r.priority,
            confidence=r.confidence,
            depends_on=r.depends_on or [],
            finding_id=r.finding_id,
        )

    def _verdict_db_to_schema(self, v: DealVerdictDB, company_a_recommendations=None, company_b_recommendations=None) -> DealVerdict:
        return DealVerdict(
            id=v.id,
            comparison_id=v.comparison_id,
            transaction_id=v.transaction_id,
            overall_assessment=v.overall_assessment,
            overall_risk_level=v.overall_risk_level,
            key_asymmetries=v.key_asymmetries,
            critical_issues=v.critical_issues,
            material_asymmetries=v.material_asymmetries,
            evidence_backed_findings=v.evidence_backed_findings,
            company_a_advantages=v.company_a_advantages or [],
            company_a_weaknesses=v.company_a_weaknesses or [],
            company_b_advantages=v.company_b_advantages or [],
            company_b_weaknesses=v.company_b_weaknesses or [],
            critical_findings=v.critical_findings or [],
            recommended_actions=v.recommended_actions or [],
            unresolved_questions=v.unresolved_questions or [],
            score=v.score,
            score_methodology=v.score_methodology,
            company_a_recommendations=[],
            company_b_recommendations=[],
            confidence=v.confidence,
        )


class ComparisonContext:
    def __init__(self, company_a_role: CompanyRole, company_b_role: CompanyRole):
        self.company_a_role = company_a_role
        self.company_b_role = company_b_role

from app.models.schemas import DifferenceDetail