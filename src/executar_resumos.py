"""
Script FINAL CORRIGIDO - Gerador de Resumos de Combustível
Versão com separação por tipo de combustível e hodômetros corretos
Com priorização de filial de manutenção sobre garagem
"""

import os

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Importar módulo de mapeamento de filiais
from src.filial_mapping import aplicar_filial_manutencao, criar_mapa_filiais, normalizar_filial


def limpar_e_converter_numero(valor):
    """
    Converte valores com vírgula decimal para float
    """
    if pd.isna(valor):
        return np.nan

    if isinstance(valor, (int, float)):
        return float(valor)

    valor_str = str(valor).strip()
    valor_str = valor_str.replace("R$", "").replace(" ", "")

    if "." in valor_str and "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    elif "," in valor_str:
        valor_str = valor_str.replace(",", ".")
    elif "." in valor_str:
        # Remove ponto (separador de milhar) para manter apenas dígitos
        valor_str = valor_str.replace(".", "")

    try:
        return float(valor_str)
    except:
        return np.nan


def limpar_e_converter_hodometro(valor):
    """
    Converte hodômetros - multiplica por 1000 se for decimal (corrige leitura do Excel)
    Exemplo: 120.655 vira 120655
    """
    if pd.isna(valor):
        return np.nan

    if isinstance(valor, (int, float)):
        # Se for float menor que 1000000, provavelmente foi lido errado (120.655 ao invés de 120655)
        if isinstance(valor, float) and valor < 1000000:
            return int(valor * 1000)
        return int(valor)

    valor_str = str(valor).strip()
    valor_str = valor_str.replace("R$", "").replace(" ", "")

    # Remove pontos e vírgulas
    valor_str = valor_str.replace(".", "").replace(",", "")

    try:
        return int(valor_str)
    except:
        return np.nan


def tratar_dados(df):
    """
    Trata os dados do DataFrame convertendo colunas numéricas corretamente
    """
    print("🔧 Tratando dados...")

    # Colunas de valores monetários e litragem
    colunas_numericas = ["Litragem", "Valor total", "Preco"]

    for col in colunas_numericas:
        if col in df.columns:
            print(f"   Convertendo: {col}")
            df[col] = df[col].apply(limpar_e_converter_numero)

    # Hodômetros precisam de tratamento especial
    colunas_hodometro = ["Hodometro/Horimetro", "Hodometro/Horimetro anterior"]

    for col in colunas_hodometro:
        if col in df.columns:
            print(f"   Convertendo hodômetro: {col}")
            df[col] = df[col].apply(limpar_e_converter_hodometro)

    print("✅ Dados tratados com sucesso!")
    return df


def substituir_freguesia_por_perus(df, coluna="Garagem"):
    """
    Substitui SAO (FREGUESIA) por SAO (PERUS) na coluna especificada
    """
    if coluna in df.columns:
        df[coluna] = df[coluna].str.replace(
            "SAO (FREGUESIA)", "SAO (PERUS)", regex=False
        )
        df[coluna] = df[coluna].str.replace("SAO FREGUESIA", "SAO PERUS", regex=False)
        print("🔄 SAO (FREGUESIA) substituído por SAO (PERUS)")
    return df


def corrigir_filial_por_posto(
    df, coluna_filial="Filial_Final", coluna_estabelecimento="Estabelecimento"
):
    """
    Corrige a filial com base no posto de abastecimento
    APENAS para registros que estão em CSC
    Postos específicos de CSC devem ser realocados para filiais corretas
    """
    # Mapeamento de postos para filiais (APENAS quando estiver em CSC)
    MAPA_POSTOS_CSC = {
        "GP POSTOS - POSTO SAO JOSE": "GRITSCH - CWB (BASE)",
        "GP POSTOS - POSTO TREVO": "GRITSCH - PBC",
        "POSTO BARAO MATRIZ|| REDE BARAO": "GRITSCH - CWB (BASE)",
        "POSTO COPA": "GRITSCH - GPA",
        "SIM REDE - CAMAQUA PARADOURO 0071-94 - CENTRO RS": "GRITSCH - POA",
        "SIM REDE - TC LITORAL 0040-98 - SC SUL": "GRITSCH - POA",
    }

    if coluna_estabelecimento not in df.columns or coluna_filial not in df.columns:
        return df

    registros_corrigidos = 0

    for posto, filial_correta in MAPA_POSTOS_CSC.items():
        # Aplica APENAS quando a filial atual é CSC E o posto bate
        mask = (df[coluna_filial] == "GRITSCH - CSC") & (
            df[coluna_estabelecimento] == posto
        )

        registros_afetados = mask.sum()
        if registros_afetados > 0:
            df.loc[mask, coluna_filial] = filial_correta
            registros_corrigidos += registros_afetados
            print(
                f"   📍 CSC: {posto[:35]}... → {filial_correta} ({registros_afetados} reg)"
            )

    if registros_corrigidos > 0:
        print(f"🔄 {registros_corrigidos} registros de CSC realocados por posto")

    return df


def gerar_resumos_filial(df_filial, nome_filial, caminho_saida):
    """
    Gera arquivo Excel com abas separadas por tipo de combustível
    """

    # Separar dados por tipo de combustível
    df_sem_arla = df_filial[df_filial["Combustivel"] != "Arla 32"].copy()
    df_arla = df_filial[df_filial["Combustivel"] == "Arla 32"].copy()

    # ==================== RESUMO COMBUSTÍVEL (SEM ARLA) ====================
    if len(df_sem_arla) > 0:
        resumo_combustivel = (
            df_sem_arla.groupby("Placa")
            .agg(
                {
                    "Litragem": "sum",
                    "Valor total": "sum",
                    "Hodometro/Horimetro anterior": "min",
                    "Hodometro/Horimetro": "max",
                }
            )
            .reset_index()
        )

        resumo_combustivel.columns = [
            "Rótulos de Linha",
            "Soma de Litragem",
            "Soma de Valor total",
            "Min. de Hodometro/Horimetro anterior",
            "Máx. de Hodometro/Horimetro",
        ]

        # Adicionar linha de total
        total_combustivel = pd.DataFrame(
            [
                {
                    "Rótulos de Linha": "Total Geral",
                    "Soma de Litragem": resumo_combustivel["Soma de Litragem"].sum(),
                    "Soma de Valor total": resumo_combustivel[
                        "Soma de Valor total"
                    ].sum(),
                    "Min. de Hodometro/Horimetro anterior": resumo_combustivel[
                        "Min. de Hodometro/Horimetro anterior"
                    ].min(),
                    "Máx. de Hodometro/Horimetro": resumo_combustivel[
                        "Máx. de Hodometro/Horimetro"
                    ].max(),
                }
            ]
        )
        resumo_combustivel = pd.concat(
            [resumo_combustivel, total_combustivel], ignore_index=True
        )
    else:
        resumo_combustivel = None

    # ==================== RESUMO ARLA ====================
    if len(df_arla) > 0:
        resumo_arla = df_arla.groupby("Placa").agg({"Valor total": "sum"}).reset_index()

        resumo_arla.columns = ["Rótulos de Linha", "Soma de Valor total"]

        # Adicionar linha de total
        total_arla = pd.DataFrame(
            [
                {
                    "Rótulos de Linha": "Total Geral",
                    "Soma de Valor total": resumo_arla["Soma de Valor total"].sum(),
                }
            ]
        )
        resumo_arla = pd.concat([resumo_arla, total_arla], ignore_index=True)
    else:
        resumo_arla = None

    # ==================== RESUMO POR POSTO ====================
    # Usar df_sem_arla para NÃO incluir Arla 32 no resumo por posto
    resumo_posto = (
        df_sem_arla.groupby("Estabelecimento")
        .agg({"Litragem": "sum", "Valor total": "sum"})
        .reset_index()
    )

    resumo_posto.columns = [
        "Rótulos de Linha",
        "Soma de Litragem",
        "Soma de Valor total",
    ]

    # Adicionar linha de total
    total_posto = pd.DataFrame(
        [
            {
                "Rótulos de Linha": "Total Geral",
                "Soma de Litragem": resumo_posto["Soma de Litragem"].sum(),
                "Soma de Valor total": resumo_posto["Soma de Valor total"].sum(),
            }
        ]
    )
    resumo_posto = pd.concat([resumo_posto, total_posto], ignore_index=True)

    # ==================== SALVAR EXCEL ====================
    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        # Aba 1: Dados Brutos
        df_filial.to_excel(writer, sheet_name="Dados Brutos", index=False)

        # Aba 2: Combustível (sem Arla)
        if resumo_combustivel is not None:
            resumo_combustivel.to_excel(
                writer, sheet_name="Combustível (Vários itens)", index=False
            )

        # Aba 3: Arla 32
        if resumo_arla is not None:
            resumo_arla.to_excel(writer, sheet_name="Arla 32", index=False)

        # Aba 4: Resumo por Posto
        resumo_posto.to_excel(writer, sheet_name="Resumo por Posto", index=False)

    # ==================== APLICAR FORMATAÇÃO ====================
    wb = load_workbook(caminho_saida)

    cor_amarelo = PatternFill(
        start_color="FFFF00", end_color="FFFF00", fill_type="solid"
    )
    cor_cinza = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    fonte_negrito = Font(bold=True)
    alinhamento_centro = Alignment(horizontal="center", vertical="center")

    # --- Formatar Combustível (Vários itens) ---
    if resumo_combustivel is not None and "Combustível (Vários itens)" in wb.sheetnames:
        ws = wb["Combustível (Vários itens)"]

        # Cabeçalho amarelo
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(1, col)
            cell.fill = cor_amarelo
            cell.font = fonte_negrito
            cell.alignment = alinhamento_centro

        # Última linha (Total Geral)
        ultima_linha = ws.max_row
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(ultima_linha, col)
            cell.fill = cor_cinza
            cell.font = fonte_negrito

        # Formatar valores
        for row in range(2, ws.max_row + 1):
            ws.cell(row, 2).number_format = "#,##0.00"  # Litragem
            ws.cell(row, 3).number_format = "R$ #,##0.00"  # Valor
            if ws.cell(row, 4).value:
                ws.cell(row, 4).number_format = "0"  # Hod anterior (sem separadores)
            if ws.cell(row, 5).value:
                ws.cell(row, 5).number_format = "0"  # Hod atual (sem separadores)

        # Ajustar largura
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 35
        ws.column_dimensions["E"].width = 30

    # --- Formatar Arla 32 ---
    if resumo_arla is not None and "Arla 32" in wb.sheetnames:
        ws = wb["Arla 32"]

        # Cabeçalho amarelo
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(1, col)
            cell.fill = cor_amarelo
            cell.font = fonte_negrito
            cell.alignment = alinhamento_centro

        # Última linha
        ultima_linha = ws.max_row
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(ultima_linha, col)
            cell.fill = cor_cinza
            cell.font = fonte_negrito

        # Formatar valores
        for row in range(2, ws.max_row + 1):
            ws.cell(row, 2).number_format = "R$ #,##0.00"

        # Ajustar largura
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 22

    # --- Formatar Resumo por Posto ---
    ws = wb["Resumo por Posto"]

    # Cabeçalho amarelo
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(1, col)
        cell.fill = cor_amarelo
        cell.font = fonte_negrito
        cell.alignment = alinhamento_centro

    # Última linha
    ultima_linha = ws.max_row
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(ultima_linha, col)
        cell.fill = cor_cinza
        cell.font = fonte_negrito

    # Formatar valores
    for row in range(2, ws.max_row + 1):
        ws.cell(row, 2).number_format = "#,##0.00"
        ws.cell(row, 3).number_format = "R$ #,##0.00"

    # Ajustar largura
    ws.column_dimensions["A"].width = 60
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 22

    wb.save(caminho_saida)
    return True


from src import config

# ==================== CONFIGURAÇÕES ====================
print("=" * 80)
print(f"GERADOR DE RESUMOS DE COMBUSTÍVEL - {config.MES}/{config.ANO}")
print("=" * 80)

arquivo_excel = config.ARQUIVO_ENTRADA_COMBUSTIVEL
nome_coluna_filial = "Garagem"
prefixo_saida = "Combustivel - "
nome_da_aba = "Sheet1"

print(f"\n📁 Arquivo de entrada: {os.path.basename(arquivo_excel)}")
print(f"📁 Pasta de destino: {os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO)}")

# ==================== PROCESSAMENTO ====================

if not os.path.exists(arquivo_excel):
    print(f"\n❌ ERRO: O arquivo '{arquivo_excel}' não foi encontrado.")
    print("Verifique se o nome do arquivo está correto no config.py")
else:
    try:
        print(f"\n🔄 Lendo o arquivo '{os.path.basename(arquivo_excel)}'...")
        df = pd.read_excel(arquivo_excel, sheet_name=nome_da_aba)
        print("✅ Leitura concluída com sucesso.")

        df = tratar_dados(df)

        # ==================== MAPEAMENTO DE FILIAIS ====================
        print("\n" + "=" * 80)
        print("APLICANDO PRIORIZAÇÃO DE FILIAL DE MANUTENÇÃO COM LÓGICA TEMPORAL")
        print("=" * 80)

        # Criar mapa de filiais a partir da planilha de manutenção
        arquivo_manutencao = config.ARQUIVO_ENTRADA_MANUTENCAO
        if arquivo_manutencao and os.path.exists(arquivo_manutencao):
            historico_filiais = criar_mapa_filiais(arquivo_manutencao)

            # Aplicar filial de manutenção com lógica temporal
            df = aplicar_filial_manutencao(
                df,
                historico_filiais,
                coluna_placa="Placa",
                coluna_garagem="Garagem",
                coluna_data="Data da transacao"
            )

            # Usar Filial_Final para agrupamento
            nome_coluna_filial = "Filial_Final"
        else:
            print(f"⚠️ Arquivo de manutenção não encontrado.")
            print("   Usando coluna 'Garagem' original.")
            nome_coluna_filial = "Garagem"

        # Substituir SAO FREGUESIA por SAO PERUS
        df = substituir_freguesia_por_perus(df, nome_coluna_filial)

        if nome_coluna_filial not in df.columns:
            print(f"\n❌ ERRO: A coluna '{nome_coluna_filial}' não foi encontrada.")
        else:
            filiais_unicas = df[nome_coluna_filial].dropna().unique()

            if len(filiais_unicas) == 0:
                print("\n⚠️ AVISO: Nenhuma filial encontrada.")
            else:
                print(f"\n✅ {len(filiais_unicas)} filiais únicas encontradas")
                print("\n" + "=" * 80)
                print("GERANDO ARQUIVOS POR FILIAL")
                print("=" * 80)

                for idx, filial in enumerate(filiais_unicas, 1):
                    df_filial = df[df[nome_coluna_filial] == filial].copy()

                    # Criar pasta da filial
                    pasta_filial = config.obter_caminho_saida_filial(filial)
                    os.makedirs(pasta_filial, exist_ok=True)

                    nome_filial_limpo = "".join(
                        c for c in str(filial) if c.isalnum() or c in (" ", "_")
                    ).rstrip()
                    nome_arquivo_saida = f"{prefixo_saida}{nome_filial_limpo}.xlsx"
                    caminho_completo_saida = os.path.join(
                        pasta_filial, nome_arquivo_saida
                    )

                    print(f"\n[{idx}/{len(filiais_unicas)}] 📊 {filial}")
                    print(f"      Registros: {len(df_filial)}")
                    print(f"      Pasta: {filial}/")
                    print(f"      Gerando: {nome_arquivo_saida}")

                    if os.path.exists(caminho_completo_saida):
                        try:
                            os.remove(caminho_completo_saida)
                            print(f"      🗑️  Arquivo antigo removido")
                        except Exception as e:
                            print(f"      ⚠️  Não foi possível remover: {e}")
                            continue

                    gerar_resumos_filial(df_filial, filial, caminho_completo_saida)
                    print(f"      ✅ Concluído!")

                print("\n" + "=" * 80)
                print("SALVANDO ARQUIVO GERAL")
                print("=" * 80)

                # Nome dinâmico: MMAA COMBUSTIVEL...
                mes_num = config.obter_numero_mes()
                ano_short = config.ANO[-2:]
                nome_arquivo_geral = (
                    f"{mes_num}{ano_short} COMBUSTIVEL GRITSCH TRANSPORTES GERAL.xlsx"
                )
                pasta_periodo = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO)
                os.makedirs(pasta_periodo, exist_ok=True)
                caminho_completo_geral = os.path.join(
                    pasta_periodo, nome_arquivo_geral
                )

                print(f"\n🔄 Salvando arquivo geral...")
                df.to_excel(caminho_completo_geral, index=False, engine="openpyxl")
                print(f"✅ Arquivo geral salvo!")

                print("\n" + "=" * 80)
                print("🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
                print("=" * 80)
                print(f"\n📁 Arquivos salvos em: {pasta_periodo}")
                print(f"\n✨ Estrutura:")
                print(f"   📂 {config.PASTA_PERIODO}/")
                for filial in sorted(filiais_unicas):
                    nome_limpo = "".join(
                        c for c in str(filial) if c.isalnum() or c in (" ", "_", "-")
                    ).strip()
                    print(f"      📂 {nome_limpo}/")
                    print(f"         📋 Combustivel - *.xlsx")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback

        traceback.print_exc()
