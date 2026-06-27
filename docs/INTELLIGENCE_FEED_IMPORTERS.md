# Intelligence Feed Importers

## Objetivo

Este pacote adiciona um importador local para converter feeds CSV/JSON de inteligência de carteiras no formato consumido por `ADDRESS_INTEL_FILE`.

Ele permite transformar exportações de fontes internas, MISP, OFAC-derived datasets, abuse feeds ou listas de parceiros em um arquivo compatível com o `FileAddressIntelligenceProvider`.

## Uso

Exemplo com CSV:

```bash
PYTHONPATH=backend python -m app.layers.intelligence_importer \
  --input feeds/input.example.csv \
  --format csv \
  --source-name external_watchlist \
  --output backend/data/address_intelligence.generated.json
```

## Campos aceitos

O importador aceita aliases comuns:

- `address`, `wallet`, `wallet_address`, `btc_address`;
- `asset`, `chain`, `network`;
- `category`, `type`, `tag`;
- `label`, `name`, `description`;
- `source_ref`, `reference`, `url`, `source_url`;
- `confidence`, `score`;
- `first_seen`, `first_seen_at`, `date`, `created_at`;
- `last_seen`, `last_seen_at`, `updated_at`.

## Categorias normalizadas

Categorias aceitas:

- sanctioned;
- ransomware;
- scam;
- fraud;
- darknet;
- mixer;
- gambling;
- marketplace;
- exchange;
- legitimate;
- unknown.

Categorias fora da lista são normalizadas como `unknown`.

## Saída

A saída segue o formato:

```json
{
  "source_name": "external_watchlist",
  "description": "Generated from input.example.csv",
  "generated_at": "...",
  "items": [
    {
      "address": "bc1...",
      "asset": "BTC",
      "category": "scam",
      "label": "Twitter 2020 BTC scam wallet",
      "source_ref": "public incident reference",
      "confidence": 0.85,
      "first_seen": "2020-07-15",
      "last_seen": null,
      "source_name": "external_watchlist",
      "raw_sha256": "...",
      "imported_at": "..."}
  ]
}
```

## Arquivos gerados

Arquivos gerados como `backend/data/address_intelligence.generated.json` não devem ser versionados por padrão, pois contêm timestamps e podem variar a cada execução.

## Validação executada

```bash
docker-compose build backend
docker-compose run --rm -e ADDRESS_INTEL_FILE=/app/data/address_intelligence.generated.json backend python -m pytest tests/ -v
docker-compose run --rm backend python -m pytest tests/test_intelligence_importer.py -v
```

Resultado:

```text
38 passed
3 passed em test_intelligence_importer.py
```
