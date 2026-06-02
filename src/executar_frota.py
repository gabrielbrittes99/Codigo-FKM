"""
Gerador de Relatórios de Frota por Filial
Conecta ao Bluefleet, extrai veículos ativos e gera as planilhas por filial.
"""

import os
import sys

import pandas as pd
import pyodbc
from dotenv import load_dotenv
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src import config
from src.filial_mapping import normalizar_filial

load_dotenv()


def obter_conexao_bluefleet():
    """Retorna uma conexão pyodbc com o SQL Server BlueFleet."""
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

    return pyodbc.connect(conn_str)


def extrair_frota_bluefleet():
    print("🔄 Conectando ao Bluefleet para extrair dados da frota...")
    conn = obter_conexao_bluefleet()
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
    df = pd.read_sql(query, conn)
    conn.close()

    print(f"✅ Extração concluída. Total de veículos encontrados: {len(df)}")
    return df


def gerar_relatorio_frota(df_filial, filial, caminho_saida):
    """
    Gera o arquivo Excel com a frota da filial e aplica formatação.
    """
    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df_filial.to_excel(writer, sheet_name="Relação de Veículos", index=False)

    # Aplicar formatação
    wb = load_workbook(caminho_saida)
    ws = wb["Relação de Veículos"]

    cor_amarelo = PatternFill(
        start_color="FFFF00", end_color="FFFF00", fill_type="solid"
    )
    cor_cinza = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    fonte_negrito = Font(bold=True)
    alinhamento_centro = Alignment(horizontal="center", vertical="center")

    # Formatar cabeçalho
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(1, col)
        cell.fill = cor_amarelo
        cell.font = fonte_negrito
        cell.alignment = alinhamento_centro

    # Adicionar linha de totalização no final
    ultima_linha = ws.max_row + 1
    ws.cell(ultima_linha, 1).value = "Total de Veículos"
    ws.cell(ultima_linha, 1).fill = cor_cinza
    ws.cell(ultima_linha, 1).font = fonte_negrito

    ws.cell(ultima_linha, 2).value = len(df_filial)
    ws.cell(ultima_linha, 2).fill = cor_cinza
    ws.cell(ultima_linha, 2).font = fonte_negrito
    ws.cell(ultima_linha, 2).alignment = alinhamento_centro

    for col in range(3, ws.max_column + 1):
        ws.cell(ultima_linha, col).fill = cor_cinza

    # Ajustar larguras
    ws.column_dimensions["A"].width = 15  # Placa
    ws.column_dimensions["B"].width = 40  # Modelo
    ws.column_dimensions["C"].width = 30  # FilialOperacional
    ws.column_dimensions["D"].width = 25  # SituacaoVeiculo

    wb.save(caminho_saida)


def main():
    print("=" * 80)
    print(f"GERADOR DE RESUMOS DE FROTA - {config.MES}/{config.ANO}")
    print("=" * 80)

    try:
        df = extrair_frota_bluefleet()
    except Exception as e:
        print(f"\n❌ ERRO ao conectar no banco de dados: {e}")
        sys.exit(1)

    if df.empty:
        print("⚠️  Nenhum veículo encontrado com os critérios fornecidos.")
        sys.exit(0)

    # Normalizar nomes das filiais para ficar igual Manutenção e Combustível
    df["Filial_Normalizada"] = df["FilialOperacional"].apply(normalizar_filial)

    # Se normalizar_filial não mapear algumas, garantimos que fiquem parecidas com o padrão
    # Mas a normalização lida bem com 'GRITSCH - XXX'

    filiais_unicas = df["Filial_Normalizada"].dropna().unique()

    print(f"\n✅ {len(filiais_unicas)} filiais únicas encontradas")
    print("\n" + "=" * 80)
    print("GERANDO ARQUIVOS POR FILIAL")
    print("=" * 80)

    for idx, filial in enumerate(filiais_unicas, 1):
        # Filtramos pelas filiais normalizadas para o Excel
        df_filial = df[df["Filial_Normalizada"] == filial].copy()

        # Removemos a coluna auxiliar antes de salvar
        df_filial = df_filial.drop(columns=["Filial_Normalizada"])

        # Criar pasta da filial
        pasta_filial = config.obter_caminho_saida_filial(filial)
        os.makedirs(pasta_filial, exist_ok=True)

        nome_filial_limpo = "".join(
            c for c in str(filial) if c.isalnum() or c in (" ", "_")
        ).rstrip()
        nome_arquivo_saida = f"Frota - {nome_filial_limpo}.xlsx"
        caminho_completo_saida = os.path.join(pasta_filial, nome_arquivo_saida)

        print(f"\n[{idx}/{len(filiais_unicas)}] 🚙 {filial}")
        print(f"      Veículos: {len(df_filial)}")
        print(f"      Pasta: {filial}/")
        print(f"      Gerando: {nome_arquivo_saida}")

        if os.path.exists(caminho_completo_saida):
            try:
                os.remove(caminho_completo_saida)
                print(f"      🗑️  Arquivo antigo removido")
            except Exception as e:
                print(f"      ⚠️  Não foi possível remover: {e}")
                continue

        gerar_relatorio_frota(df_filial, filial, caminho_completo_saida)
        print(f"      ✅ Concluído!")

    print("\n" + "=" * 80)
    print("SALVANDO ARQUIVO GERAL")
    print("=" * 80)

    mes_num = config.obter_numero_mes()
    ano_short = config.ANO[-2:]
    nome_arquivo_geral = f"{mes_num}{ano_short} FROTA GRITSCH TRANSPORTES GERAL.xlsx"
    pasta_periodo = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO)
    os.makedirs(pasta_periodo, exist_ok=True)
    caminho_completo_geral = os.path.join(pasta_periodo, nome_arquivo_geral)

    print(f"\n🔄 Salvando arquivo geral...")
    df.drop(columns=["Filial_Normalizada"]).to_excel(
        caminho_completo_geral, index=False, engine="openpyxl"
    )
    print(f"✅ Arquivo geral salvo!")

    print("\n" + "=" * 80)
    print("🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
    print("=" * 80)
    print(f"\n📁 Arquivos salvos em: {pasta_periodo}")


if __name__ == "__main__":
    main()
