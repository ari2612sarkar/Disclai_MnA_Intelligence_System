#!/usr/bin/env python
"""
DISCLAI End-to-End Demo Script
Tests the complete workflow from transaction creation to deal verdict.
"""
import os
import sys
import tempfile
import time
import threading
import requests
import fitz
import uvicorn
from app.api.main import app


def run_server():
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='error')


def ensure_server(base_url):
    """Use an existing local server when available; otherwise start one."""
    try:
        r = requests.get(f"{base_url}/api/health", timeout=2)
        if r.ok:
            return None
    except requests.RequestException:
        pass

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/api/health", timeout=1)
            if r.ok:
                return thread
        except requests.RequestException:
            time.sleep(0.25)
    raise RuntimeError("Local DISCLAI server did not become healthy on port 8000")



def create_spa_a():
    doc = fitz.open()
    page = doc.new_page()
    spa_text = """SHARE PURCHASE AGREEMENT - COMPANY A (SELLER)
This Share Purchase Agreement is entered into by and between Acme Corporation (Buyer) and Beta Holdings LLC (Seller).
ARTICLE 3: INDEMNIFICATION
Section 3.1 Survival. The representations and warranties of Seller shall survive the Closing for a period of 18 months.
Section 3.3 Limitation of Liability. The aggregate liability of Seller shall not exceed 15% of the Purchase Price. The Cap shall not apply to fraud or willful misconduct.
Section 3.4 Basket. Seller shall have no obligation to indemnify Buyer unless Losses exceed $500,000.
ARTICLE 5: MATERIAL ADVERSE EFFECT
Section 5.1 MAE Definition. MAE means any material adverse effect except: general economic conditions; industry changes; acts of war.
ARTICLE 4: TERMINATION
Section 4.1 Termination. By Buyer if material breach not cured within 30 days.
ARTICLE 6: CLOSING CONDITIONS
Section 6.1 Conditions. Representations true and correct; Seller performed obligations; No MAE.
ARTICLE 7: LITIGATION
Section 7.1 Pending Litigation. ABC Corp v. Beta Holdings LLC is a pending contract dispute involving a claim of $5,000,000."""
    page.insert_text((72, 72), spa_text, fontsize=10)
    f = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    f.close()
    doc.save(f.name)
    doc.close()
    return f.name


def create_spa_b():
    doc = fitz.open()
    page = doc.new_page()
    spa_text = """SHARE PURCHASE AGREEMENT - COMPANY B (BUYER)
This Share Purchase Agreement is entered into by and between Acme Corporation (Buyer) and Beta Holdings LLC (Seller).
ARTICLE 3: INDEMNIFICATION
Section 3.1 Survival. The representations and warranties of Seller shall survive the Closing for a period of 24 months.
Section 3.3 Limitation of Liability. The aggregate liability of Seller shall not exceed 20% of the Purchase Price. The Cap shall not apply to fraud, willful misconduct, or breach of fundamental representations.
Section 3.4 Basket. Seller shall have no obligation to indemnify Buyer unless Losses exceed $250,000.
ARTICLE 5: MATERIAL ADVERSE EFFECT
Section 5.1 MAE Definition. MAE means any material adverse effect except: general economic conditions; industry changes; acts of war; pandemics; regulatory changes.
ARTICLE 4: TERMINATION
Section 4.1 Termination. By Buyer if material breach not cured within 30 days; By Buyer if MAE occurred and continuing.
ARTICLE 6: CLOSING CONDITIONS
Section 6.1 Conditions. Representations true and correct; Seller performed obligations; No MAE; Regulatory approvals received.
 ARTICLE 7: LITIGATION
 Section 7.1 Pending Litigation. ABC Corp v. Beta Holdings LLC is a pending contract dispute involving a claim of $5,000,000.
ARTICLE 2: REPRESENTATIONS
Section 2.1(d) Intellectual Property. Target owns all IP rights necessary for its business."""
    page.insert_text((72, 72), spa_text, fontsize=10)
    f = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    f.close()
    doc.save(f.name)
    doc.close()
    return f.name


def main():
    pdf_a = pdf_b = None
    print("=" * 60)
    print("DISCLAI End-to-End Demo")
    print("=" * 60)
    
    base_url = 'http://127.0.0.1:8000'
    server_thread = ensure_server(base_url)
    
    try:
        # Health check
        r = requests.get(f'{base_url}/api/health', timeout=5)
        print(f"Health check: {r.json()}")
        
        # 1. Create companies
        print("\n1. Creating Company A (Seller)...")
        r = requests.post(f'{base_url}/api/companies', json={'name': 'Beta Holdings LLC', 'role': 'Seller'})
        r.raise_for_status()
        company_a = r.json()
        print(f"   Company A ID: {company_a['id']}")
        
        print("2. Creating Company B (Buyer)...")
        r = requests.post(f'{base_url}/api/companies', json={'name': 'Acme Corporation', 'role': 'Buyer'})
        r.raise_for_status()
        company_b = r.json()
        print(f"   Company B ID: {company_b['id']}")
        
        # 2. Create transaction
        print("3. Creating transaction...")
        r = requests.post(f'{base_url}/api/transactions', json={
            'name': 'Acme-Beta Acquisition',
            'company_a_id': company_a['id'],
            'company_b_id': company_b['id'],
            'company_a_role': 'Seller',
            'company_b_role': 'Buyer',
            'deal_value': 50000000
        })
        r.raise_for_status()
        transaction = r.json()
        print(f"   Transaction ID: {transaction['id']}")
        
        # 3. Upload documents
        pdf_a = create_spa_a()
        pdf_b = create_spa_b()
        
        print("4. Uploading Company A SPA...")
        with open(pdf_a, 'rb') as f:
            files = {'file': ('company_a_spa.pdf', f, 'application/pdf')}
            data = {'transaction_id': transaction['id'], 'company_id': company_a['id'], 'role_in_document': 'Seller'}
            r = requests.post(f'{base_url}/documents/upload', files=files, data=data)
        r.raise_for_status()
        doc_a = r.json()
        print(f"   Document A ID: {doc_a['document_id']}")
        
        print("5. Uploading Company B SPA...")
        with open(pdf_b, 'rb') as f:
            files = {'file': ('company_b_spa.pdf', f, 'application/pdf')}
            data = {'transaction_id': transaction['id'], 'company_id': company_b['id'], 'role_in_document': 'Buyer'}
            r = requests.post(f'{base_url}/documents/upload', files=files, data=data)
        r.raise_for_status()
        doc_b = r.json()
        print(f"   Document B ID: {doc_b['document_id']}")
        
        # 4. Run analysis
        print("6. Running analysis for Company A...")
        r = requests.post(f'{base_url}/api/analysis/run', json={'document_id': doc_a['document_id']})
        r.raise_for_status()
        run_a = r.json()
        print(f"   Run A ID: {run_a['run_id']}")
        
        print("7. Running analysis for Company B...")
        r = requests.post(f'{base_url}/api/analysis/run', json={'document_id': doc_b['document_id']})
        r.raise_for_status()
        run_b = r.json()
        print(f"   Run B ID: {run_b['run_id']}")
        
        # Wait for analysis
        print("8. Waiting for analysis to complete...")
        time.sleep(10)
        
        # 5. Run comparison
        print("9. Running comparison...")
        r = requests.post(f'{base_url}/api/comparison/run', json={
            'transaction_id': transaction['id'],
            'company_a_run_id': run_a['run_id'],
            'company_b_run_id': run_b['run_id']
        })
        r.raise_for_status()
        comparison = r.json()
        print(f"   Comparison ID: {comparison['id']}")
        
        time.sleep(3)
        
        # 6. Get results
        print("10. Getting comparison results...")
        r = requests.get(f'{base_url}/api/comparison/{comparison["id"]}')
        r.raise_for_status()
        result = r.json()
        
        print(f"   Matches: {len(result['matches'])}")
        print(f"   Findings: {len(result['findings'])}")
        print(f"   Cross-doc risks: {len(result['cross_document_risks'])}")
        print(f"   Disclosure issues: {len(result['disclosure_issues'])}")
        
        verdict = result['verdict']
        print("\n11. Deal Verdict:")
        print(f"   Overall Assessment: {verdict['overall_assessment']}")
        print(f"   Risk Level: {verdict['overall_risk_level']}")
        print(f"   Score: {verdict['score']}/100")
        print(f"   Material Asymmetries: {verdict['material_asymmetries']}")
        print(f"   Company A Advantages: {len(verdict['company_a_advantages'])}")
        print(f"   Company B Advantages: {len(verdict['company_b_advantages'])}")
        print(f"   Company A Recommendations: {len(verdict['company_a_recommendations'])}")
        print(f"   Company B Recommendations: {len(verdict['company_b_recommendations'])}")
        
        # 7. Test export
        print("\n12. Testing report export...")
        r = requests.get(f'{base_url}/comparison/{comparison["id"]}/export')
        r.raise_for_status()
        print(f"   Export status: {r.status_code}")
        print(f"   Report length: {len(r.text)} chars")
        
        # Save report
        with open('demo_report.html', 'w') as f:
            f.write(r.text)
        print("   Report saved to demo_report.html")
        
        print("\n" + "=" * 60)
        print("END-TO-END DEMO COMPLETE")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        for pdf in [pdf_a, pdf_b]:
            if os.path.exists(pdf):
                os.unlink(pdf)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
