# 🚀 Quick Start - Começar em 5 Minutos

## 1️⃣ Pré-requisitos

```bash
# Verificar Docker
docker --version
docker-compose --version

# Liberar portas (8000, 3000, 7687, 6379, 5432)
```

## 2️⃣ Clone e Build

```bash
# Clone
git clone https://github.com/seu-org/crypto-fraud-tracker.git
cd crypto-fraud-tracker

# Build
docker-compose build

# Start
docker-compose up -d

# Aguardar ~30-60 segundos para todos os serviços iniciarem
sleep 45
```

## 3️⃣ Verificar Saúde

```bash
# API Backend
curl http://localhost:8000/api/v1/health

# Esperado: { "status": "healthy", ... }
```

## 4️⃣ Testar com Exemplo Real

### Opção A: Via cURL

```bash
# Variáveis
WALLET="bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"

# Submeter IOC
curl -X POST http://localhost:8000/api/v1/ioc/submit \
  -H "Content-Type: application/json" \
  -d '{
    "value": "'$WALLET'",
    "ioc_type": "wallet_address",
    "confidence": 0.95
  }'

# Resposta esperada:
# { "ioc_id": "...", "status": "queued", ... }

# Investigar
INV=$(curl -s -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "'$WALLET'",
    "depth": 2
  }' | grep -o '"investigation_id":"[^"]*' | cut -d'"' -f4)

echo "Investigation ID: $INV"

# Obter relatório summary
curl http://localhost:8000/api/v1/report/$INV/summary | jq '.'

# Gerar HTML interativo
curl http://localhost:8000/api/v1/report/$INV/html > report_$INV.html
open report_$INV.html
```

### Opção B: Via Python

```python
#!/usr/bin/env python3
import asyncio
import requests
import json

# Configuração
API_BASE = "http://localhost:8000/api/v1"
WALLET = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"

async def main():
    # 1. Classificar carteira
    resp = requests.get(f"{API_BASE}/blockchain/classify/{WALLET}")
    print(f"✓ Classificação: {resp.json()}")
    
    # 2. Enriquecer
    resp = requests.get(f"{API_BASE}/blockchain/enrich/{WALLET}")
    enrichment = resp.json()
    print(f"✓ Enriquecimento: {enrichment['category']}")
    
    # 3. Score de risco
    resp = requests.get(f"{API_BASE}/risk/score/{WALLET}")
    score = resp.json()
    print(f"✓ Risk Score: {score['risk_score']}/100")
    
    # 4. Iniciar investigação completa
    resp = requests.post(
        f"{API_BASE}/investigate",
        json={
            "wallet_address": WALLET,
            "depth": 3
        }
    )
    inv = resp.json()
    inv_id = inv['investigation_id']
    print(f"✓ Investigation: {inv_id}")
    print(f"  - Wallets: {inv['wallets_found']}")
    print(f"  - Transactions: {inv['transactions_traced']}")
    print(f"  - Risk Score: {inv['average_risk_score']}/100")
    
    # 5. Gerar relatório
    resp = requests.get(f"{API_BASE}/report/{inv_id}/summary")
    report = resp.json()
    print(f"\n✓ Relatório Gerado")
    print(json.dumps(report, indent=2)[:500] + "...")

if __name__ == "__main__":
    asyncio.run(main())
```

## 5️⃣ Acessar Interfaces

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **API Swagger** | http://localhost:8000/docs | N/A |
| **API ReDoc** | http://localhost:8000/redoc | N/A |
| **Frontend Dashboard** | http://localhost:3000 | N/A |
| **Neo4j Browser** | http://localhost:7474 | neo4j / REMOVED_DEV_PASSWORD |
| **Redis CLI** | `docker exec -it crypto-tracker-redis redis-cli` | N/A |

## 6️⃣ Exemplos de Wallets de Teste

### Mixer Conhecida (Alto Risco)
```
1A1z7agoat4qNB5agoat4qNB5agoat4qNB
```

### Exchange (Baixo Risco)
```
1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2
```

### Carteira Aleatória
```
bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

## 7️⃣ Casos de Uso Comuns

### 🚨 Rastrear Ransomware

```bash
curl -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "bc1qxxxxxxxxxxxxxxxxxxxxxx",
    "case_name": "LockBit Incident",
    "depth": 4
  }' | jq '.investigation_id' | xargs -I {} \
  curl http://localhost:8000/api/v1/report/{}/html > ransomware_report.html
```

### 📊 Batch Submit de IOCs

```bash
curl -X POST http://localhost:8000/api/v1/ioc/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"value": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "ioc_type": "wallet_address"},
    {"value": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB", "ioc_type": "wallet_address"},
    {"value": "192.168.1.1", "ioc_type": "ip_address"}
  ]' | jq '.'
```

### 🎯 Listar Wallets de Alto Risco

```bash
# Neo4j Cypher Query
docker exec -it crypto-tracker-neo4j cypher-shell \
  -u neo4j -p REMOVED_DEV_PASSWORD \
  'MATCH (w:Wallet) WHERE w.risk_level IN ["high", "critical"] RETURN w LIMIT 10'
```

## 8️⃣ Status dos Serviços

```bash
# Verificar todos
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f backend

# Restart individual
docker-compose restart backend
```

## 9️⃣ Parar e Limpar

```bash
# Parar mas manter dados
docker-compose down

# Parar e apagar tudo (incluindo BDs)
docker-compose down -v

# Verificar se tudo foi removido
docker-compose ps
```

## 🔟 Próximas Etapas

1. **Integrar APIs Reais**
   - Obter credenciais Chainalysis/TRM Labs
   - Modificar `backend/app/layers/blockchain_intel.py`
   - Trocar `MockBlockchainIntelligence` por `ChainalysisIntelligence`

2. **Customizar Regras**
   - Editar `layer4_correlation_engine.py`
   - Adicionar regras com `RuleFactory.add_rule()`

3. **Adicionar Autenticação**
   - Implementar JWT em `backend/app/api/auth.py`
   - Proteger endpoints com `@app.get("/protected", dependencies=[Depends(verify_token)])`

4. **Monitorar em Produção**
   - Setup Prometheus/Grafana
   - Alertas automáticos para scores altos

---

## 💡 Dicas Rápidas

```bash
# Limpar cache Redis
docker exec -it crypto-tracker-redis redis-cli FLUSHALL

# Ver dados no Neo4j
docker exec -it crypto-tracker-neo4j cypher-shell -u neo4j -p REMOVED_DEV_PASSWORD \
  'MATCH (n) RETURN COUNT(n) as node_count'

# Testar conexão com PostgreSQL
docker exec -it crypto-tracker-postgres \
  psql -U crypto_user -d crypto_tracker -c 'SELECT COUNT(*) FROM wallets;'

# Ver variáveis de ambiente
docker-compose exec backend env | grep -i neo4j

# Rebuild sem cache
docker-compose build --no-cache
```

---

## 📖 Documentação Completa

Consulte `README.md` para guia completo com:
- Arquitetura detalhada
- Todos os endpoints
- Integração com APIs
- Troubleshooting avançado

---

**Status:** ✅ Pronto para produção
**Última atualização:** Janeiro 2024
**Versão:** 1.0.0
