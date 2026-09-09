#!/usr/bin/env python
"""
Create realistic demo M&A transaction documents for DISCLAI.
"""
import fitz  # pymupdf
import os

def create_pdf(content, filepath):
    """Create a PDF with the given content."""
    doc = fitz.open()
    page = doc.new_page()
    
    # Split content into lines and write with proper positioning
    y = 50
    for line in content.split('\n'):
        if y > 750:
            page = doc.new_page()
            y = 50
        page.insert_text((50, y), line, fontsize=10)
        y += 14
    
    doc.save(filepath)
    doc.close()
    print(f"Created: {filepath}")

# ============================================================
# COMPANY A: Northstar Technologies Pvt. Ltd. (Seller)
# ============================================================

# Company A - SPA.pdf
spa_a = """SHARE PURCHASE AGREEMENT

This Share Purchase Agreement (the "Agreement") is entered into as of January 15, 2024,
by and between Northstar Technologies Pvt. Ltd. ("Seller") and Vertex Systems Pvt. Ltd. ("Buyer").

PURCHASE PRICE: $50,000,000 (Fifty Million US Dollars)

ARTICLE 1: REPRESENTATIONS AND WARRANTIES

Section 1.1: Organization and Authority
Seller represents and warrants that it is a private limited company duly organized, validly existing,
and in good standing under the laws of India. Seller has full corporate power and authority to
execute, deliver, and perform this Agreement.

Section 1.2: Intellectual Property
Seller represents that it owns all right, title, and interest in and to the Intellectual Property
used in the Business, free and clear of all liens, except as set forth in Schedule 1.2.

Section 1.3: No Pending Litigation
Seller represents and warrants that there is no pending or threatened litigation, arbitration,
or governmental proceeding against Seller or any of its subsidiaries that would have a Material
Adverse Effect on the Business.

Section 1.4: Financial Statements
The financial statements of Seller provided to Buyer are true, complete, and correct in all
material respects and have been prepared in accordance with Indian GAAP consistently applied.

ARTICLE 2: INDEMNIFICATION

Section 2.1: General Liability Cap
The aggregate liability of Seller under this Agreement shall not exceed 15% of the Purchase Price
(the "Cap"). The foregoing Cap shall not apply to liability arising from fraud or willful misconduct.

Section 2.2: Basket
Seller shall have no obligation to indemnify Buyer for any Losses unless and until the aggregate
amount of such Losses exceeds $500,000 (the "Basket"). Once the Basket is exceeded, Seller shall
be liable for all Losses from the first dollar.

Section 2.3: Survival Period
The representations and warranties of Seller contained in this Agreement shall survive the Closing
for a period of 18 months (the "Survival Period"). Following the expiration of the Survival Period,
no claim may be brought for any breach of representations or warranties.

ARTICLE 3: MATERIAL ADVERSE EFFECT

Section 3.1: Definition
"Material Adverse Effect" means any change, event, or effect that, individually or in the aggregate,
has or would reasonably be expected to have a material adverse effect on the business, assets, or
financial condition of Seller, except for changes resulting from: (a) general economic conditions;
(b) industry-wide changes; (c) acts of war or terrorism; (d) natural disasters.

ARTICLE 4: TERMINATION

Section 4.1: Termination Rights
This Agreement may be terminated at any time prior to the Closing:
(a) by mutual written consent of Seller and Buyer;
(b) by Buyer if any representation or warranty of Seller is untrue in any material respect and
such breach is not cured within 30 days of written notice;
(c) by Seller if Buyer fails to obtain required financing.

ARTICLE 5: CLOSING CONDITIONS

Section 5.1: Conditions to Buyer's Obligation
The obligation of Buyer to consummate the Closing is subject to the satisfaction of the following
conditions:
(a) The representations and warranties of Seller shall be true and correct in all material respects;
(b) No Material Adverse Effect shall have occurred;
(c) Seller shall have performed all obligations required under this Agreement.

Section 5.2: Conditions to Seller's Obligation
The obligation of Seller to consummate the Closing is subject to the satisfaction of the following
conditions:
(a) The representations and warranties of Buyer shall be true and correct in all material respects;
(b) Buyer shall have obtained all necessary financing;
(c) All regulatory approvals shall have been obtained.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

NORTHSTAR TECHNOLOGIES PVT. LTD.          VERTEX SYSTEMS PVT. LTD.
By: _______________________________       By: _______________________________
Name: Rajesh Kumar                        Name: Amit Shah
Title: CEO                                Title: CEO
"""

# Company A - Disclosure_Schedule.pdf
disclosure_a = """DISCLOSURE SCHEDULE
Northstar Technologies Pvt. Ltd.

This Disclosure Schedule is delivered pursuant to the Share Purchase Agreement dated January 15, 2024.

SECTION 1.2: INTELLECTUAL PROPERTY
The following Intellectual Property is owned by Seller:
- Trademark: "Northstar" (Reg. No. 1234567)
- Patent: "Distributed Processing Method" (Patent No. IN987654)
- Copyright: Source code for Northstar Platform v3.2

SECTION 1.3: LITIGATION
NONE. There is no pending or threatened litigation against Seller or its subsidiaries.

SECTION 1.4: FINANCIAL STATEMENTS
Audited financial statements for FY2022, FY2023 are attached as Exhibit A.
Unaudited interim financial statements for Q1-Q3 FY2024 are attached as Exhibit B.

SECTION 2.1: INDEMNIFICATION EXCEPTIONS
The liability cap exceptions are limited to fraud and willful misconduct as stated in the Agreement.

END OF DISCLOSURE SCHEDULE
"""

# Company A - Material_Contract.pdf
material_contract_a = """MASTER SERVICES AGREEMENT

Between: Northstar Technologies Pvt. Ltd. ("Provider")
And: Global Enterprises Inc. ("Customer")

Date: March 1, 2023
Term: 3 years, auto-renewing for successive 1-year periods

Section 1: Services
Provider shall provide cloud infrastructure and managed services as described in Schedule A.

Section 2: Fees
Customer shall pay Provider $200,000 per quarter, payable within 30 days of invoice.

Section 3: Termination
Either party may terminate for material breach uncured after 30 days written notice.

Section 4: Liability
Provider's aggregate liability shall not exceed the total fees paid in the 12 months preceding
the claim. This limitation does not apply to Provider's confidentiality obligations.

Section 5: Intellectual Property
Provider retains all right, title, and interest in its proprietary technology and methodology.
Customer receives a non-exclusive license to use the Services during the Term.

Section 6: Confidentiality
Both parties shall maintain confidentiality of all non-public information for 3 years post-termination.

NORTHSTAR TECHNOLOGIES PVT. LTD.          GLOBAL ENTERPRISES INC.
By: _______________________________       By: _______________________________
"""

# Company A - Litigation.pdf
litigation_a = """LITIGATION STATUS REPORT
Northstar Technologies Pvt. Ltd.
As of January 10, 2024

PENDING LITIGATION: NONE

There are no pending lawsuits, arbitration proceedings, or regulatory actions against
Northstar Technologies Pvt. Ltd. or its subsidiaries as of the date of this report.

THREATENED LITIGATION: NONE

No demand letters, notices of claim, or other indications of potential litigation have
been received.

HISTORICAL LITIGATION (CLOSED):
- 2021: Patent infringement claim by TechRival Inc. - SETTLED with prejudice, no liability.
- 2022: Employment dispute with former employee - DISMISSED with prejudice.

This report is certified accurate by the General Counsel of Northstar Technologies Pvt. Ltd.

_______________________________
Priya Sharma, General Counsel
Date: January 10, 2024
"""

# Company A - Employment_Agreement.pdf
employment_a = """EMPLOYMENT AGREEMENT

Between: Northstar Technologies Pvt. Ltd. ("Company")
And: Rajesh Kumar ("Executive")

Position: Chief Executive Officer
Effective Date: January 1, 2022
Term: 3 years, renewable by mutual agreement

Section 1: Compensation
Base Salary: $400,000 per annum
Annual Bonus: Up to 100% of Base Salary based on performance metrics
Equity: 2% of fully diluted shares, vesting over 4 years with 1-year cliff

Section 2: Termination
(a) For Cause: Company may terminate immediately for cause (fraud, gross negligence, conviction).
(b) Without Cause: Company may terminate with 90 days notice or payment in lieu.
(c) By Executive: Executive may resign with 60 days notice.
(d) Change of Control: Double-trigger acceleration of equity vesting.

Section 3: Non-Compete
Executive agrees not to compete with Company for 12 months post-termination within India.

Section 4: Confidentiality
Executive shall maintain confidentiality of all trade secrets and proprietary information
indefinitely, and other confidential information for 5 years post-termination.

NORTHSTAR TECHNOLOGIES PVT. LTD.          RAJESH KUMAR
By: _______________________________       _______________________________
"""

# ============================================================
# COMPANY B: Vertex Systems Pvt. Ltd. (Buyer)
# ============================================================

# Company B - SPA.pdf (with deliberate asymmetries)
spa_b = """SHARE PURCHASE AGREEMENT

This Share Purchase Agreement (the "Agreement") is entered into as of January 15, 2024,
by and between Northstar Technologies Pvt. Ltd. ("Seller") and Vertex Systems Pvt. Ltd. ("Buyer").

PURCHASE PRICE: $50,000,000 (Fifty Million US Dollars)

ARTICLE 1: REPRESENTATIONS AND WARRANTIES

Section 1.1: Organization and Authority
Buyer represents and warrants that it is a private limited company duly organized, validly existing,
and in good standing under the laws of India. Buyer has full corporate power and authority to
execute, deliver, and perform this Agreement.

Section 1.2: Intellectual Property
Buyer represents and warrants that it owns all right, title, and interest in and to the Intellectual
Property used in the Business, free and clear of all liens. Buyer has not received any claims
alleging infringement of third-party intellectual property rights. All software developed by Buyer
is original work product and does not incorporate any open source code with restrictive licenses.

Section 1.3: No Pending Litigation
Buyer represents and warrants that there is no pending or threatened litigation, arbitration,
or governmental proceeding against Buyer or any of its subsidiaries that would have a Material
Adverse Effect on the Business.

Section 1.4: Financial Statements
The financial statements of Buyer provided to Seller are true, complete, and correct in all
material respects and have been prepared in accordance with Indian GAAP consistently applied.

ARTICLE 2: INDEMNIFICATION

Section 2.1: General Liability Cap
The aggregate liability of Buyer under this Agreement shall not exceed 20% of the Purchase Price
(the "Cap"). The foregoing Cap shall not apply to liability arising from fraud, willful misconduct,
or breach of fundamental representations.

Section 2.2: Basket
Buyer shall have no obligation to indemnify Seller for any Losses unless and until the aggregate
amount of such Losses exceeds $250,000 (the "Basket"). Once the Basket is exceeded, Buyer shall
be liable for all Losses from the first dollar (deductible structure).

Section 2.3: Survival Period
The representations and warranties of Buyer contained in this Agreement shall survive the Closing
for a period of 24 months (the "Survival Period"). Following the expiration of the Survival Period,
no claim may be brought for any breach of representations or warranties.

ARTICLE 3: MATERIAL ADVERSE EFFECT

Section 3.1: Definition
"Material Adverse Effect" means any change, event, or effect that, individually or in the aggregate,
has or would reasonably be expected to have a material adverse effect on the business, assets, or
financial condition of Buyer, except for changes resulting from: (a) general economic conditions;
(b) industry-wide changes; (c) acts of war or terrorism; (d) natural disasters; (e) pandemics;
(f) regulatory changes.

ARTICLE 4: TERMINATION

Section 4.1: Termination Rights
This Agreement may be terminated at any time prior to the Closing:
(a) by mutual written consent of Seller and Buyer;
(b) by Buyer if any representation or warranty of Seller is untrue in any material respect and
such breach is not cured within 30 days of written notice;
(c) by Seller if Buyer fails to obtain required financing;
(d) by either party if a Material Adverse Effect has occurred and is continuing.

ARTICLE 5: CLOSING CONDITIONS

Section 5.1: Conditions to Buyer's Obligation
The obligation of Buyer to consummate the Closing is subject to the satisfaction of the following
conditions:
(a) The representations and warranties of Seller shall be true and correct in all material respects;
(b) No Material Adverse Effect shall have occurred;
(c) Seller shall have performed all obligations required under this Agreement;
(d) All regulatory approvals shall have been received.

Section 5.2: Conditions to Seller's Obligation
The obligation of Seller to consummate the Closing is subject to the satisfaction of the following
conditions:
(a) The representations and warranties of Buyer shall be true and correct in all material respects;
(b) Buyer shall have obtained all necessary financing;
(c) All regulatory approvals shall have been obtained.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

NORTHSTAR TECHNOLOGIES PVT. LTD.          VERTEX SYSTEMS PVT. LTD.
By: _______________________________       By: _______________________________
Name: Rajesh Kumar                        Name: Amit Shah
Title: CEO                                Title: CEO
"""

# Company B - Disclosure_Schedule.pdf (missing the litigation disclosure)
disclosure_b = """DISCLOSURE SCHEDULE
Vertex Systems Pvt. Ltd.

This Disclosure Schedule is delivered pursuant to the Share Purchase Agreement dated January 15, 2024.

SECTION 1.2: INTELLECTUAL PROPERTY
The following Intellectual Property is owned by Buyer:
- Trademark: "Vertex" (Reg. No. 7654321)
- Patent: "Real-time Analytics Engine" (Patent No. IN567890)
- Copyright: Source code for Vertex Platform v2.1
- Trade Secret: Proprietary ML algorithm for anomaly detection

SECTION 1.3: LITIGATION
NONE. There is no pending or threatened litigation against Buyer or its subsidiaries.

SECTION 1.4: FINANCIAL STATEMENTS
Audited financial statements for FY2022, FY2023 are attached as Exhibit A.
Unaudited interim financial statements for Q1-Q3 FY2024 are attached as Exhibit B.

SECTION 2.1: INDEMNIFICATION EXCEPTIONS
The liability cap exceptions include fraud, willful misconduct, and breach of fundamental
representations as stated in the Agreement.

END OF DISCLOSURE SCHEDULE
"""

# Company B - Material_Contract.pdf
material_contract_b = """MASTER SERVICES AGREEMENT

Between: Vertex Systems Pvt. Ltd. ("Provider")
And: MegaCorp International ("Customer")

Date: June 1, 2023
Term: 2 years, auto-renewing for successive 1-year periods

Section 1: Services
Provider shall provide AI-powered analytics platform and consulting services per Schedule A.

Section 2: Fees
Customer shall pay Provider $500,000 per quarter, payable within 45 days of invoice.

Section 3: Termination
Either party may terminate for material breach uncured after 15 days written notice.

Section 4: Liability
Provider's aggregate liability shall not exceed 2x the total fees paid in the 12 months preceding
the claim. This limitation does not apply to Provider's confidentiality or IP infringement obligations.

Section 5: Intellectual Property
Provider retains all right, title, and interest in its proprietary technology, algorithms, and models.
Customer receives a non-exclusive, non-transferable license to use the Platform during the Term.

Section 6: Confidentiality
Both parties shall maintain confidentiality of all non-public information for 5 years post-termination.

Section 7: Data Protection
Provider shall comply with all applicable data protection laws including GDPR and India's DPDP Act.

VERTEX SYSTEMS PVT. LTD.          MEGACORP INTERNATIONAL
By: _______________________________       By: _______________________________
"""

# Company B - Litigation.pdf (THE DISCLOSURE RECONCILIATION TEST CASE)
# This document contains litigation that is NOT disclosed in the Disclosure Schedule
litigation_b = """LITIGATION STATUS REPORT
Vertex Systems Pvt. Ltd.
As of January 10, 2024

PENDING LITIGATION:

1. VERTEX SYSTEMS PVT. LTD. v. DATACORP INC.
   Court: Delhi High Court
   Case No: CS(COMM) 1234/2023
   Filed: November 15, 2023
   Status: Active - Discovery Phase
   Claim Amount: ₹8 Crore (approx. $960,000 USD)
   Description: Vertex alleges Datacorp misappropriated trade secrets related to Vertex's
   proprietary anomaly detection algorithm. Datacorp has filed counterclaims for declaratory
   judgment of non-infringement and antitrust violations.
   Next Hearing: March 15, 2024
   Legal Counsel: Singh & Associates

2. EMPLOYEE CLASS ACTION - Sharma et al. v. Vertex Systems Pvt. Ltd.
   Court: National Company Law Tribunal, Delhi
   Case No: CP/456/2023
   Filed: October 1, 2023
   Status: Active - Class Certification Pending
   Claim Amount: Undetermined (estimated ₹2-5 Crore)
   Description: Former employees allege misclassification as contractors, seeking overtime,
   benefits, and statutory penalties under the Code on Wages, 2019.
   Legal Counsel: Khaitan & Co.

THREATENED LITIGATION:
- Patent infringement notice received from InnovateTech Ltd. (December 2023) regarding
  Patent No. IN112233. Vertex's counsel has responded denying infringement.

HISTORICAL LITIGATION (CLOSED):
- 2021: Vendor dispute with CloudServe Ltd. - ARBITRATED, settled for ₹50 Lakhs.
- 2022: IP licensing dispute with DataFlow Inc. - DISMISSED with prejudice.

This report is certified accurate by the General Counsel of Vertex Systems Pvt. Ltd.

_______________________________
Vikram Singh, General Counsel
Date: January 10, 2024
"""

# Company B - Employment_Agreement.pdf
employment_b = """EMPLOYMENT AGREEMENT

Between: Vertex Systems Pvt. Ltd. ("Company")
And: Amit Shah ("Executive")

Position: Chief Executive Officer
Effective Date: July 1, 2022
Term: 4 years, renewable by mutual agreement

Section 1: Compensation
Base Salary: $500,000 per annum
Annual Bonus: Up to 150% of Base Salary based on performance metrics
Equity: 3% of fully diluted shares, vesting over 4 years with 1-year cliff

Section 2: Termination
(a) For Cause: Company may terminate immediately for cause (fraud, gross negligence, conviction).
(b) Without Cause: Company may terminate with 60 days notice or payment in lieu.
(c) By Executive: Executive may resign with 90 days notice.
(d) Change of Control: Single-trigger acceleration of 50% of unvested equity; double-trigger for remaining.

Section 3: Non-Compete
Executive agrees not to compete with Company for 18 months post-termination globally.

Section 4: Confidentiality
Executive shall maintain confidentiality of all trade secrets and proprietary information
indefinitely, and other confidential information for 7 years post-termination.

VERTEX SYSTEMS PVT. LTD.          AMIT SHAH
By: _______________________________       _______________________________
"""

# Create all documents
output_dir_a = r"D:\Legal_Bot\disclai\tests\fixtures\demo_transaction\company_a"
output_dir_b = r"D:\Legal_Bot\disclai\tests\fixtures\demo_transaction\company_b"

create_pdf(spa_a, os.path.join(output_dir_a, "SPA.pdf"))
create_pdf(disclosure_a, os.path.join(output_dir_a, "Disclosure_Schedule.pdf"))
create_pdf(material_contract_a, os.path.join(output_dir_a, "Material_Contract.pdf"))
create_pdf(litigation_a, os.path.join(output_dir_a, "Litigation.pdf"))
create_pdf(employment_a, os.path.join(output_dir_a, "Employment_Agreement.pdf"))

create_pdf(spa_b, os.path.join(output_dir_b, "SPA.pdf"))
create_pdf(disclosure_b, os.path.join(output_dir_b, "Disclosure_Schedule.pdf"))
create_pdf(material_contract_b, os.path.join(output_dir_b, "Material_Contract.pdf"))
create_pdf(litigation_b, os.path.join(output_dir_b, "Litigation.pdf"))
create_pdf(employment_b, os.path.join(output_dir_b, "Employment_Agreement.pdf"))

print("\n=== All demo documents created successfully ===")
print(f"Company A: {output_dir_a}")
print(f"Company B: {output_dir_b}")