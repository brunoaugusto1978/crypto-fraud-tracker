import json
from pathlib import Path

from app.layers.address_enrichment import (
    FileAddressIntelligenceProvider,
    classification_from_matches,
)


TWITTER_2020_WALLET = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"


def test_file_provider_loads_external_wallet_intelligence(tmp_path):
    feed = {
        "source_name": "unit_test_feed",
        "items": [
            {
                "address": TWITTER_2020_WALLET,
                "asset": "BTC",
                "category": "scam",
                "label": "Twitter 2020 BTC scam wallet",
                "source_ref": "unit-test",
                "confidence": 0.85,
            }
        ],
    }

    path = tmp_path / "feed.json"
    path.write_text(json.dumps(feed), encoding="utf-8")

    provider = FileAddressIntelligenceProvider(str(path))
    matches = provider.lookup_address(TWITTER_2020_WALLET)

    assert len(matches) == 1
    assert matches[0]["category"] == "scam"
    assert matches[0]["source_name"] == "unit_test_feed"
    assert len(matches[0]["raw_sha256"]) == 64


def test_classification_from_external_match_becomes_high_risk_scam():
    matches = [
        {
            "address": TWITTER_2020_WALLET,
            "asset": "BTC",
            "category": "scam",
            "label": "Twitter 2020 BTC scam wallet",
            "source_name": "unit_test_feed",
            "confidence": 0.85,
            "raw_sha256": "a" * 64,
        }
    ]

    cls = classification_from_matches(TWITTER_2020_WALLET, matches)

    assert cls["category"] == "scam"
    assert cls["risk_level"] == "high"
    assert cls["intelligence_status"] == "matched"
    assert cls["confidence"] == 0.85
    assert cls["intelligence_matches"]


def test_classification_without_match_is_unknown_not_low():
    cls = classification_from_matches("bc1qunknown", [])

    assert cls["category"] == "unknown"
    assert cls["risk_level"] == "unknown"
    assert cls["intelligence_status"] == "no_external_label_found"


def test_blockstream_provider_uses_external_address_intel_file(monkeypatch):
    from app.layers.layer2_blockstream import BlockstreamIntelligence

    feed_path = Path(__file__).resolve().parents[1] / "data" / "address_intelligence.example.json"

    monkeypatch.setenv("ADDRESS_INTEL_FILE", str(feed_path))

    provider = BlockstreamIntelligence()
    cls = provider._classify(TWITTER_2020_WALLET, tx_count=0)

    assert cls["category"] == "scam"
    assert cls["risk_level"] == "high"
    assert cls["intelligence_status"] == "matched"
    assert cls["intelligence_matches"][0]["source_name"] == "example_external_watchlist"
