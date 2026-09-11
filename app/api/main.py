from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
import shutil
import logging
from datetime import datetime
from app.services.analysis import AnalysisService
from app.comparison.service import ComparisonService
from app.models.schemas import (
    UploadResponse, RunResponse, AnalysisResult, Document, LegalPosition, FindingsResponse,
    Company, Transaction, CompanyRole, ComparisonRun, ComparisonResult
)
from app.models.session import init_db
from app.core.logging import setup_logging
from app.models.database import CompanyDB, TransactionDB, CompanyRoleEnum, DocumentDB, AnalysisRunDB, DocumentOwnershipDB, LegalPositionDB, ComparisonRunDB
from app.models.session import get_db
from app.api.demo_seed import router as demo_seed_router

setup_logging()
logger = logging.getLogger(__name__)
init_db()

app = FastAPI(
    title="DISCLAI API",
    description="AI-Powered Comparative M&A Legal Intelligence",
    version="0.3.0",
)

# Templates and static files
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(demo_seed_router)

analysis_service = AnalysisService()
comparison_service = ComparisonService()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class RunRequest(BaseModel):
    document_id: str


class CompanyCreate(BaseModel):
    name: str
    role: CompanyRole = CompanyRole.UNKNOWN
    description: Optional[str] = None


class TransactionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    company_a_id: str
    company_b_id: str
    company_a_role: CompanyRole
    company_b_role: CompanyRole
    deal_value: Optional[float] = None
    currency: str = "USD"


class ComparisonRequest(BaseModel):
    transaction_id: str
    company_a_run_id: str
    company_b_run_id: str


# ========== UI ROUTES ==========

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, transaction_id: Optional[str] = None):
    import traceback
    import sys
    print(f"DEBUG: Dashboard route called, transaction_id={transaction_id}", file=sys.stderr, flush=True)
    try:
        with get_db() as db:
            if transaction_id:
                txn_db = db.query(TransactionDB).filter(TransactionDB.id == transaction_id).first()
                if not txn_db:
                    return RedirectResponse(url="/dashboard")
            else:
                txn_db = db.query(TransactionDB).order_by(TransactionDB.created_at.desc()).first()
            
            print(f"DEBUG: txn_db={txn_db.id if txn_db else None}", file=sys.stderr, flush=True)
            
            if not txn_db:
                print("DEBUG: No transaction, returning empty dashboard", file=sys.stderr, flush=True)
                return templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "transaction": None,
                    "verdict": None,
                    "company_a": None,
                    "company_b": None,
                    "company_a_doc_count": 0,
                    "company_b_doc_count": 0,
                    "company_a_positions": 0,
                    "company_b_positions": 0,
                    "comparison_id": None,
                    "top_findings": [],
                    "company_a_recs": [],
                    "company_b_recs": [],
                })
            
            company_a_db = db.query(CompanyDB).filter(CompanyDB.id == txn_db.company_a_id).first()
            company_b_db = db.query(CompanyDB).filter(CompanyDB.id == txn_db.company_b_id).first()
            
            print(f"DEBUG: company_a_db={company_a_db.name if company_a_db else None}, company_b_db={company_b_db.name if company_b_db else None}", file=sys.stderr, flush=True)
            
            # Get documents for each company
            company_a_docs = db.query(DocumentDB).join(DocumentOwnershipDB).filter(
                DocumentOwnershipDB.company_id == company_a_db.id
            ).all() if company_a_db else []
            company_b_docs = db.query(DocumentDB).join(DocumentOwnershipDB).filter(
                DocumentOwnershipDB.company_id == company_b_db.id
            ).all() if company_b_db else []
            
            print(f"DEBUG: company_a_docs={len(company_a_docs)}, company_b_docs={len(company_b_docs)}", file=sys.stderr, flush=True)
            
            # Get latest analysis runs
            run_a = db.query(AnalysisRunDB).join(LegalPositionDB).filter(
                LegalPositionDB.document_id == company_a_docs[0].id
            ).order_by(AnalysisRunDB.started_at.desc()).first() if company_a_docs else None
            
            run_b = db.query(AnalysisRunDB).join(LegalPositionDB).filter(
                LegalPositionDB.document_id == company_b_docs[0].id
            ).order_by(AnalysisRunDB.started_at.desc()).first() if company_b_docs else None
            
            print(f"DEBUG: run_a={run_a.id if run_a else None}, run_b={run_b.id if run_b else None}", file=sys.stderr, flush=True)
            
            # Get comparison
            comparison_db = db.query(ComparisonRunDB).filter(
                ComparisonRunDB.transaction_id == txn_db.id
            ).order_by(ComparisonRunDB.started_at.desc()).first()
            
            print(f"DEBUG: comparison_db={comparison_db.id if comparison_db else None}", file=sys.stderr, flush=True)
            
            verdict = None
            top_findings = []
            company_a_recs = []
            company_b_recs = []
            comparison_id = None
            
            if comparison_db:
                comparison_id = comparison_db.id
                comparison_result = comparison_service.get_comparison(comparison_db.id)
                if comparison_result:
                    verdict = comparison_result.verdict
                    top_findings = sorted(
                        comparison_result.findings,
                        key=lambda f: (
                            0 if f.classification.value == "MATERIAL_ASYMMETRY" else
                            1 if f.classification.value == "POTENTIAL_ASYMMETRY" else
                            2 if f.classification.value == "PRESENCE_ABSENCE" else
                            3 if f.classification.value == "CONFLICT" else 4
                        )
                    )[:10]
                    company_a_recs = verdict.company_a_recommendations if verdict else []
                    company_b_recs = verdict.company_b_recommendations if verdict else []
            
            print(f"DEBUG: verdict={verdict is not None}, top_findings={len(top_findings)}", file=sys.stderr, flush=True)
            
            company_a = Company(
                id=company_a_db.id,
                name=company_a_db.name,
                role=CompanyRole(company_a_db.role.value),
                description=company_a_db.description,
                company_metadata=company_a_db.company_metadata or {},
                created_at=company_a_db.created_at,
                updated_at=company_a_db.updated_at,
            ) if company_a_db else None
            
            company_b = Company(
                id=company_b_db.id,
                name=company_b_db.name,
                role=CompanyRole(company_b_db.role.value),
                description=company_b_db.description,
                company_metadata=company_b_db.company_metadata or {},
                created_at=company_b_db.created_at,
                updated_at=company_b_db.updated_at,
            ) if company_b_db else None
            
            transaction = Transaction(
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
            
            print("DEBUG: About to render template", file=sys.stderr, flush=True)
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "transaction": transaction,
                "verdict": verdict,
                "company_a": company_a,
                "company_b": company_b,
                "company_a_doc_count": len(company_a_docs),
                "company_b_doc_count": len(company_b_docs),
                "company_a_positions": run_a.provisions_extracted if run_a else 0,
                "company_b_positions": run_b.provisions_extracted if run_b else 0,
                "comparison_id": comparison_id,
                "top_findings": top_findings,
                "company_a_recs": company_a_recs,
                "company_b_recs": company_b_recs,
            })
    except Exception as e:
        print(f"Dashboard error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        raise


@app.get("/transactions", response_class=HTMLResponse)
async def transactions_list(request: Request):
    with get_db() as db:
        txns = db.query(TransactionDB).order_by(TransactionDB.created_at.desc()).all()
        transactions = []
        for txn in txns:
            company_a = db.query(CompanyDB).filter(CompanyDB.id == txn.company_a_id).first()
            company_b = db.query(CompanyDB).filter(CompanyDB.id == txn.company_b_id).first()
            transactions.append({
                "id": txn.id,
                "name": txn.name,
                "company_a_name": company_a.name if company_a else "Unknown",
                "company_a_role": txn.company_a_role.value,
                "company_b_name": company_b.name if company_b else "Unknown",
                "company_b_role": txn.company_b_role.value,
                "deal_value": txn.deal_value,
                "currency": txn.currency,
                "status": txn.status,
                "created_at": txn.created_at,
            })
        return templates.TemplateResponse("transactions.html", {
            "request": request,
            "transactions": transactions,
        })


@app.get("/transactions/new", response_class=HTMLResponse)
async def new_transaction_page(request: Request):
    return templates.TemplateResponse("new_transaction.html", {"request": request})


@app.post("/transactions/create", response_class=HTMLResponse)
async def create_transaction_ui(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    deal_value: Optional[float] = Form(None),
    company_a_name: str = Form(...),
    company_a_role: str = Form(...),
    company_a_description: str = Form(""),
    company_b_name: str = Form(...),
    company_b_role: str = Form(...),
    company_b_description: str = Form(""),
):
    with get_db() as db:
        company_a = CompanyDB(
            id=str(uuid.uuid4()),
            name=company_a_name,
            role=CompanyRoleEnum(company_a_role),
            description=company_a_description,
        )
        company_b = CompanyDB(
            id=str(uuid.uuid4()),
            name=company_b_name,
            role=CompanyRoleEnum(company_b_role),
            description=company_b_description,
        )
        db.add(company_a)
        db.add(company_b)
        db.flush()
        
        transaction = TransactionDB(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            company_a_id=company_a.id,
            company_b_id=company_b.id,
            company_a_role=CompanyRoleEnum(company_a_role),
            company_b_role=CompanyRoleEnum(company_b_role),
            deal_value=deal_value,
        )
        db.add(transaction)
        db.commit()
    
    return RedirectResponse(url=f"/dashboard?transaction_id={transaction.id}", status_code=303)


@app.get("/comparisons", response_class=HTMLResponse)
async def comparisons_list(request: Request):
    with get_db() as db:
        comparisons_db = db.query(ComparisonRunDB).order_by(ComparisonRunDB.started_at.desc()).all()
        comparisons = []
        for comp in comparisons_db:
            txn = db.query(TransactionDB).filter(TransactionDB.id == comp.transaction_id).first()
            company_a = db.query(CompanyDB).filter(CompanyDB.id == txn.company_a_id).first() if txn else None
            company_b = db.query(CompanyDB).filter(CompanyDB.id == txn.company_b_id).first() if txn else None
            comparisons.append({
                "id": comp.id,
                "transaction_name": txn.name if txn else "Unknown",
                "company_a_name": company_a.name if company_a else "Unknown",
                "company_b_name": company_b.name if company_b else "Unknown",
                "matched_provisions": comp.matched_provisions,
                "findings_count": comp.findings_count,
                "material_asymmetries_count": comp.material_asymmetries_count,
                "cross_document_risks_count": comp.cross_document_risks_count,
                "disclosure_issues_count": comp.disclosure_issues_count,
                "status": comp.status,
            })
        return templates.TemplateResponse("comparisons.html", {
            "request": request,
            "comparisons": comparisons,
        })


@app.get("/comparisons/new", response_class=HTMLResponse)
async def new_comparison_page(request: Request):
    with get_db() as db:
        transactions = db.query(TransactionDB).all()
        txn_list = []
        for txn in transactions:
            company_a = db.query(CompanyDB).filter(CompanyDB.id == txn.company_a_id).first()
            company_b = db.query(CompanyDB).filter(CompanyDB.id == txn.company_b_id).first()
            runs_a = db.query(AnalysisRunDB).join(LegalPositionDB).join(DocumentDB).join(DocumentOwnershipDB).filter(DocumentOwnershipDB.company_id == txn.company_a_id).all() if company_a else []
            runs_b = db.query(AnalysisRunDB).join(LegalPositionDB).join(DocumentDB).join(DocumentOwnershipDB).filter(DocumentOwnershipDB.company_id == txn.company_b_id).all() if company_b else []
            txn_list.append({
                "id": txn.id,
                "name": txn.name,
                "company_a_name": company_a.name if company_a else "Unknown",
                "company_b_name": company_b.name if company_b else "Unknown",
                "runs_a": runs_a,
                "runs_b": runs_b,
            })
        return templates.TemplateResponse("new_comparison.html", {
            "request": request,
            "transactions": txn_list,
        })


@app.post("/comparison/run", response_class=HTMLResponse)
async def run_comparison_ui(
    request: Request,
    transaction_id: str = Form(...),
    company_a_run_id: str = Form(...),
    company_b_run_id: str = Form(...),
):
    result = comparison_service.run_comparison(
        transaction_id=transaction_id,
        company_a_run_id=company_a_run_id,
        company_b_run_id=company_b_run_id,
    )
    return RedirectResponse(url=f"/comparison/{result.comparison_id}", status_code=303)


@app.get("/comparison/{comparison_id}", response_class=HTMLResponse)
async def comparison_detail(request: Request, comparison_id: str):
    result = comparison_service.get_comparison(comparison_id)
    if not result:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    return templates.TemplateResponse("comparison_detail.html", {
        "request": request,
        "comparison": result,
        "verdict": result.verdict,
    })


@app.get("/comparison/{comparison_id}/export", response_class=HTMLResponse)
async def export_report(request: Request, comparison_id: str):
    result = comparison_service.get_comparison(comparison_id)
    if not result:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    # Generate HTML report
    from app.report.export import generate_html_report
    html_content = generate_html_report(result)
    return HTMLResponse(content=html_content)


@app.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request, transaction_id: Optional[str] = None):
    with get_db() as db:
        if transaction_id:
            txn_db = db.query(TransactionDB).filter(TransactionDB.id == transaction_id).first()
        else:
            txn_db = db.query(TransactionDB).order_by(TransactionDB.created_at.desc()).first()
        
        if not txn_db:
            return templates.TemplateResponse("documents.html", {
                "request": request,
                "transaction": None,
                "company_a": None,
                "company_b": None,
                "company_a_documents": [],
                "company_b_documents": [],
            })
        
        company_a_db = db.query(CompanyDB).filter(CompanyDB.id == txn_db.company_a_id).first()
        company_b_db = db.query(CompanyDB).filter(CompanyDB.id == txn_db.company_b_id).first()
        
        company_a_docs = []
        if company_a_db:
            docs = db.query(DocumentDB).join(DocumentOwnershipDB).filter(
                DocumentOwnershipDB.company_id == company_a_db.id
            ).all()
            for doc in docs:
                run = db.query(AnalysisRunDB).filter(
                    AnalysisRunDB.document_ids.contains(doc.id)
                ).order_by(AnalysisRunDB.started_at.desc()).first()
                company_a_docs.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "page_count": doc.page_count,
                    "document_type": doc.document_type,
                    "size_bytes": doc.size_bytes,
                    "analysis_status": run.status if run else "pending",
                    "run_id": run.id if run else None,
                })
        
        company_b_docs = []
        if company_b_db:
            docs = db.query(DocumentDB).join(DocumentOwnershipDB).filter(
                DocumentOwnershipDB.company_id == company_b_db.id
            ).all()
            for doc in docs:
                run = db.query(AnalysisRunDB).filter(
                    AnalysisRunDB.document_ids.contains(doc.id)
                ).order_by(AnalysisRunDB.started_at.desc()).first()
                company_b_docs.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "page_count": doc.page_count,
                    "document_type": doc.document_type,
                    "size_bytes": doc.size_bytes,
                    "analysis_status": run.status if run else "pending",
                    "run_id": run.id if run else None,
                })
        
        transaction = Transaction(
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
        
        company_a = Company(
            id=company_a_db.id,
            name=company_a_db.name,
            role=CompanyRole(company_a_db.role.value),
            description=company_a_db.description,
            company_metadata=company_a_db.company_metadata or {},
            created_at=company_a_db.created_at,
            updated_at=company_a_db.updated_at,
        ) if company_a_db else None
        
        company_b = Company(
            id=company_b_db.id,
            name=company_b_db.name,
            role=CompanyRole(company_b_db.role.value),
            description=company_b_db.description,
            company_metadata=company_b_db.company_metadata or {},
            created_at=company_b_db.created_at,
            updated_at=company_b_db.updated_at,
        ) if company_b_db else None
        
        return templates.TemplateResponse("documents.html", {
            "request": request,
            "transaction": transaction,
            "company_a": company_a,
            "company_b": company_b,
            "company_a_documents": company_a_docs,
            "company_b_documents": company_b_docs,
        })


@app.get("/documents/upload", response_class=HTMLResponse)
async def upload_page(request: Request, transaction_id: Optional[str] = None, company: Optional[str] = None):
    with get_db() as db:
        transaction = None
        company_a = None
        company_b = None
        
        if transaction_id:
            txn_db = db.query(TransactionDB).filter(TransactionDB.id == transaction_id).first()
            if txn_db:
                transaction = Transaction(
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
                company_a_db = db.query(CompanyDB).filter(CompanyDB.id == txn_db.company_a_id).first()
                company_b_db = db.query(CompanyDB).filter(CompanyDB.id == txn_db.company_b_id).first()
                company_a = Company(
                    id=company_a_db.id,
                    name=company_a_db.name,
                    role=CompanyRole(company_a_db.role.value),
                    description=company_a_db.description,
                    company_metadata=company_a_db.company_metadata or {},
                    created_at=company_a_db.created_at,
                    updated_at=company_a_db.updated_at,
                ) if company_a_db else None
                company_b = Company(
                    id=company_b_db.id,
                    name=company_b_db.name,
                    role=CompanyRole(company_b_db.role.value),
                    description=company_b_db.description,
                    company_metadata=company_b_db.company_metadata or {},
                    created_at=company_b_db.created_at,
                    updated_at=company_b_db.updated_at,
                ) if company_b_db else None
        
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "transaction": transaction,
            "company_a": company_a,
            "company_b": company_b,
            "selected_company": company,
        })


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    transaction_id: Optional[str] = Form(None),
    company_id: Optional[str] = Form(None),
    role_in_document: str = Form("UNKNOWN"),
    document_type: str = Form("UNKNOWN"),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    document_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.pdf")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)

        # Save document to database
        with get_db() as db:
            # Map document_type to valid enum value
            doc_type_value = document_type if document_type != "UNKNOWN" else "Unknown"
            doc_db = DocumentDB(
                id=document_id,
                filename=file.filename,
                content_type="application/pdf",
                size_bytes=file_size,
                document_type=doc_type_value,
            )
            db.add(doc_db)
            
            if transaction_id and company_id:
                ownership = DocumentOwnershipDB(
                    document_id=document_id,
                    company_id=company_id,
                    role_in_document=CompanyRoleEnum(role_in_document),
                )
                db.add(ownership)
            
            db.commit()

        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="uploaded",
            message=f"Document uploaded successfully. Size: {file_size} bytes",
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/analysis/status/{document_id}")
async def analysis_status(document_id: str):
    with get_db() as db:
        doc = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        run = db.query(AnalysisRunDB).join(LegalPositionDB).filter(
            LegalPositionDB.document_id == document_id
        ).order_by(AnalysisRunDB.started_at.desc()).first()
        
        if not run:
            return {"status": "pending", "document_id": document_id}
        
        return {
            "status": run.status,
            "document_id": document_id,
            "run_id": run.id,
            "positions_extracted": run.provisions_extracted,
            "verified": run.verified_findings,
            "progress": f"{run.verified_findings}/{run.provisions_extracted}" if run.provisions_extracted else "processing",
        }


# ========== API ROUTES ==========

@app.post("/api/analysis/run", response_model=RunResponse)
async def run_analysis(request: RunRequest):
    file_path = os.path.join(UPLOAD_DIR, f"{request.document_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        result = analysis_service.run_analysis(request.document_id, file_path, request.document_id)
        return RunResponse(
            run_id=result.run_id,
            status="completed",
            message=f"Analysis completed. {len(result.positions)} positions extracted.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analysis/{run_id}", response_model=AnalysisResult)
async def get_analysis(run_id: str):
    run = analysis_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    positions = analysis_service.get_findings(run_id)

    from app.models.schemas import ClassificationResult
    classification = ClassificationResult(
        document_type=run.document_ids[0] if run.document_ids else "UNKNOWN",
        confidence=0.0,
        reason="",
    )

    return AnalysisResult(
        run_id=run_id,
        document_id=run.document_ids[0] if run.document_ids else "",
        positions=positions,
        classification=classification,
        processing_time_ms=0,
    )


@app.get("/api/documents")
async def list_documents_api(transaction_id: str):
    with get_db() as db:
        txn_db = db.query(TransactionDB).filter(TransactionDB.id == transaction_id).first()
        if not txn_db:
            raise HTTPException(status_code=404, detail="Transaction not found")

        def documents_for_company(company_id: str):
            docs = db.query(DocumentDB).join(DocumentOwnershipDB).filter(
                DocumentOwnershipDB.company_id == company_id
            ).order_by(DocumentDB.created_at.desc()).all()
            result = []
            for doc in docs:
                run = db.query(AnalysisRunDB).filter(
                    AnalysisRunDB.document_ids.contains(doc.id)
                ).order_by(AnalysisRunDB.started_at.desc()).first()
                result.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "page_count": doc.page_count,
                    "document_type": doc.document_type,
                    "size_bytes": doc.size_bytes,
                    "analysis_status": run.status if run else "pending",
                    "run_id": run.id if run else None,
                    "classification_confidence": doc.classification_confidence,
                })
            return result

        return {
            "transaction_id": transaction_id,
            "company_a_documents": documents_for_company(txn_db.company_a_id),
            "company_b_documents": documents_for_company(txn_db.company_b_id),
        }


@app.get("/api/analysis/runs/company/{company_id}")
async def list_analysis_runs_for_company(company_id: str):
    with get_db() as db:
        company = db.query(CompanyDB).filter(CompanyDB.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        runs = (
            db.query(AnalysisRunDB)
            .join(LegalPositionDB, LegalPositionDB.run_id == AnalysisRunDB.id)
            .join(
                DocumentOwnershipDB,
                DocumentOwnershipDB.document_id == LegalPositionDB.document_id,
            )
            .filter(DocumentOwnershipDB.company_id == company_id)
            .distinct()
            .order_by(AnalysisRunDB.started_at.desc())
            .all()
        )
        return [
            {
                "id": run.id,
                "model_id": run.model_id,
                "status": run.status,
                "provisions_extracted": run.provisions_extracted,
                "verified_findings": run.verified_findings,
                "documents_processed": run.documents_processed,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
            }
            for run in runs
        ]


@app.get("/api/documents/{document_id}", response_model=Document)
async def get_document(document_id: str):
    doc = analysis_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.get("/api/findings/{run_id}", response_model=FindingsResponse)
async def get_findings(run_id: str):
    run = analysis_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    positions = analysis_service.get_findings(run_id)
    verified = sum(1 for p in positions if p.status.value == "VERIFIED")
    unverified = len(positions) - verified

    return FindingsResponse(
        run_id=run_id,
        total_positions=len(positions),
        verified=verified,
        unverified=unverified,
        positions=positions,
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "disclai"}


# ========== PHASE 2 COMPARISON ENDPOINTS ==========

@app.get("/api/companies")
async def list_companies():
    with get_db() as db:
        companies = db.query(CompanyDB).order_by(CompanyDB.created_at.desc()).all()
        return [
            {
                "id": company.id,
                "name": company.name,
                "role": company.role.value if hasattr(company.role, "value") else str(company.role),
            }
            for company in companies
        ]


@app.get("/api/transactions")
async def list_transactions():
    with get_db() as db:
        txns = db.query(TransactionDB).order_by(TransactionDB.created_at.desc()).all()
        result = []
        for txn in txns:
            company_a = db.query(CompanyDB).filter(CompanyDB.id == txn.company_a_id).first()
            company_b = db.query(CompanyDB).filter(CompanyDB.id == txn.company_b_id).first()
            result.append({
                "id": txn.id,
                "name": txn.name,
                "description": txn.description,
                "company_a_id": txn.company_a_id,
                "company_b_id": txn.company_b_id,
                "company_a_name": company_a.name if company_a else "Company A",
                "company_b_name": company_b.name if company_b else "Company B",
                "company_a_role": txn.company_a_role.value if hasattr(txn.company_a_role, "value") else str(txn.company_a_role),
                "company_b_role": txn.company_b_role.value if hasattr(txn.company_b_role, "value") else str(txn.company_b_role),
                "deal_value": txn.deal_value,
                "currency": txn.currency,
                "status": txn.status,
                "created_at": txn.created_at,
                "updated_at": txn.updated_at,
            })
        return result


@app.get("/api/comparisons")
async def list_comparisons():
    with get_db() as db:
        runs = db.query(ComparisonRunDB).order_by(ComparisonRunDB.started_at.desc()).all()
        results = []
        for run in runs:
            try:
                result = comparison_service.get_comparison(run.id)
                if result:
                    results.append(result)
            except Exception as exc:
                logger.warning("Skipping comparison %s: %s", run.id, exc)
        return results


@app.post("/api/companies", response_model=Company)
async def create_company(company: CompanyCreate):
    with get_db() as db:
        comp_db = CompanyDB(
            id=str(uuid.uuid4()),
            name=company.name,
            role=CompanyRoleEnum(company.role.value),
            description=company.description,
        )
        db.add(comp_db)
        db.commit()
        db.refresh(comp_db)
        return Company(
            id=comp_db.id,
            name=comp_db.name,
            role=CompanyRole(comp_db.role.value),
            description=comp_db.description,
            company_metadata=comp_db.company_metadata or {},
            created_at=comp_db.created_at,
            updated_at=comp_db.updated_at,
        )


@app.get("/api/companies/{company_id}", response_model=Company)
async def get_company(company_id: str):
    with get_db() as db:
        comp_db = db.query(CompanyDB).filter(CompanyDB.id == company_id).first()
        if not comp_db:
            raise HTTPException(status_code=404, detail="Company not found")
        return Company(
            id=comp_db.id,
            name=comp_db.name,
            role=CompanyRole(comp_db.role.value),
            description=comp_db.description,
            company_metadata=comp_db.company_metadata or {},
            created_at=comp_db.created_at,
            updated_at=comp_db.updated_at,
        )


@app.post("/api/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate):
    with get_db() as db:
        txn_db = TransactionDB(
            id=str(uuid.uuid4()),
            name=transaction.name,
            description=transaction.description,
            company_a_id=transaction.company_a_id,
            company_b_id=transaction.company_b_id,
            company_a_role=CompanyRoleEnum(transaction.company_a_role.value),
            company_b_role=CompanyRoleEnum(transaction.company_b_role.value),
            deal_value=transaction.deal_value,
            currency=transaction.currency,
        )
        db.add(txn_db)
        db.commit()
        db.refresh(txn_db)
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


@app.get("/api/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str):
    with get_db() as db:
        txn_db = db.query(TransactionDB).filter(TransactionDB.id == transaction_id).first()
        if not txn_db:
            raise HTTPException(status_code=404, detail="Transaction not found")
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


@app.post("/api/comparison/run", response_model=ComparisonRun)
async def run_comparison(request: ComparisonRequest):
    try:
        result = comparison_service.run_comparison(
            transaction_id=request.transaction_id,
            company_a_run_id=request.company_a_run_id,
            company_b_run_id=request.company_b_run_id,
        )
        return ComparisonRun(
            id=result.comparison_id,
            transaction_id=result.transaction_id,
            company_a_run_id=request.company_a_run_id,
            company_b_run_id=request.company_b_run_id,
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            total_positions_a=len(comparison_service.analysis_service.get_findings(request.company_a_run_id)),
            total_positions_b=len(comparison_service.analysis_service.get_findings(request.company_b_run_id)),
            matched_provisions=len([m for m in result.matches if m.match_status.value == "MATCHED"]),
            unmatched_provisions=len([m for m in result.matches if m.match_status.value == "UNMATCHED"]),
            findings_count=len(result.findings),
            material_asymmetries_count=len([f for f in result.findings if f.classification.value == "MATERIAL_ASYMMETRY"]),
            cross_document_risks_count=len(result.cross_document_risks),
            disclosure_issues_count=len(result.disclosure_issues),
            llm_calls=result.total_llm_calls,
            processing_time_ms=result.processing_time_ms,
            error_details=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.get("/api/comparison/{comparison_id}", response_model=ComparisonResult)
async def get_comparison(comparison_id: str):
    result = comparison_service.get_comparison(comparison_id)
    if not result:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return result


@app.get("/api/comparison/{comparison_id}/findings")
async def get_comparison_findings(comparison_id: str):
    result = comparison_service.get_comparison(comparison_id)
    if not result:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return {
        "comparison_id": comparison_id,
        "total_findings": len(result.findings),
        "material_asymmetries": len([f for f in result.findings if f.classification.value == "MATERIAL_ASYMMETRY"]),
        "findings": result.findings,
    }


@app.get("/api/comparison/{comparison_id}/verdict")
async def get_comparison_verdict(comparison_id: str):
    result = comparison_service.get_comparison(comparison_id)
    if not result or not result.verdict:
        raise HTTPException(status_code=404, detail="Verdict not found")
    return result.verdict


@app.get("/api/comparison/{comparison_id}/recommendations")
async def get_comparison_recommendations(comparison_id: str):
    result = comparison_service.get_comparison(comparison_id)
    if not result:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    return {
        "comparison_id": comparison_id,
        "verdict_recommendations": {
            "company_a": result.verdict.company_a_recommendations if result.verdict else [],
            "company_b": result.verdict.company_b_recommendations if result.verdict else [],
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)