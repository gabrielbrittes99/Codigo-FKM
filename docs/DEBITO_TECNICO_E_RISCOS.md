# Débito Técnico e Riscos Conhecidos

> Resultado de uma revisão completa do código feita em 2026-08-27, na saída do mantenedor original, para deixar registrado o que um novo responsável precisa saber antes de mexer no sistema. Itens organizados por impacto. Onde há número de linha, trate como aproximado — confirme pelo nome da função/constante, que é o que não muda.

---

## 🔴 Alto risco — pode gerar dado errado sem nenhum aviso

### 1. Docstring contradiz o código em `src/executar_manutencao.py`

`aplicar_excecoes_placa()` (linha ~70) tem a docstring *"DESABILITADO: Não usar exceções forçadas"*, mas o corpo da função **aplica ativamente** `EXCECOES_FORCADAS` + `EXCECOES_MANUTENCAO`, e a função **é chamada de fato** na geração real (linha ~322). Confirmado lendo o código: o comentário está errado, não o comportamento. Risco: um mantenedor novo lê o comentário, assume que a exceção não está em vigor, e toma uma decisão errada achando que o número de manutenção de uma placa não foi redirecionado quando na verdade foi.

**Ação recomendada**: corrigir a docstring para refletir a realidade (ou decidir se o comportamento *deveria* mesmo estar desabilitado, e nesse caso desabilitar de verdade).

### 2. Quatro mecanismos independentes e não sincronizados para forçar a filial de uma placa

Não existe um único lugar que decide "essa placa pertence a essa filial, sempre". Existem quatro, cada um editado separadamente:

1. `EXCECOES_FORCADAS` (dict Python) em `src/filial_mapping.py`
2. Lista de placas PET embutida direto numa query SQL em `src/extrair_dados_bluefleet.py` (linhas ~132, ~140)
3. Três listas de placas (PET, CXJ, PMW) embutidas em `CASE WHEN` dentro de `sql/Criacao - Relatorio Fechamento.sql` (linhas ~242-255) — **as placas CXJ e PMW aí não têm equivalente em nenhum arquivo `.py`**, ou seja, só existem "documentadas" nesse `.sql`, que por sua vez pode nem ser a fonte real da view em produção (ver item 6)
4. Overrides por usuário-criador do lançamento, também só no `.sql` (`#UsuariosFiliais`, 44 usuários mapeados para filiais "REFERÊNCIA X")

**Risco concreto**: atualizar uma exceção de placa em `filial_mapping.py` não garante nada sobre os outros três lugares. Uma placa pode estar "corrigida" no Python e continuar errada no relatório que depende da view SQL.

**Ação recomendada**: pelo menos documentar explicitamente os 4 lugares sempre que uma exceção for criada/removida; idealmente, consolidar em uma fonte única (ex.: uma tabela no banco que todos os mecanismos leem).

### 3. Duas cópias divergentes do mapa nome-de-pasta-da-filial

`tools/validar_retorno_fkms.py` tem `MAPA_FILIAIS_NOME_PASTA` com 35 entradas (a versão "canônica", mais recente — inclui Diretoria, Pelotas com nome alternativo, e Santa Maria/RIA). `tools/gerar_relatorio_validacao.py` mantém sua **própria cópia separada** com 32 entradas, **desatualizada** (sem Santa Maria/RIA, por exemplo — foi criada antes dessa filial existir). Se alguém usar `gerar_relatorio_validacao.py` para validar o FKM de uma filial que só existe no mapa mais novo, o mapeamento de pasta vai falhar silenciosamente ou cair num "não encontrado".

**Ação recomendada**: extrair `MAPA_FILIAIS_NOME_PASTA` para um módulo compartilhado (ex.: dentro de `filial_mapping.py` ou um novo `filiais_constantes.py`) e importar dos dois lugares.

### 4. `tools/diagnostico_placa.py` está desatualizado e pode enganar

Reimplementa manualmente a lógica antiga de alocação (moda de `FILIAL` + comparação temporal manutenção×combustível), que **não é mais** a lógica real do sistema. Hoje `aplicar_filial_manutencao()` em `filial_mapping.py` prioriza a consulta à tabela `dbo.Movimentos` do Bluefleet — e esta ferramenta nem consulta essa tabela. Rodar este diagnóstico hoje pode dar uma explicação **incorreta** de por que uma placa foi parar em determinada filial.

**Ação recomendada**: reescrever para chamar a função real (`aplicar_filial_manutencao`) em vez de reimplementar a lógica à parte, ou aposentar a ferramenta com um aviso claro no topo do arquivo.

### 5. `EXCECOES_FORCADAS` não está sendo zerada mensalmente, como o próprio comentário no código manda

O comentário em `src/filial_mapping.py` (linhas ~16-17 e ~59) é explícito: *"ATENÇÃO: ZERAR ESTE DICIONÁRIO A CADA NOVO FECHAMENTO MENSAL PARA EVITAR QUE REGRAS ANTIGAS AFETEM OS DADOS DO MÊS ATUAL!"*. Na revisão de 2026-08-27, o dicionário tinha entradas de Julho **e** Agosto/2026 misturadas — ou seja, essa limpeza não vem acontecendo. Ver checklist no [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md#1-antes-de-rodar-checklist-de-início-de-mês).

### 6. `dados/emails_filiais.csv` não tem nenhum efeito no envio real de e-mail

Confirmado por busca em todo o repositório: nenhum arquivo `.py` lê `emails_filiais.csv`. `src/enviar_emails.py` consulta diretamente `torre.email_gritsch_filiais` no PostgreSQL. Isso já foi corrigido no [README.md](../README.md) e no [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md), mas fica registrado aqui como risco: enquanto o CSV continuar existindo e sendo editado manualmente (como aconteceu nesta mesma revisão — havia um commit pendente atualizando contatos nele), alguém pode continuar assumindo por engano que é a fonte de verdade.

---

## 🟡 Médio — dívida técnica que não é bug ativo, mas custa tempo/confiança

### 7. Camada "arquitetura limpa" parcialmente desconectada

`src/extractors/excel_extractor.py` e `src/transformers/fuel_transformer.py` (+ `schemas.py`, com validação Pandera) são testados (`tests/test_transformers.py`) mas **não são chamados por nenhum script de produção**. Só `src/loaders/excel_loader.py` está de fato em uso (via `executar_resumos.py`). Um mantenedor novo pode assumir que essa é a forma "oficial" e mais robusta de tratar combustível — não é, ainda; o pipeline real usa outro caminho.

### 8. `PLACA_EXCECAO = "TBU9D20"` é código morto

Definida em `src/filial_mapping.py` (linha ~448), não é referenciada em nenhum outro lugar da função. O tratamento genérico de filiais `REFERÊNCIA` hoje se aplica a todas as placas, sem carve-out especial — mas a mesma exceção "TBU9D20 pode ir para REFERÊNCIA CURITIBA" sobrevive, reimplementada de forma **independente**, em `tools/diagnostico_placa.py` (linhas ~101-107) e `tools/diagnostico_conferencia.py` (linhas ~191-202).

### 9. Zero cobertura de teste nos módulos mais críticos

`tests/` só cobre `src/loaders/excel_loader.py` e `src/transformers/fuel_transformer.py` — exatamente a camada menos usada em produção (item 7). **Sem nenhum teste**: `src/filial_mapping.py` (o módulo com mais regras e exceções do sistema todo), `src/frota_mapping.py`, `src/torre_dados.py` (toda a matemática de KPI — dias úteis, custo/km, detecção de sinistro), `src/gerar_relatorio_kpis.py`, os dois geradores de PDF, e todos os 16 arquivos de `tools/`.

### 10. `DW_SCHEMA` no `.env` é uma variável vestigial

O README documenta `DW_SCHEMA=torre` no exemplo de `.env`, mas nenhum código lê essa variável — o schema `"torre"` está hardcoded direto nas strings SQL. Mudar o schema no futuro exigiria find-and-replace em vários arquivos, não uma simples troca de variável.

### 11. Lista de feriados nacionais hardcoded só para 2026

`FERIADOS_NACIONAIS` em `src/torre_dados.py` (linhas ~138-151) tem só as 12 datas de 2026. **O cálculo de dias úteis vai ficar errado a partir de janeiro de 2027** se ninguém atualizar essa lista antes. Vale colocar um lembrete de calendário para isso ou trocar por uma biblioteca de feriados (ex. `holidays`).

### 12. Limiares de auditoria divergentes entre módulos

`tools/validar_fechamento.py` usa seus próprios limiares (litragem > 600L, salto de hodômetro > 4000km) para checagens conceitualmente equivalentes às que `src/torre_dados.py` faz com outros números (`LIMITE_PERCORRIDO=50000`, `LIMITE_DIAS_GAP=45`). Não é necessariamente um bug — pode ser intencional (contextos diferentes) — mas vale confirmar com quem decidiu esses números originalmente, porque hoje não há comentário explicando a diferença.

### 13. Pequenos resquícios de código

- `src/extrair_dados_bluefleet.py:119-121` — `return None` duplicado dentro do `except` de `extrair_manutencao()`. Inofensivo, mas indica edição apressada.
- `tests/test_transformers.py:64-67` — a mesma chave `"Litragem": [-10]` repetida 3x no mesmo dict literal. Só a última atribuição vale; inofensivo, mas confuso de ler.

---

## 🟢 Organização e limpeza (baixo risco, fácil de resolver)

### 14. Scripts de depuração pontual na raiz

`debug_fln.py`, `debug_formato.py`, `debug_formato2.py` foram criados para investigar um incidente específico (retorno do FKM de Florianópolis em Abril/2026) e hardcodam caminhos e índices de aba daquele arquivo exato. Não fazem parte do conjunto de ferramentas mantidas, não importam nada de `src/`, e não têm mais utilidade agora que o incidente foi resolvido. Já estão no `.gitignore` (não serão commitados); seguro apagar fisicamente quando quiser.

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
