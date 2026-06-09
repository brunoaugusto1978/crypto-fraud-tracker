"""
CAMADA 3: GRAPH DATABASE (Neo4j) - Versão Corrigida
Driver síncrono compatível com Neo4j 5.x
"""

from typing import List, Dict, Optional
from neo4j import GraphDatabase
from datetime import datetime


class Neo4jConnection:
    """Gerencia conexão síncrona com Neo4j (compatível com 5.x)"""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

    def connect(self):
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.driver.verify_connectivity()
        return True

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        if parameters is None:
            parameters = {}
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [dict(record) for record in result]


class GraphDatabaseService:
    def __init__(self, connection: Neo4jConnection):
        self.conn = connection

    def add_wallet(self, address, category='unknown', risk_level='low', risk_score=0.0):
        query = """
        MERGE (w:Wallet {address: $address})
        SET w.category = $category, w.risk_level = $risk_level,
            w.risk_score = $risk_score, w.updated_at = datetime()
        """
        self.conn.run_query(query, {'address': address, 'category': category,
                                     'risk_level': risk_level, 'risk_score': risk_score})

    def add_transaction(self, from_address, to_address, amount_btc, txid=None, timestamp=None):
        if txid is None:
            txid = f"tx_{datetime.utcnow().timestamp()}"
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat() + 'Z'
        self.add_wallet(from_address)
        self.add_wallet(to_address)
        query = """
        MATCH (from:Wallet {address: $from_address})
        MATCH (to:Wallet {address: $to_address})
        MERGE (from)-[r:SENDS_TO {txid: $txid}]->(to)
        SET r.amount_btc = $amount_btc, r.timestamp = $timestamp
        """
        self.conn.run_query(query, {'from_address': from_address, 'to_address': to_address,
                                     'amount_btc': amount_btc, 'txid': txid, 'timestamp': timestamp})

    def find_recipients(self, address, depth=3):
        query = f"""
        MATCH path = (start:Wallet {{address: $address}})-[:SENDS_TO*1..{depth}]->(recipient:Wallet)
        RETURN DISTINCT recipient.address AS address, recipient.category AS category,
                        recipient.risk_score AS risk_score, length(path) AS hops
        ORDER BY hops LIMIT 100
        """
        return self.conn.run_query(query, {'address': address})

    def get_wallet_stats(self, address):
        sent = self.conn.run_query("""
            MATCH (w:Wallet {address: $address})-[r:SENDS_TO]->()
            RETURN count(r) AS count, sum(r.amount_btc) AS total
        """, {'address': address})
        received = self.conn.run_query("""
            MATCH ()-[r:SENDS_TO]->(w:Wallet {address: $address})
            RETURN count(r) AS count, sum(r.amount_btc) AS total
        """, {'address': address})
        return {'wallet': address,
                'sent': sent[0] if sent else {'count': 0, 'total': 0},
                'received': received[0] if received else {'count': 0, 'total': 0}}

    def get_high_risk_wallets(self, min_score=50):
        query = """
        MATCH (w:Wallet) WHERE w.risk_score >= $min_score
        RETURN w.address AS address, w.category AS category,
               w.risk_level AS risk_level, w.risk_score AS risk_score
        ORDER BY w.risk_score DESC LIMIT 100
        """
        return self.conn.run_query(query, {'min_score': min_score})

    def clear_all(self):
        self.conn.run_query("MATCH (n) DETACH DELETE n")
