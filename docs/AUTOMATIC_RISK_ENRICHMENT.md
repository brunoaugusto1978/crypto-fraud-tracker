# Automatic Risk Enrichment

## Objetivo

Este pacote adiciona enriquecimento automático de risco para carteiras, reduzindo a dependência de indicadores hardcoded no código Python.

A lógica passa a permitir que fontes externas ou internas alimentem a classificação de carteiras por arquivo JSON configurável via `ADDRESS_INTEL_FILE`.

## Problema resolvido

Antes, uma carteira que não estivesse em `KNOWN_ADDRESSES` podia ser tratada como `unknown` com `risk_level=low`.

Isso é conceitualmente incorreto para investigação AML, porque ausência de match em uma lista local não é evidência de baixo risco.

Agora, quando não há inteligência externa, o endereço pode ser tratado como:

```text
category: unknown
risk_level: unknown
intelligence_status: no_external_label_found
```

## Como funciona

O backend lê um feed JSON de inteligência de endereços definido por:

```env
ADDRESS_INTEL_FILE=/app/data/address_intelligence.example.json
```

Formato esperado:

```json
{
  "source_name": "example_external_watchlist",
  "items": [
    {
      "address": "bc1...",
      "asset": "BTC",
      "category": "scam",
      "label": "Example scam wallet",
      "source_ref": "public reference",
      "confidence": 0.85,
      "first_seen": "2020-07-15"
    }
  ]
}
```

## Fontes futuras

O provider por arquivo prepara o caminho para integrações com:

- OFAC;
- MISP;
- Chainabuse;
- BitcoinAbuse;
- feeds internos;
- provedores comerciais como Chainalysis, TRM e Elliptic.

## Validação executada

```bash
python3 -m compileall backend/app backend/tests
find backend/app backend/tests -name "*.py" -print0 | xargs -0 python3 -m py_compile
docker-compose run --rm -e ADDRESS_INTEL_FILE=/app/data/address_intelligence.example.json backend python -m pytest tests/ -v
```

Resultado:

```text
35 passed
```

## Smoke test funcional

Carteira usada:

```text
bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
```

Resultado esperado:

```text
category: scam
risk_level: high
score: 50
label: Twitter 2020 BTC scam wallet
intelligence_status: matched
```

## Observação

O arquivo `backend/data/address_intelligence.example.json` é um feed de exemplo. Em produção, deve ser substituído por fonte aprovada, versionada e rastreável, como exportação de MISP, OFAC-derived dataset, abuse feed ou provedor comercial.
