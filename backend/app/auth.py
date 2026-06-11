"""
AUTH - Autenticacao com JWT e usuarios no PostgreSQL.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError

POSTGRES_URL = os.getenv("POSTGRES_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# Fail-safe: nao permitir subir com segredos ausentes ou inseguros.
_INSECURE_DEFAULTS = {"", "dev-secret-change-me", "change-me", "secret"}
if not JWT_SECRET or JWT_SECRET in _INSECURE_DEFAULTS:
    raise RuntimeError(
        "JWT_SECRET ausente ou inseguro. Defina um valor forte no .env "
        "(ex: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\")."
    )
if not POSTGRES_URL:
    raise RuntimeError("POSTGRES_URL ausente. Defina a conexao do banco no .env.")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


import re


def validate_password_strength(password: str):
    """Valida forca da senha. Retorna (ok: bool, erro: str|None)."""
    if len(password) < 12:
        return False, "senha deve ter ao menos 12 caracteres"
    if not re.search(r"[A-Z]", password):
        return False, "senha deve conter ao menos uma letra maiuscula"
    if not re.search(r"[a-z]", password):
        return False, "senha deve conter ao menos uma letra minuscula"
    if not re.search(r"[0-9]", password):
        return False, "senha deve conter ao menos um numero"
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "senha deve conter ao menos um caractere especial"
    return True, None


class AuthService:
    def __init__(self, postgres_url=POSTGRES_URL):
        self.postgres_url = postgres_url
        self._init_table()

    def _connect(self):
        conn = psycopg2.connect(self.postgres_url)
        conn.autocommit = True
        return conn

    def _init_table(self):
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id           SERIAL PRIMARY KEY,
                        username     VARCHAR(80) UNIQUE NOT NULL,
                        email        VARCHAR(160) UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        role         VARCHAR(20) DEFAULT 'analyst',
                        created_at   TIMESTAMP DEFAULT NOW()
                    )
                """)
            conn.close()
            print("[AuthService] tabela users pronta")
        except Exception as e:
            print(f"[AuthService] erro ao criar tabela users: {e}")

    @staticmethod
    def hash_password(password):
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain, hashed):
        return pwd_context.verify(plain, hashed)

    def create_user(self, username, password, email=None, role="analyst"):
        if len(username) < 3:
            raise ValueError("username deve ter ao menos 3 caracteres")
        ok, erro = validate_password_strength(password)
        if not ok:
            raise ValueError(erro)
        pwd_hash = self.hash_password(password)
        try:
            conn = self._connect()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, username, email, role, created_at
                """, (username, email, pwd_hash, role))
                user = cur.fetchone()
            conn.close()
            return dict(user)
        except psycopg2.errors.UniqueViolation:
            raise ValueError("username ou email ja existe")

    def get_user(self, username):
        conn = self._connect()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
        conn.close()
        return dict(user) if user else None

    def authenticate(self, username, password):
        user = self.get_user(username)
        if not user:
            return None
        if not self.verify_password(password, user["password_hash"]):
            return None
        return user

    def count_users(self):
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            n = cur.fetchone()[0]
        conn.close()
        return n

    # ---- gerenciamento de conta propria ----
    def update_email(self, username, new_email):
        try:
            conn = self._connect()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    UPDATE users SET email = %s WHERE username = %s
                    RETURNING id, username, email, role, created_at
                """, (new_email, username))
                user = cur.fetchone()
            conn.close()
            return dict(user) if user else None
        except psycopg2.errors.UniqueViolation:
            raise ValueError("email ja esta em uso")

    def change_password(self, username, current_password, new_password):
        # Verifica a senha atual
        user = self.get_user(username)
        if not user:
            raise ValueError("usuario nao encontrado")
        if not self.verify_password(current_password, user["password_hash"]):
            raise ValueError("senha atual incorreta")
        # Valida a nova senha
        ok, erro = validate_password_strength(new_password)
        if not ok:
            raise ValueError(erro)
        new_hash = self.hash_password(new_password)
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password_hash = %s WHERE username = %s",
                        (new_hash, username))
        conn.close()
        return True

    # ---- gerenciamento de usuarios (admin) ----
    def list_users(self):
        conn = self._connect()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, username, email, role, created_at
                FROM users ORDER BY created_at ASC
            """)
            rows = cur.fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            result.append(d)
        return result

    def update_role(self, user_id, new_role):
        if new_role not in ("admin", "analyst"):
            raise ValueError("role invalido (use admin ou analyst)")
        conn = self._connect()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE users SET role = %s WHERE id = %s
                RETURNING id, username, email, role
            """, (new_role, user_id))
            user = cur.fetchone()
        conn.close()
        return dict(user) if user else None

    def delete_user(self, user_id):
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
            deleted = cur.fetchone()
        conn.close()
        return deleted is not None

    def count_admins(self):
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            n = cur.fetchone()[0]
        conn.close()
        return n

    @staticmethod
    def create_token(username, role="analyst"):
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
        payload = {"sub": username, "role": role, "exp": expire}
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_token(token):
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError:
            return None
