"""
Módulo de Mapeamento de Filiais - FKM
Mapeia placas para suas respectivas filiais de manutenção
"""

import numpy as np
import pandas as pd

# Exceções forçadas para filiais específicas (centralizado)
# DESABILITADO: Não usar exceções forçadas - seguir apenas mapeamento de manutenção
EXCECOES_FORCADAS = {}


def criar_mapa_filiais(caminho_manutencao):
    """
    Lê a planilha de manutenção e cria um dicionário {placa: filial}
    Usa a filial mais frequente (mode) para cada placa

    Args:
        caminho_manutencao: Caminho para o arquivo Excel de manutenção

    Returns:
        dict: Dicionário com {placa_normalizada: filial_manutencao}
    """
    try:
        print("🔍 Carregando dados de manutenção para mapeamento de filiais...")
        df_manut = pd.read_excel(caminho_manutencao)

        if "Placa" not in df_manut.columns or "FILIAL" not in df_manut.columns:
            print(
                "⚠️ Colunas 'Placa' ou 'FILIAL' não encontradas na planilha de manutenção"
            )
            return {}

        # Normalizar placas (remover hífens, espaços, uppercase)
        df_manut["Placa_Clean"] = (
            df_manut["Placa"]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )

        # Remover placas vazias ou inválidas
        df_manut = df_manut[df_manut["Placa_Clean"].str.len() > 0]
        df_manut = df_manut[df_manut["Placa_Clean"] != "NAN"]

        # Para cada placa, pegar a filial mais frequente (mode)
        mapa = {}
        for placa in df_manut["Placa_Clean"].unique():
            df_placa = df_manut[df_manut["Placa_Clean"] == placa]
            filial_mode = df_placa["FILIAL"].mode()

            if len(filial_mode) > 0:
                mapa[placa] = filial_mode.iloc[0]

        print(
            f"✅ Mapeamento criado: {len(mapa)} placas mapeadas para filiais de manutenção"
        )
        return mapa

    except Exception as e:
        print(f"❌ Erro ao criar mapa de filiais: {e}")
        return {}


def aplicar_filial_manutencao(
    df, mapa_filiais, coluna_placa="Placa", coluna_garagem="Garagem"
):
    """
    Aplica a filial de manutenção ao DataFrame, priorizando sobre a garagem

    REGRAS:
    - Filiais "REFERÊNCIA..." são IGNORADAS (empresa não usa Truckpag)
    - EXCEÇÃO: Placa TBU9D20 vai para REFERÊNCIA CURITIBA (veículo compartilhado)
    - Demais filiais (GRITSCH, RATEIO, etc.) são aplicadas normalmente

    Args:
        df: DataFrame de combustível
        mapa_filiais: Dicionário {placa: filial_manutencao}
        coluna_placa: Nome da coluna com a placa
        coluna_garagem: Nome da coluna com a garagem original

    Returns:
        DataFrame: DataFrame com nova coluna 'Filial_Final'
    """
    # Normalizar placas no DataFrame
    df["Placa_Clean"] = (
        df[coluna_placa]
        .astype(str)
        .str.replace("-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    # Placa de exceção que pode ir para REFERÊNCIA
    PLACA_EXCECAO = "TBU9D20"

    def determinar_filial(row):
        placa = row["Placa_Clean"]
        garagem_original = row[coluna_garagem]

        # Verificar se a placa tem mapeamento de manutenção
        if placa not in mapa_filiais:
            return garagem_original

        filial_manutencao = mapa_filiais[placa]

        # Verificar se é filial REFERÊNCIA
        if str(filial_manutencao).upper().startswith("REFERÊNCIA") or str(
            filial_manutencao
        ).upper().startswith("REFERENCIA"):
            # Exceção: placa TBU9D20 pode ir para REFERÊNCIA CURITIBA
            if placa == PLACA_EXCECAO and "CURITIBA" in str(filial_manutencao).upper():
                return filial_manutencao
            # Demais placas com filial REFERÊNCIA: manter garagem original
            return garagem_original

        # Filiais GRITSCH, RATEIO, etc.: usar filial de manutenção
        return filial_manutencao

    # Criar coluna Filial_Final
    df["Filial_Final"] = df.apply(determinar_filial, axis=1)

    # Contar realocações
    total_registros = len(df)
    realocados = df[df["Filial_Final"] != df[coluna_garagem]]
    placas_realocadas = (
        realocados["Placa_Clean"].nunique() if len(realocados) > 0 else 0
    )
    registros_realocados = len(realocados)

    # Contar quantas foram ignoradas por serem REFERÊNCIA
    placas_referencia_ignoradas = 0
    for placa, filial in mapa_filiais.items():
        if str(filial).upper().startswith("REFERÊNCIA") or str(
            filial
        ).upper().startswith("REFERENCIA"):
            if not (placa == PLACA_EXCECAO and "CURITIBA" in str(filial).upper()):
                placas_referencia_ignoradas += 1

    print(f"📊 Realocação de filiais:")
    print(
        f"   - {placas_realocadas} placas únicas realocadas para filial de manutenção"
    )
    print(
        f"   - {registros_realocados}/{total_registros} registros afetados ({registros_realocados / total_registros * 100:.1f}%)"
    )
    print(
        f"   - {placas_referencia_ignoradas} placas REFERÊNCIA ignoradas (empresa não usa Truckpag)"
    )
    if PLACA_EXCECAO in mapa_filiais:
        print(
            f"   - ⚠️  Exceção: {PLACA_EXCECAO} → REFERÊNCIA CURITIBA (veículo compartilhado)"
        )

    return df
