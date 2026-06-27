"""Regression tests for AML hardening changes."""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.layers.evidence import build_evidence_record, sha256_payload
from app.layers.layer1_ioc_intake import IOCValidator
from app.layers.layer2_blockchain_intelligence import BlockchainIntelligenceAdapter, BlockchainIntelligenceService


class FakeProvider(BlockchainIntelligenceAdapter):
    async def enrich_wallet(self, wallet_address):
        return {"wallet": wallet_address, "category": "unknown", "risk_level": "low", "source": "fake"}

    async def get_wallet_history(self, wallet_address, limit=100):
        return [{
            "txid": "a" * 64,
            "timestamp": "2026-01-01T00:00:00Z",
            "confirmed": True,
            "confirmations": 10,
            "from_address": wallet_address,
            "to_address": "1BoatSLRHtKNngkdXEeobR76b53LETtpyT",
            "amount_btc": 0.12345678,
            "amount_sats": 12345678,
            "source": "fake",
            "raw_sha256": sha256_payload({"txid": "a" * 64}),
            "transfers": [{
                "from_address": wallet_address,
                "to_address": "1BoatSLRHtKNngkdXEeobR76b53LETtpyT",
                "amount_btc": 0.12345678,
                "amount_sats": 12345678,
            }],
        }]

    async def classify_wallet(self, wallet_address):
        return "unknown"


def test_wallet_normalization_preserves_base58_case():
    address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert IOCValidator.normalize_value(address, "wallet_address") == address


def test_evidence_record_is_deterministic_hash():
    payload = {"b": 2, "a": 1}
    ev1 = build_evidence_record(
        investigation_id="inv_1", evidence_type="test", source_name="unit",
        subject="subject", raw_payload=payload, collected_by="analyst"
    )
    ev2 = build_evidence_record(
        investigation_id="inv_1", evidence_type="test", source_name="unit",
        subject="subject", raw_payload={"a": 1, "b": 2}, collected_by="analyst"
    )
    assert ev1["raw_sha256"] == ev2["raw_sha256"]


def test_trace_uses_provider_transactions_without_synthetic_values():
    service = BlockchainIntelligenceService(FakeProvider())
    trace = asyncio.run(service.trace_transaction_chain("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", depth=1))
    assert trace["transactions"][0]["txid"] == "a" * 64
    assert trace["transactions"][0]["amount_btc"] == 0.12345678
