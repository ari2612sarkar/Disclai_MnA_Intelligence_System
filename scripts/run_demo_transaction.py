#!/usr/bin/env python
"""
Run the full demo transaction through DISCLAI pipeline.
"""
import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, r"D:\Legal_Bot\disclai")

from app.services.analysis import AnalysisService
from app.comparison.service import ComparisonService
from app.models.database import (
    CompanyDB, TransactionDB, DocumentDB, DocumentOwnershipDB,
    CompanyRoleEnum, DocumentTypeEnum
)
from app.models.session import get_db, init_db

init_db()

# File paths
COMPANY_A_DIR = r"D:\Legal_Bot\disclai\tests\fixtures\demo_transaction\company_a"
COMPANY_B_DIR = r"D:\Legal_Bot\disclai\tests\fixtures\demo_transaction\company_b"

company_a_files = [
    ("SPA.pdf", "SPA", CompanyRoleEnum.SELLER),
    ("Disclosure_Schedule.pdf", "Disclosure Schedule", CompanyRoleEnum.SELLER),
    ("Material_Contract.pdf", "Commercial Contract", CompanyRoleEnum.SELLER),
    ("Litigation.pdf", "Litigation Document", CompanyRoleEnum.SELLER),
    ("Employment_Agreement.pdf", "Employment Document", CompanyRoleEnum.SELLER),
]

company_b_files = [
    ("SPA.pdf", "SPA", CompanyRoleEnum.BUYER),
    ("Disclosure_Schedule.pdf", "Disclosure Schedule", CompanyRoleEnum.BUYER),
    ("Material_Contract.pdf", "Commercial Contract", CompanyRoleEnum.BUYER),
    ("Litigation.pdf", "Litigation Document", CompanyRoleEnum.BUYER),
    ("Employment_Agreement.pdf", "Employment Document", CompanyRoleEnum.BUYER),
]

analysis_service = AnalysisService()

def upload_and_analyze(company_name, company_role, files, company_dir):
    """Upload documents and run analysis for a company."""
    print(f"\n{'='*60}")
    print(f"Processing {company_name} ({company_role.value})")
    print(f"{'='*60}")
    
    with get_db() as db:
        # Create company
        company = CompanyDB(
            id=str(uuid.uuid4()),
            name=company_name,
            role=company_role,
            description=f"{company_name} - {company_role.value} in demo transaction"
        )
        db.add(company)
        db.flush()
        company_id = company.id
        print(f"Created company: {company_id}")
        
        # Create transaction (only for first company)
        transaction = None
    
    document_ids = []
    run_ids = []
    
    for filename, doc_type, role_in_doc in files:
        filepath = os.path.join(company_dir, filename)
        file_size = os.path.getsize(filepath)
        
        print(f"\n  Uploading {filename}...")
        
        with get_db() as db:
            doc = DocumentDB(
                id=str(uuid.uuid4()),
                filename=filename,
                content_type="application/pdf",
                size_bytes=file_size,
                document_type=DocumentTypeEnum(doc_type),
            )
            db.add(doc)
            
            ownership = DocumentOwnershipDB(
                document_id=doc.id,
                company_id=company_id,
                role_in_document=role_in_doc,
            )
            db.add(ownership)
            db.commit()
            
            document_ids.append(doc.id)
        
        # Run analysis
        print(f"  Analyzing {filename}...")
        try:
            result = analysis_service.run_analysis(doc.id, filepath, doc.id)
            run_ids.append(result.run_id)
            print(f"    Run ID: {result.run_id}")
            print(f"    Positions extracted: {len(result.positions)}")
            for pos in result.positions:
                print(f"      - {pos.category.value}: {pos.provision_name} ({pos.party.value})")
        except Exception as e:
            print(f"    ERROR: {e}")
    
    return company_id, document_ids, run_ids

# Process Company A
company_a_id, a_doc_ids, a_run_ids = upload_and_analyze(
    "Northstar Technologies Pvt. Ltd.", CompanyRoleEnum.SELLER, company_a_files, COMPANY_A_DIR
)

# Process Company B
company_b_id, b_doc_ids, b_run_ids = upload_and_analyze(
    "Vertex Systems Pvt. Ltd.", CompanyRoleEnum.BUYER, company_b_files, COMPANY_B_DIR
)

# Create transaction
with get_db() as db:
    transaction = TransactionDB(
        id=str(uuid.uuid4()),
        name="Northstar-Vertex Acquisition",
        description="Acquisition of Northstar Technologies by Vertex Systems",
        company_a_id=company_a_id,
        company_b_id=company_b_id,
        company_a_role=CompanyRoleEnum.SELLER,
        company_b_role=CompanyRoleEnum.BUYER,
        deal_value=50000000.0,
        currency="USD",
    )
    db.add(transaction)
    db.commit()
    transaction_id = transaction.id
    print(f"\nCreated transaction: {transaction_id}")

# Run comparison using the SPA analysis runs (first run for each company)
# Find the SPA run for each company
spa_run_a = None
spa_run_b = None

with get_db() as db:
    from app.models.database import AnalysisRunDB, LegalPositionDB
    for run_id in a_run_ids:
        run = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == run_id).first()
        if run:
            pos = db.query(LegalPositionDB).filter(LegalPositionDB.run_id == run_id).first()
            if pos and pos.provision_name == "General Liability Cap":
                spa_run_a = run_id
                break
    
    for run_id in b_run_ids:
        run = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == run_id).first()
        if run:
            pos = db.query(LegalPositionDB).filter(LegalPositionDB.run_id == run_id).first()
            if pos and pos.provision_name == "General Liability Cap":
                spa_run_b = run_id
                break

print(f"\nSPA Run A: {spa_run_a}")
print(f"SPA Run B: {spa_run_b}")

if spa_run_a and spa_run_b:
    print("\n" + "="*60)
    print("RUNNING COMPARISON")
    print("="*60)
    
    comparison_service = ComparisonService()
    result = comparison_service.run_comparison(
        transaction_id=transaction_id,
        company_a_run_id=spa_run_a,
        company_b_run_id=spa_run_b,
    )
    
    print(f"\nComparison ID: {result.comparison_id}")
    print(f"Matches: {len(result.matches)}")
    print(f"Findings: {len(result.findings)}")
    print(f"Cross-Document Risks: {len(result.cross_document_risks)}")
    print(f"Disclosure Issues: {len(result.disclosure_issues)}")
    
    print("\n--- MATCHES ---")
    for match in result.matches:
        print(f"  {match.match_status.value}: {match.company_a_position_id} <-> {match.company_b_position_id} (conf: {match.match_confidence:.2f})")
    
    print("\n--- FINDINGS ---")
    for finding in result.findings:
        print(f"  [{finding.classification.value}] {finding.provision}")
        print(f"    A: {finding.company_a_position}")
        print(f"    B: {finding.company_b_position}")
        print(f"    Impact: {finding.legal_impact}")
    
    print("\n--- CROSS-DOCUMENT RISKS ---")
    for risk in result.cross_document_risks:
        print(f"  [{risk.severity.value}] {risk.risk_type}: {risk.description}")
    
    print("\n--- DISCLOSURE ISSUES ---")
    for issue in result.disclosure_issues:
        print(f"  [{issue.severity.value}] {issue.issue_type}: {issue.description}")
    
    if result.verdict:
        print("\n--- DEAL VERDICT ---")
        print(f"  Overall Assessment: {result.verdict.overall_assessment}")
        print(f"  Risk Level: {result.verdict.overall_risk_level.value}")
        print(f"  Score: {result.verdict.score}/100")
        print(f"  Material Asymmetries: {result.verdict.material_asymmetries}")
        print(f"  Critical Issues: {result.verdict.critical_issues}")
        print(f"  Company A Advantages: {result.verdict.company_a_advantages}")
        print(f"  Company A Weaknesses: {result.verdict.company_a_weaknesses}")
        print(f"  Company B Advantages: {result.verdict.company_b_advantages}")
        print(f"  Company B Weaknesses: {result.verdict.company_b_weaknesses}")
        print(f"  Recommended Actions: {result.verdict.recommended_actions}")
        print(f"  Company A Recs: {len(result.verdict.company_a_recommendations)}")
        print(f"  Company B Recs: {len(result.verdict.company_b_recommendations)}")
        for rec in result.verdict.company_a_recommendations:
            print(f"    A[{rec.priority.value}]: {rec.title}")
        for rec in result.verdict.company_b_recommendations:
            print(f"    B[{rec.priority.value}]: {rec.title}")

print("\n=== DEMO COMPLETE ===")