"""
INVESTIGATION STORE - Persiste investigacoes e evidencias no PostgreSQL.
"""
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


class InvestigationStore:
    def __init__(self, postgres_url):
        self.postgres_url = postgres_url
        self._memory = {}
        self._evidence_memory = {}
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
                        case_name        VARCHAR(180),
                        owner_username   VARCHAR(80) NOT NULL DEFAULT 'system',
                        overall_risk     REAL,
                        risk_level       VARCHAR(20),
                        suspected_crime  VARCHAR(60),
                        wallets_found    INTEGER,
                        evidence_count   INTEGER DEFAULT 0,
                        data             JSONB NOT NULL,
                        created_at       TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("ALTER TABLE investigations ADD COLUMN IF NOT EXISTS case_name VARCHAR(180)")
                cur.execute("ALTER TABLE investigations ADD COLUMN IF NOT EXISTS owner_username VARCHAR(80) NOT NULL DEFAULT 'system'")
                cur.execute("ALTER TABLE investigations ADD COLUMN IF NOT EXISTS evidence_count INTEGER DEFAULT 0")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS evidence_records (
                        id SERIAL PRIMARY KEY,
                        investigation_id VARCHAR(120) NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
                        evidence_type VARCHAR(50) NOT NULL,
                        source_name VARCHAR(80) NOT NULL,
                        source_url TEXT,
                        subject TEXT NOT NULL,
                        raw_payload JSONB NOT NULL,
                        raw_sha256 CHAR(64) NOT NULL,
                        collected_by VARCHAR(80) NOT NULL,
                        collected_at TIMESTAMP DEFAULT NOW(),
                        algorithm_version VARCHAR(40),
                        UNIQUE (investigation_id, raw_sha256)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_investigations_owner_created ON investigations(owner_username, created_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_evidence_investigation ON evidence_records(investigation_id)")
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
                        (investigation_id, initial_wallet, case_name, owner_username,
                         overall_risk, risk_level, suspected_crime, wallets_found,
                         evidence_count, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (investigation_id) DO UPDATE SET
                        initial_wallet = EXCLUDED.initial_wallet,
                        case_name = EXCLUDED.case_name,
                        owner_username = EXCLUDED.owner_username,
                        overall_risk = EXCLUDED.overall_risk,
                        risk_level = EXCLUDED.risk_level,
                        suspected_crime = EXCLUDED.suspected_crime,
                        wallets_found = EXCLUDED.wallets_found,
                        evidence_count = EXCLUDED.evidence_count,
                        data = EXCLUDED.data
                """, (
                    key,
                    value.get("initial_wallet"),
                    value.get("case_name"),
                    value.get("owner_username", "system"),
                    (value.get("scoring") or {}).get("overall_risk_score"),
                    (value.get("scoring") or {}).get("risk_level"),
                    (value.get("cluster_analysis") or {}).get("suspected_crime"),
                    len(value.get("wallets", [])),
                    len(value.get("evidence_records", [])),
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

    @staticmethod
    def _can_access(inv: dict, username: str, role: str) -> bool:
        return role == "admin" or inv.get("owner_username") == username

    def get_for_user(self, investigation_id: str, username: str, role: str):
        try:
            inv = self[investigation_id]
        except KeyError:
            return None
        if self._can_access(inv, username, role):
            return inv
        return None

    def list_recent(self, limit=50, username=None, role="analyst"):
        limit = max(1, min(int(limit), 200))
        if not self._pg_ok:
            rows = []
            for k, v in list(self._memory.items())[-limit:]:
                if username and not self._can_access(v, username, role):
                    continue
                rows.append({
                    "investigation_id": k,
                    "initial_wallet": v.get("initial_wallet"),
                    "case_name": v.get("case_name"),
                    "owner_username": v.get("owner_username"),
                    "overall_risk": (v.get("scoring") or {}).get("overall_risk_score"),
                    "risk_level": (v.get("scoring") or {}).get("risk_level"),
                    "suspected_crime": (v.get("cluster_analysis") or {}).get("suspected_crime"),
                    "wallets_found": len(v.get("wallets", [])),
                    "evidence_count": len(v.get("evidence_records", [])),
                    "created_at": v.get("created_at"),
                })
            return rows
        try:
            conn = self._connect()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if role == "admin" or not username:
                    cur.execute("""
                        SELECT investigation_id, initial_wallet, case_name, owner_username,
                               overall_risk, risk_level, suspected_crime, wallets_found,
                               evidence_count, created_at
                        FROM investigations ORDER BY created_at DESC LIMIT %s
                    """, (limit,))
                else:
                    cur.execute("""
                        SELECT investigation_id, initial_wallet, case_name, owner_username,
                               overall_risk, risk_level, suspected_crime, wallets_found,
                               evidence_count, created_at
                        FROM investigations
                        WHERE owner_username = %s
                        ORDER BY created_at DESC LIMIT %s
                    """, (username, limit))
                rows = cur.fetchall()
            conn.close()
            for r in rows:
                if isinstance(r.get("created_at"), datetime):
                    r["created_at"] = r["created_at"].isoformat() + "Z"
            return rows
        except Exception as e:
            print(f"[InvestigationStore] erro ao listar: {e}")
            return []

    def count(self, username=None, role="analyst"):
        if not self._pg_ok:
            if not username or role == "admin":
                return len(self._memory)
            return sum(1 for inv in self._memory.values() if self._can_access(inv, username, role))
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                if role == "admin" or not username:
                    cur.execute("SELECT COUNT(*) FROM investigations")
                    n = cur.fetchone()[0]
                else:
                    cur.execute("SELECT COUNT(*) FROM investigations WHERE owner_username = %s", (username,))
                    n = cur.fetchone()[0]
            conn.close()
            return n
        except Exception:
            return len(self._memory)

    def save_evidence_records(self, investigation_id: str, evidence_records: list):
        self._evidence_memory[investigation_id] = evidence_records
        if not self._pg_ok or not evidence_records:
            return
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                for ev in evidence_records:
                    cur.execute("""
                        INSERT INTO evidence_records
                            (investigation_id, evidence_type, source_name, source_url,
                             subject, raw_payload, raw_sha256, collected_by,
                             collected_at, algorithm_version)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (investigation_id, raw_sha256) DO NOTHING
                    """, (
                        investigation_id,
                        ev.get("evidence_type"),
                        ev.get("source_name"),
                        ev.get("source_url"),
                        ev.get("subject"),
                        json.dumps(ev.get("raw_payload"), default=str),
                        ev.get("raw_sha256"),
                        ev.get("collected_by"),
                        ev.get("collected_at"),
                        ev.get("algorithm_version"),
                    ))
            conn.close()
        except Exception as e:
            print(f"[InvestigationStore] erro ao salvar evidencias {investigation_id}: {e}")
