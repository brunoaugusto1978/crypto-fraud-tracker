"""Testes do validador de enderecos Bitcoin (camada 1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.layers.layer1_ioc_intake import IOCValidator


def test_aceita_p2pkh_valido():
    # Genesis do Satoshi (com minusculas - o bug que corrigimos)
    assert IOCValidator.validate_bitcoin_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")

def test_aceita_bech32_valido():
    assert IOCValidator.validate_bitcoin_address("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")

def test_aceita_wannacry_real():
    assert IOCValidator.validate_bitcoin_address("13AM4VW2dhxYgXeQepoHkHSQuy6NgaEb94")

def test_rejeita_vazio():
    assert not IOCValidator.validate_bitcoin_address("")

def test_rejeita_caracteres_invalidos():
    # '0', 'O', 'I', 'l' nao existem no Base58
    assert not IOCValidator.validate_bitcoin_address("10OIl1234567890123456789012345")

def test_rejeita_muito_curto():
    assert not IOCValidator.validate_bitcoin_address("1ABC")
