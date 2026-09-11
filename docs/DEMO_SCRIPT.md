# DISCLAI Demo Script

**Target Duration: 90–120 seconds**

---

## Opening (10 seconds)

> **"Traditional contract AI tells you what is in a document. DISCLAI asks what changes between the two sides — and what those changes mean for the deal."**

---

## Demo Flow

### 1. Create Transaction (15 seconds)
- Click **"New Transaction"**
- Enter: "Northstar-Vertex Acquisition"
- Company A: "Northstar Technologies Pvt. Ltd." (Seller)
- Company B: "Vertex Systems Pvt. Ltd." (Buyer)
- Deal Value: $50,000,000
- Click **Create**

### 2. Upload Company A Data Room (20 seconds)
- Navigate to **Data Room** → **Upload**
- Select Company A (Northstar)
- Upload 5 documents:
  - `SPA.pdf` — Share Purchase Agreement
  - `Disclosure_Schedule.pdf` — Disclosure Schedule
  - `Material_Contract.pdf` — Key Commercial Contract
  - `Litigation.pdf` — Litigation Status Report
  - `Employment_Agreement.pdf` — CEO Employment Agreement
- Click **"Run Analysis"** for each
- Show: "6 positions extracted" for SPA

### 3. Upload Company B Data Room (20 seconds)
- Select Company B (Vertex)
- Upload 5 corresponding documents:
  - `SPA.pdf` — Share Purchase Agreement (different terms)
  - `Disclosure_Schedule.pdf` — Disclosure Schedule (missing litigation)
  - `Material_Contract.pdf` — Key Commercial Contract
  - `Litigation.pdf` — Litigation Status Report (shows ₹8 Cr pending case)
  - `Employment_Agreement.pdf` — CEO Employment Agreement
- Click **"Run Analysis"** for each

### 4. Run Comparison (10 seconds)
- Navigate to **Comparisons** → **New Comparison**
- Select transaction: "Northstar-Vertex Acquisition"
- Select Company A run: SPA analysis
- Select Company B run: SPA analysis
- Click **"Run Comparison"**

### 5. Side-by-Side Comparison View (25 seconds)
**Show the central comparison table:**

| Provision | Company A (Northstar) | Company B (Vertex) | Difference | Materiality |
|-----------|----------------------|-------------------|------------|-------------|
| **Liability Cap** | 15% of Purchase Price | 20% of Purchase Price | 5% gap | POTENTIAL_ASYMMETRY |
| **Basket** | $500,000 | $250,000 | $250K gap | **MATERIAL_ASYMMETRY** |
| **Survival Period** | 18 months | 24 months | 6 months | **MATERIAL_ASYMMETRY** |
| **MAE Definition** | 4 carve-outs | 6 carve-outs (pandemic, regulatory) | 2 extra carve-outs | **MATERIAL_ASYMMETRY** |
| **Termination Rights** | 30-day cure only | 30-day cure + MAE continuing | Additional trigger | **MATERIAL_ASYMMETRY** |
| **Closing Conditions** | 3 conditions | 4 conditions (regulatory approvals) | Extra condition | **MATERIAL_ASYMMETRY** |
| **IP Representation** | ❌ Absent | ✅ Present | Presence/Absence | PRESENCE_ABSENCE |

**Click evidence links** to show exact page/section/text for each finding.

### 6. Disclosure Reconciliation (15 seconds)
- Navigate to **Disclosure Issues** tab
- **Finding**: "No pending litigation" representation in SPA
- **Evidence**: Litigation document (page 1) shows "Vertex Systems v. Datacorp — ₹8 Crore pending"
- **Disclosure Schedule**: "NONE — no pending litigation"
- **Impact**: HIGH — Potential representation/disclosure mismatch
- **Show**: Company A (Seller) recommendation: "Disclose pending litigation"
- **Show**: Company B (Buyer) recommendation: "Negotiate specific indemnity for Datacorp litigation"

### 7. Cross-Document Dependencies (10 seconds)
- Show **Risk Panel**:
  - **CAP_BASKET_RATIO** (LOW): Basket $500K = 6.7% of $7.5M cap
  - **SURVIVAL vs INDEMNITY** (MEDIUM): 18-month survival limits indemnity claim window
  - **SURVIVAL vs INDEMNITY** (MEDIUM): Same for basket

### 8. Party-Specific Recommendations (10 seconds)
**Company A (Seller) — 7 recommendations:**
- [HIGH] Align Termination Rights
- [HIGH] Align Closing Conditions  
- [HIGH] Add IP Representation
- [MEDIUM] Maintain/Increase Liability Cap to 20%
- [MEDIUM] Reduce Basket to $250K
- [MEDIUM] Qualify Representations with Knowledge
- [MEDIUM] Broaden MAE Carve-outs

**Company B (Buyer) — 7 recommendations:**
- [HIGH] Align Termination Rights
- [HIGH] Align Closing Conditions
- [MEDIUM] Reduce Basket for Earlier Recovery
- [MEDIUM] Resist Over-Qualification of Representations
- [MEDIUM] Narrow MAE Carve-outs
- [LOW] Maintain Current Cap Position
- [MEDIUM] Seek Absolute Representations for Fundamentals

### 9. Deal Verdict (10 seconds)
- **Overall Assessment**: CRITICAL RISK — Significant legal asymmetries threaten transaction viability
- **Risk Level**: CRITICAL
- **Score**: 17/100
- **Key Asymmetries**: 7 (5 MATERIAL)
- **Evidence-Backed Findings**: 7/7
- **Company A Advantages**: Higher cap (15% vs 20%), Higher basket ($500K vs $250K)
- **Company A Weaknesses**: Shorter survival (18 vs 24 months)
- **Company B Advantages**: Longer survival period
- **Company B Weaknesses**: Lower cap, Lower basket

### 10. Export Report (5 seconds)
- Click **"Export Report"**
- Download `demo_report_full.html`
- Show: Professional report with all findings, evidence, recommendations, methodology

---

## Key Messages to Emphasize

1. **COMPARE** — Not just extract. DISCLAI finds what's DIFFERENT between parties.
2. **UNDERSTAND** — Every finding traces to evidence (page, section, exact text).
3. **ACT** — Different recommendations for each party based on their position.

---

## If Asked: "What if evidence is missing?"
> "The system explicitly flags 'Insufficient evidence — lawyer review required' rather than hallucinating a conclusion."

## If Asked: "Is this legal advice?"
> "No. DISCLAI is legal decision support. It identifies issues and evidence; qualified counsel makes the legal judgment."

## If Asked: "How does it prevent hallucinations?"
> "Evidence verification step checks every extracted position against source text. Missing evidence = 'REQUIRES_REVIEW' status, not a fabricated answer."

---

## Fallback Plan (if live demo fails)
- Use pre-recorded screenshots/video
- Show exported `demo_report_full.html`
- Walk through the static report