# Acessos e Credenciais Necessários

> Checklist para transferir o acesso operacional deste sistema para outra pessoa. Nenhuma senha real está neste arquivo — só nomes de sistema e de variável. As senhas reais vivem no `.env` local (não versionado) e devem ser recadastradas para quem assumir.

## Sistemas que exigem acesso

| Sistema | Para quê | Variáveis no `.env` |
|---|---|---|
| **SQL Server "Bluefleet"** (`bi.bluefleet.com.br`, banco `referencia`) | Extração de Frota e Manutenção | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| **PostgreSQL "DW Torre"** (`192.168.0.37:5433`, schema `torre`) | Combustível (TruckPag), pedágio, dados da Torre executiva, destinatários de e-mail | `DW_HOST`, `DW_PORT`, `DW_NAME`, `DW_USER`, `DW_PASSWORD` |
| **SMTP** (`smtp.gritsch.com.br`) | Envio automático de e-mails de fechamento | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |
| **Repositório git** | Código-fonte deste projeto | acesso ao remoto (`origin`, branch `develop`) — confirmar se é GitHub/GitLab interno e quem administra os colaboradores |

Ver o `.env` de exemplo no [README.md](../README.md#%EF%B8%8F-variáveis-de-ambiente-env) para o formato completo.

## ⚠️ Antes de encerrar o acesso do colaborador atual

- [ ] **Trocar a senha do PostgreSQL DW Torre.** Ela esteve exposta em texto puro no histórico do git (`docs/n8n-migracao-plano.md`, corrigido em 2026-08-27) — mesmo removida do arquivo atual, a senha antiga permanece nos commits anteriores e deve ser considerada comprometida.
- [ ] Revogar/trocar as credenciais de `DB_PASSWORD` (Bluefleet) e `SMTP_PASSWORD` associadas ao colaborador que está saindo, se forem pessoais (não uma conta de serviço compartilhada).
- [ ] Confirmar se o usuário do SQL Server e do PostgreSQL usados por este pipeline são contas de serviço (recomendado) ou contas pessoais do colaborador — se pessoais, criar uma conta de serviço antes de desativar a pessoal.
- [ ] Transferir/confirmar o acesso ao repositório git para quem assumir a manutenção.
- [ ] Confirmar quem administra o driver ODBC / a máquina onde o pipeline roda hoje (agendado via cron/Task Scheduler? Rodado manualmente?) — **isto não foi encontrado em nenhum arquivo do repositório**, precisa ser levantado com o time de infraestrutura antes da saída.

## Contatos e responsáveis

> Preencher antes da saída — esta informação não está em nenhum arquivo do código e só o colaborador atual sabe.

| Papel | Nome/contato | Observação |
|---|---|---|
| Quem administra o banco Bluefleet | _preencher_ | |
| Quem administra o PostgreSQL DW Torre | _preencher_ | |
| Quem recebe os PDFs executivos da Torre | _preencher_ | Ver também `dados/emails_filiais.csv` (referência manual) e a tabela `torre.email_gritsch_filiais` (fonte real) |
| Time de dados/BI (dono do plano de migração n8n) | _preencher_ | Ver [status do plano](DEBITO_TECNICO_E_RISCOS.md#18-status-do-docsn8n-migracao-planomd) |
| Onde/como o pipeline é agendado (se for) | _preencher_ | Não documentado em nenhum arquivo encontrado |
