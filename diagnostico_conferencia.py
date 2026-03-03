"""
Script de Diagnóstico e Conferência - FKMs
Identifica anomalias e padrões suspeitos nos dados de combustível e manutenção

Verificações:
A - Garagem vs Filial de Manutenção (divergências)
B - REFERÊNCIA indevida no Combustível (garagem não pode ser REFERÊNCIA, exceto TBU9D20)
C - Veículos multi-filial (possível transferência/empréstimo)
D - Hodômetros suspeitos
"""

import os
import sys

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

import config
from filial_mapping import normalizar_filial


# ==================== MAPEAMENTO FILIAL → ESTADO ESPERADO ====================
# Usado na Verificação D para detectar abastecimentos fora da região

FILIAL_ESTADO_ESPERADO = {
    "GRITSCH - BLN": ["SC"],            # Blumenau - SC
    "GRITSCH - BSB": ["DF", "GO"],      # Brasília - DF (pode abastecer em GO)
    "GRITSCH - CBL": ["GO"],            # Campos Belos - GO
    "GRITSCH - CGB": ["MT"],            # Cuiabá - MT
    "GRITSCH - CGR": ["MS"],            # Campo Grande - MS
    "GRITSCH - CHA": ["SC"],            # Chapecó - SC
    "GRITSCH - CRI": ["SC"],            # Criciúma - SC
    "GRITSCH - CSC": ["SC"],            # Centro SC
    "GRITSCH - CTB": ["PR"],            # Curitiba - PR
    "GRITSCH - CWB (BASE)": ["PR"],     # Curitiba Base - PR
    "GRITSCH - CWB (DIR)": ["PR"],      # Curitiba Diretoria - PR
    "GRITSCH - CXJ": ["RS"],            # Caxias do Sul - RS
    "GRITSCH - FLN": ["SC"],            # Florianópolis - SC
    "GRITSCH - GOI": ["GO"],            # Goiânia - GO
    "GRITSCH - GPA": ["PR"],            # Guarapuava - PR
    "GRITSCH - JOI": ["SC"],            # Joinville - SC
    "GRITSCH - LDB": ["PR"],            # Londrina - PR
    "GRITSCH - MATRIZ": ["PR"],         # Matriz - PR
    "GRITSCH - MGA": ["PR"],            # Maringá - PR
    "GRITSCH - PBC": ["PR"],            # Ponta Grossa/PBC - PR
    "GRITSCH - PGR": ["PR"],            # Paranaguá? - PR
    "GRITSCH - PMW": ["TO"],            # Palmas - TO
    "GRITSCH - POA": ["RS"],            # Porto Alegre - RS
    "GRITSCH - RDN": ["RO"],            # Rondônia - RO
    "GRITSCH - RVD": ["MT"],            # Rondonópolis? - MT
    "GRITSCH - SAO PERUS": ["SP"],      # São Paulo - SP
    "GRITSCH - SNO": ["SP"],            # Sorocaba/SP? - SP
    "GRITSCH - SSA": ["BA"],            # Salvador - BA
}


def carregar_dados():
    """Carrega e prepara os dados de combustível e manutenção"""
    print("=" * 80)
    print(f"DIAGNÓSTICO DE CONFERÊNCIA - {config.MES}/{config.ANO}")
    print("=" * 80)

    # Combustível
    arq_comb = config.ARQUIVO_ENTRADA_COMBUSTIVEL
    if not arq_comb or not os.path.exists(arq_comb):
        print(f"❌ Arquivo de combustível não encontrado: {arq_comb}")
        sys.exit(1)

    print(f"\n📁 Carregando combustível: {arq_comb}")
    df_comb = pd.read_excel(arq_comb)

    # Normalizar placas
    df_comb["Placa_Clean"] = (
        df_comb["Placa"]
        .astype(str)
        .str.replace("-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    # Normalizar garagem
    if "Garagem" in df_comb.columns:
        df_comb["Garagem"] = df_comb["Garagem"].apply(normalizar_filial)

    print(f"   ✅ {len(df_comb)} registros de combustível carregados")
    print(f"   📊 {df_comb['Placa_Clean'].nunique()} placas únicas")

    # Manutenção
    arq_manut = config.ARQUIVO_ENTRADA_MANUTENCAO
    if not arq_manut or not os.path.exists(arq_manut):
        print(f"❌ Arquivo de manutenção não encontrado: {arq_manut}")
        sys.exit(1)

    print(f"\n📁 Carregando manutenção: {arq_manut}")
    df_manut = pd.read_excel(arq_manut)

    # Normalizar placas
    df_manut["Placa_Clean"] = (
        df_manut["Placa"]
        .astype(str)
        .str.replace("-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    # Normalizar filial
    if "FILIAL" in df_manut.columns:
        df_manut["FILIAL"] = df_manut["FILIAL"].apply(normalizar_filial)

    print(f"   ✅ {len(df_manut)} registros de manutenção carregados")
    print(f"   📊 {df_manut['Placa_Clean'].nunique()} placas únicas")

    return df_comb, df_manut


# ==================== VERIFICAÇÃO A ====================
def verificar_garagem_vs_filial(df_comb, df_manut):
    """
    Verifica divergências entre Garagem (combustível) e FILIAL (manutenção).
    Identifica veículos que abastecem em uma garagem mas fazem manutenção em outra filial.
    Pode indicar: transferência não registrada, empréstimo, ou dado incorreto.
    """
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO A: Garagem (Combustível) vs FILIAL (Manutenção)")
    print("=" * 80)

    # Para cada placa, pegar a filial mais frequente na manutenção
    filial_por_placa = (
        df_manut.groupby("Placa_Clean")["FILIAL"]
        .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None)
        .to_dict()
    )

    # Para cada placa, pegar a garagem mais frequente no combustível
    garagem_por_placa = (
        df_comb.groupby("Placa_Clean")["Garagem"]
        .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None)
        .to_dict()
    )

    # Cruzar
    resultados = []
    for placa in set(filial_por_placa.keys()) & set(garagem_por_placa.keys()):
        filial_manut = filial_por_placa[placa]
        garagem_comb = garagem_por_placa[placa]

        if pd.isna(filial_manut) or pd.isna(garagem_comb):
            continue

        # Normalizar para comparação
        filial_norm = str(filial_manut).strip().upper()
        garagem_norm = str(garagem_comb).strip().upper()

        if filial_norm != garagem_norm:
            # Contar abastecimentos e manutenções
            qtd_abast = len(df_comb[df_comb["Placa_Clean"] == placa])
            qtd_manut = len(df_manut[df_manut["Placa_Clean"] == placa])

            # Pegar todas as garagens distintas nos abastecimentos
            garagens_usadas = df_comb[df_comb["Placa_Clean"] == placa]["Garagem"].unique()
            garagens_str = " | ".join([str(g) for g in garagens_usadas if pd.notna(g)])

            # Pegar todas as filiais distintas na manutenção
            filiais_usadas = df_manut[df_manut["Placa_Clean"] == placa]["FILIAL"].unique()
            filiais_str = " | ".join([str(f) for f in filiais_usadas if pd.notna(f)])

            resultados.append({
                "Placa": placa,
                "Garagem (Combustível)": garagem_comb,
                "Filial (Manutenção)": filial_manut,
                "Todas Garagens": garagens_str,
                "Todas Filiais Manut.": filiais_str,
                "Qtd Abastecimentos": qtd_abast,
                "Qtd Manutenções": qtd_manut,
            })

    df_result = pd.DataFrame(resultados)
    if len(df_result) > 0:
        df_result = df_result.sort_values("Placa").reset_index(drop=True)

    print(f"   🔍 {len(df_result)} placas com divergência Garagem ≠ Filial Manutenção")
    return df_result


# ==================== VERIFICAÇÃO B ====================
def verificar_referencia_indevida(df_comb, df_manut):
    """
    Identifica placas com Garagem REFERÊNCIA no COMBUSTÍVEL.
    A Garagem do combustível NÃO pode ser REFERÊNCIA (exceto TBU9D20 → REFERÊNCIA CURITIBA).
    Na manutenção, REFERÊNCIA é normal e esperado.
    """
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO B: REFERÊNCIA Indevida no Combustível")
    print("=" * 80)

    # Verificar no COMBUSTÍVEL (coluna Garagem)
    mask_ref = df_comb["Garagem"].str.contains(
        "REFERÊNCIA|REFERENCIA", case=False, na=False
    )
    mask_excecao = df_comb["Placa_Clean"].str.contains("TBU9D20", case=False, na=False)

    df_ref_indevida = df_comb[mask_ref & ~mask_excecao].copy()

    if len(df_ref_indevida) > 0:
        # Resumo por placa + garagem
        resumo = (
            df_ref_indevida.groupby(["Placa_Clean", "Garagem"])
            .agg(
                Qtd_Abastecimentos=("Placa", "count"),
                Valor_Total=("Valor total", "sum"),
                Litragem_Total=("Litragem", "sum"),
            )
            .reset_index()
        )
        resumo.columns = [
            "Placa", "Garagem REFERÊNCIA", "Qtd Abastecimentos",
            "Valor Total (R$)", "Litragem Total"
        ]

        # Adicionar filial da manutenção para contexto
        filial_map = (
            df_manut.groupby("Placa_Clean")["FILIAL"]
            .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "N/A")
            .to_dict()
        )
        resumo["Filial na Manutenção"] = resumo["Placa"].map(filial_map).fillna("Sem manutenção")

        resumo = resumo.sort_values("Qtd Abastecimentos", ascending=False).reset_index(drop=True)
    else:
        resumo = pd.DataFrame(columns=[
            "Placa", "Garagem REFERÊNCIA", "Qtd Abastecimentos",
            "Valor Total (R$)", "Litragem Total", "Filial na Manutenção"
        ])

    print(f"   🔍 {len(resumo)} placas com Garagem REFERÊNCIA no combustível (excluindo TBU9D20)")

    if len(resumo) > 0:
        print("\n   ⚠️  ATENÇÃO: Garagem de combustível NÃO pode ser REFERÊNCIA!")
        for _, row in resumo.head(10).iterrows():
            print(f"      {row['Placa']} → {row['Garagem REFERÊNCIA']} ({row['Qtd Abastecimentos']} abastecimentos)")

    return resumo


# ==================== VERIFICAÇÃO C ====================
def verificar_multi_filial(df_manut, df_comb):
    """
    Identifica veículos com manutenção em mais de uma filial.
    Pode indicar transferência entre filiais ou empréstimo de veículo.
    Mostra também a Garagem do combustível para ajudar na alocação.
    """
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO C: Veículos Multi-Filial (Manutenção)")
    print("=" * 80)

    # Filtrar REFERÊNCIA para não poluir a análise
    df_sem_ref = df_manut[
        ~df_manut["FILIAL"].str.contains("REFERÊNCIA|REFERENCIA", case=False, na=False)
    ].copy()

    # Contar filiais por placa
    filiais_por_placa = df_sem_ref.groupby("Placa_Clean")["FILIAL"].nunique()
    placas_multi = filiais_por_placa[filiais_por_placa > 1].index

    # Mapa de garagem do combustível
    garagem_map = (
        df_comb.groupby("Placa_Clean")["Garagem"]
        .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "N/A")
        .to_dict()
    )

    resultados = []
    for placa in placas_multi:
        df_placa = df_sem_ref[df_sem_ref["Placa_Clean"] == placa]
        filiais = df_placa["FILIAL"].unique()
        
        # Para cada filial, pegar detalhes
        detalhes = []
        for filial in filiais:
            df_fil = df_placa[df_placa["FILIAL"] == filial]
            qtd = len(df_fil)
            valor = df_fil["ValorTotal"].sum() if "ValorTotal" in df_fil.columns else 0
            if "DataEmissao" in df_fil.columns:
                datas = pd.to_datetime(df_fil["DataEmissao"], format="mixed", errors="coerce")
                data_min = datas.min()
                data_max = datas.max()
                data_min_str = data_min.strftime("%d/%m") if pd.notna(data_min) else "?"
                data_max_str = data_max.strftime("%d/%m") if pd.notna(data_max) else "?"
                periodo = f"{data_min_str} a {data_max_str}"
            else:
                periodo = "s/data"
            detalhes.append(f"{filial} ({qtd} reg, R${valor:,.0f}, {periodo})")

        # Garagem no combustível
        garagem = garagem_map.get(placa, "Sem abastecimento")

        # Qtd abastecimentos
        qtd_abast = len(df_comb[df_comb["Placa_Clean"] == placa])

        resultados.append({
            "Placa": placa,
            "Garagem (Combustível)": garagem,
            "Qtd Abastecimentos": qtd_abast,
            "Qtd Filiais Manut.": len(filiais),
            "Filiais": " | ".join([str(f) for f in filiais]),
            "Detalhamento": " || ".join(detalhes),
        })

    df_result = pd.DataFrame(resultados)
    if len(df_result) > 0:
        df_result = df_result.sort_values("Qtd Filiais Manut.", ascending=False).reset_index(drop=True)

    print(f"   🔍 {len(df_result)} placas com manutenção em múltiplas filiais")
    if len(df_result) > 0:
        for _, row in df_result.iterrows():
            print(f"      {row['Placa']} | Garagem: {row['Garagem (Combustível)']} | Manut: {row['Filiais']}")
    return df_result


# ==================== VERIFICAÇÃO D ====================
def verificar_hodometros(df_comb):
    """
    Detecta hodômetros suspeitos:
    - Regressão (hodômetro atual < anterior)
    - Saltos muito grandes (>15.000 km entre abastecimentos consecutivos)
    """
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO D: Hodômetros Suspeitos")
    print("=" * 80)

    col_hod = "Hodometro/Horimetro"
    col_hod_ant = "Hodometro/Horimetro anterior"

    if col_hod not in df_comb.columns or col_hod_ant not in df_comb.columns:
        print("   ⚠️  Colunas de hodômetro não encontradas")
        return pd.DataFrame()

    resultados = []

    for placa, df_placa in df_comb.groupby("Placa_Clean"):
        if placa in ("", "NAN", "NONE"):
            continue

        df_placa = df_placa.copy()

        # Converter hodômetros
        df_placa[col_hod] = pd.to_numeric(df_placa[col_hod], errors="coerce")
        df_placa[col_hod_ant] = pd.to_numeric(df_placa[col_hod_ant], errors="coerce")

        # Verificar regressão (hodômetro atual < anterior no mesmo registro)
        mask_regressao = (df_placa[col_hod] < df_placa[col_hod_ant]) & df_placa[col_hod].notna() & df_placa[col_hod_ant].notna()
        regressoes = mask_regressao.sum()

        # Verificar Percorrido suspeito se existir
        if "Percorrido" in df_placa.columns:
            df_placa["Percorrido_num"] = pd.to_numeric(df_placa["Percorrido"], errors="coerce")
            saltos = (df_placa["Percorrido_num"].abs() > 15000).sum()
        else:
            # Calcular manualmente
            df_placa["Percorrido_calc"] = df_placa[col_hod] - df_placa[col_hod_ant]
            saltos = (df_placa["Percorrido_calc"].abs() > 15000).sum()

        if regressoes > 0 or saltos > 0:
            garagem = df_placa["Garagem"].mode().iloc[0] if len(df_placa["Garagem"].mode()) > 0 else "N/A"
            
            # Pegar exemplos de regressão
            exemplos = ""
            if regressoes > 0:
                df_reg = df_placa[mask_regressao].head(2)
                for _, row in df_reg.iterrows():
                    data = row.get("Data da transacao", "s/data")
                    exemplos += f"[{data}] Hod: {row[col_hod_ant]:.0f} → {row[col_hod]:.0f}; "

            resultados.append({
                "Placa": placa,
                "Garagem": garagem,
                "Regressões": regressoes,
                "Saltos >15.000km": saltos,
                "Qtd Abastecimentos": len(df_placa),
                "Exemplos": exemplos[:150] if exemplos else "",
            })

    df_result = pd.DataFrame(resultados)
    if len(df_result) > 0:
        df_result = df_result.sort_values("Regressões", ascending=False).reset_index(drop=True)

    total_problemas = len(df_result)
    print(f"   🔍 {total_problemas} placas com hodômetros suspeitos")

    return df_result


# ==================== SALVAR RELATÓRIO ====================
def salvar_relatorio(resultados, caminho_saida):
    """Salva o relatório de diagnóstico como Excel formatado"""
    print("\n" + "=" * 80)
    print("SALVANDO RELATÓRIO DE DIAGNÓSTICO")
    print("=" * 80)

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        # Resumo geral
        resumo_data = []
        nomes_abas = {
            "A_Garagem_vs_Filial": "A - Garagem vs Filial",
            "B_Referencia_Combustivel": "B - REFERÊNCIA Combustível",
            "C_Multi_Filial": "C - Multi-Filial",
            "D_Hodometros": "D - Hodômetros",
        }

        for chave, (titulo, df) in zip(nomes_abas.keys(), resultados):
            qtd = len(df)
            status = "✅ OK" if qtd == 0 else f"⚠️ {qtd} anomalia(s)"
            resumo_data.append({
                "Verificação": titulo,
                "Resultado": status,
                "Qtd Anomalias": qtd,
            })

            # Salvar aba de detalhamento
            nome_aba = chave[:31]  # Limite do Excel
            if len(df) > 0:
                df.to_excel(writer, sheet_name=nome_aba, index=False)
            else:
                pd.DataFrame({"Resultado": ["Nenhuma anomalia encontrada ✅"]}).to_excel(
                    writer, sheet_name=nome_aba, index=False
                )

        # Salvar aba de resumo
        df_resumo = pd.DataFrame(resumo_data)
        df_resumo.to_excel(writer, sheet_name="RESUMO", index=False)

    # Formatação
    wb = load_workbook(caminho_saida)

    # Formatar aba RESUMO
    ws = wb["RESUMO"]
    cor_header = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid")
    fonte_header = Font(bold=True, color="FFFFFF", size=12)
    fonte_negrito = Font(bold=True)
    alinhamento = Alignment(horizontal="center", vertical="center")

    for col in range(1, ws.max_column + 1):
        cell = ws.cell(1, col)
        cell.fill = cor_header
        cell.font = fonte_header
        cell.alignment = alinhamento

    # Colorir resultados
    cor_ok = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    cor_warn = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    for row in range(2, ws.max_row + 1):
        resultado = ws.cell(row, 2).value
        cor = cor_ok if "OK" in str(resultado) else cor_warn
        for col in range(1, ws.max_column + 1):
            ws.cell(row, col).fill = cor

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 18

    # Formatar abas de detalhamento
    for sheet_name in wb.sheetnames:
        if sheet_name == "RESUMO":
            continue
        ws = wb[sheet_name]
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(1, col)
            cell.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
            cell.font = Font(bold=True)
            cell.alignment = alinhamento

        # Auto-ajustar largura
        for col_idx in range(1, ws.max_column + 1):
            max_len = 0
            col_letter = ws.cell(1, col_idx).column_letter
            for row in range(1, min(ws.max_row + 1, 50)):
                val = ws.cell(row, col_idx).value
                if val:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[col_letter].width = min(max_len + 4, 60)

    wb.save(caminho_saida)
    print(f"\n✅ Relatório salvo em: {caminho_saida}")


# ==================== EXECUÇÃO PRINCIPAL ====================
if __name__ == "__main__":
    # Carregar dados
    df_comb, df_manut = carregar_dados()

    # Executar verificações
    print("\n🔍 Iniciando verificações de conferência...\n")

    res_a = verificar_garagem_vs_filial(df_comb, df_manut)
    res_b = verificar_referencia_indevida(df_comb, df_manut)
    res_c = verificar_multi_filial(df_manut, df_comb)
    res_d = verificar_hodometros(df_comb)

    # Agrupar resultados
    resultados = [
        ("A - Garagem vs Filial", res_a),
        ("B - REFERÊNCIA Combustível", res_b),
        ("C - Multi-Filial", res_c),
        ("D - Hodômetros", res_d),
    ]

    # Resumo no terminal
    print("\n" + "=" * 80)
    print("📊 RESUMO DO DIAGNÓSTICO")
    print("=" * 80)
    for titulo, df in resultados:
        qtd = len(df)
        emoji = "✅" if qtd == 0 else "⚠️ "
        print(f"   {emoji} {titulo}: {qtd} anomalia(s)")

    # Salvar relatório
    mes_num = config.obter_numero_mes()
    ano_short = config.ANO[-2:]
    nome_arquivo = f"DIAGNOSTICO_{mes_num}{ano_short}_{config.MES}_{config.ANO}.xlsx"
    caminho_saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome_arquivo)

    salvar_relatorio(resultados, caminho_saida)

    print("\n" + "=" * 80)
    print("🎉 DIAGNÓSTICO CONCLUÍDO!")
    print("=" * 80)
    print(f"\n📁 Abra o arquivo para ver os detalhes: {nome_arquivo}")
