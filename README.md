# 🚚 Sistema de Fechamento de FKM, KPIs e Torre de Controle — GRITSCH

Sistema automatizado de alta precisão para **extração, tratamento, rateio temporal, auditoria e fechamento mensal** das informações de **Frota, Combustível e Manutenção**, além de relatórios executivos para a **Torre de Controle** da **GRITSCH**.

---

## 📌 Sumário
- [Visão Geral e Arquitetura](#-visão-geral-e-arquitetura)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [🛠️ Configuração Inicial do Ambiente](#%EF%B8%8F-configuração-inicial-do-ambiente)
- [⚙️ Variáveis de Ambiente (.env)](#%EF%B8%8F-variáveis-de-ambiente-env)
- [🚀 Fluxo Completo de Fechamento Mensal](#-fluxo-completo-de-fechamento-mensal)
- [🕵️ Auditoria e Validação de FKMs Retornados](#%EF%B8%8F-auditoria-e-validação-de-fkms-retornados)
- [📊 Relatórios da Torre de Controle (PDF Executivo)](#-relatórios-da-torre-de-controle-pdf-executivo)
- [📧 Disparo Automático de E-mails para Gestores](#-disparo-automático-de-e-mails-para-gestores)
- [🔧 Mapeamentos Especiais e Exceções](#-mapeamentos-especiais-e-exceções)
- [❓ Troubleshooting e Solução de Problemas](#-troubleshooting-e-solução-de-problemas)
- [📚 Documentação de Handoff](#-documentação-de-handoff)

---

## 🏢 Visão Geral e Arquitetura

O sistema integra múltiplas fontes de dados da empresa para eliminar custos perdidos, divergências de cartões e falhas de preenchimento dos FKMs pelas filiais operacionais.

```
                    ┌─────────────────────────┐
                    │  Bluefleet (SQL Server) │ ──> Frota & Manutenção
                    └─────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │  PostgreSQL (DW Torre)  │ ──> Combustível (TruckPag)
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     fechar_mes.py       │ ──> Consolidação & Rateios Temporais
                    └─────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌─────────────────────┐
│ Dados Tratados/  │   │  Auditoria FKM   │   │  Torre de Controle  │
│ (28+ Filiais)    │   │ (Retornos/Erros) │   │   (Relatórios PDF)  │
└──────────────────┘   └──────────────────┘   └─────────────────────┘
```

---

## 📁 Estrutura do Projeto

```text
codigo-FKM/
├── fechar_mes.py                 # Script orquestrador principal do fechamento mensal
├── src/                          # Módulos principais de tratamento e geração
│   ├── config.py                 # Configurações globais, período (Mês/Ano) e paths
│   ├── filial_mapping.py         # Regras de normalização, exceções manuais e busca no DB
│   ├── frota_mapping.py          # Higienização e enriquecimento da frota
│   ├── extrair_dados_bluefleet.py # Extração de dados brutos SQL Server & PostgreSQL DW
│   ├── executar_frota.py         # Gerador de relatórios de Frota por filial
│   ├── executar_resumos.py       # Gerador de relatórios de Combustível por filial
│   ├── executar_manutencao.py    # Gerador de relatórios de Manutenção por filial
│   ├── gerar_relatorio_kpis.py   # Gerador do Relatório Consolidado de KPIs (10 abas Excel)
│   ├── enviar_emails.py          # Envio automático das planilhas para cada gestor
│   ├── gerar_pdf_mensal.py       # Gerador do PDF Executivo Mensal da Torre
│   ├── gerar_pdf_torre.py        # Gerador do PDF Executivo Semestral da Torre
│   ├── torre_dados.py            # Extração de inteligência e cálculo dos KPIs da Torre
│   └── torre_layout.py           # Design System (Cores, Fontes e Layouts ReportLab PDF)
├── tools/                        # Ferramentas de auditoria e operações pontuais
│   ├── validar_retorno_fkms.py   # Auditor automático dos FKMs retornados pelas filiais
│   ├── arquivar_mes.py           # Ferramenta para arquivamento do fechamento
│   └── gerar_fkm_matriz.py       # Consolidador de custos excedentes da Matriz/Diretoria
├── dados/
│   ├── entrada/                  # Planilhas brutas oficiais do mês (Frota, Combustível)
│   ├── retornados/               # FKMs preenchidos e devolvidos pelos gestores
│   ├── historico/                # Base histórica de fechamentos
│   ├── emails_filiais.csv        # Cadastro de e-mails dos gestores das filiais
│   └── cache/                    # Cache local para aceleração dos relatórios PDF
├── Dados Tratados/               # Saída final organizada por filial em subpastas
├── conteudo_mensal.yaml          # Análises executivas do relatório mensal
└── conteudo_torre.yaml           # Análises executivas do relatório semestral
```

---

## 🛠️ Configuração Inicial do Ambiente

### 1. Clonar o Repositório e Criar o Ambiente Virtual

#### **Linux / macOS (Bash / Zsh):**
```bash
# 1. Clonar o repositório
git clone https://github.com/sua-empresa/codigo-FKM.git
cd codigo-FKM

# 2. Criar o ambiente virtual
python3 -m venv .venv

# 3. Ativar o ambiente virtual
source .venv/bin/activate

# 4. Atualizar pip e instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# 5. Instalar o projeto em modo editável (Essencial para resolver imports da pasta src)
pip install -e .
```

#### **Linux (Fish Shell):**
```fish
python3 -m venv .venv
source .venv/bin/activate.fish
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

#### **Windows (PowerShell / CMD):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

> 💡 **Dica:** Certifique-se de que o terminal exiba o prefixo `(.venv)` indicando que o ambiente virtual está ativo.

---

## ⚙️ Variáveis de Ambiente (.env)

Crie um arquivo `.env` na raiz do projeto com as credenciais dos bancos de dados e servidor SMTP:

```env
# Banco Bluefleet (SQL Server - Frota e Manutenção)
DB_HOST=bi.bluefleet.com.br
DB_NAME=referencia
DB_USER=seu_usuario
DB_PASSWORD=sua_senha

# PostgreSQL DW (Torre / Combustível TruckPag)
DW_HOST=192.168.0.37
DW_PORT=5433
DW_NAME=dw
DW_USER=seu_usuario
DW_PASSWORD=sua_senha
DW_SCHEMA=torre

# Servidor SMTP de E-mails
SMTP_HOST=smtp.gritsch.com.br
SMTP_PORT=587
SMTP_USER=naoresponda@gritsch.com.br
SMTP_PASSWORD=sua_senha
```

---

## 🚀 Fluxo Completo de Fechamento Mensal

### **Passo 1: Definir Mês e Ano de Fechamento**
Edite as variáveis `MES` e `ANO` no arquivo [`src/config.py`](file:///home/gabriel/Projetos/codigo-FKM/src/config.py):
```python
MES = "Julho"
ANO = 2026
```

### **Passo 2: Executar o Processamento Completo**
Rode o script orquestrador que executa todas as etapas de extração, tratamento, conciliação e geração dos relatórios:

```bash
python fechar_mes.py
```

O script irá executar em sequência:
1. 🔄 **Extração dos dados brutos** do SQL Server e PostgreSQL DW.
2. 🚙 **Geração das Planilhas de Frota** por filial com datas de transferência.
3. ⛽ **Geração dos Resumos de Combustível** por filial (Rateio por movimentações).
4. 🔧 **Geração dos Resumos de Manutenção** por filial.
5. 📊 **Geração do Relatório Consolidado de KPIs** (Excel de 10 abas em `Dados Tratados/[Mês Ano]/`).

---

## 🕵️ Auditoria e Validação de FKMs Retornados

Quando os gestores das filiais preencherem e devolverem suas planilhas de FKM, salve os arquivos na pasta `dados/retornados/` e execute o validador automático:

```bash
python -m tools.validar_retorno_fkms
```

### **O que o Validador Audita:**
- ✅ **Completude da Frota:** Garante que todos os veículos pertencentes à filial constam no FKM enviado.
- 🚫 **Placas Extras/Erros de Digitação:** Identifica placas preenchidas incorretamente pelo gerente ou divergentes.
- ⛽ **Valores de Combustível e Arla:** Compara os valores preenchidos contra os abastecimentos oficiais da TruckPag. Filiais com compra direta no mês (fora da TruckPag) não são reprovadas por valor "a maior" — a compra direta não tem placa associada no financeiro, então não dá pra conferir o valor exato linha a linha.
- 💸 **Compra Direta do Mês (fora da TruckPag):** Não é mais uma auditoria — o relatório só lista, por filial, quanto teve de combustível e Arla comprado fora da TruckPag (informativo, para saber quem cobrar).
- 🔧 **Manutenções e OSs Transferidas:** Alerta caso manutenções redirecionadas via exceção não tenham sido declaradas pelo gestor destino.

### **Resumo dos Status na Tela:**
- 🟢 **APROVADO (100% OK):** Dados totalmente consistentes com os sistemas oficiais.
- 🚨 **REJEITADO:** Erros graves que exigem correção pelo gerente (placas faltantes, divergências de valores).

---

## 📊 Relatórios da Torre de Controle (PDF Executivo)

O sistema gera relatórios executivos de alto nível em formato PDF com gráficos, tabelas comparativas e análises narrativas.

| Relatório | Comando | Frequência & Objetivo |
| :--- | :--- | :--- |
| **PDF Mensal** | `python -m src.gerar_pdf_mensal --mes 7 --ano 2026` | Comparativo do mês fechado vs mês anterior + acumulado do ano |
| **PDF Semestral** | `python -m src.gerar_pdf_torre` | Análise semestral por bimestres (B1 vs B2 vs B3) |

> ⚡ **Aceleração por Cache:** A primeira execução salva o cache dos bancos em `dados/cache/`. As execuções subsequentes rodam em poucos segundos. Use a flag `--sem-cache` para forçar atualização no banco.

### **Textos, observações e ações**

Os números vêm dos bancos; os textos ficam em [`conteudo_mensal.yaml`](file:///home/gabriel/Projetos/codigo-FKM/conteudo_mensal.yaml) e [`conteudo_torre.yaml`](file:///home/gabriel/Projetos/codigo-FKM/conteudo_torre.yaml):

- **`observacoes:`** — existe em toda página, para comentar aquele gráfico. Vazio, o box não é impresso.
- **Última página** — espaço livre com blocos para *o que melhoramos*, *ações em andamento* e *pontos de atenção*.
- **`habilitada: false`** — remove a página do PDF.
- **`{placeholders}`** — trocados pelos valores calculados. Ex.: `"O custo por km ficou em {mes_ckm}, {var_ckm_sinal} vs {mes_anterior}."` vira `"O custo por km ficou em R$ 1,24, -2,4% vs Junho."` A lista completa está comentada no topo de cada YAML.

### **Formato dos números**

Todo valor monetário sai com **2 casas decimais no padrão brasileiro** (`R$ 1.234,56`). A formatação é centralizada em [`src/torre_layout.py`](file:///home/gabriel/Projetos/codigo-FKM/src/torre_layout.py) — nunca formate no meio do código, use os helpers:

| Helper | Saída | Onde usar |
| :--- | :--- | :--- |
| `moeda()` | `R$ 2,94M` / `R$ 684,24K` | Cards e rótulos curtos (escala automática) |
| `moeda_cheia()` | `R$ 2.941.567,89` | Valor completo, sem escala |
| `moeda_k()` | `R$ 1.212,45K` | Rótulo de gráfico cujo eixo já está em milhares |
| `valor_km()` | `R$ 1,24/km` | Custo por quilômetro |
| `valor_litro()` | `R$ 6,42/L` | Preço do diesel |
| `numero_br()` | `1.212,45` | Coluna de tabela, sem o símbolo |

Para mudar a quantidade de casas em todo o relatório, altere `CASAS_MOEDA` em `torre_layout.py`.

---

## 📧 Disparo Automático de E-mails para Gestores

Após a validação dos arquivos, você pode enviar automaticamente o kit de fechamento para cada filial:

```bash
python -m src.enviar_emails
```

> ⚠️ **Os destinatários NÃO vêm do arquivo `dados/emails_filiais.csv`.** Esse CSV é mantido manualmente como referência humana, mas o script lê a lista real de destinatários (e-mail, cópia, ativo/inativo) diretamente da tabela **`torre.email_gritsch_filiais`** no PostgreSQL (DW). Para adicionar/trocar um destinatário, é preciso dar `UPDATE`/`INSERT` **nessa tabela** — editar só o CSV não tem nenhum efeito no envio real. Vale manter o CSV atualizado mesmo assim, como registro legível para humanos, mas sincronizando manualmente com o banco. Não existe flag `--teste`; o script sempre envia para os destinatários ativos cadastrados no banco.

---

## 🔧 Mapeamentos Especiais e Exceções

O arquivo [`src/filial_mapping.py`](file:///home/gabriel/Projetos/codigo-FKM/src/filial_mapping.py) permite configurar ajustes temporários do fechamento atual:

- **`EXCECOES_FORCADAS`**: Redireciona combustível e frota de uma placa para uma filial específica.
- **`EXCECOES_MANUTENCAO`**: Redireciona **apenas a manutenção** de uma placa específica (mantendo combustível na filial de origem).
- **`PLACAS_EXCLUIDAS`**: Placas desmobilizadas, sinistradas ou disponíveis para venda que devem ser removidas da frota operacional.

---

## ❓ Troubleshooting e Solução de Problemas

### **1. `ModuleNotFoundError: No module named 'src'`**
Execute a instalação do pacote local em modo editável:
```bash
pip install -e .
```

### **2. `Can't open lib 'ODBC Driver 17/18 for SQL Server'`**
Garantir que os drivers de SQL Server estejam instalados no SO Linux:
```bash
sudo apt-get install -y msodbcsql18
```

### **3. Dúvidas ou Suporte**
- **Equipe:** Engenharia de Dados & Torre de Controle FKM — GRITSCH
- **Versão:** 2.0.0 (Julho/2026)

---

## 📚 Documentação de Handoff

Revisão completa do projeto feita em 2026-08-27. Para arquitetura detalhada, runbook operacional passo a passo, débito técnico/riscos conhecidos, dicionário de dados e checklist de acessos, veja o índice em [`docs/README.md`](docs/README.md).
