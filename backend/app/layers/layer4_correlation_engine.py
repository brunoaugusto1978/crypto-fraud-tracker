"""
CAMADA 4: CORRELATION ENGINE
Responsável por:
- Calcular scores de risco (0-100)
- Aplicar regras de detecção
- Correlacionar evidências
- Identificar padrões de fraude
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

# ============================================================================
# REGRAS DE CORRELAÇÃO
# ============================================================================

@dataclass
class DetectionRule:
    """Define uma regra de detecção"""
    rule_id: str
    name: str
    description: str
    weight: float  # Pontos adicionados ao score
    condition: Callable  # Função que retorna True/False
    enabled: bool = True
    
    def __post_init__(self):
        if not isinstance(self.weight, (int, float)) or self.weight < 0 or self.weight > 50:
            raise ValueError("Weight deve estar entre 0 e 50")

# ============================================================================
# RULE FACTORY
# ============================================================================

class RuleFactory:
    """Factory para criar regras de detecção"""
    
    @staticmethod
    def mixer_transaction_rule() -> DetectionRule:
        """Regra: Transação para mixer"""
        return DetectionRule(
            rule_id='rule_mixer_001',
            name='Destination is Known Mixer',
            description='Carteira destino é um mixer conhecido (Tornado, Mixing Service, etc)',
            weight=30.0,
            condition=lambda enrichment: enrichment.get('category') == 'mixer'
        )
    
    @staticmethod
    def ransomware_wallet_rule() -> DetectionRule:
        """Regra: Carteira associada a ransomware"""
        return DetectionRule(
            rule_id='rule_ransomware_001',
            name='Known Ransomware Wallet',
            description='Carteira está associada a exploits conhecidos de ransomware',
            weight=50.0,
            condition=lambda enrichment: enrichment.get('category') == 'ransomware'
        )
    
    @staticmethod
    def multiple_victims_rule() -> DetectionRule:
        """Regra: Múltiplas vítimas em curto período"""
        def check_multiple_victims(context: Dict) -> bool:
            senders = context.get('senders_in_24h', 0)
            return senders >= 10
        
        return DetectionRule(
            rule_id='rule_victims_001',
            name='Multiple Victims in 24h',
            description='Mais de 10 remetentes enviaram para essa carteira em menos de 24 horas',
            weight=25.0,
            condition=check_multiple_victims
        )
    
    @staticmethod
    def exchange_consolidation_rule() -> DetectionRule:
        """Regra: Consolidação em exchange"""
        return DetectionRule(
            rule_id='rule_exchange_001',
            name='Consolidation to Exchange',
            description='Fundos consolidados e depositados em exchange KYC',
            weight=15.0,
            condition=lambda enrichment: enrichment.get('category') == 'exchange'
        )
    
    @staticmethod
    def scam_wallet_rule() -> DetectionRule:
        """Regra: Carteira conhecida de scam"""
        return DetectionRule(
            rule_id='rule_scam_001',
            name='Known Scam Wallet',
            description='Carteira está listada em banco de dados de scams',
            weight=40.0,
            condition=lambda enrichment: enrichment.get('category') == 'scam'
        )
    
    @staticmethod
    def fast_consolidation_rule() -> DetectionRule:
        """Regra: Consolidação rápida de fundos"""
        def check_fast_consolidation(context: Dict) -> bool:
            transactions = context.get('recent_transactions', [])
            # Se todas as transações ocorreram em menos de 1 hora
            if len(transactions) >= 5:
                parsed = []
                for tx in transactions:
                    ts = tx.get('timestamp')
                    if not ts:
                        continue
                    try:
                        parsed.append(datetime.fromisoformat(str(ts).replace('Z', '+00:00')))
                    except ValueError:
                        continue
                if len(parsed) >= 5:
                    time_diff = max(parsed) - min(parsed)
                    return time_diff < timedelta(hours=1)
            return False
        
        return DetectionRule(
            rule_id='rule_consolidation_001',
            name='Fast Fund Consolidation',
            description='Múltiplos fundos consolidados rapidamente (< 1 hora)',
            weight=20.0,
            condition=check_fast_consolidation
        )
    
    @staticmethod
    def high_value_transaction_rule(threshold_btc: float = 10) -> DetectionRule:
        """Regra: Transação de alto valor"""
        return DetectionRule(
            rule_id='rule_highvalue_001',
            name=f'High Value Transaction (>{threshold_btc} BTC)',
            description=f'Transação acima de {threshold_btc} BTC',
            weight=10.0,
            condition=lambda tx: tx.get('amount_btc', 0) > threshold_btc
        )

# ============================================================================
# CORRELATION ENGINE
# ============================================================================

class CorrelationEngine:
    """Motor de correlação e scoring de risco"""
    
    def __init__(self, rules: Optional[List[DetectionRule]] = None):
        """
        Inicializa engine com regras padrão ou customizadas
        
        Args:
            rules: Lista de DetectionRule. Se None, usa regras padrão.
        """
        if rules is None:
            self.rules = self._create_default_rules()
        else:
            self.rules = rules
    
    def _create_default_rules(self) -> List[DetectionRule]:
        """Cria set padrão de regras"""
        return [
            RuleFactory.mixer_transaction_rule(),
            RuleFactory.ransomware_wallet_rule(),
            RuleFactory.multiple_victims_rule(),
            RuleFactory.exchange_consolidation_rule(),
            RuleFactory.scam_wallet_rule(),
            RuleFactory.fast_consolidation_rule(),
        ]
    
    def calculate_risk_score(
        self,
        wallet_enrichment: Dict,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Calcula score de risco (0-100) para uma carteira
        
        Args:
            wallet_enrichment: Dados de enriquecimento do blockchain
            context: Contexto adicional (transações, vítimas, etc)
        
        Returns:
            {
                "entity_id": "wallet_address",
                "risk_score": 75.5,
                "risk_level": "high",
                "triggered_rules": ["rule_mixer_001", "rule_victims_001"],
                "evidence": ["É um mixer conhecido", "10+ vítimas em 24h"],
                "calculated_at": "2024-01-15T10:30:00Z"
            }
        """
        
        if context is None:
            context = {}
        
        triggered_rules = []
        evidence = []
        total_score = 0.0
        
        wallet_address = wallet_enrichment.get('wallet', 'unknown')
        
        # Executar cada regra
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                # Decidir qual argumento passar baseado no tipo de regra
                rule_data = context if rule.rule_id.endswith('_victims_001') or \
                                       rule.rule_id.endswith('_consolidation_001') else \
                           wallet_enrichment
                
                if rule.condition(rule_data):
                    total_score += rule.weight
                    triggered_rules.append(rule.rule_id)
                    evidence.append(rule.description)
            
            except Exception as e:
                print(f"Erro ao executar regra {rule.rule_id}: {e}")
                continue
        
        # Normalizar score para 0-100
        risk_score = min(100.0, total_score)
        
        # Determinar nível de risco
        if risk_score >= 80:
            risk_level = 'critical'
        elif risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 25:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'entity_id': wallet_address,
            'entity_type': 'wallet',
            'risk_score': round(risk_score, 1),
            'risk_level': risk_level,
            'triggered_rules': triggered_rules,
            'evidence': evidence,
            'calculated_at': datetime.utcnow().isoformat() + 'Z'
        }
    
    def score_transaction_chain(
        self,
        wallets_chain: List[Dict],
        transactions: List[Dict]
    ) -> List[Dict]:
        """
        Marca todas as wallets e transações em uma cadeia
        
        Args:
            wallets_chain: Lista de wallets enriquecidas
            transactions: Lista de transações
        
        Returns:
            Lista de scores com análise agregada
        """
        
        scores = []
        
        # Score cada wallet
        for wallet in wallets_chain:
            context = {
                'senders_in_24h': self._count_senders_in_24h(wallet.get('address'), transactions),
                'recent_transactions': self._get_recent_transactions(wallet.get('address'), transactions),
            }
            
            score = self.calculate_risk_score(wallet, context)
            scores.append(score)
        
        return scores
    
    @staticmethod
    def _count_senders_in_24h(wallet_address: str, transactions: List[Dict]) -> int:
        """Conta quantos endereços enviaram para essa wallet em 24h"""
        now = datetime.utcnow().replace(tzinfo=None)
        cutoff = now - timedelta(hours=24)
        
        senders = set()
        for tx in transactions:
            if tx.get('to_address') == wallet_address:
                tx_time = datetime.fromisoformat(tx.get('timestamp', '').replace('Z', '')).replace(tzinfo=None)
                if tx_time >= cutoff:
                    senders.add(tx.get('from_address'))
        
        return len(senders)
    
    @staticmethod
    def _get_recent_transactions(wallet_address: str, transactions: List[Dict]) -> List[Dict]:
        """Retorna transações recentes de/para uma wallet"""
        now = datetime.utcnow().replace(tzinfo=None)
        cutoff = now - timedelta(hours=24)
        
        recent = []
        for tx in transactions:
            if tx.get('from_address') == wallet_address or tx.get('to_address') == wallet_address:
                tx_time = datetime.fromisoformat(tx.get('timestamp', '').replace('Z', '')).replace(tzinfo=None)
                if tx_time >= cutoff:
                    recent.append(tx)
        
        return recent
    
    def add_rule(self, rule: DetectionRule):
        """Adiciona nova regra de detecção"""
        self.rules.append(rule)
    
    def disable_rule(self, rule_id: str):
        """Desabilita uma regra"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
    
    def get_rules(self) -> List[Dict]:
        """Retorna todas as regras em formato JSON"""
        return [
            {
                'rule_id': r.rule_id,
                'name': r.name,
                'description': r.description,
                'weight': r.weight,
                'enabled': r.enabled
            }
            for r in self.rules
        ]

# ============================================================================
# CLUSTER ANALYSIS
# ============================================================================

class ClusterAnalyzer:
    """Analisa clusters de wallets suspeitas"""
    
    def __init__(self, engine: CorrelationEngine):
        self.engine = engine
    
    def analyze_cluster(
        self,
        cluster_id: str,
        wallets: List[Dict],
        transactions: List[Dict]
    ) -> Dict:
        """
        Analisa um cluster de wallets relacionadas
        
        Returns:
            {
                "cluster_id": "...",
                "primary_wallet": "...",
                "cluster_size": 10,
                "total_volume_btc": 45.5,
                "average_risk_score": 72.3,
                "suspected_crime": "ransomware",
                "timeline": [...],
                "recommendations": [...]
            }
        """
        
        # Score cada wallet
        scores = self.engine.score_transaction_chain(wallets, transactions)
        
        # Calcular estatísticas
        avg_risk = sum(s['risk_score'] for s in scores) / len(scores) if scores else 0
        total_volume = sum(t.get('amount_btc', 0) for t in transactions)
        
        # Inferir tipo de crime
        suspected_crime = self._infer_crime_type(wallets, transactions, scores)
        
        # Criar timeline
        timeline = self._build_timeline(transactions)
        
        # Tipologias AML cripto
        aml_typologies = self._detect_aml_typologies(wallets, transactions)

        # Recomendações
        recommendations = self._generate_recommendations(wallets, scores, suspected_crime, aml_typologies)
        
        return {
            'cluster_id': cluster_id,
            'primary_wallet': wallets[0].get('address') if wallets else 'unknown',
            'cluster_size': len(wallets),
            'total_volume_btc': round(total_volume, 2),
            'transaction_count': len(transactions),
            'average_risk_score': round(avg_risk, 1),
            'suspected_crime': suspected_crime,
            'aml_typologies': aml_typologies,
            'timeline': timeline,
            'recommendations': recommendations,
            'analyzed_at': datetime.utcnow().isoformat() + 'Z'
        }
    
    @staticmethod
    def _detect_aml_typologies(wallets: List[Dict], transactions: List[Dict]) -> List[Dict]:
        """Detecta tipologias AML básicas e explicáveis para criptoativos."""
        typologies = []
        incoming = {}
        outgoing = {}
        counterparties = {}
        mixer_addresses = {w.get('address') for w in wallets if w.get('category') == 'mixer'}
        exchange_addresses = {w.get('address') for w in wallets if w.get('category') == 'exchange'}

        for tx in transactions:
            src = tx.get('from_address')
            dst = tx.get('to_address')
            amount = float(tx.get('amount_btc') or 0)
            if not src or not dst:
                continue
            outgoing[src] = outgoing.get(src, 0) + amount
            incoming[dst] = incoming.get(dst, 0) + amount
            counterparties.setdefault(src, set()).add(dst)
            counterparties.setdefault(dst, set()).add(src)

        for address, peers in counterparties.items():
            if len(peers) >= 8:
                typologies.append({
                    'id': 'fan_in_fan_out',
                    'severity': 'medium',
                    'address': address,
                    'peer_count': len(peers),
                    'explanation': 'Carteira interage com muitas contrapartes, padrao compativel com coleta/dispersao.'
                })

        for tx in transactions:
            if tx.get('to_address') in mixer_addresses:
                typologies.append({
                    'id': 'mixer_exposure_direct',
                    'severity': 'high',
                    'address': tx.get('to_address'),
                    'txid': tx.get('txid'),
                    'amount_btc': tx.get('amount_btc'),
                    'explanation': 'Fluxo direto para endereco classificado como mixer.'
                })
            if tx.get('to_address') in exchange_addresses:
                typologies.append({
                    'id': 'exchange_cashout_candidate',
                    'severity': 'medium',
                    'address': tx.get('to_address'),
                    'txid': tx.get('txid'),
                    'amount_btc': tx.get('amount_btc'),
                    'explanation': 'Fluxo para exchange; possivel ponto de cash-out/KYC.'
                })

        # Peel-chain simplificado: sequencia com baixo fan-out seguindo uma carteira por hop.
        small_chain = [tx for tx in transactions if float(tx.get('amount_btc') or 0) > 0]
        if len(small_chain) >= 4:
            typologies.append({
                'id': 'layering_or_peel_chain_candidate',
                'severity': 'medium',
                'transaction_count': len(small_chain),
                'explanation': 'Cadeia com multiplos hops; requer revisao para layering/peel chain.'
            })

        # Remover duplicatas preservando ordem.
        seen = set()
        unique = []
        for item in typologies:
            key = (item.get('id'), item.get('address'), item.get('txid'))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    @staticmethod
    def _infer_crime_type(wallets: List[Dict], transactions: List[Dict], scores: List[Dict]) -> str:
        """Infere tipo de crime baseado nas evidências"""
        
        crime_indicators = {
            'ransomware': 0,
            'scam': 0,
            'money_laundering': 0,
            'fraud': 0
        }

        for wallet in wallets:
            cat = wallet.get('category')
            if cat == 'ransomware':
                crime_indicators['ransomware'] += 30
            elif cat == 'scam':
                crime_indicators['scam'] += 30
            elif cat == 'darknet':
                crime_indicators['money_laundering'] += 25
            elif cat == 'mixer':
                crime_indicators['money_laundering'] += 20

        # Padrao: muitos remetentes pode indicar scam de coleta
        if len(wallets) > 20:
            crime_indicators['scam'] += 10

        # Se nenhum indicador pontuou, nao ha crime evidente
        # (evita retornar 'ransomware' por ser o 1o do dict)
        if max(crime_indicators.values()) == 0:
            return 'indeterminado'

        return max(crime_indicators, key=crime_indicators.get)
    
    @staticmethod
    def _build_timeline(transactions: List[Dict]) -> List[Dict]:
        """Constrói timeline de transações"""
        sorted_txs = sorted(transactions, key=lambda x: x.get('timestamp', ''))
        
        timeline = []
        for tx in sorted_txs[:20]:  # Limitar a 20 eventos
            timeline.append({
                'timestamp': tx.get('timestamp'),
                'event_type': 'transaction',
                'description': f"{tx['from_address'][:10]}... → {tx['to_address'][:10]}...",
                'amount_btc': tx.get('amount_btc'),
            })
        
        return timeline
    
    @staticmethod
    def _generate_recommendations(wallets: List[Dict], scores: List[Dict], crime_type: str, aml_typologies: Optional[List[Dict]] = None) -> List[str]:
        """Gera recomendações de ação"""
        
        recommendations = []
        
        # Baseado em tipo de crime
        if crime_type == 'ransomware':
            recommendations.append('⚠️  Notificar coordenador de ransomware')
            recommendations.append('📋 Reportar para CISA/FS-ISAC')
            recommendations.append('🔒 Bloquear endereço em exchanges')
        
        elif crime_type == 'scam':
            recommendations.append('📢 Alertar vítimas identificadas')
            recommendations.append('🚨 Reportar para autoridades locais')
            recommendations.append('📋 Compartilhar IOCs em ISACs')
        
        elif crime_type == 'money_laundering':
            recommendations.append('🔍 Investigar origem de fundos')
            recommendations.append('💰 Reportar para FinCEN/FATF')
            recommendations.append('🔗 Rastrear destino final')
        
        typology_ids = {t.get('id') for t in (aml_typologies or [])}
        if 'mixer_exposure_direct' in typology_ids:
            recommendations.append('🧾 Preservar evidencia on-chain e revisar exposicao direta a mixer')
        if 'exchange_cashout_candidate' in typology_ids:
            recommendations.append('🏦 Preparar pacote de evidencias para eventual pedido a exchange/KYC')
        if 'layering_or_peel_chain_candidate' in typology_ids:
            recommendations.append('🔁 Revisar cadeia de hops para layering/peel chain')

        # Score médio alto
        avg_score = sum(s['risk_score'] for s in scores) / len(scores) if scores else 0
        if avg_score >= 80:
            recommendations.append('🚨 Prioridade CRÍTICA - escalação imediata')
        
        return recommendations

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def main():
    # Criar engine
    engine = CorrelationEngine()
    
    # Teste 1: Score uma wallet
    print("=== Test 1: Score Single Wallet ===")
    enrichment = {
        'wallet': '1A1z7agoat4qNB5agoat4qNB5agoat4qNB',
        'category': 'mixer',
        'risk_level': 'high',
        'transactions_count': 1500
    }
    context = {
        'senders_in_24h': 15,
        'recent_transactions': [
            {'from_address': 'addr1', 'timestamp': datetime.utcnow().isoformat() + 'Z'},
            {'from_address': 'addr2', 'timestamp': datetime.utcnow().isoformat() + 'Z'},
        ]
    }
    
    score = engine.calculate_risk_score(enrichment, context)
    print(json.dumps(score, indent=2))
    
    # Teste 2: Analisar cluster
    print("\n=== Test 2: Analyze Cluster ===")
    analyzer = ClusterAnalyzer(engine)
    
    cluster = analyzer.analyze_cluster(
        cluster_id='cluster_001',
        wallets=[
            {'address': 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4', 'category': 'ransomware'},
            {'address': '1A1z7agoat4qNB5agoat4qNB5agoat4qNB', 'category': 'mixer'},
            {'address': '3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy', 'category': 'exchange'},
        ],
        transactions=[
            {
                'from_address': 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
                'to_address': '1A1z7agoat4qNB5agoat4qNB5agoat4qNB',
                'amount_btc': 2.5,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        ]
    )
    
    print(json.dumps(cluster, indent=2))
    
    # Teste 3: Listar regras
    print("\n=== Test 3: Detection Rules ===")
    rules = engine.get_rules()
    for rule in rules:
        print(f"[{rule['rule_id']}] {rule['name']} ({rule['weight']} pts)")

if __name__ == "__main__":
    main()
