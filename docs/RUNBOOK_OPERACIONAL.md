# Runbook Operacional — Fechamento Mensal

> Passo a passo real de como rodar o fechamento todo mês, incluindo as pegadinhas que não são óbvias olhando só o código. Para entender *por que* cada peça existe, veja [ARQUITETURA.md](ARQUITETURA.md). Para a lista de contas/acessos necessários, veja [ACESSOS_CREDENCIAIS.md](ACESSOS_CREDENCIAIS.md).

## 0. Pré-requisitos (uma vez só, por máquina)

1. Ambiente virtual + dependências — ver [README.md](../README.md#%EF%B8%8F-configuração-inicial-do-ambiente).
2. Arquivo `.env` na raiz com as credenciais do SQL Server (Bluefleet), do PostgreSQL (DW Torre) e do SMTP — ver [ACESSOS_CREDENCIAIS.md](ACESSOS_CREDENCIAIS.md) para a lista completa de variáveis.
3. Driver ODBC do SQL Server instalado (`sudo apt-get install -y msodbcsql18` no Linux/WSL).

## 1. Antes de rodar: checklist de início de mês

- [ ] **Atualizar `MES`/`ANO`** — na prática o `src/config.py` calcula automaticamente o mês calendário anterior (`obter_mes_ano_fechamento()`), então normalmente **não precisa editar nada** se você rodar no início do mês certo. Só edite manualmente se for reprocessar um mês específico fora da sequência normal.
- [ ] **Revisar `EXCECOES_FORCADAS` em `src/filial_mapping.py`.** O comentário no topo do dicionário diz explicitamente *"ZERAR ESTE DICIONÁRIO A CADA NOVO FECHAMENTO MENSAL"* — na prática isso **não vem sendo feito**: hoje o dicionário acumula entradas de meses diferentes misturadas (Julho e Agosto/2026 juntas). Antes de fechar um mês novo, confira se cada entrada ainda faz sentido para o mês atual; uma exceção esquecida de dois meses atrás pode redirecionar uma placa para a filial errada silenciosamente. Não há teste automatizado que pegue isso.
- [ ] **Conferir se o arquivo de frota (`Frota*.xlsx`) está em `dados/entrada/`.** Sem ele, o pipeline roda mas com "SEM GRUPO"/"SEM MODELO" em vez de dados reais de frota.

## 2. Extração e geração dos relatórios por filial

```bash
python fechar_mes.py
```

Executa em sequência (para no primeiro erro):
1. Extração do SQL Server (Bluefleet) e do PostgreSQL DW → grava `Manutencao MMAA.xlsx`/`Frota MMAA.xlsx`/`Combustivel MMAA.xlsx` em `dados/entrada/`.
2. Resumos de combustível por filial.
3. Resumos de manutenção por filial.
4. Resumos de frota por filial.
5. Injeção de compra direta (combustível/Arla comprado fora da rede credenciada TruckPag): consulta o financeiro (`dbo.LancamentosComNaturezas`) e, para toda filial que teve compra direta no mês, adiciona ao "Combustivel - FILIAL.xlsx" oficial as abas "Compra Direta (Fora TruckPag)" e "Resumo Geral" (TruckPag + Direta = Total Real) — sem isso, o FKM da filial não tem como saber que precisa declarar aquele valor. Roda automaticamente, para toda filial, todo mês — não precisa checar se "houve compra fora" antes de rodar. (Até 2026-08-28 era um passo manual e opcional em `tools/`, o que fazia a auditoria do passo 3 aprovar FKMs sem cobrar a compra direta quando alguém esquecia de rodar — ver [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md).)
6. Relatório consolidado de KPIs (Excel de 10 abas).

Resultado: `Dados Tratados/[Mês Ano]/[Filial]/*.xlsx` para cada filial, mais o KPI consolidado na raiz da pasta do mês.

> O envio de e-mail **não roda automaticamente** dentro de `fechar_mes.py` (está comentado no orquestrador) — é sempre um passo manual, depois da validação (passo 3 abaixo).

## 3. Aguardar e validar o retorno dos FKMs das filiais

Depois que os gestores de filial preenchem e devolvem a planilha FKM, salve os arquivos em `dados/retornados/` e rode:

```bash
python -m tools.validar_retorno_fkms
```

Veja a seção "Auditoria e Validação" do [README.md](../README.md#%EF%B8%8F-auditoria-e-validação-de-fkms-retornados) para o que é checado. (A ferramenta `tools/diagnostico_placa.py`, que dava explicações desatualizadas sobre alocação de placa, foi removida em 2026-08-27 — ver [DEBITO_TECNICO_E_RISCOS.md](DEBITO_TECNICO_E_RISCOS.md).)

## 4. Enviar e-mails às filiais

```bash
python -m src.enviar_emails
```

> ⚠️ **Os destinatários vêm da tabela `torre.email_gritsch_filiais` no PostgreSQL (DW), não de `dados/emails_filiais.csv`.** Se precisar adicionar, trocar ou desativar um destinatário, faça isso **direto no banco** (`UPDATE`/`INSERT ... WHERE ativo = TRUE`). Atualizar só o CSV não muda nada no envio real — mas vale manter o CSV em sincronia mesmo assim, como referência legível para humanos.

## 5. Gerar os PDFs executivos da Torre de Controle

```bash
# Mensal — mês fechado vs mês anterior + acumulado do ano
python -m src.gerar_pdf_mensal --mes 7 --ano 2026

# Semestral — B1 vs B2 vs B3 (rodar ao fim de cada bimestre/semestre, não todo mês)
python -m src.gerar_pdf_torre
```

Antes de gerar, escreva os textos e observações do mês em [`conteudo_mensal.yaml`](../conteudo_mensal.yaml) (e [`conteudo_torre.yaml`](../conteudo_torre.yaml) no caso semestral) — os números vêm dos bancos automaticamente, os textos são manuais. Detalhes de cada página e dos placeholders disponíveis estão comentados no topo de cada arquivo YAML. Use sempre os helpers de `src/torre_layout.py` (`moeda()`, `valor_km()`, etc.) se for mexer no código de geração — nunca formate `R$` direto inline.

A primeira execução do mês salva cache dos bancos em `dados/cache/`; execuções seguintes rodam em segundos. Use `--sem-cache` para forçar releitura do banco se os números parecerem desatualizados.

## 6. Arquivar o mês fechado

```bash
python -m tools.arquivar_mes
```

Move os arquivos de `dados/entrada/` e `dados/retornados/` para `dados/historico/{Mês Ano}/`.

## Checklist de fim de mês

- [ ] `Dados Tratados/[Mês Ano]/` conferido e com todas as filiais presentes
- [ ] FKMs retornados validados (`validar_retorno_fkms.py` sem rejeições pendentes, incluindo compra direta)
- [ ] E-mails enviados (destinatários corretos confirmados na tabela do banco, não só no CSV)
- [ ] PDF mensal gerado e revisado (textos do YAML preenchidos, não deixados em branco/genéricos)
- [ ] Mês arquivado em `dados/historico/`
- [ ] `EXCECOES_FORCADAS` revisada antes do **próximo** fechamento

## Troubleshooting

Ver a seção "Troubleshooting e Solução de Problemas" no [README.md](../README.md#-troubleshooting-e-solução-de-problemas) para os dois erros mais comuns (`ModuleNotFoundError: No module named 'src'` e driver ODBC faltando).

Se um número da Torre parecer errado ou desatualizado, o primeiro suspeito é o cache: rode de novo com `--sem-cache`.
