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

# Percorrido acima deste valor é ruído de hodômetro (troca de painel, digitação)
LIMITE_PERCORRIDO = 50000

# Filial com quilometragem muito baixa gera R$/km instável (divisão por
# quase zero), então fica fora do ranking e da tabela comparativa.
KM_MINIMO_FILIAL = 10000


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


def _variacao(atual, anterior):
    if anterior and anterior > 0:
        return ((atual / anterior) - 1) * 100
    return 0.0 if not atual else 100.0


def _kpis(df_comb, df_manut, df_ped):
    """Bloco de indicadores para um recorte já filtrado dos três dataframes."""
    comb = float(df_comb["valor"].sum()) if not df_comb.empty else 0.0
    manut = float(df_manut["valor"].sum()) if not df_manut.empty else 0.0
    ped = float(df_ped["valor"].sum()) if not df_ped.empty else 0.0
    total = comb + manut + ped

    km = float(df_comb.loc[df_comb["percorrido"] > 0, "percorrido"].sum()) if not df_comb.empty else 0.0
    litros = float(df_comb["litragem"].sum()) if not df_comb.empty else 0.0

    # Preço do Diesel S10: média ponderada pela litragem (não média simples,
    # que distorceria por causa de abastecimentos pequenos)
    s10 = df_comb[df_comb["eh_diesel_s10"]] if not df_comb.empty else df_comb
    litros_s10 = float(s10["litragem"].sum()) if not s10.empty else 0.0
    valor_s10 = float(s10["valor"].sum()) if not s10.empty else 0.0
    preco_s10 = valor_s10 / litros_s10 if litros_s10 > 0 else 0.0

    placas = pd.concat([df_comb["placa"], df_manut["placa"], df_ped["placa"]]).nunique()

    return {
        "Manutenção total": manut,
        "Combustível total": comb,
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

    for col in ["valor", "litragem", "preco_unitario", "hodometro"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # KM rodado = diferença entre hodômetros consecutivos da mesma placa.
    # Calculado sobre a série completa antes de qualquer recorte de período.
    df = df.sort_values(["placa", "data", "hodometro"])
    df["percorrido"] = df.groupby("placa")["hodometro"].diff().fillna(0)
    df.loc[(df["percorrido"] < 0) | (df["percorrido"] > LIMITE_PERCORRIDO), "percorrido"] = 0

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
               OdometroConfirmadoOS as odometro
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
        ])
        vazio["valor"] = pd.to_numeric(vazio["valor"])
        vazio["odometro"] = pd.to_numeric(vazio["odometro"])
        return vazio

    df = pd.concat(partes, ignore_index=True)
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.month
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["odometro"] = pd.to_numeric(df["odometro"], errors="coerce").fillna(0.0)
    df["natureza_limpa"] = df["natureza"].apply(_limpar_natureza)
    df["filial"] = df["filial"].apply(_limpar_filial)
    return df


def _extrair_pedagio(conn, inicio, fim):
    print("🛣️ Extraindo dados de Pedágio (DW)...")
    query = f"""
    SELECT data, placa, valor, operadora, garagem, filial_nome
    FROM torre.gold_truckpag_pedagio
    WHERE data >= '{inicio}' AND data < '{fim}'
    """
    df = pd.read_sql(query, conn)
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.month
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["concessionaria"] = df["operadora"].apply(_concessionaria)
    df["filial"] = df["garagem"].apply(_limpar_filial)
    return df


def _extrair_frota(ano):
    """Idade dos veículos, usada para colorir o gráfico de hodômetro x custo."""
    print("🚚 Extraindo cadastro da frota (Bluefleet)...")
    try:
        conn = obter_conexao_bluefleet()
        df = pd.read_sql(
            "SELECT Placa, AnoFabricacao, AnoModelo, Modelo FROM dbo.Veiculos", conn
        )
        conn.close()
    except Exception as erro:
        print(f"   ⚠️ Não foi possível ler a frota: {erro}")
        return {}

    df["placa"] = df["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    df["ano"] = pd.to_numeric(df["AnoFabricacao"], errors="coerce")
    df["ano"] = df["ano"].fillna(pd.to_numeric(df["AnoModelo"], errors="coerce"))
    df = df.dropna(subset=["ano"])
    return {r.placa: max(0, int(ano - r.ano)) for r in df.itertuples()}


# =======================================================================
# QUEBRAS
# =======================================================================

def _quebras(df_comb, df_manut, df_ped, meses_ref, meses_atual, idade_frota,
             sub_meses=None):
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
    ped_b3 = df_ped[df_ped["mes"].isin(meses_b3)]
    quebras["pedagio_concessionaria"] = {
        k: float(v) for k, v in ped_b3.groupby("concessionaria")["valor"].sum().nlargest(8).items()
    }

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
        if not filial or filial in ("NAN", "REFERENCIA CURITIBA"):
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
    if not manut_b3.empty:
        agrupado = manut_b3.groupby("placa").agg(valor=("valor", "sum"), odometro=("odometro", "max"))
        # Sem hodômetro confirmado a placa não tem onde ser plotada no eixo X
        agrupado = agrupado[agrupado["odometro"] > 0].nlargest(20, "valor")
        quebras["top_placas_manutencao"] = [
            {
                "placa": str(placa).strip().upper(),
                "valor": float(linha.valor),
                "odometro": float(linha.odometro),
                "idade": idade_frota.get(str(placa).replace("-", "").strip().upper()),
            }
            for placa, linha in agrupado.iterrows()
        ]
    else:
        quebras["top_placas_manutencao"] = []

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
        idade_frota = _extrair_frota(ano)

        if salvar_cache:
            os.makedirs(DIR_CACHE, exist_ok=True)
            with open(caminho_cache, "wb") as arquivo:
                pickle.dump({
                    "combustivel": df_comb,
                    "manutencao": df_manut,
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
        )

    for nome, info in bimestres.items():
        alvo = info["meses"]
        dados["bimestral"][nome] = _kpis(
            df_comb[df_comb["mes"].isin(alvo)],
            df_manut[df_manut["mes"].isin(alvo)],
            df_ped[df_ped["mes"].isin(alvo)],
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
        idade_frota = _extrair_frota(ano)

        if salvar_cache:
            os.makedirs(DIR_CACHE, exist_ok=True)
            with open(caminho_cache, "wb") as arquivo:
                pickle.dump({
                    "combustivel": df_comb,
                    "manutencao": df_manut,
                    "pedagio": df_ped,
                    "frota": idade_frota,
                    "extraido_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }, arquivo)
            print(f"💾 Dados brutos gravados em {caminho_cache}")

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
        dados["mensal"][MESES[m]] = _kpis(
            df_comb[df_comb["mes"] == m],
            df_manut[df_manut["mes"] == m],
            df_ped[df_ped["mes"] == m],
        )

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
    dados["acumulado"] = _kpis(df_comb, df_manut, df_ped)
    dados["media_mensal"] = {
        chave: (valor / len(meses) if isinstance(valor, (int, float)) else valor)
        for chave, valor in dados["acumulado"].items()
        if chave in ("Manutenção total", "Combustível total", "Pedágio total",
                     "Total operacional", "KM rodado total")
    }

    meses_ref = [mes_anterior] if mes_anterior else [mes]
    dados["quebras"] = _quebras(df_comb, df_manut, df_ped, meses_ref, [mes],
                                idade_frota, sub_meses=(meses_ref[0], mes))

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
