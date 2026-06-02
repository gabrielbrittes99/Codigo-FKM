"""
Script de Validação e Auditoria do Fechamento Mensal
Verifica consistência de dados, hodômetros, litragens e possíveis anomalias nos relatórios gerados.
"""

import os
import pandas as pd
import numpy as np
from src import config

def validar_combustivel(pasta_periodo):
    caminho_geral = os.path.join(config.DIRETORIO_BASE_SAIDA, pasta_periodo, f"{config.obter_numero_mes()}{config.ANO[-2:]} COMBUSTIVEL GRITSCH TRANSPORTES GERAL.xlsx")
    
    if not os.path.exists(caminho_geral):
        print(f"⚠️ Arquivo geral de combustível não encontrado em: {caminho_geral}")
        return []

    print(f"📖 Carregando arquivo de combustível geral para validação: {os.path.basename(caminho_geral)}")
    df = pd.read_excel(caminho_geral)
    
    anomalias = []
    
    # 1. Verificar valores negativos ou nulos onde não deveriam
    negativos_litros = df[df["Litragem"] < 0]
    if not negativos_litros.empty:
        for _, r in negativos_litros.iterrows():
            anomalias.append({
                "tabela": "Combustível",
                "placa": r["Placa"],
                "tipo": "Litragem Negativa",
                "detalhe": f"Data: {r['Data da transacao']} | Litros: {r['Litragem']} | Transação: {r['Transacao']}"
            })
            
    negativos_valor = df[df["Valor total"] < 0]
    if not negativos_valor.empty:
        for _, r in negativos_valor.iterrows():
            anomalias.append({
                "tabela": "Combustível",
                "placa": r["Placa"],
                "tipo": "Valor Negativo",
                "detalhe": f"Data: {r['Data da transacao']} | Valor: {r['Valor total']} | Transação: {r['Transacao']}"
            })

    # 2. Verificar abastecimentos individuais com litragem suspeita (> 600 litros para veículos normais, exceto se tanque gigante)
    abast_gigante = df[df["Litragem"] > 600]
    if not abast_gigante.empty:
        for _, r in abast_gigante.iterrows():
            anomalias.append({
                "tabela": "Combustível",
                "placa": r["Placa"],
                "tipo": "Litragem Muito Alta (>600L)",
                "detalhe": f"Data: {r['Data da transacao']} | Litros: {r['Litragem']} | Posto: {r['Estabelecimento']}"
            })

    # 3. Verificar inconsistências de Hodômetro (Diferença negativa ou distância percorrida absurda por abastecimento)
    # Ignora Arla 32 pois não mede consumo por km diretamente da mesma forma
    df_comb = df[~df["Combustivel"].str.contains("Arla", case=False, na=False)].copy()
    
    # Converter para numérico
    df_comb["Hodometro/Horimetro"] = pd.to_numeric(df_comb["Hodometro/Horimetro"], errors="coerce")
    df_comb["Hodometro/Horimetro anterior"] = pd.to_numeric(df_comb["Hodometro/Horimetro anterior"], errors="coerce")
    
    df_comb["Dif_Km"] = df_comb["Hodometro/Horimetro"] - df_comb["Hodometro/Horimetro anterior"]
    
    # Km negativo (Atual menor que anterior)
    km_negativo = df_comb[(df_comb["Dif_Km"] < 0) & (df_comb["Hodometro/Horimetro anterior"] > 0) & (df_comb["Hodometro/Horimetro"] > 0)]
    if not km_negativo.empty:
        for _, r in km_negativo.iterrows():
            anomalias.append({
                "tabela": "Combustível",
                "placa": r["Placa"],
                "tipo": "Hodômetro Invertido (KM atual < anterior)",
                "detalhe": f"Data: {r['Data da transacao']} | Anterior: {r['Hodometro/Horimetro anterior']} | Atual: {r['Hodometro/Horimetro']} | Dif: {r['Dif_Km']}"
            })
            
    # Km percorrido absurdo em um único abastecimento (> 4.000 km)
    km_absurdo = df_comb[(df_comb["Dif_Km"] > 4000) & (df_comb["Hodometro/Horimetro anterior"] > 0)]
    if not km_absurdo.empty:
        for _, r in km_absurdo.iterrows():
            anomalias.append({
                "tabela": "Combustível",
                "placa": r["Placa"],
                "tipo": "KM Percorrido Absurdo (>4000 km)",
                "detalhe": f"Data: {r['Data da transacao']} | Anterior: {r['Hodometro/Horimetro anterior']} | Atual: {r['Hodometro/Horimetro']} | Dif: {r['Dif_Km']}"
            })
            
    # 4. Verificar duplicidade de Transação
    duplicados = df[df.duplicated(subset=["Transacao"], keep=False)]
    if not duplicados.empty:
        ids_unicos = duplicados["Transacao"].unique()
        for tid in ids_unicos[:5]:  # Mostrar no máximo 5 no relatório
            placas_dup = duplicados[duplicados["Transacao"] == tid]["Placa"].tolist()
            anomalias.append({
                "tabela": "Combustível",
                "placa": ", ".join(placas_dup),
                "tipo": "Transação Duplicada",
                "detalhe": f"ID Transação: {tid} aparece múltiplas vezes"
            })

    return anomalias

def validar_manutencao(pasta_periodo):
    caminho_geral = os.path.join(config.DIRETORIO_BASE_SAIDA, pasta_periodo, f"{config.obter_numero_mes()}{config.ANO[-2:]} MANUTENÇÃO GRITSCH TRANSPORTES GERAL.xlsx")
    
    if not os.path.exists(caminho_geral):
        print(f"⚠️ Arquivo geral de manutenção não encontrado em: {caminho_geral}")
        return []

    print(f"📖 Carregando arquivo de manutenção geral para validação: {os.path.basename(caminho_geral)}")
    df = pd.read_excel(caminho_geral)
    
    anomalias = []
    
    # 1. Valores negativos ou nulos
    negativos_valor = df[df["ValorTotal"] < 0]
    if not negativos_valor.empty:
        for _, r in negativos_valor.iterrows():
            anomalias.append({
                "tabela": "Manutenção",
                "placa": r["Placa"],
                "tipo": "Valor Total Negativo",
                "detalhe": f"Ordem Servico: {r['OrdemServico']} | Descrição: {r['DescricaoItem']} | Valor: {r['ValorTotal']}"
            })
            
    # 2. OS sem filial definida (Matriz ou Rateio que não deveria estar)
    sem_filial = df[df["FILIAL"].isna() | (df["FILIAL"] == "")]
    if not sem_filial.empty:
        for _, r in sem_filial.iterrows():
            anomalias.append({
                "tabela": "Manutenção",
                "placa": r["Placa"],
                "tipo": "Filial Nula ou Vazia",
                "detalhe": f"Ordem Servico: {r['OrdemServico']} | Descrição: {r['DescricaoItem']}"
            })
            
    return anomalias

def main():
    print("=" * 80)
    print(f"🔍 INICIANDO AUDITORIA E VERIFICAÇÃO DE ANOMALIAS - {config.MES}/{config.ANO}")
    print("=" * 80)
    
    pasta_periodo = config.PASTA_PERIODO
    
    anomalias = []
    anomalias.extend(validar_combustivel(pasta_periodo))
    anomalias.extend(validar_manutencao(pasta_periodo))
    
    print("\n" + "=" * 80)
    print("📋 RELATÓRIO FINAL DE ANOMALIAS E INCONSISTÊNCIAS")
    print("=" * 80)
    
    if not anomalias:
        print("\n✅ NENHUMA ANOMALIA OU INCONSISTÊNCIA DETECTADA!")
        print("Os dados estão consistentes para envio.")
    else:
        print(f"\n⚠️ FORAM ENCONTRADAS {len(anomalias)} POSSÍVEIS ANOMALIAS:")
        df_anomalias = pd.DataFrame(anomalias)
        
        # Agrupar por tipo para melhor visualização
        for tipo, g in df_anomalias.groupby("tipo"):
            print(f"\n📌 Tipo: {tipo} ({len(g)} ocorrências)")
            for _, r in g.head(10).iterrows():
                print(f"   • Placa: {r['placa']:<8} | {r['detalhe']}")
            if len(g) > 10:
                print(f"   ... e mais {len(g) - 10} ocorrências deste tipo.")
                
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
