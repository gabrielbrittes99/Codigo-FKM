# Sistema de Fechamento de FKM e KPIs - GRITSCH

Sistema totalmente automatizado para extração, processamento e fechamento mensal das informações de Frota, Manutenção e Combustível.

## 🚀 Como Usar (Workflow Automatizado 2026)

### Passo 1: Inserir a Planilha de Combustível

Para realizar o fechamento, o sistema precisa de apenas **um arquivo manual**:

- Coloque o arquivo de combustível do mês na pasta `dados/entrada/` do projeto.
- Exemplo: `dados/entrada/Combustivel 0426.xlsx`

_(Obs: Os arquivos de Manutenção e Frota não precisam ser extraídos manualmente. O sistema fará o download direto do banco de dados Bluefleet e os salvará automaticamente nesta mesma pasta)._

### Passo 2: Ajustes Manuais por Placa (Opcional)

Se ao longo dos meses você precisar forçar alguma placa para uma filial específica (ex: uma filial que ainda não existe no sistema), você pode criar um arquivo chamado `ajustes_placas.csv` na pasta raiz do projeto.

**Formato do `ajustes_placas.csv`:**

```csv
Placa,Filial
ABC1234,GRITSCH - NOVA FILIAL
XYZ9876,GRITSCH - OUTRA
```

O sistema lerá esse arquivo e aplicará essa regra forçada para Manutenção, Combustível e Frota.

### Passo 3: Executar o Fechamento Completo

Abra o terminal na pasta do projeto e rode o orquestrador:

```bash
python fechar_mes.py
```

Pronto! O script executará as etapas automaticamente:

1. Conecta no Bluefleet e baixa `Manutencao MMAA.xlsx` e `Frota MMAA.xlsx`.
2. Processa os dados e separa o Combustível por filial.
3. Processa e separa a Manutenção por filial.
4. Gera o inventário de Frota por filial.
5. Cruza as informações e gera a **Planilha Consolidada de KPIs**.

---

## 📁 Pastas de Saída

Todos os relatórios gerados serão organizados e salvos dentro da pasta `Dados Tratados/[Mês Ano]`.

Exemplo:

```text
codigo-FKM/
├── Dados Tratados/
│   └── Abril 2026/
│       ├── GRITSCH - PET/
│       │   ├── Combustivel - GRITSCH PET.xlsx
│       │   ├── Frota - GRITSCH PET.xlsx
│       │   └── Manutencao - GRITSCH PET.xlsx
│       ├── GRITSCH - CWB (BASE)/
│       │   └── ...
│       ├── 0426 COMBUSTIVEL GRITSCH TRANSPORTES GERAL.xlsx
│       ├── 0426 FROTA GRITSCH TRANSPORTES GERAL.xlsx
│       ├── 0426 MANUTENÇÃO GRITSCH TRANSPORTES GERAL.xlsx
│       └── Relatorio KPIs Abril 2026 - Combustivel e Manutencao.xlsx
```

---

## ⚙️ Funcionalidades Internas

- **Lógica Temporal de Manutenção:** O sistema analisa a data de cada abastecimento e localiza qual era a filial de manutenção do veículo **naquele dia exato**.
- **Filiais Unificadas:** Regras inteligentes que consolidam `CWB (ECT)` → `CWB (BASE)` e `RATEIO GRI` → `GRITSCH - MATRIZ`.
- **Query Otimizada:** A conexão direta com o SQL Server utiliza tabelas temporárias e filtros no banco para garantir que grandes volumes de dados (18.000+ manutenções/mês) sejam baixados rapidamente.

## 🛠️ Requisitos e Configurações de Ambiente

1. **Python 3.x**
2. O arquivo `.env` deve existir na raiz com as credenciais do banco `Bluefleet`:

```env
DB_HOST=seu_host
DB_NAME=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

3. **Instalação das dependências**:

```bash
pip install -r requirements.txt
```

Para forçar um mês diferente do padrão (que é sempre o mês anterior ao atual), edite o arquivo `src/config.py` descomentando as variáveis `MES` e `ANO`.
