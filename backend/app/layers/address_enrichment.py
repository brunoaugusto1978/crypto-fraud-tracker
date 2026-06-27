"""
Address enrichment layer.

This module resolves wallet intelligence from provider-backed sources instead
of relying only on hardcoded Python indicators.

Initial provider:
- JSON feed provider, suitable for curated internal feeds, exported MISP data,
  OFAC-derived datasets, abuse-report datasets or test fixtures.

Future providers:
- OFAC sanctions import
- MISP
- BitcoinAbuse / Chainabuse
- Commercial providers such as Chainalysis, TRM or Elliptic
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.layers.evidence import sha256_payload, utc_now_iso


CATEGORY_RISK_LEVEL = {
    "sanctioned": "critical",
    "ransomware": "critical",
    "scam": "high",
    "fraud": "high",
    "darknet": "high",
    "mixer": "high",
    "gambling": "medium",
    "marketplace": "medium",
    "exchange": "low",
    "legitimate": "low",
    "unknown": "unknown",
}


CATEGORY_BASE_SCORE = {
    "sanctioned": 100,
    "ransomware": 90,
    "scam": 75,
    "fraud": 75,
    "darknet": 80,
    "mixer": 70,
    "gambling": 35,
    "marketplace": 35,
    "exchange": 10,
    "legitimate": 0,
    "unknown": 0,
}


class FileAddressIntelligenceProvider:
    """
    Loads address intelligence from a JSON file.

    Expected format:
    {
      "source_name": "internal_watchlist",
      "items": [
        {
          "address": "bc1...",
          "asset": "BTC",
          "category": "scam",
          "label": "Example scam wallet",
          "source_ref": "case-or-url",
          "confidence": 0.85
        }
      ]
    }
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.getenv("ADDRESS_INTEL_FILE")
        self.source_name = "file_address_intelligence"
        self._items: List[Dict[str, Any]] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return

        self._loaded = True

        if not self.path:
            return

        path = Path(self.path)
        if not path.exists():
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        self.source_name = data.get("source_name") or self.source_name

        items = data.get("items", [])
        if not isinstance(items, list):
            items = []

        normalized = []
        for item in items:
            if not isinstance(item, dict):
                continue

            address = str(item.get("address", "")).strip()
            if not address:
                continue

            asset = str(item.get("asset", "BTC")).upper().strip() or "BTC"
            category = str(item.get("category", "unknown")).lower().strip() or "unknown"

            raw_payload = dict(item)
            raw_payload.setdefault("source_name", item.get("source_name") or self.source_name)

            normalized.append({
                "address": address,
                "asset": asset,
                "category": category,
                "label": item.get("label"),
                "source_name": item.get("source_name") or self.source_name,
                "source_ref": item.get("source_ref"),
                "confidence": float(item.get("confidence", 0.5)),
                "first_seen": item.get("first_seen"),
                "last_seen": item.get("last_seen"),
                "raw_payload": raw_payload,
                "raw_sha256": sha256_payload(raw_payload),
                "collected_at": utc_now_iso(),
            })

        self._items = normalized

    def lookup_address(self, address: str, asset: str = "BTC") -> List[Dict[str, Any]]:
        self._load()

        asset = asset.upper()
        return [
            item for item in self._items
            if item.get("address") == address and item.get("asset", "BTC").upper() == asset
        ]


def classification_from_matches(address: str, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts provider matches into the enrichment shape consumed by the app.
    Picks the highest base score first, then confidence.
    """

    if not matches:
        return {
            "wallet": address,
            "category": "unknown",
            "label": None,
            "risk_level": "unknown",
            "risk_score_hint": 0,
            "confidence": 0.0,
            "intelligence_status": "no_external_label_found",
            "intelligence_matches": [],
        }

    def rank(match: Dict[str, Any]):
        category = str(match.get("category", "unknown")).lower()
        return (
            CATEGORY_BASE_SCORE.get(category, 0),
            float(match.get("confidence", 0.0)),
        )

    best = sorted(matches, key=rank, reverse=True)[0]
    category = str(best.get("category", "unknown")).lower()

    return {
        "wallet": address,
        "category": category,
        "label": best.get("label"),
        "risk_level": CATEGORY_RISK_LEVEL.get(category, "unknown"),
        "risk_score_hint": CATEGORY_BASE_SCORE.get(category, 0),
        "confidence": float(best.get("confidence", 0.5)),
        "intelligence_status": "matched",
        "intelligence_matches": matches,
    }
