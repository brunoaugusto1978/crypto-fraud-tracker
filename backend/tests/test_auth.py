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


# ---- Testes da politica de senha forte ----
from app.auth import validate_password_strength


def test_senha_forte_aceita():
    ok, erro = validate_password_strength("Senha@Forte123")
    assert ok is True
    assert erro is None

def test_senha_curta_rejeitada():
    ok, erro = validate_password_strength("Ab@1cd")
    assert ok is False

def test_senha_sem_maiuscula_rejeitada():
    ok, erro = validate_password_strength("senha@forte123")
    assert ok is False

def test_senha_sem_numero_rejeitada():
    ok, erro = validate_password_strength("SenhaForte@abc")
    assert ok is False

def test_senha_sem_especial_rejeitada():
    ok, erro = validate_password_strength("SenhaForte1234")
    assert ok is False
