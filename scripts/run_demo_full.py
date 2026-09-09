#!/usr/bin/env python
"""
Run the full demo transaction through DISCLAI API.
"""
import os
import sys
import time
import requests
import threading
import uvicorn
from app.api.main import app

# File paths
COMPANY_A_DIR = r"D:\Legal_Bot\disclai\tests\fixtures\demo_transaction\company_a"
COMPANY_B_DIR = r"D:\Legal_Bot\disclai\tests\fixtures\demo_transaction\company_b"

company_a_files = [
    ("SPA.pdf", "Seller"),
    ("Disclosure_Schedule.pdf", "Seller"),
    ("Material_Contract.pdf", "Seller"),
    ("Litigation.pdf", "Seller"),
    ("Employment_Agreement.pdf", "Seller"),
]

company_b_files = [
    ("SPA.pdf", "Buyer"),
    ("Disclosure_Schedule.pdf", "Buyer"),
    ("Material_Contract.pdf", "Buyer"),
    ("Litigation.pdf", "Buyer"),
    ("Employment_Agreement.pdf", "Buyer"),
]

def run_server():
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='error')

def get_doc_type(filename):
    if filename == 'SPA.pdf':
        return 'SPA'
    elif filename == 'Disclosure_Schedule.pdf':
        return 'Disclosure Schedule'
    elif filename == 'Material_Contract.pdf':
        return 'Commercial Contract'
    elif filename == 'Litigation.pdf':
        return 'Litigation Document'
    elif filename == 'Employment_Agreement.pdf':
        return 'Employment Document'
    return 'Other'

def upload_and_analyze(base_url, transaction_id, company_id, company_dir, files, company_name):
    doc_ids = []
    run_ids = []
    for filename, role in files:
        filepath = os.path.join(company_dir, filename)
        print(f"   Uploading {filename}...")
        with open(filepath, 'rb') as f:
            files_dict = {'file': (filename, f, 'application/pdf')}
            data = {
                'transaction_id': transaction_id, 
                'company_id': company_id, 
                'role_in_document': role,
                'document_type': get_doc_type(filename)
            }
            r = requests.post(f'{base_url}/documents/upload', files=files_dict, data=data, timeout=30)
        doc = r.json()
        doc_ids.append(doc['document_id'])
        print(f"     Document ID: {doc['document_id']}")
        
        # Run analysis
        print(f"     Running analysis...")
        r = requests.post(f'{base_url}/api/analysis/run', json={'document_id': doc['document_id']}, timeout=60)
        run = r.json()
        run_ids.append(run['run_id'])
        print(f"     Run ID: {run['run_id']}")
    return doc_ids, run_ids

def main():
    print("=" * 60)
    print("DISCLAI Full Demo Transaction")
    print("Northstar Technologies (Seller) vs Vertex Systems (Buyer)")
    print("=" * 60)
    
    # Start server
    print("Starting API server...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(5)
    
    base_url = 'http://127.0.0.1:8000'
    
    try:
        # Health check
        r = requests.get(f'{base_url}/api/health', timeout=10)
        print(f"Health check: {r.json()}")
        
        # 1. Create companies
        print("\n1. Creating Company A (Seller)...")
        r = requests.post(f'{base_url}/api/companies', json={
            'name': 'Northstar Technologies Pvt. Ltd.', 
            'role': 'Seller',
            'description': 'Seller in the Northstar-Vertex Acquisition'
        }, timeout=10)
        company_a = r.json()
        print(f"   Company A ID: {company_a['id']}")
        
        print("2. Creating Company B (Buyer)...")
        r = requests.post(f'{base_url}/api/companies', json={
            'name': 'Vertex Systems Pvt. Ltd.', 
            'role': 'Buyer',
            'description': 'Buyer in the Northstar-Vertex Acquisition'
        }, timeout=10)
        company_b = r.json()
        print(f"   Company B ID: {company_b['id']}")
        
        # 2. Create transaction
        print("\n3. Creating transaction...")
        r = requests.post(f'{base_url}/api/transactions', json={
            'name': 'Northstar-Vertex Acquisition',
            'company_a_id': company_a['id'],
            'company_b_id': company_b['id'],
            'company_a_role': 'Seller',
            'company_b_role': 'Buyer',
            'deal_value': 50000000
        }, timeout=10)
        transaction = r.json()
        transaction_id = transaction['id']
        print(f"   Transaction ID: {transaction_id}")
        
        # 3. Upload Company A documents
        print("\n4. Uploading Company A documents...")
        a_doc_ids, a_run_ids = upload_and_analyze(
            base_url, transaction_id, company_a['id'], COMPANY_A_DIR, company_a_files, "Company A"
        )
        
        # 4. Upload Company B documents
        print("\n5. Uploading Company B documents...")
        b_doc_ids, b_run_ids = upload_and_analyze(
            base_url, transaction_id, company_b['id'], COMPANY_B_DIR, company_b_files, "Company B"
        )
        
        # Wait for analysis to complete
        print("\n6. Waiting for analysis to complete...")
        time.sleep(20)
        
        # Check analysis status
        print("   Checking analysis status...")
        for i, (doc_id, run_id) in enumerate(zip(a_doc_ids + b_doc_ids, a_run_ids + b_run_ids)):
            r = requests.get(f'{base_url}/analysis/status/{doc_id}', timeout=10)
            status = r.json()
            print(f"     Doc {i+1}: {status.get('status', 'unknown')} - {status.get('positions_extracted', 0)} positions")
        
        # 5. Run comparison using the SPA runs (first run for each)
        print("\n7. Running comparison...")
        r = requests.post(f'{base_url}/api/comparison/run', json={
            'transaction_id': transaction_id,
            'company_a_run_id': a_run_ids[0],  # SPA is first
            'company_b_run_id': b_run_ids[0],  # SPA is first
        }, timeout=60)
        comparison = r.json()
        comparison_id = comparison['id']
        print(f"   Comparison ID: {comparison_id}")
        
        time.sleep(5)
        
        # 6. Get results
        print("\n8. Getting comparison results...")
        r = requests.get(f'{base_url}/api/comparison/{comparison_id}', timeout=10)
        result = r.json()
        
        print(f"   Matches: {len(result['matches'])}")
        print(f"   Findings: {len(result['findings'])}")
        print(f"   Cross-doc risks: {len(result['cross_document_risks'])}")
        print(f"   Disclosure issues: {len(result['disclosure_issues'])}")
        
        print("\n--- MATCHES ---")
        for match in result['matches']:
            print(f"  {match['match_status']}: conf={match['match_confidence']:.2f}")
        
        print("\n--- FINDINGS ---")
        for finding in result['findings']:
            print(f"  [{finding['classification']}] {finding['provision']}")
            if finding.get('company_a_position'):
                a_pos = finding['company_a_position']
                a_val = f"{a_pos.get('percentage', '')}%" if a_pos.get('percentage') else f"${a_pos.get('amount', '')}" if a_pos.get('amount') else a_pos.get('duration', '')
                print(f"    A: {a_val}")
            if finding.get('company_b_position'):
                b_pos = finding['company_b_position']
                b_val = f"{b_pos.get('percentage', '')}%" if b_pos.get('percentage') else f"${b_pos.get('amount', '')}" if b_pos.get('amount') else b_pos.get('duration', '')
                print(f"    B: {b_val}")
            print(f"    Impact: {finding.get('legal_impact', 'N/A')[:100]}")
        
        print("\n--- CROSS-DOCUMENT RISKS ---")
        for risk in result['cross_document_risks']:
            print(f"  [{risk['severity']}] {risk['risk_type']}: {risk['description'][:100]}")
        
        print("\n--- DISCLOSURE ISSUES ---")
        for issue in result['disclosure_issues']:
            print(f"  [{issue['severity']}] {issue['issue_type']}: {issue['description'][:150]}")
        
        verdict = result['verdict']
        if verdict:
            print("\n--- DEAL VERDICT ---")
            print(f"  Overall Assessment: {verdict['overall_assessment']}")
            print(f"  Risk Level: {verdict['overall_risk_level']}")
            print(f"  Score: {verdict['score']}/100")
            print(f"  Material Asymmetries: {verdict['material_asymmetries']}")
            print(f"  Critical Issues: {verdict['critical_issues']}")
            print(f"  Evidence-Backed Findings: {verdict['evidence_backed_findings']}")
            print(f"  Key Asymmetries: {verdict['key_asymmetries']}")
            print(f"  Confidence: {verdict['confidence']:.0%}")
            print(f"  Company A Advantages: {len(verdict.get('company_a_advantages', []))}")
            for adv in verdict.get('company_a_advantages', []):
                print(f"    + {adv[:100]}")
            print(f"  Company A Weaknesses: {len(verdict.get('company_a_weaknesses', []))}")
            for weak in verdict.get('company_a_weaknesses', []):
                print(f"    - {weak[:100]}")
            print(f"  Company B Advantages: {len(verdict.get('company_b_advantages', []))}")
            for adv in verdict.get('company_b_advantages', []):
                print(f"    + {adv[:100]}")
            print(f"  Company B Weaknesses: {len(verdict.get('company_b_weaknesses', []))}")
            for weak in verdict.get('company_b_weaknesses', []):
                print(f"    - {weak[:100]}")
            print(f"  Recommended Actions: {len(verdict.get('recommended_actions', []))}")
            for action in verdict.get('recommended_actions', []):
                print(f"    * {action[:100]}")
            print(f"  Company A Recommendations: {len(verdict.get('company_a_recommendations', []))}")
            for rec in verdict.get('company_a_recommendations', []):
                print(f"    A[{rec['priority']}]: {rec['title']} - {rec['description'][:80]}")
            print(f"  Company B Recommendations: {len(verdict.get('company_b_recommendations', []))}")
            for rec in verdict.get('company_b_recommendations', []):
                print(f"    B[{rec['priority']}]: {rec['title']} - {rec['description'][:80]}")
        
        # 7. Test export
        print("\n9. Testing report export...")
        r = requests.get(f'{base_url}/comparison/{comparison_id}/export', timeout=30)
        print(f"   Export status: {r.status_code}")
        print(f"   Report length: {len(r.text)} chars")
        
        # Save report
        with open('demo_report_full.html', 'w', encoding='utf-8') as f:
            f.write(r.text)
        print("   Report saved to demo_report_full.html")
        
        print("\n" + "=" * 60)
        print("FULL DEMO TRANSACTION COMPLETE")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)