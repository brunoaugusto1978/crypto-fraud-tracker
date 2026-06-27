# AML Investigation Hardening

## Objetivo

Este pacote melhora o Crypto Fraud Tracker para uso investigativo em cenários de fraude cripto e lavagem de dinheiro, com foco em qualidade da evidência, rastreabilidade, controle de acesso e integridade dos dados on-chain.

## Principais mudanças

### 1. Remoção de transações sintéticas

O fluxo de investigação deixa de construir transações artificiais com valores e timestamps simulados. A investigação passa a usar transações retornadas pelo provider de blockchain intelligence.

### 2. Preservação de evidência

Foi adicionada estrutura para preservar evidências com:

- payload bruto;
- hash SHA-256;
- fonte;
- URL de origem;
- usuário coletor;
- timestamp de coleta;
- versão do algoritmo.

### 3. Modelo Bitcoin/UTXO mais fiel

O provider passa a preservar inputs, outputs e transfers, permitindo análises futuras de:

- peel chain;
- fan-in;
- fan-out;
- layering;
- mixer exposure;
- cash-out.

### 4. Controle de acesso por investigação

Investigações passam a ter owner e escopo de leitura. Usuários com papel analyst acessam apenas suas próprias investigações, enquanto admin pode consultar todas.

### 5. Endpoints sensíveis protegidos

Endpoints de submissão de IOC, regras de risco e status de fila passam a exigir autenticação e, quando necessário, papel admin.

### 6. Relatório HTML seguro

Campos dinâmicos usados no relatório HTML passam por escaping para reduzir risco de XSS em dados vindos de fontes externas.

### 7. Tipologias AML iniciais

Foram adicionadas tipologias iniciais para:

- fan-in/fan-out;
- exposição direta a mixer;
- candidato a cash-out em exchange;
- layering ou peel chain.

## Validação executada

```bash
python3 -m compileall backend/app backend/tests
find backend/app backend/tests -name "*.py" -print0 | xargs -0 python3 -m py_compile
docker-compose build
docker-compose up -d
curl http://localhost:8002/api/v1/health
docker-compose exec backend python -m pytest tests/ -v
docker-compose exec backend python -m pytest tests/test_aml_hardening.py -v
```

Resultado:

```text
31 passed
3 passed em test_aml_hardening.py
```

## Observação de ambiente local

A validação local usou a porta 8002 porque a porta 8000 já estava ocupada por outro projeto local. Essa alteração de porta foi usada apenas para teste e não deve ser versionada no PR.

## Próximas etapas recomendadas

- ingestão de watchlists/OFAC;
- integração MISP;
- workflow formal de caso;
- exportação de dossiê investigativo;
- trilha de auditoria imutável;
- classificação de entidades;
- integração com datasets sintéticos como SantanderAI/gen-fraud-graph.
