"""
Intelligence feed importer.

Converts CSV/JSON wallet intelligence feeds into the ADDRESS_INTEL_FILE format
consumed by address_enrichment.FileAddressIntelligenceProvider.

Supported input fields / aliases:
- address, wallet, wallet_address, btc_address
- asset
- category, type, tag
- label, name, description
- source_ref, reference, url, source_url
- confidence
- first_seen
- last_seen
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.layers.evidence import sha256_payload, utc_now_iso


ADDRESS_KEYS = ("address", "wallet", "wallet_address", "btc_address")
CATEGORY_KEYS = ("category", "type", "tag")
LABEL_KEYS = ("label", "name", "description")
SOURCE_REF_KEYS = ("source_ref", "reference", "url", "source_url")
ASSET_KEYS = ("asset", "chain", "network")
CONFIDENCE_KEYS = ("confidence", "score")
FIRST_SEEN_KEYS = ("first_seen", "first_seen_at", "date", "created_at")
LAST_SEEN_KEYS = ("last_seen", "last_seen_at", "updated_at")


VALID_CATEGORIES = {
    "sanctioned",
    "ransomware",
    "scam",
    "fraud",
    "darknet",
    "mixer",
    "gambling",
    "marketplace",
    "exchange",
    "legitimate",
    "unknown",
}


def _first(record: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return default


def _normalize_category(value: Any) -> str:
    category = str(value or "unknown").strip().lower().replace(" ", "_")
    return category if category in VALID_CATEGORIES else "unknown"


def _normalize_confidence(value: Any, default: float = 0.5) -> float:
    if value in (None, ""):
        return default

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default

    if confidence > 1:
        confidence = confidence / 100.0

    return max(0.0, min(1.0, confidence))


def normalize_record(record: Dict[str, Any], source_name: str, default_asset: str = "BTC") -> Optional[Dict[str, Any]]:
    address = str(_first(record, ADDRESS_KEYS, "")).strip()
    if not address:
        return None

    asset = str(_first(record, ASSET_KEYS, default_asset)).strip().upper() or default_asset
    category = _normalize_category(_first(record, CATEGORY_KEYS, "unknown"))
    label = _first(record, LABEL_KEYS)
    source_ref = _first(record, SOURCE_REF_KEYS)
    confidence = _normalize_confidence(_first(record, CONFIDENCE_KEYS, 0.5))

    raw_payload = dict(record)
    raw_payload.setdefault("source_name", source_name)

    return {
        "address": address,
        "asset": asset,
        "category": category,
        "label": label,
        "source_ref": source_ref,
        "confidence": confidence,
        "first_seen": _first(record, FIRST_SEEN_KEYS),
        "last_seen": _first(record, LAST_SEEN_KEYS),
        "source_name": source_name,
        "raw_sha256": sha256_payload(raw_payload),
        "imported_at": utc_now_iso(),
    }


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        items = []

    return [item for item in items if isinstance(item, dict)]


def load_records(path: Path, input_format: str) -> List[Dict[str, Any]]:
    fmt = input_format.lower().strip()

    if fmt == "csv":
        return load_csv(path)

    if fmt == "json":
        return load_json(path)

    raise ValueError(f"Unsupported format: {input_format}")


def import_feed(input_path: str, input_format: str, source_name: str, output_path: str) -> Dict[str, Any]:
    src = Path(input_path)
    dst = Path(output_path)

    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {src}")

    records = load_records(src, input_format)

    normalized = []
    seen = set()

    for record in records:
        item = normalize_record(record, source_name=source_name)
        if not item:
            continue

        key = (
            item["address"],
            item["asset"],
            item["category"],
            item.get("source_name"),
        )

        if key in seen:
            continue

        seen.add(key)
        normalized.append(item)

    output = {
        "source_name": source_name,
        "description": f"Generated from {src.name}",
        "generated_at": utc_now_iso(),
        "items": normalized,
    }

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return output


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import wallet intelligence feeds into ADDRESS_INTEL_FILE JSON format.")
    parser.add_argument("--input", required=True, help="Input CSV/JSON file")
    parser.add_argument("--format", required=True, choices=["csv", "json"], help="Input format")
    parser.add_argument("--source-name", required=True, help="Source name to attach to imported records")
    parser.add_argument("--output", required=True, help="Output JSON path")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    output = import_feed(
        input_path=args.input,
        input_format=args.format,
        source_name=args.source_name,
        output_path=args.output,
    )

    print(f"Imported {len(output['items'])} intelligence records into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
