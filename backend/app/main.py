"""
CRYPTO FRAUD TRACKER - Backend Integrado (5 Camadas)
"""
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import AuthService
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.layers.layer1_ioc_intake import IOCIntakeService, IOCValidator
from app.layers.layer2_blockchain_intelligence import (
    MockBlockchainIntelligence, BlockchainIntelligenceService,
)
from app.layers.layer2_blockstream import BlockstreamIntelligence
from app.layers.layer3_graph_fixed import Neo4jConnection, GraphDatabaseService
from app.layers.layer4_correlation_engine import CorrelationEngine, ClusterAnalyzer
from app.layers.layer5_report_generator import (
    ReportGenerator, TimelineGenerator, GraphVisualizer,
)
from app.layers.investigation_scorer import InvestigationScorer
from app.layers.db_store import InvestigationStore
from app.layers.evidence import build_evidence_record, utc_now_iso

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
POSTGRES_URL = os.getenv("POSTGRES_URL")
ENV = os.getenv("ENV", "dev")  # "dev" ou "prod"
INTEL_PROVIDER = os.getenv("INTEL_PROVIDER") or ("mock" if ENV != "prod" else "")  # "mock" ou "blockstream"

# Fail-safe: credenciais criticas sao obrigatorias (nao usar defaults inseguros)
if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD ausente. Defina no .env.")
if not POSTGRES_URL:
    raise RuntimeError("POSTGRES_URL ausente. Defina no .env.")
if INTEL_PROVIDER not in {"mock", "blockstream"}:
    raise RuntimeError("INTEL_PROVIDER invalido ou ausente. Use 'blockstream' ou 'mock'.")
if ENV == "prod" and INTEL_PROVIDER == "mock":
    raise RuntimeError("INTEL_PROVIDER=mock nao e permitido em producao.")
# CORS: origens permitidas (separadas por virgula no .env)
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]


class SubmitIOCRequest(BaseModel):
    value: str
    ioc_type: str = "wallet_address"
    source: str = "api"
    confidence: float = 0.8
    notes: Optional[str] = None


class InvestigateRequest(BaseModel):
    wallet_address: str
    case_name: Optional[str] = None
    depth: int = Field(3, ge=1, le=5)  # limite seguro: 1..5


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateEmailRequest(BaseModel):
    email: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateRoleRequest(BaseModel):
    role: str


app = FastAPI(
    title="Crypto Fraud Tracker API",
    description="Sistema de rastreamento de fraudes em Bitcoin - 5 camadas",
    version="2.0.0",
    docs_url=None if ENV == "prod" else "/docs",
    redoc_url=None if ENV == "prod" else "/redoc",
)
# Em producao: credenciais desligadas e metodos/headers restritos.
# Como usamos JWT via header Authorization (nao cookies), nao precisamos de credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

ioc_service = IOCIntakeService(redis_host=REDIS_HOST, redis_port=REDIS_PORT)
if INTEL_PROVIDER == "blockstream":
    blockchain_intel = BlockstreamIntelligence()
    print("[Intel] usando BlockstreamIntelligence (dados reais)")
else:
    blockchain_intel = MockBlockchainIntelligence()
    print("[Intel] usando MockBlockchainIntelligence (prototipagem)")
blockchain_service = BlockchainIntelligenceService(blockchain_intel)
correlation_engine = CorrelationEngine()
cluster_analyzer = ClusterAnalyzer(correlation_engine)
report_gen = ReportGenerator()
investigation_scorer = InvestigationScorer()
auth_service = AuthService()
security = HTTPBearer(auto_error=False)


# ---- Dependency: exige token JWT valido ----
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Token ausente")
    payload = auth_service.decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    return {"username": payload.get("sub"), "role": payload.get("role")}


# ---- Dependency: exige usuario admin ----
def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return current_user

neo4j_conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
graph_service = None
investigations = InvestigationStore(POSTGRES_URL)


def get_graph_service():
    global graph_service
    if graph_service is None:
        try:
            neo4j_conn.connect()
            graph_service = GraphDatabaseService(neo4j_conn)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Neo4j indisponível: {e}")
    return graph_service


def _extract_wallet_intel(enr: dict) -> dict:
    """Extrai os dados reais de inteligencia da carteira (Blockstream)."""
    if not enr:
        return {}
    return {
        "source": enr.get("source", "mock"),
        "category": enr.get("category"),
        "labeled_as": enr.get("labeled_as"),
        "confidence": enr.get("confidence"),
        "balance_btc": enr.get("balance_btc"),
        "total_received_btc": enr.get("total_received_btc"),
        "total_sent_btc": enr.get("total_sent_btc"),
        "transactions_count": enr.get("transactions_count"),
    }


def _get_investigation_or_404(investigation_id: str, current_user: dict) -> dict:
    inv = investigations.get_for_user(
        investigation_id=investigation_id,
        username=current_user["username"],
        role=current_user.get("role", "analyst"),
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Investigação não encontrada")
    return inv


@app.get("/api/v1/health")
async def health_check():
    services = {"ioc_intake": "ready", "blockchain_intelligence": "ready",
                "correlation_engine": "ready", "report_generator": "ready",
                "intel_provider": INTEL_PROVIDER}
    try:
        ioc_service.redis_client.ping()
        services["redis"] = "connected"
    except Exception:
        services["redis"] = "offline"
    try:
        get_graph_service()
        services["neo4j"] = "connected"
    except Exception:
        services["neo4j"] = "offline"
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "2.0.0", "services": services}


@app.post("/api/v1/ioc/submit")
async def submit_ioc(req: SubmitIOCRequest, current_user: dict = Depends(get_current_user)):
    result = ioc_service.submit_ioc(value=req.value, ioc_type=req.ioc_type,
                                    source=req.source, confidence=req.confidence, notes=req.notes)
    if result["status"] == "rejected":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/api/v1/ioc/queue-status")
async def queue_status(current_user: dict = Depends(require_admin)):
    return ioc_service.get_queue_status()


@app.get("/api/v1/blockchain/enrich/{wallet_address}")
async def enrich_wallet(wallet_address: str, current_user: dict = Depends(get_current_user)):
    if not IOCValidator.validate_bitcoin_address(wallet_address):
        raise HTTPException(status_code=400, detail="Endereço Bitcoin inválido")
    return await blockchain_intel.enrich_wallet(wallet_address)


@app.get("/api/v1/blockchain/classify/{wallet_address}")
async def classify_wallet(wallet_address: str, current_user: dict = Depends(get_current_user)):
    if not IOCValidator.validate_bitcoin_address(wallet_address):
        raise HTTPException(status_code=400, detail="Endereço Bitcoin inválido")
    category = await blockchain_intel.classify_wallet(wallet_address)
    return {"wallet": wallet_address, "category": category}


@app.get("/api/v1/risk/score/{wallet_address}")
async def risk_score(wallet_address: str, current_user: dict = Depends(get_current_user)):
    enrichment = await blockchain_intel.enrich_wallet(wallet_address)
    return correlation_engine.calculate_risk_score(enrichment, {})


@app.get("/api/v1/risk/rules")
async def list_rules(current_user: dict = Depends(get_current_user)):
    return {"rules": correlation_engine.get_rules()}


@app.post("/api/v1/investigate")
async def investigate(req: InvestigateRequest, current_user: dict = Depends(get_current_user)):
    if not IOCValidator.validate_bitcoin_address(req.wallet_address):
        raise HTTPException(status_code=400, detail="Endereço Bitcoin inválido")

    investigation_id = f"inv_{datetime.utcnow().timestamp()}"
    trace = await blockchain_service.trace_transaction_chain(req.wallet_address, depth=req.depth)
    chain = trace["wallets"]
    wallets = [item["wallet"] for item in chain]
    enrichments = {item["wallet"]: item["enrichment"] for item in chain}
    transactions = trace.get("transactions", [])
    raw_transactions = trace.get("raw_transactions", [])

    evidence_records = []
    for wallet, enrichment in enrichments.items():
        evidence_records.append(build_evidence_record(
            investigation_id=investigation_id,
            evidence_type="wallet_enrichment",
            source_name=enrichment.get("source", INTEL_PROVIDER),
            source_url=enrichment.get("source_url"),
            subject=wallet,
            raw_payload=enrichment.get("raw_payload", enrichment),
            collected_by=current_user["username"],
        ))
    for tx in raw_transactions:
        evidence_records.append(build_evidence_record(
            investigation_id=investigation_id,
            evidence_type="blockchain_transaction",
            source_name=tx.get("source", INTEL_PROVIDER),
            source_url=tx.get("source_url"),
            subject=tx.get("txid") or req.wallet_address,
            raw_payload=tx.get("raw_payload", tx),
            collected_by=current_user["username"],
        ))

    risk_scores = []
    for w in wallets:
        wallet_txs = [t for t in transactions if t.get("from_address") == w or t.get("to_address") == w]
        score = correlation_engine.calculate_risk_score(enrichments.get(w, {}), {"recent_transactions": wallet_txs})
        score["wallet"] = w
        risk_scores.append(score)

    scoring = investigation_scorer.score_investigation(
        initial_wallet=req.wallet_address,
        wallets=wallets,
        enrichments=enrichments,
        risk_scores=risk_scores,
    )
    cluster = cluster_analyzer.analyze_cluster(
        cluster_id=investigation_id,
        wallets=[{"address": w, **enrichments.get(w, {})} for w in wallets],
        transactions=transactions)

    neo4j_status = "skipped"
    try:
        gs = get_graph_service()
        for w in wallets:
            enr = enrichments.get(w, {})
            sc = next((s for s in risk_scores if s["wallet"] == w), {})
            gs.add_wallet(w, enr.get("category", "unknown"),
                          enr.get("risk_level", "low"), sc.get("risk_score", 0))
        for tx in transactions:
            gs.add_transaction(tx.get("from_address"), tx.get("to_address"),
                               tx.get("amount_btc", 0), txid=tx.get("txid"),
                               timestamp=tx.get("timestamp"),
                               evidence_hash=tx.get("raw_sha256"),
                               source=tx.get("source"))
        neo4j_status = "persisted"
    except HTTPException:
        neo4j_status = "neo4j_offline"
    except Exception as e:
        neo4j_status = f"error: {e}"

    investigation_data = {
        "id": investigation_id,
        "case_name": req.case_name,
        "owner_username": current_user["username"],
        "initial_wallet": req.wallet_address,
        "wallets": wallets,
        "enrichments": enrichments,
        "transactions": transactions,
        "raw_transactions": raw_transactions,
        "evidence_records": evidence_records,
        "risk_scores": risk_scores,
        "cluster_analysis": cluster,
        "scoring": scoring,
        "created_at": utc_now_iso(),
    }
    investigations[investigation_id] = investigation_data
    investigations.save_evidence_records(investigation_id, evidence_records)

    return {"investigation_id": investigation_id, "status": "completed",
            "wallet_address": req.wallet_address, "wallets_found": len(wallets),
            "transactions_traced": len(transactions),
            "evidence_count": len(evidence_records),
            "overall_risk_score": scoring["overall_risk_score"],
            "risk_level": scoring["risk_level"],
            "initial_wallet_score": scoring["initial_wallet_score"],
            "max_risk_score": scoring["max_risk_score"],
            "weighted_risk_score": scoring["weighted_risk_score"],
            "dangerous_destinations": scoring["dangerous_destinations"],
            "explanation": scoring["explanation"],
            "suspected_crime": cluster.get("suspected_crime"),
            "aml_typologies": cluster.get("aml_typologies", []),
            "wallet_intel": _extract_wallet_intel(enrichments.get(req.wallet_address, {})),
            "neo4j": neo4j_status, "report_ready": True}


@app.get("/api/v1/investigation/{investigation_id}")
async def get_investigation(investigation_id: str, current_user: dict = Depends(get_current_user)):
    inv = _get_investigation_or_404(investigation_id, current_user)
    scoring = inv.get("scoring", {})
    return {"investigation_id": investigation_id, "status": "completed",
            "case_name": inv.get("case_name"),
            "owner_username": inv.get("owner_username"),
            "wallet_address": inv["initial_wallet"],
            "wallets_found": len(inv["wallets"]),
            "transactions_traced": len(inv["transactions"]),
            "evidence_count": len(inv.get("evidence_records", [])),
            "overall_risk_score": scoring.get("overall_risk_score", 0),
            "risk_level": scoring.get("risk_level", "low"),
            "initial_wallet_score": scoring.get("initial_wallet_score", 0),
            "max_risk_score": scoring.get("max_risk_score", 0),
            "weighted_risk_score": scoring.get("weighted_risk_score", 0),
            "dangerous_destinations": scoring.get("dangerous_destinations", []),
            "explanation": scoring.get("explanation", ""),
            "suspected_crime": inv["cluster_analysis"].get("suspected_crime"),
            "aml_typologies": inv["cluster_analysis"].get("aml_typologies", []),
            "wallet_intel": _extract_wallet_intel(inv.get("enrichments", {}).get(inv["initial_wallet"], {})),
            "neo4j": "persisted", "report_ready": True,
            "created_at": inv["created_at"]}


@app.get("/api/v1/report/{investigation_id}/summary")
async def report_summary(investigation_id: str, current_user: dict = Depends(get_current_user)):
    inv = _get_investigation_or_404(investigation_id, current_user)
    return report_gen.generate_investigation_report(
        investigation_id=investigation_id, initial_wallet=inv["initial_wallet"],
        wallets=[{"address": w} for w in inv["wallets"]], transactions=inv["transactions"],
        enrichments=inv["enrichments"], cluster_analysis=inv["cluster_analysis"],
        risk_scores=inv["risk_scores"])


@app.get("/api/v1/report/{investigation_id}/timeline")
async def report_timeline(investigation_id: str, current_user: dict = Depends(get_current_user)):
    inv = _get_investigation_or_404(investigation_id, current_user)
    tg = TimelineGenerator()
    return {"timeline": tg.generate_timeline(inv["transactions"], inv["enrichments"])}


@app.get("/api/v1/report/{investigation_id}/graph")
async def report_graph(investigation_id: str, current_user: dict = Depends(get_current_user)):
    inv = _get_investigation_or_404(investigation_id, current_user)
    gv = GraphVisualizer()
    return gv.generate_graph_data(
        wallets=[{"address": w} for w in inv["wallets"]],
        transactions=inv["transactions"], enrichments=inv["enrichments"])


@app.get("/api/v1/report/{investigation_id}/html", response_class=HTMLResponse)
async def report_html(investigation_id: str, current_user: dict = Depends(get_current_user)):
    inv = _get_investigation_or_404(investigation_id, current_user)
    report = report_gen.generate_investigation_report(
        investigation_id=investigation_id, initial_wallet=inv["initial_wallet"],
        wallets=[{"address": w} for w in inv["wallets"]], transactions=inv["transactions"],
        enrichments=inv["enrichments"], cluster_analysis=inv["cluster_analysis"],
        risk_scores=inv["risk_scores"])
    gv = GraphVisualizer()
    graph_data = gv.generate_graph_data(
        wallets=[{"address": w} for w in inv["wallets"]],
        transactions=inv["transactions"], enrichments=inv["enrichments"])
    return report_gen.generate_html_report(report, gv.generate_d3_html(graph_data))


@app.get("/api/v1/graph/high-risk")
async def graph_high_risk(min_score: float = 50, current_user: dict = Depends(get_current_user)):
    gs = get_graph_service()
    return {"wallets": gs.get_high_risk_wallets(min_score)}


@app.get("/api/v1/graph/recipients/{wallet_address}")
async def graph_recipients(wallet_address: str, depth: int = Query(3, ge=1, le=5), current_user: dict = Depends(get_current_user)):
    gs = get_graph_service()
    return {"recipients": gs.find_recipients(wallet_address, depth)}


@app.post("/api/v1/auth/register")
async def register(
    req: RegisterRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Bootstrap de admin:
    - Se NAO ha usuarios ainda, o 1o registro vira 'admin' (sem exigir token).
    - Se ja existem usuarios, registrar exige um admin autenticado.
    """
    is_first_user = auth_service.count_users() == 0

    if is_first_user:
        role = "admin"
    else:
        # Exige token de admin
        if credentials is None:
            raise HTTPException(status_code=401, detail="Token ausente (registro exige admin)")
        payload = auth_service.decode_token(credentials.credentials)
        if payload is None:
            raise HTTPException(status_code=401, detail="Token invalido ou expirado")
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Apenas administradores podem registrar usuarios")
        role = "analyst"

    try:
        user = auth_service.create_user(req.username, req.password, req.email, role=role)
        token = auth_service.create_token(user["username"], user["role"])
        return {"status": "registered", "username": user["username"],
                "role": user["role"], "access_token": token, "token_type": "bearer",
                "bootstrap_admin": is_first_user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    user = auth_service.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario ou senha invalidos")
    token = auth_service.create_token(user["username"], user["role"])
    return {"status": "ok", "username": user["username"], "role": user["role"],
            "access_token": token, "token_type": "bearer"}


@app.get("/api/v1/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.get("/api/v1/investigations/recent")
async def list_recent_investigations(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Lista investigacoes persistidas (historico)."""
    return {"investigations": investigations.list_recent(limit, current_user["username"], current_user.get("role", "analyst")),
            "total": investigations.count(current_user["username"], current_user.get("role", "analyst"))}


# ---- Conta propria ----
@app.patch("/api/v1/auth/me/email")
async def update_my_email(req: UpdateEmailRequest, current_user: dict = Depends(get_current_user)):
    try:
        user = auth_service.update_email(current_user["username"], req.email)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        return {"status": "updated", "email": user["email"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/auth/change-password")
async def change_my_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    try:
        auth_service.change_password(current_user["username"], req.current_password, req.new_password)
        return {"status": "password_changed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Painel admin ----
@app.get("/api/v1/admin/users")
async def admin_list_users(admin: dict = Depends(require_admin)):
    return {"users": auth_service.list_users(), "total": auth_service.count_users()}


@app.patch("/api/v1/admin/users/{user_id}/role")
async def admin_update_role(user_id: int, req: UpdateRoleRequest, admin: dict = Depends(require_admin)):
    try:
        user = auth_service.update_role(user_id, req.role)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        return {"status": "role_updated", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/admin/users/{user_id}")
async def admin_delete_user(user_id: int, admin: dict = Depends(require_admin)):
    # Protecao: nao permitir deletar o ultimo admin
    users = auth_service.list_users()
    target = next((u for u in users if u["id"] == user_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if target["role"] == "admin" and auth_service.count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Nao e possivel remover o ultimo admin")
    ok = auth_service.delete_user(user_id)
    return {"status": "deleted" if ok else "not_found", "user_id": user_id}


@app.get("/")
async def root():
    return {"name": "Crypto Fraud Tracker API", "version": "2.0.0",
            "layers": ["1. IOC Intake", "2. Blockchain Intelligence",
                       "3. Graph Database (Neo4j)", "4. Correlation Engine",
                       "5. Report Generation"],
            "docs": "/docs", "health": "/api/v1/health"}
