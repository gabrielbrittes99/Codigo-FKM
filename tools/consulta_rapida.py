#!/usr/bin/env python3
"""Consulta rápida de custos por placa nos arquivos processados"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd

placas = ["SDU9F54", "SEP6E19", "SEP3C30", "SFI4A19", "SFL9J84", "TAS4H02"]
base = "/home/gabriel/projetos/codigo-FKM/Dados Tratados/Março 2026"

# Combustivel GERAL
arq_comb = os.path.join(base, "0326 COMBUSTIVEL GRITSCH TRANSPORTES GERAL.xlsx")
arq_manut = os.path.join(base, "0326 MANUTENÇÃO GRITSCH TRANSPORTES GERAL.xlsx")

print("=== COMBUSTÍVEL ===")
if os.path.exists(arq_comb):
    df = pd.read_excel(arq_comb)
    print(f"Colunas: {list(df.columns)}")
    dc = df.copy()
    dc["Placa_Clean"] = dc["Placa"].astype(str).str.replace("-","",regex=False).str.strip().str.upper()
    for p in placas:
        sub = dc[dc["Placa_Clean"] == p]
        if len(sub) > 0:
            print(f"\n{p}: {len(sub)} registros")
            # Tentar pegar valor e garagem/filial
            for c in sub.columns:
                if "valor" in c.lower() or "total" in c.lower():
                    print(f"  {c}: R$ {pd.to_numeric(sub[c], errors='coerce').sum():,.2f}")
                if "filial" in c.lower() or "garagem" in c.lower():
                    print(f"  {c}: {sub[c].value_counts().to_dict()}")
        else:
            print(f"\n{p}: SEM REGISTROS DE COMBUSTÍVEL")

print("\n\n=== MANUTENÇÃO ===")
if os.path.exists(arq_manut):
    df = pd.read_excel(arq_manut)
    print(f"Colunas: {list(df.columns)}")
    dm = df.copy()
    dm["Placa_Clean"] = dm["Placa"].astype(str).str.replace("-","",regex=False).str.strip().str.upper()
    for p in placas:
        sub = dm[dm["Placa_Clean"] == p]
        if len(sub) > 0:
            print(f"\n{p}: {len(sub)} registros")
            for c in sub.columns:
                if "valor" in c.lower() or "total" in c.lower():
                    print(f"  {c}: R$ {pd.to_numeric(sub[c], errors='coerce').sum():,.2f}")
                if "filial" in c.lower():
                    print(f"  {c}: {sub[c].value_counts().to_dict()}")
        else:
            print(f"\n{p}: SEM REGISTROS DE MANUTENÇÃO")
