"""
CAMADA 5: REPORT GENERATION
Responsável por:
- Gerar timelines de fraude
- Criar grafos navegáveis
- Gerar PDFs executivos
- Exportar relatórios técnicos
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
from io import BytesIO

# ============================================================================
# TIMELINE GENERATOR
# ============================================================================

class TimelineGenerator:
    """Gera timeline de transações"""
    
    @staticmethod
    def generate_timeline(
        transactions: List[Dict],
        enrichments: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Gera timeline formatada com eventos
        
        Args:
            transactions: Lista de transações
            enrichments: Dict de { wallet_address: enrichment_data }
        
        Returns:
            Lista de eventos ordenados por tempo
        """
        
        events = []
        
        # Agrupar transações por timestamp
        sorted_txs = sorted(transactions, key=lambda x: x.get('timestamp', ''))
        
        for tx in sorted_txs:
            from_addr = tx.get('from_address', '')
            to_addr = tx.get('to_address', '')
            amount = tx.get('amount_btc', 0)
            timestamp = tx.get('timestamp', '')
            
            # Detectar tipo de evento
            event_type = 'transaction'
            description_parts = []
            
            # Checar se é envio para mixer
            to_enrichment = enrichments.get(to_addr, {})
            if to_enrichment.get('category') == 'mixer':
                event_type = 'mixer_passage'
                description_parts.append(f'Envio para MIXER: {to_enrichment.get("labeled_as", "mixer desconhecido")}')
            
            # Checkar se é depósito em exchange
            if to_enrichment.get('category') == 'exchange':
                event_type = 'exchange_deposit'
                description_parts.append(f'Depósito em EXCHANGE: {to_enrichment.get("labeled_as", "exchange")}')
            
            # Default
            if not description_parts:
                from_short = from_addr[:16] + '...'
                to_short = to_addr[:16] + '...'
                description_parts.append(f'{from_short} → {to_short}')
            
            events.append({
                'timestamp': timestamp,
                'event_type': event_type,
                'description': description_parts[0],
                'amount_btc': amount,
                'from_address': from_addr,
                'to_address': to_addr,
                'from_category': enrichments.get(from_addr, {}).get('category', 'unknown'),
                'to_category': enrichments.get(to_addr, {}).get('category', 'unknown'),
            })
        
        return events

# ============================================================================
# GRAPH VISUALIZATION
# ============================================================================

class GraphVisualizer:
    """Gera dados para visualização de grafo"""
    
    @staticmethod
    def generate_graph_data(
        wallets: List[Dict],
        transactions: List[Dict],
        enrichments: Dict[str, Dict]
    ) -> Dict:
        """
        Gera dados para visualização com D3.js/Cytoscape
        
        Returns:
            {
                "nodes": [...],
                "edges": [...],
                "metadata": {...}
            }
        """
        
        nodes = []
        edges = []
        node_set = set()
        
        # Criar nós de wallets
        for wallet in wallets:
            addr = wallet.get('address', '')
            if addr not in node_set:
                enrichment = enrichments.get(addr, {})
                
                # Determinar cor baseado em categoria
                color_map = {
                    'mixer': '#FF6B6B',           # Vermelho
                    'exchange': '#4ECDC4',        # Teal
                    'ransomware': '#FFD93D',      # Amarelo
                    'scam': '#FF006E',            # Rosa
                    'legitimate': '#95E1D3',      # Verde claro
                    'unknown': '#A8A8A8'          # Cinza
                }
                
                category = enrichment.get('category', 'unknown')
                
                nodes.append({
                    'id': addr,
                    'label': f"{addr[:12]}...",
                    'category': category,
                    'color': color_map.get(category, '#A8A8A8'),
                    'risk_level': enrichment.get('risk_level', 'low'),
                    'risk_score': enrichment.get('risk_score', 0),
                    'size': 30,
                    'title': enrichment.get('labeled_as', addr)  # Tooltip
                })
                
                node_set.add(addr)
        
        # Criar edges (transações)
        for tx in transactions:
            from_addr = tx.get('from_address', '')
            to_addr = tx.get('to_address', '')
            amount = tx.get('amount_btc', 0)
            
            if from_addr in node_set and to_addr in node_set:
                edges.append({
                    'source': from_addr,
                    'target': to_addr,
                    'weight': amount,
                    'label': f'{amount:.2f} BTC',
                    'timestamp': tx.get('timestamp', '')
                })
        
        # Calcular estatísticas
        total_volume = sum(t.get('amount_btc', 0) for t in transactions)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'node_count': len(nodes),
                'edge_count': len(edges),
                'total_volume_btc': round(total_volume, 2),
                'generated_at': datetime.utcnow().isoformat() + 'Z'
            }
        }
    
    @staticmethod
    def generate_d3_html(graph_data: Dict) -> str:
        """Gera HTML interativo com D3.js"""
        
        nodes_json = json.dumps(graph_data['nodes'])
        edges_json = json.dumps(graph_data['edges'])
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Blockchain Transaction Graph</title>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 10px; }}
                #graph {{ border: 1px solid #ccc; }}
                .node {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; }}
                .node:hover {{ stroke: #000; stroke-width: 2px; }}
                .link {{ stroke: #999; stroke-opacity: 0.6; }}
                .tooltip {{ position: absolute; padding: 8px; background: #333; color: #fff; border-radius: 4px; font-size: 12px; z-index: 1000; }}
                #stats {{ margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h2>Blockchain Transaction Graph</h2>
            <svg id="graph" width="1000" height="600"></svg>
            <div id="stats">
                <p><strong>Nós:</strong> {graph_data['metadata']['node_count']} | <strong>Transações:</strong> {graph_data['metadata']['edge_count']} | <strong>Volume:</strong> {graph_data['metadata']['total_volume_btc']} BTC</p>
            </div>
            
            <script>
                const nodes = {nodes_json};
                const links = {edges_json};
                
                const svg = d3.select("#graph");
                const width = +svg.attr("width");
                const height = +svg.attr("height");
                
                const simulation = d3.forceSimulation(nodes)
                    .force("link", d3.forceLink(links).id(d => d.id).distance(100))
                    .force("charge", d3.forceManyBody().strength(-300))
                    .force("center", d3.forceCenter(width / 2, height / 2));
                
                const link = svg.append("g")
                    .selectAll("line")
                    .data(links)
                    .enter().append("line")
                    .attr("class", "link")
                    .attr("stroke-width", d => Math.sqrt(d.weight));
                
                const node = svg.append("g")
                    .selectAll("circle")
                    .data(nodes)
                    .enter().append("circle")
                    .attr("class", "node")
                    .attr("r", d => d.size)
                    .attr("fill", d => d.color)
                    .call(drag(simulation));
                
                node.append("title").text(d => d.title);
                
                simulation.on("tick", () => {{
                    link.attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);
                    
                    node.attr("cx", d => d.x)
                        .attr("cy", d => d.y);
                }});
                
                function drag(simulation) {{
                    function dragstarted(event, d) {{
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        d.fx = d.x;
                        d.fy = d.y;
                    }}
                    
                    function dragged(event, d) {{
                        d.fx = event.x;
                        d.fy = event.y;
                    }}
                    
                    function dragended(event, d) {{
                        if (!event.active) simulation.alphaTarget(0);
                        d.fx = null;
                        d.fy = null;
                    }}
                    
                    return d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended);
                }}
            </script>
        </body>
        </html>
        '''
        
        return html

# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Gera relatórios consolidados"""
    
    def __init__(self):
        self.timeline_gen = TimelineGenerator()
        self.graph_viz = GraphVisualizer()
    
    def generate_investigation_report(
        self,
        investigation_id: str,
        initial_wallet: str,
        wallets: List[Dict],
        transactions: List[Dict],
        enrichments: Dict[str, Dict],
        cluster_analysis: Dict,
        risk_scores: List[Dict]
    ) -> Dict:
        """
        Gera relatório completo de investigação
        
        Returns:
            {
                "report_id": "...",
                "title": "Investigação de Fraude - Bitcoin",
                "executive_summary": {...},
                "timeline": [...],
                "graph_data": {...},
                "clusters": {...},
                "risk_assessment": {...},
                "recommendations": [...],
                "generated_at": "..."
            }
        """
        
        # Gerar timeline
        timeline = self.timeline_gen.generate_timeline(transactions, enrichments)
        
        # Gerar dados de grafo
        graph_data = self.graph_viz.generate_graph_data(wallets, transactions, enrichments)
        
        # Calcular estatísticas
        total_volume = sum(t.get('amount_btc', 0) for t in transactions)
        avg_risk = sum(s['risk_score'] for s in risk_scores) / len(risk_scores) if risk_scores else 0
        
        # Sumário executivo
        executive_summary = {
            'title': 'Investigação de Fraude/Ransomware em Bitcoin',
            'case_date': datetime.utcnow().isoformat() + 'Z',
            'initial_indicator': initial_wallet,
            'key_findings': [
                f'{len(wallets)} carteiras rastreadas',
                f'{len(transactions)} transações identificadas',
                f'{total_volume:.2f} BTC movidos',
                f'Score de risco médio: {avg_risk:.1f}/100'
            ],
            'estimated_loss_btc': total_volume,
            'risk_assessment': self._assess_risk_level(avg_risk),
            'action_items': self._generate_action_items(cluster_analysis, risk_scores)
        }
        
        return {
            'report_id': investigation_id,
            'title': 'Blockchain Fraud Investigation Report',
            'executive_summary': executive_summary,
            'initial_wallet': initial_wallet,
            'investigation_date': datetime.utcnow().isoformat() + 'Z',
            'wallets_discovered': len(wallets),
            'transactions_traced': len(transactions),
            'total_volume_btc': round(total_volume, 2),
            'average_risk_score': round(avg_risk, 1),
            'timeline': timeline,
            'graph_visualization': {
                'html_file': 'graph.html',
                'node_count': graph_data['metadata']['node_count'],
                'edge_count': graph_data['metadata']['edge_count']
            },
            'cluster_analysis': cluster_analysis,
            'risk_assessment': executive_summary['risk_assessment'],
            'recommendations': executive_summary['action_items'],
            'status': 'completed',
            'analyst': 'Crypto Fraud Tracker v1.0'
        }
    
    def generate_json_report(self, report: Dict) -> str:
        """Gera relatório em JSON"""
        return json.dumps(report, indent=2)
    
    def generate_html_report(
        self,
        report: Dict,
        graph_html: str
    ) -> str:
        """Gera relatório HTML interativo"""
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Investigação de Fraude em Bitcoin</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                h1, h2 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f9f9f9; border-left: 4px solid #4CAF50; border-radius: 4px; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #4CAF50; }}
                .metric-label {{ font-size: 12px; color: #777; margin-top: 5px; }}
                .risk-critical {{ background: #FFE5E5; border-left-color: #FF6B6B; }}
                .risk-high {{ background: #FFF3E0; border-left-color: #FF9800; }}
                .risk-medium {{ background: #FFFDE7; border-left-color: #FBC02D; }}
                .risk-low {{ background: #E8F5E9; border-left-color: #4CAF50; }}
                .timeline {{ margin: 20px 0; }}
                .timeline-item {{ margin-bottom: 20px; padding-left: 30px; position: relative; }}
                .timeline-item:before {{ content: ""; position: absolute; left: 0; top: 0; width: 2px; height: 100%; background: #ccc; }}
                .timeline-item .dot {{ position: absolute; left: -8px; top: 0; width: 12px; height: 12px; background: #4CAF50; border-radius: 50%; border: 2px solid white; }}
                .finding {{ margin: 10px 0; padding: 10px; background: #f5f5f5; border-left: 3px solid #4CAF50; }}
                .recommendation {{ margin: 10px 0; padding: 10px; background: #e8f5e9; border-left: 3px solid #4CAF50; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #4CAF50; color: white; }}
                tr:hover {{ background: #f5f5f5; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Investigação de Fraude em Bitcoin</h1>
                
                <div style="margin: 20px 0;">
                    <div class="metric">
                        <div class="metric-label">Relatório ID</div>
                        <div class="metric-value">{report['report_id'][:12]}...</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Wallets Rastreadas</div>
                        <div class="metric-value">{report['wallets_discovered']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Transações</div>
                        <div class="metric-value">{report['transactions_traced']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Volume (BTC)</div>
                        <div class="metric-value">{report['total_volume_btc']:.2f}</div>
                    </div>
                    <div class="metric risk-{report['risk_assessment'].lower().replace('/', '_')}">
                        <div class="metric-label">Score de Risco</div>
                        <div class="metric-value">{report['average_risk_score']:.1f}/100</div>
                    </div>
                </div>
                
                <h2>📋 Sumário Executivo</h2>
                <p><strong>Data:</strong> {report['investigation_date']}</p>
                <p><strong>Carteira Inicial:</strong> <code>{report['initial_wallet']}</code></p>
                <h3>Principais Descobertas:</h3>
                <ul>
        '''
        
        for finding in report['executive_summary']['key_findings']:
            html += f'<li>{finding}</li>\n'
        
        html += '''
                </ul>
                
                <h2>⏱️ Timeline de Transações</h2>
                <div class="timeline">
        '''
        
        for event in report['timeline'][:10]:  # Primeiros 10 eventos
            html += f'''
                    <div class="timeline-item">
                        <div class="dot"></div>
                        <strong>{event['event_type'].upper()}</strong>
                        <p>{event['description']}</p>
                        <small>💰 {event['amount_btc']:.8f} BTC | 📅 {event['timestamp']}</small>
                    </div>
            '''
        
        html += '''
                </div>
                
                <h2>🎯 Recomendações</h2>
        '''
        
        for rec in report['recommendations']:
            html += f'<div class="recommendation">{rec}</div>\n'
        
        html += '''
                <h2>🔗 Visualização de Grafo</h2>
                <p>Clique e arraste os nós para explorar as relações entre carteiras.</p>
        '''
        
        # Inserir grafo HTML
        html += graph_html
        
        html += '''
                <hr>
                <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #777; font-size: 12px;">
                    <p>Relatório gerado automaticamente pelo Crypto Fraud Tracker v1.0</p>
                    <p>Para consultas, contacte security@organization.com</p>
                </footer>
            </div>
        </body>
        </html>
        '''
        
        return html
    
    @staticmethod
    def _assess_risk_level(avg_score: float) -> str:
        """Avalia nível de risco baseado em score"""
        if avg_score >= 80:
            return '🚨 CRÍTICO'
        elif avg_score >= 50:
            return '⚠️ ALTO'
        elif avg_score >= 25:
            return '⚡ MÉDIO'
        else:
            return '✅ BAIXO'
    
    @staticmethod
    def _generate_action_items(cluster_analysis: Dict, risk_scores: List[Dict]) -> List[str]:
        """Gera itens de ação baseado em análise"""
        
        actions = []
        suspected_crime = cluster_analysis.get('suspected_crime', '')
        
        if suspected_crime == 'ransomware':
            actions.append('🚨 AÇÃO PRIORITÁRIA: Notificar coordenador de ransomware')
            actions.append('📋 Reportar para CISA/FS-ISAC imediatamente')
            actions.append('🔒 Coordenar com exchanges para bloquear wallets')
        
        elif suspected_crime == 'scam':
            actions.append('📢 Identificar e contactar vítimas confirmadas')
            actions.append('🚨 Reportar para autoridades locais e FBI (se US)')
            actions.append('📋 Publicar IOCs em MISP/OSINT communities')
        
        actions.append('🔍 Continuar rastreamento para destino final')
        actions.append('💾 Arquivar evidências para auditorias/investigações')
        
        return actions

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    
    gen = ReportGenerator()
    
    # Dados de exemplo
    sample_report = gen.generate_investigation_report(
        investigation_id='inv_20240115_001',
        initial_wallet='bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
        wallets=[
            {'address': 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4', 'category': 'ransomware'},
            {'address': '1A1z7agoat4qNB5agoat4qNB5agoat4qNB', 'category': 'mixer'},
        ],
        transactions=[
            {
                'from_address': 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
                'to_address': '1A1z7agoat4qNB5agoat4qNB5agoat4qNB',
                'amount_btc': 2.5,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        ],
        enrichments={},
        cluster_analysis={'suspected_crime': 'ransomware'},
        risk_scores=[{'risk_score': 85}]
    )
    
    print("=== Sample Report ===")
    print(json.dumps(sample_report, indent=2))
