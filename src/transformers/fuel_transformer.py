"""
Módulo de Transformação de Dados de Combustível
Responsável por limpar, formatar e aplicar regras de negócio em dados extraídos.
"""

import logging

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame

from src.transformers.schemas import FuelCleanSchema

logger = logging.getLogger(__name__)


def limpar_e_converter_numero(valor) -> float:
    """Converte valores monetários/litragem em float seguro."""
    if pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    valor_str = str(valor).strip()
    valor_str = valor_str.replace("R$", "").replace(" ", "")

    if "." in valor_str and "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    elif "," in valor_str:
        valor_str = valor_str.replace(",", ".")

    try:
        return float(valor_str)
    except Exception as e:
        logger.debug(f"Falha ao converter número '{valor}': {e}")
        return 0.0


def limpar_e_converter_hodometro(valor) -> float:
    """
    Converte hodômetros - multiplica por 1000 se for decimal (corrige leitura do Excel)
    Exemplo: 120.655 vira 120655
    NÃO multiplica valores que já são inteiros (ex: 576.0 → 576)
    """
    if pd.isna(valor):
        return np.nan

    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and valor < 1000000 and valor != int(valor):
            return float(valor * 1000)
        return float(valor)

    valor_str = str(valor).strip()
    valor_str = valor_str.replace("R$", "").replace(" ", "")

    # Remove pontos e vírgulas
    valor_str = valor_str.replace(".", "").replace(",", "")

    try:
        return float(valor_str)
    except Exception as e:
        logger.debug(f"Falha ao converter hodômetro '{valor}': {e}")
        return np.nan


@pa.check_types
def transformar_dados_combustivel(df: pd.DataFrame) -> DataFrame[FuelCleanSchema]:
    """
    Aplica as rotinas de limpeza numérica nas colunas de combustível e hodômetro.
    Valida o schema via Pandera após a limpeza.

    Args:
        df (pd.DataFrame): DataFrame bruto.

    Returns:
        DataFrame[FuelCleanSchema]: DataFrame validado e com tipos corretos.
    """
    logger.info("Iniciando transformação e limpeza de dados numéricos...")
    df_clean = df.copy()

    colunas_monetarias = ["Litragem", "Valor total", "Preco"]
    for col in colunas_monetarias:
        if col in df_clean.columns:
            logger.info(f"Limpando coluna: {col}")
            df_clean[col] = df_clean[col].apply(limpar_e_converter_numero)

    colunas_hodometro = ["Hodometro/Horimetro", "Hodometro/Horimetro anterior"]
    for col in colunas_hodometro:
        if col in df_clean.columns:
            logger.info(f"Limpando hodômetro: {col}")
            df_clean[col] = df_clean[col].apply(limpar_e_converter_hodometro)

    # Padronizar Placas
    if "Placa" in df_clean.columns:
        logger.info("Normalizando coluna Placa")
        df_clean["Placa_Clean"] = (
            df_clean["Placa"].astype(str).str.replace("-", "").str.strip().str.upper()
        )

    logger.info("Transformação concluída. Validando contrato de dados com Pandera...")
    return df_clean
