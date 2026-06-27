import json

from app.layers.intelligence_importer import import_feed, normalize_record


TWITTER_2020_WALLET = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"


def test_normalize_record_supports_aliases():
    record = {
        "wallet_address": TWITTER_2020_WALLET,
        "type": "scam",
        "name": "Twitter 2020 BTC scam wallet",
        "url": "public-reference",
        "confidence": "85",
        "date": "2020-07-15",
    }

    item = normalize_record(record, source_name="unit_test_feed")

    assert item["address"] == TWITTER_2020_WALLET
    assert item["asset"] == "BTC"
    assert item["category"] == "scam"
    assert item["label"] == "Twitter 2020 BTC scam wallet"
    assert item["source_ref"] == "public-reference"
    assert item["confidence"] == 0.85
    assert len(item["raw_sha256"]) == 64


def test_import_csv_feed(tmp_path):
    src = tmp_path / "input.csv"
    dst = tmp_path / "address_intelligence.generated.json"

    src.write_text(
        "address,asset,category,label,source_ref,confidence,first_seen\n"
        f"{TWITTER_2020_WALLET},BTC,scam,Twitter 2020 BTC scam wallet,public-reference,0.85,2020-07-15\n",
        encoding="utf-8",
    )

    output = import_feed(
        input_path=str(src),
        input_format="csv",
        source_name="unit_csv_feed",
        output_path=str(dst),
    )

    assert dst.exists()
    assert output["source_name"] == "unit_csv_feed"
    assert len(output["items"]) == 1
    assert output["items"][0]["category"] == "scam"

    saved = json.loads(dst.read_text(encoding="utf-8"))
    assert saved["items"][0]["address"] == TWITTER_2020_WALLET


def test_import_json_feed_deduplicates(tmp_path):
    src = tmp_path / "input.json"
    dst = tmp_path / "address_intelligence.generated.json"

    src.write_text(
        json.dumps({
            "items": [
                {
                    "address": TWITTER_2020_WALLET,
                    "asset": "BTC",
                    "category": "scam",
                    "label": "Twitter 2020 BTC scam wallet",
                    "confidence": 0.85,
                },
                {
                    "address": TWITTER_2020_WALLET,
                    "asset": "BTC",
                    "category": "scam",
                    "label": "Twitter 2020 BTC scam wallet",
                    "confidence": 0.85,
                },
            ]
        }),
        encoding="utf-8",
    )

    output = import_feed(
        input_path=str(src),
        input_format="json",
        source_name="unit_json_feed",
        output_path=str(dst),
    )

    assert len(output["items"]) == 1
    assert output["items"][0]["source_name"] == "unit_json_feed"
