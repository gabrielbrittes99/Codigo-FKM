# Arquitetura do Sistema FKM/Torre de Controle

> Leitura de referência para quem vai assumir o sistema. Para o passo a passo de "como rodar o fechamento todo mês", veja [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md). Para os problemas conhecidos e riscos, veja [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md).

## Visão geral do fluxo

```
┌────────────────────────┐        ┌──────────────────────────┐
│  SQL Server "Bluefleet"│        │  PostgreSQL "DW Torre"   │
│  (host bi.bluefleet... )│        │  (192.168.0.37:5433)     │
│  Frota, Manutenção      │        │  Combustível (TruckPag), │
│  dbo.Veiculos           │        │  Pedágio, e-mails        │
│  dbo.Movimentos         │        │  schema "torre"          │
│  torre_vw_Fechamento... │        │  gold_truckpag_*         │
│  dbo.LancamentosCom...  │        │  vw_RelatorioFKM_Comb.   │
└──────────┬──────────────┘        └───────────┬──────────────┘
           │                                    │
           ▼                                    ▼
   src/extrair_dados_bluefleet.py  (grava .xlsx em dados/entrada/)
           │
           ▼
   src/filial_mapping.py + src/frota_mapping.py
   (normaliza placa/filial, aplica todas as exceções — ver Débito Técnico)
           │
   ┌───────┼────────────────┬─────────────────────┐
   ▼       ▼                ▼                      ▼
executar_  executar_        executar_              gerar_relatorio_kpis.py
frota.py   resumos.py       manutencao.py          (Excel consolidado, 10 abas)
   │       (combustível)    (manutenção)                  │
   └───────┴────────────────┴──────────────────────┘      │
           ▼                                               ▼
   Dados Tratados/[Mês Ano]/[Filial]/*.xlsx      Dados Tratados/[Mês Ano]/*.xlsx
           │
           ▼ (gestor de filial preenche e devolve)
   dados/retornados/*.xls  ──► tools/validar_retorno_fkms.py (auditoria)
                            └► tools/gerar_relatorio_validacao.py (versão Excel)

   src/torre_dados.py  (cálculo dos KPIs executivos, cache em dados/cache/*.pkl)
           │
           ├──► src/gerar_pdf_mensal.py   (PDF mensal, conteudo_mensal.yaml)
           └──► src/gerar_pdf_torre.py    (PDF semestral, conteudo_torre.yaml)
                     (layout/formatação compartilhados em src/torre_layout.py)

   src/enviar_emails.py  ──► SMTP (destinatários vêm de torre.email_gritsch_filiais,
                              NÃO de dados/emails_filiais.csv — ver nota abaixo)
```

O diagrama do [README.md](../README.md) raiz mostra a versão resumida deste mesmo fluxo.

---

## Fontes de dados externas

### SQL Server "Bluefleet" (`DB_HOST`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`)

Banco físico chamado `referencia` (`USE referencia;` no `.sql`, `DB_NAME=referencia` no `.env`). Tabelas/views usadas pelo código Python:

- `dbo.Veiculos`, `dbo.Movimentos` (filtrado por `Unidade_movimentada = 'OPERAÇÃO'`) — frota e histórico de transferência entre filiais.
- `[referencia].[dbo].[torre_vw_FechamentoManutencao]` — view que já vem com a manutenção fechada por natureza/filial. **A definição desta view não está neste repositório** — só a "receita" que deveria corresponder a ela está em [`sql/Criacao - Relatorio Fechamento.sql`](../sql/Criacao%20-%20Relatorio%20Fechamento.sql) (ver abaixo). Se a view for alterada direto no banco sem atualizar esse `.sql` (ou vice-versa), nada no código avisa da divergência.
- `dbo.LancamentosComNaturezas` — usada só por `torre_dados.py` para extrair "compra direta" (combustível fora da TruckPag).

Tabelas-base por trás da view (visíveis só no `.sql`, não referenciadas diretamente em nenhum `.py`): `dbo.ItensOrdemServico`, `dbo.NotasFiscais`, `dbo.GruposDespesa`, `dbo.NaturezasFinanceiras`, `dbo.OcorrenciasManutencao`, `dbo.ContratosComerciais`, `dbo.HistoricoSituacaoVeiculos`, `dbo.Usuarios`.

A conexão com esse banco é reimplementada **de forma independente em 3 lugares** (`src/filial_mapping.py`, `src/executar_frota.py`, `tools/gerar_fkm_matriz.py`) — nenhuma reusa uma função comum. Funciona, mas qualquer mudança de driver/porta precisa ser replicada nos três.

### PostgreSQL "DW Torre" (`DW_HOST`/`DW_PORT`/`DW_NAME`/`DW_USER`/`DW_PASSWORD`, schema `torre`)

- `torre.vw_RelatorioFKM_Combustivel` — alimenta o arquivo `Combustivel MMAA.xlsx` que entra no pipeline de fechamento por filial.
- `torre.gold_truckpag_combustivel`, `torre.gold_truckpag_pedagio` — fonte separada e mais granular, usada só pela Torre executiva (`torre_dados.py`), não pelo fechamento por filial.
- `torre.email_gritsch_filiais` (colunas `filial_operacional`, `email_destino`, `email_cc`, `ativo`, `id`) — **fonte real** dos destinatários de e-mail. Ver aviso na seção seguinte.

A função canônica de conexão é `obter_conexao_dw()` em `src/extrair_dados_bluefleet.py` (reusada por `enviar_emails.py` e `torre_dados.py`), mas `tools/diagnostico_cobertura_b1.py` reimplementa a mesma coisa de novo.

> ⚠️ O `.env` de exemplo no README lista `DW_SCHEMA=torre`, mas **nenhum código lê essa variável** — o schema `torre` está escrito direto nas strings SQL em todo lugar. Se um dia isso precisar mudar, é find-and-replace em vários arquivos, não uma variável de ambiente.

### SMTP (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`)

Usado só por `src/enviar_emails.py`.

> ⚠️ **Armadilha operacional confirmada**: `dados/emails_filiais.csv` **não é lido por nenhum código** (confirmado por busca em todo o repositório). O script de envio consulta diretamente a tabela `torre.email_gritsch_filiais` no PostgreSQL. O CSV é mantido manualmente como referência humana, mas editá-lo **não muda para quem o e-mail é enviado**. Para adicionar/trocar destinatário, é preciso `UPDATE`/`INSERT` direto na tabela do banco.

---

## Camadas do código

### Orquestração e configuração

- **`fechar_mes.py`** — orquestrador. Roda em sequência: extração → resumos de combustível → resumos de manutenção → resumos de frota → relatório de KPIs. Cada etapa é um subprocesso `python -m <módulo>`; se uma falhar, o processo para (`sys.exit(1)`). O envio de e-mail está comentado no fluxo automático — é sempre um passo manual à parte.
- **`src/config.py`** — lê `config.yaml`, faz glob em `dados/entrada/` pelos padrões de nome de arquivo, e calcula `MES`/`ANO` automaticamente como o **mês calendário anterior** ao mês corrente (`obter_mes_ano_fechamento()`). Não lê nenhuma variável de ambiente. É o "botão" central: `MES`/`ANO` propagam para todos os scripts via `from src import config`.
- **`config.yaml`** — diretórios de entrada/saída e os 3 padrões de glob (`Combustivel*.xlsx`, `Manutencao*.xlsx`, `Frota*.xlsx`).

### Mapeamento e normalização (o núcleo mais sensível do sistema)

- **`src/filial_mapping.py`** (~585 linhas) — resolve para qual filial cada linha de combustível/manutenção deve ir. Concentra praticamente todas as exceções manuais do sistema (lista completa em [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md)). Prioridade de resolução, da mais alta para a mais baixa:
  1. `EXCECOES_TRANSACOES` (por ID de transação específico — hoje vazio)
  2. `EXCECOES_FORCADAS` (por placa — ~34 entradas hoje, deveria ser zerado a cada fechamento e não está sendo)
  3. Regras temporais hardcoded por placa (ex.: grupo de placas Sinop→Matriz a partir de uma data fixa)
  4. Consulta à tabela `dbo.Movimentos` do Bluefleet (mecanismo "oficial" para o caso comum)
  5. Fallback: garagem original cadastrada no veículo
- **`src/frota_mapping.py`** — carrega e normaliza o Excel de frota (`Frota*.xlsx`), remove `PLACAS_EXCLUIDAS`, enriquece combustível/manutenção com `Grupo` e `Modelo Simplificado`.

### Geração de relatórios por filial

- **`src/extrair_dados_bluefleet.py`** — puxa Manutenção/Frota do SQL Server e Combustível do DW Postgres, salva como `Manutencao MMAA.xlsx`/`Frota MMAA.xlsx`/`Combustivel MMAA.xlsx` em `dados/entrada/`.
- **`src/executar_frota.py`** — gera "Frota - FILIAL.xlsx" por filial, com alocação histórica dentro do mês quando há transferência de veículo.
- **`src/executar_resumos.py`** — gera "Combustível - FILIAL.xlsx" (via `src/loaders/excel_loader.py`, ver abaixo). Tem seu próprio mapa `MAPA_POSTOS_GERAL`/`MAPA_POSTOS_CSC` (posto→filial) e separa filiais `REFERÊNCIA*`/não-operacionais para um relatório à parte.
- **`src/executar_manutencao.py`** — gera "Manutenção - FILIAL.xlsx". **Atenção**: `aplicar_excecoes_placa()` tem docstring dizendo "DESABILITADO: Não usar exceções forçadas", mas a função **aplica ativamente** `EXCECOES_FORCADAS` + `EXCECOES_MANUTENCAO` e é chamada de fato na geração (linha ~322). O comentário está errado, não o código — mas é fácil um novo mantenedor confiar no comentário e se confundir. Ver [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md#risco-alto).
- **`src/injetar_compra_direta.py`** — roda depois de frota/manutenção/combustível (etapa 5 de `fechar_mes.py`), quando a pasta de toda filial já existe. Lê `dbo.LancamentosComNaturezas` (mesma fonte de `torre_dados._extrair_combustivel_fora`) e injeta no "Combustivel - FILIAL.xlsx" oficial as abas "Compra Direta (Fora TruckPag)" e "Resumo Geral" (TruckPag + Direta = Total Real). Até 2026-08-28 vivia em `tools/` como passo manual opcional do runbook (`python -m tools.injetar_compra_direta --mes X --ano Y`); como `validar_retorno_fkms.py` só reconhece compra direta pela aba que este script gera, um mês em que alguém esquecesse de rodar o comando manual aprovava o FKM sem cobrar o valor — por isso virou etapa automática. Ver [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md).
- **`src/gerar_relatorio_kpis.py`** — Excel consolidado de 10 abas (Resumo Geral, Combustível por Tipo/Filial/Região, Manutenção por Natureza/Filial/GrupoDespesa, Custo por Placa, Ranking de Postos, Análise de Frota). Ver status de implementação em [`PLANO_MELHORIA_KPIs.md`](PLANO_MELHORIA_KPIs.md).

### Torre de Controle (relatórios executivos em PDF)

- **`src/torre_dados.py`** (~1200 linhas) — o "cérebro" quantitativo: extrai combustível/pedágio dos `gold_truckpag_*`, manutenção da view Bluefleet e compra direta do `dbo.LancamentosComNaturezas`; calcula dias úteis (com lista de feriados nacionais **hardcoded só para 2026** — precisa atualizar todo ano), detecção de sinistro (via palavra "FRANQUIA"), recorrência de placas no top de manutenção, agregação por modelo. Usa cache local em `dados/cache/*.pkl` (use `--sem-cache` para forçar releitura do banco).
- **`src/torre_layout.py`** — design system compartilhado: cores, formatação monetária padronizada (`moeda()`, `moeda_cheia()`, `valor_km()`, `valor_litro()`, `numero_br()` — todas em português brasileiro, 2 casas decimais), primitivas de desenho ReportLab, motor de gráficos Matplotlib. **Sempre use estes helpers** em vez de formatar `f"R$ {x:.2f}"` direto no código — é assim que o padrão brasileiro fica consistente em todo o PDF.
- **`src/gerar_pdf_mensal.py`** — PDF executivo mensal (mês vs mês anterior + acumulado do ano), textos em `conteudo_mensal.yaml`.
- **`src/gerar_pdf_torre.py`** — PDF executivo semestral (B1 vs B2 vs B3), textos em `conteudo_torre.yaml`.
- Em ambos, uma página inteira do PDF some automaticamente se a seção correspondente no YAML estiver em branco, ou se a lista de dados calculada vier vazia — não sai folha com só o título (mecanismo em `torre_layout.montar_documento`).

### Envio de e-mails

- **`src/enviar_emails.py`** — lê destinatários de `torre.email_gritsch_filiais` (não do CSV — ver aviso acima), anexa todos os `.xlsx` da pasta de cada filial em `Dados Tratados/[Mês Ano]/[Filial]/`.

### Camada de carga do Excel

- **`src/loaders/excel_loader.py`** — `preparar_resumos()`/`salvar_resumos_filial_excel()`, chamadas por `src/executar_resumos.py`, geram o Excel real de combustível por filial (abas Dados Brutos/Combustível/Arla/Resumo por Posto).

> Havia também `src/extractors/` e `src/transformers/` (com validação Pandera), início de uma arquitetura em camadas mais testável, mas nunca conectada ao pipeline real — foram removidos numa limpeza em 2026-08-27 (ver [DEBITO_TECNICO_E_RISCOS.md, item 7](DEBITO_TECNICO_E_RISCOS.md#7--resolvido--camada-arquitetura-limpa-desconectada)).

### Ferramentas em `tools/`

**Uso operacional regular** (documentadas no README raiz):
- `arquivar_mes.py` — arquiva o mês fechado em `dados/historico/`.
- `validar_retorno_fkms.py` — auditor principal dos FKMs devolvidos pelas filiais (o mais robusto e completo).
- `gerar_fkm_matriz.py` — caso especial da GRITSCH-MATRIZ (hub de trânsito).
- `gerar_fkm_digital.py` — gera o `.xls` de FKM pré-preenchido por filial a partir de `modelos FKM/`.

**Diagnóstico e auditoria pontual**:
- `diagnostico_conferencia.py` — 4 checagens de qualidade (garagem×filial divergente, REFERÊNCIA indevida, veículo multi-filial, hodômetro suspeito).
- `validar_fechamento.py` — anomalias de litragem/hodômetro/duplicidade (limiares próprios, diferentes dos de `torre_dados.py` — ver Débito Técnico).
- `gerar_relatorio_informativos.py` — abas "Veículos para Venda" e "Referência".
- `restaurar_backups.py` — restaura `.bak` em `dados/retornados/`.
- `analisar_datas_placa.py`, `consulta_custos_placas.py` — consultas ad hoc reutilizáveis (já usam `config.py` para achar os arquivos do mês, não hardcoded).

> Numa limpeza em 2026-08-27 foram removidos por não fazerem parte do fechamento nem dos PDFs e serem uso único ou desatualizados: `gerar_relatorio_validacao.py` (duplicava `validar_retorno_fkms.py` com um mapa de filiais divergente), `diagnostico_placa.py` (dava explicação desatualizada/incorreta sobre alocação de placa), `consulta_rapida.py`, `diagnostico_cobertura_b1.py` e `gerar_relatorio_extra.py`. Detalhes em [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md).

---

## Testes

- `tests/test_loaders.py` cobre a camada `src/loaders/excel_loader.py` descrita acima, que é código de produção real.
- **Sem nenhum teste automatizado**: `src/filial_mapping.py` (o módulo com mais exceções e mais crítico do sistema), `src/frota_mapping.py`, `src/torre_dados.py` (toda a matemática de KPI), `src/gerar_relatorio_kpis.py`, os dois geradores de PDF, `src/torre_layout.py`, `src/executar_frota.py`/`executar_manutencao.py`/`executar_resumos.py`, `src/enviar_emails.py`, `src/extrair_dados_bluefleet.py`, `src/config.py`, e todos os arquivos de `tools/`.
- Rodar os testes existentes: `pytest` (configurado via `pyproject.toml`, `testpaths = ["tests"]`).
