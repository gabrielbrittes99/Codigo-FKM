# Débito Técnico e Riscos Conhecidos

> Resultado de uma revisão completa do código feita em 2026-08-27, na saída do mantenedor original, para deixar registrado o que um novo responsável precisa saber antes de mexer no sistema. Itens organizados por impacto. Onde há número de linha, trate como aproximado — confirme pelo nome da função/constante, que é o que não muda.
>
> **Atualização (2026-08-27, mesma data): rodada de limpeza.** Vários itens abaixo marcados **✅ RESOLVIDO** foram corrigidos/removidos numa limpeza de código feita logo após esta auditoria. Mantidos aqui (em vez de apagados) como registro do que existia e por quê foi removido.

---

## 🔴 Alto risco — pode gerar dado errado sem nenhum aviso

### 1. ✅ RESOLVIDO — Docstring contradizia o código em `src/executar_manutencao.py`

`aplicar_excecoes_placa()` (linha ~70) tinha a docstring *"DESABILITADO: Não usar exceções forçadas"*, mas o corpo da função **aplicava ativamente** `EXCECOES_FORCADAS` + `EXCECOES_MANUTENCAO`, e a função **era chamada de fato** na geração real (linha ~322). Confirmado lendo o código antes da correção: o comentário estava errado, não o comportamento. Docstring corrigida em 2026-08-27 para descrever o que a função realmente faz.

### 2. Quatro mecanismos independentes e não sincronizados para forçar a filial de uma placa

Não existe um único lugar que decide "essa placa pertence a essa filial, sempre". Existem quatro, cada um editado separadamente:

1. `EXCECOES_FORCADAS` (dict Python) em `src/filial_mapping.py`
2. Lista de placas PET embutida direto numa query SQL em `src/extrair_dados_bluefleet.py` (linhas ~132, ~140)
3. Três listas de placas (PET, CXJ, PMW) embutidas em `CASE WHEN` dentro de `sql/Criacao - Relatorio Fechamento.sql` (linhas ~242-255) — **as placas CXJ e PMW aí não têm equivalente em nenhum arquivo `.py`**, ou seja, só existem "documentadas" nesse `.sql`, que por sua vez pode nem ser a fonte real da view em produção (ver item 6)
4. Overrides por usuário-criador do lançamento, também só no `.sql` (`#UsuariosFiliais`, 44 usuários mapeados para filiais "REFERÊNCIA X")

**Risco concreto**: atualizar uma exceção de placa em `filial_mapping.py` não garante nada sobre os outros três lugares. Uma placa pode estar "corrigida" no Python e continuar errada no relatório que depende da view SQL.

**Ação recomendada**: pelo menos documentar explicitamente os 4 lugares sempre que uma exceção for criada/removida; idealmente, consolidar em uma fonte única (ex.: uma tabela no banco que todos os mecanismos leem).

### 3. ✅ RESOLVIDO — Duas cópias divergentes do mapa nome-de-pasta-da-filial

`tools/validar_retorno_fkms.py` tinha `MAPA_FILIAIS_NOME_PASTA` com 35 entradas (a versão "canônica", mais recente). `tools/gerar_relatorio_validacao.py` mantinha sua **própria cópia separada** com 32 entradas, **desatualizada** (sem Santa Maria/RIA, por exemplo). Resolvido em 2026-08-27 removendo `tools/gerar_relatorio_validacao.py` inteiro (era uma versão Excel duplicada e não usada do auditor de retorno — `validar_retorno_fkms.py`, no terminal, é a versão em uso). Agora só existe uma cópia do mapa.

### 4. ✅ RESOLVIDO — `tools/diagnostico_placa.py` estava desatualizado e podia enganar

Reimplementava manualmente a lógica antiga de alocação (moda de `FILIAL` + comparação temporal manutenção×combustível), que **não era mais** a lógica real do sistema — `aplicar_filial_manutencao()` em `filial_mapping.py` prioriza a consulta à tabela `dbo.Movimentos` do Bluefleet, e esta ferramenta nem consultava essa tabela. Removida em 2026-08-27 (não usada no fechamento nem nos PDFs; risco de dar explicação incorreta era maior que o benefício de manter).

### 5. `EXCECOES_FORCADAS` não está sendo zerada mensalmente, como o próprio comentário no código manda

O comentário em `src/filial_mapping.py` (linhas ~16-17 e ~59) é explícito: *"ATENÇÃO: ZERAR ESTE DICIONÁRIO A CADA NOVO FECHAMENTO MENSAL PARA EVITAR QUE REGRAS ANTIGAS AFETEM OS DADOS DO MÊS ATUAL!"*. Na revisão de 2026-08-27, o dicionário tinha entradas de Julho **e** Agosto/2026 misturadas — ou seja, essa limpeza não vem acontecendo. Ver checklist no [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md#1-antes-de-rodar-checklist-de-início-de-mês).

### 6. `dados/emails_filiais.csv` não tem nenhum efeito no envio real de e-mail

Confirmado por busca em todo o repositório: nenhum arquivo `.py` lê `emails_filiais.csv`. `src/enviar_emails.py` consulta diretamente `torre.email_gritsch_filiais` no PostgreSQL. Isso já foi corrigido no [README.md](../README.md) e no [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md), mas fica registrado aqui como risco: enquanto o CSV continuar existindo e sendo editado manualmente (como aconteceu nesta mesma revisão — havia um commit pendente atualizando contatos nele), alguém pode continuar assumindo por engano que é a fonte de verdade.

### 19. ✅ RESOLVIDO — Compra direta fora da TruckPag podia fechar sem cobrar da filial

Descoberto em 2026-08-28 rodando o fechamento real de Julho/2026 como teste. Duas falhas relacionadas:

1. `tools/validar_retorno_fkms.py` só reconhecia "abastecimento por fora" como legítimo (em vez de erro) para uma lista fixa de 5-6 filiais hardcoded (`FILIAIS_ABAST_POR_FORA`/`FILIAIS_ARLA_POR_FORA`). Mas compra direta é um evento do mês, não uma característica fixa da filial — em Julho/2026, Londrina, Sinop, Cuiabá e Porto Alegre tiveram compra direta real sem estar em nenhuma lista, então um gestor que declarasse o valor corretamente seria rejeitado por engano.
2. Mesmo para as filiais reconhecidas, a validação só comparava por placa contra o valor TruckPag — nunca conferia o total do FKM contra o TOTAL REAL (TruckPag + Direta). Como a compra direta é um valor de filial sem placa associada, uma compra direta parcial ou não declarada passava sem nenhum alerta. Com dados reais de Julho/2026: Itumbiara, Rio Verde, Curitiba, Cuiabá e Sinop fecharam ~R$ 20.193 abaixo do total real sem nenhum erro acusado.
3. A causa raiz de fundo: `tools/injetar_compra_direta.py` (que gera a informação que os dois pontos acima consomem) era um passo **manual e opcional** do runbook ("se aplicável"), rodado separadamente depois de `fechar_mes.py` — fácil de esquecer, e desconectado do fluxo principal.

Corrigido em 3 passos: (1) `validar_retorno_fkms.py` passou a ler a aba real "Compra Direta"/"Resumo Geral" do arquivo oficial em vez de listas fixas. (2) ganhou uma checagem de total por filial (FKM inteiro vs TOTAL REAL). (3) o script que gera essa informação foi movido para `src/injetar_compra_direta.py` e virou etapa automática 5 de `fechar_mes.py` (depois de frota/manutenção, para que a pasta de toda filial já exista).

**Ajuste em seguida (mesmo dia):** a checagem de total (2) e a tabela por placa de (1) se mostraram difíceis de usar na prática — a compra direta é um lançamento financeiro sem placa associada, então bater valor exato linha a linha não dá resultado confiável, e as rejeições geradas não tinham correção óbvia. Substituídas por um relatório puramente informativo ("COMPRA DIRETA DO MÊS"): filial, valor de combustível, valor de Arla e total, sem tentar auditar contra o FKM. A supressão de erro por divergência positiva (pra não rejeitar por engano um gestor que declara a compra direta corretamente) foi mantida. Ver [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md#2-extração-e-geração-dos-relatórios-por-filial) e [ARQUITETURA.md](ARQUITETURA.md).

---

## 🟡 Médio — dívida técnica que não é bug ativo, mas custa tempo/confiança

### 7. ✅ RESOLVIDO — Camada "arquitetura limpa" desconectada

`src/extractors/excel_extractor.py` e `src/transformers/fuel_transformer.py` (+ `schemas.py`, com validação Pandera) eram testados (`tests/test_transformers.py`) mas **não eram chamados por nenhum script de produção** — só `src/loaders/excel_loader.py` estava de fato em uso (via `executar_resumos.py`). Removidos por completo em 2026-08-27 (`src/extractors/`, `src/transformers/` e `tests/test_transformers.py`), já que confundiam mais do que ajudavam sem estar conectados ao pipeline real. `src/loaders/excel_loader.py` continua normalmente, é código de produção.

### 8. ✅ Parcialmente resolvido — `PLACA_EXCECAO = "TBU9D20"` era código morto

Estava definida em `src/filial_mapping.py`, não era referenciada em nenhum outro lugar da função — removida em 2026-08-27. A mesma exceção "TBU9D20 pode ir para REFERÊNCIA CURITIBA", que estava reimplementada de forma independente em dois lugares, agora só sobrevive em um: `tools/diagnostico_conferencia.py` (linhas ~191-202) — a outra cópia, em `tools/diagnostico_placa.py`, foi removida junto com o arquivo (item 4).

### 9. Zero cobertura de teste nos módulos mais críticos

`tests/` hoje só cobre `src/loaders/excel_loader.py` (`tests/test_loaders.py`) — `tests/test_transformers.py` foi removido em 2026-08-27 junto com o código que testava (item 7), que não era usado em produção mesmo. **Sem nenhum teste**: `src/filial_mapping.py` (o módulo com mais regras e exceções do sistema todo), `src/frota_mapping.py`, `src/torre_dados.py` (toda a matemática de KPI — dias úteis, custo/km, detecção de sinistro), `src/gerar_relatorio_kpis.py`, os dois geradores de PDF, e todos os arquivos de `tools/`.

### 10. `DW_SCHEMA` no `.env` é uma variável vestigial

O README documenta `DW_SCHEMA=torre` no exemplo de `.env`, mas nenhum código lê essa variável — o schema `"torre"` está hardcoded direto nas strings SQL. Mudar o schema no futuro exigiria find-and-replace em vários arquivos, não uma simples troca de variável.

### 11. Lista de feriados nacionais hardcoded só para 2026

`FERIADOS_NACIONAIS` em `src/torre_dados.py` (linhas ~138-151) tem só as 12 datas de 2026. **O cálculo de dias úteis vai ficar errado a partir de janeiro de 2027** se ninguém atualizar essa lista antes. Vale colocar um lembrete de calendário para isso ou trocar por uma biblioteca de feriados (ex. `holidays`).

### 12. Limiares de auditoria divergentes entre módulos

`tools/validar_fechamento.py` usa seus próprios limiares (litragem > 600L, salto de hodômetro > 4000km) para checagens conceitualmente equivalentes às que `src/torre_dados.py` faz com outros números (`LIMITE_PERCORRIDO=50000`, `LIMITE_DIAS_GAP=45`). Não é necessariamente um bug — pode ser intencional (contextos diferentes) — mas vale confirmar com quem decidiu esses números originalmente, porque hoje não há comentário explicando a diferença.

### 13. ✅ RESOLVIDO — Pequenos resquícios de código

- `src/extrair_dados_bluefleet.py` — `return None` duplicado dentro do `except` de `extrair_manutencao()`. Corrigido em 2026-08-27.
- `tests/test_transformers.py` — chave repetida num dict literal de teste. Arquivo inteiro removido junto com o código não usado que testava (item 7).

---

## 🟢 Organização e limpeza (baixo risco, fácil de resolver)

### 14. ✅ RESOLVIDO — Scripts de uso único removidos

Removidos em 2026-08-27, todos confirmados sem nenhuma referência cruzada no resto do código antes da remoção:

- `debug_fln.py`, `debug_formato.py`, `debug_formato2.py` (raiz) — investigação pontual do retorno do FKM de Florianópolis em Abril/2026, com caminhos e índice de aba daquele arquivo específico hardcoded.
- `tools/consulta_rapida.py` — caminho absoluto e lista de placas hardcoded, script de investigação descartável.
- `tools/diagnostico_cobertura_b1.py` — auditoria de backfill do 1º semestre/2026, uso único, já concluída.
- `tools/gerar_relatorio_extra.py` — relatório filtrado para 28 placas específicas de um pedido pontual de stakeholder, não genérico.
- `tools/gerar_relatorio_validacao.py` e `tools/diagnostico_placa.py` — ver itens 3 e 4.

Se algum desses fizer falta, o histórico do git preserva o conteúdo (`git log --diff-filter=D -- <caminho>`).

### 15. Pasta solta `dados/0626 - RETORNADAS/`

Fora do padrão usado pelo resto do código (`dados/retornados/`, sem data no nome). Parece resíduo de um fechamento anterior processado fora do fluxo oficial. Já coberta pelo `.gitignore` (padrão `dados/*RETORNADAS*/`); avaliar se pode ser apagada ou movida para `dados/historico/`.

### 16. `docs/HARDCODED_VALUES.md` está desatualizado

Documento de abril/2026 — quase nenhum valor concreto nele ainda bate com o código atual (`EXCECOES_FORCADAS` tinha 20 entradas, hoje tem ~34, quase todas com destino diferente; a exceção `EXCECOES_TRANSACOES` que ele descreve com 25 transações está hoje vazia; os arquivos de teste que ele cita como hardcoded não existem mais). Mantido no repositório com um aviso de arquivamento no topo — útil como *exemplo do tipo de auditoria a repetir*, não como referência viva. Esta lista (`DEBITO_TECNICO_E_RISCOS.md`) é a que deve ser mantida atualizada daqui para frente.

### 17. `docs/PLANO_MELHORIA_KPIs.md` — já implementado quase por completo

O plano de expandir o relatório de KPIs de 7 para 10 abas **foi implementado** (confirmado lendo `src/gerar_relatorio_kpis.py`), com pequenas exceções:
- Aba 1 (Resumo Geral): a linha "Veículos sem Custo no Período" é calculada (`placas_sem_custo`) mas nunca escrita no Excel final.
- Aba 9 (Ranking de Postos): faltam a seção D (tabela pivô Posto × Tipo de Combustível) e a seção E (insights de melhor/pior preço por tipo, lista de postos com preço elevado) — só as seções A, B e C foram implementadas.

Mantido no repositório com aviso de status no topo. Se alguém quiser fechar os 5-10% restantes, essas duas lacunas são o ponto de partida.

### 18. Status do `docs/n8n-migracao-plano.md`

Plano de migrar a criação/população das tabelas do DW de Python para n8n. Não foi possível confirmar, só pela leitura do código, se essa migração está em andamento, pausada ou abandonada — **confirme com o time de dados/BI atual** antes de assumir que ele reflete o estado real do banco. A credencial de banco que estava em texto puro nesse arquivo já foi removida (ver histórico do git, commit de segurança de 2026-08-27) — **a senha exposta deve ser trocada no PostgreSQL se ainda não foi**.
