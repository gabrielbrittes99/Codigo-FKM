"""
Gerador de Resumos de Manutenção por Filial
COLUNAS LADO A LADO com 2 COLUNAS VAZIAS entre cada natureza
"""

import os

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

# Importar função de normalização de filiais
from src.filial_mapping import normalizar_filial


def limpar_e_converter_numero(valor):
    """Converte valores com vírgula decimal para float"""
    if pd.isna(valor):
        return np.nan
    if isinstance(valor, (int, float)):
        return float(valor)
    valor_str = str(valor).strip().replace("R$", "").replace(" ", "")
    if "." in valor_str and "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    elif "," in valor_str:
        valor_str = valor_str.replace(",", ".")
    try:
        return float(valor_str)
    except:
        return np.nan


def tratar_dados(df):
    """Trata os dados do DataFrame"""
    print("🔧 Tratando dados...")
    colunas_numericas = ["Quantidade", "ValorUnitario", "ValorTotal"]
    for col in colunas_numericas:
        if col in df.columns:
            print(f"   Convertendo: {col}")
            df[col] = df[col].apply(limpar_e_converter_numero)

    if "Placa" in df.columns:
        print("   Removendo hífens das placas")
        df["Placa"] = df["Placa"].astype(str).str.replace("-", "", regex=False)

    print("✅ Dados tratados com sucesso!")
    return df


def substituir_freguesia_por_perus(df, coluna="FILIAL"):
    """
    Substitui SAO (FREGUESIA) por SAO (PERUS) na coluna especificada
    """
    if coluna in df.columns:
        df[coluna] = (
            df[coluna]
            .astype(str)
            .str.replace("SAO (FREGUESIA)", "SAO (PERUS)", regex=False)
        )
        df[coluna] = (
            df[coluna]
            .astype(str)
            .str.replace("SAO FREGUESIA", "SAO PERUS", regex=False)
        )
        print("🔄 SAO (FREGUESIA) substituído por SAO (PERUS)")
    return df


def aplicar_excecoes_placa(df, coluna_filial="FILIAL", coluna_placa="Placa"):
    """
    Aplica exceções forçadas de placas para filiais específicas
    DESABILITADO: Não usar exceções forçadas
    """
    # Normalizar placa para busca (mantido para compatibilidade)
    if coluna_placa in df.columns:
        df["Placa_Clean"] = (
            df[coluna_placa]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )

    from src.filial_mapping import EXCECOES_FORCADAS, EXCECOES_MANUTENCAO

    excecoes = {**EXCECOES_FORCADAS, **EXCECOES_MANUTENCAO}
    
    # Aplica para placas que estão na lista de exceções forçadas ou de manutenção
    for placa, filial_correta in excecoes.items():
        if "Placa_Clean" in df.columns:
            mask = df["Placa_Clean"] == placa
        else:
            mask = df[coluna_placa] == placa
            
        registros_afetados = mask.sum()
        if registros_afetados > 0:
            df.loc[mask, coluna_filial] = filial_correta
            print(f"   📍 Placa {placa} forçada para filial {filial_correta} ({registros_afetados} registros de manutenção ajustados)")

    return df


def gerar_resumos_manutencao(df_filial, nome_filial, caminho_saida):
    """
    Gera arquivo Excel com naturezas LADO A LADO
    com 2 COLUNAS VAZIAS entre cada natureza
    """

    # Obter naturezas únicas e ordenar
    naturezas = sorted(df_filial["Natureza_Correta"].fillna("(vazio)").unique())

    # Criar resumos para cada natureza
    resumos_dict = {}
    max_linhas = 0

    for natureza in naturezas:
        # Filtrar dados dessa natureza
        if natureza == "(vazio)":
            df_natureza = df_filial[df_filial["Natureza_Correta"].isna()].copy()
        else:
            df_natureza = df_filial[df_filial["Natureza_Correta"] == natureza].copy()

        if len(df_natureza) > 0:
            # Agrupar por placa
            resumo = (
                df_natureza.groupby("Placa").agg({"ValorTotal": "sum"}).reset_index()
            )

            resumo.columns = [natureza, "Valor"]

            # Adicionar total
            total = pd.DataFrame(
                [[" Total Geral", resumo["Valor"].sum()]], columns=[natureza, "Valor"]
            )
            resumo = pd.concat([resumo, total], ignore_index=True)

            resumos_dict[natureza] = resumo
            max_linhas = max(max_linhas, len(resumo))

    # Criar DataFrame consolidado lado a lado
    df_consolidado = pd.DataFrame()

    for idx, (natureza, resumo) in enumerate(resumos_dict.items()):
        # Adicionar linhas vazias se o resumo for menor que max_linhas
        while len(resumo) < max_linhas:
            resumo = pd.concat(
                [resumo, pd.DataFrame([[" ", " "]], columns=[natureza, "Valor"])],
                ignore_index=True,
            )

        # Concatenar horizontalmente
        if df_consolidado.empty:
            df_consolidado = resumo
        else:
            df_consolidado = pd.concat([df_consolidado, resumo], axis=1)

        # Adicionar 2 COLUNAS VAZIAS de separação (exceto depois da última natureza)
        if idx < len(resumos_dict) - 1:
            coluna_vazia1 = pd.DataFrame({f"_sep1_{idx}": [" "] * max_linhas})
            coluna_vazia2 = pd.DataFrame({f"_sep2_{idx}": [" "] * max_linhas})
            df_consolidado = pd.concat(
                [df_consolidado, coluna_vazia1, coluna_vazia2], axis=1
            )

    # Salvar Excel
    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        # Aba 1: Dados Brutos
        df_filial.to_excel(writer, sheet_name="Dados Brutos", index=False)

        # Aba 2: Resumo Consolidado
        df_consolidado.to_excel(writer, sheet_name="Resumo por Natureza", index=False)

    # Aplicar formatação
    wb = load_workbook(caminho_saida)
    ws = wb["Resumo por Natureza"]

    # Cores da empresa (Azul, Vermelho, Amarelo)
    cores_empresa = [
        {
            "fill": PatternFill(
                start_color="0070C0", end_color="0070C0", fill_type="solid"
            ),
            "font_color": "FFFFFF",
        },  # Azul (fonte branca)
        {
            "fill": PatternFill(
                start_color="FF0000", end_color="FF0000", fill_type="solid"
            ),
            "font_color": "FFFFFF",
        },  # Vermelho (fonte branca)
        {
            "fill": PatternFill(
                start_color="FFFF00", end_color="FFFF00", fill_type="solid"
            ),
            "font_color": "000000",
        },  # Amarelo (fonte preta)
    ]

    cor_cinza = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    fonte_negrito = Font(bold=True)
    alinhamento_centro = Alignment(horizontal="center", vertical="center")

    # Formatar cabeçalhos com cores da empresa (rotacionando)
    num_naturezas = len(resumos_dict)

    for i in range(num_naturezas):
        # Calcular índices das colunas (1-based)
        col_start = 1 + i * 4
        col_end = col_start + 1

        # Escolher cor (rotacionar)
        estilo_atual = cores_empresa[i % len(cores_empresa)]
        fill_atual = estilo_atual["fill"]
        font_atual = Font(bold=True, color=estilo_atual["font_color"])

        # Aplicar cor no cabeçalho (linha 1)
        if col_start <= ws.max_column:
            ws.cell(1, col_start).fill = fill_atual
            ws.cell(1, col_start).font = font_atual
            ws.cell(1, col_start).alignment = alinhamento_centro

        if col_end <= ws.max_column:
            ws.cell(1, col_end).fill = fill_atual
            ws.cell(1, col_end).font = font_atual
            ws.cell(1, col_end).alignment = alinhamento_centro

    # Última linha de cada seção (Total Geral) - cinza
    for row in range(2, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            col_name = ws.cell(1, col).value
            if col_name and "_sep" in str(col_name):
                continue

            if (
                ws.cell(row, col).value
                and str(ws.cell(row, col).value).strip() == "Total Geral"
            ):
                # Formatar essa linha como total (placa + valor)
                ws.cell(row, col).fill = cor_cinza
                ws.cell(row, col).font = fonte_negrito
                if col + 1 <= ws.max_column:
                    ws.cell(row, col + 1).fill = cor_cinza
                    ws.cell(row, col + 1).font = fonte_negrito

    # Formatar valores monetários
    for row in range(2, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            col_name = ws.cell(1, col).value
            if col_name and "_sep" in str(col_name):
                continue
            if col_name and col_name == "Valor":
                if ws.cell(row, col).value and ws.cell(row, col).value != " ":
                    try:
                        ws.cell(row, col).number_format = "R$ #,##0.00"
                    except:
                        pass

    # Ajustar largura das colunas
    for col in range(1, ws.max_column + 1):
        col_letter = (
            chr(64 + col) if col <= 26 else chr(64 + (col // 26)) + chr(64 + (col % 26))
        )
        col_name = ws.cell(1, col).value

        if col_name and "_sep" in str(col_name):
            # Coluna de separação - estreita
            ws.column_dimensions[col_letter].width = 2
        elif col_name and col_name == "Valor":
            # Coluna de valor
            ws.column_dimensions[col_letter].width = 18
        else:
            # Coluna de placa/natureza
            ws.column_dimensions[col_letter].width = 35

    # Limpar textos dos cabeçalhos de separação (deixar em branco)
    for col in range(1, ws.max_column + 1):
        col_name = ws.cell(1, col).value
        if col_name and "_sep" in str(col_name):
            ws.cell(1, col).value = ""

    wb.save(caminho_saida)
    return True


from src import config

# ==================== CONFIGURAÇÕES ====================
print("=" * 80)
print(f"GERADOR DE RESUMOS DE MANUTENÇÃO - {config.MES}/{config.ANO}")
print("=" * 80)

arquivo_excel = config.ARQUIVO_ENTRADA_MANUTENCAO
nome_coluna_filial = "FILIAL"
prefixo_saida = "Manutencao - "

print(f"\n📁 Arquivo de entrada: {os.path.basename(arquivo_excel)}")
print(f"📁 Pasta de destino: {os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO)}")

# ==================== PROCESSAMENTO ====================

if not os.path.exists(arquivo_excel):
    print(f"\n❌ ERRO: O arquivo '{arquivo_excel}' não foi encontrado.")
    print("Verifique se o nome do arquivo está correto no config.py")
else:
    try:
        print(f"\n🔄 Lendo o arquivo '{os.path.basename(arquivo_excel)}'...")
        df = pd.read_excel(arquivo_excel)
        print("✅ Leitura concluída com sucesso.")

        df = tratar_dados(df)

        # Normalizar filiais (consolidar CWB ECT e BASE)
        if nome_coluna_filial in df.columns:
            df[nome_coluna_filial] = df[nome_coluna_filial].apply(normalizar_filial)
            print("🔄 Filiais normalizadas (CWB ECT → CWB BASE)")

        # Substituir SAO FREGUESIA por SAO PERUS
        df = substituir_freguesia_por_perus(df, nome_coluna_filial)

        # Aplicar exceções forçadas de placas
        df = aplicar_excecoes_placa(df, nome_coluna_filial, "Placa")

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

                    gerar_resumos_manutencao(df_filial, filial, caminho_completo_saida)
                    print(f"      ✅ Concluído!")

                print("\n" + "=" * 80)
                print("SALVANDO ARQUIVO GERAL")
                print("=" * 80)

                # Nome dinâmico: MMAA MANUTENÇÃO...
                mes_num = config.obter_numero_mes()
                ano_short = config.ANO[-2:]
                nome_arquivo_geral = (
                    f"{mes_num}{ano_short} MANUTENÇÃO GRITSCH TRANSPORTES GERAL.xlsx"
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
                    print(f"         📋 Manutencao - *.xlsx")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback

        traceback.print_exc()
