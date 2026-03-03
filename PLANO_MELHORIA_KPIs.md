# Plano de Melhoria do Relatorio de KPIs
## Combustivel e Manutencao - Gritsch Transportes

---

## VISAO GERAL

O relatorio atual gera **7 abas** com informacoes basicas.
O novo relatorio tera **10 abas** com analises profundas, integracao da frota e visao de especialista.

### Arquivos que serao modificados/criados:

| Arquivo | Acao | O que muda |
|---------|------|------------|
| `config.py` | Modificar | Adicionar deteccao automatica do arquivo de frota |
| `frota_mapping.py` | **CRIAR** | Modulo para carregar e normalizar dados da frota |
| `gerar_relatorio_kpis.py` | Modificar | Reescrita principal: de 7 para 10 abas |

### Dados disponiveis para a analise:

| Fonte | Registros | Colunas-chave |
|-------|-----------|---------------|
| Combustivel 0126.xlsx | 5.178 | Placa, Garagem, Combustivel (8 tipos), Litragem, Valor, Preco, Estabelecimento, **Estado** (12), **Cidade** (165) |
| Manutencao 0126.xlsx | 12.360 | Placa, FILIAL, ValorTotal, Natureza_Correta (3), **GrupoDespesa** (21), Tipo (7) |
| Frota Gritsch 012026.xlsx | 824 | Placa, **Grupo** (17), Modelo Original, Modelo Padrao, **Modelo Simplificado** (30) |

---

## FASE 1 - INFRAESTRUTURA

### 1.1 - config.py (pequena alteracao)

**O que muda:** Adicionar uma linha para detectar automaticamente o arquivo de frota, igual ja faz para combustivel e manutencao.

```python
# Linha a adicionar:
ARQUIVO_ENTRADA_FROTA = encontrar_arquivo_entrada("Frota*.xlsx")
```

Tambem adicionar validacao do arquivo na funcao `validar_configuracao()` (aviso se nao encontrar, mas nao bloqueia).

### 1.2 - frota_mapping.py (arquivo novo)

**Objetivo:** Modulo dedicado para carregar e tratar os dados da frota.

**Funcoes:**

1. **`carregar_frota(caminho)`** - Le o Excel da frota e retorna DataFrame limpo:
   - Normaliza placas (remove hifen, uppercase, strip)
   - Normaliza Grupo para uppercase (resolve "LEVE"/"Leve"/"leve" -> "LEVE" e "MEDIO"/"Medio" -> "MEDIO")
   - Mantem colunas: Placa_Clean, Grupo, Modelo Simplificado
   - Remove duplicatas

2. **`enriquecer_com_frota(df, df_frota)`** - Faz left-merge por Placa_Clean:
   - Adiciona colunas Grupo e Modelo Simplificado ao DataFrame
   - Preenche "SEM GRUPO" / "SEM MODELO" quando a placa nao esta na frota
   - Funciona com DataFrame vazio (se arquivo de frota nao existir)

**Segue o mesmo padrao do `filial_mapping.py` existente.**

---

## FASE 2 - CARREGAMENTO E TRATAMENTO DE DADOS

### 2.1 - Carregamento (no gerar_relatorio_kpis.py)

Apos carregar combustivel e manutencao (como ja faz), adicionar carregamento da frota:

```
1. Carregar Combustivel 0126.xlsx (existente)
2. Carregar Manutencao 0126.xlsx (existente)
3. Carregar Frota Gritsch 012026.xlsx (NOVO)
```

### 2.2 - Tratamento

Apos o tratamento existente (limpar numeros, normalizar filiais, mapeamento), adicionar:

```
4. Enriquecer df_comb com dados da frota (Grupo, Modelo Simplificado)
5. Enriquecer df_manut com dados da frota (Grupo, Modelo Simplificado)
```

Isso permite que todas as abas subsequentes usem Grupo e Modelo para agrupamentos.

---

## FASE 3 - ABAS DO RELATORIO

### ABA 1: "Resumo Geral" (MELHORADA)

**Antes:** 13 linhas basicas (total veiculos, gasto total, media)

**Depois:** ~45 linhas organizadas em secoes:

```
=== PERIODO ===
Periodo: Janeiro/2026
Total de Veiculos (Combustivel): 412
Total de Veiculos (Manutencao): 650
Total de Veiculos (Geral): 720

=== FROTA ===
Total de Veiculos na Frota: 824
Veiculos com Custo no Periodo: 720
Veiculos sem Custo no Periodo: 104

=== RESUMO POR GRUPO DE VEICULO ===
LEVE: 150 veiculos | R$ XX.XXX,XX
MEDIO: 200 veiculos | R$ XX.XXX,XX
PESADO: 300 veiculos | R$ XX.XXX,XX
CAMINHAO4.2TON: ... | ...
... (um por grupo)

=== COMBUSTIVEL ===
Gasto Total Combustivel: R$ 1.234.567,89
Total de Litros: 456.789,00
Preco Medio/Litro (Geral): R$ 5,12
---
Diesel S10: R$ XXX | YYY L | R$ Z,ZZ/L
Diesel S10 Aditivado: R$ XXX | YYY L | R$ Z,ZZ/L
Diesel Aditivado: R$ XXX | YYY L | R$ Z,ZZ/L
Gasolina Comum: R$ XXX | YYY L | R$ Z,ZZ/L
Gasolina Aditivada: R$ XXX | YYY L | R$ Z,ZZ/L
Alcool Comum: R$ XXX | YYY L | R$ Z,ZZ/L
Alcool Aditivado: R$ XXX | YYY L | R$ Z,ZZ/L
Arla 32: R$ XXX | YYY L | R$ Z,ZZ/L

=== MANUTENCAO ===
Gasto Total Manutencao: R$ 2.345.678,90
---
Por Natureza:
  03.02 LATARIA E PINTURA: R$ XX | XX%
  03.03 MANUTENCAO DE VEICULOS: R$ XX | XX%
  03.05 RODAS E PNEUS: R$ XX | XX%
---
Por Grupo de Despesa (21 categorias):
  PNEUS: R$ XX | XX%
  FREIOS: R$ XX | XX%
  MOTOR: R$ XX | XX%
  ... (21 categorias)

=== MANUTENCAO POR TIPO ===
Manutencao Corretiva: R$ XX | XX%
Manutencao Preventiva: R$ XX | XX%
Sinistro: R$ XX | XX%
... (7 tipos)

=== CUSTO OPERACIONAL ===
CUSTO OPERACIONAL TOTAL: R$ 3.580.246,79
Media por Veiculo: R$ 4.972,56
```

---

### ABA 2: "Combustivel por Tipo" (MELHORADA)

**Antes:**
| Tipo Combustivel | Litros | Valor Total | Veiculos | Preco Medio/L | % do Total |

**Depois (colunas adicionadas):**
| Tipo Combustivel | Litros | Valor Total | Veiculos | Preco Medio/L | % do Total | **Estados** | **Cidades** |

As novas colunas `Estados` e `Cidades` mostram em quantos estados e cidades cada tipo de combustivel e utilizado.

---

### ABA 3: "Combustivel por Filial" (MELHORADA)

**Antes:**
| Filial | Litros | Valor Total | Veiculos | Media por Veiculo |

**Depois - Tabela Principal:**
| Filial | Veiculos | Litros Total | Valor Total | Media/Veiculo | Diesel S10 (L) | Diesel S10 (R$) | Gasolina (L) | Gasolina (R$) | Arla 32 (L) | Arla 32 (R$) | Outros (L) | Outros (R$) |

**Depois - Sub-tabela (abaixo, separada por linha em branco):**
Mesmos dados agrupados por Filial + Grupo de veiculo:

| Filial | Grupo | Veiculos | Litros | Valor Total | Media por Veiculo |

**Isso permite comparar "laranja com laranja"** - ex: quanto gasta um LEVE em POA vs um LEVE em CTB.

---

### ABA 4: "Manutencao por Natureza" (SEM MUDANCAS)
Mantem como esta.

### ABA 5: "Manutencao por Filial" (SEM MUDANCAS)
Mantem como esta.

---

### ABA 6: "Manut por GrupoDespesa" (NOVA)

Visao detalhada das 21 categorias de despesa de manutencao:

| GrupoDespesa | Valor Total (R$) | Veiculos | Qtd Registros | Media/Registro (R$) | % do Total |
|---|---|---|---|---|---|
| PNEUS | R$ 150.000 | 200 | 450 | R$ 333,33 | 18,5% |
| FREIOS | R$ 80.000 | 180 | 320 | R$ 250,00 | 9,8% |
| MOTOR | R$ 75.000 | 50 | 80 | R$ 937,50 | 9,2% |
| MAO DE OBRA - CORRETIVA | ... | ... | ... | ... | ... |
| MAO DE OBRA - PREVENTIVA | ... | ... | ... | ... | ... |
| SUSPENSAO | ... | ... | ... | ... | ... |
| SISTEMA ELETRICO | ... | ... | ... | ... | ... |
| TRANSMISSAO | ... | ... | ... | ... | ... |
| OLEOS E LUBRIFICANTES | ... | ... | ... | ... | ... |
| ... (21 categorias) | | | | | |
| **TOTAL** | **R$ XXX** | **-** | **XXX** | **-** | **100%** |

---

### ABA 7: "Custo por Placa" (MELHORADA)

**Antes:**
| Placa | Filial | Litros | Combustivel (R$) | Manutencao (R$) | TOTAL (R$) |

**Depois:**
| Placa | Filial | **Grupo** | **Modelo Simplificado** | Litros | Combustivel (R$) | Manutencao (R$) | TOTAL (R$) | **% Comb** | **% Manut** |

Exemplos:
| RDN1A23 | POA | LEVE | FIAT STRADA | 450 | R$ 2.500 | R$ 800 | R$ 3.300 | 75,8% | 24,2% |
| TBG7A13 | CTB | MEDIO | VW SAVEIRO | 380 | R$ 2.100 | R$ 1.500 | R$ 3.600 | 58,3% | 41,7% |

**O Modelo Simplificado vem da frota** (ja normalizado, resolve "fiat strada" vs "fiat strada nova").

---

### ABA 8: "Comb por Regiao" (NOVA)

**Secao A - Resumo por Estado:**

| Estado | Litros | Valor Total (R$) | Veiculos | Preco Medio/L | Postos | Cidades |
|---|---|---|---|---|---|---|
| PARANA | 150.000 | R$ 820.000 | 300 | R$ 5,47 | 45 | 25 |
| SAO PAULO | 80.000 | R$ 450.000 | 150 | R$ 5,63 | 30 | 18 |
| RIO GRANDE DO SUL | ... | ... | ... | ... | ... | ... |
| ... (12 estados) | | | | | | |

**Secao B - Por Estado x Tipo de Combustivel:**

| Estado | Tipo Combustivel | Litros | Valor Total (R$) | Preco Medio/L |
|---|---|---|---|---|
| PARANA | Diesel S10 | 120.000 | R$ 680.000 | R$ 5,67 |
| PARANA | Gasolina Comum | 15.000 | R$ 85.000 | R$ 5,67 |
| PARANA | Arla 32 | 10.000 | R$ 30.000 | R$ 3,00 |
| SAO PAULO | Diesel S10 | 60.000 | R$ 350.000 | R$ 5,83 |
| ... | | | | |

---

### ABA 9: "Ranking Postos" (MELHORADA)

**Secao A - Ranking Geral (melhorado):**

| Rank | Posto | Estado | Litros | Valor Total | Veiculos | Preco Medio/L | Percentil | Flag |
|---|---|---|---|---|---|---|---|---|
| 1 | AUTO POSTO CENTRAL | PARANA | 25.000 | R$ 140.000 | 80 | R$ 5,60 | 55% | |
| 2 | POSTO SAO JOSE | PARANA | 20.000 | R$ 115.000 | 60 | R$ 5,75 | 72% | PRECO ELEVADO |
| ... | | | | | | | | |

**Secao B - Ranking por Estado:**
Mesmo ranking mas agrupado por estado. Permite ver os melhores postos em cada regiao.

**Secao C - Ranking por Tipo de Combustivel:**
Para cada tipo de combustivel, quais postos vendem e a que preco:

| Tipo Combustivel | Posto | Estado | Litros | Valor Total | Preco Medio/L | Rank |
|---|---|---|---|---|---|---|
| Diesel S10 | POSTO ABC | PARANA | 15.000 | R$ 82.500 | R$ 5,50 | 1 |
| Diesel S10 | POSTO XYZ | SAO PAULO | 12.000 | R$ 70.800 | R$ 5,90 | 2 |
| ... | | | | | | |

**Secao D - Tabela de Precos por Posto (pivo):**
Todos os tipos de combustivel lado a lado por posto:

| Posto | Estado | Diesel S10 (R$/L) | Diesel Adit (R$/L) | Gasolina (R$/L) | Arla 32 (R$/L) |
|---|---|---|---|---|---|
| POSTO ABC | PR | R$ 5,50 | R$ 5,80 | R$ 5,45 | R$ 2,90 |
| POSTO XYZ | SP | R$ 5,90 | - | R$ 5,70 | R$ 3,10 |

**Secao E - Insights de Precos:**

```
INSIGHTS DE PRECOS:

DIESEL S10:
  Melhor preco: POSTO ABC (R$ 5,30/L) - 6,3% abaixo da media
  Pior preco: POSTO XYZ (R$ 6,20/L) - 9,6% acima da media
  Media do mercado: R$ 5,66/L

GASOLINA COMUM:
  Melhor preco: POSTO DEF (R$ 5,10/L) - 8,1% abaixo da media
  Pior preco: POSTO GHI (R$ 5,95/L) - 7,2% acima da media
  Media do mercado: R$ 5,55/L

... (para cada tipo de combustivel)

POSTOS COM PRECO ELEVADO (>10% acima da media):
  - POSTO XYZ: Diesel S10 a R$ 6,20/L (+9,6%)
  - POSTO GHI: Gasolina a R$ 5,95/L (+7,2%)
```

---

### ABA 10: "Analise Frota" (NOVA - visao de especialista)

**Secao A - Custo por Grupo de Veiculo:**
Permite comparar "laranja com laranja":

| Grupo | Veiculos Frota | Veiculos c/ Custo | Combustivel (R$) | Manutencao (R$) | Total (R$) | Media/Veiculo | Media Comb/Veic | Media Manut/Veic |
|---|---|---|---|---|---|---|---|---|
| LEVE | 150 | 140 | R$ 200.000 | R$ 80.000 | R$ 280.000 | R$ 2.000 | R$ 1.429 | R$ 571 |
| MEDIO | 200 | 190 | R$ 350.000 | R$ 150.000 | R$ 500.000 | R$ 2.632 | R$ 1.842 | R$ 789 |
| PESADO | 80 | 75 | R$ 180.000 | R$ 120.000 | R$ 300.000 | R$ 4.000 | R$ 2.400 | R$ 1.600 |
| CAMINHAO5TON | ... | ... | ... | ... | ... | ... | ... | ... |
| ... | | | | | | | | |

**Secao B - Top 10 Veiculos Mais Caros:**

| Rank | Placa | Grupo | Modelo | Filial | Combustivel (R$) | Manutencao (R$) | Total (R$) |
|---|---|---|---|---|---|---|---|
| 1 | ABC1D23 | PESADO | CAMINHAO TRUCK | CTB | R$ 8.500 | R$ 12.000 | R$ 20.500 |
| 2 | DEF4G56 | MEDIO | MB SPRINTER | POA | R$ 6.200 | R$ 9.800 | R$ 16.000 |
| ... (top 10) | | | | | | | |

**Secao C - Custo por Modelo Simplificado:**

| Modelo | Grupo | Veiculos | Combustivel (R$) | Manutencao (R$) | Total (R$) | Media/Veiculo |
|---|---|---|---|---|---|---|
| FIAT STRADA | LEVE | 45 | R$ 80.000 | R$ 30.000 | R$ 110.000 | R$ 2.444 |
| VW SAVEIRO | LEVE | 30 | R$ 55.000 | R$ 25.000 | R$ 80.000 | R$ 2.667 |
| MB SPRINTER | MEDIO | 20 | R$ 60.000 | R$ 40.000 | R$ 100.000 | R$ 5.000 |
| ... (30 modelos) | | | | | | |

**Secao D - Veiculos com Custo SEM Registro na Frota:**
Placas com gasto mas que nao constam no arquivo de frota (problema de cadastro):

| Placa | Filial | Combustivel (R$) | Manutencao (R$) |
|---|---|---|---|
| ABC9Z99 | CSC | R$ 1.200 | R$ 500 |
| ... | | | |

---

## FASE 4 - FORMATACAO E SAIDA

- Abas com secao unica: usa `formatar_aba()` existente (sem mudancas)
- Abas com multiplas secoes (Ranking Postos, Comb por Regiao, Analise Frota): nova funcao `formatar_aba_multi_secao()` que formata cada secao com cabecalho proprio
- Cores distintas para cada aba (expandir lista de cores de 7 para 10)
- Separadores visuais entre secoes (linha em branco + cabecalho formatado)

---

## FASE 5 - TESTES E VALIDACAO

1. **Teste completo:** Executar `python gerar_relatorio_kpis.py` e verificar as 10 abas
2. **Validar resumo:** Conferir totais do Resumo Geral vs abas detalhadas
3. **Validar frota:** Conferir se Grupo e Modelo aparecem corretamente em Custo por Placa
4. **Validar regioes:** Confirmar 12 estados no Comb por Regiao
5. **Validar insights:** Verificar se flags de preco elevado/baixo fazem sentido
6. **Teste sem frota:** Renomear arquivo de frota e rodar - deve funcionar com "SEM GRUPO"
7. **Comparar totais:** Gasto total do Resumo = soma das abas detalhadas

---

## RESUMO DAS MELHORIAS

| O que | Antes | Depois |
|-------|-------|--------|
| Abas no relatorio | 7 | 10 |
| Resumo Geral | 13 linhas basicas | ~45 linhas com breakdowns completos |
| Combustivel por Tipo | Tabela simples | + estados e cidades atendidos |
| Combustivel por Filial | Media geral | + breakdown por tipo combustivel + por grupo veiculo |
| Manutencao detalhada | Apenas Natureza (3 cat.) | + GrupoDespesa (21 categorias) |
| Custo por Placa | Placa + Filial | + Grupo + Modelo Simplificado + % |
| Analise Regional | Nao existia | Combustivel por Estado e Cidade |
| Ranking Postos | Ranking simples | Por regiao, por tipo, analise de precos, insights |
| Analise Frota | Nao existia | Comparativo por grupo, top 10, por modelo, gaps |
| Integracao Frota | Nao existia | Grupo e Modelo em todas as analises |
