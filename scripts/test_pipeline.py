#!/usr/bin/env python
"""
Test script for DISCLAI Phase 1 pipeline.
Tests the complete flow: upload -> parse -> classify -> identify -> extract -> verify
"""
import os
import sys
import tempfile
import fitz

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.analysis import AnalysisService
from app.models.session import init_db, drop_db
from app.models.schemas import DocumentType


def create_test_pdf() -> str:
    """Create a test SPA PDF for testing."""
    doc = fitz.open()
    page = doc.new_page()

    spa_text = """
SHARE PURCHASE AGREEMENT

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

Section 7.2 Entire Agreement. This Agreement constitutes the entire agreement
between the parties with respect to the subject matter hereof.

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


def test_pipeline():
    print("=" * 60)
    print("DISCLAI Phase 1 - Pipeline Test")
    print("=" * 60)

    # Initialize database
    print("\n1. Initializing database...")
    drop_db()
    init_db()
    print("   Database initialized.")

    # Create test PDF
    print("\n2. Creating test SPA document...")
    pdf_path = create_test_pdf()
    print(f"   Created: {pdf_path}")

    # Run analysis
    print("\n3. Running analysis pipeline...")
    service = AnalysisService()
    document_id = "test-doc-001"

    try:
        result = service.run_analysis(document_id, pdf_path, "test_spa.pdf")

        print(f"\n   Run ID: {result.run_id}")
        print(f"   Document ID: {result.document_id}")
        print(f"   Processing Time: {result.processing_time_ms}ms")
        print(f"   Classification: {result.classification.document_type.value} (confidence: {result.classification.confidence:.2f})")
        print(f"   Reason: {result.classification.reason}")
        print(f"   Positions Extracted: {len(result.positions)}")

        # Display positions
        print("\n4. Extracted Legal Positions:")
        print("-" * 60)
        for i, pos in enumerate(result.positions):
            print(f"\n   Position {i+1}:")
            print(f"     Category: {pos.category.value}")
            print(f"     Provision: {pos.provision_name}")
            print(f"     Party: {pos.party.value}")
            print(f"     Obligation/Right: {pos.obligation_right}")
            if pos.percentage:
                print(f"     Percentage: {pos.percentage} {pos.unit or ''}")
            if pos.amount:
                print(f"     Amount: {pos.amount}")
            if pos.duration:
                print(f"     Duration: {pos.duration}")
            if pos.qualifier:
                print(f"     Qualifiers: {', '.join(pos.qualifier)}")
            if pos.exception:
                print(f"     Exceptions: {', '.join(pos.exception)}")
            if pos.consequence:
                print(f"     Consequences: {', '.join(pos.consequence)}")
            print(f"     Evidence:")
            print(f"       Page: {pos.evidence.page_number}")
            print(f"       Section: {pos.evidence.section_number or 'N/A'}")
            print(f"       Heading: {pos.evidence.heading}")
            print(f"       Text: {pos.evidence.text[:200]}...")
            print(f"     Confidence: {pos.confidence:.2f}")
            print(f"     Status: {pos.status.value}")

        # Summary
        print("\n" + "=" * 60)
        print("PIPELINE TEST SUMMARY")
        print("=" * 60)
        verified = sum(1 for p in result.positions if p.status.value == "VERIFIED")
        print(f"Total Positions: {len(result.positions)}")
        print(f"Verified: {verified}")
        print(f"Unverified: {len(result.positions) - verified}")
        print(f"Classification: {result.classification.document_type.value}")
        print(f"Processing Time: {result.processing_time_ms}ms")

        # Verify expected findings
        expected = [
            ("Indemnification / Liability Caps", "General Liability Cap", "Seller", 15),
            ("Indemnification / Liability Caps", "Basket", "Seller", 500000),
            ("Representations & Warranties", "Survival Period", "Seller", 18),
            ("Material Adverse Effect", "Material Adverse Effect Definition", "N/A", None),
            ("Termination Rights", "Termination Rights", "Buyer/Seller", None),
            ("Closing Conditions", "Closing Conditions", "Buyer", None),
        ]

        print("\nExpected vs Found:")
        for cat, prov, party, val in expected:
            found = any(p.category.value == cat and prov.lower() in p.provision_name.lower()
                       for p in result.positions)
            status = "FOUND" if found else "MISSING"
            print(f"  [{status}] {cat} -> {prov} ({party})")

        return True

    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)