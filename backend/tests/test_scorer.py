"""Testes do scoring de investigacao."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.layers.investigation_scorer import InvestigationScorer

scorer = InvestigationScorer()


def test_ransomware_nao_dilui():
    # Carteira ransomware + 9 legitimas: score NAO deve cair para media
    wallets = ['w0'] + [f'w{i}' for i in range(1, 10)]
    enr = {'w0': {'category': 'ransomware'}}
    enr.update({f'w{i}': {'category': 'legitimate'} for i in range(1, 10)})
    scores = [{'wallet': 'w0', 'risk_score': 50}]
    scores += [{'wallet': f'w{i}', 'risk_score': 0} for i in range(1, 10)]
    r = scorer.score_investigation('w0', wallets, enr, scores)
    assert r['overall_risk_score'] == 50
    assert r['risk_level'] == 'high'

def test_fundos_para_mixer_eleva_risco():
    r = scorer.score_investigation('v', ['v', 'm'],
        {'v': {'category': 'unknown'}, 'm': {'category': 'mixer'}},
        [{'wallet': 'v', 'risk_score': 10}, {'wallet': 'm', 'risk_score': 30}])
    assert r['overall_risk_score'] == 80
    assert r['risk_level'] == 'critical'
    assert len(r['dangerous_destinations']) == 1

def test_carteira_legitima_baixo_risco():
    r = scorer.score_investigation('c', ['c'],
        {'c': {'category': 'legitimate'}},
        [{'wallet': 'c', 'risk_score': 0}])
    assert r['risk_level'] == 'low'

def test_niveis_de_risco():
    assert InvestigationScorer._level(85) == 'critical'
    assert InvestigationScorer._level(50) == 'high'
    assert InvestigationScorer._level(25) == 'medium'
    assert InvestigationScorer._level(10) == 'low'
