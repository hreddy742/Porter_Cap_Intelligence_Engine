"""ORM models for Porter Verify.

Importing this package registers every model on ``Base.metadata`` so that
``create_all`` (tests) and Alembic autogenerate see the full schema.
"""

from porter_verify.db.models.audit import AuditLog, ErrorLog, GeneratedReport
from porter_verify.db.models.company import Company, CompanyIdentifier
from porter_verify.db.models.registration import (
    BusinessRegistration,
    CompanyOfficer,
    RegisteredAgent,
)
from porter_verify.db.models.review import ReviewDecisionRecord
from porter_verify.db.models.salesforce import SalesforceSyncStatus
from porter_verify.db.models.source import (
    SourceCredential,
    SourcePolicy,
    SourceQualityDaily,
    SourceRegistry,
)
from porter_verify.db.models.staging import (
    CoBusinessEntity,
    CtBusinessEntity,
    OhBusinessEntity,
    OrBusinessEntity,
)
from porter_verify.db.models.user import Role, User
from porter_verify.db.models.verification import (
    ConfidenceScore,
    EvidenceItem,
    RawSourceEvent,
    VerificationRun,
)

__all__ = [
    "AuditLog",
    "BusinessRegistration",
    "CoBusinessEntity",
    "CtBusinessEntity",
    "OrBusinessEntity",
    "OhBusinessEntity",
    "Company",
    "CompanyIdentifier",
    "CompanyOfficer",
    "ConfidenceScore",
    "ErrorLog",
    "EvidenceItem",
    "GeneratedReport",
    "RawSourceEvent",
    "RegisteredAgent",
    "ReviewDecisionRecord",
    "Role",
    "SalesforceSyncStatus",
    "SourceCredential",
    "SourcePolicy",
    "SourceQualityDaily",
    "SourceRegistry",
    "User",
    "VerificationRun",
]
