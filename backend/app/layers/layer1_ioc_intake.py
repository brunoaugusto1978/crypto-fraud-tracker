"""
CAMADA 1: IOC INTAKE
Responsável por:
- Receber indicadores de comprometimento (carteiras, TXIDs, etc)
- Validar formato
- Enfileirar para processamento
- Evitar duplicatas
"""

import re
import hashlib
from datetime import datetime
from typing import Optional, List
import redis
import json
from enum import Enum

# ============================================================================
# VALIDADORES
# ============================================================================

class IOCValidator:
    """Valida e normaliza IOCs"""
    
    # Padrões regex para diferentes tipos
    BITCOIN_ADDRESS_PATTERNS = {
        'P2PKH': r'^1[1-9A-HJ-NP-Z]{25,34}$',           # Começa com 1
        'P2SH': r'^3[1-9A-HJ-NP-Z]{25,34}$',            # Começa com 3
        'BECH32': r'^bc1[a-z0-9]{39,59}$',              # Começa com bc1
    }
    
    TXID_PATTERN = r'^[a-f0-9]{64}$'
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    IPV4_PATTERN = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    DOMAIN_PATTERN = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$'
    
    @staticmethod
    def validate_bitcoin_address(address: str) -> bool:
        """Valida endereço Bitcoin"""
        address = address.strip()
        
        for pattern_name, pattern in IOCValidator.BITCOIN_ADDRESS_PATTERNS.items():
            if re.match(pattern, address):
                return True
        
        return False
    
    @staticmethod
    def validate_txid(txid: str) -> bool:
        """Valida TXID (hash de transação)"""
        txid = txid.strip().lower()
        return bool(re.match(IOCValidator.TXID_PATTERN, txid))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Valida email"""
        return bool(re.match(IOCValidator.EMAIL_PATTERN, email.strip()))
    
    @staticmethod
    def validate_ipv4(ip: str) -> bool:
        """Valida IPv4"""
        return bool(re.match(IOCValidator.IPV4_PATTERN, ip.strip()))
    
    @staticmethod
    def validate_domain(domain: str) -> bool:
        """Valida nome de domínio"""
        return bool(re.match(IOCValidator.DOMAIN_PATTERN, domain.strip().lower()))
    
    @staticmethod
    def normalize_value(value: str, ioc_type: str) -> str:
        """Normaliza valor para comparação"""
        value = value.strip()
        
        if ioc_type == 'wallet_address':
            return value.lower()  # Bitcoin é case-insensitive
        elif ioc_type == 'transaction_id':
            return value.lower().strip()
        elif ioc_type == 'email':
            return value.lower().strip()
        elif ioc_type == 'domain':
            return value.lower().strip()
        elif ioc_type == 'ip_address':
            return value.strip()
        
        return value

    @staticmethod
    def classify_bitcoin_address(address: str) -> Optional[str]:
        """Classifica tipo de endereço Bitcoin"""
        address = address.strip()
        
        if re.match(IOCValidator.BITCOIN_ADDRESS_PATTERNS['P2PKH'], address):
            return 'P2PKH'
        elif re.match(IOCValidator.BITCOIN_ADDRESS_PATTERNS['P2SH'], address):
            return 'P2SH'
        elif re.match(IOCValidator.BITCOIN_ADDRESS_PATTERNS['BECH32'], address):
            return 'BECH32'
        
        return None

# ============================================================================
# IOC INTAKE SERVICE
# ============================================================================

class IOCIntakeService:
    """Serviço de intake de IOCs"""
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        """Inicializa conexão Redis"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.ioc_queue_key = 'crypto:ioc:queue'
        self.ioc_processed_key = 'crypto:ioc:processed'
        self.ioc_failed_key = 'crypto:ioc:failed'
    
    def submit_ioc(
        self,
        value: str,
        ioc_type: str,
        source: str = 'api',
        confidence: float = 0.8,
        notes: Optional[str] = None
    ) -> dict:
        """
        Submete um IOC para processamento
        
        Returns:
            {
                "ioc_id": "...",
                "status": "queued",
                "message": "...",
                "created_at": "2024-01-15T10:30:00Z"
            }
        """
        
        # Normalizar e validar
        normalized_value = IOCValidator.normalize_value(value, ioc_type)
        
        if not self._validate_ioc(normalized_value, ioc_type):
            return {
                "ioc_id": None,
                "status": "rejected",
                "message": f"Formato inválido para {ioc_type}: {value}",
                "created_at": datetime.utcnow().isoformat() + 'Z'
            }
        
        # Gerar ID único
        ioc_id = self._generate_ioc_id(normalized_value)
        
        # Verificar duplicata
        if self.redis_client.exists(f"{self.ioc_processed_key}:{ioc_id}"):
            return {
                "ioc_id": ioc_id,
                "status": "already_processed",
                "message": f"IOC já foi processado",
                "created_at": datetime.utcnow().isoformat() + 'Z'
            }
        
        # Criar registro
        ioc_record = {
            "ioc_id": ioc_id,
            "value": normalized_value,
            "type": ioc_type,
            "source": source,
            "confidence": confidence,
            "notes": notes,
            "created_at": datetime.utcnow().isoformat() + 'Z',
            "status": "pending"
        }
        
        # Enfileirar
        self.redis_client.rpush(self.ioc_queue_key, json.dumps(ioc_record))
        
        return {
            "ioc_id": ioc_id,
            "status": "queued",
            "message": f"IOC enfileirado para processamento",
            "created_at": ioc_record["created_at"]
        }
    
    def _validate_ioc(self, value: str, ioc_type: str) -> bool:
        """Valida IOC baseado em tipo"""
        
        if ioc_type == 'wallet_address':
            return IOCValidator.validate_bitcoin_address(value)
        elif ioc_type == 'transaction_id':
            return IOCValidator.validate_txid(value)
        elif ioc_type == 'email':
            return IOCValidator.validate_email(value)
        elif ioc_type == 'ip_address':
            return IOCValidator.validate_ipv4(value)
        elif ioc_type == 'domain':
            return IOCValidator.validate_domain(value)
        
        return False
    
    @staticmethod
    def _generate_ioc_id(value: str) -> str:
        """Gera ID único para IOC"""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
    
    def get_queue_status(self) -> dict:
        """Retorna status da fila"""
        pending_count = self.redis_client.llen(self.ioc_queue_key)
        processed_count = self.redis_client.dbsize()  # Approximation
        
        return {
            "pending": pending_count,
            "processed": processed_count,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    
    def get_next_ioc(self) -> Optional[dict]:
        """Retorna próximo IOC da fila (não-bloqueante)"""
        ioc_json = self.redis_client.lpop(self.ioc_queue_key)
        
        if ioc_json:
            return json.loads(ioc_json)
        
        return None
    
    def mark_as_processed(self, ioc_id: str, metadata: dict):
        """Marca IOC como processado"""
        self.redis_client.setex(
            f"{self.ioc_processed_key}:{ioc_id}",
            86400 * 30,  # Expira em 30 dias
            json.dumps(metadata)
        )
    
    def mark_as_failed(self, ioc_id: str, error: str):
        """Marca IOC como falho"""
        self.redis_client.rpush(
            self.ioc_failed_key,
            json.dumps({
                "ioc_id": ioc_id,
                "error": error,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            })
        )
    
    def batch_submit(self, iocs: List[dict]) -> List[dict]:
        """Submete múltiplos IOCs em lote"""
        results = []
        
        for ioc in iocs:
            result = self.submit_ioc(
                value=ioc.get('value'),
                ioc_type=ioc.get('type'),
                source=ioc.get('source', 'batch_api'),
                confidence=ioc.get('confidence', 0.8),
                notes=ioc.get('notes')
            )
            results.append(result)
        
        return results

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    
    service = IOCIntakeService()
    
    # Teste 1: Submeter endereço Bitcoin válido
    result = service.submit_ioc(
        value='1A1z7agoat4qNB5agoat4qNB5agoat4qNB',
        ioc_type='wallet_address',
        source='manual',
        confidence=0.95
    )
    print(f"Test 1 - Bitcoin Address: {result}")
    
    # Teste 2: Submeter TXID válido
    result = service.submit_ioc(
        value='e4d5a6f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b',
        ioc_type='transaction_id',
        source='api'
    )
    print(f"Test 2 - TXID: {result}")
    
    # Teste 3: IOC inválido
    result = service.submit_ioc(
        value='invalid_address_12345',
        ioc_type='wallet_address'
    )
    print(f"Test 3 - Invalid: {result}")
    
    # Teste 4: Status da fila
    status = service.get_queue_status()
    print(f"Queue Status: {status}")
    
    # Teste 5: Batch submit
    iocs = [
        {'value': '1A1z7agoat4qNB5agoat4qNB5agoat4qNB', 'type': 'wallet_address'},
        {'value': 'test@example.com', 'type': 'email'},
    ]
    results = service.batch_submit(iocs)
    print(f"Batch Results: {results}")
