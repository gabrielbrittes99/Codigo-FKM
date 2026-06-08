"""
Script de Auditoria de FKMs Retornados pelas Filiais
Valida os arquivos preenchidos pelos gerentes de filiais contra os dados oficiais gerados pelo sistema.
Detecta placas digitadas incorretamente, valores divergentes de combustível/Arla/manutenção e divergências de hodômetro.
"""

import os
import glob
import pandas as pd
import numpy as np
from src import config

# Mapeamento do nome da filial preenchido na célula B2/F2 para a pasta oficial do sistema
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

def auditar_arquivo(caminho_fkm, mes_ano_fkm):
    erros = []
    avisos = []
    
    # 1. Carregar o arquivo Excel
    try:
        xl = pd.ExcelFile(caminho_fkm)
    except Exception as e:
        return None, [f"Erro crítico ao abrir o arquivo: {e}"], []
        
    # Identificar a aba correta do FKM do mês
    sheet_name = None
    # Prioridade para o formato FKm MMyy ou Fkm MMyy
    for s in xl.sheet_names:
        if "fkm" in s.lower() and mes_ano_fkm in s:
            sheet_name = s
            break
            
    # Fallback para abas contendo fkm
    if not sheet_name:
        fkm_sheets = [s for s in xl.sheet_names if "fkm" in s.lower()]
        if fkm_sheets:
            sheet_name = fkm_sheets[-1]
            avisos.append(f"Aba específica '{mes_ano_fkm}' não localizada. Usando a aba '{sheet_name}'.")
        else:
            if len(xl.sheet_names) > 1:
                sheet_name = xl.sheet_names[1]  # Geralmente a segunda aba na planilha modelo
                avisos.append(f"Nenhuma aba FKM encontrada. Usando a segunda aba por padrão: '{sheet_name}'.")
            else:
                sheet_name = xl.sheet_names[0]
                avisos.append(f"Apenas uma aba disponível. Usando: '{sheet_name}'.")
                
    try:
        df_raw = xl.parse(sheet_name, header=None)
    except Exception as e:
        return None, [f"Erro crítico ao ler aba '{sheet_name}': {e}"], avisos
        
    # 2. Ler metadata da filial (Normalmente na Linha 1, Coluna 5)
    branch_name_raw = None
    if df_raw.shape[0] > 1 and df_raw.shape[1] > 5:
        branch_name_raw = df_raw.iloc[1, 5]
        
    if not branch_name_raw or pd.isna(branch_name_raw):
        # Tenta buscar a célula "Centralizadora:" na linha 1 e achar o valor ao lado
        for col_idx in range(df_raw.shape[1]):
            val = str(df_raw.iloc[1, col_idx]).strip() if pd.notna(df_raw.iloc[1, col_idx]) else ""
            if "Centralizadora:" in val and col_idx + 1 < df_raw.shape[1]:
                branch_name_raw = df_raw.iloc[1, col_idx + 1]
                break
                
    if not branch_name_raw or pd.isna(branch_name_raw):
        # Tenta na linha 0
        for col_idx in range(df_raw.shape[1]):
            val = str(df_raw.iloc[0, col_idx]).strip() if pd.notna(df_raw.iloc[0, col_idx]) else ""
            if "Centralizadora:" in val and col_idx + 1 < df_raw.shape[1]:
                branch_name_raw = df_raw.iloc[0, col_idx + 1]
                break
                
    if not branch_name_raw or pd.isna(branch_name_raw):
        # Fallback pelo nome do arquivo
        base_name = os.path.basename(caminho_fkm).upper()
        # Procura siglas de filiais no nome do arquivo
        sigla_encontrada = None
        for k, v in MAPA_FILIAIS_NOME_PASTA.items():
            sigla = v.split("-")[-1].strip()
            if sigla in base_name:
                sigla_encontrada = sigla
                branch_name_raw = k
                break
        if not sigla_encontrada:
            return None, [f"Não foi possível identificar a filial pela célula de cabeçalho ou nome do arquivo."], avisos
            
    branch_name = str(branch_name_raw).strip()
    folder_name = MAPA_FILIAIS_NOME_PASTA.get(branch_name)
    
    if not folder_name:
        return branch_name, [f"Filial '{branch_name}' identificada mas não está mapeada no sistema."], avisos
        
    branch_dir = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO, folder_name)
    
    if not os.path.exists(branch_dir):
        return branch_name, [f"Diretório oficial de fechamento não encontrado para esta filial: {branch_dir}"], avisos
        
    # 3. Processar dados do FKM retornado
    # Descobrir a linha do cabeçalho
    header_row_idx = 3
    for idx in range(min(15, df_raw.shape[0])):
        row_vals = [str(x).lower().strip() for x in df_raw.iloc[idx].tolist() if pd.notna(x)]
        if "placa" in row_vals and "modelo" in row_vals:
            header_row_idx = idx
            break
            
    headers = df_raw.iloc[header_row_idx].tolist()
    df_fkm = df_raw.iloc[header_row_idx + 1:].copy()
    df_fkm.columns = [str(h).strip() if pd.notna(h) else f"col_{idx}" for idx, h in enumerate(headers)]
    
    # Limpar placas
    df_fkm["Placa_Clean"] = df_fkm["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    # Filtrar apenas linhas com placas válidas (7 caracteres)
    df_fkm = df_fkm[df_fkm["Placa_Clean"].str.len() == 7]
    
    # Converter colunas do FKM para numérico
    colunas_valores = [
        "Km Inicial", "Km Final", "Total de Km", 
        "Litros Comb.", "Valor Comb.", "Arla", 
        "Lataria e Pintura", "Manutenção em Geral", "Rodas / Pneus"
    ]
    for col in colunas_valores:
        if col in df_fkm.columns:
            df_fkm[col] = pd.to_numeric(df_fkm[col], errors="coerce").fillna(0)
        else:
            # Tentar achar por coluna aproximada caso o cabeçalho mude ligeiramente
            for c in df_fkm.columns:
                if col.lower() in c.lower() or c.lower() in col.lower():
                    df_fkm[col] = pd.to_numeric(df_fkm[c], errors="coerce").fillna(0)
                    break
                    
    # 4. Carregar dados oficiais gerados pelo sistema
    filial_acronym = folder_name.replace(" - ", "  ")
    caminho_frota = os.path.join(branch_dir, f"Frota - {filial_acronym}.xlsx")
    caminho_comb = os.path.join(branch_dir, f"Combustivel - {filial_acronym}.xlsx")
    caminho_manut = os.path.join(branch_dir, f"Manutencao - {filial_acronym}.xlsx")
    
    df_frota = pd.read_excel(caminho_frota) if os.path.exists(caminho_frota) else pd.DataFrame(columns=["Placa"])
    df_comb = pd.read_excel(caminho_comb) if os.path.exists(caminho_comb) else pd.DataFrame(columns=["Placa", "Litragem", "Valor total", "Combustivel", "Hodometro/Horimetro", "Hodometro/Horimetro anterior", "Data da transacao"])
    df_manut = pd.read_excel(caminho_manut) if os.path.exists(caminho_manut) else pd.DataFrame(columns=["Placa", "ValorTotal"])
    
    df_frota["Placa_Clean"] = df_frota["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    df_comb["Placa_Clean"] = df_comb["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    df_manut["Placa_Clean"] = df_manut["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()
    
    # 5. Executar Auditorias
    
    # --- A. Validação de Placas ---
    fkm_plates = set(df_fkm["Placa_Clean"])
    frota_plates = set(df_frota[df_frota["Placa_Clean"] != "TOTAL DE VEÍCULOS"]["Placa_Clean"])
    
    missing_in_fkm = frota_plates - fkm_plates
    extra_in_fkm = fkm_plates - frota_plates
    
    if missing_in_fkm:
        avisos.append(f"Placas da frota oficial ausentes no FKM: {sorted(list(missing_in_fkm))}")
    if extra_in_fkm:
        # Verifica se alguma placa extra no FKM é parecida com alguma ausente da frota (possível typo do gerente)
        for extra in extra_in_fkm:
            sugestoes = []
            for miss in missing_in_fkm:
                # Calcula distância de Hamming rápida
                diffs = sum(1 for a, b in zip(extra, miss) if a != b)
                if diffs <= 2:
                    sugestoes.append(miss)
            if sugestoes:
                erros.append(f"Placa inválida/extra no FKM: '{extra}' (provável erro de digitação para: {sugestoes})")
            else:
                avisos.append(f"Placa no FKM que não está na frota oficial de {branch_name}: '{extra}' (pode ser veículo novo ou emprestado)")
                
    # --- B. Validação de Combustível e Arla ---
    # Agrupar colunas por placa caso a mesma placa apareça em múltiplas linhas no FKM
    df_fkm_grouped = df_fkm.groupby("Placa_Clean").agg(
        Placa=("Placa", "first"),
        Km_Inicial=("Km Inicial", "min"),
        Km_Final=("Km Final", "max"),
        Total_de_Km=("Total de Km", "sum"),
        Litros_Comb=("Litros Comb.", "sum"),
        Valor_Comb=("Valor Comb.", "sum"),
        Arla=("Arla", "sum"),
        Lataria_e_Pintura=("Lataria e Pintura", "sum"),
        Manutencao_em_Geral=("Manutenção em Geral", "sum"),
        Rodas_Pneus=("Rodas / Pneus", "sum")
    ).reset_index()
    
    df_fkm_grouped["Km Inicial"] = df_fkm_grouped["Km_Inicial"]
    df_fkm_grouped["Km Final"] = df_fkm_grouped["Km_Final"]
    df_fkm_grouped["Total de Km"] = df_fkm_grouped["Total_de_Km"]
    df_fkm_grouped["Litros Comb."] = df_fkm_grouped["Litros_Comb"]
    df_fkm_grouped["Valor Comb."] = df_fkm_grouped["Valor_Comb"]
    df_fkm_grouped["Lataria e Pintura"] = df_fkm_grouped["Lataria_e_Pintura"]
    df_fkm_grouped["Manutenção em Geral"] = df_fkm_grouped["Manutencao_em_Geral"]
    df_fkm_grouped["Rodas / Pneus"] = df_fkm_grouped["Rodas_Pneus"]
    
    # Substituir df_fkm pela versão agrupada para as validações seguintes
    df_fkm = df_fkm_grouped

    # Filtrar Arla em combustível oficial
    df_comb_arla = df_comb[df_comb["Combustivel"].str.contains("Arla", case=False, na=False)].groupby("Placa_Clean").agg(
        Arla_Liters_Source=("Litragem", "sum"),
        Arla_Valor_Source=("Valor total", "sum")
    ).reset_index()
    
    df_comb_no_arla = df_comb[~df_comb["Combustivel"].str.contains("Arla", case=False, na=False)].groupby("Placa_Clean").agg(
        Fuel_Liters_Source=("Litragem", "sum"),
        Fuel_Valor_Source=("Valor total", "sum")
    ).reset_index()
    
    df_comp_comb = df_fkm[["Placa_Clean", "Placa", "Litros Comb.", "Valor Comb.", "Arla"]]
    df_comp_comb = df_comp_comb.merge(df_comb_arla, on="Placa_Clean", how="outer").merge(df_comb_no_arla, on="Placa_Clean", how="outer").fillna(0)
    
    # Calcular diferenças
    df_comp_comb["Diff_Litros"] = df_comp_comb["Litros Comb."] - df_comp_comb["Fuel_Liters_Source"]
    df_comp_comb["Diff_Valor"] = df_comp_comb["Valor Comb."] - df_comp_comb["Fuel_Valor_Source"]
    df_comp_comb["Diff_Arla"] = df_comp_comb["Arla"] - df_comp_comb["Arla_Valor_Source"]
    
    # Identificar divergências significativas
    for _, r in df_comp_comb.iterrows():
        placa = r["Placa_Clean"]
        # Ignorar placas não presentes no FKM (já reportadas como ausentes)
        if placa not in fkm_plates:
            continue
            
        if abs(r["Diff_Litros"]) > 0.5:
            erros.append(f"Combustível Placa {placa}: Litragem divergente! Preenchido: {r['Litros Comb.']:.2f}L | Oficial: {r['Fuel_Liters_Source']:.2f}L (Dif: {r['Diff_Litros']:.2f}L)")
            
        if abs(r["Diff_Valor"]) > 1.0: # Margem de R$ 1.00 para arredondamento
            erros.append(f"Combustível Placa {placa}: Custo de combustível divergente! Preenchido: R$ {r['Valor Comb.']:.2f} | Oficial: R$ {r['Fuel_Valor_Source']:.2f} (Dif: R$ {r['Diff_Valor']:.2f})")
            
        if abs(r["Diff_Arla"]) > 0.5:
            erros.append(f"Arla Placa {placa}: Valor divergente! Preenchido: R$ {r['Arla']:.2f} | Oficial: R$ {r['Arla_Valor_Source']:.2f} (Dif: R$ {r['Diff_Arla']:.2f})")
            
    # --- C. Validação de Manutenção ---
    df_manut_agg = df_manut.groupby("Placa_Clean").agg(
        Manut_Source_Total=("ValorTotal", "sum")
    ).reset_index()
    
    df_fkm["Only_Manut_FKM"] = df_fkm["Lataria e Pintura"] + df_fkm["Manutenção em Geral"] + df_fkm["Rodas / Pneus"]
    
    df_comp_manut = df_fkm[["Placa_Clean", "Placa", "Only_Manut_FKM"]]
    df_comp_manut = df_comp_manut.merge(df_manut_agg, on="Placa_Clean", how="outer").fillna(0)
    df_comp_manut["Diff_Manut"] = df_comp_manut["Only_Manut_FKM"] - df_comp_manut["Manut_Source_Total"]
    
    for _, r in df_comp_manut.iterrows():
        placa = r["Placa_Clean"]
        if placa not in fkm_plates:
            continue
            
        if abs(r["Diff_Manut"]) > 1.0: # Margem de R$ 1.00
            erros.append(f"Manutenção Placa {placa}: Valor de Manutenção total divergente! Preenchido: R$ {r['Only_Manut_FKM']:.2f} (Soma das 3 colunas) | Oficial: R$ {r['Manut_Source_Total']:.2f} (Dif: R$ {r['Diff_Manut']:.2f})")
            
    # --- D. Validação de Quilometragem (KM) ---
    if not df_comb.empty:
        df_comb["Hodometro/Horimetro"] = pd.to_numeric(df_comb["Hodometro/Horimetro"], errors="coerce")
        df_comb["Hodometro/Horimetro anterior"] = pd.to_numeric(df_comb["Hodometro/Horimetro anterior"], errors="coerce")
        df_comb_sorted = df_comb.sort_values(by=["Data da transacao", "Transacao"])
        
        df_kms_source = df_comb_sorted.groupby("Placa_Clean").agg(
            Min_Odo_Anterior=("Hodometro/Horimetro anterior", "first"),
            Max_Odo=("Hodometro/Horimetro", "last")
        ).reset_index()
        
        df_comp_km = df_fkm[["Placa_Clean", "Placa", "Km Inicial", "Km Final", "Total de Km"]]
        df_comp_km = df_comp_km.merge(df_kms_source, on="Placa_Clean", how="inner").fillna(0)
        
        # Guardar placas que tem km inicial invertido ou de outras placas
        km_iniciais = df_comp_km.set_index("Placa_Clean")["Km Inicial"].to_dict()
        primeiros_odos = df_comp_km.set_index("Placa_Clean")["Min_Odo_Anterior"].to_dict()
        
        # 1. Checar Km Inicial (admite diferença se veículo iniciou zerado/outro)
        for _, r in df_comp_km.iterrows():
            placa = r["Placa_Clean"]
            k_ini_fkm = r["Km Inicial"]
            k_ini_oficial = r["Min_Odo_Anterior"]
            
            # Se for divergente de forma considerável (> 20 km) e ambos maiores que 0
            if abs(k_ini_fkm - k_ini_oficial) > 20 and k_ini_fkm > 0 and k_ini_oficial > 0:
                # Verificar se o gerente inverteu os odômetros com outro veículo da frota
                trocado_com = None
                for outra_placa, outro_val in primeiros_odos.items():
                    if outra_placa != placa and abs(k_ini_fkm - outro_val) <= 20:
                        trocado_com = outra_placa
                        break
                if trocado_com:
                    erros.append(f"Hodômetro Inicial Placa {placa}: Km Inicial preenchido ({k_ini_fkm:.0f}) parece pertencer à Placa '{trocado_com}' ({outro_val:.0f}).")
                else:
                    avisos.append(f"Hodômetro Inicial Placa {placa}: Km Inicial divergente! FKM: {k_ini_fkm:.0f} | Primeiro Abastecimento: {k_ini_oficial:.0f} (Dif: {k_ini_fkm - k_ini_oficial:.0f})")
                    
        # 2. Checar Km Final
        for _, r in df_comp_km.iterrows():
            placa = r["Placa_Clean"]
            k_fim_fkm = r["Km Final"]
            k_fim_oficial = r["Max_Odo"]
            if abs(k_fim_fkm - k_fim_oficial) > 20 and k_fim_fkm > 0 and k_fim_oficial > 0:
                avisos.append(f"Hodômetro Final Placa {placa}: Km Final divergente! FKM: {k_fim_fkm:.0f} | Último Abastecimento: {k_fim_oficial:.0f} (Dif: {k_fim_fkm - k_fim_oficial:.0f})")
                
        # 3. Checar cálculo interno da planilha (Km Final - Km Inicial != Total de Km)
        for _, r in df_comp_km.iterrows():
            placa = r["Placa_Clean"]
            diff_calc = abs((r["Km Final"] - r["Km Inicial"]) - r["Total de Km"])
            if diff_calc > 1.0: # Margem de tolerância
                erros.append(f"Cálculo Km Placa {placa}: Km Final ({r['Km Final']:.0f}) - Km Inicial ({r['Km Inicial']:.0f}) = {(r['Km Final'] - r['Km Inicial']):.0f}, mas a coluna Total Km diz {r['Total de Km']:.0f}.")
                
    return branch_name, erros, avisos

def main():
    print("=" * 80)
    print(f"🕵️  SISTEMA DE AUDITORIA E VALIDAÇÃO DE RETORNOS DE FKM - {config.MES}/{config.ANO}")
    print("=" * 80)
    
    pasta_retorno = os.path.join(config.PROJECT_ROOT, "dados", "retornados")
    
    if not os.path.exists(pasta_retorno):
        print(f"❌ Diretório de retornos não encontrado em: {pasta_retorno}")
        print("Crie esta pasta e insira os FKMs enviados pelas filiais para auditoria.")
        return
        
    arquivos = glob.glob(os.path.join(pasta_retorno, "*.xls*"))
    # Filtrar arquivos temporários ou metadados de sistema (como Zone.Identifier ou arquivos temporários do Office)
    arquivos = [
        a for a in arquivos 
        if "Zone.Identifier" not in a 
        and not os.path.basename(a).startswith("~$") 
        and not os.path.basename(a).startswith(".")
        and not a.endswith(".bak")
    ]
    
    if not arquivos:
        print(f"⚠️  Nenhum arquivo FKM (.xls ou .xlsx) localizado na pasta dados/retornados/.")
        return
        
    print(f"📂 Encontrados {len(arquivos)} arquivos válidos para validar.")
    
    mes_ano_cod = f"{config.obter_numero_mes()}{config.ANO[-2:]}" # Ex: 0526
    
    resumo_auditoria = []
    
    for arq in sorted(arquivos):
        nome_arq = os.path.basename(arq)
        print(f"\n📄 Analisando: {nome_arq}...")
        
        branch_name, erros, avisos = auditar_arquivo(arq, mes_ano_cod)
        
        status = "APROVADO"
        cor = GREEN
        
        if erros:
            status = "REJEITADO"
            cor = RED
        elif avisos:
            status = "ATENÇÃO"
            cor = YELLOW
            
        resumo_auditoria.append({
            "Arquivo": nome_arq,
            "Filial": branch_name or "Desconhecido",
            "Status": status,
            "Erros": len(erros),
            "Avisos": len(avisos)
        })
        
        # Exibir relatório detalhado da filial
        print(f"   🏛️  Filial: {BOLD}{branch_name or 'N/A'}{RESET}")
        print(f"   📊 Status: {cor}{BOLD}{status}{RESET}")
        
        if erros:
            print(f"   {RED}🚨 Inconsistências Críticas Encontradas ({len(erros)}):{RESET}")
            for err in erros:
                print(f"     ✖ {err}")
                
        if avisos:
            print(f"   {YELLOW}⚠️  Alertas/Avisos ({len(avisos)}):{RESET}")
            for av in avisos:
                print(f"     ⚠ {av}")
                
        if not erros and not avisos:
            print(f"   {GREEN}✔ Dados 100% consistentes com as planilhas oficiais!{RESET}")
            
    print("\n" + "=" * 80)
    print(f"{BOLD}📋 QUADRO RESUMO DA AUDITORIA MENSAL{RESET}")
    print("=" * 80)
    
    # Formatação do quadro de resumo
    for item in resumo_auditoria:
        cor = GREEN if item["Status"] == "APROVADO" else (RED if item["Status"] == "REJEITADO" else YELLOW)
        print(f"• {item['Arquivo']:<32} | {item['Filial']:<20} | Status: {cor}{BOLD}{item['Status']:<10}{RESET} (Erros: {item['Erros']}, Alertas: {item['Avisos']})")
        
    print("=" * 80)

if __name__ == "__main__":
    main()
