"""
Script para extrair dados de Manutenção e Frota diretamente do Bluefleet
e salvar como planilhas Excel na raiz do projeto, para alimentar os
relatórios de KPI e resumos mensais.
"""

import os
import re
import sys

import pandas as pd
import pyodbc
from dotenv import load_dotenv

from src import config
from src.executar_frota import obter_conexao_bluefleet

load_dotenv()

MESES_PT = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Marco": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}

SQL_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sql",
    "Criacao - Relatorio Fechamento.sql",
)


def carregar_sql(mes_num: int, ano: int) -> str:
    """
    Carrega o SQL do arquivo .sql, remove a linha USE referencia;
    e substitui o filtro de DataCriacao pelo período informado.
    """
    if not os.path.exists(SQL_FILE_PATH):
        raise FileNotFoundError(f"Arquivo SQL não encontrado: {SQL_FILE_PATH}")

    with open(SQL_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    sql = re.sub(r"^\s*USE\s+\w+\s*;?\s*$", "", sql, flags=re.MULTILINE | re.IGNORECASE)

    if mes_num == 12:
        ano_prox = ano + 1
        mes_prox = 1
    else:
        ano_prox = ano
        mes_prox = mes_num + 1

    data_inicio = f"{ano}-{mes_num:02d}-01"
    data_fim = f"{ano_prox}-{mes_prox:02d}-01"

    sql = re.sub(
        r"DECLARE\s+@DataIni\s+DATETIME\s*=\s*DATEADD\s*\(.*?\)\s*;",
        f"DECLARE @DataIni DATETIME = '{data_inicio}';",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"DECLARE\s+@DataFim\s+DATETIME\s*=\s*DATEADD\s*\(.*?\)\s*;",
        f"DECLARE @DataFim DATETIME = '{data_fim}';",
        sql,
        flags=re.IGNORECASE,
    )

    return sql


def extrair_manutencao(mes_nome, ano):
    print(f"\n🔄 Iniciando extração de MANUTENÇÃO ({mes_nome}/{ano})...")

    mes_num = MESES_PT.get(mes_nome)
    if not mes_num:
        raise ValueError(f"Mês inválido: {mes_nome}")

    try:
        sql = carregar_sql(mes_num, ano)
    except Exception as e:
        print(f"❌ Erro ao carregar SQL de manutenção: {e}")
        return None

    try:
        conn = obter_conexao_bluefleet()
        print("   Conectado ao Bluefleet.")

        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)

            cursor = conn.cursor()
            cursor.execute(sql)

            while cursor.description is None:
                if not cursor.nextset():
                    break

            if cursor.description:
                colunas = [desc[0] for desc in cursor.description]
                linhas = cursor.fetchall()
                df = pd.DataFrame.from_records(linhas, columns=colunas)
            else:
                df = pd.DataFrame()

        conn.close()

        print(f"✅ Extração de Manutenção concluída. {len(df)} registros encontrados.")
        return df
    except Exception as e:
        print(f"❌ Erro ao extrair Manutenção do banco: {e}")
        return None
        return None


def extrair_frota():
    print(f"\n🔄 Iniciando extração de FROTA ATIVA...")

    query = """
    SELECT
        Placa,
        Modelo,
        CASE
            WHEN Placa IN ('UBN-9E24','UBN-9E26','UBK-4B56','UBR-9B03','TAV-9E95','UBN-9E25','UBR-9B07','SFD-4I64','UBR-9B05') THEN 'GRITSCH - PET'
            ELSE FilialOperacional
        END AS FilialOperacional,
        SituacaoVeiculo
    FROM
        dbo.Veiculos
    WHERE
        SituacaoVeiculo <> 'Vendido'
        AND (FilialOperacional LIKE '%GRIT%' OR Placa IN ('UBN-9E24','UBN-9E26','UBK-4B56','UBR-9B03','TAV-9E95','UBN-9E25','UBR-9B07','SFD-4I64','UBR-9B05'))
    ORDER BY
        FilialOperacional,
        Placa;
    """
    try:
        conn = obter_conexao_bluefleet()
        print("   Conectado ao Bluefleet.")

        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            df = pd.read_sql(query, conn)

        conn.close()

        print(f"✅ Extração de Frota concluída. {len(df)} veículos encontrados.")
        return df
    except Exception as e:
        print(f"❌ Erro ao extrair Frota do banco: {e}")
        return None


def main():
    print("=" * 80)
    print(f"EXTRAÇÃO DE DADOS BLUEFLEET - {config.MES}/{config.ANO}")
    print("=" * 80)

    # Identificar nomenclaturas para os arquivos
    mes_num_str = config.obter_numero_mes()
    ano_short = config.ANO[-2:]
    sufixo_arquivo = f"{mes_num_str}{ano_short}.xlsx"

    arquivo_manutencao = os.path.join(
        config.DIRETORIO_ENTRADA, f"Manutencao {sufixo_arquivo}"
    )
    arquivo_frota = os.path.join(config.DIRETORIO_ENTRADA, f"Frota {sufixo_arquivo}")

    # 1. Extrair Manutenção
    df_manutencao = extrair_manutencao(config.MES, int(config.ANO))
    if df_manutencao is not None and not df_manutencao.empty:
        print(f"📝 Salvando {os.path.basename(arquivo_manutencao)}...")
        df_manutencao.to_excel(arquivo_manutencao, index=False, engine="openpyxl")
        print("   Salvo com sucesso!")

    # 2. Extrair Frota
    df_frota = extrair_frota()
    if df_frota is not None and not df_frota.empty:
        print(f"📝 Salvando {os.path.basename(arquivo_frota)}...")
        df_frota.to_excel(arquivo_frota, index=False, engine="openpyxl")
        print("   Salvo com sucesso!")

    print("\n" + "=" * 80)
    print("🎉 PROCESSO DE EXTRAÇÃO FINALIZADO!")
    print("=" * 80)


if __name__ == "__main__":
    main()
