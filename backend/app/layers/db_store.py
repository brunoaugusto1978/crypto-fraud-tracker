"""
INVESTIGATION STORE - Persiste investigacoes no PostgreSQL com interface dict-like.
"""
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


class InvestigationStore:
    def __init__(self, postgres_url):
        self.postgres_url = postgres_url
        self._memory = {}
        self._pg_ok = False
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
                    CREATE TABLE IF NOT EXISTS investigations (
                        investigation_id VARCHAR(120) PRIMARY KEY,
                        initial_wallet   VARCHAR(120),
                        overall_risk     REAL,
                        risk_level       VARCHAR(20),
                        suspected_crime  VARCHAR(60),
                        wallets_found    INTEGER,
                        data             JSONB NOT NULL,
                        created_at       TIMESTAMP DEFAULT NOW()
                    )
                """)
            conn.close()
            self._pg_ok = True
            print("[InvestigationStore] PostgreSQL conectado")
        except Exception as e:
            print(f"[InvestigationStore] Postgres indisponivel, usando memoria: {e}")
            self._pg_ok = False

    def __setitem__(self, key, value):
        self._memory[key] = value
        if not self._pg_ok:
            return
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO investigations
                        (investigation_id, initial_wallet, overall_risk,
                         risk_level, suspected_crime, wallets_found, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (investigation_id) DO UPDATE SET
                        initial_wallet = EXCLUDED.initial_wallet,
                        overall_risk = EXCLUDED.overall_risk,
                        risk_level = EXCLUDED.risk_level,
                        suspected_crime = EXCLUDED.suspected_crime,
                        wallets_found = EXCLUDED.wallets_found,
                        data = EXCLUDED.data
                """, (
                    key,
                    value.get("initial_wallet"),
                    (value.get("scoring") or {}).get("overall_risk_score"),
                    (value.get("scoring") or {}).get("risk_level"),
                    (value.get("cluster_analysis") or {}).get("suspected_crime"),
                    len(value.get("wallets", [])),
                    json.dumps(value, default=str),
                ))
            conn.close()
        except Exception as e:
            print(f"[InvestigationStore] erro ao salvar {key}: {e}")

    def __getitem__(self, key):
        if key in self._memory:
            return self._memory[key]
        if self._pg_ok:
            try:
                conn = self._connect()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT data FROM investigations WHERE investigation_id = %s", (key,))
                    row = cur.fetchone()
                conn.close()
                if row:
                    self._memory[key] = row["data"]
                    return row["data"]
            except Exception as e:
                print(f"[InvestigationStore] erro ao ler {key}: {e}")
        raise KeyError(key)

    def __contains__(self, key):
        if key in self._memory:
            return True
        if self._pg_ok:
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM investigations WHERE investigation_id = %s", (key,))
                    exists = cur.fetchone() is not None
                conn.close()
                return exists
            except Exception as e:
                print(f"[InvestigationStore] erro ao verificar {key}: {e}")
        return False

    def list_recent(self, limit=50):
        if not self._pg_ok:
            return [{"investigation_id": k, "initial_wallet": v.get("initial_wallet"),
                     "created_at": v.get("created_at")} for k, v in list(self._memory.items())[-limit:]]
        try:
            conn = self._connect()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT investigation_id, initial_wallet, overall_risk,
                           risk_level, suspected_crime, wallets_found, created_at
                    FROM investigations ORDER BY created_at DESC LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
            conn.close()
            for r in rows:
                if isinstance(r.get("created_at"), datetime):
                    r["created_at"] = r["created_at"].isoformat() + "Z"
            return rows
        except Exception as e:
            print(f"[InvestigationStore] erro ao listar: {e}")
            return []

    def count(self):
        if not self._pg_ok:
            return len(self._memory)
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM investigations")
                n = cur.fetchone()[0]
            conn.close()
            return n
        except Exception:
            return len(self._memory)
