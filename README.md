# Sistema de Geração de FKMs - GRITSCH

Sistema automatizado para processamento de fechamento mensal de combustível e manutenção.

## 🚀 Como Usar (Simples e Rápido)

### Passo 1: Preparar os Arquivos

Coloque os arquivos Excel do mês na pasta do projeto:

- `Combustivel MMAA.xlsx` (exemplo: `Combustivel 0126.xlsx`)
- `Manutencao MMAA.xlsx` (exemplo: `Manutencao 0126.xlsx`)

### Passo 2: Executar o Menu Interativo

```bash
python menu_interativo.py
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
├── config.py                    # Configuração automática (detecta mês/ano e arquivos)
├── menu_interativo.py           # Menu principal (USE ESTE!)
├── executar_resumos.py          # Processamento de combustível
├── executar_manutencao.py       # Processamento de manutenção
├── filial_mapping.py            # Mapeamento de filiais e exceções
├── Combustivel 0126.xlsx        # Arquivo de entrada (exemplo)
├── Manutencao 0126.xlsx         # Arquivo de entrada (exemplo)
└── README.md                    # Este arquivo
```

## 🎯 Pastas de Saída

Os arquivos gerados são salvos em:

```
\\wsl.localhost\Ubuntu\home\gabriel\projetos\Arquivos FKMs\
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

Se precisar forçar um mês/ano específico, edite o arquivo `config.py`:

```python
# Descomente estas linhas para forçar um período específico:
MES = "Janeiro"
ANO = "2026"
```

## 🔧 Executar Scripts Individualmente

Se preferir rodar sem o menu:

```bash
# Apenas combustível
python executar_resumos.py

# Apenas manutenção
python executar_manutencao.py

# Verificar configuração
python config.py
```

## 📊 O Que o Sistema Faz

### Combustível (`executar_resumos.py`)

- Separa combustível comum de Arla 32
- Agrupa por filial e placa
- Calcula hodômetros (inicial e final)
- Gera resumo por posto
- Aplica priorização de filial de manutenção

### Manutenção (`executar_manutencao.py`)

- Separa por natureza de manutenção
- Agrupa por filial e placa
- Calcula totais por natureza
- Layout lado a lado com cores da empresa

## 🛠️ Dependências

```bash
pip install pandas openpyxl numpy
```

## 📝 Notas Importantes

1. **Nomes de Arquivos**: O sistema busca automaticamente arquivos que começam com "Combustivel" ou "Manutencao"
2. **Múltiplos Arquivos**: Se houver vários arquivos, usa o mais recente (por data de modificação)
3. **Filiais Especiais**: SAO FREGUESIA é automaticamente convertido para SAO PERUS
4. **Exceções de Placas**: Placas específicas têm filiais fixas (definidas em `filial_mapping.py`)

## ❓ Solução de Problemas

### Erro: "Arquivo não encontrado"

- Verifique se os arquivos Excel estão na pasta do projeto
- Verifique se os nomes começam com "Combustivel" ou "Manutencao"

### Erro: "Coluna não encontrada"

- Verifique se o arquivo Excel tem a estrutura esperada
- Verifique se as abas estão nomeadas corretamente

### Mês/Ano errado

- Edite `config.py` e descomente/modifique as variáveis MES e ANO

## 📧 Suporte

Para dúvidas ou problemas, verifique:

1. Os arquivos estão na pasta correta?
2. O mês/ano detectado está correto? (veja no menu)
3. As dependências estão instaladas? (`pip install -r requirements.txt`)

---

**Versão:** 2.0 - Automatizada  
**Última atualização:** Fevereiro 2026
