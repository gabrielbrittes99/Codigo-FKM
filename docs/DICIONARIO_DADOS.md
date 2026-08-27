# Dicionário de Dados

> Referência rápida dos arquivos, tabelas e campos que o sistema consome e produz. Para o fluxo completo entre eles, veja [ARQUITETURA.md](ARQUITETURA.md).

## Arquivos de entrada (`dados/entrada/`)

Gerados por `src/extrair_dados_bluefleet.py`, nomeados `Combustivel MMAA.xlsx` / `Manutencao MMAA.xlsx` / `Frota MMAA.xlsx` (`MMAA` = mês+ano com 2 dígitos cada, ex. `0726` = Julho/2026). Achados pelo `glob` em `src/config.py` conforme os padrões de `config.yaml`.

| Arquivo | Colunas-chave | Observação |
|---|---|---|
| `Combustivel MMAA.xlsx` | Placa, Garagem, tipo de combustível (Diesel S10, Diesel S10 Aditivado, Diesel Aditivado, Gasolina Comum/Aditivada, Álcool Comum/Aditivado, Arla 32), Litragem, Valor, Estabelecimento, Estado, Cidade, hodômetro | Vem de `torre.vw_RelatorioFKM_Combustivel` (Postgres) |
| `Manutencao MMAA.xlsx` | Placa, FILIAL, ValorTotal, Natureza_Correta (3 categorias), GrupoDespesa (21 categorias), Tipo (7 categorias: corretiva, preventiva, sinistro, etc.) | Vem de `torre_vw_FechamentoManutencao` (SQL Server) |
| `Frota MMAA.xlsx` | Placa, Grupo (Leve/Médio/Pesado/...), Modelo Original, Modelo Padrão, Modelo Simplificado | Vem de `dbo.Veiculos` (SQL Server) |

## Arquivos de mapeamento/referência

| Arquivo | Usado por | Papel |
|---|---|---|
| `dados/mapa_frota.csv` | `tools/gerar_fkm_digital.py` | Lookup de Grupo/Modelo Padrão a partir do Modelo_Original de cada veículo |
| `dados/mapa_modelo.csv` | `tools/gerar_fkm_digital.py` | Mesma finalidade, tabela auxiliar |
| `dados/emails_filiais.csv` | **Nenhum script** — apenas referência manual | ⚠️ Não alimenta o envio real de e-mail. Ver [DEBITO_TECNICO_E_RISCOS.md #6](DEBITO_TECNICO_E_RISCOS.md#6-dadosemails_filiaiscsv-não-tem-nenhum-efeito-no-envio-real-de-e-mail) |
| `ajustes_placas.csv` (raiz, opcional) | `src/filial_mapping.py` | Mecanismo de exceção carregado dinamicamente se o arquivo existir — hoje não existe no repositório |

## Saídas do pipeline

- **`Dados Tratados/[Mês Ano]/[Filial]/`** — por filial: `Frota - FILIAL.xlsx`, `Combustível - FILIAL.xlsx` (abas Dados Brutos/Combustível/Arla/Resumo por Posto), `Manutenção - FILIAL.xlsx`.
- **`Dados Tratados/[Mês Ano]/`** (raiz da pasta do mês) — relatório consolidado de KPIs (10 abas, ver [ARQUITETURA.md](ARQUITETURA.md)).
- **`dados/retornados/`** — FKMs preenchidos e devolvidos pelos gestores de filial (entrada da auditoria).
- **`dados/historico/`** — arquivamento de meses fechados (`tools/arquivar_mes.py`).
- **`dados/cache/*.pkl`** — cache local das extrações brutas do banco, usado pela Torre de Controle para acelerar a geração de PDF.
- **PDFs executivos** (`Torre_Controle_Mensal_*.pdf`, `Torre_Controle_*_S*.pdf`) — não versionados no git (são saída, não código-fonte).

## Tabelas/views externas

### SQL Server "Bluefleet" (banco `referencia`)

| Tabela/View | Papel |
|---|---|
| `dbo.Veiculos` | Cadastro de frota |
| `dbo.Movimentos` | Histórico de transferência de veículo entre filiais (filtrado por `Unidade_movimentada = 'OPERAÇÃO'`) — mecanismo prioritário de resolução de filial |
| `torre_vw_FechamentoManutencao` | View com manutenção já fechada por natureza/filial. Definição "fonte" (pode estar desatualizada) em [`sql/Criacao - Relatorio Fechamento.sql`](../sql/Criacao%20-%20Relatorio%20Fechamento.sql) |
| `dbo.LancamentosComNaturezas` | Lançamentos financeiros com natureza — usada para extrair "compra direta" de combustível fora da TruckPag |

### PostgreSQL "DW Torre" (schema `torre`)

| Tabela/View | Papel |
|---|---|
| `torre.vw_RelatorioFKM_Combustivel` | Fonte do `Combustivel MMAA.xlsx` de entrada do pipeline por filial |
| `torre.gold_truckpag_combustivel` | Combustível granular, só para a Torre executiva (PDFs) |
| `torre.gold_truckpag_pedagio` | Pedágio granular, só para a Torre executiva |
| `torre.email_gritsch_filiais` | **Fonte real** de destinatários de e-mail (`filial_operacional`, `email_destino`, `email_cc`, `ativo`, `id`) |

## Glossário rápido

- **FKM** — planilha de fechamento mensal por filial (Frota, Combustível, Manutenção) que o gestor de filial preenche e devolve para auditoria.
- **Filial / Garagem** — unidade operacional da Gritsch (ex. `GRITSCH - CTB` = Curitiba). "Garagem" é o campo cru do Bluefleet antes da normalização; "Filial_Final"/"FILIAL" é o resultado já resolvido por `filial_mapping.py`.
- **Torre de Controle** — a camada de relatórios executivos em PDF (mensal e semestral), separada do fechamento operacional por filial.
- **B1/B2/B3** — bimestres do ano civil (Jan-Fev / Mar-Abr / Mai-Jun, etc.) usados na comparação semestral da Torre.
- **TruckPag** — rede de postos credenciados para abastecimento; "compra direta" ou "fora da TruckPag" é o abastecimento feito fora dessa rede, lançado por nota fiscal separada.
- **Arla 32** — aditivo (não é combustível), sempre tratado separado do cálculo de km/consumo mas somado ao custo total.
