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
# Placas que devem SEMPRE ir para uma filial específica, independente da lógica temporal
EXCECOES_FORCADAS = {
    # Exceção para placas da filial GRITSCH - PET que ainda não existe no sistema
    "UBN9E24": "GRITSCH - PET",
    "UBN9E26": "GRITSCH - PET",
    "UBK4B56": "GRITSCH - PET",
    "UBR9B03": "GRITSCH - PET",
    "TAV9E95": "GRITSCH - PET",
    "UBN9E25": "GRITSCH - PET",
    "UBR9B07": "GRITSCH - PET",
    "SFG4I64": "GRITSCH - PET",
    "SFD4I64": "GRITSCH - PET",
    "UBR9B05": "GRITSCH - PET",
    # Placas coringas para veículos novos (sem placa/chassi)
    "TBI2068": "GRITSCH - MATRIZ",
    "TBI2067": "GRITSCH - MATRIZ",
    "TAX5J72": "GRITSCH - LDB",
    "SFL-1E4": "GRITSCH - PMW",
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
EXCECOES_TRANSACOES = {}


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
    Aplica a filial de manutenção ao DataFrame usando LÓGICA TEMPORAL.

    Para cada abastecimento:
    1. Verifica exceções forçadas (EXCECOES_FORCADAS)
    2. Busca no histórico temporal a manutenção mais recente ANTES do abastecimento
    3. Usa a filial desse registro de manutenção
    4. Se a filial for REFERÊNCIA → ignora (exceto TBU9D20)
    5. Se não houver manutenção antes → mantém garagem original

    Args:
        df: DataFrame de combustível
        historico_filiais: Dict {placa: [(data, filial), ...]} de criar_mapa_filiais
        mapa_datas_manutencao: IGNORADO (mantido por compatibilidade)
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

    PLACA_EXCECAO = "TBU9D20"

    stats = {
        "total": 0,
        "excecao_forcada": 0,
        "sem_historico": 0,
        "referencia_ignorada": 0,
        "referencia_excecao": 0,
        "temporal_match": 0,
        "sem_data_fallback": 0,
    }

    def buscar_filial_temporal(historico_placa, data_combustivel):
        """Busca a filial da manutenção mais recente ANTES/NA data do abastecimento."""
        if not historico_placa:
            return None

        # Sem data de combustível → usar a filial mais recente disponível
        if pd.isna(data_combustivel):
            for data, filial in reversed(historico_placa):
                if pd.notna(data):
                    return filial
            return historico_placa[-1][1]

        # Buscar a entrada mais recente com data <= data_combustivel
        melhor_filial = None
        for data, filial in historico_placa:
            if pd.notna(data) and data <= data_combustivel:
                melhor_filial = filial
            elif pd.notna(data) and data > data_combustivel:
                break

        # Se não achou antes da data, usar a primeira entrada disponível
        if melhor_filial is None:
            for data, filial in historico_placa:
                if pd.isna(data):
                    return filial
            melhor_filial = historico_placa[0][1]

        return melhor_filial

    def determinar_filial(row):
        stats["total"] += 1
        placa = row["Placa_Clean"]
        garagem_original = row[coluna_garagem]

        # PRIORIDADE 0: Exceções por ID de Transação (Robust Match)
        # Tenta encontrar a coluna de ID dinamicamente
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
                # Converte float/num para string inteira (ex: 123.0 -> "123")
                try:
                    id_trans = str(int(float(val_raw))).strip()
                except:
                    id_trans = str(val_raw).split(".")[0].strip()

                if id_trans in EXCECOES_TRANSACOES:
                    stats["excecao_forcada"] += 1
                    return EXCECOES_TRANSACOES[id_trans]

        # PRIORIDADE 1: Exceções forçadas por placa
        if placa in EXCECOES_FORCADAS:
            stats["excecao_forcada"] += 1
            return EXCECOES_FORCADAS[placa]

        # NOVA LÓGICA: Exceção temporal para SFD3E82 após 17/03
        data_comb = row.get("Data_Combustivel_Parsed", pd.NaT)
        if placa == "SFD3E82" and pd.notna(data_comb):
            if data_comb >= pd.Timestamp("2026-03-17"):
                stats["excecao_forcada"] += 1
                return "GRITSCH - MGA"

        # Verificar histórico de manutenção
        if placa not in historico_filiais:
            stats["sem_historico"] += 1
            return garagem_original

        # Buscar filial temporal
        data_comb = row.get("Data_Combustivel_Parsed", pd.NaT)
        filial_encontrada = buscar_filial_temporal(historico_filiais[placa], data_comb)

        if filial_encontrada is None:
            stats["sem_historico"] += 1
            return garagem_original

        # Verificar se é REFERÊNCIA
        filial_upper = str(filial_encontrada).upper()
        if filial_upper.startswith("REFERÊNCIA") or filial_upper.startswith(
            "REFERENCIA"
        ):
            if placa == PLACA_EXCECAO and "CURITIBA" in filial_upper:
                stats["referencia_excecao"] += 1
                return filial_encontrada
            stats["referencia_ignorada"] += 1
            return garagem_original

        # Filial válida via lógica temporal
        if pd.notna(data_comb):
            stats["temporal_match"] += 1
        else:
            stats["sem_data_fallback"] += 1

        return filial_encontrada

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
    print(f"\n📅 Lógica temporal aplicada:")
    print(f"   - {stats['excecao_forcada']} registros: exceção forçada")
    print(f"   - {stats['temporal_match']} registros: manutenção temporal usada")
    print(f"   - {stats['sem_data_fallback']} registros: sem data (usou filial geral)")
    print(f"\n⚙️  Outras decisões:")
    print(f"   - {stats['sem_historico']} registros: sem histórico (manteve garagem)")
    print(
        f"   - {stats['referencia_ignorada']} registros: REFERÊNCIA ignorada (manteve garagem)"
    )
    if stats["referencia_excecao"] > 0:
        print(
            f"   - {stats['referencia_excecao']} registros: exceção TBU9D20 → REFERÊNCIA CURITIBA"
        )

    return df
