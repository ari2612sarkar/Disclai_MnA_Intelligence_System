from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import re


class DocumentType(str, Enum):
    SPA = "SPA"
    MERGER_AGREEMENT = "Merger Agreement"
    DISCLOSURE_SCHEDULE = "Disclosure Schedule"
    COMMERCIAL_CONTRACT = "Commercial Contract"
    LITIGATION_DOCUMENT = "Litigation Document"
    EMPLOYMENT_DOCUMENT = "Employment Document"
    IP_DOCUMENT = "IP Document"
    FINANCING_DOCUMENT = "Financing Document"
    REGULATORY_DOCUMENT = "Regulatory Document"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class LegalCategory(str, Enum):
    REPRESENTATIONS_WARRANTIES = "Representations & Warranties"
    INDEMNIFICATION = "Indemnification / Liability Caps"
    MATERIAL_ADVERSE_EFFECT = "Material Adverse Effect"
    TERMINATION_RIGHTS = "Termination Rights"
    CLOSING_CONDITIONS = "Closing Conditions"
    MATERIAL_CONTRACTS = "Material Contracts"
    LITIGATION = "Litigation"
    CHANGE_OF_CONTROL = "Change-of-Control / Assignment"
    DISCLOSURE_EXCEPTIONS = "Disclosure / Exceptions"
    RW_INSURANCE = "R&W Insurance"


class PartyRole(str, Enum):
    SELLER = "Seller"
    BUYER = "Buyer"
    TARGET = "Target"
    COMPANY = "Company"
    PARENT = "Parent"
    UNKNOWN = "Unknown"


class ExtractionStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class DocumentBase(BaseModel):
    filename: str
    content_type: str = "application/pdf"
    size_bytes: int


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: DocumentType = DocumentType.UNKNOWN
    classification_confidence: float = 0.0
    classification_reason: str = ""
    governing_entities: List[str] = Field(default_factory=list)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    page_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Page(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    text: str = ""
    char_start: int = 0
    char_end: int = 0


class Section(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    section_number: Optional[str] = None
    heading: str
    level: int = 1
    char_start: int = 0
    char_end: int = 0


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    section_id: Optional[str] = None
    heading: str = ""
    text: str
    char_start: int
    char_end: int
    token_count: int = 0
    embedding: Optional[List[float]] = None


class ClassificationResult(BaseModel):
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    governing_entities: List[str] = Field(default_factory=list)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    document_id: str
    page_number: int
    section_id: Optional[str] = None
    section_number: Optional[str] = None
    heading: str = ""
    text: str
    char_start: Optional[int] = 0
    char_end: Optional[int] = 0
    chunk_id: Optional[str] = None


class DurationNormalized(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    normalized_months: Optional[float] = None
    raw_text: Optional[str] = None
    parse_status: str = "PARSED"

    @property
    def is_valid(self) -> bool:
        return self.normalized_months is not None and self.parse_status == "PARSED"


def parse_duration(duration_text: Optional[str]) -> DurationNormalized:
    if not duration_text:
        return DurationNormalized(parse_status="NOT_PROVIDED")
    
    text = duration_text.strip().lower()
    raw = duration_text.strip()
    
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*(year|years|yr|yrs)\b', 'years', 12),
        (r'(\d+(?:\.\d+)?)\s*(month|months|mo|mos)\b', 'months', 1),
        (r'(\d+(?:\.\d+)?)\s*(week|weeks|wk|wks)\b', 'weeks', 1/4.345),
        (r'(\d+(?:\.\d+)?)\s*(day|days|d)\b', 'days', 1/30.4375),
        (r'(\d+(?:\.\d+)?)\s*(quarter|quarters|qtr|qtrs)\b', 'quarters', 3),
    ]
    
    for pattern, unit, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1))
            normalized = value * multiplier
            return DurationNormalized(
                value=value,
                unit=unit,
                normalized_months=normalized,
                raw_text=raw,
                parse_status="PARSED"
            )
    
    return DurationNormalized(
        raw_text=raw,
        parse_status="REQUIRES_REVIEW"
    )


def compare_durations(dur_a: DurationNormalized, dur_b: DurationNormalized) -> Optional[Dict[str, Any]]:
    if not dur_a.is_valid or not dur_b.is_valid:
        return {
            "difference_months": None,
            "status": "REQUIRES_REVIEW",
            "reason": f"Duration parsing failed: A={dur_a.parse_status}, B={dur_b.parse_status}"
        }
    
    diff = dur_b.normalized_months - dur_a.normalized_months
    return {
        "difference_months": round(diff, 2),
        "difference_weeks": round(diff * 4.345, 2),
        "difference_days": round(diff * 30.4375, 2),
        "company_a_months": dur_a.normalized_months,
        "company_b_months": dur_b.normalized_months,
        "status": "COMPARED"
    }


class LegalPosition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: LegalCategory
    subcategory: Optional[str] = None
    provision_name: str
    party: PartyRole
    obligation_right: str = ""
    threshold: Optional[str] = None
    amount: Optional[float] = None
    percentage: Optional[float] = None
    unit: Optional[str] = None
    duration: Optional[str] = None
    duration_normalized: Optional[DurationNormalized] = None
    condition: List[str] = Field(default_factory=list)
    exception: List[str] = Field(default_factory=list)
    qualifier: List[str] = Field(default_factory=list)
    consequence: List[str] = Field(default_factory=list)
    evidence: Evidence
    confidence: float = Field(ge=0.0, le=1.0)
    status: ExtractionStatus = ExtractionStatus.UNVERIFIED
    raw_extraction: Optional[Dict[str, Any]] = None

    def to_comparable_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "subcategory": self.subcategory,
            "provision": self.provision_name,
            "party": self.party.value,
            "position": {
                "obligation_right": self.obligation_right,
                "threshold": self.threshold,
                "amount": self.amount,
                "percentage": self.percentage,
                "unit": self.unit,
                "duration": self.duration,
                "conditions": self.condition,
                "exceptions": self.exception,
                "qualifiers": self.qualifier,
                "consequences": self.consequence,
            },
            "evidence": self.evidence.model_dump(),
            "confidence": self.confidence,
            "status": self.status.value,
        }


class Provision(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    category: LegalCategory
    subcategory: Optional[str] = None
    provision_name: str
    section_id: Optional[str] = None
    heading: str = ""
    text: str
    page_number: int
    char_start: int
    char_end: int
    party_mentioned: List[PartyRole] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class AnalysisRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str
    documents_processed: int = 0
    provisions_extracted: int = 0
    verified_findings: int = 0
    unverified_findings: int = 0
    errors: int = 0
    status: str = "running"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    document_ids: List[str] = Field(default_factory=list)
    error_details: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    run_id: str
    document_id: str
    positions: List[LegalPosition]
    classification: ClassificationResult
    processing_time_ms: int
    errors: List[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class FindingsResponse(BaseModel):
    run_id: str
    total_positions: int
    verified: int
    unverified: int
    positions: List[LegalPosition]


# ========== PHASE 2 MODELS ==========

class CompanyRole(str, Enum):
    BUYER = "Buyer"
    SELLER = "Seller"
    TARGET = "Target"
    ACQUIRER = "Acquirer"
    PARENT = "Parent"
    AFFILIATE = "Affiliate"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class Company(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: CompanyRole = CompanyRole.UNKNOWN
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    status: str = "active"
    company_a_id: str
    company_b_id: str
    company_a_role: CompanyRole
    company_b_role: CompanyRole
    deal_value: Optional[float] = None
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentOwnership(BaseModel):
    document_id: str
    company_id: str
    role_in_document: CompanyRole


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    UNMATCHED = "UNMATCHED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class LegalPositionMatch(BaseModel):
    company_a_position: Optional[LegalPosition] = None
    company_b_position: Optional[LegalPosition] = None
    match_status: MatchStatus
    match_confidence: float = Field(ge=0.0, le=1.0)
    match_reason: str = ""
    matched_attributes: List[str] = Field(default_factory=list)


class AsymmetryClassification(str, Enum):
    MATERIAL_ASYMMETRY = "MATERIAL_ASYMMETRY"
    MINOR_DIFFERENCE = "MINOR_DIFFERENCE"
    POTENTIAL_ASYMMETRY = "POTENTIAL_ASYMMETRY"
    NO_MATERIAL_DIFFERENCE = "NO_MATERIAL_DIFFERENCE"
    CONFLICT = "CONFLICT"
    INFORMATIONAL = "INFORMATIONAL"
    PRESENCE_ABSENCE = "PRESENCE_ABSENCE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class DifferenceDetail(BaseModel):
    attribute: str
    company_a_value: Any = None
    company_b_value: Any = None
    difference: Optional[Any] = None
    direction: Optional[str] = None
    absolute_difference: Optional[float] = None


class ComparisonFinding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    comparison_id: str
    category: LegalCategory
    provision: str
    subcategory: Optional[str] = None
    
    company_a_position: Optional[LegalPosition] = None
    company_b_position: Optional[LegalPosition] = None
    
    differences: List[DifferenceDetail] = Field(default_factory=list)
    classification: AsymmetryClassification = AsymmetryClassification.REQUIRES_REVIEW
    classification_reason: str = ""
    
    beneficiary: Optional[CompanyRole] = None
    affected_dimension: Optional[str] = None
    advantage_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    advantage_explanation: str = ""
    
    legal_impact: str = ""
    commercial_impact: str = ""
    closing_impact: str = ""
    post_closing_impact: str = ""
    negotiation_impact: str = ""
    
    comparison_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    materiality_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_lawyer_review: bool = True
    
    evidence_a: List[Evidence] = Field(default_factory=list)
    evidence_b: List[Evidence] = Field(default_factory=list)
    
    cross_document_dependencies: List[str] = Field(default_factory=list)
    disclosure_issues: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationType(str, Enum):
    DISCLOSURE = "DISCLOSURE"
    REPRESENTATION_WARRANTY_QUALIFICATION = "REPRESENTATION_WARRANTY_QUALIFICATION"
    INDEMNITY = "INDEMNITY"
    COVENANT = "COVENANT"
    CONSENT = "CONSENT"
    PRICE_ADJUSTMENT = "PRICE_ADJUSTMENT"
    SPA_AMENDMENT = "SPA_AMENDMENT"
    TERMINATION_PROTECTION = "TERMINATION_PROTECTION"
    LIABILITY_CAP_ADJUSTMENT = "LIABILITY_CAP_ADJUSTMENT"
    TARGETED_EXCEPTION = "TARGETED_EXCEPTION"
    INFORMATION_REQUEST = "INFORMATION_REQUEST"
    FURTHER_DILIGENCE = "FURTHER_DILIGENCE"


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PartySpecificRecommendation(BaseModel):
    company_id: str
    company_role: CompanyRole
    recommendation_type: RecommendationType
    title: str
    description: str
    rationale: str
    current_position: str
    proposed_adjustment: str
    legal_basis: str
    commercial_tradeoff: str
    negotiation_objective: str
    priority: Priority = Priority.MEDIUM
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    depends_on: List[str] = Field(default_factory=list)
    finding_id: Optional[str] = None


class RecommendationSet(BaseModel):
    finding_id: str
    company_a_recommendation: Optional[PartySpecificRecommendation] = None
    company_b_recommendation: Optional[PartySpecificRecommendation] = None


class CrossDocumentRisk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    comparison_id: str
    risk_type: str
    severity: Priority
    component_findings: List[str]
    description: str
    impact: str
    evidence_references: List[Evidence] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DisclosureIssue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    comparison_id: str
    issue_type: str
    description: str
    spa_requirement: Optional[LegalPosition] = None
    disclosure_schedule_evidence: Optional[Evidence] = None
    data_room_evidence: Optional[Evidence] = None
    severity: Priority
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = "POTENTIAL_MISSING_DISCLOSURE"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DealVerdict(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    comparison_id: str
    transaction_id: str
    
    overall_assessment: str
    overall_risk_level: Priority
    
    key_asymmetries: int = 0
    critical_issues: int = 0
    material_asymmetries: int = 0
    evidence_backed_findings: int = 0
    
    company_a_advantages: List[str] = Field(default_factory=list)
    company_a_weaknesses: List[str] = Field(default_factory=list)
    company_b_advantages: List[str] = Field(default_factory=list)
    company_b_weaknesses: List[str] = Field(default_factory=list)
    
    critical_findings: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    
    score: Optional[float] = None
    score_methodology: str = ""
    
    company_a_recommendations: List[PartySpecificRecommendation] = Field(default_factory=list)
    company_b_recommendations: List[PartySpecificRecommendation] = Field(default_factory=list)
    
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ComparisonRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str
    company_a_run_id: str
    company_b_run_id: str
    status: str = "running"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_positions_a: int = 0
    total_positions_b: int = 0
    matched_provisions: int = 0
    unmatched_provisions: int = 0
    findings_count: int = 0
    material_asymmetries_count: int = 0
    cross_document_risks_count: int = 0
    disclosure_issues_count: int = 0
    llm_calls: int = 0
    processing_time_ms: int = 0
    error_details: List[str] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    comparison_id: str
    transaction_id: str
    company_a_name: str
    company_b_name: str
    company_a_role: CompanyRole
    company_b_role: CompanyRole
    
    matches: List[LegalPositionMatch]
    findings: List[ComparisonFinding]
    cross_document_risks: List[CrossDocumentRisk]
    disclosure_issues: List[DisclosureIssue]
    verdict: DealVerdict
    
    processing_time_ms: int
    total_llm_calls: int