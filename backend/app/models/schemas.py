from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re

# ============================================================================
# ENUMS
# ============================================================================

class WalletCategory(str, Enum):
    """Categorização de carteiras"""
    UNKNOWN = "unknown"
    EXCHANGE = "exchange"
    MIXER = "mixer"
    RANSOMWARE = "ransomware"
    SCAM = "scam"
    DARKNET = "darknet"
    GAMBLING = "gambling"
    MARKETPLACE = "marketplace"
    LEGITIMATE = "legitimate"

class RiskLevel(str, Enum):
    """Nível de risco"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IOCType(str, Enum):
    """Tipo de Indicador de Comprometimento"""
    WALLET_ADDRESS = "wallet_address"
    TRANSACTION_ID = "transaction_id"
    IP_ADDRESS = "ip_address"
    EMAIL = "email"
    DOMAIN = "domain"

# ============================================================================
# MODELS - CAMADA 1: IOC INTAKE
# ============================================================================

class IOCInput(BaseModel):
    """Input de IOC (Indicador de Comprometimento)"""
    value: str = Field(..., description="Endereço Bitcoin, TXID, IP, email, etc")
    ioc_type: IOCType = Field(..., description="Tipo de indicador")
    source: str = Field("manual", description="Origem do IOC")
    confidence: float = Field(0.8, ge=0, le=1, description="Confiança (0-1)")
    notes: Optional[str] = None
    
    @validator('value')
    def validate_value(cls, v):
        """Validação básica de formato"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Valor não pode estar vazio")
        return v.strip()

class IOCRecord(IOCInput):
    """IOC com metadata de processamento"""
    id: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    status: str = "pending"  # pending, processing, completed, failed

# ============================================================================
# MODELS - CAMADA 2: BLOCKCHAIN INTELLIGENCE
# ============================================================================

class BlockchainEnrichment(BaseModel):
    """Enriquecimento de dados blockchain"""
    wallet_address: str
    category: WalletCategory
    risk_level: RiskLevel
    confidence: float = Field(0.0, ge=0, le=1)
    source: str  # "chainalysis", "trm", "elliptic", "mock"
    labeled_as: Optional[str] = None
    known_exploits: List[str] = []
    transactions_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_volume_btc: float = 0.0
    
class Transaction(BaseModel):
    """Transação blockchain"""
    txid: str
    from_address: str
    to_address: str
    amount_btc: float
    timestamp: datetime
    confirmations: int = 0
    fee_satoshi: Optional[int] = None
    is_coinbase: bool = False
    metadata: Optional[dict] = {}

class Wallet(BaseModel):
    """Carteira (node no grafo)"""
    address: str
    category: WalletCategory = WalletCategory.UNKNOWN
    risk_level: RiskLevel = RiskLevel.LOW
    enrichment: Optional[BlockchainEnrichment] = None
    transactions: List[Transaction] = []
    balance_btc: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# MODELS - CAMADA 3: GRAPH DATABASE
# ============================================================================

class GraphNode(BaseModel):
    """Nó no grafo Neo4j"""
    node_id: str
    node_type: str  # "Wallet", "Transaction", "Victim", "Case"
    properties: dict

class GraphEdge(BaseModel):
    """Aresta no grafo Neo4j"""
    source_id: str
    target_id: str
    relationship_type: str  # "RECEIVES", "SENDS", "RELATED_TO", etc
    properties: Optional[dict] = {}

class GraphCluster(BaseModel):
    """Cluster de wallets relacionadas"""
    cluster_id: str
    wallets: List[str]
    risk_score: float
    size: int
    properties: dict

# ============================================================================
# MODELS - CAMADA 4: CORRELATION ENGINE
# ============================================================================

class CorrelationRule(BaseModel):
    """Regra de correlação para scoring"""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression a ser avaliada
    weight: float  # Pontos adicionados ao score
    enabled: bool = True

class RiskScore(BaseModel):
    """Score de risco calculado"""
    entity_id: str  # Wallet ou TX
    entity_type: str  # "wallet" ou "transaction"
    risk_score: float = Field(0.0, ge=0, le=100)
    risk_level: RiskLevel
    triggered_rules: List[str] = []
    evidence: List[str] = []
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

class ClusterAnalysis(BaseModel):
    """Análise de cluster de fraude"""
    cluster_id: str
    primary_wallet: str
    related_wallets: List[str]
    total_volume_btc: float
    transaction_count: int
    risk_score: float
    suspected_crime: str  # "ransomware", "scam", "money_laundering", etc
    timeline: List[dict]

# ============================================================================
# MODELS - CAMADA 5: REPORT GENERATION
# ============================================================================

class TimelineEvent(BaseModel):
    """Evento na timeline de investigação"""
    timestamp: datetime
    event_type: str  # "transaction", "mixer_passage", "exchange_deposit", etc
    description: str
    related_addresses: List[str]
    amount_btc: Optional[float] = None

class InvestigationReport(BaseModel):
    """Relatório de investigação"""
    report_id: str
    case_id: Optional[str] = None
    initial_wallet: str
    investigation_date: datetime
    
    # Dados extraídos
    wallets_discovered: List[Wallet]
    transactions_traced: List[Transaction]
    timeline: List[TimelineEvent]
    clusters: List[ClusterAnalysis]
    
    # Análise
    total_volume_btc: float
    primary_risk_score: float
    summary: str
    recommendations: List[str]
    
    # Metadata
    analyst: Optional[str] = None
    status: str = "draft"  # draft, completed, approved

class ExecutiveSummary(BaseModel):
    """Sumário executivo para relatório"""
    title: str
    case_date: datetime
    initial_indicator: str
    key_findings: List[str]
    estimated_loss_btc: float
    risk_assessment: str
    action_items: List[str]

# ============================================================================
# MODELS - API REQUEST/RESPONSE
# ============================================================================

class SubmitIOCRequest(BaseModel):
    """Request para submeter IOC"""
    value: str
    ioc_type: IOCType
    source: str = "api"
    confidence: float = 0.8
    notes: Optional[str] = None

class SubmitIOCResponse(BaseModel):
    """Response após submeter IOC"""
    ioc_id: str
    status: str
    message: str
    created_at: datetime

class InvestigateRequest(BaseModel):
    """Request para iniciar investigação"""
    wallet_address: str
    case_name: Optional[str] = None
    depth: int = Field(3, ge=1, le=5)  # Profundidade do rastreamento

class InvestigateResponse(BaseModel):
    """Response com resultado da investigação"""
    investigation_id: str
    status: str
    wallets_found: int
    transactions_traced: int
    risk_score: float
    report_ready: bool
    report_url: Optional[str] = None

class SearchQuery(BaseModel):
    """Query de busca"""
    query: str
    entity_type: Optional[str] = None  # "wallet", "transaction", "cluster"
    filters: Optional[dict] = None

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    database: str  # "online", "offline"
    redis: str
    timestamp: datetime

# ============================================================================
# CONFIG
# ============================================================================

class Settings(BaseModel):
    """Configurações da aplicação"""
    
    # API
    api_title: str = "Crypto Fraud Tracker"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # PostgreSQL (metadata)
    postgres_url: str = "postgresql://user:password@localhost/crypto_tracker"
    
    # Blockchain Intelligence (APIs)
    chainalysis_api_key: Optional[str] = None
    trm_labs_api_key: Optional[str] = None
    elliptic_api_key: Optional[str] = None
    
    # Mode
    mock_intelligence: bool = True  # Usar mocks para prototipagem
    
    class Config:
        env_file = ".env"
