"""
Gerador de Relatório de KPIs - Combustível e Manutenção
Versão 2.0 - Com integração de frota e análises avançadas
"""

import os

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src import config
from src.filial_mapping import (
    aplicar_filial_manutencao,
    criar_mapa_filiais,
    normalizar_filial,
)
from src.frota_mapping import carregar_frota, enriquecer_com_frota


def limpar_numero(valor):
    """Converte valores para float"""
    if pd.isna(valor):
        return 0.0
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
        return 0.0


def formatar_aba(ws, cor_cabecalho="0070C0"):
    """Aplica formatação padrão na aba"""
    # Cores
    fill_cabecalho = PatternFill(
        start_color=cor_cabecalho, end_color=cor_cabecalho, fill_type="solid"
    )
    fill_total = PatternFill(
        start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"
    )
    fonte_cabecalho = Font(bold=True, color="FFFFFF")
    fonte_total = Font(bold=True)
    alinhamento = Alignment(horizontal="center", vertical="center")
    borda = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Formatar cabeçalho
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(1, col)
        cell.fill = fill_cabecalho
        cell.font = fonte_cabecalho
        cell.alignment = alinhamento
        cell.border = borda

    # Formatar dados
    for row in range(2, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row, col)
            cell.border = borda

            # Última linha (totais)
            if row == ws.max_row:
                valor = ws.cell(row, 1).value
                if valor and "Total" in str(valor).upper():
                    cell.fill = fill_total
                    cell.font = fonte_total

    # Ajustar largura das colunas
    for col in range(1, ws.max_column + 1):
        max_length = 0
        col_letter = get_column_letter(col)
        for row in range(1, min(ws.max_row + 1, 100)):  # Check first 100 rows
            cell = ws.cell(row, col)
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max(max_length + 2, 12), 50)


def gerar_relatorio_kpis():
    """Gera relatório completo de KPIs com 10 abas"""

    print("=" * 80)
    print(f"GERADOR DE RELATÓRIO DE KPIs - {config.MES}/{config.ANO}")
    print("Versão 2.0 - Com integração de frota")
    print("=" * 80)

    # ==================== CARREGAR DADOS ====================
    print("\n📥 Carregando dados...")

    # Combustível
    if not os.path.exists(config.ARQUIVO_ENTRADA_COMBUSTIVEL):
        print(
            f"❌ Arquivo de combustível não encontrado: {config.ARQUIVO_ENTRADA_COMBUSTIVEL}"
        )
        return

    df_comb = pd.read_excel(config.ARQUIVO_ENTRADA_COMBUSTIVEL)
    print(f"   ✅ Combustível: {len(df_comb)} registros")

    # Manutenção
    if not os.path.exists(config.ARQUIVO_ENTRADA_MANUTENCAO):
        print(
            f"❌ Arquivo de manutenção não encontrado: {config.ARQUIVO_ENTRADA_MANUTENCAO}"
        )
        return

    df_manut = pd.read_excel(config.ARQUIVO_ENTRADA_MANUTENCAO)
    print(f"   ✅ Manutenção: {len(df_manut)} registros")

    # Frota
    df_frota = carregar_frota(config.ARQUIVO_ENTRADA_FROTA)

    # ==================== TRATAR DADOS ====================
    print("\n🔧 Tratando dados...")

    # Combustível - converter valores numéricos
    df_comb["Litragem"] = df_comb["Litragem"].apply(limpar_numero)
    df_comb["Valor total"] = df_comb["Valor total"].apply(limpar_numero)
    df_comb["Preco"] = df_comb["Preco"].apply(limpar_numero)

    # Normalizar placas
    df_comb["Placa_Clean"] = (
        df_comb["Placa"].astype(str).str.replace("-", "").str.strip().str.upper()
    )

    # Manutenção - converter valores
    df_manut["ValorTotal"] = df_manut["ValorTotal"].apply(limpar_numero)
    df_manut["Placa_Clean"] = (
        df_manut["Placa"].astype(str).str.replace("-", "").str.strip().str.upper()
    )

    # Aplicar normalização de filiais
    df_comb["Garagem"] = df_comb["Garagem"].apply(normalizar_filial)
    df_manut["FILIAL"] = df_manut["FILIAL"].apply(normalizar_filial)

    # FILTRAR: Remover filiais REFERÊNCIA da manutenção
    registros_antes = len(df_manut)
    df_manut = df_manut[
        ~df_manut["FILIAL"].str.contains("REFERÊNCIA|REFERENCIA", case=False, na=False)
    ]
    registros_removidos = registros_antes - len(df_manut)
    if registros_removidos > 0:
        print(
            f"   🚧 Removidos {registros_removidos} registros de filiais REFERÊNCIA da manutenção"
        )

    # Aplicar mapeamento de filiais para combustível
    historico_filiais = criar_mapa_filiais(config.ARQUIVO_ENTRADA_MANUTENCAO)
    df_comb = aplicar_filial_manutencao(
        df_comb,
        historico_filiais,
        coluna_placa="Placa",
        coluna_garagem="Garagem",
        coluna_data="Data da transacao",
    )

    # Enriquecer com dados da frota
    print("\n🚗 Enriquecendo com dados da frota...")
    df_comb = enriquecer_com_frota(df_comb, df_frota)
    df_manut = enriquecer_com_frota(df_manut, df_frota)

    # ==================== PREPARAR DADOS PARA KPIs ====================
    print("\n📊 Calculando KPIs...")

    # Totais gerais
    total_placas_comb = df_comb["Placa_Clean"].nunique()
    total_placas_manut = df_manut["Placa_Clean"].nunique()
    total_placas = len(
        set(df_comb["Placa_Clean"].unique()) | set(df_manut["Placa_Clean"].unique())
    )

    total_combustivel = df_comb["Valor total"].sum()
    total_litros = df_comb["Litragem"].sum()
    total_manutencao = df_manut["ValorTotal"].sum()
    total_geral = total_combustivel + total_manutencao

    # ===== ABA 1: RESUMO GERAL (EXPANDIDO) =====
    resumo_rows = []

    # SEÇÃO: PERÍODO
    resumo_rows.append({"Indicador": "=== PERÍODO ===", "Valor": ""})
    resumo_rows.append({"Indicador": "Período", "Valor": f"{config.MES}/{config.ANO}"})
    resumo_rows.append(
        {"Indicador": "Total de Veículos (Combustível)", "Valor": total_placas_comb}
    )
    resumo_rows.append(
        {"Indicador": "Total de Veículos (Manutenção)", "Valor": total_placas_manut}
    )
    resumo_rows.append(
        {"Indicador": "Total de Veículos (Geral)", "Valor": total_placas}
    )
    resumo_rows.append({"Indicador": "", "Valor": ""})

    # SEÇÃO: FROTA
    total_frota = len(df_frota)
    placas_com_custo = set(df_comb["Placa_Clean"].unique()) | set(
        df_manut["Placa_Clean"].unique()
    )
    placas_sem_custo = (
        len(df_frota) - len(set(df_frota["Placa_Clean"].unique()) & placas_com_custo)
        if len(df_frota) > 0
        else 0
    )

    resumo_rows.append({"Indicador": "=== FROTA ===", "Valor": ""})
    resumo_rows.append(
        {"Indicador": "Total de Veículos na Frota", "Valor": total_frota}
    )
    resumo_rows.append(
        {"Indicador": "Veículos com Custo no Período", "Valor": total_placas}
    )
    resumo_rows.append({"Indicador": "", "Valor": ""})

    # SEÇÃO: RESUMO POR GRUPO
    resumo_rows.append(
        {"Indicador": "=== RESUMO POR GRUPO DE VEÍCULO ===", "Valor": ""}
    )
    placas_com_custo_set = set(df_comb["Placa_Clean"].unique()) | set(
        df_manut["Placa_Clean"].unique()
    )
    custo_por_placa_resumo = pd.merge(
        df_comb.groupby("Placa_Clean").agg({"Valor total": "sum"}).reset_index(),
        df_manut.groupby("Placa_Clean").agg({"ValorTotal": "sum"}).reset_index(),
        on="Placa_Clean",
        how="outer",
    ).fillna(0)
    custo_por_placa_resumo = enriquecer_com_frota(custo_por_placa_resumo, df_frota)
    custo_por_placa_resumo["Total"] = (
        custo_por_placa_resumo["Valor total"] + custo_por_placa_resumo["ValorTotal"]
    )

    if "Grupo" in custo_por_placa_resumo.columns:
        resumo_grupo = (
            custo_por_placa_resumo.groupby("Grupo")
            .agg({"Placa_Clean": "count", "Total": "sum"})
            .reset_index()
            .sort_values("Total", ascending=False)
        )

        for _, row in resumo_grupo.iterrows():
            grupo = row["Grupo"]
            veiculos = row["Placa_Clean"]
            total = row["Total"]
            resumo_rows.append(
                {
                    "Indicador": f"  {grupo}",
                    "Valor": f"{veiculos} veículos | R$ {total:,.2f}",
                }
            )
    resumo_rows.append({"Indicador": "", "Valor": ""})

    # SEÇÃO: COMBUSTÍVEL
    resumo_rows.append({"Indicador": "=== COMBUSTÍVEL ===", "Valor": ""})
    resumo_rows.append(
        {
            "Indicador": "Gasto Total Combustível",
            "Valor": f"R$ {total_combustivel:,.2f}",
        }
    )
    resumo_rows.append(
        {"Indicador": "Total de Litros", "Valor": f"{total_litros:,.2f}"}
    )
    resumo_rows.append(
        {
            "Indicador": "Preço Médio/Litro (Geral)",
            "Valor": f"R$ {total_combustivel / total_litros:.4f}"
            if total_litros > 0
            else "-",
        }
    )
    resumo_rows.append({"Indicador": "---", "Valor": "---"})

    # Por tipo de combustível
    comb_tipo_resumo = (
        df_comb.groupby("Combustivel")
        .agg({"Valor total": "sum", "Litragem": "sum"})
        .reset_index()
        .sort_values("Valor total", ascending=False)
    )

    for _, row in comb_tipo_resumo.iterrows():
        tipo = row["Combustivel"]
        valor = row["Valor total"]
        litros = row["Litragem"]
        preco_medio = valor / litros if litros > 0 else 0
        resumo_rows.append(
            {
                "Indicador": f"  {tipo}",
                "Valor": f"R$ {valor:,.2f} | {litros:,.2f} L | R$ {preco_medio:.4f}/L",
            }
        )
    resumo_rows.append({"Indicador": "", "Valor": ""})

    # SEÇÃO: MANUTENÇÃO
    resumo_rows.append({"Indicador": "=== MANUTENÇÃO ===", "Valor": ""})
    resumo_rows.append(
        {"Indicador": "Gasto Total Manutenção", "Valor": f"R$ {total_manutencao:,.2f}"}
    )
    resumo_rows.append({"Indicador": "---", "Valor": "---"})

    # Por Natureza_Correta
    if "Natureza_Correta" in df_manut.columns:
        manut_natureza_resumo = (
            df_manut.groupby("Natureza_Correta")
            .agg({"ValorTotal": "sum"})
            .reset_index()
            .sort_values("ValorTotal", ascending=False)
        )

        resumo_rows.append({"Indicador": "Por Natureza:", "Valor": ""})
        for _, row in manut_natureza_resumo.iterrows():
            natureza = row["Natureza_Correta"]
            valor = row["ValorTotal"]
            pct = (valor / total_manutencao * 100) if total_manutencao > 0 else 0
            resumo_rows.append(
                {"Indicador": f"  {natureza}", "Valor": f"R$ {valor:,.2f} | {pct:.1f}%"}
            )
        resumo_rows.append({"Indicador": "---", "Valor": "---"})

    # Por GrupoDespesa (top 10)
    if "GrupoDespesa" in df_manut.columns:
        manut_grupo_resumo = (
            df_manut.groupby("GrupoDespesa")
            .agg({"ValorTotal": "sum"})
            .reset_index()
            .sort_values("ValorTotal", ascending=False)
            .head(10)
        )

        resumo_rows.append({"Indicador": "Por Grupo de Despesa (Top 10):", "Valor": ""})
        for _, row in manut_grupo_resumo.iterrows():
            grupo = row["GrupoDespesa"]
            valor = row["ValorTotal"]
            pct = (valor / total_manutencao * 100) if total_manutencao > 0 else 0
            resumo_rows.append(
                {"Indicador": f"  {grupo}", "Valor": f"R$ {valor:,.2f} | {pct:.1f}%"}
            )
        resumo_rows.append({"Indicador": "---", "Valor": "---"})

    # Por Tipo de Manutenção
    if "Tipo" in df_manut.columns:
        manut_tipo_resumo = (
            df_manut.groupby("Tipo")
            .agg({"ValorTotal": "sum"})
            .reset_index()
            .sort_values("ValorTotal", ascending=False)
        )

        resumo_rows.append({"Indicador": "Por Tipo de Manutenção:", "Valor": ""})
        for _, row in manut_tipo_resumo.iterrows():
            tipo = row["Tipo"]
            valor = row["ValorTotal"]
            pct = (valor / total_manutencao * 100) if total_manutencao > 0 else 0
            resumo_rows.append(
                {"Indicador": f"  {tipo}", "Valor": f"R$ {valor:,.2f} | {pct:.1f}%"}
            )

    resumo_rows.append({"Indicador": "", "Valor": ""})

    # SEÇÃO: CUSTO OPERACIONAL
    resumo_rows.append({"Indicador": "=== CUSTO OPERACIONAL ===", "Valor": ""})
    resumo_rows.append(
        {"Indicador": "CUSTO OPERACIONAL TOTAL", "Valor": f"R$ {total_geral:,.2f}"}
    )
    resumo_rows.append(
        {
            "Indicador": "Média por Veículo",
            "Valor": f"R$ {total_geral / total_placas:,.2f}"
            if total_placas > 0
            else "-",
        }
    )

    resumo_geral = pd.DataFrame(resumo_rows)

    # ===== ABA 2: COMBUSTÍVEL POR TIPO (MELHORADO) =====
    combustivel_por_tipo = (
        df_comb.groupby("Combustivel")
        .agg(
            {
                "Litragem": "sum",
                "Valor total": "sum",
                "Placa_Clean": "nunique",
                "Estado": "nunique",
                "Cidade": "nunique",
            }
        )
        .reset_index()
    )
    combustivel_por_tipo.columns = [
        "Tipo Combustível",
        "Litros",
        "Valor Total (R$)",
        "Veículos",
        "Estados Atendidos",
        "Cidades Atendidas",
    ]

    # Calcular preço médio por litro
    combustivel_por_tipo["Preço Médio/L"] = (
        combustivel_por_tipo["Valor Total (R$)"] / combustivel_por_tipo["Litros"]
    )
    combustivel_por_tipo["Preço Médio/L"] = combustivel_por_tipo[
        "Preço Médio/L"
    ].fillna(0)

    # Adicionar % do total
    combustivel_por_tipo["% do Total"] = (
        combustivel_por_tipo["Valor Total (R$)"] / total_combustivel * 100
    ).round(2)

    # Ordenar por valor
    combustivel_por_tipo = combustivel_por_tipo.sort_values(
        "Valor Total (R$)", ascending=False
    )

    # Adicionar linha de total
    total_row = pd.DataFrame(
        [
            {
                "Tipo Combustível": "TOTAL GERAL",
                "Litros": combustivel_por_tipo["Litros"].sum(),
                "Valor Total (R$)": combustivel_por_tipo["Valor Total (R$)"].sum(),
                "Veículos": "-",
                "Estados Atendidos": "-",
                "Cidades Atendidas": "-",
                "Preço Médio/L": "-",
                "% do Total": 100.0,
            }
        ]
    )
    combustivel_por_tipo = pd.concat(
        [combustivel_por_tipo, total_row], ignore_index=True
    )

    # ===== ABA 3: COMBUSTÍVEL POR FILIAL (MELHORADO) =====
    # Tabela principal
    combustivel_por_filial = (
        df_comb.groupby("Filial_Final")
        .agg({"Placa_Clean": "nunique", "Litragem": "sum", "Valor total": "sum"})
        .reset_index()
    )
    combustivel_por_filial.columns = [
        "Filial",
        "Veículos",
        "Litros Total",
        "Valor Total (R$)",
    ]
    combustivel_por_filial["Média por Veículo (R$)"] = (
        combustivel_por_filial["Valor Total (R$)"] / combustivel_por_filial["Veículos"]
    )

    # Pivot por tipo de combustível (litros e valores)
    tipos_principais = [
        "Diesel S10",
        "Diesel S10 Aditivado",
        "Gasolina Comum",
        "Arla 32",
    ]

    for tipo in tipos_principais:
        df_tipo = df_comb[df_comb["Combustivel"] == tipo]
        if len(df_tipo) > 0:
            tipo_litros = (
                df_tipo.groupby("Filial_Final").agg({"Litragem": "sum"}).reset_index()
            )
            tipo_litros.columns = ["Filial", f"{tipo} (L)"]
            combustivel_por_filial = pd.merge(
                combustivel_por_filial, tipo_litros, on="Filial", how="left"
            )
            combustivel_por_filial[f"{tipo} (L)"] = combustivel_por_filial[
                f"{tipo} (L)"
            ].fillna(0)

            tipo_valor = (
                df_tipo.groupby("Filial_Final")
                .agg({"Valor total": "sum"})
                .reset_index()
            )
            tipo_valor.columns = ["Filial", f"{tipo} (R$)"]
            combustivel_por_filial = pd.merge(
                combustivel_por_filial, tipo_valor, on="Filial", how="left"
            )
            combustivel_por_filial[f"{tipo} (R$)"] = combustivel_por_filial[
                f"{tipo} (R$)"
            ].fillna(0)

    # Outros combustíveis
    df_outros = df_comb[~df_comb["Combustivel"].isin(tipos_principais)]
    if len(df_outros) > 0:
        outros_litros = (
            df_outros.groupby("Filial_Final").agg({"Litragem": "sum"}).reset_index()
        )
        outros_litros.columns = ["Filial", "Outros (L)"]
        combustivel_por_filial = pd.merge(
            combustivel_por_filial, outros_litros, on="Filial", how="left"
        )
        combustivel_por_filial["Outros (L)"] = combustivel_por_filial[
            "Outros (L)"
        ].fillna(0)

        outros_valor = (
            df_outros.groupby("Filial_Final").agg({"Valor total": "sum"}).reset_index()
        )
        outros_valor.columns = ["Filial", "Outros (R$)"]
        combustivel_por_filial = pd.merge(
            combustivel_por_filial, outros_valor, on="Filial", how="left"
        )
        combustivel_por_filial["Outros (R$)"] = combustivel_por_filial[
            "Outros (R$)"
        ].fillna(0)

    combustivel_por_filial = combustivel_por_filial.sort_values(
        "Valor Total (R$)", ascending=False
    )

    # Sub-tabela: Por Filial + Grupo
    combustivel_filial_grupo = (
        df_comb.groupby(["Filial_Final", "Grupo"])
        .agg({"Placa_Clean": "nunique", "Litragem": "sum", "Valor total": "sum"})
        .reset_index()
    )
    combustivel_filial_grupo.columns = [
        "Filial",
        "Grupo",
        "Veículos",
        "Litros",
        "Valor Total (R$)",
    ]
    combustivel_filial_grupo["Média por Veículo (R$)"] = (
        combustivel_filial_grupo["Valor Total (R$)"]
        / combustivel_filial_grupo["Veículos"]
    )
    combustivel_filial_grupo = combustivel_filial_grupo.sort_values(
        ["Filial", "Valor Total (R$)"], ascending=[True, False]
    )

    # ===== ABA 4: MANUTENÇÃO POR NATUREZA (sem mudanças) =====
    coluna_natureza = (
        "Natureza_Correta" if "Natureza_Correta" in df_manut.columns else "Natureza"
    )

    manut_por_natureza = (
        df_manut.groupby(coluna_natureza)
        .agg({"ValorTotal": "sum", "Placa_Clean": "nunique"})
        .reset_index()
    )
    manut_por_natureza.columns = ["Natureza", "Valor Total (R$)", "Veículos"]
    manut_por_natureza["% do Total"] = (
        manut_por_natureza["Valor Total (R$)"] / total_manutencao * 100
    ).round(2)
    manut_por_natureza = manut_por_natureza.sort_values(
        "Valor Total (R$)", ascending=False
    )

    # Total
    total_row = pd.DataFrame(
        [
            {
                "Natureza": "TOTAL GERAL",
                "Valor Total (R$)": manut_por_natureza["Valor Total (R$)"].sum(),
                "Veículos": "-",
                "% do Total": 100.0,
            }
        ]
    )
    manut_por_natureza = pd.concat([manut_por_natureza, total_row], ignore_index=True)

    # ===== ABA 5: MANUTENÇÃO POR FILIAL (sem mudanças) =====
    manut_por_filial = (
        df_manut.groupby("FILIAL")
        .agg({"ValorTotal": "sum", "Placa_Clean": "nunique"})
        .reset_index()
    )
    manut_por_filial.columns = ["Filial", "Valor Total (R$)", "Veículos"]
    manut_por_filial["Média por Veículo (R$)"] = (
        manut_por_filial["Valor Total (R$)"] / manut_por_filial["Veículos"]
    )
    manut_por_filial = manut_por_filial.sort_values("Valor Total (R$)", ascending=False)

    # Total
    total_row = pd.DataFrame(
        [
            {
                "Filial": "TOTAL GERAL",
                "Valor Total (R$)": manut_por_filial["Valor Total (R$)"].sum(),
                "Veículos": manut_por_filial["Veículos"].sum(),
                "Média por Veículo (R$)": manut_por_filial["Valor Total (R$)"].sum()
                / manut_por_filial["Veículos"].sum(),
            }
        ]
    )
    manut_por_filial = pd.concat([manut_por_filial, total_row], ignore_index=True)

    # ===== ABA 6: MANUTENÇÃO POR GRUPO DE DESPESA (NOVA) =====
    manut_por_grupo_despesa = pd.DataFrame()

    if "GrupoDespesa" in df_manut.columns:
        manut_por_grupo_despesa = (
            df_manut.groupby("GrupoDespesa")
            .agg(
                valor_total=("ValorTotal", "sum"),
                veiculos=("Placa_Clean", "nunique"),
                qtd_registros=("ValorTotal", "count"),
            )
            .reset_index()
        )

        manut_por_grupo_despesa.columns = [
            "GrupoDespesa",
            "Valor Total (R$)",
            "Veículos",
            "Qtd Registros",
        ]
        manut_por_grupo_despesa["Média por Registro (R$)"] = (
            manut_por_grupo_despesa["Valor Total (R$)"]
            / manut_por_grupo_despesa["Qtd Registros"]
        )
        manut_por_grupo_despesa["% do Total"] = (
            manut_por_grupo_despesa["Valor Total (R$)"] / total_manutencao * 100
        ).round(2)
        manut_por_grupo_despesa = manut_por_grupo_despesa.sort_values(
            "Valor Total (R$)", ascending=False
        )

        # Total
        total_row = pd.DataFrame(
            [
                {
                    "GrupoDespesa": "TOTAL GERAL",
                    "Valor Total (R$)": manut_por_grupo_despesa[
                        "Valor Total (R$)"
                    ].sum(),
                    "Veículos": "-",
                    "Qtd Registros": manut_por_grupo_despesa["Qtd Registros"].sum(),
                    "Média por Registro (R$)": "-",
                    "% do Total": 100.0,
                }
            ]
        )
        manut_por_grupo_despesa = pd.concat(
            [manut_por_grupo_despesa, total_row], ignore_index=True
        )

    # ===== ABA 7: CUSTO POR PLACA (MELHORADO) =====
    # Agrupar combustível por placa
    comb_por_placa = (
        df_comb.groupby(["Placa_Clean", "Filial_Final"])
        .agg({"Valor total": "sum", "Litragem": "sum"})
        .reset_index()
    )
    comb_por_placa.columns = ["Placa", "Filial", "Combustível (R$)", "Litros"]

    # Agrupar manutenção por placa
    manut_por_placa = (
        df_manut.groupby(["Placa_Clean", "FILIAL"])
        .agg({"ValorTotal": "sum"})
        .reset_index()
    )
    manut_por_placa.columns = ["Placa", "Filial_Manut", "Manutenção (R$)"]

    # Juntar dados
    custo_por_placa = pd.merge(comb_por_placa, manut_por_placa, on="Placa", how="outer")
    custo_por_placa["Combustível (R$)"] = custo_por_placa["Combustível (R$)"].fillna(0)
    custo_por_placa["Manutenção (R$)"] = custo_por_placa["Manutenção (R$)"].fillna(0)
    custo_por_placa["Litros"] = custo_por_placa["Litros"].fillna(0)

    # Usar filial de combustível ou manutenção
    custo_por_placa["Filial"] = custo_por_placa["Filial"].fillna(
        custo_por_placa["Filial_Manut"]
    )
    custo_por_placa = custo_por_placa.drop(columns=["Filial_Manut"])

    # Enriquecer com frota
    custo_por_placa = enriquecer_com_frota(custo_por_placa, df_frota)

    # Calcular total e percentuais
    custo_por_placa["TOTAL (R$)"] = (
        custo_por_placa["Combustível (R$)"] + custo_por_placa["Manutenção (R$)"]
    )
    custo_por_placa["% Combustível"] = (
        custo_por_placa["Combustível (R$)"] / custo_por_placa["TOTAL (R$)"] * 100
    ).round(1)
    custo_por_placa["% Manutenção"] = (
        custo_por_placa["Manutenção (R$)"] / custo_por_placa["TOTAL (R$)"] * 100
    ).round(1)
    custo_por_placa["% Combustível"] = custo_por_placa["% Combustível"].fillna(0)
    custo_por_placa["% Manutenção"] = custo_por_placa["% Manutenção"].fillna(0)

    # Ordenar do maior para o menor
    custo_por_placa = custo_por_placa.sort_values("TOTAL (R$)", ascending=False)

    # Reordenar colunas
    custo_por_placa = custo_por_placa[
        [
            "Placa",
            "Filial",
            "Grupo",
            "Modelo Simplificado",
            "Litros",
            "Combustível (R$)",
            "Manutenção (R$)",
            "TOTAL (R$)",
            "% Combustível",
            "% Manutenção",
        ]
    ]

    # ===== ABA 8: COMBUSTÍVEL POR REGIÃO (NOVA) =====
    # Seção A: Por Estado
    comb_por_estado = (
        df_comb.groupby("Estado")
        .agg(
            {
                "Litragem": "sum",
                "Valor total": "sum",
                "Placa_Clean": "nunique",
                "Estabelecimento": "nunique",
                "Cidade": "nunique",
            }
        )
        .reset_index()
    )
    comb_por_estado.columns = [
        "Estado",
        "Litros",
        "Valor Total (R$)",
        "Veículos",
        "Postos",
        "Cidades",
    ]
    comb_por_estado["Preço Médio/L"] = (
        comb_por_estado["Valor Total (R$)"] / comb_por_estado["Litros"]
    )
    comb_por_estado = comb_por_estado.sort_values("Valor Total (R$)", ascending=False)

    # Seção B: Por Estado x Combustível
    comb_estado_tipo = (
        df_comb.groupby(["Estado", "Combustivel"])
        .agg({"Litragem": "sum", "Valor total": "sum"})
        .reset_index()
    )
    comb_estado_tipo.columns = [
        "Estado",
        "Tipo Combustível",
        "Litros",
        "Valor Total (R$)",
    ]
    comb_estado_tipo["Preço Médio/L"] = (
        comb_estado_tipo["Valor Total (R$)"] / comb_estado_tipo["Litros"]
    )
    comb_estado_tipo = comb_estado_tipo.sort_values(
        ["Estado", "Valor Total (R$)"], ascending=[True, False]
    )

    # ===== ABA 9: RANKING POSTOS (MELHORADO) =====
    # Seção A: Ranking Geral
    postos = (
        df_comb.groupby("Estabelecimento")
        .agg(
            {
                "Litragem": "sum",
                "Valor total": "sum",
                "Placa_Clean": "nunique",
                "Estado": lambda x: x.mode()[0]
                if len(x.mode()) > 0
                else x.iloc[0],  # Mais frequente
            }
        )
        .reset_index()
    )
    postos.columns = ["Posto", "Litros", "Valor Total (R$)", "Veículos", "Estado"]
    postos["Preço Médio/L"] = postos["Valor Total (R$)"] / postos["Litros"]

    # Calcular percentil de preço
    postos["Percentil Preço"] = (postos["Preço Médio/L"].rank(pct=True) * 100).round(1)

    # Flag de preço elevado (>10% acima da média)
    preco_medio_geral = postos["Valor Total (R$)"].sum() / postos["Litros"].sum()
    postos["Flag"] = postos["Preço Médio/L"].apply(
        lambda x: "PREÇO ELEVADO"
        if x > preco_medio_geral * 1.10
        else ("PREÇO BAIXO" if x < preco_medio_geral * 0.90 else "")
    )

    postos["Rank"] = range(1, len(postos) + 1)
    postos = postos[
        [
            "Rank",
            "Posto",
            "Estado",
            "Litros",
            "Valor Total (R$)",
            "Veículos",
            "Preço Médio/L",
            "Percentil Preço",
            "Flag",
        ]
    ]
    postos = postos.sort_values("Valor Total (R$)", ascending=False)

    # Seção B: Por Estado
    postos_por_estado = (
        df_comb.groupby(["Estado", "Estabelecimento"])
        .agg({"Litragem": "sum", "Valor total": "sum"})
        .reset_index()
    )
    postos_por_estado.columns = ["Estado", "Posto", "Litros", "Valor Total (R$)"]
    postos_por_estado["Preço Médio/L"] = (
        postos_por_estado["Valor Total (R$)"] / postos_por_estado["Litros"]
    )
    postos_por_estado = postos_por_estado.sort_values(
        ["Estado", "Valor Total (R$)"], ascending=[True, False]
    )

    # Seção C: Por Tipo de Combustível
    postos_por_tipo = (
        df_comb.groupby(["Combustivel", "Estabelecimento", "Estado"])
        .agg({"Litragem": "sum", "Valor total": "sum"})
        .reset_index()
    )
    postos_por_tipo.columns = [
        "Tipo Combustível",
        "Posto",
        "Estado",
        "Litros",
        "Valor Total (R$)",
    ]
    postos_por_tipo["Preço Médio/L"] = (
        postos_por_tipo["Valor Total (R$)"] / postos_por_tipo["Litros"]
    )
    postos_por_tipo = postos_por_tipo.sort_values(
        ["Tipo Combustível", "Valor Total (R$)"], ascending=[True, False]
    )

    # ===== ABA 10: ANÁLISE FROTA (NOVA) =====
    # Seção A: Custo por Grupo de Veículo
    analise_por_grupo = (
        custo_por_placa.groupby("Grupo")
        .agg(
            {
                "Placa": "count",
                "Combustível (R$)": "sum",
                "Manutenção (R$)": "sum",
                "TOTAL (R$)": "sum",
            }
        )
        .reset_index()
    )
    analise_por_grupo.columns = [
        "Grupo",
        "Veículos com Custo",
        "Combustível (R$)",
        "Manutenção (R$)",
        "Total (R$)",
    ]

    # Veículos na frota por grupo
    if len(df_frota) > 0:
        veiculos_frota_grupo = (
            df_frota.groupby("Grupo").size().reset_index(name="Veículos Frota")
        )
        analise_por_grupo = pd.merge(
            veiculos_frota_grupo, analise_por_grupo, on="Grupo", how="left"
        )
        analise_por_grupo["Veículos com Custo"] = (
            analise_por_grupo["Veículos com Custo"].fillna(0).astype(int)
        )
        analise_por_grupo["Combustível (R$)"] = analise_por_grupo[
            "Combustível (R$)"
        ].fillna(0)
        analise_por_grupo["Manutenção (R$)"] = analise_por_grupo[
            "Manutenção (R$)"
        ].fillna(0)
        analise_por_grupo["Total (R$)"] = analise_por_grupo["Total (R$)"].fillna(0)
    else:
        analise_por_grupo["Veículos Frota"] = analise_por_grupo["Veículos com Custo"]

    analise_por_grupo["Média por Veículo"] = (
        analise_por_grupo["Total (R$)"] / analise_por_grupo["Veículos com Custo"]
    )
    analise_por_grupo["Média Combustível/Veículo"] = (
        analise_por_grupo["Combustível (R$)"] / analise_por_grupo["Veículos com Custo"]
    )
    analise_por_grupo["Média Manutenção/Veículo"] = (
        analise_por_grupo["Manutenção (R$)"] / analise_por_grupo["Veículos com Custo"]
    )
    analise_por_grupo = analise_por_grupo.fillna(0)
    analise_por_grupo = analise_por_grupo.sort_values("Total (R$)", ascending=False)

    # Seção B: Top 10 Veículos Mais Caros
    top10_caros = custo_por_placa.head(10)[
        [
            "Placa",
            "Grupo",
            "Modelo Simplificado",
            "Filial",
            "Combustível (R$)",
            "Manutenção (R$)",
            "TOTAL (R$)",
        ]
    ].copy()
    top10_caros.insert(0, "Rank", range(1, len(top10_caros) + 1))

    # Seção C: Custo por Modelo Simplificado
    custo_por_modelo = (
        custo_por_placa.groupby(["Modelo Simplificado", "Grupo"])
        .agg(
            {
                "Placa": "count",
                "Combustível (R$)": "sum",
                "Manutenção (R$)": "sum",
                "TOTAL (R$)": "sum",
            }
        )
        .reset_index()
    )
    custo_por_modelo.columns = [
        "Modelo Simplificado",
        "Grupo",
        "Veículos",
        "Combustível (R$)",
        "Manutenção (R$)",
        "Total (R$)",
    ]
    custo_por_modelo["Média por Veículo"] = (
        custo_por_modelo["Total (R$)"] / custo_por_modelo["Veículos"]
    )
    custo_por_modelo = custo_por_modelo.sort_values(
        "Média por Veículo", ascending=False
    )

    # Seção D: Veículos com Custo SEM Registro na Frota
    placas_com_custo_set = set(custo_por_placa["Placa"].unique())
    placas_frota_set = (
        set(df_frota["Placa_Clean"].unique()) if len(df_frota) > 0 else set()
    )
    placas_sem_frota = placas_com_custo_set - placas_frota_set

    veiculos_sem_frota = custo_por_placa[
        custo_por_placa["Placa"].isin(placas_sem_frota)
    ][["Placa", "Filial", "Combustível (R$)", "Manutenção (R$)"]].sort_values("Filial")

    # ==================== GERAR EXCEL ====================
    print("\n📝 Gerando arquivo Excel...")

    # Criar diretório de saída
    caminho_saida = os.path.join(config.DIRETORIO_BASE_SAIDA, config.MES)
    os.makedirs(caminho_saida, exist_ok=True)

    # Nome do arquivo
    nome_arquivo = (
        f"Relatorio KPIs {config.MES} {config.ANO} - Combustivel e Manutencao.xlsx"
    )
    caminho_completo = os.path.join(caminho_saida, nome_arquivo)

    # Salvar Excel com múltiplas abas
    with pd.ExcelWriter(caminho_completo, engine="openpyxl") as writer:
        # Aba 1: Resumo Geral
        resumo_geral.to_excel(writer, sheet_name="Resumo Geral", index=False)

        # Aba 2: Combustível por Tipo
        combustivel_por_tipo.to_excel(
            writer, sheet_name="Combustível por Tipo", index=False
        )

        # Aba 3: Combustível por Filial (com sub-tabela)
        combustivel_por_filial.to_excel(
            writer, sheet_name="Combustível por Filial", index=False, startrow=0
        )
        startrow_subtabela = len(combustivel_por_filial) + 3
        combustivel_filial_grupo.to_excel(
            writer,
            sheet_name="Combustível por Filial",
            index=False,
            startrow=startrow_subtabela,
        )

        # Aba 4: Manutenção por Natureza
        manut_por_natureza.to_excel(
            writer, sheet_name="Manutenção por Natureza", index=False
        )

        # Aba 5: Manutenção por Filial
        manut_por_filial.to_excel(
            writer, sheet_name="Manutenção por Filial", index=False
        )

        # Aba 6: Manutenção por GrupoDespesa
        if len(manut_por_grupo_despesa) > 0:
            manut_por_grupo_despesa.to_excel(
                writer, sheet_name="Manut por GrupoDespesa", index=False
            )

        # Aba 7: Custo por Placa
        custo_por_placa.to_excel(writer, sheet_name="Custo por Placa", index=False)

        # Aba 8: Combustível por Região (multi-seção)
        comb_por_estado.to_excel(
            writer, sheet_name="Comb por Região", index=False, startrow=0
        )
        startrow_tipo = len(comb_por_estado) + 3
        comb_estado_tipo.to_excel(
            writer, sheet_name="Comb por Região", index=False, startrow=startrow_tipo
        )

        # Aba 9: Ranking Postos (multi-seção)
        postos.to_excel(writer, sheet_name="Ranking Postos", index=False, startrow=0)
        startrow_estado = len(postos) + 3
        postos_por_estado.to_excel(
            writer, sheet_name="Ranking Postos", index=False, startrow=startrow_estado
        )
        startrow_tipo_postos = startrow_estado + len(postos_por_estado) + 3
        postos_por_tipo.to_excel(
            writer,
            sheet_name="Ranking Postos",
            index=False,
            startrow=startrow_tipo_postos,
        )

        # Aba 10: Análise Frota (multi-seção)
        analise_por_grupo.to_excel(
            writer, sheet_name="Análise Frota", index=False, startrow=0
        )
        startrow_top10 = len(analise_por_grupo) + 3
        top10_caros.to_excel(
            writer, sheet_name="Análise Frota", index=False, startrow=startrow_top10
        )
        startrow_modelo = startrow_top10 + len(top10_caros) + 3
        custo_por_modelo.to_excel(
            writer, sheet_name="Análise Frota", index=False, startrow=startrow_modelo
        )
        startrow_sem_frota = startrow_modelo + len(custo_por_modelo) + 3
        if len(veiculos_sem_frota) > 0:
            veiculos_sem_frota.to_excel(
                writer,
                sheet_name="Análise Frota",
                index=False,
                startrow=startrow_sem_frota,
            )

    # Aplicar formatação
    print("   🎨 Aplicando formatação...")
    wb = load_workbook(caminho_completo)

    cores = [
        "0070C0",
        "FF6600",
        "339933",
        "9933FF",
        "CC0066",
        "336699",
        "FF3366",
        "00B0F0",
        "C00000",
        "70AD47",
    ]
    for idx, sheet_name in enumerate(wb.sheetnames):
        ws = wb[sheet_name]
        formatar_aba(ws, cores[idx % len(cores)])

    wb.save(caminho_completo)

    # ==================== RESUMO FINAL ====================
    print("\n" + "=" * 80)
    print("🎉 RELATÓRIO DE KPIs GERADO COM SUCESSO!")
    print("=" * 80)
    print(f"\n📁 Arquivo: {caminho_completo}")
    print(f"\n📊 Conteúdo (10 abas):")
    print(
        f"   1. Resumo Geral (expandido com grupos, tipos de combustível e manutenção)"
    )
    print(f"   2. Combustível por Tipo (+ estados e cidades atendidos)")
    print(f"   3. Combustível por Filial (+ por tipo + por grupo)")
    print(f"   4. Manutenção por Natureza")
    print(f"   5. Manutenção por Filial")
    print(f"   6. Manutenção por GrupoDespesa (21 categorias)")
    print(f"   7. Custo por Placa (+ grupo e modelo)")
    print(f"   8. Combustível por Região (estado + cidade + tipo)")
    print(f"   9. Ranking Postos (+ por estado + por tipo + análise de preços)")
    print(f"  10. Análise Frota (por grupo + top 10 + por modelo + sem registro)")
    print("\n" + "=" * 80)

    return caminho_completo


if __name__ == "__main__":
    gerar_relatorio_kpis()
