"""
Módulo de Extração de Dados
Responsável apenas por ler dados de fontes externas (arquivos, banco de dados, APIs).
"""

import logging
import os

import pandas as pd

# Configuração básica de logging (melhoraremos isso depois)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extrair_excel(caminho_arquivo: str, nome_aba: str = 0) -> pd.DataFrame:
    """
    Lê um arquivo Excel e retorna um DataFrame.

    Args:
        caminho_arquivo (str): Caminho completo para o arquivo Excel.
        nome_aba (str | int): Nome ou índice da aba a ser lida.

    Returns:
        pd.DataFrame: Dados extraídos do arquivo.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o arquivo estiver vazio ou corrompido.
    """
    if not os.path.exists(caminho_arquivo):
        logger.error(f"Arquivo não encontrado: {caminho_arquivo}")
        raise FileNotFoundError(f"O arquivo {caminho_arquivo} não foi encontrado.")

    logger.info(f"Extraindo dados do arquivo: {os.path.basename(caminho_arquivo)}")

    try:
        df = pd.read_excel(caminho_arquivo, sheet_name=nome_aba)
        if df.empty:
            logger.warning(f"O arquivo {os.path.basename(caminho_arquivo)} está vazio.")
        else:
            logger.info(f"Extração concluída: {len(df)} registros encontrados.")
        return df
    except Exception as e:
        logger.error(f"Falha ao ler o arquivo {caminho_arquivo}: {e}")
        raise ValueError(f"Erro ao processar o arquivo Excel: {e}")
