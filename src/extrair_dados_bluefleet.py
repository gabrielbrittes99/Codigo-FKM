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
import psycopg2
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


def obter_conexao_dw():
    """Retorna uma conexão psycopg2 com o PostgreSQL DW."""
    host = os.getenv("DW_HOST")
    port = os.getenv("DW_PORT", "5432")
    db = os.getenv("DW_NAME")
    user = os.getenv("DW_USER")
    pwd = os.getenv("DW_PASSWORD")

    if not all([host, db, user, pwd]):
        raise EnvironmentError(
            "Variáveis de ambiente do DW incompletas. "
            "Configure DW_HOST, DW_NAME, DW_USER e DW_PASSWORD no arquivo .env"
        )

    return psycopg2.connect(
        host=host,
        port=port,
        database=db,
        user=user,
        password=pwd
    )


def extrair_manutencao(mes_nome, ano):
    print(f"\n🔄 Iniciando extração de MANUTENÇÃO ({mes_nome}/{ano})...")

    mes_num = MESES_PT.get(mes_nome)
    if not mes_num:
        raise ValueError(f"Mês inválido: {mes_nome}")

    if mes_num == 12:
        ano_prox = ano + 1
        mes_prox = 1
    else:
        ano_prox = ano
        mes_prox = mes_num + 1

    data_inicio = f"{ano}-{mes_num:02d}-01"
    data_fim = f"{ano_prox}-{mes_prox:02d}-01"

    query = f"""
    SELECT * 
    FROM [referencia].[dbo].[vw_RelatorioFKM_Historico]
    WHERE DataCriacao >= '{data_inicio}' AND DataCriacao < '{data_fim}'
    ORDER BY DataCriacao DESC;
    """

    try:
        conn = obter_conexao_bluefleet()
        print("   Conectado ao Bluefleet.")

        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)

            cursor = conn.cursor()
            cursor.execute(query)

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
            WHEN Placa IN ('UBN-9E24','UBN-9E26','UBK-4B56','UBR-9B03','TAV-9E95','UBN-9E25','UBR-9B07','SFD-4I64','SFG-4I64','UBR-9B05') THEN 'GRITSCH - PET'
            ELSE FilialOperacional
        END AS FilialOperacional,
        SituacaoVeiculo
    FROM
        dbo.Veiculos
    WHERE
        SituacaoVeiculo <> 'Vendido'
        AND (FilialOperacional LIKE '%GRIT%' OR Placa IN ('UBN-9E24','UBN-9E26','UBK-4B56','UBR-9B03','TAV-9E95','UBN-9E25','UBR-9B07','SFD-4I64','SFG-4I64','UBR-9B05'))
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


def extrair_combustivel(mes_nome, ano):
    print(f"\n🔄 Iniciando extração de COMBUSTÍVEL ({mes_nome}/{ano})...")

    mes_num = MESES_PT.get(mes_nome)
    if not mes_num:
        raise ValueError(f"Mês inválido: {mes_nome}")

    if mes_num == 12:
        ano_prox = ano + 1
        mes_prox = 1
    else:
        ano_prox = ano
        mes_prox = mes_num + 1

    data_inicio = f"{ano}-{mes_num:02d}-01"
    data_fim = f"{ano_prox}-{mes_prox:02d}-01"

    query = f"""
    SELECT * 
    FROM torre.vw_RelatorioFKM_Combustivel
    WHERE "Data da transacao" >= '{data_inicio}' AND "Data da transacao" < '{data_fim}'
      AND "Status" = 'APROVADA'
      AND "Servico" = 'ABASTECIMENTO'
    ORDER BY "Data da transacao" DESC, "Transacao" DESC;
    """

    try:
        conn = obter_conexao_dw()
        print("   Conectado ao DW (PostgreSQL).")

        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            df = pd.read_sql(query, conn)

        conn.close()

        print(f"✅ Extração de Combustível concluída. {len(df)} registros encontrados.")
        return df
    except Exception as e:
        print(f"❌ Erro ao extrair Combustível do banco: {e}")
        return None


def main():
    print("=" * 80)
    print(f"EXTRAÇÃO DE DADOS BANCO DE DADOS - {config.MES}/{config.ANO}")
    print("=" * 80)

    # Identificar nomenclaturas para os arquivos
    mes_num_str = config.obter_numero_mes()
    ano_short = config.ANO[-2:]
    sufixo_arquivo = f"{mes_num_str}{ano_short}.xlsx"

    arquivo_manutencao = os.path.join(
        config.DIRETORIO_ENTRADA, f"Manutencao {sufixo_arquivo}"
    )
    arquivo_frota = os.path.join(config.DIRETORIO_ENTRADA, f"Frota {sufixo_arquivo}")
    arquivo_combustivel = os.path.join(config.DIRETORIO_ENTRADA, f"Combustivel {sufixo_arquivo}")

    # Criar diretório de entrada caso não exista
    os.makedirs(config.DIRETORIO_ENTRADA, exist_ok=True)

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

    # 3. Extrair Combustível
    df_combustivel = extrair_combustivel(config.MES, int(config.ANO))
    if df_combustivel is not None and not df_combustivel.empty:
        print(f"📝 Salvando {os.path.basename(arquivo_combustivel)}...")
        # Remover colunas auxiliares que não fazem parte do relatório final antes de salvar
        if "Status" in df_combustivel.columns:
            df_combustivel = df_combustivel.drop(columns=["Status"])
        if "Servico" in df_combustivel.columns:
            df_combustivel = df_combustivel.drop(columns=["Servico"])
        df_combustivel.to_excel(arquivo_combustivel, index=False, engine="openpyxl")
        print("   Salvo com sucesso!")

    print("\n" + "=" * 80)
    print("🎉 PROCESSO DE EXTRAÇÃO FINALIZADO!")
    print("=" * 80)


if __name__ == "__main__":
    main()
