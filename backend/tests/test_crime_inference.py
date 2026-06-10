"""Testes da inferencia de tipo de crime (camada 4)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.layers.layer4_correlation_engine import ClusterAnalyzer


def test_ransomware_classificado():
    wallets = [{"category": "ransomware"}]
    crime = ClusterAnalyzer._infer_crime_type(wallets, [], [])
    assert crime == "ransomware"

def test_mixer_vira_money_laundering():
    wallets = [{"category": "mixer"}]
    crime = ClusterAnalyzer._infer_crime_type(wallets, [], [])
    assert crime == "money_laundering"

def test_sem_indicio_retorna_indeterminado():
    # Carteira exchange/legitima nao deve virar 'ransomware' por default
    wallets = [{"category": "exchange"}, {"category": "legitimate"}]
    crime = ClusterAnalyzer._infer_crime_type(wallets, [], [])
    assert crime == "indeterminado"

def test_scam_classificado():
    wallets = [{"category": "scam"}]
    crime = ClusterAnalyzer._infer_crime_type(wallets, [], [])
    assert crime == "scam"
