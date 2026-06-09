# 🔍 Crypto Fraud Tracker - Arquitetura Completa

## Visão Geral
Sistema de rastreamento de movimentações financeiras ligadas a fraudes, golpes, carding, ransomware e lavagem de dinheiro em Bitcoin.

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
│  Dashboard | Timeline | Graph Viewer | Risk Scoring        │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼────────────────────────────────────────┐
│                  BACKEND (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. IOC INTAKE LAYER                                  │  │
│  │    - API para submissão de endereços                 │  │
│  │    - Validação de formato                             │  │
│  │    - Enfileiramento (Redis)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 2. BLOCKCHAIN INTELLIGENCE LAYER                     │  │
│  │    - APIs mockadas (Chainalysis, TRM, Elliptic)    │  │
│  │    - Classificação de carteiras                      │  │
│  │    - Histórico de transações                         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 3. GRAPH DATABASE LAYER (Neo4j)                      │  │
│  │    - Relacionamentos wallet → tx → wallet            │  │
│  │    - Clustering automático                           │  │
│  │    - Queries de grafo complexas                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 4. CORRELATION ENGINE                               │  │
│  │    - Scoring de risco (0-100)                        │  │
│  │    - Regras de detecção customizáveis               │  │
│  │    - Clustering de fraude                            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 5. REPORT GENERATION                                │  │
│  │    - Timeline automática                             │  │
│  │    - Grafo navegável                                 │  │
│  │    - PDF executivo                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼──┐    ┌───▼────┐  ┌───▼────┐
   │ Neo4j │    │ Redis  │  │PostgreSQL
   │ Graph │    │ Cache  │  │ Metadata
   └───────┘    └────────┘  └────────┘
```

## 📊 Fluxo de Dados

```
Usuário entra com carteira/TXID
         ↓
    IOC INTAKE
    (validação)
         ↓
    Fila (Redis)
         ↓
    BLOCKCHAIN INTEL
    (enriquecimento)
         ↓
    GRAPH DATABASE
    (persistência)
         ↓
    CORRELATION ENGINE
    (scoring)
         ↓
    REPORT GENERATOR
    (visualização)
         ↓
    Frontend React
    (Dashboard)
```

## 🏗️ Estrutura de Diretórios

```
crypto-fraud-tracker/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Variáveis de ambiente
│   │   │
│   │   ├── layers/
│   │   │   ├── __init__.py
│   │   │   ├── ioc_intake.py       # Layer 1: IOC Intake
│   │   │   ├── blockchain_intel.py # Layer 2: Intelligence
│   │   │   ├── graph_db.py         # Layer 3: Graph DB
│   │   │   ├── correlation.py      # Layer 4: Correlation
│   │   │   └── reporter.py         # Layer 5: Reports
│   │   │
│   │   ├── models/
│   │   │   ├── ioc.py              # Dataclass para IOC
│   │   │   ├── wallet.py           # Dataclass para Wallet
│   │   │   ├── transaction.py      # Dataclass para TX
│   │   │   └── risk_score.py       # Dataclass para Risk
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py           # Endpoints FastAPI
│   │   │   └── websocket.py        # WebSocket para real-time
│   │   │
│   │   ├── db/
│   │   │   ├── neo4j.py            # Conexão Neo4j
│   │   │   └── postgres.py         # PostgreSQL para metadata
│   │   │
│   │   ├── services/
│   │   │   ├── redis_queue.py      # Fila de processamento
│   │   │   └── cache.py            # Cache layer
│   │   │
│   │   └── utils/
│   │       ├── validators.py       # Validação de endereços
│   │       ├── formatters.py       # Format de dados
│   │       └── logger.py           # Logging estruturado
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── index.js
│   │   ├── App.jsx
│   │   │
│   │   ├── components/
│   │   │   ├── Dashboard.jsx       # Dashboard principal
│   │   │   ├── GraphViewer.jsx     # Visualização de grafo
│   │   │   ├── Timeline.jsx        # Timeline de TX
│   │   │   ├── SearchBar.jsx       # Busca
│   │   │   └── RiskScore.jsx       # Card de risco
│   │   │
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Investigation.jsx
│   │   │   └── Reports.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js              # Chamadas ao backend
│   │   │
│   │   ├── hooks/
│   │   │   ├── useGraph.js         # Graph logic
│   │   │   └── useWebSocket.js     # Real-time updates
│   │   │
│   │   └── styles/
│   │       └── App.css
│   │
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
│
├── docker-compose.yml             # Neo4j + Redis + Backend
├── README.md
└── examples/
    ├── test_iocs.json             # IOCs de teste
    └── sample_wallets.json        # Carteiras mockadas
```

## 🔌 Integrações

### Camada 2 - Blockchain Intelligence (Mockada inicialmente)

```python
# Adaptador genérico para trocar depois
class BlockchainIntelligence:
    async def enrich_wallet(wallet_address: str):
        # Retorna categoria, risco, histórico
        return {
            "category": "mixer|exchange|ransomware|scam",
            "risk_level": "low|medium|high|critical",
            "history": [...],
            "source": "chainalysis|trm|elliptic|mock"
        }
```

### APIs Reais Suportadas (Futuros)
- ✅ **Chainalysis** - Mais rigorosa, para instituições financeiras
- ✅ **TRM Labs** - Detecção de fraude em tempo real
- ✅ **Elliptic** - Análise de risco
- ✅ **Blockchain.com** - Explorador público (livre)

## 📈 Camada 4 - Scoring de Risco

Cada transação/wallet recebe score 0-100 baseado em:

```
Score = Σ (rule_weight × rule_match)

Regra 1: Destinação conhecida como mixer
  Weight: 30 points
  
Regra 2: Múltiplas vítimas em < 24h
  Weight: 25 points
  
Regra 3: Wallet associada a ransomware
  Weight: 50 points
  
Regra 4: Movimentação para exchange KYC
  Weight: 15 points
  
Regra 5: Consolidação de fundos
  Weight: 20 points
```

**Scores Interpretativos:**
- 0-20: Baixo risco ✅
- 21-50: Risco médio ⚠️
- 51-80: Alto risco 🔴
- 81-100: Crítico 🚨

## 🎯 Casos de Uso

| Caso | Input | Output |
|------|-------|--------|
| Fraude inicial | Carteira vítima | Timeline + Rastreamento |
| Investigação | TXID | Grafo completo + Score |
| Relatório | Wallet origem | PDF com evidências |
| Monitoramento | Lista de IOCs | Alertas automáticos |
| Compliance | Endereço exchange | Validação de origem |

## 🔐 Considerações de Segurança

- ✅ Sem credenciais em código (.env apenas)
- ✅ Validação rigorosa de IOCs
- ✅ Logging auditável de todas as ações
- ✅ CORS restritivo no backend
- ✅ Rate limiting por IP
- ✅ JWT para autenticação (futuro)

---

**Status:** Prototipagem | **Próximos passos:** Integração com APIs reais
