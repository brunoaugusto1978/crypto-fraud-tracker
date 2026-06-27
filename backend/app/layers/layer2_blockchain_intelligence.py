"""
CAMADA 2: BLOCKCHAIN INTELLIGENCE
Responsável por:
- Enriquecer dados de carteiras Bitcoin
- Classificar carteiras (exchange, mixer, ransomware, etc)
- Rastrear histórico de transações
- Integrar com APIs reais (Chainalysis, TRM, Elliptic)
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum
import random
import json
from app.layers.evidence import sha256_payload, utc_now_iso

# ============================================================================
# MOCKS DE DADOS
# ============================================================================

class MockBlockchainData:
    """Dados mockados para prototipagem"""
    
    # Carteiras conhecidas como MIXERS
    KNOWN_MIXERS = {
        '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa': {
            'name': 'Tornado Cash',
            'category': 'mixer',
            'risk_level': 'high',
        },
        '3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy': {
            'name': 'Mixing Service A',
            'category': 'mixer',
            'risk_level': 'high',
        }
    }
    
    # Carteiras conhecidas como EXCHANGES
    KNOWN_EXCHANGES = {
        '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2': {
            'name': 'Binance Cold Wallet',
            'category': 'exchange',
            'risk_level': 'low',
        },
        '3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy': {
            'name': 'Kraken Deposit',
            'category': 'exchange',
            'risk_level': 'low',
        }
    }
    
    # Carteiras conhecidas como RANSOMWARE
    KNOWN_RANSOMWARE = {
        'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4': {
            'exploits': ['LockBit 3.0', 'BlackCat'],
            'risk_level': 'critical',
        }
    }
    
    # Carteiras de SCAM
    KNOWN_SCAMS = {
        '17JsmEygzmhwjXkof4NSiVeNJEihardDiV': {
            'scam_type': 'Ponzi Scheme',
            'victims': 500,
            'total_btc': 25.5,
            'risk_level': 'critical',
        }
    }

# ============================================================================
# ADAPTER PATTERN - Suporta múltiplas APIs
# ============================================================================

class BlockchainIntelligenceAdapter:
    """Interface genérica para provedores de blockchain intelligence"""
    
    async def enrich_wallet(self, wallet_address: str) -> Dict:
        """Enriquece dados de uma carteira"""
        raise NotImplementedError
    
    async def get_wallet_history(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Retorna histórico de transações"""
        raise NotImplementedError
    
    async def classify_wallet(self, wallet_address: str) -> str:
        """Classifica carteira"""
        raise NotImplementedError

# ============================================================================
# IMPLEMENTAÇÃO: MOCK
# ============================================================================

class MockBlockchainIntelligence(BlockchainIntelligenceAdapter):
    """Mock de blockchain intelligence para prototipagem"""
    
    def __init__(self):
        self.data = MockBlockchainData()
    
    async def enrich_wallet(self, wallet_address: str) -> Dict:
        """
        Simula enriquecimento de carteira
        
        Returns:
            {
                "wallet": "...",
                "category": "mixer|exchange|ransomware|scam|unknown",
                "risk_level": "low|medium|high|critical",
                "confidence": 0.95,
                "source": "mock",
                "labeled_as": "Tornado Cash",
                "transactions_count": 1234,
                "first_seen": "2021-03-15T...",
                "last_seen": "2024-01-15T...",
                "total_volume_btc": 456.78
            }
        """
        
        # Simular latência
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        wallet_addr = wallet_address.strip()
        
        # Verificar se é mixer conhecida
        if wallet_addr in self.data.KNOWN_MIXERS:
            mixer = self.data.KNOWN_MIXERS[wallet_addr]
            return {
                "wallet": wallet_addr,
                "category": "mixer",
                "risk_level": "high",
                "confidence": 0.95,
                "source": "mock",
                "labeled_as": mixer['name'],
                "transactions_count": random.randint(500, 5000),
                "first_seen": (datetime.utcnow() - timedelta(days=1095)).isoformat() + 'Z',
                "last_seen": datetime.utcnow().isoformat() + 'Z',
                "total_volume_btc": round(random.uniform(100, 10000), 2)
            }
        
        # Verificar se é exchange conhecida
        if wallet_addr in self.data.KNOWN_EXCHANGES:
            exchange = self.data.KNOWN_EXCHANGES[wallet_addr]
            return {
                "wallet": wallet_addr,
                "category": "exchange",
                "risk_level": "low",
                "confidence": 0.98,
                "source": "mock",
                "labeled_as": exchange['name'],
                "transactions_count": random.randint(1000, 100000),
                "first_seen": (datetime.utcnow() - timedelta(days=2000)).isoformat() + 'Z',
                "last_seen": datetime.utcnow().isoformat() + 'Z',
                "total_volume_btc": round(random.uniform(50000, 500000), 2)
            }
        
        # Verificar se é ransomware conhecida
        if wallet_addr in self.data.KNOWN_RANSOMWARE:
            ransomware = self.data.KNOWN_RANSOMWARE[wallet_addr]
            return {
                "wallet": wallet_addr,
                "category": "ransomware",
                "risk_level": "critical",
                "confidence": 1.0,
                "source": "mock",
                "labeled_as": f"Ransomware: {', '.join(ransomware['exploits'])}",
                "transactions_count": random.randint(50, 500),
                "first_seen": (datetime.utcnow() - timedelta(days=365)).isoformat() + 'Z',
                "last_seen": datetime.utcnow().isoformat() + 'Z',
                "total_volume_btc": round(random.uniform(100, 5000), 2)
            }
        
        # Verificar se é scam conhecida
        if wallet_addr in self.data.KNOWN_SCAMS:
            scam = self.data.KNOWN_SCAMS[wallet_addr]
            return {
                "wallet": wallet_addr,
                "category": "scam",
                "risk_level": "critical",
                "confidence": 0.99,
                "source": "mock",
                "labeled_as": scam['scam_type'],
                "transactions_count": random.randint(100, 1000),
                "first_seen": (datetime.utcnow() - timedelta(days=730)).isoformat() + 'Z',
                "last_seen": datetime.utcnow().isoformat() + 'Z',
                "total_volume_btc": scam['total_btc']
            }
        
        # Carteira desconhecida - classificar aleatoriamente para demonstração
        categories = ["legitimate", "unknown", "gambling", "marketplace"]
        chosen_category = random.choice(categories)
        
        return {
            "wallet": wallet_addr,
            "category": chosen_category,
            "risk_level": "low" if chosen_category == "legitimate" else "medium",
            "confidence": round(random.uniform(0.5, 0.8), 2),
            "source": "mock",
            "labeled_as": None,
            "transactions_count": random.randint(1, 100),
            "first_seen": (datetime.utcnow() - timedelta(days=random.randint(30, 730))).isoformat() + 'Z',
            "last_seen": datetime.utcnow().isoformat() + 'Z',
            "total_volume_btc": round(random.uniform(0.1, 100), 2)
        }
    
    async def get_wallet_history(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Simula histórico de transações no formato UTXO compatível com evidência."""

        await asyncio.sleep(random.uniform(0.2, 0.8))

        transactions = []
        current_date = datetime.utcnow()

        for _ in range(min(limit, random.randint(5, 50))):
            tx_date = current_date - timedelta(days=random.randint(0, 365))
            txid = f"{''.join([hex(random.randint(0, 15))[2:] for _ in range(64)])}"
            to_address = f"bc1q{''.join([hex(random.randint(0, 15))[2:] for _ in range(38)])}"
            from_address = wallet_address if random.random() > 0.5 else f"bc1q{''.join([hex(random.randint(0, 15))[2:] for _ in range(38)])}"
            amount_btc = round(random.uniform(0.01, 10), 8)
            amount_sats = int(amount_btc * 100_000_000)
            raw_payload = {
                "txid": txid,
                "mock": True,
                "from_address": from_address,
                "to_address": to_address,
                "amount_sats": amount_sats,
            }

            transactions.append({
                "txid": txid,
                "from_address": from_address,
                "to_address": to_address,
                "amount_btc": amount_btc,
                "timestamp": tx_date.isoformat() + 'Z',
                "confirmed": True,
                "confirmations": random.randint(1, 100000),
                "fee_satoshi": random.randint(100, 10000),
                "inputs": [{"address": from_address, "value_sats": amount_sats, "value_btc": amount_btc}],
                "outputs": [{"index": 0, "address": to_address, "value_sats": amount_sats, "value_btc": amount_btc}],
                "transfers": [{"from_address": from_address, "to_address": to_address, "amount_btc": amount_btc, "amount_sats": amount_sats}],
                "source": "mock",
                "source_url": None,
                "raw_sha256": sha256_payload(raw_payload),
                "collected_at": utc_now_iso(),
            })

        return sorted(transactions, key=lambda x: x['timestamp'], reverse=True)
    
    async def classify_wallet(self, wallet_address: str) -> str:
        """Classifica carteira"""
        enrichment = await self.enrich_wallet(wallet_address)
        return enrichment['category']

# ============================================================================
# IMPLEMENTAÇÃO: CHAINALYSIS (FUTURO)
# ============================================================================

class ChainalysisIntelligence(BlockchainIntelligenceAdapter):
    """Integração com Chainalysis API (requer credenciais)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.chainalysis.com/v1"
    
    async def enrich_wallet(self, wallet_address: str) -> Dict:
        """Usa API real da Chainalysis"""
        
        headers = {
            "Token": self.api_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/entities/{wallet_address}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Chainalysis API error: {response.status_code}")
    
    async def get_wallet_history(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Retorna histórico usando Chainalysis"""
        # Implementação similar
        raise NotImplementedError
    
    async def classify_wallet(self, wallet_address: str) -> str:
        """Classifica usando Chainalysis"""
        raise NotImplementedError

# ============================================================================
# BLOCKCHAIN INTELLIGENCE SERVICE
# ============================================================================

class BlockchainIntelligenceService:
    """Serviço de enrichment de blockchain"""
    
    def __init__(self, provider: BlockchainIntelligenceAdapter):
        self.provider = provider
    
    async def enrich_wallet_with_caching(self, wallet_address: str, cache: Optional[Dict] = None) -> Dict:
        """Enriquece carteira com cache"""
        
        if cache and wallet_address in cache:
            return cache[wallet_address]
        
        enrichment = await self.provider.enrich_wallet(wallet_address)
        
        if cache is not None:
            cache[wallet_address] = enrichment
        
        return enrichment
    
    async def trace_transaction_chain(self, start_wallet: str, depth: int = 3) -> Dict:
        """
        Rastreia cadeia de transações até profundidade N.

        Retorna carteiras, transferências e transações brutas/projetadas preservando
        txid, UTXO inputs/outputs e hashes de evidência. Não fabrica valores.
        """

        visited = set()
        chain = []
        transactions = []
        raw_transactions = []
        queue = [(start_wallet, 0)]

        # Teto de wallets proporcional ao depth (evita explosao do grafo)
        max_wallets = min(50, 2 + 2 * (2 ** depth))
        # Quantos ramos seguir por wallet (fan-out controlado)
        branching = 3

        while queue and len(visited) < max_wallets:
            wallet, current_depth = queue.pop(0)

            if wallet in visited or current_depth >= depth:
                continue

            visited.add(wallet)

            enrichment = await self.provider.enrich_wallet(wallet)
            chain.append({
                "wallet": wallet,
                "depth": current_depth,
                "enrichment": enrichment
            })

            history = await self.provider.get_wallet_history(wallet, limit=branching)
            for tx in history[:branching]:
                raw_transactions.append(tx)
                transfers = tx.get("transfers") or [{
                    "from_address": tx.get("from_address"),
                    "to_address": tx.get("to_address"),
                    "amount_btc": tx.get("amount_btc", 0),
                    "amount_sats": int((tx.get("amount_btc", 0) or 0) * 100_000_000),
                }]

                for transfer in transfers[:branching]:
                    from_address = transfer.get("from_address")
                    to_address = transfer.get("to_address")
                    if not from_address or not to_address:
                        continue

                    transaction = {
                        "txid": tx.get("txid"),
                        "from_address": from_address,
                        "to_address": to_address,
                        "amount_btc": transfer.get("amount_btc", 0),
                        "amount_sats": transfer.get("amount_sats"),
                        "timestamp": tx.get("timestamp"),
                        "confirmed": tx.get("confirmed"),
                        "confirmations": tx.get("confirmations", 0),
                        "block_height": tx.get("block_height"),
                        "fee_satoshi": tx.get("fee_satoshi", 0),
                        "source": tx.get("source"),
                        "source_url": tx.get("source_url"),
                        "raw_sha256": tx.get("raw_sha256"),
                    }
                    transactions.append(transaction)

                    next_wallet = to_address
                    if next_wallet not in visited and len(visited) + len(queue) < max_wallets:
                        queue.append((next_wallet, current_depth + 1))

        return {
            "wallets": sorted(chain, key=lambda x: x['depth']),
            "transactions": transactions,
            "raw_transactions": raw_transactions,
        }

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

async def main():
    # Usar mock para prototipagem
    provider = MockBlockchainIntelligence()
    service = BlockchainIntelligenceService(provider)
    
    # Teste 1: Enriquecer carteira
    print("=== Test 1: Enrich Wallet ===")
    wallet_address = '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'
    enrichment = await service.provider.enrich_wallet(wallet_address)
    print(json.dumps(enrichment, indent=2))
    
    # Teste 2: Histórico
    print("\n=== Test 2: Wallet History ===")
    history = await service.provider.get_wallet_history(wallet_address, limit=5)
    print(f"Found {len(history)} transactions")
    
    # Teste 3: Rastreamento de cadeia
    print("\n=== Test 3: Trace Transaction Chain ===")
    trace = await service.trace_transaction_chain(wallet_address, depth=2)
    chain = trace["wallets"]
    print(f"Traced {len(chain)} wallets up to depth 2")
    for item in chain:
        print(f"  - {item['wallet'][:20]}... (depth: {item['depth']}) - {item['enrichment']['category']}")

if __name__ == "__main__":
    asyncio.run(main())
