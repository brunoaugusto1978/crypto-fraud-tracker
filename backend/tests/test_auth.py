"""Testes de hash de senha e JWT (sem banco)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.auth import AuthService


def test_hash_e_verify():
    h = AuthService.hash_password("senha123")
    assert h != "senha123"          # nunca texto puro
    assert AuthService.verify_password("senha123", h)
    assert not AuthService.verify_password("errada", h)

def test_hash_diferente_cada_vez():
    # bcrypt usa salt: mesmo input gera hashes diferentes
    h1 = AuthService.hash_password("igual")
    h2 = AuthService.hash_password("igual")
    assert h1 != h2
    assert AuthService.verify_password("igual", h1)
    assert AuthService.verify_password("igual", h2)

def test_jwt_cria_e_decodifica():
    token = AuthService.create_token("bruno", "admin")
    payload = AuthService.decode_token(token)
    assert payload is not None
    assert payload["sub"] == "bruno"
    assert payload["role"] == "admin"

def test_jwt_invalido_retorna_none():
    assert AuthService.decode_token("token.invalido.aqui") is None
