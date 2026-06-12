# Crypto Fraud Tracker

Sistema full-stack de rastreamento de fraudes em Bitcoin com arquitetura de 5 camadas, autenticacao JWT, dados reais da blockchain e dashboard interativo.

## Status: v3.0 - autenticado, testado e com dados reais

Sistema completo: rastreia movimentacoes reais de Bitcoin, classifica carteiras por categoria de risco (ransomware, mixer, exchange, etc), persiste investigacoes e visualiza tudo em um dashboard com grafo interativo. Protegido por autenticacao JWT com controle de acesso por papel (admin/analyst).

## Arquitetura de 5 Camadas

```
LOGIN (JWT)
    |
FRONTEND (React + D3)  -- localhost:3000
    |  token em cada chamada
BACKEND (FastAPI)      -- localhost:8000
  1. IOC Intake        -> Redis (validacao/fila)
  2. Blockchain Intel  -> Blockstream API (dados reais) ou mock
  3. Graph Database    -> Neo4j (persistencia do grafo)
  4. Correlation       -> Scoring de risco (0-100)
  5. Report Generation -> Timeline + Grafo + HTML
    |
PostgreSQL (investigacoes + usuarios) + Neo4j (grafo) + Redis (cache)
```
## Funcionalidades

- Rastreamento de cadeia de transacoes Bitcoin (dados reais via Blockstream)
- Scoring de risco inteligente (sem diluicao: max de inicial/ponderado/propagacao)
- Classificacao de carteiras: ransomware, scam, darknet, mixer, exchange, etc
- Lista de IOCs reais (WannaCry, SamSam/OFAC) + heuristica
- Deteccao de destinos perigosos na cadeia de fundos
- Persistencia de investigacoes (sobrevivem a restart)
- Dashboard com grafo de forca interativo (zoom, pan, destaque da carteira)
- Historico de investigacoes (reabrir investigacoes anteriores)
- Autenticacao JWT + controle de acesso (admin/analyst)

## Pre-requisitos

- WSL2 (Windows) ou Linux
- Docker 27+ e Docker Compose 2.32+
- Acesso a internet (para a API Blockstream)

## Instalacao

### 1. Clonar e configurar o .env

```bash
git clone https://github.com/SEU_USUARIO/crypto-fraud-tracker.git
cd crypto-fraud-tracker
```

Crie um arquivo .env na raiz (NAO versionar) com as variaveis: POSTGRES_*, NEO4J_*, REDIS_*, INTEL_PROVIDER, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, ALLOWED_ORIGINS e ENV.

Gere o JWT_SECRET com:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

O backend NAO sobe sem JWT_SECRET, POSTGRES_URL e NEO4J_PASSWORD (fail-safe).

### 2. Subir

```bash
docker-compose build
docker-compose up -d
docker-compose ps
```

### 3. Criar o primeiro usuario (vira admin automaticamente)

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SuaSenha@Forte123"}'
```

O primeiro usuario vira admin (bootstrap). Os demais exigem um admin autenticado.

### 4. Acessar

- Dashboard: http://localhost:3000 (faca login)
- API (dev): http://localhost:8000/docs

## Testes

```bash
docker-compose exec backend python -m pytest tests/ -v
```

28 testes: validador Base58, scoring, classificacao de crime, IOCs, hash bcrypt, JWT e politica de senha.

## Seguranca

- Senhas armazenadas com hash bcrypt e salt único;
- JWT com expiração e segredo obrigatório via .env;
- Política de senha forte, exigindo 12+ caracteres, maiúscula, minúscula, número e caractere especial;
- Controle de acesso por papel, com perfis admin e analyst;
- Registro de novos usuários restrito a administradores após o bootstrap inicial;
- Rotas de dados protegidas por token;
- Uso de queries PostgreSQL parametrizadas para mitigação de SQL injection;
- CORS restrito, sem uso de credentials, utilizando header Authorization;
- Bancos configurados para comunicação pela rede interna do Docker;
- Limite de profundidade nas consultas para reduzir risco de abuso e DoS lógico;
- Swagger e ReDoc desabilitados em produção quando ENV=prod;
- Segredos mantidos fora do código-fonte, com .env não versionado.

### Production Checklist

- [ ] ENV=prod no .env (esconde Swagger/ReDoc)
- [ ] Senhas fortes e unicas para Postgres/Neo4j
- [ ] JWT_SECRET rotacionado (48+ bytes)
- [ ] ALLOWED_ORIGINS apontando para o dominio real (https)
- [ ] HTTPS/TLS via reverse proxy (nginx/traefik/caddy)
- [ ] Rate limiting no backend ou no proxy
- [ ] Backups automaticos dos volumes
- [ ] Logs centralizados e monitoramento
- [ ] Revisar expiracao do JWT
- [ ] Considerar refresh tokens

## Stack

- Backend: FastAPI, Python 3.10, Uvicorn
- Bancos: Neo4j 5.14, Redis 7, PostgreSQL 15
- Frontend: React 18 + D3.js v7 (CDN), nginx
- Auth: python-jose (JWT), passlib + bcrypt
- Dados: Blockstream Esplora API
- DevOps: Docker, Docker Compose

## Aviso Legal

Esta ferramenta é disponibilizada para fins legítimos de compliance, detecção de fraude, OSINT, investigação autorizada, pesquisa em segurança e apoio analítico. O uso deve respeitar a legislação aplicável, políticas institucionais, privacidade, proteção de dados e cadeia de custódia quando aplicável.

O projeto não realiza atribuição automática de autoria, não substitui análise pericial formal e não deve ser utilizado para perseguição, exposição indevida de pessoas, acesso não autorizado ou qualquer finalidade ilícita.

## Licenca

Este projeto está licenciado sob a Apache License 2.0.

A redistribuição, uso, modificação e integração em outras plataformas são permitidos nos termos da licença, desde que sejam preservados os avisos de copyright, os créditos do autor, a referência ao projeto original e o arquivo de licença correspondente.

Consulte o arquivo LICENSE para mais detalhes.

---
Versao: 3.0.0 | Autenticado, testado (28 testes) e com dados reais da blockchain
