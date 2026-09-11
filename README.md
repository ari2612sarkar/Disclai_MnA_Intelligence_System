# DISCLAI

## What it solves

The key problem:

M&A legal risk is distributed across documents and parties. Traditional review identifies clauses but does not necessarily reconcile equivalent legal positions across parties or connect them to transaction-level consequences.

## Core capability

Comparative legal intelligence.

DISCLAI compares Company A and Company B across equivalent legal provisions and documents, detects material asymmetries and inconsistencies, traces them to evidence, evaluates transaction impact, and produces party-specific recommendations and a deal verdict.

## Architecture

```
PDF
 ↓
Page-aware ingestion
 ↓
Document classification
 ↓
Provision identification
 ↓
Structured legal-position extraction
 ↓
Evidence verification
 ↓
Persistence
 ↓
Company A / Company B legal mapping
 ↓
Equivalent provision matching
 ↓
Comparative reasoning
 ↓
Asymmetry detection
 ↓
Cross-document dependency analysis
 ↓
Disclosure reconciliation
 ↓
Party-specific recommendations
 ↓
Deal verdict
 ↓
Professional report
```

```
disclai/
├── app/
│   ├── api/              # FastAPI endpoints + Web UI
│   ├── core/             # Configuration, logging
│   ├── classification/   # Document type classification
│   ├── comparison/       # Phase 2: A vs B comparison engine
│   ├── evidence/         # Evidence verification
│   ├── extraction/       # Legal position extraction
│   ├── ingestion/        # PDF parsing, chunking
│   ├── llm/              # LLM provider abstraction (HF + Mock)
│   ├── models/           # Pydantic + SQLAlchemy models
│   ├── report/           # HTML report generation
│   ├── retrieval/        # BM25 + embedding retrieval
│   └── services/         # Orchestration services
├── prompts/              # Modular LLM prompts
├── data/                 # Dataset directories
├── tests/
│   └── fixtures/         # Demo transaction PDFs
├── docs/                 # DEMO_SCRIPT.md, JUDGE_QA.md
└── scripts/              # Test, evaluation, demo scripts
```

## Features

- PDF ingestion with page/section/chunk preservation
- Legal document classification (SPA, Disclosure Schedule, etc.)
- Provision identification across 10+ M&A categories
- Structured legal-position extraction with evidence
- Evidence verification (VERIFIED / UNVERIFIED / REQUIRES_REVIEW)
- A/B legal comparison with semantic provision matching
- Numerical, duration, exception, condition, presence/absence asymmetry detection
- Cross-document dependency analysis (cap/basket ratio, survival vs indemnity)
- Disclosure reconciliation (SPA rep vs data room vs disclosure schedule)
- Party-specific recommendations (different guidance for each side)
- Transparent deal scoring and verdict
- Professional HTML report export
- Web UI: transaction dashboard, data room, comparison view, evidence explorer

## Tech Stack

- **Python 3.11+**
- **FastAPI** — API + server-side rendered UI (Jinja2)
- **SQLAlchemy + SQLite** — Persistence (PostgreSQL via DATABASE_URL)
- **PyMuPDF (fitz)** — PDF parsing
- **sentence-transformers** — Optional embedding retrieval (`pip install -e '.[embeddings]'`); BM25 remains available without it
- **rank-bm25** — Lexical retrieval
- **Hugging Face Inference API** — LLM (Mistral-7B-Instruct-v0.2 default)
- **Pydantic** — Structured I/O validation
- **Rich** — CLI output

## Setup

```bash
cd D:\Legal_Bot\disclai

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your HF_API_KEY (optional - uses mock provider if not set)
# HF_API_KEY=your_huggingface_token
# HF_MODEL_ID=mistralai/Mistral-7B-Instruct-v0.2
```

## Running

```bash
# Start API server + Web UI
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# Or run directly
python -m app.api.main
```

UI: http://localhost:8000  
API: http://localhost:8000/api/health

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HF_API_KEY` | Hugging Face API token (enables real model) | *empty → mock provider* |
| `HF_MODEL_ID` | Model repo ID | `mistralai/Mistral-7B-Instruct-v0.2` |
| `DATABASE_URL` | SQLite/PostgreSQL URL | `sqlite:///./disclai.db` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

**Never commit `.env` or real API keys.**

## Testing

```bash
# Phase 1 pipeline test
python scripts/test_pipeline.py

# Phase 2 comparison test
python scripts/test_phase2.py

# Gold evaluation suite (10 deterministic cases)
python scripts/evaluation.py

# End-to-end demo (creates companies, uploads SPAs, compares, exports report)
python scripts/demo_e2e.py
```

All tests should pass (10/10 evaluation, pipeline + phase2 + e2e green).

## Demo

### Quick Demo (synthetic SPAs)
```bash
python scripts/demo_e2e.py
```
Creates two synthetic SPAs with known asymmetries (cap 15% vs 20%, basket $500K vs $250K, survival 18 vs 24mo), runs full pipeline, exports `demo_report.html`.

### Full Demo Transaction (realistic M&A)
```bash
python scripts/run_demo_full.py
```
Uses `tests/fixtures/demo_transaction/`:
- **Company A (Seller)**: Northstar Technologies Pvt. Ltd.
- **Company B (Buyer)**: Vertex Systems Pvt. Ltd.
- 5 documents each: SPA, Disclosure Schedule, Material Contract, Litigation, Employment Agreement
- Deliberate asymmetries: cap 15%/20%, basket $500K/$250K, survival 18/24mo, MAE carve-outs, IP rep presence/absence
- **Disclosure reconciliation test**: Company B litigation document shows ₹8 Cr pending case; disclosure schedule says "NONE"

See `docs/DEMO_SCRIPT.md` for 90-second judge demo walkthrough.

## Deployment — Free Demo

### Recommended: Render

DISCLAI is a FastAPI web service, so deploy the repository as a Render **Web Service**.

1. Push the repository to GitHub.
2. In Render, create **New → Web Service** and connect the repository.
3. Use the included `render.yaml`, or configure:
   - Build command: `pip install -e .`
   - Start command: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - Health check: `/api/health`
4. Add `HF_API_KEY` as a secret and set `HF_MODEL_ID`.
5. Deploy.

For the free Render service, `ENABLE_EMBEDDINGS=false` is recommended. DISCLAI then uses BM25 retrieval and avoids downloading the optional embedding model.

**Important:** the free Render filesystem is ephemeral. Local SQLite data and uploaded PDFs can disappear after restarts/redeploys. This setup is intended for a hackathon/demo deployment, not production data retention. For persistent deployment, move the database to managed PostgreSQL and uploaded documents to object storage.

### Local frontend development

The TypeScript frontend is in `frontend/`.

```bash
cd frontend
npm install
npm run build
```

The Vite build is configured to emit the production assets directly into `app/static/assets/`.

### Optional semantic embeddings

For local environments where memory is available:

```bash
pip install -e ".[embeddings]"
```

Then keep:

```text
ENABLE_EMBEDDINGS=true
```

## Limitations

- Legal interpretation remains probabilistic — LLM output classified `REQUIRES_REVIEW` when evidence is insufficient
- Dataset coverage limited to 10 M&A categories
- Public benchmark performance (MAUD/CUAD/ContractNLI) not evaluated in this build
- OCR/scanned-document support depends on current ingestion capabilities (text-based PDFs only)
- Transaction-specific legal judgment requires qualified counsel
- Recommendations are decision support, not legal advice
- Mock LLM provider returns fixed extractions; real model needed for actual document variation
- Single-SPA comparison in current UI (multi-document data room comparison in backlog)

## Legal Disclaimer

**DISCLAI is legal decision support software, not a lawyer.** It identifies issues, traces them to evidence, and suggests negotiation positions. It does not provide legal advice, guarantee outcomes, or replace qualified counsel. All material findings require lawyer review before transaction decisions.

## Documentation

- `docs/DEMO_SCRIPT.md` — 90-second judge demo walkthrough
- `docs/JUDGE_QA.md` — 18 anticipated questions with concise answers