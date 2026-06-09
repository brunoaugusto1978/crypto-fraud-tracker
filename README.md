# Crypto Fraud Tracker

Sistema de rastreamento de fraudes em Bitcoin com arquitetura de 5 camadas.

## Status: v2.0 - 5 camadas integradas e funcionando

1. IOC Intake (Redis)
2. Blockchain Intelligence
3. Graph Database (Neo4j)
4. Correlation Engine (scoring)
5. Report Generation (HTML/Timeline/Grafo)

## Instalacao

    docker-compose build
    docker-compose up -d
    docker-compose ps

## Testar

    curl http://localhost:8000/api/v1/health

    curl -X POST http://localhost:8000/api/v1/investigate \
      -H "Content-Type: application/json" \
      -d '{"wallet_address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "depth": 3}'

## Interfaces

- API Swagger: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474 (neo4j/REMOVED_DEV_PASSWORD)

## Stack

FastAPI, Neo4j 5.14, Redis 7, PostgreSQL 15, Docker

## Roadmap

- [x] 5 camadas integradas
- [x] Scoring real
- [x] Persistencia Neo4j
- [ ] Frontend React
- [ ] APIs reais (Chainalysis/TRM)
- [ ] Autenticacao JWT

## Aviso

Senhas no docker-compose sao apenas para dev local. Producao usa .env.
