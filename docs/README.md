# Documentação — Sistema FKM / Torre de Controle GRITSCH

Índice da documentação de handoff, escrita em 2026-08-27 na saída do mantenedor original. Comece pelo [README.md](../README.md) na raiz do projeto (visão geral e como rodar) e use este índice para o resto.

| Documento | Para quê |
|---|---|
| [ARQUITETURA.md](ARQUITETURA.md) | Como o sistema é organizado por dentro: fluxo de dados, todos os módulos de `src/` e `tools/`, tabelas/views externas, o que tem teste e o que não tem |
| [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md) | Passo a passo real de como rodar o fechamento mensal, com os checklists e pegadinhas que não são óbvias só lendo o código |
| [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md) | Lista viva de problemas conhecidos, inconsistências e riscos, por ordem de impacto — leia antes de mexer em `filial_mapping.py` ou em qualquer exceção de placa |
| [DICIONARIO_DADOS.md](DICIONARIO_DADOS.md) | Arquivos, tabelas, colunas e glossário de termos do negócio (FKM, filial, TruckPag, B1/B2/B3, etc.) |
| [ACESSOS_CREDENCIAIS.md](ACESSOS_CREDENCIAIS.md) | Checklist de sistemas, variáveis de ambiente e contatos a transferir para quem assumir |
| [PLANO_MELHORIA_KPIs.md](PLANO_MELHORIA_KPIs.md) | Histórico: plano de expansão do relatório de KPIs (7→10 abas) — já implementado quase por completo, ver status no topo do arquivo |
| [HARDCODED_VALUES.md](HARDCODED_VALUES.md) | Histórico: auditoria pontual de valores hardcoded feita em Abril/2026 — arquivado, desatualizado; a lista viva agora é o Débito Técnico acima |
| [n8n-migracao-plano.md](n8n-migracao-plano.md) | Plano de migrar criação/população das tabelas do DW para n8n — confirmar status atual com o time de dados/BI |
| `relatorio torre controle B2 vs B3.pdf` | Exemplo de saída do relatório semestral da Torre, mantido como referência visual |

## Por onde começar, na prática

1. Leia o [README.md](../README.md) raiz e o [ARQUITETURA.md](ARQUITETURA.md) para entender o todo.
2. Antes do primeiro fechamento que você rodar sozinho, leia o [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md) do início ao fim.
3. Leia o [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md) inteiro pelo menos uma vez — os itens de risco alto podem te economizar horas de investigação de "por que esse número está errado".
4. Resolva o quanto antes o checklist de [ACESSOS_CREDENCIAIS.md](ACESSOS_CREDENCIAIS.md), especialmente a troca de senha do PostgreSQL.
