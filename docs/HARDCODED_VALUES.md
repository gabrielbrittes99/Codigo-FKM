> 🗄️ **ARQUIVADO (revisão de 2026-08-27).** Este documento é uma auditoria pontual de Abril/2026 e está desatualizado: os valores concretos abaixo (contagens, linhas, arquivos citados) já não batem com o código atual — por exemplo `EXCECOES_FORCADAS` tinha 20 entradas então, hoje tem ~34, quase todas com destino diferente. Mantido como histórico/exemplo do tipo de auditoria a repetir. **A lista viva e atualizada de riscos e valores hardcoded é [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md).**

# Valores Hardcoded - Referência para Validação

## 📍 Alocação de Recursos - src/filial_mapping.py

### EXCECOES_FORCADAS (linhas 13-36)

Dicionário que força placas específicas para filiais fixas, **independente** da lógica temporal de manutenção.

```python
EXCECOES_FORCADAS = {
    "SEW5B72": "GRITSCH - FLN",
    "SDS3F58": "GRITSCH - CWB (BASE)",
    "SFD5C32": "GRITSCH - SNO",
    "SEF8G22": "GRITSCH - CWB (BASE)",
    "SFA0J37": "GRITSCH - CWB (BASE)",
    "SEP6E14": "GRITSCH - MGA",
    "SFD3E82": "GRITSCH - MGA (após 17/03)",
    "SFG4I55": "GRITSCH - MATRIZ",
    "SFI8F40": "GRITSCH - MATRIZ",
    "SFI8F53": "GRITSCH - CTB",       # Era MATRIZ, transferiu para CTB
    "TAS4H02": "GRITSCH - CXJ",
    "SDU9F54": "GRITSCH - CXJ",
    "SFI4A19": "GRITSCH - CXJ",
    "BCV9J79": "GRITSCH - CTB",
    "TBG7A13": "GRITSCH - CTB",
    "UAV5J75": "GRITSCH - PMW",
    "SFH5H88": "GRITSCH - BSB",
    "TBK1J46": "GRITSCH - SP",
    "SEH4I04": "GRITSCH - RVD",
    "TAS4H09": "GRITSCH - RVD",
    "TBK1J24": "GRITSCH - RVD",
    "TBW9G12": "GRITSCH - POA",
    "TBK1J34": "GRITSCH - RVD",
}
```

**⚠️ IMPORTANTE**: Estas placas têm prioridade máxima e SEMPRE vão para a filial especificada.

**❓ VALIDAR**:
- Estas 20 placas ainda devem ter alocação forçada?
- Alguma mudou de filial recentemente?
- SFI8F53: O comentário diz "transferiu de MATRIZ para CTB" - quando foi isso?

### PLACA_EXCECAO (linha 222)

```python
PLACA_EXCECAO = "TBU9D20"
```

Esta placa tem tratamento especial para aceitar filial "REFERÊNCIA CURITIBA" (normalmente filiais REFERÊNCIA são ignoradas).

**❓ VALIDAR**: Esta placa ainda precisa deste tratamento especial?

---

## 🆔 Exceções por ID de Transação - src/filial_mapping.py

### EXCECOES_TRANSACOES (linhas 34-64)

Dicionário que vincula IDs de transação específicos a filiais, independentemente da placa ou da data. Tem a **maior prioridade** no mapeamento.

**Atuais (Abril 2026):**
- 25 transações para **GRITSCH - CGB** (Cuiabá)

**Lógica**: Se o ID da transação estiver nesta lista, a filial será forçada para a configurada.

---

## 📄 Arquivos Hardcoded nos Testes

### tests/test_tbg7a13.py

```python
# Linha 8
mapa_filiais, mapa_datas = criar_mapa_filiais("Manutencao 0126.xlsx")

# Linha 11
df = pd.read_excel("Combustivel 0126.xlsx")
```

**Impacto**: Teste sempre usa dados de Janeiro/2026. Para testar meses recentes, precisa atualizar manualmente.

**Sugestão**: Usar `config.ARQUIVO_ENTRADA_MANUTENCAO` e `config.ARQUIVO_ENTRADA_COMBUSTIVEL`

---

### tests/test_cwb_consolidacao.py

```python
# Linha 13
mapa_filiais, mapa_datas = criar_mapa_filiais("Manutencao 0126.xlsx")

# Linha 32
df_comb = pd.read_excel("Combustivel 0126.xlsx")
```

**Impacto**: Mesmo problema - sempre usa Janeiro/2026.

**Sugestão**: Usar arquivos do config.py ou aceitar como parâmetro.

---

## 🔧 Arquivos Hardcoded nas Ferramentas

### tools/analisar_datas_placa.py

```python
# Linha 19
df_comb = pd.read_excel("Combustivel 0126.xlsx")

# Linha 44
df_manut = pd.read_excel("Manutencao 0126.xlsx")
```

**Impacto**: Ferramenta sempre analisa Janeiro/2026, não funciona para meses recentes.

**Sugestão**:
- Opção 1: Aceitar arquivo como argumento da linha de comando
- Opção 2: Usar config.py para pegar arquivos atuais
- Opção 3: Criar um menu para escolher o arquivo

---

## 📊 Planilhas no Projeto

### Root - Dados de Trabalho
```
Combustivel 0126.xlsx        - Janeiro/2026   (750KB)
Combustivel 0226.xlsx        - Fevereiro/2026 (676KB)
Combustivel 0326.xlsx        - Março/2026     (5.6MB)  ← ATUAL
Manutencao 0126.xlsx         - Janeiro/2026   (2.7MB)
Manutencao 0226.xlsx         - Fevereiro/2026 (3.8MB)
Manutencao 0326.xlsx         - Março/2026     (4.1MB)  ← ATUAL
Frota Gritsch 012026.xlsx    - Janeiro/2026   (37KB)
```

### Root - Planilhas de Teste/Diagnóstico
```
DIAGNOSTICO_0226_Fevereiro_2026.xlsx (9.2KB)
```

**Sugestão de Organização**:
1. Criar pasta `planilhas-antigas/` e mover 0126 e 0226
2. Criar pasta `planilhas-teste/` e mover DIAGNOSTICO
3. Manter 0326 (atual) no root para fácil acesso

---

## 🎯 Ações Sugeridas

### 1. Organizar Planilhas (Proposta Simples)

```
codigo-FKM/
├── planilhas-antigas/
│   ├── 2026-01/
│   │   ├── Combustivel_0126.xlsx
│   │   ├── Manutencao_0126.xlsx
│   │   └── Frota_Gritsch_012026.xlsx
│   └── 2026-02/
│       ├── Combustivel_0226.xlsx
│       └── Manutencao_0226.xlsx
│
├── planilhas-teste/
│   └── DIAGNOSTICO_0226_Fevereiro_2026.xlsx
│
├── Combustivel_0326.xlsx    ← Atual (mantém no root)
├── Manutencao_0326.xlsx     ← Atual (mantém no root)
└── ...
```

### 2. Atualizar .gitignore

Adicionar:
```gitignore
# Planilhas antigas arquivadas
planilhas-antigas/

# Planilhas de teste
planilhas-teste/
```

### 3. Atualizar Testes para Usar config.py

Em vez de:
```python
df = pd.read_excel("Combustivel 0126.xlsx")
```

Usar:
```python
from src import config
df = pd.read_excel(config.ARQUIVO_ENTRADA_COMBUSTIVEL)
```

### 4. Atualizar Ferramentas

Adicionar argumento de linha de comando:
```python
import sys
arquivo = sys.argv[1] if len(sys.argv) > 1 else config.ARQUIVO_ENTRADA_COMBUSTIVEL
df = pd.read_excel(arquivo)
```

---

## ❓ Checklist de Validação

- [ ] Validar EXCECOES_FORCADAS (20 placas)
- [ ] Validar PLACA_EXCECAO (TBU9D20)
- [ ] Decidir organização de planilhas
- [ ] Atualizar testes para usar config.py
- [ ] Atualizar ferramentas para usar config.py ou argumentos
- [ ] Mover planilhas antigas
- [ ] Atualizar .gitignore

---

**Gerado em**: Abril 2026
**Versão do Projeto**: 3.0
