-- Inicialização do PostgreSQL para Crypto Fraud Tracker

-- Tabela de IOCs (Indicadores de Comprometimento)
CREATE TABLE IF NOT EXISTS iocs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    value VARCHAR(255) NOT NULL UNIQUE,
    ioc_type VARCHAR(50) NOT NULL,
    source VARCHAR(100),
    confidence FLOAT DEFAULT 0.8,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    CONSTRAINT valid_type CHECK (ioc_type IN ('wallet_address', 'transaction_id', 'email', 'ip_address', 'domain'))
);

-- Tabela de Carteiras (Wallets)
CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(30) DEFAULT 'unknown',
    risk_level VARCHAR(20) DEFAULT 'low',
    risk_score FLOAT DEFAULT 0.0,
    total_sent_btc FLOAT DEFAULT 0.0,
    total_received_btc FLOAT DEFAULT 0.0,
    transaction_count INT DEFAULT 0,
    first_seen TIMESTAMP NULL,
    last_seen TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    CONSTRAINT valid_category CHECK (category IN ('unknown', 'exchange', 'mixer', 'ransomware', 'scam', 'darknet', 'gambling', 'marketplace', 'legitimate')),
    CONSTRAINT valid_risk_level CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);

-- Tabela de Transações
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    txid VARCHAR(100) NOT NULL UNIQUE,
    from_wallet_id UUID NOT NULL REFERENCES wallets(id),
    to_wallet_id UUID NOT NULL REFERENCES wallets(id),
    amount_btc FLOAT NOT NULL,
    fee_satoshi INT,
    timestamp TIMESTAMP NOT NULL,
    confirmations INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Tabela de Investigações
CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id VARCHAR(100) NOT NULL UNIQUE,
    initial_wallet_id UUID NOT NULL REFERENCES wallets(id),
    case_name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'in_progress',
    depth INT DEFAULT 3,
    wallets_count INT DEFAULT 0,
    transactions_count INT DEFAULT 0,
    total_volume_btc FLOAT DEFAULT 0.0,
    average_risk_score FLOAT DEFAULT 0.0,
    suspected_crime VARCHAR(100),
    notes TEXT,
    analyst VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    metadata JSONB
);

-- Tabela de Relatórios
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id VARCHAR(100) NOT NULL UNIQUE,
    investigation_id UUID NOT NULL REFERENCES investigations(id),
    title VARCHAR(255),
    status VARCHAR(20) DEFAULT 'draft',
    content TEXT,
    html_content TEXT,
    json_content JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,
    metadata JSONB
);

-- Tabela de Regras de Detecção
CREATE TABLE IF NOT EXISTS detection_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    weight FLOAT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    condition TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Alertas
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT,
    affected_wallet VARCHAR(100),
    investigation_id UUID REFERENCES investigations(id),
    acknowledged BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP NULL,
    metadata JSONB
);

-- Tabela de Auditoria
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    user_id VARCHAR(100),
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para Performance
CREATE INDEX idx_wallets_address ON wallets(address);
CREATE INDEX idx_wallets_category ON wallets(category);
CREATE INDEX idx_wallets_risk_level ON wallets(risk_level);
CREATE INDEX idx_wallets_risk_score ON wallets(risk_score DESC);
CREATE INDEX idx_transactions_from ON transactions(from_wallet_id);
CREATE INDEX idx_transactions_to ON transactions(to_wallet_id);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp DESC);
CREATE INDEX idx_investigations_status ON investigations(status);
CREATE INDEX idx_iocs_value ON iocs(value);
CREATE INDEX idx_iocs_type ON iocs(ioc_type);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);

-- Função para atualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para wallets
CREATE TRIGGER update_wallets_timestamp BEFORE UPDATE ON wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View: Top Risk Wallets
CREATE OR REPLACE VIEW v_top_risk_wallets AS
SELECT 
    address,
    category,
    risk_level,
    risk_score,
    transaction_count,
    total_sent_btc + total_received_btc as total_volume_btc,
    last_seen
FROM wallets
WHERE risk_level IN ('high', 'critical')
ORDER BY risk_score DESC
LIMIT 100;

-- View: Investigation Summary
CREATE OR REPLACE VIEW v_investigation_summary AS
SELECT 
    investigation_id,
    case_name,
    status,
    wallets_count,
    transactions_count,
    total_volume_btc,
    average_risk_score,
    suspected_crime,
    created_at,
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - created_at)) as days_elapsed
FROM investigations
ORDER BY created_at DESC;

-- Comentários de documentação
COMMENT ON TABLE wallets IS 'Armazena informações de carteiras Bitcoin rastreadas';
COMMENT ON TABLE transactions IS 'Armazena transações entre wallets';
COMMENT ON TABLE investigations IS 'Armazena investigações de fraude';
COMMENT ON TABLE reports IS 'Armazena relatórios gerados';
COMMENT ON COLUMN wallets.risk_score IS 'Score de risco (0-100) calculado pelo Correlation Engine';
COMMENT ON COLUMN investigations.suspected_crime IS 'Tipo de crime suspeito (ransomware, scam, money_laundering, etc)';

-- Dados de exemplo para testes
INSERT INTO detection_rules (rule_id, name, description, weight) VALUES
    ('rule_mixer_001', 'Destination is Known Mixer', 'Carteira destino é um mixer conhecido', 30.0),
    ('rule_ransomware_001', 'Known Ransomware Wallet', 'Carteira está associada a ransomware', 50.0),
    ('rule_victims_001', 'Multiple Victims in 24h', '10+ remetentes em menos de 24h', 25.0),
    ('rule_exchange_001', 'Consolidation to Exchange', 'Fundos consolidados em exchange KYC', 15.0),
    ('rule_scam_001', 'Known Scam Wallet', 'Carteira listada como scam', 40.0)
ON CONFLICT (rule_id) DO NOTHING;

-- Permissões
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO crypto_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO crypto_user;
