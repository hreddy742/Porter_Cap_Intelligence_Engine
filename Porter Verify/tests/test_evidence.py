"""Tests for the evidence service (hashing + content-addressed WORM storage)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from porter_verify.db.enums import EvidenceType, RunStatus
from porter_verify.db.models import VerificationRun
from porter_verify.services.evidence import (
    EvidenceStore,
    canonical_json_hash,
    sha256_bytes,
)


def _make_run(session: Session) -> VerificationRun:
    run = VerificationRun(status=RunStatus.RUNNING)
    session.add(run)
    session.commit()
    return run


def test_canonical_json_hash_is_order_independent() -> None:
    assert canonical_json_hash({"a": 1, "b": 2}) == canonical_json_hash({"b": 2, "a": 1})


def test_sha256_bytes_matches_known_value() -> None:
    # SHA-256 of an empty input is a well-known constant.
    assert sha256_bytes(b"") == ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


def test_store_creates_artifact_and_record(tmp_path: Path, db_session: Session) -> None:
    run = _make_run(db_session)
    store = EvidenceStore(tmp_path)
    content = b'{"status": "active"}'

    item = store.store(
        db_session,
        verification_run_id=run.id,
        evidence_type=EvidenceType.RAW_JSON,
        content=content,
        source_url="https://sos.example.gov/record/123",
    )
    db_session.commit()

    assert item.sha256 == sha256_bytes(content)
    assert item.source_url == "https://sos.example.gov/record/123"
    assert store.verify(item) is True


def test_store_is_idempotent_for_identical_content(tmp_path: Path, db_session: Session) -> None:
    run = _make_run(db_session)
    store = EvidenceStore(tmp_path)
    content = b"same-bytes"

    first = store.store(
        db_session, verification_run_id=run.id, evidence_type=EvidenceType.RAW_JSON, content=content
    )
    second = store.store(
        db_session, verification_run_id=run.id, evidence_type=EvidenceType.RAW_JSON, content=content
    )
    db_session.commit()

    # Same content => same hash => same storage path (WORM, no overwrite).
    assert first.storage_uri == second.storage_uri


def test_verify_detects_tampering(tmp_path: Path, db_session: Session) -> None:
    run = _make_run(db_session)
    store = EvidenceStore(tmp_path)
    item = store.store(
        db_session,
        verification_run_id=run.id,
        evidence_type=EvidenceType.RAW_JSON,
        content=b"original",
    )
    db_session.commit()

    # Tamper with the stored file on disk.
    stored = Path(store._path_for(item.sha256, item.type))
    stored.write_bytes(b"tampered")

    assert store.verify(item) is False
