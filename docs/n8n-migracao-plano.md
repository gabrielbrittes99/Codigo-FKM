# Plano de Migração para n8n - FKM Data Warehouse

## Objetivo
Migrar a criação e população das tabelas do Data Warehouse do código Python para workflows no n8n.

---

## 1. Estrutura das Tabelas

### 1.1 Tabela: filiais
```sql
CREATE TABLE IF NOT EXISTS torre.filiais (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(20) UNIQUE NOT NULL,
    nome            VARCHAR(100) NOT NULL,
    nome_exibicao   VARCHAR(100),
    ativo           BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

**Dados para inserir:**
```sql
INSERT INTO torre.filiais (codigo, nome, nome_exibicao) VALUES
('GRITSCH - BLN', 'Blumenau', 'GRITSCH - BLN'),
('GRITSCH - BSB', 'Brasília', 'GRITSCH - BSB'),
('GRITSCH - CGB', 'Campo Grande', 'GRITSCH - CGB'),
('GRITSCH - CSC', 'Caxias do Sul', 'GRITSCH - CSC'),
('GRITSCH - CHA', 'Chapecó', 'GRITSCH - CHA'),
('GRITSCH - CRI', 'Criciuma', 'GRITSCH - CRI'),
('GRITSCH - CUI', 'Cuiabá', 'GRITSCH - CUI'),
('GRITSCH - CTB', 'Curitiba', 'GRITSCH - CTB'),
('GRITSCH - CBN', 'Curitibanos', 'GRITSCH - CBN'),
('GRITSCH - FLN', 'Florianópolis', 'GRITSCH - FLN'),
('GRITSCH - GOI', 'Goiânia', 'GRITSCH - GOI'),
('GRITSCH - GPA', 'Guarapuava', 'GRITSCH - GPA'),
('GRITSCH - ITR', 'Itumbiara', 'GRITSCH - ITR'),
('GRITSCH - JOI', 'Joinville', 'GRITSCH - JOI'),
('GRITSCH - LDB', 'Londrina', 'GRITSCH - LDB'),
('GRITSCH - MGA', 'Maringá', 'GRITSCH - MGA'),
('GRITSCH - PMW', 'Palmas', 'GRITSCH - PMW'),
('GRITSCH - PBC', 'Pato Branco', 'GRITSCH - PBC'),
('GRITSCH - PGR', 'Ponta Grossa', 'GRITSCH - PGR'),
('GRITSCH - POA', 'Porto Alegre', 'GRITSCH - POA'),
('GRITSCH - RVD', 'Rio Verde', 'GRITSCH - RVD'),
('GRITSCH - RDN', 'Rondonópolis', 'GRITSCH - RDN'),
('GRITSCH - SSA', 'Salvador', 'GRITSCH - SSA'),
('GRITSCH - SNO', 'Sinop', 'GRITSCH - SNO'),
('GRITSCH - SAO', 'São Paulo (Perus)', 'GRITSCH - SAO (PERUS)'),
('GRITSCH - CWB', 'Curitiba (Base)', 'GRITSCH - CWB (BASE)'),
('GRITSCH - CXJ', 'Caxias do Sul', 'GRITSCH - CXJ');
```

---

### 1.2 Tabela: grupos_veiculo
```sql
CREATE TABLE IF NOT EXISTS torre.grupos_veiculo (
    id                  SERIAL PRIMARY KEY,
    grupo_bluefleet     VARCHAR(100) UNIQUE NOT NULL,
    grupo_simplificado  VARCHAR(50) NOT NULL
);
```

**Dados para inserir:**
```sql
INSERT INTO torre.grupos_veiculo (grupo_bluefleet, grupo_simplificado) VALUES
('Leve', 'Leve'),
('Médio', 'Médio'),
('Pesado', 'Pesado'),
('Kombi', 'Kombi'),
('Moto', 'Moto'),
('Reboque', 'Reboque'),
('Caminhão 4.2 Ton', 'Leve'),
('Caminhão 5 Ton', 'Leve'),
('Caminhão 5.5 Ton', 'Leve'),
('Caminhão 6 Ton', 'Médio'),
('Caminhão 7.5 Ton', 'Médio'),
('Caminhão 9 Ton', 'Pesado'),
('Caminhão 10.5 Ton', 'Pesado'),
('Caminhão 12 Ton', 'Pesado'),
('Caminhão 17 Ton', 'Pesado');
```

---

### 1.3 Tabela: tipos_combustivel
```sql
CREATE TABLE IF NOT EXISTS torre.tipos_combustivel (
    id       SERIAL PRIMARY KEY,
    nome     VARCHAR(50) NOT NULL UNIQUE,
    is_arla  BOOLEAN DEFAULT FALSE
);
```

**Dados para inserir:**
```sql
INSERT INTO torre.tipos_combustivel (nome, is_arla) VALUES
('Diesel', FALSE),
('Diesel S10', FALSE),
('Etanol', FALSE),
('Gasolina', FALSE),
('Arla 32', TRUE);
```

---

### 1.4 Tabela: dias_uteis
```sql
CREATE TABLE IF NOT EXISTS torre.dias_uteis (
    id          SERIAL PRIMARY KEY,
    ano         INTEGER NOT NULL,
    mes         INTEGER NOT NULL,
    dias_uteis  INTEGER NOT NULL,
    UNIQUE (ano, mes)
);
```

---

### 1.5 Tabela: veiculos_rastreador
```sql
CREATE TABLE IF NOT EXISTS torre.veiculos_rastreador (
    id              SERIAL PRIMARY KEY,
    placa           VARCHAR(20) NOT NULL,
    rastreador      VARCHAR(100) NOT NULL,
    is_gr_parceria  BOOLEAN DEFAULT FALSE,
    data_inicio     DATE,
    data_fim        DATE,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

### 1.6 Tabela: contratos
```sql
CREATE TABLE IF NOT EXISTS torre.contratos (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(200) NOT NULL,
    tipo_rota   VARCHAR(50),
    id_filial   INTEGER REFERENCES torre.filiais(id),
    ativo       BOOLEAN DEFAULT TRUE,
    data_inicio DATE,
    data_fim    DATE,
    observacao  TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);
```

**Dados para inserir (exemplo):**
```sql
INSERT INTO torre.contratos (nome, tipo_rota, id_filial, ativo) VALUES
('Administrativo - Sinop', 'Administrativo', 25, TRUE),
('Cargas - Sinop', 'Rodoviário', 25, TRUE),
('Administrativo - Curitiba', 'Administrativo', 9, TRUE),
('Cargas - Curitiba', 'Rodoviário', 9, TRUE);
-- CONTINUAR COM OS DEMAIS CONTRATOS...
```

---

### 1.7 Tabela: veiculos_contratos
```sql
CREATE TABLE IF NOT EXISTS torre.veiculos_contratos (
    id           SERIAL PRIMARY KEY,
    placa        VARCHAR(20) NOT NULL,
    id_contrato  INTEGER REFERENCES torre.contratos(id),
    motorista    VARCHAR(200),
    data_inicio  DATE NOT NULL,
    data_fim     DATE,
    observacao   TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
```

---

### 1.8 Tabela: mapeamento_naturezas
```sql
CREATE TABLE IF NOT EXISTS torre.mapeamento_naturezas (
    id                   SERIAL PRIMARY KEY,
    descricao_completa   VARCHAR(200) NOT NULL UNIQUE,
    natureza_vinculada   VARCHAR(200) NOT NULL,
    created_at           TIMESTAMP DEFAULT NOW()
);
```

**Dados para inserir:**
```sql
INSERT INTO torre.mapeamento_naturezas (descricao_completa, natureza_vinculada) VALUES
('Troca de óleo', 'Manutenção'),
('Troca de filtro', 'Manutenção'),
('Troca de pneu', 'Rodas/Pneus'),
('Recapagem', 'Rodas/Pneus'),
('Alinhamento', 'Manutenção'),
('Balanceamento', 'Manutenção'),
('Revisão', 'Manutenção'),
('Lataria', 'Lataria/Pintura'),
('Pintura', 'Lataria/Pintura');
```

---

### 1.9 Tabela: combustivel_raw
```sql
CREATE TABLE IF NOT EXISTS torre.combustivel_raw (
    id                      BIGINT PRIMARY KEY,
    transacao               VARCHAR(100),
    data_transacao          TIMESTAMP,
    hodometro               INTEGER,
    valor                   DECIMAL(12,2),
    litragem                DECIMAL(10,3),
    nome_combustivel        VARCHAR(100),
    is_arla                 BOOLEAN DEFAULT FALSE,
    placa                   VARCHAR(20),
    motorista               VARCHAR(200),
    marca_veiculo           VARCHAR(100),
    modelo_veiculo          VARCHAR(200),
    razao_social_posto      VARCHAR(200),
    cidade_posto            VARCHAR(100),
    uf_posto                VARCHAR(5),
    mes_referencia          INTEGER,
    ano_referencia          INTEGER,
    synced_at               TIMESTAMP DEFAULT NOW()
);
```

---

### 1.10 Tabela: manutencao_raw
```sql
CREATE TABLE IF NOT EXISTS torre.manutencao_raw (
    id_nf                   BIGINT,
    placa                   VARCHAR(20),
    descricao_item          TEXT,
    tipo_item               VARCHAR(50),
    quantidade              DECIMAL(10,3),
    valor_unitario          DECIMAL(12,2),
    valor_total             DECIMAL(12,2),
    data_emissao            DATE,
    data_entrada            DATE,
    data_criacao            TIMESTAMP,
    filial_operacional      VARCHAR(200),
    filial_calculada        VARCHAR(200),
    natureza_correta        VARCHAR(200),
    natureza_financeira     VARCHAR(200),
    fornecedor              VARCHAR(200),
    situacao_ocorrencia     VARCHAR(100),
    mes_referencia          INTEGER,
    ano_referencia          INTEGER,
    synced_at               TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id_nf, placa, descricao_item)
);
```

---

### 1.11 Tabela: veiculos_raw
```sql
CREATE TABLE IF NOT EXISTS torre.veiculos_raw (
    placa                   VARCHAR(20) PRIMARY KEY,
    modelo                  VARCHAR(200),
    montadora               VARCHAR(200),
    grupo_veiculo_bf        VARCHAR(100),
    grupo_simplificado      VARCHAR(50),
    filial_operacional      VARCHAR(200),
    situacao_veiculo        VARCHAR(100),
    ano_modelo              INTEGER,
    synced_at               TIMESTAMP DEFAULT NOW()
);
```

---

### 1.12 Tabela: indicadores_fkm
```sql
CREATE TABLE IF NOT EXISTS torre.indicadores_fkm (
    id               SERIAL PRIMARY KEY,
    mes_referencia   INTEGER NOT NULL,
    ano_referencia   INTEGER NOT NULL,
    placa            VARCHAR(20) NOT NULL,
    id_filial        INTEGER REFERENCES torre.filiais(id),
    filial           VARCHAR(200),
    modelo           VARCHAR(200),
    grupo_veiculo    VARCHAR(50),
    marca            VARCHAR(100),
    tipo_combustivel VARCHAR(100),
    tipo_rota        VARCHAR(50),
    id_contrato      INTEGER REFERENCES torre.contratos(id),
    contrato_nome    VARCHAR(200),
    motorista        VARCHAR(200),
    tem_gr_parceria  BOOLEAN DEFAULT FALSE,
    km_inicial       INTEGER,
    km_final         INTEGER,
    total_km         INTEGER,
    litros_comb      DECIMAL(12,3),
    valor_comb       DECIMAL(12,2),
    media_kml        DECIMAL(10,4),
    comb_por_km      DECIMAL(10,4),
    arla             DECIMAL(12,3),
    lataria_pintura  DECIMAL(12,2),
    manutencao_geral DECIMAL(12,2),
    rodas_pneus      DECIMAL(12,2),
    man_por_km       DECIMAL(10,4),
    total            DECIMAL(12,2),
    origem           VARCHAR(20) DEFAULT 'ETL',
    calculado_em     TIMESTAMP DEFAULT NOW(),
    UNIQUE (mes_referencia, ano_referencia, placa)
);
```

---

### 1.13 Tabela: fkm_resumo
```sql
CREATE TABLE IF NOT EXISTS torre.fkm_resumo (
    id                  SERIAL PRIMARY KEY,
    mes_referencia      INTEGER NOT NULL,
    ano_referencia      INTEGER NOT NULL,
    id_filial           INTEGER REFERENCES torre.filiais(id),
    filial              VARCHAR(200),
    qtd_veiculos        INTEGER,
    total_km            INTEGER,
    litros_comb         DECIMAL(14,3),
    valor_comb          DECIMAL(14,2),
    media_kml           DECIMAL(10,4),
    comb_por_km         DECIMAL(10,4),
    total_manutencao    DECIMAL(14,2),
    man_por_km          DECIMAL(10,4),
    total               DECIMAL(14,2),
    km_por_dia          DECIMAL(10,2),
    litros_por_dia      DECIMAL(10,3),
    valor_por_dia       DECIMAL(10,2),
    calculado_em        TIMESTAMP DEFAULT NOW(),
    UNIQUE (mes_referencia, ano_referencia, filial)
);
```

---

## 2. Fluxo Sugerido no n8n

### Workflow 1: Setup Inicial (executar uma vez)
```
┌─────────────────────────────────────────────────────────┐
│  Manual Trigger (Once)                                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: CREATE TABLE filiais                       │
│  (executar CREATE TABLE de cada tabela)                │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO filiais                        │
│  (popular tabelas de dimensões)                         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO grupos_veiculo                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO tipos_combustivel              │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO contratos                      │
│  (com dados que você precisa)                           │
└─────────────────────────────────────────────────────────┘
```

### Workflow 2: Sync Mensal (Fechamento)
```
┌─────────────────────────────────────────────────────────┐
│  Schedule Trigger (mensal - dia 1)                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Excel/CSV Reader: Combustivel                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Transform: Processar dados                              │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: TRUNCATE combustivel_raw                    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO combustivel_raw                 │
│  (bulk insert)                                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Excel/CSV Reader: Manutencao                            │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO manutencao_raw                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Excel/CSV Reader: Frota/Veiculos                       │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO veiculos_raw                   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO indicadores_fkm                 │
│  (calcular KPIs)                                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL: INSERT INTO fkm_resumo                     │
│  (resumo por filial)                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Queries Úteis no n8n

### Ler dados de uma tabela:
```sql
SELECT * FROM torre.filiais ORDER BY id;
```

### Atualizar contratos com filial:
```sql
UPDATE torre.contratos 
SET id_filial = {id_filial}
WHERE nome LIKE '%{nome_filial}%';
```

### Verificar dados:
```sql
SELECT table_name, (SELECT COUNT(*) FROM torre.{table_name}) as cnt
FROM information_schema.tables 
WHERE table_schema = 'torre';
```

### Truncate antes de recarregar:
```sql
TRUNCATE TABLE torre.combustivel_raw RESTART IDENTITY CASCADE;
```

---

## 4. Próximos Passos

1. **Criar as tabelas** - Executar os CREATE TABLE no n8n
2. **Popular dimensões** - filiais, grupos_veiculo, tipos_combustivel
3. **Popular contratos** - Com os dados corretos que você precisa
4. **Testar sync** - Fazer um teste com dados de combustível
5. **Automatizar** - Colocar em schedule mensal

---

## 5. Variáveis de Conexão (para configurar no n8n)

| Variável | Valor |
|----------|-------|
| Host | 192.168.0.37 |
| Porta | 5433 |
| Database | dw |
| Schema | torre |
| Usuário | gabriel_brittes |
| Senha | OKkK5yGSO6hxAU |
