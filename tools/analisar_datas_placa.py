#!/usr/bin/env python3
"""
Analisa as datas de combustível e manutenção para uma placa específica
"""

import pandas as pd
import sys
from src import config

def analisar_datas_placa(placa_busca):
    placa_normalizada = placa_busca.upper().replace("-", "").strip()

    print("=" * 80)
    print(f"ANÁLISE DE DATAS - PLACA: {placa_busca}")
    print("=" * 80)
    print(f"\n📋 Período: {config.MES}/{config.ANO}")
    print(f"   Combustível: {config.ARQUIVO_ENTRADA_COMBUSTIVEL}")
    print(f"   Manutenção: {config.ARQUIVO_ENTRADA_MANUTENCAO}")

    # COMBUSTÍVEL
    print("\n📊 COMBUSTÍVEL:")
    try:
        df_comb = pd.read_excel(config.ARQUIVO_ENTRADA_COMBUSTIVEL)
        df_comb['Placa_Clean'] = df_comb['Placa'].astype(str).str.replace('-', '').str.strip().str.upper()
        df_placa_comb = df_comb[df_comb['Placa_Clean'] == placa_normalizada]
        
        if len(df_placa_comb) > 0:
            df_placa_comb['Data da transacao'] = pd.to_datetime(df_placa_comb['Data da transacao'], dayfirst=True, format='mixed')
            data_mais_recente_comb = df_placa_comb['Data da transacao'].max()
            garagem = df_placa_comb['Garagem'].mode()[0] if len(df_placa_comb['Garagem'].mode()) > 0 else "N/A"
            
            print(f"   Total de registros: {len(df_placa_comb)}")
            print(f"   Garagem: {garagem}")
            print(f"   Data mais recente: {data_mais_recente_comb.strftime('%d/%m/%Y')}")
            print(f"\n   Distribuição por data:")
            for data, count in df_placa_comb['Data da transacao'].value_counts().head(10).items():
                print(f"      - {data.strftime('%d/%m/%Y')}: {count} registros")
        else:
            print("   ❌ Placa não encontrada")
            data_mais_recente_comb = None
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        data_mais_recente_comb = None
    
    # MANUTENÇÃO
    print("\n🔧 MANUTENÇÃO:")
    try:
        df_manut = pd.read_excel(config.ARQUIVO_ENTRADA_MANUTENCAO)
        df_manut['Placa_Clean'] = df_manut['Placa'].astype(str).str.replace('-', '').str.strip().str.upper()
        df_placa_manut = df_manut[df_manut['Placa_Clean'] == placa_normalizada].copy()
        
        if len(df_placa_manut) > 0:
            df_placa_manut['DataEmissao'] = pd.to_datetime(df_placa_manut['DataEmissao'], dayfirst=True, format='mixed')
            data_mais_recente_manut = df_placa_manut['DataEmissao'].max()
            filial = df_placa_manut['FILIAL'].mode()[0] if len(df_placa_manut['FILIAL'].mode()) > 0 else "N/A"
            
            print(f"   Total de registros: {len(df_placa_manut)}")
            print(f"   Filial: {filial}")
            print(f"   Data mais recente: {data_mais_recente_manut.strftime('%d/%m/%Y')}")
            print(f"\n   Distribuição por data:")
            for data, count in df_placa_manut['DataEmissao'].value_counts().head(10).items():
                print(f"      - {data.strftime('%d/%m/%Y')}: {count} registros")
        else:
            print("   ❌ Placa não encontrada")
            data_mais_recente_manut = None
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        data_mais_recente_manut = None
    
    # COMPARAÇÃO
    print("\n" + "=" * 80)
    print("COMPARAÇÃO DE DATAS:")
    print("=" * 80)
    
    if data_mais_recente_comb and data_mais_recente_manut:
        print(f"\n   Combustível (mais recente): {data_mais_recente_comb.strftime('%d/%m/%Y')}")
        print(f"   Manutenção (mais recente):  {data_mais_recente_manut.strftime('%d/%m/%Y')}")
        
        if data_mais_recente_comb > data_mais_recente_manut:
            print(f"\n   ✅ COMBUSTÍVEL é mais recente!")
            print(f"   → Deveria usar: {garagem}")
        elif data_mais_recente_manut > data_mais_recente_comb:
            print(f"\n   ✅ MANUTENÇÃO é mais recente!")
            print(f"   → Deveria usar: {filial}")
        else:
            print(f"\n   ⚠️  Datas iguais - usar critério de manutenção")
            print(f"   → Deveria usar: {filial}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    placa = sys.argv[1] if len(sys.argv) > 1 else "SEH0B26"
    analisar_datas_placa(placa)
