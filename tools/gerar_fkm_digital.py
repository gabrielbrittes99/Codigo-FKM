"""
Gerador de FKM Digital por Filial.

Gera um arquivo .xls pré-preenchido por filial por mês, usando o template
existente em modelos FKM/. O gestor só precisa preencher: Contrato (col G),
Tipo de Rota (col F), Roteiro Principal (col H), Motorista Principal (col I),
Rastreador (col W), fundo fixo e abastecimento por fora.

Lookup de Grupo e Modelo_Padrão é feito por Modelo_Original do BlueFleet
via dados/mapa_modelo.csv — qualquer placa nova com modelo conhecido é
classificada automaticamente sem precisar atualizar uma lista de placas.
"""

import os
import csv

import pandas as pd
import xlrd
from xlutils.copy import copy as xl_copy

from src import config
from tools.validar_retorno_fkms import MAPA_FILIAIS_NOME_PASTA

def carregar_dados_oficiais(folder_name):
    """Carrega dados oficiais de frota, combustível e manutenção da filial."""
    branch_dir = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO, folder_name)
    filial_acronym = folder_name.replace(" - ", "  ")
    
    caminho_frota = os.path.join(branch_dir, f"Frota - {filial_acronym}.xlsx")
    caminho_comb = os.path.join(branch_dir, f"Combustivel - {filial_acronym}.xlsx")
    caminho_manut = os.path.join(branch_dir, f"Manutencao - {filial_acronym}.xlsx")
    
    df_frota = pd.read_excel(caminho_frota) if os.path.exists(caminho_frota) else pd.DataFrame(columns=["Placa"])
    df_comb = pd.read_excel(caminho_comb) if os.path.exists(caminho_comb) else pd.DataFrame(columns=["Placa", "Hodometro/Horimetro", "Hodometro/Horimetro anterior", "Data da transacao"])
    df_manut = pd.read_excel(caminho_manut) if os.path.exists(caminho_manut) else pd.DataFrame(columns=["Placa", "ValorTotal"])
    
    df_frota["Placa_Clean"] = df_frota["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    df_comb["Placa_Clean"] = df_comb["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    df_manut["Placa_Clean"] = df_manut["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    
    return df_frota, df_comb, df_manut

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELOS_DIR = os.path.join(PROJECT_ROOT, "modelos FKM")
MAPA_MODELO_CSV = os.path.join(PROJECT_ROOT, "dados", "mapa_modelo.csv")

# Colunas de fórmula que não devem ser escritas
FORMULA_COLS = {11, 14, 15, 20, 21}


def carregar_mapa_modelo():
    """
    Carrega dados/mapa_modelo.csv → dict keyed by Modelo_Original.upper().
    Retorna {modelo_upper: {'Modelo_Padrao': ..., 'Grupo': ...}}
    """
    mapa = {}
    if not os.path.exists(MAPA_MODELO_CSV):
        print(f"⚠️  mapa_modelo.csv não encontrado em {MAPA_MODELO_CSV}")
        return mapa
    with open(MAPA_MODELO_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            chave = row["Modelo_Original"].strip().upper()
            mapa[chave] = {
                "Modelo_Padrao": row["Modelo_Padrao"].strip(),
                "Grupo": row["Grupo"].strip(),
            }
    return mapa


def normalizar_tipo_comb(tipo):
    t = str(tipo).strip().upper()
    if t in ("DIESEL", "DIESEL S10", "DIESEL S500"):
        return "Diesel"
    if t in ("GASOLINA", "GASOLINA ADITIVADA", "GASOLINA COMUM"):
        return "Gasolina"
    if t in ("ALCOOL", "ÁLCOOL", "ETANOL", "FLEX"):
        return "Álcool"
    return tipo.strip().title()


def agregar_combustivel(df_comb):
    """
    Agrega dados de combustível por placa (excluindo Arla).
    Retorna dict {placa: {Litros, Valor_Comb, Km_Ini, Km_Fim, Tipo_Comb, Arla_Valor}}
    """
    if df_comb.empty:
        return {}

    mask_arla = df_comb["Combustivel"].str.contains("Arla", case=False, na=False)
    df_regular = df_comb[~mask_arla].copy()
    df_arla = df_comb[mask_arla].copy()

    result = {}

    if "Data da transacao" in df_regular.columns:
        df_sorted = df_regular.sort_values("Data da transacao")
    else:
        df_sorted = df_regular

    for placa, grp in df_sorted.groupby("Placa_Clean"):
        km_ini_vals = grp["Hodometro/Horimetro anterior"].dropna()
        km_fim_vals = grp["Hodometro/Horimetro"].dropna()
        km_ini = int(km_ini_vals.iloc[0]) if not km_ini_vals.empty else None
        km_fim = int(km_fim_vals.iloc[-1]) if not km_fim_vals.empty else None

        litros = grp["Litragem"].sum() if "Litragem" in grp.columns else 0
        valor_comb = grp["Valor total"].sum() if "Valor total" in grp.columns else 0

        tipo_comb = ""
        if "Combustivel" in grp.columns and "Litragem" in grp.columns:
            por_tipo = grp.groupby("Combustivel")["Litragem"].sum()
            if not por_tipo.empty:
                tipo_comb = normalizar_tipo_comb(por_tipo.idxmax())

        result[placa] = {
            "Litros": round(litros, 2),
            "Valor_Comb": round(valor_comb, 2),
            "Km_Ini": km_ini,
            "Km_Fim": km_fim,
            "Tipo_Comb": tipo_comb,
            "Arla_Valor": 0,
        }

    if not df_arla.empty and "Valor total" in df_arla.columns:
        for placa, grp in df_arla.groupby("Placa_Clean"):
            if placa not in result:
                result[placa] = {"Litros": 0, "Valor_Comb": 0, "Km_Ini": None, "Km_Fim": None, "Tipo_Comb": "", "Arla_Valor": 0}
            result[placa]["Arla_Valor"] = round(grp["Valor total"].sum(), 2)

    return result


def agregar_manutencao(df_manut):
    """
    Agrega manutenção por placa em três categorias:
    Lataria (03.02/LATARIA), Rodas/Pneus (03.05/RODAS), Manut_Geral (resto).
    """
    result = {}
    if df_manut.empty or "ValorTotal" not in df_manut.columns:
        return result

    col_nat = "Natureza_Correta" if "Natureza_Correta" in df_manut.columns else (
        "TipoItem" if "TipoItem" in df_manut.columns else None
    )

    for _, row in df_manut.iterrows():
        placa = str(row.get("Placa_Clean", "")).strip()
        val = float(row.get("ValorTotal", 0) or 0)
        if not placa or val == 0:
            continue

        nat = str(row.get(col_nat, "") if col_nat else "").strip()

        if placa not in result:
            result[placa] = {"Lataria": 0, "Manut_Geral": 0, "Rodas_Pneus": 0}

        if "03.02" in nat or "LATARIA" in nat.upper():
            result[placa]["Lataria"] += val
        elif "03.05" in nat or "RODAS" in nat.upper():
            result[placa]["Rodas_Pneus"] += val
        else:
            result[placa]["Manut_Geral"] += val

    return result


def escrever_fkm(template_path, veiculos, pasta_saida, template_name, mes_ano_cod, periodo):
    """
    Abre o template .xls, encontra a aba FKm MMAA, escreve os dados dos veículos
    e salva em pasta_saida. Retorna o caminho do arquivo gerado.
    """
    rb = xlrd.open_workbook(template_path, formatting_info=True)
    wb = xl_copy(rb)

    sheet_idx = None
    mes_num_busca = mes_ano_cod[:2]

    for idx in range(rb.nsheets):
        name = rb.sheet_names()[idx]
        if "fkm" in name.lower() and mes_ano_cod in name:
            sheet_idx = idx
            break

    if sheet_idx is None:
        for idx in range(rb.nsheets):
            name = rb.sheet_names()[idx]
            if "fkm" in name.lower() and mes_num_busca in name and "resumo" not in name.lower():
                sheet_idx = idx
                break

    if sheet_idx is None:
        for idx in reversed(range(rb.nsheets)):
            if "fkm" in rb.sheet_names()[idx].lower():
                sheet_idx = idx
                break

    if sheet_idx is None:
        print(f"   ⚠️  Aba FKm não encontrada em {os.path.basename(template_path)}")
        return None

    ws = wb.get_sheet(sheet_idx)

    for r, vei in enumerate(veiculos, start=4):
        col_values = {
            0: vei.get("Modelo_Padrao") or "",
            1: vei.get("Grupo") or "",
            2: vei.get("Placa") or "",
            3: vei.get("Montadora") or "",
            4: vei.get("Tipo_Comb") or "",
            9: vei.get("Km_Ini"),
            10: vei.get("Km_Fim"),
            12: vei.get("Litros") or 0,
            13: vei.get("Valor_Comb") or 0,
            16: vei.get("Arla_Valor") or 0,
            17: vei.get("Lataria") or 0,
            18: vei.get("Manut_Geral") or 0,
            19: vei.get("Rodas_Pneus") or 0,
            23: template_name,
            24: periodo,
        }

        for col, val in col_values.items():
            if col in FORMULA_COLS:
                continue
            if val is None or val == "":
                continue
            if isinstance(val, (int, float)) and val == 0 and col not in (12, 13, 16, 17, 18, 19):
                continue
            ws.write(r, col, val)

    cidade = template_name.replace("Gritsch ", "").strip()
    nome_arquivo = f"FKM {mes_ano_cod} Gritsch {cidade}.xls"
    os.makedirs(pasta_saida, exist_ok=True)
    caminho_saida = os.path.join(pasta_saida, nome_arquivo)
    wb.save(caminho_saida)
    return caminho_saida


def main():
    mes_num = config.obter_numero_mes()
    ano_short = config.ANO[-2:]
    mes_ano_cod = f"{mes_num}{ano_short}"
    periodo = f"{mes_num}/{config.ANO}"

    print("=" * 80)
    print(f"GERADOR DE FKM DIGITAL — {config.MES}/{config.ANO} ({mes_ano_cod})")
    print("=" * 80)

    mapa_modelo = carregar_mapa_modelo()
    print(f"✅ Mapa de modelos carregado: {len(mapa_modelo)} tipos")

    modelos_desconhecidos = set()
    folders_processados = {}

    for template_name, folder_name in MAPA_FILIAIS_NOME_PASTA.items():
        if folder_name in folders_processados:
            continue
        template_path = os.path.join(MODELOS_DIR, f"{template_name}.xls")
        if not os.path.exists(template_path):
            continue
        folders_processados[folder_name] = template_name

    total = len(folders_processados)
    print(f"✅ {total} filiais a processar\n")

    gerados = 0
    for idx, (folder_name, template_name) in enumerate(folders_processados.items(), 1):
        print(f"[{idx}/{total}] {template_name} ({folder_name})")

        template_path = os.path.join(MODELOS_DIR, f"{template_name}.xls")

        branch_dir = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO, folder_name)
        if not os.path.isdir(branch_dir):
            print(f"   ⚠️  Pasta de dados não encontrada: {branch_dir} — pulando")
            continue

        try:
            df_frota, df_comb, df_manut = carregar_dados_oficiais(folder_name)
        except Exception as e:
            print(f"   ⚠️  Erro ao carregar dados: {e} — pulando")
            continue

        comb_por_placa = agregar_combustivel(df_comb)
        manut_por_placa = agregar_manutencao(df_manut)

        # Filtrar apenas placas válidas (7 chars alfanuméricos) — exclui linha de totalização
        def _placa_valida(p):
            return len(p) == 7 and p.isalnum()

        placas_frota = set(
            p for p in df_frota["Placa_Clean"].dropna().unique() if _placa_valida(p)
        ) if not df_frota.empty else set()
        todas_placas = sorted(placas_frota | set(comb_por_placa) | set(manut_por_placa))

        frota_idx = {}
        if not df_frota.empty:
            for _, row in df_frota.iterrows():
                p = str(row.get("Placa_Clean", "")).strip()
                if _placa_valida(p):
                    frota_idx[p] = row

        veiculos = []
        for placa in todas_placas:
            frota_row = frota_idx.get(placa, {})
            modelo_bf = str(frota_row.get("Modelo", "") or "").strip()
            montadora = str(frota_row.get("Montadora", "") or "").strip()

            # Lookup por modelo (case-insensitive) — funciona para qualquer placa nova
            info_modelo = mapa_modelo.get(modelo_bf.upper(), {})
            modelo_padrao = info_modelo.get("Modelo_Padrao", "") or modelo_bf
            grupo = info_modelo.get("Grupo", "")

            if not info_modelo and modelo_bf:
                modelos_desconhecidos.add(modelo_bf)

            comb = comb_por_placa.get(placa, {})
            manut = manut_por_placa.get(placa, {})

            veiculos.append({
                "Placa": placa,
                "Modelo_Padrao": modelo_padrao,
                "Grupo": grupo,
                "Montadora": montadora,
                "Tipo_Comb": comb.get("Tipo_Comb", ""),
                "Km_Ini": comb.get("Km_Ini"),
                "Km_Fim": comb.get("Km_Fim"),
                "Litros": comb.get("Litros", 0),
                "Valor_Comb": comb.get("Valor_Comb", 0),
                "Arla_Valor": comb.get("Arla_Valor", 0),
                "Lataria": round(manut.get("Lataria", 0), 2),
                "Manut_Geral": round(manut.get("Manut_Geral", 0), 2),
                "Rodas_Pneus": round(manut.get("Rodas_Pneus", 0), 2),
            })

        print(f"   Veículos: {len(veiculos)} | Comb: {len(comb_por_placa)} | Manut: {len(manut_por_placa)}")

        try:
            saida = escrever_fkm(template_path, veiculos, branch_dir, template_name, mes_ano_cod, periodo)
            if saida:
                print(f"   ✅ {os.path.basename(saida)}")
                gerados += 1
        except Exception as e:
            print(f"   ❌ Erro ao gerar FKM: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"✅ {gerados}/{total} FKMs gerados em {config.PASTA_PERIODO}")

    if modelos_desconhecidos:
        print(f"\n⚠️  {len(modelos_desconhecidos)} modelos sem mapeamento em mapa_modelo.csv")
        print("   Adicione uma linha no CSV para classificar esses tipos automaticamente:")
        for m in sorted(modelos_desconhecidos):
            print(f"   - {m}")
    print("=" * 80)


if __name__ == "__main__":
    main()
