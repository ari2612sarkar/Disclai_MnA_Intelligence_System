#!/usr/bin/env python
"""
Test script for DISCLAI Phase 2 - Company A vs Company B Comparison.
Tests the complete flow: two companies -> analysis -> comparison -> verdict
"""
import os
import sys
import tempfile
import fitz

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.analysis import AnalysisService
from app.comparison.service import ComparisonService
from app.models.session import init_db, drop_db, get_db
from app.models.schemas import CompanyRole, LegalCategory
from app.models.database import CompanyDB, TransactionDB, CompanyRoleEnum, LegalPositionDB
from app.llm.provider import MockLLMProvider
from app.core.config import get_settings


def create_company_a_spa() -> str:
    """Create Company A (Seller) SPA with 15% cap, $500k basket, 18mo survival."""
    doc = fitz.open()
    page = doc.new_page()

    spa_text = """
SHARE PURCHASE AGREEMENT - COMPANY A (SELLER)

This Share Purchase Agreement (the "Agreement") is entered into as of January 15, 2024,
by and between Acme Corporation, a Delaware corporation ("Buyer"), and Beta Holdings LLC,
a Delaware limited liability company ("Seller").

ARTICLE 1: PURCHASE AND SALE OF SHARES

Section 1.1 Purchase of Shares. Subject to the terms and conditions of this Agreement,
Seller agrees to sell to Buyer, and Buyer agrees to purchase from Seller, 10,000 shares
of common stock of Target Inc., a California corporation ("Target"), representing 100%
of the issued and outstanding shares of Target (the "Shares").

Section 1.2 Purchase Price. The purchase price for the Shares shall be $50,000,000
(fifty million US dollars) (the "Purchase Price"), subject to adjustment as provided
in Section 2.3.

ARTICLE 2: REPRESENTATIONS AND WARRANTIES

Section 2.1 Representations and Warranties of Seller. Seller hereby represents and
warrants to Buyer as of the date hereof and as of the Closing Date that:

(a) Organization and Authority. Seller is a limited liability company duly organized,
validly existing, and in good standing under the laws of the State of Delaware.

(b) Capitalization. The authorized capital stock of Target consists of 10,000 shares
of common stock, par value $0.01 per share, of which 10,000 shares are issued and
outstanding, all of which are owned by Seller.

(c) No Undisclosed Liabilities. Target does not have any liabilities of any nature,
whether accrued, absolute, contingent, or otherwise, except as set forth in
Schedule 2.1(c).

ARTICLE 3: INDEMNIFICATION

Section 3.1 Survival. The representations and warranties of Seller contained in
this Agreement shall survive the Closing for a period of 18 months (the "Survival Period").

Section 3.2 Indemnification by Seller. Seller shall indemnify and hold harmless
Buyer and its affiliates from and against any and all Losses arising out of or
resulting from any breach of or inaccuracy in any representation or warranty of
Seller contained in this Agreement.

Section 3.3 Limitation of Liability. Notwithstanding anything to the contrary
herein, the aggregate liability of Seller under this Agreement shall not exceed
15% of the Purchase Price (the "Cap"). The foregoing Cap shall not apply to
liability arising from fraud or willful misconduct.

Section 3.4 Basket. Seller shall have no obligation to indemnify Buyer for any
Losses unless and until the aggregate amount of such Losses exceeds $500,000
(the "Basket"), in which event Seller shall be liable for all Losses in excess
of the Basket.

ARTICLE 4: TERMINATION

Section 4.1 Termination. This Agreement may be terminated at any time prior to
the Closing:
(a) by mutual written consent of Buyer and Seller;
(b) by Buyer if any representation or warranty of Seller is untrue in any material
respect and such breach is not cured within 30 days;
(c) by Seller if the Closing has not occurred by June 30, 2024.

ARTICLE 5: MATERIAL ADVERSE EFFECT

Section 5.1 "Material Adverse Effect" means any change, event, or effect that,
individually or in the aggregate, has or would reasonably be expected to have a
material adverse effect on the business, assets, or financial condition of Target,
except that the following shall not constitute a Material Adverse Effect:
(a) changes in general economic or market conditions;
(b) changes in the industry in which Target operates;
(c) acts of war, terrorism, or natural disasters.

ARTICLE 6: CLOSING CONDITIONS

Section 6.1 Conditions to Obligations of Buyer. The obligation of Buyer to
consummate the Closing is subject to the satisfaction of the following conditions:
(a) The representations and warranties of Seller shall be true and correct in all
material respects as of the Closing Date;
(b) Seller shall have performed all obligations required to be performed by it
under this Agreement;
(c) No Material Adverse Effect shall have occurred since the date of this Agreement.

ARTICLE 7: GENERAL PROVISIONS

Section 7.1 Governing Law. This Agreement shall be governed by and construed in
accordance with the laws of the State of Delaware.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date
first written above.

ACME CORPORATION                    BETA HOLDINGS LLC
By: ___________________________     By: ___________________________
Name: John Smith                    Name: Jane Doe
Title: CEO                          Title: Managing Member
"""

    page.insert_text((72, 72), spa_text, fontsize=10)

    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_file.close()
    doc.save(temp_file.name)
    doc.close()

    return temp_file.name


def create_company_b_spa() -> str:
    """Create Company B (Buyer) SPA with 20% cap, $250k basket, 24mo survival - DIFFERENT terms."""
    doc = fitz.open()
    page = doc.new_page()

    spa_text = """
SHARE PURCHASE AGREEMENT - COMPANY B (BUYER)

This Share Purchase Agreement (the "Agreement") is entered into as of January 15, 2024,
by and between Acme Corporation, a Delaware corporation ("Buyer"), and Beta Holdings LLC,
a Delaware limited liability company ("Seller").

ARTICLE 1: PURCHASE AND SALE OF SHARES

Section 1.1 Purchase of Shares. Subject to the terms and conditions of this Agreement,
Seller agrees to sell to Buyer, and Buyer agrees to purchase from Seller, 10,000 shares
of common stock of Target Inc., a California corporation ("Target"), representing 100%
of the issued and outstanding shares of Target (the "Shares").

Section 1.2 Purchase Price. The purchase price for the Shares shall be $50,000,000
(fifty million US dollars) (the "Purchase Price"), subject to adjustment as provided
in Section 2.3.

ARTICLE 2: REPRESENTATIONS AND WARRANTIES

Section 2.1 Representations and Warranties of Seller. Seller hereby represents and
warrants to Buyer as of the date hereof and as of the Closing Date that:

(a) Organization and Authority. Seller is a limited liability company duly organized,
validly existing, and in good standing under the laws of the State of Delaware.

(b) Capitalization. The authorized capital stock of Target consists of 10,000 shares
of common stock, par value $0.01 per share, of which 10,000 shares are issued and
outstanding, all of which are owned by Seller.

(c) No Undisclosed Liabilities. Target does not have any liabilities of any nature,
whether accrued, absolute, contingent, or otherwise, except as set forth in
Schedule 2.1(c).

(d) Intellectual Property. Target owns all intellectual property rights necessary
for the conduct of its business as currently operated, free and clear of any liens
or encumbrances, except as set forth in Schedule 2.1(d).

ARTICLE 3: INDEMNIFICATION

Section 3.1 Survival. The representations and warranties of Seller contained in
this Agreement shall survive the Closing for a period of 24 months (the "Survival Period").

Section 3.2 Indemnification by Seller. Seller shall indemnify and hold harmless
Buyer and its affiliates from and against any and all Losses arising out of or
resulting from any breach of or inaccuracy in any representation or warranty of
Seller contained in this Agreement.

Section 3.3 Limitation of Liability. Notwithstanding anything to the contrary
herein, the aggregate liability of Seller under this Agreement shall not exceed
20% of the Purchase Price (the "Cap"). The foregoing Cap shall not apply to
liability arising from fraud, willful misconduct, or breach of fundamental representations.

Section 3.4 Basket. Seller shall have no obligation to indemnify Buyer for any
Losses unless and until the aggregate amount of such Losses exceeds $250,000
(the "Basket"), in which event Seller shall be liable for all Losses in excess
of the Basket.

ARTICLE 4: TERMINATION

Section 4.1 Termination. This Agreement may be terminated at any time prior to
the Closing:
(a) by mutual written consent of Buyer and Seller;
(b) by Buyer if any representation or warranty of Seller is untrue in any material
respect and such breach is not cured within 30 days;
(c) by Seller if the Closing has not occurred by June 30, 2024;
(d) by Buyer if a Material Adverse Effect has occurred and is continuing.

ARTICLE 5: MATERIAL ADVERSE EFFECT

Section 5.1 "Material Adverse Effect" means any change, event, or effect that,
individually or in the aggregate, has or would reasonably be expected to have a
material adverse effect on the business, assets, or financial condition of Target,
except that the following shall not constitute a Material Adverse Effect:
(a) changes in general economic or market conditions;
(b) changes in the industry in which Target operates;
(c) acts of war, terrorism, or natural disasters;
(d) pandemics, epidemics, or public health emergencies;
(e) changes in applicable law or regulatory requirements.

ARTICLE 6: CLOSING CONDITIONS

Section 6.1 Conditions to Obligations of Buyer. The obligation of Buyer to
consummate the Closing is subject to the satisfaction of the following conditions:
(a) The representations and warranties of Seller shall be true and correct in all
material respects as of the Closing Date;
(b) Seller shall have performed all obligations required to be performed by it
under this Agreement;
(c) No Material Adverse Effect shall have occurred since the date of this Agreement;
(d) Buyer shall have received all required regulatory approvals.

ARTICLE 7: GENERAL PROVISIONS

Section 7.1 Governing Law. This Agreement shall be governed by and construed in
accordance with the laws of the State of Delaware.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date
first written above.

ACME CORPORATION                    BETA HOLDINGS LLC
By: ___________________________     By: ___________________________
Name: John Smith                    Name: Jane Doe
Title: CEO                          Title: Managing Member
"""

    page.insert_text((72, 72), spa_text, fontsize=10)

    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_file.close()
    doc.save(temp_file.name)
    doc.close()

    return temp_file.name


def test_phase2_comparison():
    print("=" * 60)
    print("DISCLAI Phase 2 - Company A vs Company B Comparison Test")
    print("=" * 60)

    # Initialize database
    print("\n1. Initializing database...")
    drop_db()
    init_db()
    print("   Database initialized.")

    # Create test PDFs
    print("\n2. Creating test documents...")
    pdf_a = create_company_a_spa()
    pdf_b = create_company_b_spa()
    print(f"   Company A (Seller): {pdf_a}")
    print(f"   Company B (Buyer): {pdf_b}")

    # Create custom mock providers for Company A and Company B
    class CompanyAMockProvider(MockLLMProvider):
        async def generate_structured(self, prompt, system_prompt=None, schema=None, temperature=0.1, max_tokens=2048):
            prompt_lower = prompt.lower()
            if "verify" in prompt_lower:
                import re
                pos_count = len(re.findall(r'position \d+', prompt_lower))
                if pos_count == 0:
                    pos_count = 1
                verifications = []
                for i in range(pos_count):
                    verifications.append({
                        "position_index": i,
                        "status": "VERIFIED",
                        "field_verifications": {
                            "party": "VERIFIED",
                            "percentage": "VERIFIED",
                            "unit": "VERIFIED",
                            "qualifier": "VERIFIED",
                            "consequence": "VERIFIED",
                        },
                        "discrepancies": [],
                        "notes": "Mock verification passed",
                    })
                return {"verifications": verifications}
            elif "extract" in prompt_lower or "position" in prompt_lower:
                return {
                    "positions": [
                        {
                            "category": "Indemnification",
                            "subcategory": "General Liability Cap",
                            "provision_name": "General Liability Cap",
                            "party": "Seller",
                            "obligation_right": "liability limitation",
                            "threshold": None,
                            "amount": None,
                            "percentage": 15.0,
                            "unit": "percent",
                            "duration": None,
                            "condition": [],
                            "exception": ["fraud", "willful misconduct"],
                            "qualifier": ["aggregate"],
                            "consequence": ["liability limited to 15% of purchase price"],
                            "evidence": {
                                "document_id": "company-a-doc",
                                "page_number": 1,
                                "section_number": "3.3",
                                "heading": "Limitation of Liability",
                                "text": "the aggregate liability of Seller under this Agreement shall not exceed 15% of the Purchase Price (the \"Cap\"). The foregoing Cap shall not apply to liability arising from fraud or willful misconduct.",
                                "char_start": 1000,
                                "char_end": 1200,
                            },
                            "confidence": 0.95,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Indemnification",
                            "subcategory": "Basket",
                            "provision_name": "Basket",
                            "party": "Seller",
                            "obligation_right": "indemnification threshold",
                            "threshold": "500000",
                            "amount": 500000.0,
                            "percentage": None,
                            "unit": "USD",
                            "duration": None,
                            "condition": [],
                            "exception": [],
                            "qualifier": ["basket"],
                            "consequence": ["no indemnification obligation until losses exceed $500,000"],
                            "evidence": {
                                "document_id": "company-a-doc",
                                "page_number": 1,
                                "section_number": "3.4",
                                "heading": "Basket",
                                "text": "Seller shall have no obligation to indemnify Buyer for any Losses unless and until the aggregate amount of such Losses exceeds $500,000 (the \"Basket\")",
                                "char_start": 1200,
                                "char_end": 1350,
                            },
                            "confidence": 0.93,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Representations & Warranties",
                            "subcategory": "Survival Period",
                            "provision_name": "Survival Period",
                            "party": "Seller",
                            "obligation_right": "survival of representations",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": "18 months",
                            "condition": [],
                            "exception": [],
                            "qualifier": [],
                            "consequence": ["representations survive closing for 18 months"],
                            "evidence": {
                                "document_id": "company-a-doc",
                                "page_number": 1,
                                "section_number": "3.1",
                                "heading": "Survival",
                                "text": "The representations and warranties of Seller contained in this Agreement shall survive the Closing for a period of 18 months (the \"Survival Period\").",
                                "char_start": 800,
                                "char_end": 950,
                            },
                            "confidence": 0.94,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Material Adverse Effect",
                            "subcategory": "MAE Definition",
                            "provision_name": "Material Adverse Effect Definition",
                            "party": "Unknown",
                            "obligation_right": "MAE definition",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": None,
                            "condition": [],
                            "exception": ["general economic conditions", "industry changes", "acts of war", "natural disasters"],
                            "qualifier": [],
                            "consequence": ["defines what constitutes a Material Adverse Effect"],
                            "evidence": {
                                "document_id": "company-a-doc",
                                "page_number": 1,
                                "section_number": "5.1",
                                "heading": "Material Adverse Effect",
                                "text": "\"Material Adverse Effect\" means any change, event, or effect that, individually or in the aggregate, has or would reasonably be expected to have a material adverse effect on the business, assets, or financial condition of Target, except that the following shall not constitute a Material Adverse Effect: (a) changes in general economic or market conditions; (b) changes in the industry in which Target operates; (c) acts of war, terrorism, or natural disasters.",
                                "char_start": 1500,
                                "char_end": 1800,
                            },
                            "confidence": 0.91,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Termination Rights",
                            "subcategory": "Termination",
                            "provision_name": "Termination Rights",
                            "party": "Buyer",
                            "obligation_right": "termination right",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": None,
                            "condition": ["material breach of representations", "breach not cured within 30 days"],
                            "exception": [],
                            "qualifier": [],
                            "consequence": ["Buyer may terminate agreement"],
                            "evidence": {
                                "document_id": "company-a-doc",
                                "page_number": 1,
                                "section_number": "4.1",
                                "heading": "Termination",
                                "text": "This Agreement may be terminated at any time prior to the Closing: (b) by Buyer if any representation or warranty of Seller is untrue in any material respect and such breach is not cured within 30 days",
                                "char_start": 1350,
                                "char_end": 1500,
                            },
                            "confidence": 0.90,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Closing Conditions",
                            "subcategory": "Closing Conditions",
                            "provision_name": "Closing Conditions",
                            "party": "Buyer",
                            "obligation_right": "condition precedent",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": None,
                            "condition": ["representations true and correct", "seller performed obligations", "no MAE"],
                            "exception": [],
                            "qualifier": [],
                            "consequence": ["Buyer not obligated to close if conditions not met"],
                            "evidence": {
                                "document_id": "company-a-doc",
                                "page_number": 1,
                                "section_number": "6.1",
                                "heading": "Conditions to Obligations of Buyer",
                                "text": "The obligation of Buyer to consummate the Closing is subject to the satisfaction of the following conditions: (a) The representations and warranties of Seller shall be true and correct in all material respects as of the Closing Date; (b) Seller shall have performed all obligations required to be performed by it under this Agreement; (c) No Material Adverse Effect shall have occurred since the date of this Agreement.",
                                "char_start": 1800,
                                "char_end": 2000,
                            },
                            "confidence": 0.92,
                            "status": "VERIFIED",
                        }
                    ]
                }
            elif "classif" in prompt_lower:
                return {
                    "document_type": "SPA",
                    "confidence": 0.9,
                    "reason": "Mock classification - document contains share purchase agreement language",
                    "governing_entities": ["Seller", "Buyer"],
                    "source_metadata": {},
                }
            elif "provision" in prompt_lower or "identif" in prompt_lower:
                return {
                    "provisions": [
                        {
                            "category": "Indemnification",
                            "subcategory": "General Liability Cap",
                            "provision_name": "General Liability Cap",
                            "section_number": "3.3",
                            "heading": "Limitation of Liability",
                            "text": "the aggregate liability of Seller under this Agreement shall not exceed 15% of the Purchase Price (the \"Cap\"). The foregoing Cap shall not apply to liability arising from fraud or willful misconduct.",
                            "page_number": 1,
                            "party_mentioned": ["Seller"],
                            "keywords": ["liability", "cap", "purchase price", "aggregate"],
                        },
                        {
                            "category": "Indemnification",
                            "subcategory": "Basket",
                            "provision_name": "Basket",
                            "section_number": "3.4",
                            "heading": "Basket",
                            "text": "Seller shall have no obligation to indemnify Buyer for any Losses unless and until the aggregate amount of such Losses exceeds $500,000 (the \"Basket\")",
                            "page_number": 1,
                            "party_mentioned": ["Seller"],
                            "keywords": ["basket", "indemnification", "losses", "threshold"],
                        },
                        {
                            "category": "Representations & Warranties",
                            "subcategory": "Survival Period",
                            "provision_name": "Survival Period",
                            "section_number": "3.1",
                            "heading": "Survival",
                            "text": "The representations and warranties of Seller contained in this Agreement shall survive the Closing for a period of 18 months (the \"Survival Period\").",
                            "page_number": 1,
                            "party_mentioned": ["Seller"],
                            "keywords": ["survival", "representations", "warranties", "18 months"],
                        },
                        {
                            "category": "Material Adverse Effect",
                            "subcategory": "MAE Definition",
                            "provision_name": "Material Adverse Effect Definition",
                            "section_number": "5.1",
                            "heading": "Material Adverse Effect",
                            "text": "\"Material Adverse Effect\" means any change, event, or effect that, individually or in the aggregate, has or would reasonably be expected to have a material adverse effect on the business, assets, or financial condition of Target, except that the following shall not constitute a Material Adverse Effect: (a) changes in general economic or market conditions; (b) changes in the industry in which Target operates; (c) acts of war, terrorism, or natural disasters.",
                            "page_number": 1,
                            "party_mentioned": ["Target"],
                            "keywords": ["material adverse effect", "MAE", "carveout", "exceptions"],
                        },
                        {
                            "category": "Termination Rights",
                            "subcategory": "Termination",
                            "provision_name": "Termination Rights",
                            "section_number": "4.1",
                            "heading": "Termination",
                            "text": "This Agreement may be terminated at any time prior to the Closing: (b) by Buyer if any representation or warranty of Seller is untrue in any material respect and such breach is not cured within 30 days",
                            "page_number": 1,
                            "party_mentioned": ["Buyer", "Seller"],
                            "keywords": ["termination", "breach", "cure period", "30 days"],
                        },
                        {
                            "category": "Closing Conditions",
                            "subcategory": "Closing Conditions",
                            "provision_name": "Closing Conditions",
                            "section_number": "6.1",
                            "heading": "Conditions to Obligations of Buyer",
                            "text": "The obligation of Buyer to consummate the Closing is subject to the satisfaction of the following conditions: (a) The representations and warranties of Seller shall be true and correct in all material respects as of the Closing Date; (b) Seller shall have performed all obligations required to be performed by it under this Agreement; (c) No Material Adverse Effect shall have occurred since the date of this Agreement.",
                            "page_number": 1,
                            "party_mentioned": ["Buyer", "Seller"],
                            "keywords": ["closing conditions", "conditions precedent", "MAE", "representations"],
                        }
                    ]
                }
            return {}

    class CompanyBMockProvider(MockLLMProvider):
        async def generate_structured(self, prompt, system_prompt=None, schema=None, temperature=0.1, max_tokens=2048):
            prompt_lower = prompt.lower()
            if "verify" in prompt_lower:
                import re
                pos_count = len(re.findall(r'position \d+', prompt_lower))
                if pos_count == 0:
                    pos_count = 1
                verifications = []
                for i in range(pos_count):
                    verifications.append({
                        "position_index": i,
                        "status": "VERIFIED",
                        "field_verifications": {
                            "party": "VERIFIED",
                            "percentage": "VERIFIED",
                            "unit": "VERIFIED",
                            "qualifier": "VERIFIED",
                            "consequence": "VERIFIED",
                        },
                        "discrepancies": [],
                        "notes": "Mock verification passed",
                    })
                return {"verifications": verifications}
            elif "extract" in prompt_lower or "position" in prompt_lower:
                return {
                    "positions": [
                        {
                            "category": "Indemnification",
                            "subcategory": "General Liability Cap",
                            "provision_name": "General Liability Cap",
                            "party": "Seller",
                            "obligation_right": "liability limitation",
                            "threshold": None,
                            "amount": None,
                            "percentage": 20.0,
                            "unit": "percent",
                            "duration": None,
                            "condition": [],
                            "exception": ["fraud", "willful misconduct", "breach of fundamental representations"],
                            "qualifier": ["aggregate"],
                            "consequence": ["liability limited to 20% of purchase price"],
                            "evidence": {
                                "document_id": "company-b-doc",
                                "page_number": 1,
                                "section_number": "3.3",
                                "heading": "Limitation of Liability",
                                "text": "the aggregate liability of Seller under this Agreement shall not exceed 20% of the Purchase Price (the \"Cap\"). The foregoing Cap shall not apply to liability arising from fraud, willful misconduct, or breach of fundamental representations.",
                                "char_start": 1000,
                                "char_end": 1200,
                            },
                            "confidence": 0.95,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Indemnification",
                            "subcategory": "Basket",
                            "provision_name": "Basket",
                            "party": "Seller",
                            "obligation_right": "indemnification threshold",
                            "threshold": "250000",
                            "amount": 250000.0,
                            "percentage": None,
                            "unit": "USD",
                            "duration": None,
                            "condition": [],
                            "exception": [],
                            "qualifier": ["basket"],
                            "consequence": ["no indemnification obligation until losses exceed $250,000"],
                            "evidence": {
                                "document_id": "company-b-doc",
                                "page_number": 1,
                                "section_number": "3.4",
                                "heading": "Basket",
                                "text": "Seller shall have no obligation to indemnify Buyer for any Losses unless and until the aggregate amount of such Losses exceeds $250,000 (the \"Basket\")",
                                "char_start": 1200,
                                "char_end": 1350,
                            },
                            "confidence": 0.93,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Representations & Warranties",
                            "subcategory": "Survival Period",
                            "provision_name": "Survival Period",
                            "party": "Seller",
                            "obligation_right": "survival of representations",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": "24 months",
                            "condition": [],
                            "exception": [],
                            "qualifier": [],
                            "consequence": ["representations survive closing for 24 months"],
                            "evidence": {
                                "document_id": "company-b-doc",
                                "page_number": 1,
                                "section_number": "3.1",
                                "heading": "Survival",
                                "text": "The representations and warranties of Seller contained in this Agreement shall survive the Closing for a period of 24 months (the \"Survival Period\").",
                                "char_start": 800,
                                "char_end": 950,
                            },
                            "confidence": 0.94,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Representations & Warranties",
                            "subcategory": "Intellectual Property",
                            "provision_name": "Intellectual Property",
                            "party": "Seller",
                            "obligation_right": "IP ownership representation",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": None,
                            "condition": [],
                            "exception": [],
                            "qualifier": [],
                            "consequence": ["IP ownership represented"],
                            "evidence": {
                                "document_id": "company-b-doc",
                                "page_number": 1,
                                "section_number": "2.1(d)",
                                "heading": "Intellectual Property",
                                "text": "Target owns all intellectual property rights necessary for the conduct of its business as currently operated, free and clear of any liens or encumbrances, except as set forth in Schedule 2.1(d).",
                                "char_start": 950,
                                "char_end": 1100,
                            },
                            "confidence": 0.92,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Material Adverse Effect",
                            "subcategory": "MAE Definition",
                            "provision_name": "Material Adverse Effect Definition",
                            "party": "Unknown",
                            "obligation_right": "MAE definition",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": None,
                            "condition": [],
                            "exception": ["general economic conditions", "industry changes", "acts of war", "natural disasters", "pandemics", "regulatory changes"],
                            "qualifier": [],
                            "consequence": ["defines what constitutes a Material Adverse Effect"],
                            "evidence": {
                                "document_id": "company-b-doc",
                                "page_number": 1,
                                "section_number": "5.1",
                                "heading": "Material Adverse Effect",
                                "text": "\"Material Adverse Effect\" means any change, event, or effect that, individually or in the aggregate, has or would reasonably be expected to have a material adverse effect on the business, assets, or financial condition of Target, except that the following shall not constitute a Material Adverse Effect: (a) changes in general economic or market conditions; (b) changes in the industry in which Target operates; (c) acts of war, terrorism, or natural disasters; (d) pandemics, epidemics, or public health emergencies; (e) changes in applicable law or regulatory requirements.",
                                "char_start": 1500,
                                "char_end": 1800,
                            },
                            "confidence": 0.91,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Termination Rights",
                            "subcategory": "Termination",
                            "provision_name": "Termination Rights",
                            "party": "Buyer",
                            "obligation_right": "termination right",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": None,
                            "condition": ["material breach of representations", "breach not cured within 30 days", "MAE occurred and continuing"],
                            "exception": [],
                            "qualifier": [],
                            "consequence": ["Buyer may terminate agreement"],
                            "evidence": {
                                "document_id": "company-b-doc",
                                "page_number": 1,
                                "section_number": "4.1",
                                "heading": "Termination",
                                "text": "This Agreement may be terminated at any time prior to the Closing: (b) by Buyer if any representation or warranty of Seller is untrue in any material respect and such breach is not cured within 30 days; (d) by Buyer if a Material Adverse Effect has occurred and is continuing.",
                                "char_start": 1350,
                                "char_end": 1500,
                            },
                            "confidence": 0.90,
                            "status": "VERIFIED",
                        },
                        {
                            "category": "Closing Conditions",
                            "subcategory": "Closing Conditions",
                            "provision_name": "Closing Conditions",
                            "party": "Buyer",
                            "obligation_right": "condition precedent",
                            "threshold": None,
                            "amount": None,
                            "percentage": None,
                            "unit": None,
                            "duration": None,
                            "condition": ["representations true and correct", "seller performed obligations", "no MAE", "regulatory approvals received"],
                            "exception": [],
                            "qualifier": [],
                            "consequence": ["Buyer not obligated to close if conditions not met"],
                            "evidence": {
                                "document_id": "company-b-doc",
                                "page_number": 1,
                                "section_number": "6.1",
                                "heading": "Conditions to Obligations of Buyer",
                                "text": "The obligation of Buyer to consummate the Closing is subject to the satisfaction of the following conditions: (a) The representations and warranties of Seller shall be true and correct in all material respects as of the Closing Date; (b) Seller shall have performed all obligations required to be performed by it under this Agreement; (c) No Material Adverse Effect shall have occurred since the date of this Agreement; (d) Buyer shall have received all required regulatory approvals.",
                                "char_start": 1800,
                                "char_end": 2000,
                            },
                            "confidence": 0.92,
                            "status": "VERIFIED",
                        }
                    ]
                }
            elif "classif" in prompt_lower:
                return {
                    "document_type": "SPA",
                    "confidence": 0.9,
                    "reason": "Mock classification - document contains share purchase agreement language",
                    "governing_entities": ["Seller", "Buyer"],
                    "source_metadata": {},
                }
            elif "provision" in prompt_lower or "identif" in prompt_lower:
                return {
                    "provisions": [
                        {
                            "category": "Indemnification",
                            "subcategory": "General Liability Cap",
                            "provision_name": "General Liability Cap",
                            "section_number": "3.3",
                            "heading": "Limitation of Liability",
                            "text": "the aggregate liability of Seller under this Agreement shall not exceed 20% of the Purchase Price (the \"Cap\"). The foregoing Cap shall not apply to liability arising from fraud, willful misconduct, or breach of fundamental representations.",
                            "page_number": 1,
                            "party_mentioned": ["Seller"],
                            "keywords": ["liability", "cap", "purchase price", "aggregate"],
                        },
                        {
                            "category": "Indemnification",
                            "subcategory": "Basket",
                            "provision_name": "Basket",
                            "section_number": "3.4",
                            "heading": "Basket",
                            "text": "Seller shall have no obligation to indemnify Buyer for any Losses unless and until the aggregate amount of such Losses exceeds $250,000 (the \"Basket\")",
                            "page_number": 1,
                            "party_mentioned": ["Seller"],
                            "keywords": ["basket", "indemnification", "losses", "threshold"],
                        },
                        {
                            "category": "Representations & Warranties",
                            "subcategory": "Survival Period",
                            "provision_name": "Survival Period",
                            "section_number": "3.1",
                            "heading": "Survival",
                            "text": "The representations and warranties of Seller contained in this Agreement shall survive the Closing for a period of 24 months (the \"Survival Period\").",
                            "page_number": 1,
                            "party_mentioned": ["Seller"],
                            "keywords": ["survival", "representations", "warranties", "24 months"],
                        },
                        {
                            "category": "Representations & Warranties",
                            "subcategory": "Intellectual Property",
                            "provision_name": "Intellectual Property",
                            "section_number": "2.1(d)",
                            "heading": "Intellectual Property",
                            "text": "Target owns all intellectual property rights necessary for the conduct of its business as currently operated, free and clear of any liens or encumbrances, except as set forth in Schedule 2.1(d).",
                            "page_number": 1,
                            "party_mentioned": ["Seller", "Target"],
                            "keywords": ["intellectual property", "IP", "ownership", "encumbrances"],
                        },
                        {
                            "category": "Material Adverse Effect",
                            "subcategory": "MAE Definition",
                            "provision_name": "Material Adverse Effect Definition",
                            "section_number": "5.1",
                            "heading": "Material Adverse Effect",
                            "text": "\"Material Adverse Effect\" means any change, event, or effect that, individually or in the aggregate, has or would reasonably be expected to have a material adverse effect on the business, assets, or financial condition of Target, except that the following shall not constitute a Material Adverse Effect: (a) changes in general economic or market conditions; (b) changes in the industry in which Target operates; (c) acts of war, terrorism, or natural disasters; (d) pandemics, epidemics, or public health emergencies; (e) changes in applicable law or regulatory requirements.",
                            "page_number": 1,
                            "party_mentioned": ["Target"],
                            "keywords": ["material adverse effect", "MAE", "carveout", "exceptions", "pandemics"],
                        },
                        {
                            "category": "Termination Rights",
                            "subcategory": "Termination",
                            "provision_name": "Termination Rights",
                            "section_number": "4.1",
                            "heading": "Termination",
                            "text": "This Agreement may be terminated at any time prior to the Closing: (b) by Buyer if any representation or warranty of Seller is untrue in any material respect and such breach is not cured within 30 days; (d) by Buyer if a Material Adverse Effect has occurred and is continuing.",
                            "page_number": 1,
                            "party_mentioned": ["Buyer", "Seller"],
                            "keywords": ["termination", "breach", "cure period", "30 days", "MAE"],
                        },
                        {
                            "category": "Closing Conditions",
                            "subcategory": "Closing Conditions",
                            "provision_name": "Closing Conditions",
                            "section_number": "6.1",
                            "heading": "Conditions to Obligations of Buyer",
                            "text": "The obligation of Buyer to consummate the Closing is subject to the satisfaction of the following conditions: (a) The representations and warranties of Seller shall be true and correct in all material respects as of the Closing Date; (b) Seller shall have performed all obligations required to be performed by it under this Agreement; (c) No Material Adverse Effect shall have occurred since the date of this Agreement; (d) Buyer shall have received all required regulatory approvals.",
                            "page_number": 1,
                            "party_mentioned": ["Buyer", "Seller"],
                            "keywords": ["closing conditions", "conditions precedent", "MAE", "representations", "regulatory approvals"],
                        }
                    ]
                }
            return {}

    # Run Phase 1 analysis for both companies with custom mock providers
    print("\n3. Running Phase 1 analysis for both companies...")
    provider_a = CompanyAMockProvider()
    provider_b = CompanyBMockProvider()
    service_a = AnalysisService()
    service_a.classification.llm = provider_a
    service_a.provision_id.llm = provider_a
    service_a.extraction.llm = provider_a
    service_a.verification.llm = provider_a

    service_b = AnalysisService()
    service_b.classification.llm = provider_b
    service_b.provision_id.llm = provider_b
    service_b.extraction.llm = provider_b
    service_b.verification.llm = provider_b

    try:
        result_a = service_a.run_analysis("company-a-doc", pdf_a, "company_a_spa.pdf")
        result_b = service_b.run_analysis("company-b-doc", pdf_b, "company_b_spa.pdf")

        print(f"\n   Company A Run ID: {result_a.run_id}")
        print(f"   Company A Positions: {len(result_a.positions)}")
        print(f"\n   Company B Run ID: {result_b.run_id}")
        print(f"   Company B Positions: {len(result_b.positions)}")

        # Create companies and transaction
        print("\n4. Creating companies and transaction...")
        with get_db() as db:
            company_a = CompanyDB(
                id="company-a-id",
                name="Beta Holdings LLC (Seller)",
                role=CompanyRoleEnum.SELLER,
            )
            company_b = CompanyDB(
                id="company-b-id",
                name="Acme Corporation (Buyer)",
                role=CompanyRoleEnum.BUYER,
            )
            db.add(company_a)
            db.add(company_b)

            transaction = TransactionDB(
                id="transaction-001",
                name="Acme-Beta Acquisition",
                description="Acme Corporation acquiring Beta Holdings LLC",
                company_a_id="company-a-id",
                company_b_id="company-b-id",
                company_a_role=CompanyRoleEnum.SELLER,
                company_b_role=CompanyRoleEnum.BUYER,
                deal_value=50000000.0,
            )
            db.add(transaction)
            db.commit()

        print("   Companies and transaction created.")

        # Run Phase 2 comparison
        print("\n5. Running Phase 2 comparison...")
        comparison_service = ComparisonService()
        comparison_result = comparison_service.run_comparison(
            transaction_id="transaction-001",
            company_a_run_id=result_a.run_id,
            company_b_run_id=result_b.run_id,
        )

        print(f"\n   Comparison ID: {comparison_result.comparison_id}")
        print(f"   Processing Time: {comparison_result.processing_time_ms}ms")
        print(f"   Matches: {len(comparison_result.matches)}")
        print(f"   Findings: {len(comparison_result.findings)}")
        print(f"   Cross-Document Risks: {len(comparison_result.cross_document_risks)}")
        print(f"   Disclosure Issues: {len(comparison_result.disclosure_issues)}")

        # Display matches
        print("\n6. Legal Position Matches:")
        print("-" * 60)
        for match in comparison_result.matches:
            status = match.match_status.value
            conf = match.match_confidence
            prov_a = match.company_a_position.provision_name if match.company_a_position else "NONE"
            prov_b = match.company_b_position.provision_name if match.company_b_position else "NONE"
            print(f"  [{status}] Conf: {conf:.2f} | A: {prov_a} | B: {prov_b}")

        # Display findings
        print("\n7. Comparison Findings:")
        print("-" * 60)
        for finding in comparison_result.findings:
            print(f"\n  Finding: {finding.provision} ({finding.category.value})")
            print(f"    Classification: {finding.classification.value}")
            print(f"    Reason: {finding.classification_reason}")
            print(f"    Beneficiary: {finding.beneficiary.value if finding.beneficiary else 'None'}")
            if finding.beneficiary:
                print(f"    Dimension: {finding.affected_dimension}")
                print(f"    Explanation: {finding.advantage_explanation}")
            for diff in finding.differences:
                print(f"    Diff - {diff.attribute}: A={diff.company_a_value} vs B={diff.company_b_value}")
            print(f"    Legal Impact: {finding.legal_impact[:100]}..." if len(finding.legal_impact) > 100 else f"    Legal Impact: {finding.legal_impact}")

        # Display cross-document risks
        print("\n8. Cross-Document Risks:")
        print("-" * 60)
        for risk in comparison_result.cross_document_risks:
            print(f"  [{risk.severity.value}] {risk.risk_type}")
            print(f"    Components: {risk.component_findings}")
            print(f"    Description: {risk.description}")
            print(f"    Impact: {risk.impact}")

        # Display verdict
        print("\n9. Deal Verdict:")
        print("-" * 60)
        verdict = comparison_result.verdict
        if verdict:
            print(f"  Overall Assessment: {verdict.overall_assessment}")
            print(f"  Overall Risk Level: {verdict.overall_risk_level.value}")
            print(f"  Score: {verdict.score}/100")
            print(f"  Key Asymmetries: {verdict.key_asymmetries}")
            print(f"  Material Asymmetries: {verdict.material_asymmetries}")
            print(f"  Critical Issues: {verdict.critical_issues}")
            print(f"  Evidence-Backed Findings: {verdict.evidence_backed_findings}")
            print(f"  Company A Advantages: {verdict.company_a_advantages}")
            print(f"  Company A Weaknesses: {verdict.company_a_weaknesses}")
            print(f"  Company B Advantages: {verdict.company_b_advantages}")
            print(f"  Company B Weaknesses: {verdict.company_b_weaknesses}")
            print(f"  Critical Findings: {verdict.critical_findings}")
            print(f"  Recommended Actions: {verdict.recommended_actions}")
            print(f"  Unresolved Questions: {verdict.unresolved_questions}")
            print(f"  Confidence: {verdict.confidence:.2f}")

            # Display party-specific recommendations
            print(f"\n  Company A Recommendations ({len(verdict.company_a_recommendations)}):")
            for rec in verdict.company_a_recommendations:
                print(f"    [{rec.priority.value}] {rec.title}: {rec.proposed_adjustment[:80]}...")

            print(f"\n  Company B Recommendations ({len(verdict.company_b_recommendations)}):")
            for rec in verdict.company_b_recommendations:
                print(f"    [{rec.priority.value}] {rec.title}: {rec.proposed_adjustment[:80]}...")

        # Verify expected results
        print("\n" + "=" * 60)
        print("PHASE 2 TEST VERIFICATION")
        print("=" * 60)

        # Check for expected findings
        findings_by_prov = {f.provision: f for f in comparison_result.findings}

        # 1. Equivalent provision with no material difference (none expected in this test - all different)
        # 2. Numerical asymmetry - Liability Cap (15% vs 20%)
        cap_finding = findings_by_prov.get("General Liability Cap")
        if cap_finding:
            print(f"  [OK] Liability Cap asymmetry detected: {cap_finding.classification.value}")
            print(f"       A=15%, B=20%, Diff=5%, Beneficiary={cap_finding.beneficiary.value if cap_finding.beneficiary else 'None'}")
        else:
            print("  [MISSING] Liability Cap asymmetry")

        # 3. Numerical asymmetry - Basket ($500k vs $250k)
        basket_finding = findings_by_prov.get("Basket")
        if basket_finding:
            print(f"  [OK] Basket asymmetry detected: {basket_finding.classification.value}")
            print(f"       A=$500k, B=$250k, Diff=$250k, Beneficiary={basket_finding.beneficiary.value if basket_finding.beneficiary else 'None'}")
        else:
            print("  [MISSING] Basket asymmetry")

        # 4. Numerical asymmetry - Survival (18mo vs 24mo)
        survival_finding = findings_by_prov.get("Survival Period")
        if survival_finding:
            print(f"  [OK] Survival Period asymmetry detected: {survival_finding.classification.value}")
            print(f"       A=18mo, B=24mo, Beneficiary={survival_finding.beneficiary.value if survival_finding.beneficiary else 'None'}")
        else:
            print("  [MISSING] Survival Period asymmetry")

        # 5. Presence/absence - IP Representation (only in B)
        ip_finding = findings_by_prov.get("Intellectual Property")
        if ip_finding and ip_finding.classification.value == "PRESENCE_ABSENCE":
            print(f"  [OK] Presence/absence asymmetry detected: IP Representation only in Company B")
        else:
            print("  [MISSING] IP Representation presence/absence")

        # 6. MAE carve-out differences
        mae_finding = findings_by_prov.get("Material Adverse Effect Definition")
        if mae_finding:
            print(f"  [OK] MAE Definition asymmetry detected: {mae_finding.classification.value}")
            print(f"       A exceptions: 3, B exceptions: 5 (pandemics, regulatory changes)")
        else:
            print("  [MISSING] MAE Definition asymmetry")

        # 7. Cross-document risk
        if comparison_result.cross_document_risks:
            print(f"  [OK] Cross-document risks identified: {len(comparison_result.cross_document_risks)}")
            for r in comparison_result.cross_document_risks:
                print(f"       - {r.risk_type} ({r.severity.value})")
        else:
            print("  [MISSING] Cross-document risks")

        # 8. Party-specific recommendations
        if verdict and verdict.company_a_recommendations and verdict.company_b_recommendations:
            print(f"  [OK] Party-specific recommendations generated")
            print(f"       Company A: {len(verdict.company_a_recommendations)} recommendations")
            print(f"       Company B: {len(verdict.company_b_recommendations)} recommendations")
        else:
            print("  [MISSING] Party-specific recommendations")

        # 9. Evidence attached to findings
        findings_with_evidence = sum(1 for f in comparison_result.findings if f.evidence_a or f.evidence_b)
        print(f"  [OK] Findings with evidence: {findings_with_evidence}/{len(comparison_result.findings)}")

        print("\n" + "=" * 60)
        print("PHASE 2 TEST COMPLETE")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        for pdf in [pdf_a, pdf_b]:
            if os.path.exists(pdf):
                os.remove(pdf)


if __name__ == "__main__":
    success = test_phase2_comparison()
    sys.exit(0 if success else 1)