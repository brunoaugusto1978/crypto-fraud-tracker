"""
BLOCKSTREAM INTELLIGENCE PROVIDER - dados reais via Esplora API.
Classificacao via lista local de IOCs + heuristica.
"""
import httpx
from datetime import datetime, timezone
from typing import Dict, List

SATOSHI = 100_000_000

KNOWN_ADDRESSES = {
    # "endereco": {"category": "ransomware", "label": "LockBit"},
}

CATEGORY_RISK_LEVEL = {
    "ransomware": "critical", "scam": "critical", "darknet": "high",
    "mixer": "high", "gambling": "medium", "marketplace": "medium",
    "exchange": "low", "legitimate": "low", "unknown": "low",
}


class BlockstreamIntelligence:
    def __init__(self, base_url="https://blockstream.info/api", known_addresses=None):
        self.base_url = base_url.rstrip("/")
        self.known = dict(KNOWN_ADDRESSES)
        if known_addresses:
            self.known.update(known_addresses)

    def _classify(self, address, tx_count=0):
        if address in self.known:
            entry = self.known[address]
            cat = entry.get("category", "unknown")
            return {"category": cat, "label": entry.get("label"),
                    "risk_level": CATEGORY_RISK_LEVEL.get(cat, "low")}
        if tx_count > 5000:
            return {"category": "exchange", "label": "alto volume (heuristica)", "risk_level": "low"}
        return {"category": "unknown", "label": None, "risk_level": "low"}

    async def enrich_wallet(self, wallet_address):
        url = f"{self.base_url}/address/{wallet_address}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
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
            "confidence": 1.0 if wallet_address in self.known else 0.5,
            "source": "blockstream", "labeled_as": cls["label"],
            "transactions_count": tx_count,
            "balance_btc": round(balance_btc, 8),
            "total_received_btc": round(funded / SATOSHI, 8),
            "total_sent_btc": round(spent / SATOSHI, 8),
        }

    async def get_wallet_history(self, wallet_address, limit=25):
        url = f"{self.base_url}/address/{wallet_address}/txs"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            txs = resp.json()
        history = []
        for tx in txs[:limit]:
            vouts = tx.get("vout", [])
            best_to, best_val = None, 0
            for v in vouts:
                addr = v.get("scriptpubkey_address")
                val = v.get("value", 0)
                if addr and addr != wallet_address and val > best_val:
                    best_to, best_val = addr, val
            vins = tx.get("vin", [])
            from_addr = wallet_address
            for vin in vins:
                a = vin.get("prevout", {}).get("scriptpubkey_address")
                if a:
                    from_addr = a
                    break
            status = tx.get("status", {})
            ts = status.get("block_time")
            timestamp = (datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                         if ts else datetime.utcnow().isoformat() + "Z")
            history.append({
                "txid": tx.get("txid"), "from_address": from_addr,
                "to_address": best_to or wallet_address,
                "amount_btc": round(best_val / SATOSHI, 8),
                "timestamp": timestamp,
                "confirmations": 1 if status.get("confirmed") else 0,
                "fee_satoshi": tx.get("fee", 0),
            })
        return history

    async def classify_wallet(self, wallet_address):
        enr = await self.enrich_wallet(wallet_address)
        return enr["category"]
