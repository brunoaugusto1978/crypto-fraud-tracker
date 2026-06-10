"""
AUTH - Autenticacao com JWT e usuarios no PostgreSQL.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://crypto_user:REMOVED_DEV_PASSWORD@postgres:5432/crypto_tracker")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        if len(password) < 6:
            raise ValueError("senha deve ter ao menos 6 caracteres")
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
