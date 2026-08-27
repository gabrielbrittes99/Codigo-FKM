"""
Módulo de Mapeamento de Filiais - FKM
Mapeia placas para suas respectivas filiais de manutenção
Usa lógica temporal: para cada abastecimento, busca a manutenção
mais recente ANTES daquela data e usa a filial desse registro.
"""

import csv
import os

import numpy as np
import pandas as pd

# Exceções forçadas para filiais específicas (centralizado)
# Placas que devem SEMPRE ir para uma filial específica, independente da lógica temporal.
# ATENÇÃO: ZERAR ESTE DICIONÁRIO A CADA NOVO FECHAMENTO MENSAL PARA EVITAR QUE REGRAS
# ANTIGAS AFETEM OS DADOS DO MÊS ATUAL!
EXCECOES_FORCADAS = {
    "SDW8B50": "GRITSCH - RDN",  # Reatribuição / Rateio para Rondonópolis
    "RHE1F56": "GRITSCH - CWB (BASE)",  # Julho/2026 - Abastecimentos para CWB BASE
    "SEF8G22": "GRITSCH - CWB (BASE)",  # Julho/2026 - Abastecimentos para CWB BASE
    "RHS3G78": "GRITSCH - CWB (BASE)",  # Julho/2026 - Combustível para CWB BASE
    "SFG4I64": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "TAN9C60": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "TAV9E95": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "UBK4B56": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "UBN9E24": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "UBN9E25": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "UBN9E26": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "UBR9B03": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "UBR9B05": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "UBR9B07": "GRITSCH - PET",  # Julho/2026 - Pelotas
    "TBJ8E28": "GRITSCH - GOI",  # Julho/2026 - Goiânia
    "SDU9F60": "GRITSCH - MATRIZ",  # Julho/2026 - Matriz
    "TBK1J46": "GRITSCH - MATRIZ",  # Julho/2026 - Matriz
    "SEE9I31": "REFERÊNCIA SINOP",   # Mudar para REFERÊNCIA SINOP e sair de Gritsch Sinop
    "SEP8G07": "REFERÊNCIA SINOP",   # Mudar para REFERÊNCIA SINOP e sair de Gritsch Sinop
    "SFL6I25": "GRITSCH - BSB",     # Mapeamento Julho/2026 - Brasília
    "TAY6D07": "GRITSCH - BSB",     # Mapeamento Julho/2026 - Brasília
    "SFI8F40": "GRITSCH - GOI",     # Julho/2026 - Ajuste manual (remover de GPA)
    "BEP1I25": "GRITSCH - CWB (BASE)", # Julho/2026 - Ajuste manual (remover de GPA)
    "SFI4A35": "GRITSCH - MGA",     # Julho/2026 - Ajuste manual Maringá
    # ── Santa Maria (RIA) — Placas transferidas de POA a partir de Agosto/2026 ──
    "UBH2J71": "GRITSCH - RIA",     # Agosto/2026 - CRISTHIAN
    "UBR9B22": "GRITSCH - RIA",     # Agosto/2026 - IVO
    "UBR9B09": "GRITSCH - RIA",     # Agosto/2026 - FABRICIO
    "SEP6E34": "GRITSCH - RIA",     # Agosto/2026 - GUILHERME (Saveiro Reserva)
    "UBR9B08": "GRITSCH - RIA",     # Agosto/2026 - MAURICIO
    "UBR9A97": "GRITSCH - RIA",     # Agosto/2026 - RUI
    "UBR9B27": "GRITSCH - RIA",     # Agosto/2026 - LUCIANO RIBAS
    "UBR9A92": "GRITSCH - RIA",     # Agosto/2026 - TIAGO
    "UBR9B16": "GRITSCH - RIA",     # Agosto/2026 - GILSON
    "UCB4H75": "GRITSCH - RIA",     # Agosto/2026 - JOAO (3/4)
    "SFK1E50": "GRITSCH - RIA",     # Agosto/2026 - LEANDRO (Toco)
    "TAI9A24": "GRITSCH - RIA",     # Agosto/2026 - GUILHERME (Strada Alegrete - Envelopamento)
}

# Exceções exclusivas para MANUTENÇÃO (ajusta a filial de manutenção das placas)
# ATENÇÃO: ZERAR ESTE DICIONÁRIO A CADA NOVO FECHAMENTO MENSAL!
EXCECOES_MANUTENCAO = {
    "RHS3G78": "GRITSCH - PBC",  # Julho/2026 - Manutenção para Pato Branco
    "SDW8B50": "GRITSCH - MATRIZ",  # Julho/2026 - Manutenção para Matriz (abastecimento permanece RDN)
    "SFD5C29": "GRITSCH - CWB (BASE)", # Julho/2026 - Manutenção para CWB (BASE)
}

# Placas excluídas da frota (sinistrados, indenizados, baixados, veículos para venda / desmobilizados)
PLACAS_EXCLUIDAS = {
    "SEC7A68",
    "SDU9F70",
    "ASU8677",
    "SDU9F84",
    "SDU9F94",
    "SDU9G06",
    "SEP6E12",
    "SEP6E23",
    "SEP6E24",
    "SEP6E35",
}

# Unidades do BlueFleet que não pertencem ao FKM Gritsch
# Veículos nessas unidades são excluídos do fechamento
UNIDADES_NAO_OPERACIONAIS = {
    "VEÍCULOS PARA VENDA",
    "VEÍCULOS VENDIDOS",
    "VEÍCULOS ROUBADOS",
    "VEÍCULOS PARTICULARES",
    "VEÍCULOS A DEFINIR",
    "VEÍCULOS A DEFINIR SP",
    "X FILIAL TESTE",
}


# Tenta carregar ajustes dinâmicos mensais de um arquivo CSV na raiz do projeto
# O formato esperado é: Placa,Filial
# Exemplo: ABC1234,GRITSCH - NOVA FILIAL
arquivo_ajustes = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ajustes_placas.csv"
)
if os.path.exists(arquivo_ajustes):
    try:
        with open(arquivo_ajustes, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # Pula o cabeçalho
            for row in reader:
                if len(row) >= 2:
                    placa = row[0].strip().replace("-", "").upper()
                    filial = row[1].strip()
                    if placa and filial:
                        EXCECOES_FORCADAS[placa] = filial
        print(f"✅ Ajustes dinâmicos de placas carregados de 'ajustes_placas.csv'.")
    except Exception as e:
        print(f"⚠️  Erro ao carregar 'ajustes_placas.csv': {e}")

# Exceções por ID de Transação (Prioridade Máxima)
# IDs que devem ser vinculados a filiais específicas independente de placa ou data
EXCECOES_TRANSACOES = {
}


def normalizar_filial(filial):
    """
    Normaliza nomes de filiais para consolidação
    - CWB (ECT) → CWB (BASE)
    - CWB (BASE) → CWB (BASE)
    - CWB (DIR) permanece separada
    - RATEIO GRI / GRITSCH MATRIZ → GRITSCH - MATRIZ
    - Outras filiais permanecem inalteradas
    """
    if pd.isna(filial):
        return filial

    filial_str = str(filial).strip()

    # Normalizar espaços múltiplos para comparação
    filial_normalizada = " ".join(filial_str.split())
    filial_upper = filial_normalizada.upper()

    # Consolidar CWB (ECT) em CWB (BASE)
    if "CWB (ECT)" in filial_upper or "CWB(ECT)" in filial_upper:
        return filial_str.replace("CWB (ECT)", "CWB (BASE)").replace(
            "CWB(ECT)", "CWB (BASE)"
        )

    # Consolidar RATEIO GRI, RATEIO - GRI e GRITSCH MATRIZ em GRITSCH - MATRIZ
    if (
        "RATEIO GRI" in filial_upper
        or "RATEIO - GRI" in filial_upper
        or "GRITSCH RATEIO" in filial_upper
        or "GRITSCH MATRIZ" in filial_upper
        or "GRITSCH - MATRIZ" in filial_upper
    ):
        return "GRITSCH - MATRIZ"

    # Consolidar CBL (Campos Belos) em GOI
    if (
        "GRITSCH - CBL" in filial_upper
        or "GRITSCH CBL" in filial_upper
        or filial_upper == "CBL"
    ):
        return "GRITSCH - GOI"

    return filial_str


def criar_mapa_filiais(caminho_manutencao):
    """
    Lê a planilha de manutenção e cria um histórico temporal por placa.

    Para cada placa, retorna uma lista de (data, filial) ordenada por data.
    Assim, para cada abastecimento, podemos buscar a manutenção mais recente
    ANTES daquela data e usar a filial daquele registro.

    Args:
        caminho_manutencao: Caminho para o arquivo Excel de manutenção

    Returns:
        dict: {placa_normalizada: [(data1, filial1), (data2, filial2), ...]}
              Ordenado por data (mais antiga primeiro)
    """
    try:
        print("🔍 Carregando dados de manutenção para mapeamento de filiais...")
        df_manut = pd.read_excel(caminho_manutencao)

        if "Placa" not in df_manut.columns or "FILIAL" not in df_manut.columns:
            print(
                "⚠️ Colunas 'Placa' ou 'FILIAL' não encontradas na planilha de manutenção"
            )
            return {}

        # Normalizar placas
        df_manut["Placa_Clean"] = (
            df_manut["Placa"]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )

        # Normalizar filiais
        df_manut["FILIAL"] = df_manut["FILIAL"].apply(normalizar_filial)
        print("🔄 Filiais normalizadas (CWB ECT → CWB BASE, RATEIO GRI → MATRIZ)")

        # Aplicar exceções de manutenção
        for placa_manut, filial_manut in EXCECOES_MANUTENCAO.items():
            mask_manut = df_manut["Placa_Clean"] == placa_manut
            if mask_manut.sum() > 0:
                df_manut.loc[mask_manut, "FILIAL"] = filial_manut

        # Remover placas vazias ou inválidas
        df_manut = df_manut[df_manut["Placa_Clean"].str.len() > 0]
        df_manut = df_manut[df_manut["Placa_Clean"] != "NAN"]

        # Converter data de emissão
        if "DataEmissao" in df_manut.columns:
            df_manut["DataEmissao"] = pd.to_datetime(
                df_manut["DataEmissao"], dayfirst=True, format="mixed", errors="coerce"
            )
        else:
            df_manut["DataEmissao"] = pd.NaT

        # Construir histórico temporal por placa
        historico = {}

        for placa in df_manut["Placa_Clean"].unique():
            df_placa = df_manut[df_manut["Placa_Clean"] == placa]

            # Pegar combinações únicas de data + filial
            registros = []
            for _, row in (
                df_placa[["DataEmissao", "FILIAL"]].drop_duplicates().iterrows()
            ):
                data = row["DataEmissao"]
                filial = row["FILIAL"]
                if pd.notna(filial):
                    registros.append((data, filial))

            if registros:
                # Ordenar por data (mais antiga primeiro), NaT vai pro final
                registros.sort(
                    key=lambda x: (
                        pd.isna(x[0]),
                        x[0] if pd.notna(x[0]) else pd.Timestamp.max,
                    )
                )
                historico[placa] = registros

        total_placas = len(historico)
        multi_filial = sum(
            1 for h in historico.values() if len(set(f for _, f in h)) > 1
        )

        print(f"✅ Histórico temporal criado: {total_placas} placas mapeadas")
        print(f"   � {multi_filial} placas com múltiplas filiais no histórico")

        return historico

    except Exception as e:
        print(f"❌ Erro ao criar mapa de filiais: {e}")
        import traceback

        traceback.print_exc()
        return {}


def carregar_movimentacoes_banco():
    """Retorna o DataFrame de movimentos e veículos ativos do Bluefleet."""
    import os

    import pyodbc

    host = os.getenv("DB_HOST")
    db = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")

    if not all([host, db, user, pwd]):
        raise EnvironmentError(
            "Variáveis de ambiente do BlueFleet incompletas. "
            "Configure DB_HOST, DB_NAME, DB_USER e DB_PASSWORD no arquivo .env"
        )

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={host},1433;"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={pwd};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30;"
    )

    conn = pyodbc.connect(conn_str)

    query_mov = """
    SELECT
        Data_da_movimentação,
        Placa,
        Unidade_de_Origem,
        Unidade_de_Destino
    FROM
        dbo.Movimentos
    WHERE
        Unidade_movimentada = 'OPERAÇÃO'
    ORDER BY
        Placa, Data_da_movimentação;
    """
    df_mov = pd.read_sql(query_mov, conn)

    query_vei = """
    SELECT
        Placa,
        FilialOperacional
    FROM
        dbo.Veiculos;
    """
    df_vei = pd.read_sql(query_vei, conn)

    conn.close()

    return df_mov, df_vei


def criar_mapa_movimentacoes_e_veiculos():
    """
    Lê os movimentos e veículos do banco de dados e cria um histórico de filiais para cada placa.
    """
    try:
        print(
            "🔍 Carregando dados de movimentação e cadastro de veículos do banco de dados..."
        )
        df_mov, df_vei = carregar_movimentacoes_banco()

        # Normalizar placas e filiais
        df_mov["Placa_Clean"] = (
            df_mov["Placa"]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )
        df_vei["Placa_Clean"] = (
            df_vei["Placa"]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )

        df_mov["Unidade_de_Origem"] = df_mov["Unidade_de_Origem"].apply(
            normalizar_filial
        )
        df_mov["Unidade_de_Destino"] = df_mov["Unidade_de_Destino"].apply(
            normalizar_filial
        )
        df_vei["FilialOperacional"] = df_vei["FilialOperacional"].apply(
            normalizar_filial
        )

        df_mov["Data_da_movimentação"] = pd.to_datetime(df_mov["Data_da_movimentação"])

        # Mapear veículos para filial operacional atual (como fallback)
        fallback_veiculos = df_vei.set_index("Placa_Clean")[
            "FilialOperacional"
        ].to_dict()

        # Agrupar movimentos por placa
        mapa_movs = {}
        for placa, group in df_mov.groupby("Placa_Clean"):
            # Ordenar por data
            group_sorted = group.sort_values("Data_da_movimentação")
            movs_lista = []
            for _, row in group_sorted.iterrows():
                data = row["Data_da_movimentação"]
                origem = row["Unidade_de_Origem"]
                destino = row["Unidade_de_Destino"]
                if pd.notna(destino):
                    movs_lista.append((data, origem, destino))
            if movs_lista:
                mapa_movs[placa] = movs_lista

        print(f"   ✅ Histórico de movimentações mapeado para {len(mapa_movs)} placas.")
        return mapa_movs, fallback_veiculos

    except Exception as e:
        print(f"⚠️ Erro ao criar mapa de movimentações: {e}")
        return {}, {}


def buscar_filial_por_movimentacao(placa, data_comb, mapa_movs, fallback_veiculos):
    """
    Busca a filial onde o veículo estava na data de combustível com base nas movimentações.
    """
    if placa not in mapa_movs:
        return fallback_veiculos.get(placa)

    hist = mapa_movs[placa]

    if pd.isna(data_comb):
        return hist[-1][2]

    melhor_destino = None
    for data_mov, origem, destino in hist:
        if data_mov <= data_comb:
            melhor_destino = destino
        else:
            break

    if melhor_destino is None:
        melhor_destino = hist[0][1]

    return melhor_destino


def aplicar_filial_manutencao(
    df,
    historico_filiais,
    mapa_datas_manutencao=None,
    coluna_placa="Placa",
    coluna_garagem="Garagem",
    coluna_data="Data da transacao",
    coluna_id="Id transacao",
):
    """
    Aplica a filial de manutenção ao DataFrame usando LÓGICA TEMPORAL e DE MOVIMENTAÇÕES.

    Para cada abastecimento:
    1. Verifica exceções por ID de transação (EXCECOES_TRANSACOES)
    2. Verifica exceções forçadas por placa (EXCECOES_FORCADAS)
    3. Busca no histórico de movimentações (planilha de movimentos) a filial de destino na data do abastecimento
    4. Caso não encontre movimentos, usa o histórico de manutenção
    5. Se não houver histórico, mantém garagem original
    """
    # Normalizar placas
    df["Placa_Clean"] = (
        df[coluna_placa]
        .astype(str)
        .str.replace("-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    # Converter data de combustível
    if coluna_data in df.columns:
        df["Data_Combustivel_Parsed"] = pd.to_datetime(
            df[coluna_data], dayfirst=True, format="mixed", errors="coerce"
        )

    stats = {
        "total": 0,
        "excecao_forcada": 0,
        "sem_historico": 0,
        "referencia_manteve_garagem": 0,
        "temporal_match": 0,
        "sem_data_fallback": 0,
    }

    # Carregar dados de movimentação e veículos ativos do banco de dados
    mapa_movs, fallback_veiculos = criar_mapa_movimentacoes_e_veiculos()

    def determinar_filial(row):
        stats["total"] += 1
        placa = row["Placa_Clean"]
        garagem_original = row[coluna_garagem]

        # PRIORIDADE 0: Exceções por ID de Transação (Robust Match)
        id_col_real = (
            coluna_id
            if coluna_id in row.index
            else next(
                (
                    c
                    for c in row.index
                    if str(c).lower()
                    in [
                        "transacao",
                        "transação",
                        "id transacao",
                        "id transação",
                        "id",
                        "identificador",
                        "número tr.",
                        "nº transação",
                    ]
                ),
                None,
            )
        )

        if id_col_real:
            val_raw = row[id_col_real]
            if pd.notna(val_raw):
                try:
                    id_trans = str(int(float(val_raw))).strip()
                except:
                    id_trans = str(val_raw).split(".")[0].strip()

        # TAI9A24 agora é tratada via EXCECOES_FORCADAS (→ GRITSCH - RIA)
        # A exceção hardcoded anterior para POA foi removida em Agosto/2026.

        # PRIORIDADE 1: Exceções forçadas por placa
        if placa in EXCECOES_FORCADAS:
            stats["excecao_forcada"] += 1
            return EXCECOES_FORCADAS[placa]

        # Regra temporal Sinop -> MATRIZ após 08/06/2026 para placas SFA6I75, SFA6I76, SFA6I77 e SFD9G67
        PLACAS_SINOP_MATRIZ = {"SFA6I75", "SFA6I76", "SFA6I77", "SFD9G67"}
        data_comb = row.get("Data_Combustivel_Parsed", pd.NaT)
        if placa in PLACAS_SINOP_MATRIZ and pd.notna(data_comb):
            stats["excecao_forcada"] += 1
            if data_comb > pd.Timestamp("2026-06-08"):
                return "GRITSCH - MATRIZ"
            else:
                return "GRITSCH - SNO"

        # Exceção temporal para SFD3E82 após 17/03
        if placa == "SFD3E82" and pd.notna(data_comb):
            if data_comb >= pd.Timestamp("2026-03-17"):
                stats["excecao_forcada"] += 1
                return "GRITSCH - MGA"

        # PRIORIDADE 2: Tabela de movimentos do BlueFleet (dbo.Movimentos)
        # Regra: o custo segue o veículo — usa a filial onde o veículo estava na data
        filial_movimento = buscar_filial_por_movimentacao(
            placa, data_comb, mapa_movs, fallback_veiculos
        )
        if filial_movimento and pd.notna(filial_movimento):
            filial_mov_norm = normalizar_filial(filial_movimento)
            if filial_mov_norm:
                filial_upper = str(filial_mov_norm).upper()
                if "REFER" in filial_upper:
                    # Unidade de outra empresa do grupo → manter garagem TruckPag
                    stats["referencia_manteve_garagem"] += 1
                    return garagem_original

                # Exceção específica RHA3E79: o que era Cascavel (CSC) vai para CWB (BASE), Londrina (LDB) mantém Londrina
                if placa == "RHA3E79" and ("CSC" in filial_upper or "CASCAVEL" in filial_upper):
                    if pd.notna(data_comb):
                        stats["temporal_match"] += 1
                    else:
                        stats["sem_data_fallback"] += 1
                    return "GRITSCH - CWB (BASE)"

                if pd.notna(data_comb):
                    stats["temporal_match"] += 1
                else:
                    stats["sem_data_fallback"] += 1
                return filial_mov_norm

        # Sem filial válida via movimentos → manter garagem original do TruckPag
        stats["sem_historico"] += 1
        garagem_norm = normalizar_filial(garagem_original)
        if placa == "RHA3E79" and garagem_norm and ("CSC" in str(garagem_norm).upper() or "CASCAVEL" in str(garagem_norm).upper()):
            return "GRITSCH - CWB (BASE)"
        return garagem_original

    # Aplicar
    df["Filial_Final"] = df.apply(determinar_filial, axis=1)

    # Normalizar
    df["Filial_Final"] = df["Filial_Final"].apply(normalizar_filial)
    df[coluna_garagem] = df[coluna_garagem].apply(normalizar_filial)

    # Estatísticas
    total_registros = len(df)
    realocados = df[df["Filial_Final"] != df[coluna_garagem]]
    placas_realocadas = (
        realocados["Placa_Clean"].nunique() if len(realocados) > 0 else 0
    )
    registros_realocados = len(realocados)

    print(f"📊 Realocação de filiais:")
    print(f"   - {placas_realocadas} placas únicas realocadas")
    print(
        f"   - {registros_realocados}/{total_registros} registros afetados ({registros_realocados / total_registros * 100:.1f}%)"
    )
    print(f"\n📅 Por movimentações (dbo.Movimentos):")
    print(f"   - {stats['excecao_forcada']} registros: exceção forçada (manual)")
    print(f"   - {stats['temporal_match']} registros: filial via movimentação")
    print(f"   - {stats['sem_data_fallback']} registros: sem data (usou FilialOperacional)")
    print(f"   - {stats['referencia_manteve_garagem']} registros: unidade REFERÊNCIA → manteve garagem TruckPag")
    print(f"   - {stats['sem_historico']} registros: sem movimentação → manteve garagem TruckPag")

    return df
