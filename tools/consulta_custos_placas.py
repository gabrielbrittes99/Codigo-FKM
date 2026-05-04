#!/usr/bin/env python3
"""
Consulta de custos (combustível + manutenção) por placa.
Retorna os valores totais e detalhamento por filial para diagnóstico.
"""

import os
import sys

import pandas as pd

# Adicionar o diretório raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.filial_mapping import EXCECOES_FORCADAS


def consultar_custos(placas):
    """Consulta custos de combustível e manutenção para uma lista de placas"""

    placas_normalizadas = [p.upper().replace("-", "").strip() for p in placas]

    print(f"\n📅 Período de fechamento: {config.MES}/{config.ANO}")
    print(f"📋 Placas consultadas: {', '.join(placas_normalizadas)}\n")

    # ======================== COMBUSTÍVEL ========================
    print("=" * 100)
    print("COMBUSTÍVEL")
    print("=" * 100)

    arquivo_comb = config.ARQUIVO_ENTRADA_COMBUSTIVEL
    df_comb_resultados = {}

    if arquivo_comb and os.path.exists(arquivo_comb):
        print(f"📁 Arquivo: {os.path.basename(arquivo_comb)}")
        df_comb = pd.read_excel(arquivo_comb)
        df_comb["Placa_Clean"] = (
            df_comb["Placa"]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )

        # Detectar coluna de valor
        colunas_valor_comb = [c for c in df_comb.columns if "valor" in c.lower() or "total" in c.lower()]
        print(f"   Colunas de valor encontradas: {colunas_valor_comb}")

        # Mostrar todas as colunas para referência
        print(f"   Todas as colunas: {list(df_comb.columns)}\n")

        for placa in placas_normalizadas:
            df_placa = df_comb[df_comb["Placa_Clean"] == placa]
            df_comb_resultados[placa] = df_placa

            print(f"\n  {'─' * 90}")
            print(f"  🚗 PLACA: {placa}")
            print(f"  {'─' * 90}")

            if len(df_placa) == 0:
                print(f"    ❌ Sem registros de combustível")
                continue

            print(f"    📊 Registros: {len(df_placa)}")

            # Garagem
            if "Garagem" in df_placa.columns:
                garagens = df_placa["Garagem"].value_counts()
                print(f"    🏢 Garagem(s):")
                for g, c in garagens.items():
                    print(f"       - {g}: {c} registros")

            # Exceção forçada?
            if placa in EXCECOES_FORCADAS:
                print(f"    ⚠️  EXCEÇÃO FORÇADA: custos vão para → {EXCECOES_FORCADAS[placa]}")

            # Valores
            for col_val in colunas_valor_comb:
                try:
                    total = pd.to_numeric(df_placa[col_val], errors='coerce').sum()
                    print(f"    💰 {col_val}: R$ {total:,.2f}")
                except:
                    pass

            # Datas
            if "Data da transacao" in df_placa.columns:
                datas = pd.to_datetime(df_placa["Data da transacao"], dayfirst=True, format='mixed', errors='coerce')
                print(f"    📅 Período: {datas.min().strftime('%d/%m/%Y') if pd.notna(datas.min()) else 'N/A'} a {datas.max().strftime('%d/%m/%Y') if pd.notna(datas.max()) else 'N/A'}")

            # Litros
            colunas_litros = [c for c in df_placa.columns if "litro" in c.lower() or "quantidade" in c.lower() or "volume" in c.lower()]
            for col_l in colunas_litros:
                try:
                    total_l = pd.to_numeric(df_placa[col_l], errors='coerce').sum()
                    print(f"    ⛽ {col_l}: {total_l:,.2f}")
                except:
                    pass

    else:
        print(f"⚠️  Arquivo de combustível NÃO encontrado!")

    # ======================== MANUTENÇÃO ========================
    print("\n\n" + "=" * 100)
    print("MANUTENÇÃO")
    print("=" * 100)

    arquivo_manut = config.ARQUIVO_ENTRADA_MANUTENCAO
    df_manut_resultados = {}

    if arquivo_manut and os.path.exists(arquivo_manut):
        print(f"📁 Arquivo: {os.path.basename(arquivo_manut)}")
        df_manut = pd.read_excel(arquivo_manut)
        df_manut["Placa_Clean"] = (
            df_manut["Placa"]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.strip()
            .str.upper()
        )

        # Detectar coluna de valor
        colunas_valor_manut = [c for c in df_manut.columns if "valor" in c.lower() or "total" in c.lower() or "custo" in c.lower()]
        print(f"   Colunas de valor encontradas: {colunas_valor_manut}")
        print(f"   Todas as colunas: {list(df_manut.columns)}\n")

        for placa in placas_normalizadas:
            df_placa = df_manut[df_manut["Placa_Clean"] == placa]
            df_manut_resultados[placa] = df_placa

            print(f"\n  {'─' * 90}")
            print(f"  🚗 PLACA: {placa}")
            print(f"  {'─' * 90}")

            if len(df_placa) == 0:
                print(f"    ❌ Sem registros de manutenção")
                continue

            print(f"    📊 Registros: {len(df_placa)}")

            # Filial
            if "FILIAL" in df_placa.columns:
                filiais = df_placa["FILIAL"].value_counts()
                print(f"    🏢 Filial(ais):")
                for f, c in filiais.items():
                    print(f"       - {f}: {c} registros")

            # Exceção forçada?
            if placa in EXCECOES_FORCADAS:
                print(f"    ⚠️  EXCEÇÃO FORÇADA: custos vão para → {EXCECOES_FORCADAS[placa]}")

            # Valores
            for col_val in colunas_valor_manut:
                try:
                    total = pd.to_numeric(df_placa[col_val], errors='coerce').sum()
                    print(f"    💰 {col_val}: R$ {total:,.2f}")
                except:
                    pass

            # Datas
            if "DataEmissao" in df_placa.columns:
                datas = pd.to_datetime(df_placa["DataEmissao"], dayfirst=True, format='mixed', errors='coerce')
                print(f"    📅 Período: {datas.min().strftime('%d/%m/%Y') if pd.notna(datas.min()) else 'N/A'} a {datas.max().strftime('%d/%m/%Y') if pd.notna(datas.max()) else 'N/A'}")

            # Tipo de serviço / Descrição
            colunas_servico = [c for c in df_placa.columns if "servi" in c.lower() or "descri" in c.lower() or "tipo" in c.lower()]
            for col_s in colunas_servico[:2]:  # Limitar a 2 colunas
                services = df_placa[col_s].value_counts().head(5)
                print(f"    📝 Top {col_s}:")
                for s, c in services.items():
                    print(f"       - {str(s)[:70]}: {c}x")

    else:
        print(f"⚠️  Arquivo de manutenção NÃO encontrado!")

    # ======================== RESUMO ========================
    print("\n\n" + "=" * 100)
    print("RESUMO CONSOLIDADO")
    print("=" * 100)
    print(f"\n{'Placa':<12} {'Combustível (R$)':>20} {'Manutenção (R$)':>20} {'TOTAL (R$)':>20} {'Filial FKM':<30}")
    print("─" * 105)

    for placa in placas_normalizadas:
        # Combustível total
        custo_comb = 0
        if placa in df_comb_resultados and len(df_comb_resultados[placa]) > 0:
            for col_val in colunas_valor_comb:
                try:
                    val = pd.to_numeric(df_comb_resultados[placa][col_val], errors='coerce').sum()
                    if val > custo_comb:
                        custo_comb = val
                except:
                    pass

        # Manutenção total
        custo_manut = 0
        if placa in df_manut_resultados and len(df_manut_resultados[placa]) > 0:
            for col_val in colunas_valor_manut:
                try:
                    val = pd.to_numeric(df_manut_resultados[placa][col_val], errors='coerce').sum()
                    if val > custo_manut:
                        custo_manut = val
                except:
                    pass

        # Filial
        filial = "N/A"
        if placa in EXCECOES_FORCADAS:
            filial = f"⚠️ {EXCECOES_FORCADAS[placa]} (FORÇADA)"
        elif placa in df_manut_resultados and len(df_manut_resultados[placa]) > 0 and "FILIAL" in df_manut_resultados[placa].columns:
            filial = df_manut_resultados[placa]["FILIAL"].mode().iloc[0] if len(df_manut_resultados[placa]["FILIAL"].mode()) > 0 else "N/A"
        elif placa in df_comb_resultados and len(df_comb_resultados[placa]) > 0 and "Garagem" in df_comb_resultados[placa].columns:
            filial = df_comb_resultados[placa]["Garagem"].mode().iloc[0] if len(df_comb_resultados[placa]["Garagem"].mode()) > 0 else "N/A"

        total = custo_comb + custo_manut

        print(f"{placa:<12} {custo_comb:>20,.2f} {custo_manut:>20,.2f} {total:>20,.2f} {str(filial):<30}")

    print("─" * 105)
    print()


if __name__ == "__main__":
    placas = ["SDU9F54", "SEP6E19", "SEP3C30", "SFI4A19", "SFL9J84", "TAS4H02"]
    consultar_custos(placas)
