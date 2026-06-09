"""
CAMADA 3: GRAPH DATABASE (Neo4j)
Responsável por:
- Armazenar wallets e transações em grafo
- Modelar relacionamentos complexos
- Executar queries de traçado
- Detectar clusters automaticamente
"""

from typing import List, Dict, Optional, Tuple
from neo4j import AsyncDriver, async_driver
from datetime import datetime

# ============================================================================
# CYPHER QUERIES (Neo4j)
# ============================================================================

CYPHER_QUERIES = {
    # Criar nós
    'create_wallet': '''
    MERGE (w:Wallet {address: $address})
    SET w.category = $category,
        w.risk_level = $risk_level,
        w.updated_at = datetime()
    RETURN w
    ''',
    
    'create_transaction': '''
    MATCH (from:Wallet {address: $from_address})
    MATCH (to:Wallet {address: $to_address})
    CREATE (tx:Transaction {
        txid: $txid,
        amount_btc: $amount_btc,
        timestamp: $timestamp,
        confirmations: $confirmations
    })
    CREATE (from)-[:SENDS]->(tx)
    CREATE (tx)-[:SENDS_TO]->(to)
    RETURN tx
    ''',
    
    'link_wallets': '''
    MATCH (from:Wallet {address: $from_address})
    MATCH (to:Wallet {address: $to_address})
    MERGE (from)-[r:TRANSACTION]->(to)
    SET r.count = COALESCE(r.count, 0) + 1,
        r.total_btc = COALESCE(r.total_btc, 0) + $amount_btc
    RETURN r
    ''',
    
    # Queries de análise
    'find_direct_recipients': '''
    MATCH (w:Wallet {address: $address})-[:SENDS_TO]->(tx:Transaction)-[:SENDS_TO]->(recipient:Wallet)
    RETURN DISTINCT recipient.address AS address, recipient.category AS category
    LIMIT 100
    ''',
    
    'find_all_recipients_depth_n': '''
    MATCH path = (start:Wallet {address: $start_address})-[:SENDS_TO*1..$depth]->(recipient:Wallet)
    RETURN DISTINCT recipient.address AS address, 
                    recipient.category AS category,
                    length(path) AS hops
    LIMIT 1000
    ''',
    
    'find_wallet_cluster': '''
    MATCH (w:Wallet {address: $address})
    CALL apoc.path.spanningTree(w, {
        relationshipFilter: "TRANSACTION>",
        minLevel: 1,
        maxLevel: $depth
    })
    YIELD path
    WITH nodes(path) AS nodes
    RETURN DISTINCT nodes
    ''',
    
    'find_converging_wallets': '''
    MATCH (w:Wallet)-[:TRANSACTION]->(convergence:Wallet)
    WHERE convergence.address = $target_address
    RETURN w.address AS sender, 
           count(*) AS transaction_count,
           sum(w.total_btc) AS total_received
    LIMIT 100
    ''',
    
    'find_mixer_route': '''
    MATCH path = (start:Wallet {address: $start})-[:TRANSACTION*1..5]->(mixer:Wallet)
    WHERE mixer.category = 'mixer'
    RETURN path
    LIMIT 10
    ''',
    
    'calculate_path_to_exchange': '''
    MATCH path = shortestPath((start:Wallet {address: $start})-[:TRANSACTION*]->(exchange:Wallet))
    WHERE exchange.category = 'exchange'
    RETURN path, length(path) AS hops
    LIMIT 10
    ''',
    
    'detect_clusters': '''
    MATCH (w:Wallet)
    CALL apoc.algo.community.label_propagation()
    YIELD nodes, relationships, communityId
    RETURN communityId, collect(nodes) AS cluster_wallets, size(nodes) AS cluster_size
    ORDER BY cluster_size DESC
    ''',
    
    'get_high_risk_wallets': '''
    MATCH (w:Wallet)
    WHERE w.risk_level IN ['high', 'critical']
    RETURN w.address AS address, w.category AS category, w.risk_level AS risk
    LIMIT 100
    ''',
}

# ============================================================================
# NEO4J CONNECTION
# ============================================================================

class Neo4jConnection:
    """Gerencia conexão com Neo4j"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[AsyncDriver] = None
    
    async def connect(self):
        """Conecta ao Neo4j"""
        self.driver = async_driver(
            self.uri,
            auth=(self.user, self.password)
        )
        
        # Verificar conexão
        async with self.driver.session() as session:
            result = await session.run("RETURN 1")
            await result.single()
        
        print(f"✓ Neo4j connected: {self.uri}")
    
    async def disconnect(self):
        """Desconecta do Neo4j"""
        if self.driver:
            await self.driver.close()
            print("✓ Neo4j disconnected")
    
    async def run_query(self, query: str, parameters: Dict) -> List[Dict]:
        """Executa query e retorna resultados"""
        async with self.driver.session() as session:
            result = await session.run(query, parameters)
            return [dict(record) for record in await result.data()]
    
    async def run_write_query(self, query: str, parameters: Dict) -> Dict:
        """Executa query de escrita (CREATE, UPDATE)"""
        async with self.driver.session() as session:
            result = await session.run(query, parameters)
            return dict(await result.single())

# ============================================================================
# GRAPH DATABASE SERVICE
# ============================================================================

class GraphDatabaseService:
    """Serviço de operações no grafo"""
    
    def __init__(self, connection: Neo4jConnection):
        self.conn = connection
    
    async def add_wallet(
        self,
        address: str,
        category: str = 'unknown',
        risk_level: str = 'low'
    ) -> Dict:
        """Adiciona wallet ao grafo"""
        return await self.conn.run_write_query(
            CYPHER_QUERIES['create_wallet'],
            {
                'address': address,
                'category': category,
                'risk_level': risk_level
            }
        )
    
    async def add_transaction(
        self,
        txid: str,
        from_address: str,
        to_address: str,
        amount_btc: float,
        timestamp: str,
        confirmations: int = 0
    ) -> Dict:
        """Adiciona transação ao grafo"""
        
        # Criar/atualizar wallets
        await self.add_wallet(from_address)
        await self.add_wallet(to_address)
        
        # Criar transação e links
        return await self.conn.run_write_query(
            CYPHER_QUERIES['create_transaction'],
            {
                'txid': txid,
                'from_address': from_address,
                'to_address': to_address,
                'amount_btc': amount_btc,
                'timestamp': timestamp,
                'confirmations': confirmations
            }
        )
    
    async def find_direct_recipients(self, wallet_address: str) -> List[Dict]:
        """Encontra destinatários diretos (1 hop)"""
        return await self.conn.run_query(
            CYPHER_QUERIES['find_direct_recipients'],
            {'address': wallet_address}
        )
    
    async def find_recipients_at_depth(
        self,
        wallet_address: str,
        depth: int = 3
    ) -> List[Dict]:
        """Encontra destinatários até profundidade N"""
        return await self.conn.run_query(
            CYPHER_QUERIES['find_all_recipients_depth_n'],
            {
                'start_address': wallet_address,
                'depth': depth
            }
        )
    
    async def find_converging_wallets(self, target_address: str) -> List[Dict]:
        """Encontra wallets que enviam para um destinatário específico"""
        return await self.conn.run_query(
            CYPHER_QUERIES['find_converging_wallets'],
            {'target_address': target_address}
        )
    
    async def find_mixer_route(self, start_address: str) -> List[Dict]:
        """Encontra rota de um wallet até um mixer"""
        return await self.conn.run_query(
            CYPHER_QUERIES['find_mixer_route'],
            {'start': start_address}
        )
    
    async def find_path_to_exchange(self, start_address: str) -> List[Dict]:
        """Encontra caminho mais curto até um exchange"""
        return await self.conn.run_query(
            CYPHER_QUERIES['calculate_path_to_exchange'],
            {'start': start_address}
        )
    
    async def get_high_risk_wallets(self) -> List[Dict]:
        """Retorna todas as wallets com risco alto/crítico"""
        return await self.conn.run_query(
            CYPHER_QUERIES['get_high_risk_wallets'],
            {}
        )
    
    async def get_wallet_statistics(self, wallet_address: str) -> Dict:
        """Retorna estatísticas de uma wallet"""
        
        # Número de transações enviadas
        sent_query = '''
        MATCH (w:Wallet {address: $address})-[:SENDS]->(tx:Transaction)
        RETURN count(tx) AS sent_count, sum(tx.amount_btc) AS sent_total
        '''
        
        # Número de transações recebidas
        received_query = '''
        MATCH (tx:Transaction)-[:SENDS_TO]->(w:Wallet {address: $address})
        RETURN count(tx) AS received_count, sum(tx.amount_btc) AS received_total
        '''
        
        sent = await self.conn.run_query(sent_query, {'address': wallet_address})
        received = await self.conn.run_query(received_query, {'address': wallet_address})
        
        return {
            'wallet': wallet_address,
            'sent': sent[0] if sent else {},
            'received': received[0] if received else {},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

async def main():
    # Conectar
    conn = Neo4jConnection(
        uri='bolt://localhost:7687',
        user='neo4j',
        password='password'
    )
    
    await conn.connect()
    
    try:
        service = GraphDatabaseService(conn)
        
        # Adicionar algumas transações de exemplo
        print("=== Adding transactions ===")
        
        await service.add_transaction(
            txid='tx001',
            from_address='bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
            to_address='bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',
            amount_btc=0.5,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
        
        await service.add_transaction(
            txid='tx002',
            from_address='bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',
            to_address='1A1z7agoat4qNB5agoat4qNB5agoat4qNB',
            amount_btc=0.5,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
        
        # Rastrear
        print("\n=== Finding recipients ===")
        start_wallet = 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'
        recipients = await service.find_recipients_at_depth(start_wallet, depth=3)
        print(f"Found {len(recipients)} recipients")
        
        # Estatísticas
        print("\n=== Wallet statistics ===")
        stats = await service.get_wallet_statistics(start_wallet)
        print(f"Stats: {stats}")
    
    finally:
        await conn.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
