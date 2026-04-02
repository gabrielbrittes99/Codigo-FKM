"""
Módulo de Mapeamento de Frota - FKM
Carrega e mapeia dados da frota para enriquecimento de análises
"""

import pandas as pd


def carregar_frota(caminho_frota):
    """
    Carrega o arquivo de frota e retorna um DataFrame normalizado

    Realiza:
    - Normalização de placas (remove hífens, espaços, uppercase)
    - Normalização do campo Grupo (uppercase para resolver variações de case)
    - Remove duplicatas de placas

    Args:
        caminho_frota: Caminho para o arquivo Excel de frota

    Returns:
        DataFrame com colunas: Placa_Clean, Grupo, Modelo Simplificado
        Retorna DataFrame vazio se arquivo não existir ou houver erro
    """
    try:
        if not caminho_frota:
            print("⚠️  Nenhum arquivo de frota fornecido")
            return pd.DataFrame(columns=["Placa_Clean", "Grupo", "Modelo Simplificado"])

        print(f"🔍 Carregando dados de frota: {caminho_frota}")
        df_frota = pd.read_excel(caminho_frota)

        # Validar colunas esperadas
        colunas_esperadas = ["Placa", "Grupo", "Modelo Simplificado"]
        colunas_faltantes = [col for col in colunas_esperadas if col not in df_frota.columns]

        if colunas_faltantes:
            print(f"⚠️  Colunas faltantes no arquivo de frota: {colunas_faltantes}")
            print(f"   Colunas disponíveis: {df_frota.columns.tolist()}")
            return pd.DataFrame(columns=["Placa_Clean", "Grupo", "Modelo Simplificado"])

        # Normalizar placas (mesmo padrão do filial_mapping)
        df_frota["Placa_Clean"] = (
            df_frota["Placa"]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )

        # Normalizar Grupo para uppercase (resolve LEVE/Leve/leve e MEDIO/Medio)
        df_frota["Grupo"] = (
            df_frota["Grupo"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Remover placas vazias ou inválidas
        df_frota = df_frota[df_frota["Placa_Clean"].str.len() > 0]
        df_frota = df_frota[df_frota["Placa_Clean"] != "NAN"]

        # Manter apenas colunas relevantes
        df_frota = df_frota[["Placa_Clean", "Grupo", "Modelo Simplificado"]].copy()

        # Remover duplicatas (manter primeira ocorrência)
        placas_antes = len(df_frota)
        df_frota = df_frota.drop_duplicates(subset=["Placa_Clean"], keep="first")
        placas_depois = len(df_frota)

        if placas_antes > placas_depois:
            print(f"   ℹ️  Removidas {placas_antes - placas_depois} placas duplicadas")

        print(f"✅ Frota carregada: {len(df_frota)} veículos")
        print(f"   📊 Grupos únicos: {df_frota['Grupo'].nunique()}")
        print(f"   📊 Modelos únicos: {df_frota['Modelo Simplificado'].nunique()}")

        return df_frota

    except FileNotFoundError:
        print(f"⚠️  Arquivo de frota não encontrado: {caminho_frota}")
        return pd.DataFrame(columns=["Placa_Clean", "Grupo", "Modelo Simplificado"])
    except Exception as e:
        print(f"❌ Erro ao carregar frota: {e}")
        return pd.DataFrame(columns=["Placa_Clean", "Grupo", "Modelo Simplificado"])


def enriquecer_com_frota(df, df_frota, coluna_placa="Placa_Clean"):
    """
    Enriquece um DataFrame com dados da frota (Grupo e Modelo Simplificado)

    Realiza left-merge por Placa_Clean e preenche valores ausentes com:
    - "SEM GRUPO" para veículos sem registro na frota
    - "SEM MODELO" para veículos sem registro na frota

    Args:
        df: DataFrame a ser enriquecido
        df_frota: DataFrame da frota (retornado por carregar_frota)
        coluna_placa: Nome da coluna de placa no DataFrame (deve estar normalizada)

    Returns:
        DataFrame enriquecido com colunas Grupo e Modelo Simplificado
    """
    # Se df_frota está vazio, adicionar colunas com valores padrão
    if len(df_frota) == 0:
        print("⚠️  DataFrame de frota vazio - usando valores padrão")
        df["Grupo"] = "SEM GRUPO"
        df["Modelo Simplificado"] = "SEM MODELO"
        return df

    # Validar que a coluna de placa existe
    if coluna_placa not in df.columns:
        print(f"⚠️  Coluna '{coluna_placa}' não encontrada no DataFrame")
        df["Grupo"] = "SEM GRUPO"
        df["Modelo Simplificado"] = "SEM MODELO"
        return df

    # Realizar left merge
    df_enriquecido = pd.merge(
        df,
        df_frota[["Placa_Clean", "Grupo", "Modelo Simplificado"]],
        left_on=coluna_placa,
        right_on="Placa_Clean",
        how="left",
        suffixes=("", "_frota")
    )

    # Remover coluna duplicada se houver
    if "Placa_Clean_frota" in df_enriquecido.columns:
        df_enriquecido = df_enriquecido.drop(columns=["Placa_Clean_frota"])

    # Preencher valores ausentes
    df_enriquecido["Grupo"] = df_enriquecido["Grupo"].fillna("SEM GRUPO")
    df_enriquecido["Modelo Simplificado"] = df_enriquecido["Modelo Simplificado"].fillna("SEM MODELO")

    # Estatísticas
    total_registros = len(df_enriquecido)
    sem_grupo = (df_enriquecido["Grupo"] == "SEM GRUPO").sum()

    if sem_grupo > 0:
        placas_sem_grupo = df_enriquecido[df_enriquecido["Grupo"] == "SEM GRUPO"][coluna_placa].nunique()
        print(f"   ℹ️  {sem_grupo} registros ({placas_sem_grupo} placas únicas) sem grupo na frota")

    return df_enriquecido
