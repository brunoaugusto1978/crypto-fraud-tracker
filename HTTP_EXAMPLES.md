# 📡 HTTP Examples - API Testing Guide

## 🏥 Health & Status

### Health Check
```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "ioc_intake": "ready",
    "blockchain_intelligence": "ready",
    "correlation_engine": "ready",
    "report_generator": "ready"
  }
}
```

---

## 📥 Camada 1: IOC Intake

### 1.1 Submeter IOC Único

```bash
curl -X POST http://localhost:8000/api/v1/ioc/submit \
  -H "Content-Type: application/json" \
  -d '{
    "value": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
    "ioc_type": "wallet_address",
    "source": "manual_investigation",
    "confidence": 0.95,
    "notes": "Endereço suspeito identificado em ransomware"
  }'
```

**Response:**
```json
{
  "ioc_id": "a1b2c3d4e5f6g7h8",
  "status": "queued",
  "message": "IOC enfileirado para processamento",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 1.2 Submeter Múltiplos IOCs (Batch)

```bash
curl -X POST http://localhost:8000/api/v1/ioc/batch \
  -H "Content-Type: application/json" \
  -d '[
    {
      "value": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
      "ioc_type": "wallet_address",
      "source": "incident_response",
      "confidence": 0.95
    },
    {
      "value": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
      "ioc_type": "wallet_address",
      "source": "threat_intel",
      "confidence": 0.85
    },
    {
      "value": "192.168.1.100",
      "ioc_type": "ip_address",
      "source": "log_analysis",
      "confidence": 0.70
    },
    {
      "value": "attacker@evil.com",
      "ioc_type": "email",
      "source": "osint",
      "confidence": 0.80
    }
  ]'
```

**Response:**
```json
{
  "submitted": 4,
  "results": [
    {"ioc_id": "...", "status": "queued"},
    {"ioc_id": "...", "status": "queued"},
    {"ioc_id": "...", "status": "queued"},
    {"ioc_id": "...", "status": "queued"}
  ]
}
```

### 1.3 Verificar Status da Fila

```bash
curl -X GET http://localhost:8000/api/v1/ioc/queue-status
```

**Response:**
```json
{
  "pending": 24,
  "processed": 156,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🔗 Camada 2: Blockchain Intelligence

### 2.1 Enriquecer Carteira

```bash
curl -X GET http://localhost:8000/api/v1/blockchain/enrich/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

**Response:**
```json
{
  "wallet": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
  "category": "ransomware",
  "risk_level": "critical",
  "confidence": 0.99,
  "source": "mock",
  "labeled_as": "Ransomware: LockBit 3.0, BlackCat",
  "transactions_count": 247,
  "first_seen": "2023-03-15T14:22:00Z",
  "last_seen": "2024-01-15T09:45:00Z",
  "total_volume_btc": 2548.75
}
```

### 2.2 Obter Histórico de Transações

```bash
curl -X GET "http://localhost:8000/api/v1/blockchain/history/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4?limit=10"
```

**Response:**
```json
{
  "wallet": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
  "transactions": [
    {
      "txid": "e4d5a6f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b",
      "from_address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
      "to_address": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
      "amount_btc": 2.5,
      "timestamp": "2024-01-15T09:30:00Z",
      "confirmations": 145,
      "fee_satoshi": 2500
    },
    {
      "txid": "d3c4b5a6a7b8c9d0e1f2a3b4c5d6e7f8g9h0i1j2k3l4m5n6o7p8q9r0s1t2u3",
      "from_address": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
      "to_address": "3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy",
      "amount_btc": 2.4,
      "timestamp": "2024-01-14T23:45:00Z",
      "confirmations": 2450,
      "fee_satoshi": 2000
    }
  ]
}
```

### 2.3 Classificar Carteira

```bash
curl -X GET http://localhost:8000/api/v1/blockchain/classify/1A1z7agoat4qNB5agoat4qNB5agoat4qNB
```

**Response:**
```json
{
  "wallet": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
  "category": "mixer"
}
```

---

## 🎯 Camada 4: Correlation Engine

### 4.1 Calcular Score de Risco

```bash
curl -X GET http://localhost:8000/api/v1/risk/score/bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

**Response:**
```json
{
  "entity_id": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
  "entity_type": "wallet",
  "risk_score": 92.5,
  "risk_level": "critical",
  "triggered_rules": [
    "rule_ransomware_001",
    "rule_victims_001",
    "rule_consolidation_001"
  ],
  "evidence": [
    "Carteira está associada a exploits conhecidos de ransomware",
    "Mais de 10 remetentes enviaram para essa carteira em menos de 24 horas",
    "Múltiplos fundos consolidados rapidamente (< 1 hora)"
  ],
  "calculated_at": "2024-01-15T10:30:00Z"
}
```

### 4.2 Listar Regras de Detecção

```bash
curl -X GET http://localhost:8000/api/v1/risk/rules
```

**Response:**
```json
{
  "rules": [
    {
      "rule_id": "rule_mixer_001",
      "name": "Destination is Known Mixer",
      "description": "Carteira destino é um mixer conhecido (Tornado, Mixing Service, etc)",
      "weight": 30.0,
      "enabled": true
    },
    {
      "rule_id": "rule_ransomware_001",
      "name": "Known Ransomware Wallet",
      "description": "Carteira está associada a exploits conhecidos de ransomware",
      "weight": 50.0,
      "enabled": true
    },
    {
      "rule_id": "rule_victims_001",
      "name": "Multiple Victims in 24h",
      "description": "Mais de 10 remetentes enviaram para essa carteira em menos de 24 horas",
      "weight": 25.0,
      "enabled": true
    },
    {
      "rule_id": "rule_exchange_001",
      "name": "Consolidation to Exchange",
      "description": "Fundos consolidados e depositados em exchange KYC",
      "weight": 15.0,
      "enabled": true
    },
    {
      "rule_id": "rule_scam_001",
      "name": "Known Scam Wallet",
      "description": "Carteira está listada em banco de dados de scams",
      "weight": 40.0,
      "enabled": true
    }
  ],
  "count": 5
}
```

---

## 🔍 Investigação Completa

### 3.1 Iniciar Investigação

```bash
curl -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
    "case_name": "Ransomware LockBit - Caso #2024-001",
    "depth": 3
  }'
```

**Response:**
```json
{
  "investigation_id": "inv_1705328400.123456",
  "status": "completed",
  "wallets_found": 12,
  "transactions_traced": 24,
  "average_risk_score": 78.3,
  "primary_risk_level": "ransomware",
  "report_ready": true
}
```

### 3.2 Obter Detalhes da Investigação

```bash
curl -X GET http://localhost:8000/api/v1/investigation/inv_1705328400.123456
```

**Response:**
```json
{
  "investigation_id": "inv_1705328400.123456",
  "initial_wallet": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
  "wallets_discovered": 12,
  "transactions_traced": 24,
  "cluster_analysis": {
    "cluster_id": "inv_1705328400.123456",
    "primary_wallet": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
    "cluster_size": 12,
    "total_volume_btc": 2548.75,
    "transaction_count": 24,
    "average_risk_score": 78.3,
    "suspected_crime": "ransomware",
    "timeline": [...],
    "recommendations": [...]
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## 📊 Camada 5: Reports

### 5.1 Obter Sumário (Summary)

```bash
curl -X GET http://localhost:8000/api/v1/report/inv_1705328400.123456/summary
```

**Response:**
```json
{
  "report_id": "inv_1705328400.123456",
  "title": "Blockchain Fraud Investigation Report",
  "executive_summary": {
    "title": "Investigação de Fraude/Ransomware em Bitcoin",
    "case_date": "2024-01-15T10:30:00Z",
    "initial_indicator": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
    "key_findings": [
      "12 carteiras rastreadas",
      "24 transações identificadas",
      "2548.75 BTC movidos",
      "Score de risco médio: 78.3/100"
    ],
    "estimated_loss_btc": 2548.75,
    "risk_assessment": "🚨 CRÍTICO",
    "action_items": [
      "🚨 AÇÃO PRIORITÁRIA: Notificar coordenador de ransomware",
      "📋 Reportar para CISA/FS-ISAC imediatamente",
      "🔒 Coordenar com exchanges para bloquear wallets",
      "🔍 Continuar rastreamento para destino final",
      "💾 Arquivar evidências para auditorias/investigações"
    ]
  },
  "wallets_discovered": 12,
  "transactions_traced": 24,
  "total_volume_btc": 2548.75,
  "average_risk_score": 78.3
}
```

### 5.2 Obter Timeline

```bash
curl -X GET http://localhost:8000/api/v1/report/inv_1705328400.123456/timeline
```

**Response:**
```json
{
  "timeline": [
    {
      "timestamp": "2024-01-15T09:30:00Z",
      "event_type": "transaction",
      "description": "bc1qw508d... → 1A1z7ago...",
      "amount_btc": 2.5,
      "from_address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
      "to_address": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
      "from_category": "ransomware",
      "to_category": "mixer"
    },
    {
      "timestamp": "2024-01-14T23:45:00Z",
      "event_type": "mixer_passage",
      "description": "Envio para MIXER: Tornado Cash",
      "amount_btc": 2.4,
      "from_address": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
      "to_address": "3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy",
      "from_category": "mixer",
      "to_category": "mixer"
    },
    {
      "timestamp": "2024-01-14T15:20:00Z",
      "event_type": "exchange_deposit",
      "description": "Depósito em EXCHANGE: Binance Cold Wallet",
      "amount_btc": 2.3,
      "from_address": "3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy",
      "to_address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
      "from_category": "mixer",
      "to_category": "exchange"
    }
  ]
}
```

### 5.3 Obter Dados de Grafo (para D3.js/Cytoscape)

```bash
curl -X GET http://localhost:8000/api/v1/report/inv_1705328400.123456/graph
```

**Response:**
```json
{
  "nodes": [
    {
      "id": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
      "label": "bc1qw508d6...",
      "category": "ransomware",
      "color": "#FFD93D",
      "risk_level": "critical",
      "risk_score": 92.5,
      "size": 30,
      "title": "Ransomware: LockBit 3.0, BlackCat"
    },
    {
      "id": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
      "label": "1A1z7agoat...",
      "category": "mixer",
      "color": "#FF6B6B",
      "risk_level": "high",
      "risk_score": 75.0,
      "size": 30,
      "title": "Tornado Cash"
    }
  ],
  "edges": [
    {
      "source": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
      "target": "1A1z7agoat4qNB5agoat4qNB5agoat4qNB",
      "weight": 2.5,
      "label": "2.50 BTC",
      "timestamp": "2024-01-15T09:30:00Z"
    }
  ],
  "metadata": {
    "node_count": 12,
    "edge_count": 24,
    "total_volume_btc": 2548.75,
    "generated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 5.4 Obter Relatório HTML (Interativo)

```bash
curl -X GET http://localhost:8000/api/v1/report/inv_1705328400.123456/html > report.html
open report.html
```

**Gera:** Relatório HTML completo com:
- 📊 Estatísticas
- ⏱️ Timeline interativa
- 🔗 Grafo D3.js (clickable)
- 📋 Recomendações
- 🎯 Sumário executivo

---

## 🧪 Dados de Teste

### Populate Test Data

```bash
curl -X POST http://localhost:8000/api/v1/test/populate
```

**Response:**
```json
{
  "status": "populated",
  "test_iocs_count": 2,
  "results": [
    {"ioc_id": "...", "status": "queued"},
    {"ioc_id": "...", "status": "queued"}
  ]
}
```

---

## 📌 Wallets de Teste Recomendadas

| Wallet | Tipo | Risco | Uso |
|--------|------|-------|-----|
| `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4` | Ransom | CRÍTICO | Teste de ransomware |
| `1A1z7agoat4qNB5agoat4qNB5agoat4qNB` | Mixer | ALTO | Teste de mixer |
| `1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2` | Exchange | BAIXO | Teste de exchange |

---

## 🔄 Integração Postman

### Importar Coleção

Salvar como `crypto-fraud-tracker.postman_collection.json`:

```json
{
  "info": {
    "name": "Crypto Fraud Tracker API",
    "version": "1.0.0"
  },
  "item": [
    {
      "name": "IOC Intake",
      "item": [
        {
          "name": "Submit Single IOC",
          "request": {
            "method": "POST",
            "url": "{{baseUrl}}/api/v1/ioc/submit",
            "body": {
              "mode": "raw",
              "raw": "{\"value\": \"bc1q...\", \"ioc_type\": \"wallet_address\"}"
            }
          }
        }
      ]
    }
  ]
}
```

---

**Todas as requisições suportam:**
- ✅ cURL
- ✅ Postman
- ✅ HTTPie
- ✅ JavaScript Fetch
- ✅ Python Requests
- ✅ Go http.Client

---

**Última atualização:** Janeiro 2024
