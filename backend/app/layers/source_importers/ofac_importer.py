"""
OFAC-derived local importer.

This importer converts a local OFAC-derived CSV/export into the normalized
ADDRESS_INTEL_FILE JSON format consumed by the wallet enrichment layer.

It intentionally works offline/local-first:
- no runtime web calls;
- source file remains auditable;
- output can be reviewed before being used by ADDRESS_INTEL_FILE.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.layers.evidence import sha256_payload, utc_now_iso


ADDRESS_KEYS = (
    "address",
    "wallet",
    "wallet_address",
    "btc_address",
    "digital_currency_address",
    "digitalCurrencyAddress",
    "crypto_address",
)

NAME_KEYS = (
    "name",
    "sdn_name",
    "entity_name",
    "label",
    "description",
)

REFERENCE_KEYS = (
    "source_ref",
    "reference",
    "url",
    "source_url",
    "sdn_id",
    "uid",
    "program",
)

ASSET_KEYS = (
    "asset",
    "chain",
    "network",
    "currency",
)


def _first(record: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return default


def normalize_ofac_record(
    record: Dict[str, Any],
    source_name: str = "ofac_derived",
    default_asset: str = "BTC",
) -> Optional[Dict[str, Any]]:
    address = str(_first(record, ADDRESS_KEYS, "")).strip()
    if not address:
        return None

    asset = str(_first(record, ASSET_KEYS, default_asset)).strip().upper() or default_asset
    label = _first(record, NAME_KEYS, "OFAC-listed digital currency address")
    source_ref = _first(record, REFERENCE_KEYS, "ofac-derived-local-export")

    raw_payload = dict(record)
    raw_payload.setdefault("source_name", source_name)

    return {
        "address": address,
        "asset": asset,
        "category": "sanctioned",
        "label": label,
        "source_ref": source_ref,
        "confidence": 1.0,
        "first_seen": record.get("first_seen") or record.get("date"),
        "last_seen": record.get("last_seen") or record.get("updated_at"),
        "source_name": source_name,
        "raw_sha256": sha256_payload(raw_payload),
        "imported_at": utc_now_iso(),
    }


def import_ofac_derived_csv(
    input_path: str,
    output_path: str,
    source_name: str = "ofac_derived",
) -> Dict[str, Any]:
    src = Path(input_path)
    dst = Path(output_path)

    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {src}")

    normalized: List[Dict[str, Any]] = []
    seen = set()

    with src.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            item = normalize_ofac_record(record, source_name=source_name)
            if not item:
                continue

            key = (
                item["address"],
                item["asset"],
                item["category"],
                item["source_name"],
            )

            if key in seen:
                continue

            seen.add(key)
            normalized.append(item)

    output = {
        "source_name": source_name,
        "description": f"Generated from OFAC-derived local export {src.name}",
        "generated_at": utc_now_iso(),
        "items": normalized,
    }

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return output
