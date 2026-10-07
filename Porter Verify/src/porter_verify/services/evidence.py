"""Evidence service: immutable, hashed proof artifacts (WORM).

Artifacts are **content-addressed**: the storage path is derived from the SHA-256
of the bytes, so identical content always lands at the same path and is never
overwritten with different content. New verification runs add new evidence; nothing
is ever mutated. Each stored artifact also gets an ``evidence_items`` row linking it
to its run, with the hash for later integrity verification.

In dev the store is a local directory; in production it is an S3-compatible bucket
with object-lock (the ``storage_uri`` scheme abstracts the difference).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from porter_verify.db.enums import EvidenceType
from porter_verify.db.models import EvidenceItem

_EXTENSION = {
    EvidenceType.RAW_JSON: "json",
    EvidenceType.SCREENSHOT: "png",
    EvidenceType.PDF: "pdf",
}


def sha256_bytes(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``."""

    return hashlib.sha256(data).hexdigest()


def canonical_json_hash(obj: Any) -> str:
    """Stable SHA-256 of a JSON-serializable object (sorted keys, compact).

    Used for ``raw_source_events.raw_hash`` so the same response always hashes the
    same way regardless of key ordering.
    """

    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_bytes(encoded.encode("utf-8"))


class EvidenceStore:
    """Content-addressed artifact store rooted at a base directory."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def _path_for(self, digest: str, evidence_type: EvidenceType) -> Path:
        # Shard by the first two hex chars to avoid huge flat directories.
        ext = _EXTENSION[evidence_type]
        return self.base_dir / digest[:2] / f"{digest}.{ext}"

    def store(
        self,
        session: Session,
        *,
        verification_run_id: uuid.UUID,
        evidence_type: EvidenceType,
        content: bytes,
        source_url: str | None = None,
    ) -> EvidenceItem:
        """Write ``content`` to the store (idempotently) and record an EvidenceItem.

        Returns the created ``EvidenceItem`` (added to the session, not committed).
        """

        digest = sha256_bytes(content)
        path = self._path_for(digest, evidence_type)

        # WORM: if the path already exists it holds identical bytes (content-addressed),
        # so we never overwrite. Only write when absent.
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        item = EvidenceItem(
            verification_run_id=verification_run_id,
            type=evidence_type,
            storage_uri=path.resolve().as_uri(),
            sha256=digest,
            source_url=source_url,
        )
        session.add(item)
        return item

    def verify(self, item: EvidenceItem) -> bool:
        """Recompute the artifact's hash and confirm it matches the stored digest."""

        path = Path(self._path_for(item.sha256, item.type))
        if not path.exists():
            return False
        return sha256_bytes(path.read_bytes()) == item.sha256
