import json

from app.layers.source_importers.ofac_importer import (
    import_ofac_derived_csv,
    normalize_ofac_record,
)


BTC_WALLET = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"


def test_normalize_ofac_record_maps_to_sanctioned():
    record = {
        "digital_currency_address": BTC_WALLET,
        "currency": "BTC",
        "sdn_name": "Example Sanctioned Entity",
        "program": "EXAMPLE",
        "first_seen": "2024-01-01",
    }

    item = normalize_ofac_record(record)

    assert item["address"] == BTC_WALLET
    assert item["asset"] == "BTC"
    assert item["category"] == "sanctioned"
    assert item["label"] == "Example Sanctioned Entity"
    assert item["source_ref"] == "EXAMPLE"
    assert item["confidence"] == 1.0
    assert len(item["raw_sha256"]) == 64


def test_import_ofac_derived_csv_deduplicates(tmp_path):
    src = tmp_path / "ofac.csv"
    dst = tmp_path / "address_intelligence.ofac.json"

    src.write_text(
        "digital_currency_address,currency,sdn_name,program,first_seen\n"
        f"{BTC_WALLET},BTC,Example Sanctioned Entity,EXAMPLE,2024-01-01\n"
        f"{BTC_WALLET},BTC,Example Sanctioned Entity,EXAMPLE,2024-01-01\n",
        encoding="utf-8",
    )

    output = import_ofac_derived_csv(
        input_path=str(src),
        output_path=str(dst),
        source_name="ofac_derived_test",
    )

    assert dst.exists()
    assert output["source_name"] == "ofac_derived_test"
    assert len(output["items"]) == 1
    assert output["items"][0]["category"] == "sanctioned"

    saved = json.loads(dst.read_text(encoding="utf-8"))
    assert saved["items"][0]["address"] == BTC_WALLET
