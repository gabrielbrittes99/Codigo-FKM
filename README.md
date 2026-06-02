# Sistema de Fechamento de FKM e KPIs - GRITSCH

Sistema totalmente automatizado para extração, processamento e fechamento mensal das informações de Frota, Manutenção e Combustível.

---

## 🛠️ Configuração e Ativação do Ambiente Virtual (.venv)

O projeto utiliza um ambiente virtual Python para isolar as dependências. Para ativar e utilizar o projeto, siga os passos abaixo no terminal:

### No Linux / macOS (Seu Sistema):

1. **Ative o ambiente virtual:**

    ```bash
    source .venv/bin/activate.fish
    ```

    _Você saberá que está ativado quando ver o prefixo `(.venv)` no início da linha do terminal._

2. **Se o ambiente virtual (.venv) não existir ou precisar ser recriado:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

### No Windows:

1. **Ative o ambiente virtual:**
    ```cmd
    .venv\Scripts\activate
    ```

---

## 🚀 Como Executar o Fechamento

### Passo 1: Executar o Processo Completo

Com o `.venv` ativado, execute o script orquestrador na raiz do projeto para rodar todas as 5 etapas sequencialmente (extração, separação de combustíveis, manutenção, frota e KPIs):

```bash
python fechar_mes.py
```

### Passo 2: Ajustar Placas nas Filiais (Opcional)

Se precisar ajustar ou forçar alguma placa para uma filial específica (ex: veículos novos sem placa definitiva ou filiais sem inscrição estadual):

- **Método Recomendado (Sem alterar código):**
  Edite ou crie o arquivo **`ajustes_placas.csv`** na raiz do projeto:
    ```csv
    Placa,Filial
    ABC1234,GRITSCH - PET
    XYZ9876,GRITSCH - CWB (BASE)
    ```
- **Método Direto no Código:**
  Edite o dicionário `EXCECOES_FORCADAS` no arquivo [src/filial_mapping.py](file:///home/gabriel/Projetos/codigo-FKM/src/filial_mapping.py).

### Passo 3: Re-executar Lotes Específicos

Se você fez algum ajuste em `ajustes_placas.csv` ou no código, **não precisa rodar a extração do banco novamente**. Você pode rodar apenas as etapas de reprocessamento e geração dos arquivos:

- **Gerar relatórios de Combustível:**
    ```bash
    python -m src.executar_resumos
    ```
- **Gerar relatórios de Manutenção:**
    ```bash
    python -m src.executar_manutencao
    ```
- **Gerar relatórios de Frota:**
    ```bash
    python -m src.executar_frota
    ```
- **Gerar Relatório Geral de KPIs:**
    ```bash
    python -m src.gerar_relatorio_kpis
    ```

### Passo 4: Validar e Auditar Dados

Para verificar se há alguma anomalia crítica (hodômetros invertidos, litragens absurdas ou transações duplicadas) antes do envio:

```bash
python -m tools.validar_fechamento
```

### Passo 5: Disparo de E-mails para as Filiais

Quando tudo estiver conferido e correto, dispare os relatórios anexados automaticamente para as caixas de e-mail de cada filial:

```bash
python -m src.enviar_emails
```

---

## 📁 Pastas de Saída

Todos os relatórios gerados serão organizados e salvos dentro da pasta `Dados Tratados/[Mês Ano]`.

```text
codigo-FKM/
├── Dados Tratados/
│   └── Maio 2026/
│       ├── GRITSCH - PET/
│       │   ├── Combustivel - GRITSCH  PET.xlsx
│       │   ├── Frota - GRITSCH  PET.xlsx
│       │   └── Manutencao - GRITSCH  PET.xlsx
│       ├── GRITSCH - CWB (BASE)/
│       │   └── ...
│       ├── 0526 COMBUSTIVEL GRITSCH TRANSPORTES GERAL.xlsx
│       ├── 0526 FROTA GRITSCH TRANSPORTES GERAL.xlsx
│       ├── 0526 MANUTENÇÃO GRITSCH TRANSPORTES GERAL.xlsx
│       └── Relatorio KPIs Maio 2026 - Combustivel e Manutencao.xlsx
```

---

## ⚙️ Configurações Importantes (.env)

O arquivo `.env` na raiz do projeto deve conter os dados de conexões e credenciais de e-mail:

```env
# Banco Bluefleet (SQL Server)
DB_HOST=bi.bluefleet.com.br
DB_NAME=referencia
DB_USER=referencia
DB_PASSWORD=sua_senha

# PostgreSQL (DW Combustível)
DW_HOST=192.168.0.37
DW_PORT=5433
DW_NAME=dw
DW_USER=seu_usuario
DW_PASSWORD=sua_senha
DW_SCHEMA=torre

# Configurações de E-mail (SMTP)
SMTP_HOST=smtp.gritsch.com.br
SMTP_PORT=587
SMTP_USER=naoresponda@gritsch.com.br
SMTP_PASSWORD=sua_senha
```
