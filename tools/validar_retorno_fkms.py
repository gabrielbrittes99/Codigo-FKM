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
from src.filial_mapping import EXCECOES_MANUTENCAO

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
    "Gritsch Diretoria": "GRITSCH - CWB DIR",
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
    "Gritsch Pelotas": "GRITSCH - PET",
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
    "Gritsch Santa Maria": "GRITSCH - RIA",
    "Gritsch RIA": "GRITSCH - RIA",
}

# Cores do terminal
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Filiais com abastecimento por fora (não centralizado no prestador principal)
# Usar os nomes como aparecem no FKM (sem siglas)
FILIAIS_ABAST_POR_FORA = [
    "Gritsch Itumbiara",
    "Gritsch Goiânia",
    "Gritsch Palmas",
    "Gritsch Rio Verde",
    "Gritsch Rondonópolis"
]

# Filiais com Arla por fora (compram Arla de fornecedor externo)
FILIAIS_ARLA_POR_FORA = [
    "Gritsch Curitiba"
]

# Filiais com manutenção por fora (fundo fixo, emergenciais sem NF)
FILIAIS_MANUT_POR_FORA = [
    "Gritsch Rondonópolis"
]

def auditar_arquivo(caminho_fkm, mes_ano_fkm):
    erros = []
    avisos = []
    # Estrutura para armazenar valores oficiais para facilitar correção manual
    valores_corretos = {
        "placas_faltantes": [],
        "placas_extras": [],
        "combustivel": [],
        "manutencao": [],
        "hodometro": [],
        "abast_por_fora": [],  # Abastecimentos por fora do prestador principal
        "manut_por_fora": []   # Manutenções com fundo fixo (emergenciais sem NF)
    }
    
    # 1. Carregar o arquivo Excel
    try:
        xl = pd.ExcelFile(caminho_fkm)
    except Exception as e:
        return None, [f"Erro crítico ao abrir o arquivo: {e}"], [], valores_corretos
        
    # Identificar a aba correta do FKM do mês
    sheet_name = None
    mes_num_busca = mes_ano_fkm[:2]  # Ex: "05" de "0526"

    # Prioridade 1: match exato com MMyy (ex: "0526")
    for s in xl.sheet_names:
        if "fkm" in s.lower() and mes_ano_fkm in s:
            sheet_name = s
            break

    # Prioridade 2: match pelo mês com qualquer ano (ex: "05" em "FKm 0525")
    # Algumas planilhas usam sufixo de ano diferente no nome da aba
    if not sheet_name:
        for s in xl.sheet_names:
            if "fkm" in s.lower() and mes_num_busca in s and "resumo" not in s.lower():
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
        return None, [f"Erro crítico ao ler aba '{sheet_name}': {e}"], avisos, valores_corretos
        
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
            return None, [f"Não foi possível identificar a filial pela célula de cabeçalho ou nome do arquivo."], avisos, valores_corretos
            
    branch_name = str(branch_name_raw).strip()
    folder_name = MAPA_FILIAIS_NOME_PASTA.get(branch_name)
    
    if not folder_name:
        return branch_name, [f"Filial '{branch_name}' identificada mas não está mapeada no sistema."], avisos, valores_corretos
        
    branch_dir = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO, folder_name)
    
    if not os.path.exists(branch_dir):
        return branch_name, [f"Diretório oficial de fechamento não encontrado para esta filial: {branch_dir}"], avisos, valores_corretos
        
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
    
    colunas_km = ["Km Inicial", "Km Final", "Total de Km"]
    colunas_valores = [
        "Litros Comb.", "Valor Comb.", "Arla", 
        "Lataria e Pintura", "Manutenção em Geral", "Rodas / Pneus"
    ]

    def _clean_numeric(series, is_km=False):
        def _parse_val(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            val_str = str(val).strip()
            if "," in val_str:
                val_str = val_str.replace(".", "").replace(",", ".")
            elif "." in val_str:
                parts = val_str.split(".")
                # Em KM (ex: 137.400 -> 137400), se tiver 3 digitos apos o ponto e is_km=True, é separador de milhar
                if is_km and len(parts) == 2 and len(parts[1]) == 3:
                    val_str = "".join(parts)
            return pd.to_numeric(val_str, errors="coerce")
        return series.apply(_parse_val).fillna(0.0)

    for col in colunas_km:
        if col in df_fkm.columns:
            df_fkm[col] = _clean_numeric(df_fkm[col], is_km=True)
        else:
            for c in df_fkm.columns:
                if col.lower() in c.lower() or c.lower() in col.lower():
                    df_fkm[col] = _clean_numeric(df_fkm[c], is_km=True)
                    break

    for col in colunas_valores:
        if col in df_fkm.columns:
            df_fkm[col] = _clean_numeric(df_fkm[col], is_km=False)
        else:
            for c in df_fkm.columns:
                if col.lower() in c.lower() or c.lower() in col.lower():
                    df_fkm[col] = _clean_numeric(df_fkm[c], is_km=False)
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
        # Obter os custos oficiais de cada placa para verificar omissão crítica
        custos_comb = {}
        if not df_comb.empty:
            # Filtrar Arla em combustível oficial
            df_comb_arla = df_comb[df_comb["Combustivel"].str.contains("Arla", case=False, na=False)].groupby("Placa_Clean").agg(
                Arla_Valor_Source=("Valor total", "sum")
            ).reset_index()
            df_comb_no_arla = df_comb[~df_comb["Combustivel"].str.contains("Arla", case=False, na=False)].groupby("Placa_Clean").agg(
                Fuel_Liters_Source=("Litragem", "sum"),
                Fuel_Valor_Source=("Valor total", "sum")
            ).reset_index()
            
            for _, r in df_comb_no_arla.iterrows():
                placa = r["Placa_Clean"]
                custos_comb[placa] = {
                    "litros": r["Fuel_Liters_Source"],
                    "valor": r["Fuel_Valor_Source"],
                    "arla": 0.0
                }
            for _, r in df_comb_arla.iterrows():
                placa = r["Placa_Clean"]
                if placa not in custos_comb:
                    custos_comb[placa] = {"litros": 0.0, "valor": 0.0, "arla": 0.0}
                custos_comb[placa]["arla"] = r["Arla_Valor_Source"]
                
        custos_manut = {}
        if not df_manut.empty:
            df_manut_agg = df_manut.groupby("Placa_Clean").agg(
                Manut_Source_Total=("ValorTotal", "sum")
            ).reset_index()
            for _, r in df_manut_agg.iterrows():
                custos_manut[r["Placa_Clean"]] = r["Manut_Source_Total"]

        for miss in sorted(list(missing_in_fkm)):
            c_info = custos_comb.get(miss, {"litros": 0.0, "valor": 0.0, "arla": 0.0})
            m_val = custos_manut.get(miss, 0.0)

            # Buscar modelo do veículo
            veiculo = df_frota[df_frota["Placa_Clean"] == miss]
            modelo = veiculo.iloc[0].get("Modelo", "") if not veiculo.empty else ""
            placa_formatada = veiculo.iloc[0]["Placa"] if not veiculo.empty else miss

            has_costs = c_info["litros"] > 0 or c_info["valor"] > 0 or c_info["arla"] > 0 or m_val > 0

            # Armazenar valores corretos para exibição
            valores_corretos["placas_faltantes"].append({
                "placa": placa_formatada,
                "modelo": modelo,
                "litros": c_info["litros"],
                "valor_comb": c_info["valor"],
                "arla": c_info["arla"],
                "manutencao": m_val
            })

            if has_costs:
                erros.append(
                    f"Veículo omisso no FKM: A placa '{miss}' pertence à frota oficial e possui custos registrados "
                    f"(L: {c_info['litros']:.2f}L, V: R$ {c_info['valor']:.2f}, Arla: R$ {c_info['arla']:.2f}, OS: R$ {m_val:.2f}), "
                    f"mas foi omitida da planilha pelo gerente."
                )
            else:
                # ALTERAÇÃO: Placa da frota oficial faltando é sempre ERRO GRAVE, mesmo sem custos registrados
                erros.append(
                    f"Veículo omisso no FKM: A placa '{miss}' pertence à frota oficial mas foi omitida da planilha. "
                    f"Mesmo sem custos registrados no mês, todos os veículos da frota devem constar no FKM."
                )
    if extra_in_fkm:
        # Calcular custos para verificar se placas extras têm custos válidos
        custos_comb_extra = {}
        if not df_comb.empty:
            df_comb_arla_extra = df_comb[df_comb["Combustivel"].str.contains("Arla", case=False, na=False)].groupby("Placa_Clean").agg(
                Arla_Valor_Source=("Valor total", "sum")
            ).reset_index()
            df_comb_no_arla_extra = df_comb[~df_comb["Combustivel"].str.contains("Arla", case=False, na=False)].groupby("Placa_Clean").agg(
                Fuel_Liters_Source=("Litragem", "sum"),
                Fuel_Valor_Source=("Valor total", "sum")
            ).reset_index()

            for _, r in df_comb_no_arla_extra.iterrows():
                placa = r["Placa_Clean"]
                custos_comb_extra[placa] = {
                    "litros": r["Fuel_Liters_Source"],
                    "valor": r["Fuel_Valor_Source"],
                    "arla": 0.0
                }
            for _, r in df_comb_arla_extra.iterrows():
                placa = r["Placa_Clean"]
                if placa not in custos_comb_extra:
                    custos_comb_extra[placa] = {"litros": 0.0, "valor": 0.0, "arla": 0.0}
                custos_comb_extra[placa]["arla"] = r["Arla_Valor_Source"]

        custos_manut_extra = {}
        if not df_manut.empty:
            df_manut_agg_extra = df_manut.groupby("Placa_Clean").agg(
                Manut_Source_Total=("ValorTotal", "sum")
            ).reset_index()
            for _, r in df_manut_agg_extra.iterrows():
                custos_manut_extra[r["Placa_Clean"]] = r["Manut_Source_Total"]

        # Verifica se alguma placa extra no FKM é parecida com alguma ausente da frota (possível typo do gerente)
        filial_abast_por_fora = branch_name in FILIAIS_ABAST_POR_FORA
        for extra in extra_in_fkm:
            # Verificar se a placa extra tem custos oficiais (ou se a filial abastece por fora)
            c_info_extra = custos_comb_extra.get(extra, {"litros": 0.0, "valor": 0.0, "arla": 0.0})
            m_val_extra = custos_manut_extra.get(extra, 0.0)

            # Buscar também os valores declarados no próprio FKM retornado pelo gerente
            linha_fkm_extra = df_fkm[df_fkm["Placa_Clean"] == extra]
            val_comb_fkm = float(linha_fkm_extra["Valor Comb."].sum()) if not linha_fkm_extra.empty and "Valor Comb." in linha_fkm_extra.columns else 0.0
            lit_comb_fkm = float(linha_fkm_extra["Litros Comb."].sum()) if not linha_fkm_extra.empty and "Litros Comb." in linha_fkm_extra.columns else 0.0
            val_manut_fkm = float(linha_fkm_extra["Only_Manut_FKM"].sum()) if not linha_fkm_extra.empty and "Only_Manut_FKM" in linha_fkm_extra.columns else 0.0

            has_costs_extra = (
                c_info_extra["litros"] > 0 or c_info_extra["valor"] > 0 or c_info_extra["arla"] > 0 or m_val_extra > 0 or
                ((val_comb_fkm > 0 or lit_comb_fkm > 0 or val_manut_fkm > 0) and filial_abast_por_fora)
            )

            # Se a placa tem custos oficiais ou declarados em filial que abastece por fora, é VÁLIDA
            if has_costs_extra:
                continue  # Válido, não é erro

            # Se NÃO tem custos, verificar se é erro de digitação
            sugestoes = []
            for miss in missing_in_fkm:
                # Calcula distância de Hamming rápida
                diffs = sum(1 for a, b in zip(extra, miss) if a != b)
                if diffs <= 2:
                    sugestoes.append(miss)

            # Armazenar para exibição
            valores_corretos["placas_extras"].append({
                "placa": extra,
                "sugestao": sugestoes[0] if sugestoes else None
            })

            if sugestoes:
                erros.append(f"Placa inválida/extra no FKM: '{extra}' (provável erro de digitação para: {sugestoes})")
            else:
                erros.append(
                    f"Placa inválida no FKM: '{extra}' não pertence à frota oficial de {branch_name} e não possui custos registrados. "
                    f"Verifique se há erro de digitação ou se a frota oficial precisa ser atualizada."
                )
                
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
    # Para filiais com abastecimento por fora, registrar diferenças sem gerar erro
    filial_abast_por_fora = branch_name in FILIAIS_ABAST_POR_FORA
    filial_arla_por_fora = branch_name in FILIAIS_ARLA_POR_FORA

    for _, r in df_comp_comb.iterrows():
        placa = r["Placa_Clean"]
        # Ignorar placas não presentes no FKM (já reportadas como ausentes)
        if placa not in fkm_plates:
            continue

        # Verificar divergências
        div_pos_litros = r["Diff_Litros"] > 0.5
        div_neg_litros = r["Diff_Litros"] < -0.5
        
        div_pos_valor = r["Diff_Valor"] > 1.0
        div_neg_valor = r["Diff_Valor"] < -1.0
        
        div_pos_arla = r["Diff_Arla"] > 0.5
        div_neg_arla = r["Diff_Arla"] < -0.5

        # 1. Tratar abastecimentos por fora (apenas diferenças positivas)
        if (div_pos_litros or div_pos_valor or div_pos_arla) and filial_abast_por_fora:
            valores_corretos["abast_por_fora"].append({
                "placa": placa,
                "litros_fkm": r['Litros Comb.'],
                "litros_oficial": r['Fuel_Liters_Source'],
                "litros_por_fora": max(0.0, r['Diff_Litros']),
                "valor_fkm": r['Valor Comb.'],
                "valor_oficial": r['Fuel_Valor_Source'],
                "valor_por_fora": max(0.0, r['Diff_Valor']),
                "arla_fkm": r['Arla'],
                "arla_oficial": r['Arla_Valor_Source'],
                "arla_por_fora": max(0.0, r['Diff_Arla'])
            })
        else:
            # Se for positivo mas não é filial por fora, é erro
            if div_pos_litros:
                valores_corretos["combustivel"].append({
                    "placa": placa,
                    "tipo": "Litros",
                    "valor_fkm": r['Litros Comb.'],
                    "valor_oficial": r['Fuel_Liters_Source']
                })
                erros.append(f"Combustível Placa {placa}: Litragem divergente (a maior)! Preenchido: {r['Litros Comb.']:.2f}L | Oficial: {r['Fuel_Liters_Source']:.2f}L (Dif: {r['Diff_Litros']:.2f}L)")
            
            if div_pos_valor:
                valores_corretos["combustivel"].append({
                    "placa": placa,
                    "tipo": "Valor Combustível",
                    "valor_fkm": r['Valor Comb.'],
                    "valor_oficial": r['Fuel_Valor_Source']
                })
                erros.append(f"Combustível Placa {placa}: Custo de combustível divergente (a maior)! Preenchido: R$ {r['Valor Comb.']:.2f} | Oficial: R$ {r['Fuel_Valor_Source']:.2f} (Dif: R$ {r['Diff_Valor']:.2f})")

            if div_pos_arla:
                if filial_arla_por_fora:
                    valores_corretos["abast_por_fora"].append({
                        "placa": placa,
                        "litros_fkm": 0,
                        "litros_oficial": 0,
                        "litros_por_fora": 0,
                        "valor_fkm": 0,
                        "valor_oficial": 0,
                        "valor_por_fora": 0,
                        "arla_fkm": r['Arla'],
                        "arla_oficial": r['Arla_Valor_Source'],
                        "arla_por_fora": r['Diff_Arla']
                    })
                else:
                    valores_corretos["combustivel"].append({
                        "placa": placa,
                        "tipo": "Arla",
                        "valor_fkm": r['Arla'],
                        "valor_oficial": r['Arla_Valor_Source']
                    })
                    erros.append(f"Arla Placa {placa}: Valor divergente (a maior)! Preenchido: R$ {r['Arla']:.2f} | Oficial: R$ {r['Arla_Valor_Source']:.2f} (Dif: R$ {r['Diff_Arla']:.2f})")

        # 2. Diferenças negativas (sempre são erros, pois FKM < Oficial)
        if div_neg_litros:
            valores_corretos["combustivel"].append({
                "placa": placa,
                "tipo": "Litros",
                "valor_fkm": r['Litros Comb.'],
                "valor_oficial": r['Fuel_Liters_Source']
            })
            erros.append(f"Combustível Placa {placa}: Litragem menor que a oficial! Preenchido: {r['Litros Comb.']:.2f}L | Oficial: {r['Fuel_Liters_Source']:.2f}L (Dif: {r['Diff_Litros']:.2f}L)")
        
        if div_neg_valor:
            valores_corretos["combustivel"].append({
                "placa": placa,
                "tipo": "Valor Combustível",
                "valor_fkm": r['Valor Comb.'],
                "valor_oficial": r['Fuel_Valor_Source']
            })
            erros.append(f"Combustível Placa {placa}: Custo de combustível menor que o oficial! Preenchido: R$ {r['Valor Comb.']:.2f} | Oficial: R$ {r['Fuel_Valor_Source']:.2f} (Dif: R$ {r['Diff_Valor']:.2f})")

        if div_neg_arla:
            valores_corretos["combustivel"].append({
                "placa": placa,
                "tipo": "Arla",
                "valor_fkm": r['Arla'],
                "valor_oficial": r['Arla_Valor_Source']
            })
            erros.append(f"Arla Placa {placa}: Valor menor que o oficial! Preenchido: R$ {r['Arla']:.2f} | Oficial: R$ {r['Arla_Valor_Source']:.2f} (Dif: R$ {r['Diff_Arla']:.2f})")
            
    # --- C. Validação de Manutenção ---
    df_manut_agg = df_manut.groupby("Placa_Clean").agg(
        Manut_Source_Total=("ValorTotal", "sum")
    ).reset_index()

    # Tentar agrupar por Natureza no oficial se a coluna existir (Lataria/Mecânica/Pneus)
    col_nat_oficial = None
    for c in df_manut.columns:
        if "natureza" in c.lower():
            col_nat_oficial = c
            break

    dict_nat_oficial = {}
    if col_nat_oficial:
        for placa_c, df_p in df_manut.groupby("Placa_Clean"):
            nat_str = ", ".join([f"{n}: R$ {v:.2f}" for n, v in df_p.groupby(col_nat_oficial)["ValorTotal"].sum().items() if v > 0])
            dict_nat_oficial[placa_c] = nat_str

    df_fkm["Only_Manut_FKM"] = df_fkm["Lataria e Pintura"] + df_fkm["Manutenção em Geral"] + df_fkm["Rodas / Pneus"]

    df_comp_manut = df_fkm[["Placa_Clean", "Placa", "Lataria e Pintura", "Manutenção em Geral", "Rodas / Pneus", "Only_Manut_FKM"]]
    df_comp_manut = df_comp_manut.merge(df_manut_agg, on="Placa_Clean", how="outer").fillna(0)
    df_comp_manut["Diff_Manut"] = df_comp_manut["Only_Manut_FKM"] - df_comp_manut["Manut_Source_Total"]

    # Para filiais com manutenção por fora (fundo fixo), registrar diferenças sem gerar erro
    filial_manut_por_fora = branch_name in FILIAIS_MANUT_POR_FORA

    for _, r in df_comp_manut.iterrows():
        placa = r["Placa_Clean"]
        if placa not in fkm_plates:
            continue

        diff_manut = r["Diff_Manut"]

        if abs(diff_manut) > 1.0: # Margem de R$ 1.00
            # Montar detalhamento das 3 colunas preenchidas pelo gerente
            partes_fkm = []
            if r["Lataria e Pintura"] > 0:
                partes_fkm.append(f"Lataria: R$ {r['Lataria e Pintura']:.2f}")
            if r["Manutenção em Geral"] > 0:
                partes_fkm.append(f"Manut. Geral: R$ {r['Manutenção em Geral']:.2f}")
            if r["Rodas / Pneus"] > 0:
                partes_fkm.append(f"Pneus: R$ {r['Rodas / Pneus']:.2f}")
            
            detalhe_fkm_str = " + ".join(partes_fkm) if partes_fkm else "Total: R$ 0.00"
            detalhe_oficial_str = dict_nat_oficial.get(placa, "")
            sufixo_oficial = f" ({detalhe_oficial_str})" if detalhe_oficial_str else ""

            if diff_manut > 1.0:
                # Diferença positiva (FKM > Oficial) -> fundo fixo
                if filial_manut_por_fora:
                    valores_corretos["manut_por_fora"].append({
                        "placa": placa,
                        "valor_fkm": r['Only_Manut_FKM'],
                        "valor_oficial": r['Manut_Source_Total'],
                        "valor_fundo_fixo": diff_manut
                    })
                else:
                    erros.append(f"Manutenção Placa {placa}: Valor preenchido MAIOR que o oficial! Preenchido: R$ {r['Only_Manut_FKM']:.2f} [{detalhe_fkm_str}] | Oficial: R$ {r['Manut_Source_Total']:.2f}{sufixo_oficial} (Dif: R$ {diff_manut:.2f})")
            else:
                # Diferença negativa (FKM < Oficial) -> erro de lançamento/faltou nota
                erros.append(f"Manutenção Placa {placa}: Valor preenchido MENOR que o oficial! Preenchido: R$ {r['Only_Manut_FKM']:.2f} [{detalhe_fkm_str}] | Oficial: R$ {r['Manut_Source_Total']:.2f}{sufixo_oficial} (Dif: R$ {diff_manut:.2f})")
            
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
                # Divergências de km sem inversão são toleráveis - removido aviso

        # 2. Checar Km Final - divergências toleráveis, removido aviso
                
        # 3. Checar cálculo interno da planilha (Km Final - Km Inicial != Total de Km)
        for _, r in df_comp_km.iterrows():
            placa = r["Placa_Clean"]
            diff_calc = abs((r["Km Final"] - r["Km Inicial"]) - r["Total de Km"])
            if diff_calc > 1.0: # Margem de tolerância
                erros.append(f"Cálculo Km Placa {placa}: Km Final ({r['Km Final']:.0f}) - Km Inicial ({r['Km Inicial']:.0f}) = {(r['Km Final'] - r['Km Inicial']):.0f}, mas a coluna Total Km diz {r['Total de Km']:.0f}.")
                
    # --- E. Verificar placas de EXCECOES_MANUTENCAO que têm custo NF mas não foram declaradas no FKM ---
    # Carregar manutenção oficial completa (não filtrada por filial) para checar exceções
    df_manut_raw = pd.read_excel(config.ARQUIVO_ENTRADA_MANUTENCAO)
    df_manut_raw["Placa_Clean"] = df_manut_raw["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()

    def _sigla(nome):
        """Extrai e normaliza a sigla de um nome de filial para comparação."""
        return nome.split("- ")[-1].strip().upper().replace("(", "").replace(")", "").replace(" ", "")

    for placa_exc, filial_exc in EXCECOES_MANUTENCAO.items():
        # Só verificar se o FKM auditado é da filial destino desta exceção (compara por sigla)
        if _sigla(folder_name) != _sigla(filial_exc):
            continue

        # Verificar se há custo NF para esta placa
        df_exc = df_manut_raw[df_manut_raw["Placa_Clean"] == placa_exc]
        valor_nf = df_exc["ValorTotal"].sum()
        if valor_nf <= 0:
            continue

        # Verificar se o gestor declarou essa placa no FKM
        valor_fkm_dec = 0.0
        if placa_exc in fkm_plates:
            linha_fkm = df_fkm[df_fkm["Placa_Clean"] == placa_exc]
            if not linha_fkm.empty:
                valor_fkm_dec = float(
                    linha_fkm["Only_Manut_FKM"].sum()
                    if "Only_Manut_FKM" in linha_fkm.columns
                    else (
                        linha_fkm.get("Lataria e Pintura", pd.Series([0])).sum()
                        + linha_fkm.get("Manutenção em Geral", pd.Series([0])).sum()
                        + linha_fkm.get("Rodas / Pneus", pd.Series([0])).sum()
                    )
                )

        if abs(valor_fkm_dec - valor_nf) > 1.0:
            itens = df_exc["DescricaoItem"].tolist() if "DescricaoItem" in df_exc.columns else []
            itens_str = " | ".join(itens[:3]) + (f" (+{len(itens)-3} itens)" if len(itens) > 3 else "")
            erros.append(
                f"⚠️  CUSTO DE EXCEÇÃO NÃO DECLARADO — Placa {placa_exc}: "
                f"Manutenção realizada em outra filial e redirecionada para {filial_exc} via mapeamento. "
                f"Sistema (NF): R$ {valor_nf:,.2f} | FKM declarado: R$ {valor_fkm_dec:,.2f}. "
                f"Itens: {itens_str}. "
                f"O gestor deve declarar R$ {valor_nf:,.2f} no FKM desta placa."
            )

    return branch_name, erros, avisos, valores_corretos

def main():
    print("=" * 80)
    print(f"🕵️  SISTEMA DE AUDITORIA E VALIDAÇÃO DE RETORNOS DE FKM - {config.MES}/{config.ANO}")
    print("=" * 80)
    
    pasta_retorno = os.path.join(config.PROJECT_ROOT, "dados", "retornados")
    
    if not os.path.exists(pasta_retorno):
        print(f"❌ Diretório de retornos não encontrado em: {pasta_retorno}")
        print("Crie esta pasta e insira os FKMs enviados pelas filiais para auditoria.")
        return
        
    # Buscar apenas arquivos .xls (formato antigo do Excel, não .xlsx)
    arquivos = glob.glob(os.path.join(pasta_retorno, "*.xls"))
    # Filtrar arquivos temporários ou metadados de sistema (como Zone.Identifier ou arquivos temporários do Office)
    arquivos = [
        a for a in arquivos
        if "Zone.Identifier" not in a
        and not os.path.basename(a).startswith("~$")
        and not os.path.basename(a).startswith(".")
        and not a.endswith(".bak")
    ]
    
    if not arquivos:
        print(f"⚠️  Nenhum arquivo FKM (.xls) localizado na pasta dados/retornados/.")
        return
        
    mes_ano_cod = f"{config.obter_numero_mes()}{config.ANO[-2:]}" # Ex: 0526

    # Processar todos os arquivos primeiro (silenciosamente)
    resultados = []

    for arq in sorted(arquivos):
        nome_arq = os.path.basename(arq)
        branch_name, erros, avisos, valores_corretos = auditar_arquivo(arq, mes_ano_cod)

        # Status binário: APROVADO (sem erros) ou REJEITADO (com erros)
        # Avisos são apenas informativos e NÃO afetam o status
        status = "REJEITADO" if erros else "APROVADO"

        resultados.append({
            "arquivo": nome_arq,
            "filial": branch_name or "Desconhecido",
            "status": status,
            "erros": erros,
            "avisos": avisos,
            "valores_corretos": valores_corretos
        })

    # Separar por status (apenas aprovados e rejeitados)
    aprovados = [r for r in resultados if r["status"] == "APROVADO"]
    rejeitados = [r for r in resultados if r["status"] == "REJEITADO"]

    # ========== EXIBIR APROVADOS ==========
    if aprovados:
        print(f"\n{GREEN}{'=' * 80}{RESET}")
        print(f"{GREEN}{BOLD}✅ FILIAIS APROVADAS ({len(aprovados)}){RESET}")
        print(f"{GREEN}{'=' * 80}{RESET}\n")

        for r in aprovados:
            print(f"  {GREEN}✓{RESET} {r['filial']}")

    # ========== EXIBIR REJEITADOS ==========
    if rejeitados:
        print(f"\n{RED}{'=' * 80}{RESET}")
        print(f"{RED}{BOLD}🚨 FILIAIS REJEITADAS ({len(rejeitados)}){RESET}")
        print(f"{RED}{'=' * 80}{RESET}")

        for r in rejeitados:
            print(f"\n{RED}{'─' * 80}{RESET}")
            print(f"📄 {r['arquivo']}")
            print(f"   Filial: {BOLD}{r['filial']}{RESET}")
            print(f"{RED}{'─' * 80}{RESET}")

            print(f"\n{RED}❌ ERROS ({len(r['erros'])}):${RESET}")
            for err in r["erros"]:
                print(f"  • {err}")

            # Exibir valores para correção
            valores = r["valores_corretos"]
            if valores and (valores["placas_faltantes"] or valores["placas_extras"] or valores["combustivel"]):
                print(f"\n{BLUE}📋 VALORES PARA CORREÇÃO:{RESET}")

                if valores["placas_faltantes"]:
                    print(f"\n  {BOLD}🚗 PLACAS FALTANTES:{RESET}")
                    for p in valores["placas_faltantes"]:
                        print(f"    • {p['placa']} - {p['modelo']}")
                        if p['litros'] > 0 or p['valor_comb'] > 0:
                            print(f"      Combustível: {p['litros']:.2f}L = R$ {p['valor_comb']:.2f}")
                        if p['arla'] > 0:
                            print(f"      Arla: R$ {p['arla']:.2f}")
                        if p['manutencao'] > 0:
                            print(f"      Manutenção: R$ {p['manutencao']:.2f}")

                if valores["placas_extras"]:
                    print(f"\n  {BOLD}⚠️  PLACAS EXTRAS:{RESET}")
                    for p in valores["placas_extras"]:
                        if p['sugestao']:
                            print(f"    • {p['placa']} → Corrigir para: {p['sugestao']}")
                        else:
                            print(f"    • {p['placa']} → Remover")

                if valores["combustivel"]:
                    print(f"\n  {BOLD}⛽ COMBUSTÍVEL:{RESET}")
                    for c in valores["combustivel"]:
                        print(f"    • {c['placa']} - {c['tipo']}: {c['valor_fkm']:.2f} → {c['valor_oficial']:.2f}")

    # ========== MANUTENÇÕES COM FUNDO FIXO ==========
    filiais_com_manut_fora = []
    for r in resultados:
        if r["valores_corretos"]["manut_por_fora"]:
            filiais_com_manut_fora.append(r)

    if filiais_com_manut_fora:
        print(f"\n{YELLOW}{'=' * 80}{RESET}")
        print(f"{YELLOW}{BOLD}🔧 MANUTENÇÕES COM FUNDO FIXO (Emergenciais sem NF){RESET}")
        print(f"{YELLOW}{'=' * 80}{RESET}")
        print(f"{YELLOW}Filiais que fazem manutenções emergenciais fora do sistema oficial{RESET}\n")

        total_geral_fundo_fixo = 0

        for r in filiais_com_manut_fora:
            print(f"{YELLOW}{'─' * 80}{RESET}")
            print(f"📄 {r['arquivo']}")
            print(f"   Filial: {BOLD}{r['filial']}{RESET}")
            print(f"{YELLOW}{'─' * 80}{RESET}\n")

            total_filial_fundo_fixo = 0

            print(f"  {'Placa':<12} {'Oficial (NF)':<15} {'FKM Total':<15} {'Fundo Fixo':<15}")
            print(f"  {'-' * 60}")

            for manut in r["valores_corretos"]["manut_por_fora"]:
                total_filial_fundo_fixo += manut['valor_fundo_fixo']
                total_geral_fundo_fixo += manut['valor_fundo_fixo']

                print(f"  {manut['placa']:<12} R$ {manut['valor_oficial']:>10.2f}  R$ {manut['valor_fkm']:>10.2f}  R$ {manut['valor_fundo_fixo']:>10.2f}")

            print(f"  {'-' * 60}")
            print(f"  {'TOTAL FILIAL:':<28} {'':<15} R$ {total_filial_fundo_fixo:>10.2f}\n")

        print(f"{YELLOW}{'=' * 80}{RESET}")
        print(f"{YELLOW}{BOLD}💰 TOTAL GERAL FUNDO FIXO: R$ {total_geral_fundo_fixo:,.2f}{RESET}")
        print(f"{YELLOW}{'=' * 80}{RESET}")

    # ========== ABASTECIMENTOS POR FORA ==========
    # Consolidar abastecimentos por fora de todas as filiais
    filiais_com_abast_fora = []
    for r in resultados:
        if r["valores_corretos"]["abast_por_fora"]:
            filiais_com_abast_fora.append(r)

    if filiais_com_abast_fora:
        print(f"\n{CYAN}{'=' * 80}{RESET}")
        print(f"{CYAN}{BOLD}⛽ ABASTECIMENTOS POR FORA (Não centralizados no prestador){RESET}")
        print(f"{CYAN}{'=' * 80}{RESET}")
        print(f"{CYAN}Filiais que abastecem fora do prestador principal - Valores para mapeamento e cobrança{RESET}\n")

        total_geral_por_fora = 0

        for r in filiais_com_abast_fora:
            print(f"{CYAN}{'─' * 80}{RESET}")
            print(f"📄 {r['arquivo']}")
            print(f"   Filial: {BOLD}{r['filial']}{RESET}")
            print(f"{CYAN}{'─' * 80}{RESET}\n")

            total_filial_por_fora = 0

            print(f"  {'Placa':<12} {'Prestador':<15} {'FKM Total':<15} {'Por Fora':<15}")
            print(f"  {'-' * 60}")

            for abast in r["valores_corretos"]["abast_por_fora"]:
                # Só mostrar se tiver diferença significativa
                if abs(abast['valor_por_fora']) > 1.0:
                    total_filial_por_fora += abast['valor_por_fora']
                    total_geral_por_fora += abast['valor_por_fora']

                    print(f"  {abast['placa']:<12} R$ {abast['valor_oficial']:>10.2f}  R$ {abast['valor_fkm']:>10.2f}  R$ {abast['valor_por_fora']:>10.2f}")

            print(f"  {'-' * 60}")
            print(f"  {'TOTAL FILIAL:':<28} {'':<15} R$ {total_filial_por_fora:>10.2f}\n")

        print(f"{CYAN}{'=' * 80}{RESET}")
        print(f"{CYAN}{BOLD}💰 TOTAL GERAL POR FORA: R$ {total_geral_por_fora:,.2f}{RESET}")
        print(f"{CYAN}{'=' * 80}{RESET}")

    # ========== CUSTOS DE EXCEÇÃO PENDENTES (independente dos FKMs recebidos) ==========
    _exibir_excecoes_manutencao_pendentes(resultados)

    # ========== RESUMO FINAL ==========
    print(f"\n{'=' * 80}")
    print(f"{BOLD}📊 RESUMO FINAL{RESET}")
    print(f"{'=' * 80}")
    print(f"  {GREEN}✅ Aprovados: {len(aprovados)}{RESET}")
    print(f"  {RED}🚨 Rejeitados: {len(rejeitados)}{RESET}")
    if filiais_com_manut_fora:
        print(f"  {YELLOW}🔧 Com fundo fixo: {len(filiais_com_manut_fora)} ({BOLD}R$ {total_geral_fundo_fixo:,.2f}{RESET}{YELLOW}){RESET}")
    if filiais_com_abast_fora:
        print(f"  {CYAN}⛽ Com abast. por fora: {len(filiais_com_abast_fora)} ({BOLD}R$ {total_geral_por_fora:,.2f}{RESET}{CYAN}){RESET}")
    print(f"{'=' * 80}")

def _exibir_excecoes_manutencao_pendentes(resultados):
    """
    Verifica todas as placas em EXCECOES_MANUTENCAO e exibe um alerta claro
    para cada placa cujo custo oficial (NF) não foi declarado ou foi declarado incorretamente
    no FKM da filial destino. Só exibe se houver divergência real.
    """
    ORANGE = "\033[38;5;208m"

    def _sigla(nome):
        return nome.split("- ")[-1].strip().upper().replace("(", "").replace(")", "").replace(" ", "")

    df_manut_raw = pd.read_excel(config.ARQUIVO_ENTRADA_MANUTENCAO)
    df_manut_raw["Placa_Clean"] = df_manut_raw["Placa"].astype(str).str.replace("-", "", regex=False).str.strip().str.upper()

    # Mapear folder_name → resultado do auditar_arquivo (contém erros já processados)
    fkms_recebidos = {}
    for r in resultados:
        folder_name_r = MAPA_FILIAIS_NOME_PASTA.get(r["filial"])
        if folder_name_r:
            fkms_recebidos[folder_name_r] = r

    # Para cada placa de exceção, verificar se o valor NF foi corretamente declarado no FKM
    # A seção E de auditar_arquivo já adiciona erro quando há divergência
    # Aqui extraímos esses erros para exibição consolidada + casos de FKM ainda não recebido
    alertas_pendentes = []

    for placa_exc, filial_exc in EXCECOES_MANUTENCAO.items():
        df_exc = df_manut_raw[df_manut_raw["Placa_Clean"] == placa_exc]
        valor_nf = df_exc["ValorTotal"].sum()
        if valor_nf <= 0:
            continue

        # Encontrar folder_name da filial destino via sigla
        folder_exc = None
        sufixo = filial_exc.split("- ")[-1].strip()
        for nome, pasta in MAPA_FILIAIS_NOME_PASTA.items():
            if _sigla(pasta) == _sigla(filial_exc):
                folder_exc = pasta
                break

        fkm_recebido = folder_exc in fkms_recebidos if folder_exc else False

        if not fkm_recebido:
            # FKM ainda não chegou — alerta de pendência
            alertas_pendentes.append({
                "placa": placa_exc,
                "filial": filial_exc,
                "valor_nf": valor_nf,
                "valor_declarado": None,
                "status": "sem_fkm",
                "descricao_itens": df_exc["DescricaoItem"].tolist() if "DescricaoItem" in df_exc.columns else [],
            })
        else:
            # FKM recebido — verificar se a seção E gerou erro para esta placa
            r = fkms_recebidos[folder_exc]
            erro_exc = next(
                (e for e in r["erros"] if "CUSTO DE EXCEÇÃO" in e and placa_exc in e),
                None
            )
            if erro_exc:
                # Extrair valor declarado do erro gerado pela seção E
                alertas_pendentes.append({
                    "placa": placa_exc,
                    "filial": filial_exc,
                    "valor_nf": valor_nf,
                    "valor_declarado": 0.0,
                    "status": "nao_declarado",
                    "descricao_itens": df_exc["DescricaoItem"].tolist() if "DescricaoItem" in df_exc.columns else [],
                })
            # Se não há erro, o valor foi declarado corretamente → não aparece aqui

    if not alertas_pendentes:
        return

    print(f"\n{ORANGE}{'=' * 80}{RESET}")
    print(f"{ORANGE}{BOLD}⚠️  CUSTOS DE EXCEÇÃO — PENDENTES DE DECLARAÇÃO NO FKM{RESET}")
    print(f"{ORANGE}{'=' * 80}{RESET}")
    print(f"{ORANGE}Manutenções realizadas em outra filial, redirecionadas via mapeamento manual.")
    print(f"O gestor da filial destino NÃO visualiza essas OS no sistema e precisa ser informado.{RESET}\n")

    total_pendente = 0
    for alerta in alertas_pendentes:
        total_pendente += alerta["valor_nf"]
        if alerta["status"] == "sem_fkm":
            status_str = f"{RED}❌ FKM ainda NÃO recebido — não é possível confirmar declaração{RESET}"
        else:
            status_str = f"{RED}❌ FKM recebido mas placa NÃO declarada (valor: R$ 0,00){RESET}"

        itens = alerta["descricao_itens"]
        itens_str = " | ".join(itens[:5]) + (f" (+{len(itens)-5} itens)" if len(itens) > 5 else "")

        print(f"{ORANGE}{'─' * 80}{RESET}")
        print(f"  🚗 Placa:          {BOLD}{alerta['placa']}{RESET}")
        print(f"  📍 Filial destino: {BOLD}{alerta['filial']}{RESET}")
        print(f"  💰 Valor NF:       {BOLD}R$ {alerta['valor_nf']:,.2f}{RESET}")
        print(f"  📄 Status FKM:     {status_str}")
        if itens_str:
            print(f"  🔧 Itens OS:       {itens_str}")
        print(f"  👉 Ação:           Informar gestor para declarar R$ {alerta['valor_nf']:,.2f} no FKM da placa {alerta['placa']}")

    print(f"{ORANGE}{'─' * 80}{RESET}")
    print(f"{ORANGE}{BOLD}💰 TOTAL PENDENTE DE DECLARAÇÃO: R$ {total_pendente:,.2f}{RESET}")
    print(f"{ORANGE}{'=' * 80}{RESET}")



if __name__ == "__main__":
    main()
