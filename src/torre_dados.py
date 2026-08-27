"""
Módulo de extração e cálculo de dados para o Relatório Torre de Controle.

Consolida Combustível (DW TruckPag), Manutenção (Bluefleet) e Pedágio (DW
TruckPag) nos indicadores do relatório bimestral: totais mensais, fechamento
por bimestre (B1/B2/B3), variações e as quebras detalhadas usadas nos gráficos
e tabelas do PDF.

O resultado é um dicionário serializável, gravado em cache para permitir
regerar o PDF sem reconsultar os bancos.
"""

import os
import pickle
import unicodedata
import warnings
from datetime import datetime

import pandas as pd

from src.extrair_dados_bluefleet import obter_conexao_dw
from src.executar_frota import obter_conexao_bluefleet

warnings.filterwarnings("ignore", category=UserWarning)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_CACHE = os.path.join(RAIZ, "dados", "cache")

MESES_S1 = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun"}
MESES_S2 = {7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
MESES = {**MESES_S1, **MESES_S2}
MESES_EXTENSO = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# Rótulos de exibição para os grupos de combustível do DW
ROTULO_COMBUSTIVEL = {
    "Diesel": "Diesel S10",
    "Gasolina": "Gasolina Comum",
    "Álcool": "Álcool Comum",
    "Arla": "Arla 32",
}

# Naturezas de manutenção destacadas no relatório, na ordem de exibição.
# Chave = valor normalizado da view; valor = rótulo impresso no PDF.
NATUREZAS = {
    "MANUTENÇÃO DE VEÍCULOS": "Manutenção de Veículos",
    "RODAS E PNEUS": "Rodas e Pneus",
    "LATARIA E PINTURA": "Lataria e Pintura",
}

# =======================================================================
# EQUIVALÊNCIA CENTRO DE CUSTO -> FILIAL
#
# A compra direta de combustível vem do financeiro identificada por centro de
# custo, que traz a cidade no fim do nome ("ADMINISTRATIVO - ITUMBIARA",
# "CARGAS - LONDRINA", "FEBRABAN - RIO VERDE"). A TruckPag usa o código da
# garagem ("ITR", "LDB", "RVD"). O cruzamento é feito pela CIDADE, então
# qualquer prefixo — setor ou nome de cliente — cai na mesma filial e não é
# preciso cadastrar cada combinação.
#
# Para incluir uma filial nova, basta acrescentar a cidade aqui.
# =======================================================================

CIDADE_PARA_FILIAL = {
    # chaves mais específicas primeiro: a busca prioriza a mais longa
    "CURITIBA BASE": "CWB (BASE)",
    "CURITIBA ECT": "CWB (ECT)",
    "CURITIBA DIR": "CWB (DIR)",
    "SAO PAULO PERUS": "SAO (PERUS)",
    "SAO PAULO FREGUESIA": "SAO (FREGUESIA)",
    "CAXIAS DO SUL": "CXJ",
    "CAMPO GRANDE": "CGR",
    "PORTO ALEGRE": "POA",
    "PONTA GROSSA": "PGR",
    "PATO BRANCO": "PBC",
    "RIO VERDE": "RVD",
    "BLUMENAU": "BLN",
    "BRASILIA": "BSB",
    "CASCAVEL": "CSC",
    "CHAPECO": "CHA",
    "CRICIUMA": "CRI",
    "CUIABA": "CGB",
    "CURITIBANOS": "CBL",
    "CURITIBA": "CWB (BASE)",
    "FLORIANOPOLIS": "FLN",
    "GOIANIA": "GOI",
    "GUARAPUAVA": "GPA",
    "ITUMBIARA": "ITR",
    "JOINVILLE": "JOI",
    "LONDRINA": "LDB",
    "MARINGA": "MGA",
    "PALMAS": "PMW",
    "PELOTAS": "PET",
    "RONDONOPOLIS": "RDN",
    "SALVADOR": "SSA",
    "SAO PAULO": "SAO (PERUS)",
    "SINOP": "SNO",
    # Cidades sem filial própria, atendidas pela filial da região
    "URUACU": "GOI",           # Uruaçu (GO) opera pela base de Goiânia
    "VARZEA GRANDE": "CGB",    # região metropolitana de Cuiabá
    "NOVA ALVORADA": "CBL",    # rota atendida por Curitibanos
    "SANTA MARIA": "RIA",      # Santa Maria (RS) — filial nova a partir de Agosto/2026
}

# Centros de custo que não pertencem a uma filial operacional: rateios
# administrativos e a Referência (empresa não operacional). Ficam agrupados
# à parte em vez de serem jogados em alguma filial.
MARCAS_NAO_OPERACIONAIS = ("RATEIO", "REFERENCIA")
ROTULO_NAO_ALOCADO = "RATEIO GRI/REF"
# lançamento que chegou sem centro de custo preenchido no financeiro
ROTULO_SEM_CENTRO = "SEM CENTRO DE CUSTO"
# centro de custo preenchido, mas com cidade que não está em CIDADE_PARA_FILIAL
ROTULO_SEM_EQUIVALENCIA = "CIDADE NÃO CADASTRADA"

# =======================================================================
# UNIDADES FORA DO RELATÓRIO EXECUTIVO
#
# Matriz e diretoria são estrutura administrativa, não operação de frota, e
# distorcem o custo por km do grupo. A Referência é outra empresa. Os três
# saem de TODAS as visões: totais, custo por km, rankings e tabelas.
# =======================================================================
FILIAIS_NAO_OPERACIONAIS = {
    "MATRIZ",
    "CWB (DIR)",
    # Referência Curitiba fica: é um caminhão que presta serviço para a Gritsch
    # e o custo dele interessa no acompanhamento.
}

# =======================================================================
# DIAS ÚTEIS
#
# O mês com mais dias úteis roda mais e gasta mais em valor absoluto. Sem
# essa referência, comparar dois meses em reais leva a conclusão errada.
# Feriados nacionais; se precisar de feriado local, acrescente aqui.
# =======================================================================
FERIADOS_NACIONAIS = [
    "2026-01-01",  # Confraternização Universal
    "2026-02-16", "2026-02-17",  # Carnaval
    "2026-04-03",  # Paixão de Cristo
    "2026-04-21",  # Tiradentes
    "2026-05-01",  # Dia do Trabalho
    "2026-06-04",  # Corpus Christi
    "2026-09-07",  # Independência
    "2026-10-12",  # Nossa Senhora Aparecida
    "2026-11-02",  # Finados
    "2026-11-15",  # Proclamação da República
    "2026-11-20",  # Consciência Negra
    "2026-12-25",  # Natal
]

# Percorrido acima deste valor é ruído de hodômetro (troca de painel, digitação)
LIMITE_PERCORRIDO = 50000

# Intervalo entre abastecimentos consecutivos da mesma placa acima do qual o
# percorrido também é descartado. 99,9% dos intervalos reais ficam abaixo de
# 37 dias (a mediana é 1 dia); um gap maior costuma ser veículo que abasteceu
# por fora ou ficou parado, e o hodômetro seguinte acumula tudo de uma vez.
# Sem esse corte, esse km cai inteiro no mês do abastecimento seguinte e
# distorce o KPI daquele mês (caso real: GOI em jun/2026, RHV-8B69).
LIMITE_DIAS_GAP = 45

# Filial com quilometragem muito baixa gera R$/km instável (divisão por
# quase zero), então fica fora do ranking e da tabela comparativa.
KM_MINIMO_FILIAL = 10000

# Quantas placas entram no gráfico e na tabela de hodômetro x manutenção
TOP_PLACAS_MANUTENCAO = 10

# Texto que identifica um item de manutenção como franquia de seguro
# (sinistro). É o único sinal confiável hoje: quando o reparo é feito fora da
# franquia, ele entra como manutenção corretiva comum, sem indicar a origem.
PALAVRA_CHAVE_SINISTRO = "FRANQUIA"

# Placa entra em "recorrentes" quando aparece no top de manutenção do mês em
# pelo menos esta quantidade de meses do período (não precisam ser seguidos).
RECORRENCIA_MESES_MIN = 2

# Modelo só entra na comparação de custo médio de manutenção com esta
# quantidade mínima de veículos na frota — evita média instável tirada de 1
# ou 2 unidades.
MODELOS_MIN_UNIDADES = 5


# =======================================================================
# HELPERS
# =======================================================================

def _limpar_filial(valor):
    """'GRITSCH - CWB (BASE)' -> 'CWB (BASE)'."""
    texto = str(valor).strip()
    if texto.upper().startswith("GRITSCH"):
        partes = texto.split("-", 1)
        if len(partes) == 2:
            texto = partes[1].strip()
    return texto.upper()


def _limpar_natureza(valor):
    """'03.03 - MANUTENÇÃO DE VEÍCULOS' -> 'MANUTENÇÃO DE VEÍCULOS'."""
    texto = str(valor).strip()
    if " - " in texto:
        texto = texto.split(" - ", 1)[1].strip()
    return texto.upper()


def _concessionaria(operadora):
    """'EPR IGUACU - BR 277 - KM ...' -> 'EPR IGUACU'."""
    return str(operadora).split(" - ")[0].strip().upper()


def _eh_sinistro(descricao_item):
    """True quando o item de manutenção é franquia de seguro (sinistro)."""
    return PALAVRA_CHAVE_SINISTRO in str(descricao_item or "").upper()


def _sem_acento(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    ).upper().strip()


def centro_custo_para_filial(centro):
    """'FEBRABAN - RIO VERDE' -> 'RVD'.

    Devolve o código da filial, ROTULO_NAO_ALOCADO para rateio/Referência, ou
    ROTULO_SEM_EQUIVALENCIA quando a cidade não está no cadastro — nunca
    adivinha, para não somar valor na filial errada.
    """
    texto = _sem_acento(centro)
    if not texto or texto == "NAN" or texto == "NONE":
        return ROTULO_SEM_CENTRO
    if any(marca in texto for marca in MARCAS_NAO_OPERACIONAIS):
        return ROTULO_NAO_ALOCADO

    # centro de custo de rota ("CURITIBANOS X NOVA ALVORADA") fica na origem
    if " X " in texto:
        texto = texto.split(" X ", 1)[0].strip()

    # a chave mais longa primeiro: "CURITIBA BASE" antes de "CURITIBA"
    for cidade in sorted(CIDADE_PARA_FILIAL, key=len, reverse=True):
        if cidade in texto:
            return CIDADE_PARA_FILIAL[cidade]
    return ROTULO_SEM_EQUIVALENCIA


def _feriados_np():
    import numpy as np
    return np.array(FERIADOS_NACIONAIS, dtype="datetime64[D]")


def dias_uteis(mes, ano):
    """Dias úteis do mês: segunda a sexta, descontados os feriados nacionais."""
    import numpy as np

    inicio = np.datetime64(f"{ano}-{mes:02d}-01")
    fim = (np.datetime64(f"{ano + 1}-01-01") if mes == 12
           else np.datetime64(f"{ano}-{mes + 1:02d}-01"))
    return int(np.busday_count(inicio, fim, holidays=_feriados_np()))


def dias_do_mes(mes, ano):
    """Total de dias corridos do mês."""
    import calendar
    return calendar.monthrange(ano, mes)[1]


def _marcar_dia_util(serie_datas):
    """True/False por lançamento: a data caiu em dia útil ou não.

    É o que permite separar gasto de dia útil de gasto de fim de semana e
    feriado. Dividir o total do mês pelo número de dias úteis, como se fazia
    antes, jogava o gasto de sábado e domingo dentro da média do dia útil.
    """
    import numpy as np

    datas = pd.to_datetime(serie_datas).dt.normalize().values.astype("datetime64[D]")
    return pd.Series(np.is_busday(datas, holidays=_feriados_np()),
                     index=serie_datas.index)


def _garantir_dia_util(*dfs):
    """Recalcula o flag de dia útil em cache antigo — deriva só da data."""
    for df in dfs:
        if df is not None and not df.empty and "dia_util" not in df.columns:
            df["dia_util"] = _marcar_dia_util(df["data"])


def _remover_nao_operacionais(df, coluna="filial"):
    """Tira matriz, diretoria e Referência de qualquer recorte do relatório."""
    if df is None or df.empty or coluna not in df.columns:
        return df
    return df[~df[coluna].isin(FILIAIS_NAO_OPERACIONAIS)].copy()


def _limpar_combustivel_fora(df_fora):
    """Deixa no combustível por fora só o que é de filial operacional.

    Rateio administrativo e Referência não são abastecimento de frota; entravam
    no total sem representar consumo atribuível a nenhuma operação.
    """
    if df_fora is None or df_fora.empty:
        return df_fora

    df = df_fora.copy()
    df["filial_equivalente"] = df["filial"].apply(centro_custo_para_filial)
    descartar = {ROTULO_NAO_ALOCADO} | FILIAIS_NAO_OPERACIONAIS
    return df[~df["filial_equivalente"].isin(descartar)].copy()


def _dado_frota(frota, placa, campo):
    """Lê idade/modelo da frota tolerando o formato antigo do cache ({placa: idade})."""
    registro = (frota or {}).get(str(placa).replace("-", "").strip().upper())
    if isinstance(registro, dict):
        return registro.get(campo)
    return registro if campo == "idade" else None


def _variacao(atual, anterior):
    if anterior and anterior > 0:
        return ((atual / anterior) - 1) * 100
    return 0.0 if not atual else 100.0


def _kpis(df_comb, df_manut, df_ped, df_comb_fora=None):
    """Bloco de indicadores para um recorte já filtrado dos dataframes."""
    comb_truckpag = float(df_comb["valor"].sum()) if not df_comb.empty else 0.0
    comb_fora = float(df_comb_fora["valor"].sum()) if (df_comb_fora is not None and not df_comb_fora.empty) else 0.0
    comb = comb_truckpag + comb_fora

    manut = float(df_manut["valor"].sum()) if not df_manut.empty else 0.0
    ped = float(df_ped["valor"].sum()) if not df_ped.empty else 0.0
    total = comb + manut + ped

    # Sinistro: só existe em cache extraído depois que descricao_item passou a
    # ser lida em _extrair_manutencao — cache antigo simplesmente não tem a
    # coluna, e aqui isso vira sinistro = 0 em vez de erro.
    sinistro = 0.0
    if not df_manut.empty and "descricao_item" in df_manut.columns:
        sinistro = float(df_manut.loc[df_manut["descricao_item"].apply(_eh_sinistro), "valor"].sum())

    km = float(df_comb.loc[df_comb["percorrido"] > 0, "percorrido"].sum()) if not df_comb.empty else 0.0
    litros = float(df_comb["litragem"].sum()) if not df_comb.empty else 0.0

    # Preço do Diesel S10: média ponderada pela litragem (não média simples,
    # que distorceria por causa de abastecimentos pequenos)
    s10 = df_comb[df_comb["eh_diesel_s10"]] if not df_comb.empty else df_comb
    litros_s10 = float(s10["litragem"].sum()) if not s10.empty else 0.0
    valor_s10 = float(s10["valor"].sum()) if not s10.empty else 0.0
    preco_s10 = valor_s10 / litros_s10 if litros_s10 > 0 else 0.0

    placas = pd.concat([df_comb["placa"], df_manut["placa"], df_ped["placa"]]).nunique()

    # Gasto separado pela data do lançamento: o que caiu em dia útil e o que
    # caiu em fim de semana ou feriado. Sem isso, a média por dia útil embute
    # o gasto de sábado e domingo e fica maior do que a realidade.
    def _soma_por_dia(util):
        total = 0.0
        for df in (df_comb, df_manut, df_ped, df_comb_fora):
            if df is None or df.empty or "dia_util" not in df.columns:
                continue
            total += float(df.loc[df["dia_util"] == util, "valor"].sum())
        return total

    gasto_util = _soma_por_dia(True)
    gasto_nao_util = _soma_por_dia(False)

    return {
        "Gasto em dias úteis": gasto_util,
        "Gasto em fins de semana": gasto_nao_util,
        "Manutenção total": manut,
        "Manutenção sinistro": sinistro,
        "Manutenção sinistro %": (sinistro / manut * 100) if manut > 0 else 0.0,
        "Combustível total": comb,
        "Combustível TruckPag": comb_truckpag,
        "Combustível por fora": comb_fora,
        "Pedágio total": ped,
        "Total operacional": total,
        "KM rodado total": km,
        "Litros consumidos": litros,
        "Preço médio diesel S10": preco_s10,
        "Consumo médio (km/L)": km / litros if litros > 0 else 0.0,
        "Custo/km total": total / km if km > 0 else 0.0,
        "Custo/km combustível": comb / km if km > 0 else 0.0,
        "Custo/km manutenção": manut / km if km > 0 else 0.0,
        "Custo/km pedágio": ped / km if km > 0 else 0.0,
        "Número de passagens pedágio": int(len(df_ped)),
        "Placas ativas": int(placas),
    }


# =======================================================================
# EXTRAÇÃO
# =======================================================================

def _extrair_combustivel(conn, inicio, fim):
    print("⛽ Extraindo dados de Combustível (DW)...")
    query = f"""
    SELECT data, placa, valor, litragem, preco_unitario, grupo_combustivel,
           nome_combustivel, garagem, hodometro
    FROM torre.gold_truckpag_combustivel
    WHERE servico = 'ABASTECIMENTO' AND transacao_estornada = false
      AND data >= '{inicio}' AND data < '{fim}'
    """
    df = pd.read_sql(query, conn)
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.month
    df["dia_util"] = _marcar_dia_util(df["data"])

    for col in ["valor", "litragem", "preco_unitario", "hodometro"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # KM rodado = diferença entre hodômetros consecutivos da mesma placa.
    # Calculado sobre a série completa antes de qualquer recorte de período.
    df = df.sort_values(["placa", "data", "hodometro"])
    df["percorrido"] = df.groupby("placa")["hodometro"].diff().fillna(0)
    dias_desde_ultimo = df.groupby("placa")["data"].diff().dt.days
    df.loc[
        (df["percorrido"] < 0)
        | (df["percorrido"] > LIMITE_PERCORRIDO)
        | (dias_desde_ultimo > LIMITE_DIAS_GAP),
        "percorrido",
    ] = 0

    df["filial"] = df["garagem"].apply(_limpar_filial)
    df["eh_diesel_s10"] = (
        df["nome_combustivel"].astype(str).str.strip().str.upper().str.startswith("DIESEL S10")
    )
    return df


def _extrair_manutencao(meses, ano):
    """Extrai mês a mês: a view é pesada e uma consulta única estoura timeout."""
    print("🔧 Extraindo dados de Manutenção (Bluefleet)...")
    partes = []

    for m in meses:
        m_prox, ano_prox = (1, ano + 1) if m == 12 else (m + 1, ano)
        query = f"""
        SELECT Placa as placa, ValorTotal as valor, GrupoDespesa as grupo_despesa,
               Natureza_Correta as natureza, FILIAL as filial,
               FilialOperacional as filial_operacional, DataCriacao as data,
               OdometroConfirmadoOS as odometro, DescricaoItem as descricao_item
        FROM [referencia].[dbo].[torre_vw_FechamentoManutencao]
        WHERE DataCriacao >= '{ano}-{m:02d}-01' AND DataCriacao < '{ano_prox}-{m_prox:02d}-01'
        """
        try:
            conn = obter_conexao_bluefleet()
            cursor = conn.cursor()
            cursor.execute(query)
            colunas = [c[0] for c in cursor.description]
            linhas = cursor.fetchall()
            if linhas:
                partes.append(pd.DataFrame.from_records(linhas, columns=colunas))
            cursor.close()
            conn.close()
            print(f"   ✓ Manutenção do mês {m:02d} extraída com sucesso.")
        except Exception as erro:
            print(f"   ⚠️ Erro ao extrair mês {m:02d}: {erro}")

    if not partes:
        vazio = pd.DataFrame(columns=[
            "placa", "valor", "grupo_despesa", "natureza", "filial",
            "filial_operacional", "data", "odometro", "mes", "natureza_limpa",
            "descricao_item",
        ])
        vazio["valor"] = pd.to_numeric(vazio["valor"])
        vazio["odometro"] = pd.to_numeric(vazio["odometro"])
        return vazio

    df = pd.concat(partes, ignore_index=True)
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.month
    df["dia_util"] = _marcar_dia_util(df["data"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["odometro"] = pd.to_numeric(df["odometro"], errors="coerce").fillna(0.0)
    df["natureza_limpa"] = df["natureza"].apply(_limpar_natureza)
    df["filial"] = df["filial"].apply(_limpar_filial)
    return df


def _extrair_combustivel_fora(meses, ano):
    """Extrai combustível e Arla lançados em Notas Fiscais diretas/reembolsos (SQL Server)."""
    print("⛽ Extraindo combustível por fora / notas diretas (Bluefleet)...")
    partes = []

    for m in meses:
        m_prox, ano_prox = (1, ano + 1) if m == 12 else (m + 1, ano)
        query = f"""
        SELECT 
            FORMAT(DataCompetencia, 'yyyy-MM-dd') AS data,
            COALESCE(NULLIF(Unidade, ''), CentroCusto) AS filial,
            PagarReceberDe AS fornecedor,
            NumeroDocumento AS numero_documento,
            Natureza AS natureza,
            ValorNatureza AS valor,
            Descricao AS descricao
        FROM dbo.LancamentosComNaturezas
        WHERE (
            UPPER(Natureza) LIKE '%COMBUSTÍVEL%' 
         OR UPPER(Natureza) LIKE '%COMBUSTIVEL%' 
         OR UPPER(Natureza) LIKE '%ARLA%'
        )
        AND DataCompetencia >= '{ano}-{m:02d}-01' AND DataCompetencia < '{ano_prox}-{m_prox:02d}-01'
        AND (NumeroDocumento NOT LIKE '%FAT%' OR NumeroDocumento IS NULL)
        AND (UPPER(PagarReceberDe) NOT LIKE '%TRUCKPAG%' OR PagarReceberDe IS NULL)
        AND UPPER(COALESCE(Unidade, CentroCusto, '')) NOT LIKE '%REFERÊNCIA%'
        AND UPPER(COALESCE(Unidade, CentroCusto, '')) NOT LIKE '%REFERENCIA%'
        AND UPPER(COALESCE(Unidade, CentroCusto, '')) NOT LIKE '%LOCAÇÃO%'
        AND UPPER(COALESCE(Unidade, CentroCusto, '')) NOT LIKE '%LOCACAO%'
        """
        try:
            conn = obter_conexao_bluefleet()
            cursor = conn.cursor()
            cursor.execute(query)
            colunas = [c[0] for c in cursor.description]
            linhas = cursor.fetchall()
            if linhas:
                partes.append(pd.DataFrame.from_records(linhas, columns=colunas))
            cursor.close()
            conn.close()
        except Exception as erro:
            print(f"   ⚠️ Erro ao extrair combustível por fora mês {m:02d}: {erro}")

    if not partes:
        vazio = pd.DataFrame(columns=[
            "data", "filial", "fornecedor", "numero_documento", "natureza", "valor", "descricao", "mes"
        ])
        vazio["valor"] = pd.to_numeric(vazio["valor"])
        return vazio

    df = pd.concat(partes, ignore_index=True)
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.month
    df["dia_util"] = _marcar_dia_util(df["data"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["filial"] = df["filial"].apply(_limpar_filial)
    return df


def _extrair_pedagio(conn, inicio, fim):
    print("🛣️ Extraindo dados de Pedágio (DW)...")
    query = f"""
    SELECT data, placa, valor, operadora, garagem, filial_nome,
           cidade_posto, uf_posto
    FROM torre.gold_truckpag_pedagio
    WHERE data >= '{inicio}' AND data < '{fim}'
    """
    df = pd.read_sql(query, conn)
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.month
    df["dia_util"] = _marcar_dia_util(df["data"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["concessionaria"] = df["operadora"].apply(_concessionaria)
    df["filial"] = df["garagem"].apply(_limpar_filial)
    return df


def _extrair_frota(ano):
    """Idade e modelo dos veículos, para o gráfico de hodômetro x custo.

    Devolve {placa: {"idade": anos, "modelo": texto}}.
    """
    print("🚚 Extraindo cadastro da frota (Bluefleet)...")
    try:
        conn = obter_conexao_bluefleet()
        df = pd.read_sql(
            "SELECT Placa, AnoFabricacao, AnoModelo, Modelo, Montadora FROM dbo.Veiculos", conn
        )
        conn.close()
    except Exception as erro:
        print(f"   ⚠️ Não foi possível ler a frota: {erro}")
        return {}

    df["placa"] = df["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    df["ano"] = pd.to_numeric(df["AnoFabricacao"], errors="coerce")
    df["ano"] = df["ano"].fillna(pd.to_numeric(df["AnoModelo"], errors="coerce"))

    frota = {}
    for r in df.itertuples():
        idade = max(0, int(ano - r.ano)) if pd.notna(r.ano) else None
        frota[r.placa] = {"idade": idade, "modelo": _modelo_curto(r.Modelo, r.Montadora)}
    return frota


def _modelo_curto(modelo, montadora=None):
    """'DUCATO CARGO 2.8 CURTO/LONGO TB DIESEL' -> 'FIAT DUCATO CARGO'.

    O cadastro traz a versão completa, que não cabe na tabela do PDF. Mantemos
    a montadora e as duas primeiras palavras do modelo, que é o que identifica
    o veículo para quem lê o relatório.
    """
    texto = str(modelo or "").strip().upper()
    if not texto or texto == "NAN":
        return "—"

    # descarta cilindrada, câmbio e combustível ("2.8", "TB", "DIESEL", "16V"...)
    descartar = {"TB", "TDI", "DIESEL", "FLEX", "MT", "AT", "CD", "CS", "4X2", "4X4"}
    palavras = [p for p in texto.replace("/", " ").split()
                if p not in descartar and not any(c.isdigit() for c in p)]

    marca = str(montadora or "").strip().upper()
    if marca and marca != "NAN":
        marca = marca.split()[0]
        if palavras and palavras[0] == marca:
            palavras = palavras[1:]
        partes = [marca] + palavras[:2]
    else:
        partes = palavras[:3]

    return " ".join(partes)[:22] or "—"


# =======================================================================
# QUEBRAS
# =======================================================================

def _ufs_da_concessionaria(df_ped, nome, limite=3):
    """UFs onde a concessionária foi usada, ordenadas por gasto: 'PR, SC'."""
    if "uf_posto" not in df_ped.columns:
        return ""
    recorte = df_ped[df_ped["concessionaria"] == nome]
    por_uf = recorte.groupby("uf_posto")["valor"].sum().sort_values(ascending=False)
    ufs = [str(u).strip().upper() for u in por_uf.index if str(u).strip() and str(u) != "nan"]
    return ", ".join(ufs[:limite])


def _cidades_da_concessionaria(df_ped, nome, limite=2):
    """Praças de maior gasto da concessionária, para dar referência de rota."""
    if "cidade_posto" not in df_ped.columns:
        return ""
    recorte = df_ped[df_ped["concessionaria"] == nome]
    por_cidade = recorte.groupby("cidade_posto")["valor"].sum().sort_values(ascending=False)
    cidades = [str(c).strip().title() for c in por_cidade.index
               if str(c).strip() and str(c) != "nan"]
    return ", ".join(cidades[:limite])


def _quebras_combustivel_fora(df_comb, df_comb_fora, meses_atual):
    """Onde o abastecimento ainda escapa da TruckPag, por filial.

    Serve à página de centralização: mostra as praças que concentram a compra
    direta e o quanto cada uma pesa no combustível daquela filial.
    """
    if df_comb_fora is None or df_comb_fora.empty:
        return {"filiais": [], "fornecedores": {}, "natureza": {}, "total": 0.0}

    fora = df_comb_fora[df_comb_fora["mes"].isin(meses_atual)]
    if fora.empty:
        return {"filiais": [], "fornecedores": {}, "natureza": {}, "total": 0.0}

    # O centro de custo do financeiro é traduzido para o código da garagem via
    # CIDADE_PARA_FILIAL, o que permite comparar as duas bases na mesma chave.
    total_fora = float(fora["valor"].sum())
    fora = fora.copy()
    fora["filial_equivalente"] = fora["filial"].apply(centro_custo_para_filial)

    truckpag = df_comb[df_comb["mes"].isin(meses_atual)].groupby("filial")["valor"].sum()

    filiais = []
    for codigo, valor in fora.groupby("filial_equivalente")["valor"].sum().nlargest(12).items():
        operacional = codigo not in (ROTULO_NAO_ALOCADO, ROTULO_SEM_CENTRO, ROTULO_SEM_EQUIVALENCIA)
        via_truckpag = float(truckpag.get(codigo, 0.0)) if operacional else 0.0
        total_filial = float(valor) + via_truckpag
        filiais.append({
            "filial": codigo,
            "fora": float(valor),
            "truckpag": via_truckpag,
            # sem equivalência não há como calcular participação na filial
            "pct_fora": (float(valor) / total_filial * 100) if operacional and total_filial > 0 else None,
            "pct_do_fora": (float(valor) / total_fora * 100) if total_fora > 0 else 0.0,
            "operacional": operacional,
        })

    fornecedores = {
        str(k): float(v)
        for k, v in fora.groupby("fornecedor")["valor"].sum().nlargest(8).items()
    }

    # Parte do que o financeiro classifica como combustível é ARLA. A separação
    # evita ler o valor todo como litro de diesel comprado fora da rede.
    natureza = {}
    if "natureza" in fora.columns:
        for chave, valor in fora.groupby("natureza")["valor"].sum().items():
            rotulo = "Arla" if "ARLA" in _sem_acento(chave) else "Combustível"
            natureza[rotulo] = natureza.get(rotulo, 0.0) + float(valor)

    return {"filiais": filiais, "fornecedores": fornecedores, "natureza": natureza,
            "total": total_fora}


def _placas_recorrentes(df_manut, idade_frota):
    """Placas que aparecem no top de manutenção do mês em vários meses do período.

    Roda sobre todos os meses presentes em `df_manut` (não só o par
    anterior/atual): no mensal isso é o ano até o mês fechado, no semestral é
    o semestre inteiro. Mesma lógica de corte do top mensal (odômetro
    confirmado, `TOP_PLACAS_MANUTENCAO` maiores valores).
    """
    if df_manut.empty:
        return []

    aparicoes = {}
    for mes in sorted(df_manut["mes"].dropna().unique()):
        recorte = df_manut[df_manut["mes"] == mes]
        agrupado = recorte.groupby("placa").agg(valor=("valor", "sum"), odometro=("odometro", "max"))
        agrupado = agrupado[agrupado["odometro"] > 0].nlargest(TOP_PLACAS_MANUTENCAO, "valor")
        for posicao, (placa, linha) in enumerate(agrupado.iterrows(), start=1):
            registro = aparicoes.setdefault(placa, {"meses": [], "valor_total": 0.0, "melhor_posicao": posicao})
            registro["meses"].append(int(mes))
            registro["valor_total"] += float(linha.valor)
            registro["melhor_posicao"] = min(registro["melhor_posicao"], posicao)

    recorrentes = [
        {
            "placa": str(placa).strip().upper(),
            "modelo": _dado_frota(idade_frota, placa, "modelo") or "—",
            "meses_no_top": len(dados["meses"]),
            "meses": dados["meses"],
            "custo_nos_meses_top": dados["valor_total"],
            "melhor_posicao": dados["melhor_posicao"],
        }
        for placa, dados in aparicoes.items()
        if len(dados["meses"]) >= RECORRENCIA_MESES_MIN
    ]
    recorrentes.sort(key=lambda x: (-x["meses_no_top"], -x["custo_nos_meses_top"]))
    return recorrentes


def _manutencao_por_modelo(df_manut, idade_frota):
    """Custo médio de manutenção por veículo, agrupado por modelo.

    O denominador é a frota inteira cadastrada (`idade_frota`), não só os
    veículos com custo no período — senão um modelo com poucas ocorrências
    de manutenção pareceria mais barato do que é, por diluir em cima da
    contagem errada.
    """
    contagem_modelo = {}
    for registro in (idade_frota or {}).values():
        modelo = registro.get("modelo") if isinstance(registro, dict) else None
        if modelo and modelo != "—":
            contagem_modelo[modelo] = contagem_modelo.get(modelo, 0) + 1

    custo_por_modelo = {}
    if not df_manut.empty:
        for placa, valor in df_manut.groupby("placa")["valor"].sum().items():
            modelo = _dado_frota(idade_frota, placa, "modelo")
            if modelo and modelo != "—":
                custo_por_modelo[modelo] = custo_por_modelo.get(modelo, 0.0) + float(valor)

    linhas = [
        {
            "modelo": modelo,
            "veiculos": veiculos,
            "custo_total": float(custo_por_modelo.get(modelo, 0.0)),
            "custo_medio": float(custo_por_modelo.get(modelo, 0.0)) / veiculos,
        }
        for modelo, veiculos in contagem_modelo.items()
        if veiculos >= MODELOS_MIN_UNIDADES
    ]
    linhas.sort(key=lambda x: x["custo_medio"], reverse=True)
    return linhas


def _quebras(df_comb, df_manut, df_ped, meses_ref, meses_atual, idade_frota,
             sub_meses=None, df_comb_fora=None):
    """Detalhamentos por natureza, tipo, filial, concessionária e placa.

    Compara dois recortes quaisquer de meses: `meses_ref` (período de
    comparação) contra `meses_atual`. O relatório semestral passa B2 e B3;
    o mensal passa o mês anterior e o mês fechado. As chaves da saída são
    sempre "anterior" e "atual".

    `sub_meses` é o par de meses usado no gráfico de crescimento de passagens
    por praça; por padrão, os dois primeiros meses do período atual.
    """
    quebras = {}
    meses_b2, meses_b3 = meses_ref, meses_atual

    # --- Manutenção por natureza (anterior vs atual), em R$ e em R$/km ---
    natureza, natureza_km = {}, {}
    for nome, meses in [("anterior", meses_b2), ("atual", meses_b3)]:
        recorte = df_manut[df_manut["mes"].isin(meses)]
        km = float(df_comb.loc[df_comb["mes"].isin(meses) & (df_comb["percorrido"] > 0), "percorrido"].sum())
        soma = recorte.groupby("natureza_limpa")["valor"].sum()
        natureza[nome] = {rotulo: float(soma.get(chave, 0.0)) for chave, rotulo in NATUREZAS.items()}
        natureza_km[nome] = {n: (v / km if km > 0 else 0.0) for n, v in natureza[nome].items()}
    quebras["manutencao_natureza"] = natureza
    quebras["manutencao_natureza_km"] = natureza_km

    # --- Manutenção: top 10 filiais no B3 ---
    manut_b3 = df_manut[df_manut["mes"].isin(meses_b3)]
    quebras["manutencao_top_filiais"] = {
        k: float(v) for k, v in manut_b3.groupby("filial")["valor"].sum().nlargest(10).items()
    }

    # --- Combustível por tipo (anterior vs atual) ---
    combustivel = {}
    for nome, meses in [("anterior", meses_b2), ("atual", meses_b3)]:
        soma = df_comb[df_comb["mes"].isin(meses)].groupby("grupo_combustivel")["valor"].sum()
        combustivel[nome] = {
            rotulo: float(soma.get(grupo, 0.0)) for grupo, rotulo in ROTULO_COMBUSTIVEL.items()
        }
    quebras["combustivel_tipo"] = combustivel

    # --- Pedágio: concessionárias com maior gasto no B3 ---
    # A UF vem junto do nome: é o que mostra em quais rotas o gasto acontece.
    ped_b3 = df_ped[df_ped["mes"].isin(meses_b3)]
    quebras["pedagio_concessionaria"] = [
        {
            "nome": nome,
            "valor": float(valor),
            "ufs": _ufs_da_concessionaria(ped_b3, nome),
            "cidades": _cidades_da_concessionaria(ped_b3, nome),
        }
        for nome, valor in ped_b3.groupby("concessionaria")["valor"].sum().nlargest(8).items()
    ]

    # --- Pedágio: filiais com maior gasto no período ---
    quebras["pedagio_filial"] = [
        {"filial": nome, "valor": float(valor)}
        for nome, valor in ped_b3.groupby("filial")["valor"].sum().nlargest(6).items()
        if str(nome).strip() and str(nome) != "NAN"
    ]

    # --- Pedágio: praças que mais cresceram em passagens (mês a mês) ---
    mes_ini, mes_fim = sub_meses or (meses_b3[0], meses_b3[-1])
    escopo = df_ped[df_ped["mes"].isin([mes_ini, mes_fim])]
    passagens = escopo.groupby(["concessionaria", "mes"]).size().unstack(fill_value=0)
    crescimento = []
    for conc in passagens.index:
        antes = int(passagens.loc[conc].get(mes_ini, 0))
        depois = int(passagens.loc[conc].get(mes_fim, 0))
        crescimento.append({"praca": conc, "antes": antes, "depois": depois,
                            "delta": depois - antes})
    crescimento.sort(key=lambda x: x["delta"], reverse=True)
    quebras["pedagio_passagens"] = crescimento[:6]
    quebras["pedagio_passagens_meses"] = (mes_ini, mes_fim)

    # --- Custo/km de combustível por filial (anterior vs atual) ---
    # O corte por km evita R$/km instável em filial com quase nenhuma rodagem
    km_minimo = KM_MINIMO_FILIAL * len(meses_b3) / 2
    linhas = []
    for filial in sorted(df_comb["filial"].dropna().unique()):
        if not filial or filial == "NAN":
            continue
        registro = {"filial": filial}
        for nome, meses in [("ref", meses_b2), ("atual", meses_b3)]:
            recorte = df_comb[(df_comb["filial"] == filial) & (df_comb["mes"].isin(meses))]
            km = float(recorte.loc[recorte["percorrido"] > 0, "percorrido"].sum())
            valor = float(recorte["valor"].sum())
            registro[f"km_{nome}"] = km
            registro[f"ckm_{nome}"] = valor / km if km > 0 else 0.0
        if min(registro["km_ref"], registro["km_atual"]) < km_minimo:
            continue
        registro["var"] = _variacao(registro["ckm_atual"], registro["ckm_ref"])
        registro["placas"] = int(
            df_comb[(df_comb["filial"] == filial)
                    & (df_comb["mes"].isin(meses_b3))]["placa"].nunique()
        )
        linhas.append(registro)
    linhas.sort(key=lambda x: x["ckm_atual"], reverse=True)
    quebras["custo_km_filial"] = linhas

    # --- Top 20 placas por custo de manutenção no B3 ---
    # `posicao` numera do maior custo para o menor: é o número que aparece
    # dentro do ponto no gráfico e na primeira coluna da tabela.
    if not manut_b3.empty:
        agrupado = manut_b3.groupby("placa").agg(valor=("valor", "sum"), odometro=("odometro", "max"))
        # Sem hodômetro confirmado a placa não tem onde ser plotada no eixo X
        agrupado = agrupado[agrupado["odometro"] > 0].nlargest(TOP_PLACAS_MANUTENCAO, "valor")
        quebras["top_placas_manutencao"] = [
            {
                "posicao": i,
                "placa": str(placa).strip().upper(),
                "valor": float(linha.valor),
                "odometro": float(linha.odometro),
                "idade": _dado_frota(idade_frota, placa, "idade"),
                "modelo": _dado_frota(idade_frota, placa, "modelo") or "—",
            }
            for i, (placa, linha) in enumerate(agrupado.iterrows(), start=1)
        ]

    else:
        quebras["top_placas_manutencao"] = []

    # --- Placas recorrentes no top de manutenção, ao longo do período todo ---
    quebras["manutencao_recorrentes"] = _placas_recorrentes(df_manut, idade_frota)

    # --- Custo médio de manutenção por modelo, no período completo (não só
    # o mês atual): um mês só é amostra curta demais pra essa comparação, o
    # mesmo problema que já vale pra placas recorrentes acima.
    quebras["manutencao_modelo"] = _manutencao_por_modelo(df_manut, idade_frota)

    # --- Combustível comprado fora da TruckPag, por filial ---
    quebras["combustivel_fora"] = _quebras_combustivel_fora(df_comb, df_comb_fora, meses_b3)

    return quebras


# =======================================================================
# FUNÇÃO PRINCIPAL
# =======================================================================

def calcular_dados_torre(semestre=1, ano=2026, usar_cache=True, salvar_cache=True):
    """Consolida todos os indicadores do relatório.

    usar_cache: lê `dados/cache/torre_{ano}_S{semestre}.pkl` se existir, evitando
    reconsultar os bancos quando só o layout ou os textos do PDF mudaram.
    """
    caminho_cache = os.path.join(DIR_CACHE, f"torre_bruto_{ano}_S{semestre}.pkl")

    if semestre == 1:
        inicio, fim, meses_nomes = f"{ano}-01-01", f"{ano}-07-01", MESES_S1
    else:
        inicio, fim, meses_nomes = f"{ano}-07-01", f"{ano + 1}-01-01", MESES_S2

    meses = list(meses_nomes.keys())

    if usar_cache and os.path.exists(caminho_cache):
        with open(caminho_cache, "rb") as arquivo:
            bruto = pickle.load(arquivo)
        df_comb, df_manut, df_ped = bruto["combustivel"], bruto["manutencao"], bruto["pedagio"]
        df_comb_fora = bruto.get("combustivel_fora", pd.DataFrame())
        idade_frota = bruto["frota"]
        print(f"💾 Usando dados extraídos em {bruto['extraido_em']} (cache).")
        print("   Para reconsultar os bancos, rode com --sem-cache.")
    else:
        print(f"📊 Iniciando extração de dados da Torre de Controle - Semestre {semestre}/{ano}")
        print("🔌 Conectando aos bancos de dados...")
        conn_dw = obter_conexao_dw()
        df_comb = _extrair_combustivel(conn_dw, inicio, fim)
        df_ped = _extrair_pedagio(conn_dw, inicio, fim)
        conn_dw.close()

        df_manut = _extrair_manutencao(meses, ano)
        df_comb_fora = _extrair_combustivel_fora(meses, ano)
        idade_frota = _extrair_frota(ano)

        if salvar_cache:
            os.makedirs(DIR_CACHE, exist_ok=True)
            with open(caminho_cache, "wb") as arquivo:
                pickle.dump({
                    "combustivel": df_comb,
                    "manutencao": df_manut,
                    "combustivel_fora": df_comb_fora,
                    "pedagio": df_ped,
                    "frota": idade_frota,
                    "extraido_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }, arquivo)
            print(f"💾 Dados brutos gravados em {caminho_cache}")

    print("🧮 Calculando KPIs...")

    bimestres = {
        "B1": {"meses": meses[0:2], "rotulo": f"{meses_nomes[meses[0]]}+{meses_nomes[meses[1]]}"},
        "B2": {"meses": meses[2:4], "rotulo": f"{meses_nomes[meses[2]]}+{meses_nomes[meses[3]]}"},
        "B3": {"meses": meses[4:6], "rotulo": f"{meses_nomes[meses[4]]}+{meses_nomes[meses[5]]}"},
    }

    # Mesmo recorte do relatório mensal: matriz, diretoria e Referência fora
    _garantir_dia_util(df_comb, df_manut, df_ped, df_comb_fora)
    df_comb = _remover_nao_operacionais(df_comb)
    df_manut = _remover_nao_operacionais(df_manut)
    df_ped = _remover_nao_operacionais(df_ped)
    df_comb_fora = _limpar_combustivel_fora(df_comb_fora)

    dados = {
        "meta": {
            "semestre": semestre,
            "ano": ano,
            "meses": [meses_nomes[m] for m in meses],
            "bimestres": {k: v["rotulo"] for k, v in bimestres.items()},
            "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        },
        "mensal": {},
        "bimestral": {},
        "variacoes": {},
    }

    for m in meses:
        dados["mensal"][meses_nomes[m]] = _kpis(
            df_comb[df_comb["mes"] == m],
            df_manut[df_manut["mes"] == m],
            df_ped[df_ped["mes"] == m],
            df_comb_fora[df_comb_fora["mes"] == m] if not df_comb_fora.empty else None,
        )

    for nome, info in bimestres.items():
        alvo = info["meses"]
        dados["bimestral"][nome] = _kpis(
            df_comb[df_comb["mes"].isin(alvo)],
            df_manut[df_manut["mes"].isin(alvo)],
            df_ped[df_ped["mes"].isin(alvo)],
            df_comb_fora[df_comb_fora["mes"].isin(alvo)] if not df_comb_fora.empty else None,
        )

    for atual, anterior in [("B2", "B1"), ("B3", "B2"), ("B3", "B1")]:
        dados["variacoes"][f"{atual} vs {anterior}"] = {
            chave: _variacao(dados["bimestral"][atual][chave], dados["bimestral"][anterior][chave])
            for chave in dados["bimestral"][atual]
        }

    # Compatibilidade com o formato anterior do dicionário
    for atual, anterior in [("B2", "B1"), ("B3", "B2")]:
        dados["bimestral"][f"Variação {atual} vs {anterior}"] = dados["variacoes"][f"{atual} vs {anterior}"]

    dados["quebras"] = _quebras(df_comb, df_manut, df_ped,
                                bimestres["B2"]["meses"], bimestres["B3"]["meses"],
                                idade_frota)

    print("✅ Dados calculados com sucesso!")
    return dados


# =======================================================================
# RELATÓRIO MENSAL
# =======================================================================

def calcular_dados_mes(mes=7, ano=2026, usar_cache=True, salvar_cache=True):
    """Indicadores do mês fechado, comparado ao mês anterior.

    Extrai de janeiro até o fim do mês pedido, para que o relatório mostre
    também a evolução do ano e o acumulado. O cache é por mês de referência.
    """
    caminho_cache = os.path.join(DIR_CACHE, f"torre_bruto_mensal_{ano}_{mes:02d}.pkl")
    inicio = f"{ano}-01-01"
    fim = f"{ano + 1}-01-01" if mes == 12 else f"{ano}-{mes + 1:02d}-01"
    meses = list(range(1, mes + 1))

    if usar_cache and os.path.exists(caminho_cache):
        with open(caminho_cache, "rb") as arquivo:
            bruto = pickle.load(arquivo)
        df_comb, df_manut, df_ped = bruto["combustivel"], bruto["manutencao"], bruto["pedagio"]
        df_comb_fora = bruto.get("combustivel_fora", pd.DataFrame())
        idade_frota = bruto["frota"]
        print(f"💾 Usando dados extraídos em {bruto['extraido_em']} (cache).")
        print("   Para reconsultar os bancos, rode com --sem-cache.")
    else:
        print(f"📊 Extraindo dados até {MESES_EXTENSO[mes]}/{ano}...")
        print("🔌 Conectando aos bancos de dados...")
        conn_dw = obter_conexao_dw()
        df_comb = _extrair_combustivel(conn_dw, inicio, fim)
        df_ped = _extrair_pedagio(conn_dw, inicio, fim)
        conn_dw.close()

        df_manut = _extrair_manutencao(meses, ano)
        df_comb_fora = _extrair_combustivel_fora(meses, ano)
        idade_frota = _extrair_frota(ano)

        if salvar_cache:
            os.makedirs(DIR_CACHE, exist_ok=True)
            with open(caminho_cache, "wb") as arquivo:
                pickle.dump({
                    "combustivel": df_comb,
                    "manutencao": df_manut,
                    "combustivel_fora": df_comb_fora,
                    "pedagio": df_ped,
                    "frota": idade_frota,
                    "extraido_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }, arquivo)
            print(f"💾 Dados brutos gravados em {caminho_cache}")

    # Matriz, diretoria e Referência ficam fora do relatório executivo; o
    # rateio sai do combustível por fora. Filtrado aqui, vale para tudo abaixo.
    _garantir_dia_util(df_comb, df_manut, df_ped, df_comb_fora)
    df_comb = _remover_nao_operacionais(df_comb)
    df_manut = _remover_nao_operacionais(df_manut)
    df_ped = _remover_nao_operacionais(df_ped)
    df_comb_fora = _limpar_combustivel_fora(df_comb_fora)

    print("🧮 Calculando KPIs...")

    mes_anterior = mes - 1 if mes > 1 else None

    dados = {
        "meta": {
            "mes": mes,
            "ano": ano,
            "mes_nome": MESES[mes],
            "mes_extenso": MESES_EXTENSO[mes],
            "mes_anterior": mes_anterior,
            "mes_anterior_nome": MESES[mes_anterior] if mes_anterior else None,
            "mes_anterior_extenso": MESES_EXTENSO[mes_anterior] if mes_anterior else None,
            "meses": [MESES[m] for m in meses],
            "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        },
        "mensal": {},
    }

    for m in meses:
        kpis = _kpis(
            df_comb[df_comb["mes"] == m],
            df_manut[df_manut["mes"] == m],
            df_ped[df_ped["mes"] == m],
            df_comb_fora[df_comb_fora["mes"] == m] if not df_comb_fora.empty else None,
        )
        uteis = dias_uteis(m, ano)
        nao_uteis = dias_do_mes(m, ano) - uteis
        kpis["Dias úteis"] = uteis
        kpis["Dias não úteis"] = nao_uteis
        # média sobre o gasto que de fato ocorreu em cada tipo de dia
        kpis["Média por dia útil"] = kpis["Gasto em dias úteis"] / uteis if uteis else 0.0
        kpis["Média por fim de semana"] = (
            kpis["Gasto em fins de semana"] / nao_uteis if nao_uteis else 0.0)
        kpis["KM por dia útil"] = kpis["KM rodado total"] / uteis if uteis else 0.0
        dados["mensal"][MESES[m]] = kpis

    dados["atual"] = dados["mensal"][MESES[mes]]
    dados["anterior"] = dados["mensal"][MESES[mes_anterior]] if mes_anterior else None

    if dados["anterior"]:
        dados["variacao"] = {
            chave: _variacao(dados["atual"][chave], dados["anterior"][chave])
            for chave in dados["atual"]
        }
    else:
        dados["variacao"] = {chave: 0.0 for chave in dados["atual"]}

    # Acumulado do ano e média mensal, para dar escala ao mês isolado
    dados["acumulado"] = _kpis(df_comb, df_manut, df_ped, df_comb_fora)
    dados["media_mensal"] = {
        chave: (valor / len(meses) if isinstance(valor, (int, float)) else valor)
        for chave, valor in dados["acumulado"].items()
        if chave in ("Manutenção total", "Combustível total", "Pedágio total",
                     "Total operacional", "KM rodado total")
    }

    meses_ref = [mes_anterior] if mes_anterior else [mes]
    dados["quebras"] = _quebras(df_comb, df_manut, df_ped, meses_ref, [mes],
                                idade_frota, sub_meses=(meses_ref[0], mes),
                                df_comb_fora=df_comb_fora)

    print("✅ Dados calculados com sucesso!")
    return dados


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_resumo_validacao(dados):
    print("\n" + "=" * 60)
    print("📊 RESUMO DE VALIDAÇÃO - TORRE DE CONTROLE")
    print("=" * 60)

    for mes, kpis in dados["mensal"].items():
        print(f"\n📅 {mes}")
        print(f"  🔧 Manutenção:  {formatar_moeda(kpis['Manutenção total'])}")
        print(f"  ⛽ Combustível: {formatar_moeda(kpis['Combustível total'])}")
        print(f"  🛣️ Pedágio:     {formatar_moeda(kpis['Pedágio total'])}")
        print(f"  💵 Total:       {formatar_moeda(kpis['Total operacional'])}")
        print(f"  📏 KM rodado:   {kpis['KM rodado total']:,.0f}".replace(",", "."))
        print(f"  ⛽ Diesel S10:  {formatar_moeda(kpis['Preço médio diesel S10'])}/L")
        print(f"  💸 Custo/km:    {formatar_moeda(kpis['Custo/km total'])}")

    print("\n" + "=" * 60)
    print("📈 BIMESTRES")
    print("=" * 60)
    for bim in ["B1", "B2", "B3"]:
        kpis = dados["bimestral"][bim]
        rotulo = dados["meta"]["bimestres"][bim]
        print(f"\n📊 {bim} ({rotulo}):")
        print(f"  Total operacional: {formatar_moeda(kpis['Total operacional'])}")
        print(f"  KM rodado:         {kpis['KM rodado total']:,.0f}".replace(",", "."))
        print(f"  Custo/km:          {formatar_moeda(kpis['Custo/km total'])}")
        print(f"  Diesel S10:        {formatar_moeda(kpis['Preço médio diesel S10'])}/L")
        print(f"  Consumo médio:     {kpis['Consumo médio (km/L)']:.2f} km/L")

    for nome, variacao in dados["variacoes"].items():
        print(f"\n🔄 Variação {nome}:")
        print(f"  Total operacional: {variacao['Total operacional']:+.1f}%")
        print(f"  Custo/km:          {variacao['Custo/km total']:+.1f}%")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calcula os dados da Torre de Controle.")
    parser.add_argument("--semestre", type=int, default=1)
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--sem-cache", action="store_true", help="Reconsulta os bancos.")
    args = parser.parse_args()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dados = calcular_dados_torre(args.semestre, args.ano, usar_cache=not args.sem_cache)
        gerar_resumo_validacao(dados)
