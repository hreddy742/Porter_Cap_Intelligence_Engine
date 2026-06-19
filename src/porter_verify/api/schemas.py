"""Pydantic v2 request/response schemas for the API.

These are the validated boundary between the outside world and the services. Field
names are human-readable; labels avoid overclaiming (e.g. statuses use the plan's
explicit vocabulary, not "sales-ready").
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from porter_verify.db.enums import (
    RegistrationStatus,
    ReviewDecision,
    RunStatus,
    UccSearchOutcome,
    UccSearchStatus,
    VerificationStatus,
)


class VerifyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    state: str | None = Field(default=None, max_length=2)


class VerifyResponse(BaseModel):
    run_id: uuid.UUID
    run_status: RunStatus
    verification_status: VerificationStatus | None
    company_id: uuid.UUID | None
    match_confidence: float | None
    message: str


class CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    canonical_legal_name: str
    home_state: str | None
    status_normalized: RegistrationStatus
    verification_status: VerificationStatus | None = None
    match_confidence: float | None = None


class SearchResponse(BaseModel):
    results: list[CompanySummary]


class RecentBusinessOut(BaseModel):
    state: str
    entity_id: str
    legal_name: str
    entity_type: str | None
    registration_or_formation_date: date
    date_basis: str
    status_raw: str | None
    jurisdiction: str | None
    principal_address: str | None
    source_record_url: str
    domestic_signal: bool
    active_signal: bool
    nonprofit_signal: bool
    relevant_entity_signal: bool


class RecentBusinessFilters(BaseModel):
    states: list[str]
    formed_from: date
    formed_to: date


class RecentBusinessResponse(BaseModel):
    results: list[RecentBusinessOut]
    filters: RecentBusinessFilters


class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: str
    state_entity_id: str
    entity_type: str | None
    formation_date: date | None
    status_raw: str | None
    status_normalized: RegistrationStatus
    principal_address: str | None = None  # injected from raw evidence by the route
    mailing_address: str | None = None
    jurisdiction: str | None = None
    source_record_url: str | None = None


class RegisteredAgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_name: str | None
    agent_address: str | None


class OfficerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    title: str | None
    screened_ofac: bool | None


class ScoreComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component: str
    value: float
    weight: float
    explanation: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: RunStatus
    verification_status: VerificationStatus | None
    company_id: uuid.UUID | None
    match_confidence: float | None
    risk_score: float | None
    score_version: str | None
    started_at: datetime
    finished_at: datetime | None


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    sha256: str
    source_url: str | None
    captured_at: datetime


class UccSearchCreate(BaseModel):
    state: str = Field(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        return value.upper()


class UccSearchComplete(BaseModel):
    outcome: UccSearchOutcome
    source_url: str = Field(min_length=1, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("source_url")
    @classmethod
    def reject_blank_source(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("source_url cannot be blank")
        return value


class UccSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    state: str
    search_name: str
    status: UccSearchStatus
    outcome: UccSearchOutcome | None
    source_url: str | None
    notes: str | None
    requested_by_email: str
    completed_by_email: str | None
    created_at: datetime
    completed_at: datetime | None


class ProfileResponse(BaseModel):
    company: CompanySummary
    registrations: list[RegistrationOut]
    agents: list[RegisteredAgentOut]
    officers: list[OfficerOut]
    latest_run: RunOut | None
    scores: list[ScoreComponentOut]
    evidence: list[EvidenceOut]
    ucc_searches: list[UccSearchOut]


class RunDetailResponse(BaseModel):
    run: RunOut
    scores: list[ScoreComponentOut]
    evidence: list[EvidenceOut]


class ReviewRequest(BaseModel):
    decision: ReviewDecision
    reason: str | None = Field(default=None, max_length=2000)
    candidate_chosen: str | None = None


class ReviewResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    decision: ReviewDecision


class SourcePolicyUpdate(BaseModel):
    acquisition_method: Literal["official_api", "open_data", "vendor", "scraper", "manual"]
    legal_review_status: Literal["pending", "approved", "rejected", "expired"]
    allowed_purposes: list[str] = Field(max_length=20)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    freshness_sla_hours: int | None = Field(default=None, ge=1, le=8760)
    terms_url: str | None = Field(default=None, max_length=1000)
    owner: str | None = Field(default=None, max_length=320)


class SourcePolicyOut(SourcePolicyUpdate):
    model_config = ConfigDict(from_attributes=True)

    approved_by: str | None
    approved_at: datetime | None


class SourceHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    capabilities: list[str]
    states: list[str]
    cost_per_lookup: float
    health_status: str
    enabled: bool
    policy: SourcePolicyOut | None


class SourceQualityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_name: str
    metric_date: date
    request_count: int
    success_count: int
    record_count: int
    avg_latency_ms: int | None
    freshness_pass_rate: float | None
    estimated_cost: float
    schema_drift_detected: bool


class ErrorResponse(BaseModel):
    detail: str
