# Real Intelligence Sources

## Objetivo

Este pacote adiciona o primeiro importador de fonte real/local de inteligência: um importador OFAC-derived baseado em CSV local.

O desenho é offline-first: a aplicação não consulta fontes externas durante a investigação. Em vez disso, uma exportação local e auditável é convertida para o formato consumido por `ADDRESS_INTEL_FILE`.

## Fluxo

```text
OFAC-derived CSV/local export
→ ofac_importer.py
→ address_intelligence.ofac.generated.json
→ ADDRESS_INTEL_FILE
→ automatic wallet risk enrichment
```

## Uso

```bash
PYTHONPATH=backend python - <<PY
from app.layers.source_importers.ofac_importer import import_ofac_derived_csv

import_ofac_derived_csv(
    input_path="feeds/ofac_derived.example.csv",
    output_path="backend/data/address_intelligence.ofac.generated.json",
    source_name="ofac_derived_example",
)
PY
```

## Entrada esperada

Campos aceitos pelo importador:

- `address`, `wallet`, `wallet_address`, `btc_address`;
- `digital_currency_address`, `digitalCurrencyAddress`, `crypto_address`;
- `asset`, `chain`, `network`, `currency`;
- `name`, `sdn_name`, `entity_name`, `label`, `description`;
- `source_ref`, `reference`, `url`, `source_url`, `sdn_id`, `uid`, `program`.

## Saída

O importador normaliza registros para:

```text
category: sanctioned
confidence: 1.0
source_name: ofac_derived
raw_sha256: hash do payload original
```

## Arquivos gerados

Arquivos como `backend/data/address_intelligence.ofac.generated.json` não devem ser versionados por padrão, porque contêm timestamps e podem variar a cada execução.

## Validação executada

```bash
python3 -m compileall backend/app backend/tests
find backend/app backend/tests -name "*.py" -print0 | xargs -0 python3 -m py_compile
docker-compose build backend
docker-compose run --rm backend python -m pytest tests/test_ofac_importer.py -v
docker-compose run --rm -e ADDRESS_INTEL_FILE=/app/data/address_intelligence.example.json backend python -m pytest tests/ -v
```

Resultado:

```text
2 passed em test_ofac_importer.py
40 passed na suíte completa
```
