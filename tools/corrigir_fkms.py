"""
Script de Correção Automática de FKMs Retornados
Analisa os arquivos na pasta dados/retornados/, identifica erros conhecidos (como erros de digitação de placas
e hodômetros trocados) e aplica as correções diretamente nas planilhas Excel originais, preservando estilos.
Faz backup automático antes de qualquer modificação.
"""

import os
import glob
import shutil
import pandas as pd
import numpy as np
import xlrd
from xlutils.copy import copy
from src import config

# Mapeamento do nome da filial para a pasta oficial do sistema
MAPA_FILIAIS_NOME_PASTA = {
    "Gritsch Blumenau": "GRITSCH - BLN",
    "Gritsch Brasília": "GRITSCH - BSB",
    "Gritsch Campo Grande": "GRITSCH - CGR",
    "Gritsch Cascavel": "GRITSCH - CSC",
    "Gritsch Caxias do Sul": "GRITSCH - CXJ",
    "Gritsch Chapecó": "GRITSCH - CHA",
    "Gritsch Criciuma": "GRITSCH - CRI",
    "Gritsch Criciúma": "GRITSCH - CRI",
    "Gritsch Cuiabá": "GRITSCH - CGB",
    "Gritsch Curitiba": "GRITSCH - CWB BASE",
    "Gritsch Curitiba Base": "GRITSCH - CWB BASE",
    "Gritsch Curitiba Dir": "GRITSCH - CWB DIR",
    "Gritsch Curitibanos": "GRITSCH - CTB",
    "Gritsch Florianópolis": "GRITSCH - FLN",
    "Gritsch Goiânia": "GRITSCH - GOI",
    "Gritsch Guarapuava": "GRITSCH - GPA",
    "Gritsch Itumbiara": "GRITSCH - ITR",
    "Gritsch Joinville": "GRITSCH - JOI",
    "Gritsch Londrina": "GRITSCH - LDB",
    "Gritsch Matriz": "GRITSCH - MATRIZ",
    "Gritsch Maringá": "GRITSCH - MGA",
    "Gritsch Pato Branco": "GRITSCH - PBC",
    "Gritsch Petrolina": "GRITSCH - PET",
    "Gritsch PET": "GRITSCH - PET",
    "Gritsch Ponta Grossa": "GRITSCH - PGR",
    "Gritsch Palmas": "GRITSCH - PMW",
    "Gritsch Porto Alegre": "GRITSCH - POA",
    "Gritsch Rondonópolis": "GRITSCH - RDN",
    "Gritsch Rio Verde": "GRITSCH - RVD",
    "Gritsch São Paulo": "GRITSCH - SAO PERUS",
    "Gritsch São Paulo Perus": "GRITSCH - SAO PERUS",
    "Gritsch Sinop": "GRITSCH - SNO",
    "Gritsch Salvador": "GRITSCH - SSA",
}

# Cores do terminal
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def carregar_dados_oficiais(folder_name):
    """Carrega dados oficiais de frota, combustível e manutenção da filial."""
    branch_dir = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO, folder_name)
    filial_acronym = folder_name.replace(" - ", "  ")
    
    caminho_frota = os.path.join(branch_dir, f"Frota - {filial_acronym}.xlsx")
    caminho_comb = os.path.join(branch_dir, f"Combustivel - {filial_acronym}.xlsx")
    
    df_frota = pd.read_excel(caminho_frota) if os.path.exists(caminho_frota) else pd.DataFrame(columns=["Placa"])
    df_comb = pd.read_excel(caminho_comb) if os.path.exists(caminho_comb) else pd.DataFrame(columns=["Placa", "Hodometro/Horimetro", "Hodometro/Horimetro anterior", "Data da transacao"])
    
    df_frota["Placa_Clean"] = df_frota["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    df_comb["Placa_Clean"] = df_comb["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    
    return df_frota, df_comb

def processar_correcoes_arquivo(caminho_arq, mes_ano_cod):
    """Analisa e corrige um arquivo .xls individualmente."""
    nome_arq = os.path.basename(caminho_arq)
    
    try:
        rb = xlrd.open_workbook(caminho_arq, formatting_info=True)
    except Exception as e:
        print(f"   {RED}❌ Não foi possível abrir o arquivo com suporte a formatação: {e}{RESET}")
        return False
        
    # Encontrar a aba FKM correta
    sheet_idx = None
    for idx in range(rb.nsheets):
        sheet_name = rb.sheet_names()[idx]
        if "fkm" in sheet_name.lower() and mes_ano_cod in sheet_name:
            sheet_idx = idx
            break
    if sheet_idx is None:
        # Fallback
        for idx in range(rb.nsheets):
            sheet_name = rb.sheet_names()[idx]
            if "fkm" in sheet_name.lower():
                sheet_idx = idx
                break
                
    if sheet_idx is None:
        print(f"   {RED}❌ Aba FKM não encontrada no arquivo.{RESET}")
        return False
        
    sheet = rb.sheet_by_index(sheet_idx)
    
    # Identificar a filial
    branch_name_raw = None
    if sheet.nrows > 1 and sheet.ncols > 5:
        branch_name_raw = sheet.cell_value(1, 5)
        
    if not branch_name_raw or pd.isna(branch_name_raw):
        # Fallback pelo nome do arquivo
        base_name = nome_arq.upper()
        for k, v in MAPA_FILIAIS_NOME_PASTA.items():
            sigla = v.split("-")[-1].strip()
            if sigla in base_name:
                branch_name_raw = k
                break
                
    if not branch_name_raw:
        print(f"   {RED}❌ Filial não identificada para o arquivo.{RESET}")
        return False
        
    branch_name = str(branch_name_raw).strip()
    folder_name = MAPA_FILIAIS_NOME_PASTA.get(branch_name)
    
    if not folder_name:
        print(f"   {RED}❌ Filial '{branch_name}' não mapeada para pasta de saída.{RESET}")
        return False
        
    # Carregar dados oficiais para comparação
    df_frota, df_comb = carregar_dados_oficiais(folder_name)
    frota_plates = set(df_frota[df_frota["Placa_Clean"] != "TOTAL DE VEÍCULOS"]["Placa_Clean"])
    
    # Identificar linha de cabeçalhos
    header_row_idx = 3
    for idx in range(min(15, sheet.nrows)):
        row_vals = [str(sheet.cell_value(idx, c)).lower().strip() for c in range(sheet.ncols) if sheet.cell_type(idx, c) != xlrd.XL_CELL_EMPTY]
        if "placa" in row_vals and "modelo" in row_vals:
            header_row_idx = idx
            break
            
    # Mapear as colunas
    col_map = {}
    for c in range(sheet.ncols):
        val = str(sheet.cell_value(header_row_idx, c)).strip()
        if val:
            col_map[val] = c
            
    col_placa = col_map.get("Placa", 2)
    col_km_ini = col_map.get("Km Inicial", 9)
    col_km_fim = col_map.get("Km Final", 10)
    col_km_tot = col_map.get("Total de Km", 11)
    
    # Ler as placas e linhas da planilha
    fkm_rows = [] # list of dict: {row_idx, placa_clean, original_placa}
    fkm_plates = set()
    
    for r in range(header_row_idx + 1, sheet.nrows):
        placa_raw = sheet.cell_value(r, col_placa)
        placa_clean = str(placa_raw).replace("-", "").strip().upper()
        if len(placa_clean) == 7:
            fkm_rows.append({
                "row_idx": r,
                "placa_clean": placa_clean,
                "original_val": placa_raw
            })
            fkm_plates.add(placa_clean)
            
    missing_in_fkm = frota_plates - fkm_plates
    extra_in_fkm = fkm_plates - frota_plates
    
    correcoes_aplicadas = []
    
    # 1. Tentar corrigir erros de digitação de placa (typos)
    placa_replacements = {} # {row_idx: (old_val, new_val)}
    
    for row in fkm_rows:
        placa = row["placa_clean"]
        if placa in extra_in_fkm:
            # Achar se tem placa parecida na frota oficial ausente
            sugestoes = []
            for miss in missing_in_fkm:
                diffs = sum(1 for a, b in zip(placa, miss) if a != b)
                if diffs <= 2:
                    sugestoes.append(miss)
            if len(sugestoes) == 1:
                placa_replacements[row["row_idx"]] = (row["original_val"], sugestoes[0])
                correcoes_aplicadas.append(f"Placa corrigida: '{row['original_val']}' ➔ '{sugestoes[0]}' na linha {row['row_idx'] + 1}")
                
    # 2. Tentar corrigir odômetros invertidos
    odo_swaps = [] # list of tuples: (row_idx1, row_idx2, placa1, placa2)
    
    if not df_comb.empty:
        # Calcular odômetros oficiais
        df_comb["Hodometro/Horimetro"] = pd.to_numeric(df_comb["Hodometro/Horimetro"], errors="coerce")
        df_comb["Hodometro/Horimetro anterior"] = pd.to_numeric(df_comb["Hodometro/Horimetro anterior"], errors="coerce")
        df_comb_sorted = df_comb.sort_values(by=["Data da transacao"])
        
        df_kms_source = df_comb_sorted.groupby("Placa_Clean").agg(
            Min_Odo_Anterior=("Hodometro/Horimetro anterior", "first"),
            Max_Odo=("Hodometro/Horimetro", "last")
        ).reset_index()
        
        # Mapear valores oficiais
        oficiais_ini = df_kms_source.set_index("Placa_Clean")["Min_Odo_Anterior"].to_dict()
        oficiais_fim = df_kms_source.set_index("Placa_Clean")["Max_Odo"].to_dict()
        
        # Mapear valores atuais do FKM
        fkm_ini_vals = {}
        fkm_fim_vals = {}
        row_by_plate = {}
        for row in fkm_rows:
            r = row["row_idx"]
            placa = row["placa_clean"]
            # Lidar com placa que vai ser renomeada
            if r in placa_replacements:
                placa = placa_replacements[r][1]
                
            val_ini = sheet.cell_value(r, col_km_ini)
            val_fim = sheet.cell_value(r, col_km_fim)
            try:
                fkm_ini_vals[placa] = float(val_ini) if val_ini != "" else 0
                fkm_fim_vals[placa] = float(val_fim) if val_fim != "" else 0
                row_by_plate[placa] = r
            except:
                pass
                
        # Procurar cruzamentos/trocas
        placas_com_historico = list(row_by_plate.keys())
        placas_pareadas = set()
        
        for i in range(len(placas_com_historico)):
            p1 = placas_com_historico[i]
            if p1 in placas_pareadas:
                continue
                
            for j in range(i + 1, len(placas_com_historico)):
                p2 = placas_com_historico[j]
                if p2 in placas_pareadas:
                    continue
                    
                # Verificar se os KMs estão invertidos
                ini1_fkm = fkm_ini_vals.get(p1, 0)
                fim1_fkm = fkm_fim_vals.get(p1, 0)
                ini2_fkm = fkm_ini_vals.get(p2, 0)
                fim2_fkm = fkm_fim_vals.get(p2, 0)
                
                ini1_oficial = oficiais_ini.get(p1, 0)
                fim1_oficial = oficiais_fim.get(p1, 0)
                ini2_oficial = oficiais_ini.get(p2, 0)
                fim2_oficial = oficiais_fim.get(p2, 0)
                
                if (abs(ini1_fkm - ini2_oficial) <= 500 and abs(ini2_fkm - ini1_oficial) <= 500 and
                    ini1_fkm > 0 and ini2_fkm > 0 and ini1_oficial > 0 and ini2_oficial > 0):
                    
                    odo_swaps.append((row_by_plate[p1], row_by_plate[p2], p1, p2))
                    placas_pareadas.add(p1)
                    placas_pareadas.add(p2)
                    correcoes_aplicadas.append(f"Hodômetros desinvertidos entre as placas '{p1}' e '{p2}' (linhas {row_by_plate[p1] + 1} e {row_by_plate[p2] + 1})")
                    
    if not placa_replacements and not odo_swaps:
        print(f"   {GREEN}✔ Nenhuma correção óbvia necessária neste arquivo.{RESET}")
        return False
        
    # --- EFETUAR ALTERAÇÕES ---
    # Fazer backup do arquivo original antes de alterar
    caminho_backup = caminho_arq + ".bak"
    shutil.copy2(caminho_arq, caminho_backup)
    print(f"   💾 Backup criado em: '{os.path.basename(caminho_backup)}'")
    
    # Abrir para escrita
    wb = copy(rb)
    w_sheet = wb.get_sheet(sheet_idx)
    
    # Aplicar placas corretas
    for row_idx, (old_v, new_v) in placa_replacements.items():
        w_sheet.write(row_idx, col_placa, new_v)
        
    # Aplicar swaps de odômetros
    for r1, r2, p1, p2 in odo_swaps:
        # Ler valores originais das células
        ini1 = sheet.cell_value(r1, col_km_ini)
        fim1 = sheet.cell_value(r1, col_km_fim)
        tot1 = sheet.cell_value(r1, col_km_tot)
        
        ini2 = sheet.cell_value(r2, col_km_ini)
        fim2 = sheet.cell_value(r2, col_km_fim)
        tot2 = sheet.cell_value(r2, col_km_tot)
        
        # Escrever valores trocados
        w_sheet.write(r1, col_km_ini, ini2)
        w_sheet.write(r1, col_km_fim, fim2)
        # Recalcular Total KM (Fim - Inicio)
        try:
            w_sheet.write(r1, col_km_tot, float(fim2) - float(ini2))
        except:
            w_sheet.write(r1, col_km_tot, tot2)
            
        w_sheet.write(r2, col_km_ini, ini1)
        w_sheet.write(r2, col_km_fim, fim1)
        try:
            w_sheet.write(r2, col_km_tot, float(fim1) - float(ini1))
        except:
            w_sheet.write(r2, col_km_tot, tot1)
            
    # Salvar o arquivo original
    try:
        wb.save(caminho_arq)
        print(f"   {GREEN}🎉 Modificações aplicadas e salvas com sucesso!{RESET}")
        for corr in correcoes_aplicadas:
            print(f"     ➔ {corr}")
        return True
    except Exception as e:
        print(f"   {RED}❌ Erro ao salvar o arquivo modificado: {e}{RESET}")
        # Restaura backup em caso de falha no salvamento
        if os.path.exists(caminho_backup):
            shutil.copy2(caminho_backup, caminho_arq)
            os.remove(caminho_backup)
            print("   ⚠️ Backup restaurado devido à falha.")
        return False

def main():
    print("=" * 80)
    print(f"🛠️  CORRETOR AUTOMÁTICO DE PLANILHAS FKM RETORNADAS - {config.MES}/{config.ANO}")
    print("=" * 80)
    
    pasta_retorno = os.path.join(config.PROJECT_ROOT, "dados", "retornados")
    arquivos = glob.glob(os.path.join(pasta_retorno, "*.xls"))
    
    # Ignorar arquivos temporários do Office e backups
    arquivos = [
        a for a in arquivos 
        if not os.path.basename(a).startswith("~$") 
        and not os.path.basename(a).startswith(".") 
        and not a.endswith(".bak")
    ]
    
    if not arquivos:
        print(f"⚠️  Nenhum arquivo FKM (.xls) localizado na pasta 'dados/retornados/'.")
        return
        
    print(f"📂 Analisando {len(arquivos)} arquivos FKM...")
    
    mes_ano_cod = f"{config.obter_numero_mes()}{config.ANO[-2:]}" # Ex: 0526
    
    alterados = 0
    for arq in sorted(arquivos):
        print(f"\n📄 Planilha: {os.path.basename(arq)}...")
        sucesso = processar_correcoes_arquivo(arq, mes_ano_cod)
        if sucesso:
            alterados += 1
            
    print("\n" + "=" * 80)
    print(f"🏁 CONCLUSÃO DO AJUSTE: {alterados} planilhas corrigidas com sucesso!")
    print("=" * 80)

if __name__ == "__main__":
    main()
