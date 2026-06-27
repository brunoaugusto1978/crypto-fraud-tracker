"""
BLOCKSTREAM INTELLIGENCE PROVIDER - dados reais via Esplora API.
Classificacao via lista local de IOCs + heuristica.
"""
import httpx
from datetime import datetime, timezone
from typing import Dict, List
from app.layers.evidence import sha256_payload, utc_now_iso
from app.layers.address_enrichment import FileAddressIntelligenceProvider, classification_from_matches

SATOSHI = 100_000_000

KNOWN_ADDRESSES = {
    # ====================================================================
    # IOCs reais de threat intelligence. Fontes publicas confiaveis.
    # Expanda esta lista com indicadores de relatorios OSINT/MISP/OFAC.
    # ====================================================================

    # WannaCry ransomware (2017)
    # Fontes: Sophos, NJCCIC, Secureworks CTU, MyCERT
    "13AM4VW2dhxYgXeQepoHkHSQuy6NgaEb94": {"category": "ransomware", "label": "WannaCry"},
    "12t9YDPgwueZ9NyMgw519p7AA8isjr6SMw": {"category": "ransomware", "label": "WannaCry"},
    "115p7UMMngoj1pMvkpHijcRdfJNXj6LrLn": {"category": "ransomware", "label": "WannaCry"},

    # SamSam ransomware (facilitadores de lavagem - wallets sancionadas pela OFAC, 2018)
    # Fontes: US Treasury/OFAC SDN List, FDD, WilmerHale, Akin Gump
    "149w62rY42aZBox8fGcmqNsXUzSStKeq8C": {"category": "ransomware", "label": "SamSam (OFAC SDN)"},
    "1AjZPMsnmpdK2Rv9KQNfMurTXinscVro9V": {"category": "ransomware", "label": "SamSam (OFAC SDN)"},
}

CATEGORY_RISK_LEVEL = {
    "ransomware": "critical", "scam": "critical", "darknet": "high",
    "mixer": "high", "gambling": "medium", "marketplace": "medium",
    "exchange": "low", "legitimate": "low", "unknown": "low",
}


def _safe_btc(value_sats: int) -> float:
    return round((value_sats or 0) / SATOSHI, 8)


class BlockstreamIntelligence:
    def __init__(self, base_url="https://blockstream.info/api", known_addresses=None, cache_ttl=300):
        self.base_url = base_url.rstrip("/")
        self.known = dict(KNOWN_ADDRESSES)
        if known_addresses:
            self.known.update(known_addresses)
        self._cache = {}          # {url: (timestamp, data)}
        self._cache_ttl = cache_ttl
        self.address_intel_provider = FileAddressIntelligenceProvider()

    def _cache_get(self, url):
        import time
        entry = self._cache.get(url)
        if entry and (time.time() - entry[0]) < self._cache_ttl:
            return entry[1]
        return None

    def _cache_set(self, url, data):
        import time
        self._cache[url] = (time.time(), data)

    def _classify(self, address, tx_count=0):
        # Provider-backed intelligence comes first. This avoids relying only on
        # hardcoded Python indicators and allows external feeds to drive risk.
        external_matches = self.address_intel_provider.lookup_address(address, asset="BTC")
        if external_matches:
            return classification_from_matches(address, external_matches)

        # Legacy local indicators remain as a fallback, but are explicitly
        # marked as local_static_ioc so the source is transparent.
        if address in self.known:
            entry = self.known[address]
            cat = entry.get("category", "unknown")
            return {
                "category": cat,
                "label": entry.get("label"),
                "risk_level": CATEGORY_RISK_LEVEL.get(cat, "low"),
                "risk_score_hint": 90 if cat == "ransomware" else 75,
                "confidence": 0.95,
                "intelligence_status": "matched",
                "intelligence_matches": [{
                    "address": address,
                    "asset": "BTC",
                    "category": cat,
                    "label": entry.get("label"),
                    "source_name": "local_static_ioc",
                    "source_ref": "legacy_known_addresses",
                    "confidence": 0.95,
                    "raw_payload": entry,
                }],
            }

        # Behavioral heuristic: high-volume addresses may be services/exchanges.
        if tx_count > 5000:
            return {
                "category": "exchange",
                "label": "alto volume (heuristica)",
                "risk_level": "low",
                "risk_score_hint": 10,
                "confidence": 0.4,
                "intelligence_status": "behavioral_heuristic_only",
                "intelligence_matches": [],
            }

        # Important: lack of intelligence is not evidence of low risk.
        return {
            "category": "unknown",
            "label": None,
            "risk_level": "unknown",
            "risk_score_hint": 0,
            "confidence": 0.0,
            "intelligence_status": "no_external_label_found",
            "intelligence_matches": [],
        }

    async def _get_json(self, url: str):
        data = self._cache_get(url)
        if data is not None:
            return data
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        self._cache_set(url, data)
        return data

    async def enrich_wallet(self, wallet_address):
        url = f"{self.base_url}/address/{wallet_address}"
        data = await self._get_json(url)
        chain = data.get("chain_stats", {})
        mempool = data.get("mempool_stats", {})
        funded = chain.get("funded_txo_sum", 0)
        spent = chain.get("spent_txo_sum", 0)
        tx_count = chain.get("tx_count", 0) + mempool.get("tx_count", 0)
        balance_btc = (funded - spent) / SATOSHI
        cls = self._classify(wallet_address, tx_count)
        return {
            "wallet": wallet_address, "category": cls["category"],
            "risk_level": cls["risk_level"],
            "confidence": cls.get("confidence", 0.0),
            "source": "blockstream", "source_url": url,
            "raw_sha256": sha256_payload(data),
            "labeled_as": cls.get("label"),
            "intelligence_status": cls.get("intelligence_status"),
            "intelligence_matches": cls.get("intelligence_matches", []),
            "risk_score_hint": cls.get("risk_score_hint", 0),
            "transactions_count": tx_count,
            "balance_btc": round(balance_btc, 8),
            "total_received_btc": round(funded / SATOSHI, 8),
            "total_sent_btc": round(spent / SATOSHI, 8),
            "collected_at": utc_now_iso(),
        }

    async def get_wallet_history(self, wallet_address, limit=25):
        """
        Retorna transações on-chain preservando o modelo UTXO.

        Compatibilidade: cada item tambem expoe from_address/to_address/amount_btc,
        mas a evidencia correta está em inputs, outputs e transfers.
        """
        url = f"{self.base_url}/address/{wallet_address}/txs"
        txs = await self._get_json(url)
        history = []

        for tx in txs[:limit]:
            status = tx.get("status", {})
            ts = status.get("block_time")
            timestamp = (datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                         if ts else utc_now_iso())

            inputs = []
            input_addresses = set()
            wallet_is_input = False
            for vin in tx.get("vin", []):
                prevout = vin.get("prevout") or {}
                addr = prevout.get("scriptpubkey_address")
                value_sats = prevout.get("value", 0) or 0
                if addr:
                    input_addresses.add(addr)
                if addr == wallet_address:
                    wallet_is_input = True
                inputs.append({
                    "address": addr,
                    "value_sats": value_sats,
                    "value_btc": _safe_btc(value_sats),
                    "txid": vin.get("txid"),
                    "vout": vin.get("vout"),
                })

            outputs = []
            for idx, vout in enumerate(tx.get("vout", [])):
                value_sats = vout.get("value", 0) or 0
                outputs.append({
                    "index": idx,
                    "address": vout.get("scriptpubkey_address"),
                    "value_sats": value_sats,
                    "value_btc": _safe_btc(value_sats),
                    "scriptpubkey_type": vout.get("scriptpubkey_type"),
                })

            # Transfers are analytical projections from a UTXO transaction.
            # When the investigated wallet spends, follow outputs not returning to the same wallet.
            # When it receives, model senders as the input addresses and destination as the wallet.
            transfers = []
            if wallet_is_input:
                for out in outputs:
                    to_addr = out.get("address")
                    if to_addr and to_addr != wallet_address:
                        transfers.append({
                            "from_address": wallet_address,
                            "to_address": to_addr,
                            "amount_btc": out["value_btc"],
                            "amount_sats": out["value_sats"],
                        })
            else:
                for out in outputs:
                    if out.get("address") == wallet_address:
                        for src in sorted(a for a in input_addresses if a):
                            transfers.append({
                                "from_address": src,
                                "to_address": wallet_address,
                                "amount_btc": out["value_btc"],
                                "amount_sats": out["value_sats"],
                            })

            # Compatibility projection for existing report/graph code.
            top_transfer = max(transfers, key=lambda t: t.get("amount_sats", 0), default=None)
            raw_sha256 = sha256_payload(tx)
            history.append({
                "txid": tx.get("txid"),
                "from_address": (top_transfer or {}).get("from_address", wallet_address),
                "to_address": (top_transfer or {}).get("to_address", wallet_address),
                "amount_btc": (top_transfer or {}).get("amount_btc", 0),
                "timestamp": timestamp,
                "confirmed": status.get("confirmed", False),
                "confirmations": 1 if status.get("confirmed") else 0,
                "block_height": status.get("block_height"),
                "fee_satoshi": tx.get("fee", 0),
                "inputs": inputs,
                "outputs": outputs,
                "transfers": transfers,
                "source": "blockstream",
                "source_url": url,
                "raw_sha256": raw_sha256,
                "raw_payload": tx,
            })
        return history

    async def classify_wallet(self, wallet_address):
        enr = await self.enrich_wallet(wallet_address)
        return enr["category"]
