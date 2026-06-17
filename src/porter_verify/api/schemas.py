"""Pydantic v2 request/response schemas for the API.

These are the validated boundary between the outside world and the services. Field
names are human-readable; labels avoid overclaiming (e.g. statuses use the plan's
explicit vocabulary, not "sales-ready").
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from porter_verify.db.enums import (
    RegistrationStatus,
    ReviewDecision,
    RunStatus,
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


class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: str
    state_entity_id: str
    entity_type: str | None
    status_raw: str | None
    status_normalized: RegistrationStatus


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


class ProfileResponse(BaseModel):
    company: CompanySummary
    registrations: list[RegistrationOut]
    officers: list[OfficerOut]
    latest_run: RunOut | None
    scores: list[ScoreComponentOut]
    evidence: list[EvidenceOut]


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


class SourceHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    capabilities: list[str]
    states: list[str]
    health_status: str
    enabled: bool


class ErrorResponse(BaseModel):
    detail: str
