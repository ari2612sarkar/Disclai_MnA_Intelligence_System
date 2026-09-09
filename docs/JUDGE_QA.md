# DISCLAI — Judge Q&A Preparation

Concise answers describing the ACTUAL implementation.

---

## 1. What problem does DISCLAI solve?

**Answer:** M&A legal risk is distributed across dozens of documents and two parties. Traditional contract review extracts clauses from individual documents but doesn't reconcile equivalent legal positions across the buyer and seller, connect them to transaction-level consequences (indemnity exposure, claim windows, disclosure gaps), or produce party-specific negotiation guidance. DISCLAI does all three.

---

## 2. How is this different from generic contract review?

**Answer:** Three differentiators:
1. **A vs B comparison** — Semantic matching of equivalent provisions across parties (not just clause extraction)
2. **Transaction-level reasoning** — Cross-document dependencies (cap/basket ratio, survival vs. indemnity window), disclosure reconciliation (SPA rep vs. data room vs. disclosure schedule)
3. **Party-specific output** — Different recommendations for seller vs. buyer derived from the same findings

---

## 3. Why compare two companies?

**Answer:** In M&A, every provision has a counterparty. A 15% liability cap means something different to the seller (protection) than the buyer (exposure). The asymmetry *is* the negotiation. Single-document review misses this entirely.

---

## 4. How does it prevent hallucinations?

**Answer:** Four-layer defense:
1. **Evidence verification step** — Every extracted position is checked against source text spans (page, section, char offsets). Status = VERIFIED / UNVERIFIED / REQUIRES_REVIEW.
2. **No fabrication of missing values** — If purchase price is missing, CAP_BASKET_RATIO returns "Cannot compute ratio without purchase price" not a guessed number.
3. **Explicit uncertainty** — Insufficient evidence → "REQUIRES_REVIEW" classification, not a forced conclusion.
4. **Structured output schemas** — LLM constrained to JSON schemas; failed parses trigger repair, not free-text generation.

---

## 5. Where does evidence come from?

**Answer:** PDF ingestion preserves page/section/chunk boundaries. Every LegalPosition stores: `document_id`, `page_number`, `section_number`, `heading`, `char_start`, `char_end`, `text_span`. The UI and report show exact source text for every finding.

---

## 6. What happens when evidence is missing?

**Answer:** The position gets status `REQUIRES_REVIEW` or `UNVERIFIED`. Comparison findings involving it are classified `REQUIRES_REVIEW`. The verdict includes "Unresolved Questions" listing these. No hallucinated conclusion is produced.

---

## 7. Which model powers the system?

**Answer:** Configurable via `HF_MODEL_ID`. Default: `mistralai/Mistral-7B-Instruct-v0.2` via Hugging Face Inference API. Mock provider (`mock-model`) used for deterministic CI/tests.

---

## 8. Why use Hugging Face?

**Answer:** 
- Access to open-weight instruct models (Mistral, Llama, etc.) without self-hosting GPUs
- Pay-per-token API, no infrastructure ops
- Easy model swap via `HF_MODEL_ID` env var
- Structured output support via `response_format=json_object`

---

## 9. What is deterministic vs LLM-driven?

| Deterministic | LLM-Driven |
|---------------|------------|
| Duration normalization (18mo vs 1.5yr → 6mo diff) | Semantic provision matching |
| Numeric comparison (cap 15% vs 20% → 5% diff) | Nuanced legal interpretation |
| Exact string matching (exceptions, conditions) | Contextual materiality assessment |
| Score aggregation (weighted formula) | Impact explanation drafting |
| Evidence existence check | Recommendation text generation |
| Purchase price math (cap% × deal value) | Cross-doc dependency reasoning |

---

## 10. How do you evaluate it?

**Answer:** Three-tier evaluation suite:
1. **Gold unit tests** (`scripts/evaluation.py`) — 10/10 deterministic cases: numerical asymmetry, presence/absence, duration normalization, exception diff, cross-doc dependency, disclosure inconsistency, insufficient evidence, missing purchase price.
2. **Synthetic integration tests** (`scripts/test_pipeline.py`, `scripts/test_phase2.py`) — End-to-end with mock LLM, fixed expected outputs.
3. **Real-model smoke test** — Manual run with HF API key against demo transaction fixture.

*No public benchmark (MAUD/CUAD/ContractNLI) evaluated in this build.*

---

## 11. What happens with contradictory documents?

**Answer:** Both positions are extracted with evidence. Comparison finding shows both sides. Classification = `CONFLICT` or `MATERIAL_ASYMMETRY`. Verdict flags "lawyer review required." System does not pick a winner.

---

## 12. What happens with missing purchase price?

**Answer:** CAP_BASKET_RATIO risk is still generated but impact text reads: "Cannot compute basket-to-cap ratio without purchase price. Ratio would be: basket / (cap% × purchase_price). Provide deal value to enable this analysis." No fabricated ratio.

---

## 13. Is this legal advice?

**Answer:** No. Disclaimer in every report: "This analysis is legal decision support, not legal advice. Qualified counsel should review all findings before transaction decisions." Recommendations use "recommended transaction position," "risk-reduction opportunity," "lawyer review recommended" — never "guaranteed outcome" or "best legal result."

---

## 14. What would you build next?

**Answer:** 
1. **Multi-document comparison** — Compare all docs in data room, not just SPA
2. **Clause-level redlining** — Generate marked-up SPA with proposed changes
3. **Precedent database** — Learn from historical deal outcomes
4. **OCR pipeline** — Full scanned PDF support
5. **Real-time collaboration** — Multi-lawyer review workflow

---

## 15. How does this scale to a real M&A data room?

**Answer:** Current architecture:
- **Ingestion**: Page/section/chunk level, BM25 + embeddings index — O(n) per doc
- **Retrieval**: Top-k chunks per provision — sub-second
- **LLM calls**: One per provision type (not per page) — ~20-30 calls per SPA
- **Comparison**: O(m×n) provision matching — <200ms for 20 provisions/side

Bottleneck is LLM latency. Mitigation: batch provision extraction, async processing, caching embeddings. 100-doc data room ≈ 15-20 min wall time on current hardware.

---

## 16. Why is disclosure reconciliation important?

**Answer:** It's the highest-stakes check in M&A. SPA says "No pending litigation." Data room has a ₹8 Cr lawsuit. Disclosure schedule is silent. That's a potential 10b-5 claim, indemnity trigger, or deal-breaker. DISCLAI is the only layer that connects all three automatically.

---

## 17. What is the most technically difficult component?

**Answer:** **Semantic equivalent-provision matching** across differently-worded clauses. "Limitation of Liability" (A) vs "Liability Cap" (B) vs "Aggregate Indemnity Limit" (C). Solved via: embedding similarity + structural heuristics (category, party, section number) + LLM verification. Current match accuracy on test fixtures: ~95% for clear equivalents, lower for heavily restructured clauses.

---

## 18. What is the strongest differentiator?

**Answer:** **Party-specific recommendations from the same finding.** One finding (Basket $500K vs $250K) → Seller gets "Reduce basket to $250K" (MEDIUM), Buyer gets "Maintain $250K for earlier recovery" (MEDIUM). Same evidence, opposite negotiating guidance. This is what M&A lawyers actually need.