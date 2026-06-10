"""Testes da lista de IOCs conhecidos (classificacao)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.layers.layer2_blockstream import BlockstreamIntelligence, KNOWN_ADDRESSES


def test_tem_iocs_carregados():
    # Deve haver pelo menos os 5 IOCs (3 WannaCry + 2 SamSam)
    assert len(KNOWN_ADDRESSES) >= 5

def test_wannacry_classificado_como_ransomware():
    prov = BlockstreamIntelligence()
    cls = prov._classify("13AM4VW2dhxYgXeQepoHkHSQuy6NgaEb94")
    assert cls["category"] == "ransomware"
    assert cls["risk_level"] == "critical"
    assert cls["label"] == "WannaCry"

def test_samsam_ofac_classificado():
    prov = BlockstreamIntelligence()
    cls = prov._classify("149w62rY42aZBox8fGcmqNsXUzSStKeq8C")
    assert cls["category"] == "ransomware"
    assert "SamSam" in cls["label"]

def test_endereco_desconhecido_e_unknown():
    prov = BlockstreamIntelligence()
    cls = prov._classify("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", tx_count=10)
    assert cls["category"] == "unknown"

def test_alto_volume_vira_exchange_heuristica():
    prov = BlockstreamIntelligence()
    cls = prov._classify("1QualquerEndereco", tx_count=9999)
    assert cls["category"] == "exchange"
