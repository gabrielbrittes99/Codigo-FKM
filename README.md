# Sistema de Geração de FKMs - GRITSCH

Sistema automatizado para processamento de fechamento mensal de combustível e manutenção.

## 🚀 Como Usar (Simples e Rápido)

### Passo 1: Preparar os Arquivos

Coloque os arquivos Excel do mês na pasta do projeto:

- `Combustivel MMAA.xlsx` (exemplo: `Combustivel 0126.xlsx`)
- `Manutencao MMAA.xlsx` (exemplo: `Manutencao 0126.xlsx`)

### Passo 2: Executar o Menu Interativo

```bash
python run.py
```

Ou:

```bash
python -m src.menu_interativo
```

### Passo 3: Escolher a Opção

- **Opção 1**: Processar apenas Combustível
- **Opção 2**: Processar apenas Manutenção
- **Opção 3**: Processar TUDO (recomendado)

Pronto! O sistema vai:

- ✅ Detectar automaticamente o mês de fechamento (mês anterior ao atual)
- ✅ Encontrar os arquivos Excel automaticamente
- ✅ Gerar todos os relatórios nas pastas corretas

## 📅 Lógica de Fechamento

**IMPORTANTE:** O sistema processa o **mês anterior** (fechamento).

**Exemplos:**

- Rodando em **Fevereiro/2026** → Processa **Janeiro/2026**
- Rodando em **Março/2026** → Processa **Fevereiro/2026**
- Rodando em **Janeiro/2026** → Processa **Dezembro/2025**

## 📁 Estrutura de Arquivos

```
codigo-FKM/
├── src/                         # Código principal
│   ├── config.py                # Configuração automática
│   ├── menu_interativo.py       # Menu principal
│   ├── executar_resumos.py      # Processamento de combustível
│   ├── executar_manutencao.py   # Processamento de manutenção
│   ├── filial_mapping.py        # Mapeamento de filiais
│   ├── frota_mapping.py         # Mapeamento de frota
│   └── gerar_relatorio_kpis.py  # Geração de relatórios de KPIs
│
├── tests/                       # Testes automatizados
│   ├── test_quick.py
│   ├── test_normalizacao.py
│   ├── test_cwb_consolidacao.py
│   └── test_tbg7a13.py
│
├── tools/                       # Ferramentas de diagnóstico
│   ├── diagnostico_conferencia.py
│   ├── diagnostico_placa.py
│   └── analisar_datas_placa.py
│
├── modelos FKM/                 # Templates Excel
├── Dados Tratados/              # Saída de dados
│
├── run.py                       # Script de execução facilitado
├── README.md                    # Este arquivo
└── requirements.txt             # Dependências

(Arquivos Excel de entrada ficam no root)
```

## 🎯 Pastas de Saída

Os arquivos gerados são salvos em:

```
\\wsl.localhost\Ubuntu\home\gabriel\projetos\Dados Tratados\
└── Janeiro\
    ├── COMBUSTIVEL Janeiro 2026\
    │   ├── Combustivel - GRITSCH CSC.xlsx
    │   ├── Combustivel - GRITSCH POA.xlsx
    │   └── ... (um arquivo por filial)
    └── MANUTENÇÃO Janeiro 2026\
        ├── Manutencao - GRITSCH CSC.xlsx
        ├── Manutencao - GRITSCH POA.xlsx
        └── ... (um arquivo por filial)
```

## ⚙️ Configuração Manual (Opcional)

Se precisar forçar um mês/ano específico, edite o arquivo `src/config.py`:

```python
# Descomente estas linhas para forçar um período específico:
MES = "Janeiro"
ANO = "2026"
```

## 🔧 Executar Scripts Individualmente

Se preferir rodar sem o menu:

```bash
# Apenas combustível
python -m src.executar_resumos

# Apenas manutenção
python -m src.executar_manutencao

# Gerar relatório de KPIs
python -m src.gerar_relatorio_kpis

# Verificar configuração
python -m tests.test_quick
```

## 📊 O Que o Sistema Faz

### Combustível (`src/executar_resumos.py`)

- Separa combustível comum de Arla 32
- Agrupa por filial e placa
- Calcula hodômetros (inicial e final)
- Gera resumo por posto
- Aplica priorização de filial de manutenção

### Manutenção (`src/executar_manutencao.py`)

- Separa por natureza de manutenção
- Agrupa por filial e placa
- Calcula totais por natureza
- Layout lado a lado com cores da empresa

### Relatório de KPIs (`src/gerar_relatorio_kpis.py`)

- Enriquece dados com informações da frota
- Calcula indicadores de desempenho
- Gera relatórios consolidados

## 🛠️ Dependências

```bash
pip install -r requirements.txt
```

Ou manualmente:

```bash
pip install pandas openpyxl numpy
```

## 📝 Notas Importantes

1. **Nomes de Arquivos**: O sistema busca automaticamente arquivos que começam com "Combustivel" ou "Manutencao"
2. **Múltiplos Arquivos**: Se houver vários arquivos, usa o mais recente (por data de modificação)
3. **Filiais Especiais**: SAO FREGUESIA é automaticamente convertido para SAO PERUS
4. **Exceções de Placas**: Placas específicas têm filiais fixas (definidas em `src/filial_mapping.py`)

## ❓ Solução de Problemas

### Erro: "Arquivo não encontrado"

- Verifique se os arquivos Excel estão na pasta do projeto
- Verifique se os nomes começam com "Combustivel" ou "Manutencao"

### Erro: "Coluna não encontrada"

- Verifique se o arquivo Excel tem a estrutura esperada
- Verifique se as abas estão nomeadas corretamente

### Erro: "ModuleNotFoundError: No module named 'src'"

- Execute os scripts a partir do diretório raiz do projeto
- Use `python -m src.menu_interativo` ao invés de `python src/menu_interativo.py`

### Mês/Ano errado

- Edite `src/config.py` e descomente/modifique as variáveis MES e ANO

## 🧪 Testes

Execute os testes para validar o funcionamento:

```bash
# Teste rápido de configuração
python -m tests.test_quick

# Teste de normalização de filiais
python -m tests.test_normalizacao

# Teste de consolidação CWB
python -m tests.test_cwb_consolidacao

# Teste de placa específica
python -m tests.test_tbg7a13
```

## 🔍 Ferramentas de Diagnóstico

```bash
# Diagnóstico completo de conferência
python -m tools.diagnostico_conferencia

# Diagnóstico de placas
python -m tools.diagnostico_placa

# Análise de datas por placa
python -m tools.analisar_datas_placa
```

## 📧 Suporte

Para dúvidas ou problemas, verifique:

1. Os arquivos estão na pasta correta?
2. O mês/ano detectado está correto? (veja no menu)
3. As dependências estão instaladas? (`pip install -r requirements.txt`)
4. Está executando os scripts a partir do diretório raiz?

---

**Versão:** 3.0 - Organizada e Modular
**Última atualização:** Abril 2026
