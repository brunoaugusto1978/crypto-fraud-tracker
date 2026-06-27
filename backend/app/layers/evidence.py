"""
Utilities for evidence preservation and chain-of-custody metadata.
"""
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_evidence_record(
    *,
    investigation_id: str,
    evidence_type: str,
    source_name: str,
    subject: str,
    raw_payload: Any,
    collected_by: str,
    source_url: Optional[str] = None,
    algorithm_version: str = "aml-score-v1",
) -> Dict:
    """Builds a canonical evidence record that can be persisted and audited."""
    return {
        "investigation_id": investigation_id,
        "evidence_type": evidence_type,
        "source_name": source_name,
        "source_url": source_url,
        "subject": subject,
        "raw_payload": raw_payload,
        "raw_sha256": sha256_payload(raw_payload),
        "collected_by": collected_by,
        "collected_at": utc_now_iso(),
        "algorithm_version": algorithm_version,
    }
