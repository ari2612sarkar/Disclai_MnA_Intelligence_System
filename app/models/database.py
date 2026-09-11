from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid
from app.models.schemas import (
    DocumentType, LegalCategory, PartyRole, ExtractionStatus,
    CompanyRole, MatchStatus, AsymmetryClassification, RecommendationType, Priority
)
import enum

Base = declarative_base()


class DocumentTypeEnum(enum.Enum):
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


class LegalCategoryEnum(enum.Enum):
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


class PartyRoleEnum(enum.Enum):
    SELLER = "Seller"
    BUYER = "Buyer"
    TARGET = "Target"
    COMPANY = "Company"
    PARENT = "Parent"
    UNKNOWN = "Unknown"


class CompanyRoleEnum(enum.Enum):
    BUYER = "Buyer"
    SELLER = "Seller"
    TARGET = "Target"
    ACQUIRER = "Acquirer"
    PARENT = "Parent"
    AFFILIATE = "Affiliate"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class ExtractionStatusEnum(enum.Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class MatchStatusEnum(enum.Enum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    UNMATCHED = "UNMATCHED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class AsymmetryClassificationEnum(enum.Enum):
    MATERIAL_ASYMMETRY = "MATERIAL_ASYMMETRY"
    MINOR_DIFFERENCE = "MINOR_DIFFERENCE"
    POTENTIAL_ASYMMETRY = "POTENTIAL_ASYMMETRY"
    NO_MATERIAL_DIFFERENCE = "NO_MATERIAL_DIFFERENCE"
    CONFLICT = "CONFLICT"
    INFORMATIONAL = "INFORMATIONAL"
    PRESENCE_ABSENCE = "PRESENCE_ABSENCE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class RecommendationTypeEnum(enum.Enum):
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


class PriorityEnum(enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DocumentDB(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), default="application/pdf")
    size_bytes = Column(Integer, default=0)
    document_type = Column(SQLEnum(DocumentTypeEnum, native_enum=False, values_callable=lambda x: [e.value for e in DocumentTypeEnum]), default=DocumentTypeEnum.UNKNOWN)
    classification_confidence = Column(Float, default=0.0)
    classification_reason = Column(Text, default="")
    governing_entities = Column(JSON, default=list)
    source_metadata = Column(JSON, default=dict)
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pages = relationship("PageDB", back_populates="document", cascade="all, delete-orphan")
    sections = relationship("SectionDB", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("ChunkDB", back_populates="document", cascade="all, delete-orphan")
    provisions = relationship("ProvisionDB", back_populates="document", cascade="all, delete-orphan")
    positions = relationship("LegalPositionDB", back_populates="document", cascade="all, delete-orphan")


class PageDB(Base):
    __tablename__ = "pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, default="")
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)

    document = relationship("DocumentDB", back_populates="pages")


class SectionDB(Base):
    __tablename__ = "sections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    section_number = Column(String(50), nullable=True)
    heading = Column(Text, nullable=False)
    level = Column(Integer, default=1)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)

    document = relationship("DocumentDB", back_populates="sections")


class ChunkDB(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    section_id = Column(String(36), ForeignKey("sections.id"), nullable=True)
    heading = Column(Text, default="")
    text = Column(Text, nullable=False)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)
    token_count = Column(Integer, default=0)
    embedding = Column(JSON, nullable=True)

    document = relationship("DocumentDB", back_populates="chunks")
    section = relationship("SectionDB")


class ProvisionDB(Base):
    __tablename__ = "provisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    category = Column(SQLEnum(LegalCategoryEnum, native_enum=False, values_callable=lambda x: [e.value for e in LegalCategoryEnum]), nullable=False)
    subcategory = Column(String(100), nullable=True)
    provision_name = Column(String(255), nullable=False)
    section_id = Column(String(36), ForeignKey("sections.id"), nullable=True)
    heading = Column(Text, default="")
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)
    party_mentioned = Column(JSON, default=list)
    keywords = Column(JSON, default=list)

    document = relationship("DocumentDB", back_populates="provisions")
    section = relationship("SectionDB")


class LegalPositionDB(Base):
    __tablename__ = "legal_positions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    run_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=True)
    category = Column(SQLEnum(LegalCategoryEnum, native_enum=False, values_callable=lambda x: [e.value for e in LegalCategoryEnum]), nullable=False)
    subcategory = Column(String(100), nullable=True)
    provision_name = Column(String(255), nullable=False)
    party = Column(SQLEnum(PartyRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in PartyRoleEnum]), default=PartyRoleEnum.UNKNOWN)
    obligation_right = Column(Text, default="")
    threshold = Column(String(100), nullable=True)
    amount = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    duration = Column(String(100), nullable=True)
    condition = Column(JSON, default=list)
    exception = Column(JSON, default=list)
    qualifier = Column(JSON, default=list)
    consequence = Column(JSON, default=list)
    evidence_document_id = Column(String(36), nullable=False)
    evidence_page = Column(Integer, nullable=False)
    evidence_section_id = Column(String(36), nullable=True)
    evidence_section_number = Column(String(50), nullable=True)
    evidence_heading = Column(Text, default="")
    evidence_text = Column(Text, nullable=False)
    evidence_char_start = Column(Integer, nullable=False)
    evidence_char_end = Column(Integer, nullable=False)
    evidence_chunk_id = Column(String(36), nullable=True)
    confidence = Column(Float, default=0.0)
    status = Column(SQLEnum(ExtractionStatusEnum, native_enum=False, values_callable=lambda x: [e.value for e in ExtractionStatusEnum]), default=ExtractionStatusEnum.UNVERIFIED)
    raw_extraction = Column(JSON, nullable=True)

    document = relationship("DocumentDB", back_populates="positions")
    run = relationship("AnalysisRunDB", back_populates="positions")
    matches_as_a = relationship("LegalPositionMatchDB", back_populates="company_a_position", foreign_keys="LegalPositionMatchDB.company_a_position_id")
    matches_as_b = relationship("LegalPositionMatchDB", back_populates="company_b_position", foreign_keys="LegalPositionMatchDB.company_b_position_id")
    findings_as_a = relationship("ComparisonFindingDB", back_populates="company_a_position", foreign_keys="ComparisonFindingDB.company_a_position_id")
    findings_as_b = relationship("ComparisonFindingDB", back_populates="company_b_position", foreign_keys="ComparisonFindingDB.company_b_position_id")
    disclosure_issues = relationship("DisclosureIssueDB", back_populates="spa_requirement_position")


class AnalysisRunDB(Base):
    __tablename__ = "analysis_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(255), nullable=False)
    documents_processed = Column(Integer, default=0)
    provisions_extracted = Column(Integer, default=0)
    verified_findings = Column(Integer, default=0)
    unverified_findings = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    status = Column(String(50), default="running")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    document_ids = Column(JSON, default=list)
    error_details = Column(JSON, default=list)

    positions = relationship("LegalPositionDB", back_populates="run")
    comparisons_as_a = relationship("ComparisonRunDB", back_populates="company_a_run", foreign_keys="ComparisonRunDB.company_a_run_id")
    comparisons_as_b = relationship("ComparisonRunDB", back_populates="company_b_run", foreign_keys="ComparisonRunDB.company_b_run_id")


Index("ix_chunks_document_page", ChunkDB.document_id, ChunkDB.page_number)
Index("ix_provisions_document_category", ProvisionDB.document_id, ProvisionDB.category)
Index("ix_positions_run", LegalPositionDB.run_id)


# ========== PHASE 2 DATABASE MODELS ==========

class CompanyDB(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    role = Column(SQLEnum(CompanyRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in CompanyRoleEnum]), default=CompanyRoleEnum.UNKNOWN)
    description = Column(Text, nullable=True)
    company_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("DocumentOwnershipDB", back_populates="company")
    transactions_a = relationship("TransactionDB", back_populates="company_a", foreign_keys="TransactionDB.company_a_id")
    transactions_b = relationship("TransactionDB", back_populates="company_b", foreign_keys="TransactionDB.company_b_id")


class TransactionDB(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")
    company_a_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    company_b_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    company_a_role = Column(SQLEnum(CompanyRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in CompanyRoleEnum]), nullable=False)
    company_b_role = Column(SQLEnum(CompanyRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in CompanyRoleEnum]), nullable=False)
    deal_value = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company_a = relationship("CompanyDB", back_populates="transactions_a", foreign_keys=[company_a_id])
    company_b = relationship("CompanyDB", back_populates="transactions_b", foreign_keys=[company_b_id])
    comparisons = relationship("ComparisonRunDB", back_populates="transaction")


class DocumentOwnershipDB(Base):
    __tablename__ = "document_ownership"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    role_in_document = Column(SQLEnum(CompanyRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in CompanyRoleEnum]), default=CompanyRoleEnum.UNKNOWN)

    document = relationship("DocumentDB")
    company = relationship("CompanyDB", back_populates="documents")


class LegalPositionMatchDB(Base):
    __tablename__ = "legal_position_matches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comparison_id = Column(String(36), ForeignKey("comparison_runs.id"), nullable=False)
    company_a_position_id = Column(String(36), ForeignKey("legal_positions.id"), nullable=True)
    company_b_position_id = Column(String(36), ForeignKey("legal_positions.id"), nullable=True)
    match_status = Column(SQLEnum(MatchStatusEnum, native_enum=False, values_callable=lambda x: [e.value for e in MatchStatusEnum]), default=MatchStatusEnum.REQUIRES_REVIEW)
    match_confidence = Column(Float, default=0.0)
    match_reason = Column(Text, default="")
    matched_attributes = Column(JSON, default=list)

    comparison = relationship("ComparisonRunDB", back_populates="matches")
    company_a_position = relationship("LegalPositionDB", foreign_keys=[company_a_position_id])
    company_b_position = relationship("LegalPositionDB", foreign_keys=[company_b_position_id])


class ComparisonFindingDB(Base):
    __tablename__ = "comparison_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comparison_id = Column(String(36), ForeignKey("comparison_runs.id"), nullable=False)
    category = Column(SQLEnum(LegalCategoryEnum, native_enum=False, values_callable=lambda x: [e.value for e in LegalCategoryEnum]), nullable=False)
    provision = Column(String(255), nullable=False)
    subcategory = Column(String(100), nullable=True)

    company_a_position_id = Column(String(36), ForeignKey("legal_positions.id"), nullable=True)
    company_b_position_id = Column(String(36), ForeignKey("legal_positions.id"), nullable=True)

    differences = Column(JSON, default=list)
    classification = Column(SQLEnum(AsymmetryClassificationEnum, native_enum=False, values_callable=lambda x: [e.value for e in AsymmetryClassificationEnum]), default=AsymmetryClassificationEnum.REQUIRES_REVIEW)
    classification_reason = Column(Text, default="")

    beneficiary = Column(SQLEnum(CompanyRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in CompanyRoleEnum]), nullable=True)
    affected_dimension = Column(String(100), nullable=True)
    advantage_confidence = Column(Float, default=0.0)
    advantage_explanation = Column(Text, default="")

    legal_impact = Column(Text, default="")
    commercial_impact = Column(Text, default="")
    closing_impact = Column(Text, default="")
    post_closing_impact = Column(Text, default="")
    negotiation_impact = Column(Text, default="")

    comparison_confidence = Column(Float, default=0.0)
    materiality_confidence = Column(Float, default=0.0)
    requires_lawyer_review = Column(JSON, default=True)

    evidence_a = Column(JSON, default=list)
    evidence_b = Column(JSON, default=list)

    cross_document_dependencies = Column(JSON, default=list)
    disclosure_issues = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    comparison = relationship("ComparisonRunDB", back_populates="findings")
    company_a_position = relationship("LegalPositionDB", foreign_keys=[company_a_position_id])
    company_b_position = relationship("LegalPositionDB", foreign_keys=[company_b_position_id])
    recommendations = relationship("RecommendationDB", back_populates="finding")


class RecommendationDB(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id = Column(String(36), ForeignKey("comparison_findings.id"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    company_role = Column(SQLEnum(CompanyRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in CompanyRoleEnum]), nullable=False)
    recommendation_type = Column(SQLEnum(RecommendationTypeEnum, native_enum=False, values_callable=lambda x: [e.value for e in RecommendationTypeEnum]), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    rationale = Column(Text, default="")
    current_position = Column(Text, default="")
    proposed_adjustment = Column(Text, default="")
    legal_basis = Column(Text, default="")
    commercial_tradeoff = Column(Text, default="")
    negotiation_objective = Column(Text, default="")
    priority = Column(SQLEnum(PriorityEnum, native_enum=False, values_callable=lambda x: [e.value for e in PriorityEnum]), default=PriorityEnum.MEDIUM)
    confidence = Column(Float, default=0.0)
    depends_on = Column(JSON, default=list)

    finding = relationship("ComparisonFindingDB", back_populates="recommendations")
    company = relationship("CompanyDB")


class CrossDocumentRiskDB(Base):
    __tablename__ = "cross_document_risks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comparison_id = Column(String(36), ForeignKey("comparison_runs.id"), nullable=False)
    risk_type = Column(String(100), nullable=False)
    severity = Column(SQLEnum(PriorityEnum, native_enum=False, values_callable=lambda x: [e.value for e in PriorityEnum]), default=PriorityEnum.MEDIUM)
    component_findings = Column(JSON, default=list)
    description = Column(Text, default="")
    impact = Column(Text, default="")
    evidence_references = Column(JSON, default=list)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    comparison = relationship("ComparisonRunDB", back_populates="cross_document_risks")


class DisclosureIssueDB(Base):
    __tablename__ = "disclosure_issues"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comparison_id = Column(String(36), ForeignKey("comparison_runs.id"), nullable=False)
    issue_type = Column(String(100), nullable=False)
    description = Column(Text, default="")
    spa_requirement_position_id = Column(String(36), ForeignKey("legal_positions.id"), nullable=True)
    disclosure_schedule_evidence = Column(JSON, nullable=True)
    data_room_evidence = Column(JSON, nullable=True)
    severity = Column(SQLEnum(PriorityEnum, native_enum=False, values_callable=lambda x: [e.value for e in PriorityEnum]), default=PriorityEnum.MEDIUM)
    confidence = Column(Float, default=0.0)
    status = Column(String(50), default="POTENTIAL_MISSING_DISCLOSURE")
    created_at = Column(DateTime, default=datetime.utcnow)

    comparison = relationship("ComparisonRunDB", back_populates="disclosure_issues")
    spa_requirement_position = relationship("LegalPositionDB")


class DealVerdictDB(Base):
    __tablename__ = "deal_verdicts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comparison_id = Column(String(36), ForeignKey("comparison_runs.id"), nullable=False)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False)

    overall_assessment = Column(Text, default="")
    overall_risk_level = Column(SQLEnum(PriorityEnum, native_enum=False, values_callable=lambda x: [e.value for e in PriorityEnum]), default=PriorityEnum.MEDIUM)

    key_asymmetries = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    material_asymmetries = Column(Integer, default=0)
    evidence_backed_findings = Column(Integer, default=0)

    company_a_advantages = Column(JSON, default=list)
    company_a_weaknesses = Column(JSON, default=list)
    company_b_advantages = Column(JSON, default=list)
    company_b_weaknesses = Column(JSON, default=list)

    critical_findings = Column(JSON, default=list)
    recommended_actions = Column(JSON, default=list)
    unresolved_questions = Column(JSON, default=list)

    score = Column(Float, nullable=True)
    score_methodology = Column(Text, default="")

    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    comparison = relationship("ComparisonRunDB", back_populates="verdict")
    transaction = relationship("TransactionDB")


class ComparisonRunDB(Base):
    __tablename__ = "comparison_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False)
    company_a_run_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False)
    company_b_run_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False)
    status = Column(String(50), default="running")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_positions_a = Column(Integer, default=0)
    total_positions_b = Column(Integer, default=0)
    matched_provisions = Column(Integer, default=0)
    unmatched_provisions = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    material_asymmetries_count = Column(Integer, default=0)
    cross_document_risks_count = Column(Integer, default=0)
    disclosure_issues_count = Column(Integer, default=0)
    llm_calls = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)
    error_details = Column(JSON, default=list)

    transaction = relationship("TransactionDB", back_populates="comparisons")
    company_a_run = relationship("AnalysisRunDB", foreign_keys=[company_a_run_id])
    company_b_run = relationship("AnalysisRunDB", foreign_keys=[company_b_run_id])
    matches = relationship("LegalPositionMatchDB", back_populates="comparison")
    findings = relationship("ComparisonFindingDB", back_populates="comparison")
    cross_document_risks = relationship("CrossDocumentRiskDB", back_populates="comparison")
    disclosure_issues = relationship("DisclosureIssueDB", back_populates="comparison")
    verdict = relationship("DealVerdictDB", back_populates="comparison", uselist=False)


Index("ix_companies_role", CompanyDB.role)
Index("ix_transactions_companies", TransactionDB.company_a_id, TransactionDB.company_b_id)
Index("ix_document_ownership_document", DocumentOwnershipDB.document_id)
Index("ix_document_ownership_company", DocumentOwnershipDB.company_id)
Index("ix_position_matches_comparison", LegalPositionMatchDB.comparison_id)
Index("ix_position_matches_positions", LegalPositionMatchDB.company_a_position_id, LegalPositionMatchDB.company_b_position_id)
Index("ix_findings_comparison", ComparisonFindingDB.comparison_id)
Index("ix_findings_classification", ComparisonFindingDB.classification)
Index("ix_recommendations_finding", RecommendationDB.finding_id)
Index("ix_recommendations_company", RecommendationDB.company_id)
Index("ix_cross_doc_risks_comparison", CrossDocumentRiskDB.comparison_id)
Index("ix_disclosure_issues_comparison", DisclosureIssueDB.comparison_id)
Index("ix_deal_verdicts_comparison", DealVerdictDB.comparison_id)
Index("ix_comparison_runs_transaction", ComparisonRunDB.transaction_id)