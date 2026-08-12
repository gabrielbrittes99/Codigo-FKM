"""
Diagnóstico de Cobertura de Dados - Backfill B1 (Jan-Jun 2026)
Verifica dia a dia se há transações de combustível e pedágio no DW.
Identifica furos na coleta de informações.
"""

import os
import sys
import warnings
from datetime import date, timedelta
from collections import defaultdict

import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Carrega .env do projeto
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
for env_path in [
    os.path.join(PROJECT_ROOT, ".env"),
    "/home/gabriel/Projetos/codigo-FKM/.env"
]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

warnings.filterwarnings("ignore")


def obter_conexao_dw():
    host = os.getenv("DW_HOST")
    port = os.getenv("DW_PORT", "5432")
    db = os.getenv("DW_NAME")
    user = os.getenv("DW_USER")
    pwd = os.getenv("DW_PASSWORD")
    if not all([host, db, user, pwd]):
        raise EnvironmentError("Variáveis DW não configuradas no .env")
    return psycopg2.connect(host=host, port=port, database=db, user=user, password=pwd)


def diagnosticar_cobertura():
    print("=" * 70)
    print("🔍 DIAGNÓSTICO DE COBERTURA DE DADOS - 1º SEMESTRE 2026")
    print("=" * 70)

    conn = obter_conexao_dw()

    # ====== 1. COMBUSTÍVEL - contagem por dia ======
    print("\n⛽ Consultando COMBUSTÍVEL dia a dia (Jan-Jun 2026)...")
    query_comb = """
    SELECT data::date as dia,
           COUNT(*) as qtd_transacoes,
           COUNT(DISTINCT placa) as qtd_placas,
           SUM(valor::numeric) as total_valor,
           SUM(litragem::numeric) as total_litros
    FROM torre.gold_truckpag_combustivel
    WHERE servico = 'ABASTECIMENTO' AND transacao_estornada = false
      AND data >= '2026-01-01' AND data < '2026-07-01'
    GROUP BY data::date
    ORDER BY dia
    """
    df_comb = pd.read_sql(query_comb, conn)
    df_comb['dia'] = pd.to_datetime(df_comb['dia'])

    # ====== 2. PEDÁGIO - contagem por dia ======
    print("🛣️  Consultando PEDÁGIO dia a dia (Jan-Jun 2026)...")
    query_ped = """
    SELECT data::date as dia,
           COUNT(*) as qtd_transacoes,
           COUNT(DISTINCT placa) as qtd_placas,
           SUM(valor::numeric) as total_valor
    FROM torre.gold_truckpag_pedagio
    WHERE data >= '2026-01-01' AND data < '2026-07-01'
    GROUP BY data::date
    ORDER BY dia
    """
    df_ped = pd.read_sql(query_ped, conn)
    df_ped['dia'] = pd.to_datetime(df_ped['dia'])

    conn.close()

    # ====== 3. GERAR CALENDÁRIO COMPLETO ======
    start = date(2026, 1, 1)
    end = date(2026, 6, 30)
    todos_os_dias = []
    d = start
    while d <= end:
        todos_os_dias.append(d)
        d += timedelta(days=1)

    df_cal = pd.DataFrame({'dia': pd.to_datetime(todos_os_dias)})
    df_cal['dia_semana'] = df_cal['dia'].dt.day_name()
    df_cal['eh_domingo'] = df_cal['dia'].dt.dayofweek == 6

    # ====== 4. MERGE E IDENTIFICAR FUROS ======
    df_cal = df_cal.merge(
        df_comb[['dia', 'qtd_transacoes', 'qtd_placas', 'total_valor', 'total_litros']].rename(
            columns={
                'qtd_transacoes': 'comb_transacoes',
                'qtd_placas': 'comb_placas',
                'total_valor': 'comb_valor',
                'total_litros': 'comb_litros'
            }
        ),
        on='dia', how='left'
    )
    df_cal = df_cal.merge(
        df_ped[['dia', 'qtd_transacoes', 'qtd_placas', 'total_valor']].rename(
            columns={
                'qtd_transacoes': 'ped_transacoes',
                'qtd_placas': 'ped_placas',
                'total_valor': 'ped_valor'
            }
        ),
        on='dia', how='left'
    )

    df_cal = df_cal.fillna(0)

    # ====== 5. RESUMO POR MÊS ======
    meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho"}

    print("\n" + "=" * 70)
    print("📊 RESUMO POR MÊS")
    print("=" * 70)

    for mes_num, mes_nome in meses.items():
        df_mes = df_cal[df_cal['dia'].dt.month == mes_num]
        total_dias = len(df_mes)
        dias_com_comb = len(df_mes[df_mes['comb_transacoes'] > 0])
        dias_com_ped = len(df_mes[df_mes['ped_transacoes'] > 0])
        dias_sem_comb = total_dias - dias_com_comb
        dias_sem_ped = total_dias - dias_com_ped

        comb_total = df_mes['comb_valor'].sum()
        ped_total = df_mes['ped_valor'].sum()
        litros_total = df_mes['comb_litros'].sum()
        trans_comb = int(df_mes['comb_transacoes'].sum())
        trans_ped = int(df_mes['ped_transacoes'].sum())

        if dias_sem_comb == total_dias and comb_total == 0:
            status_comb = "🔴 SEM DADOS"
        elif dias_sem_comb > 5:
            status_comb = f"🟡 PARCIAL ({dias_sem_comb} dias sem dados)"
        elif dias_sem_comb > 0:
            status_comb = f"🟢 OK ({dias_sem_comb} dia(s) sem dados - pode ser domingo/feriado)"
        else:
            status_comb = "🟢 COMPLETO"

        if dias_sem_ped == total_dias and ped_total == 0:
            status_ped = "🔴 SEM DADOS"
        elif dias_sem_ped > 5:
            status_ped = f"🟡 PARCIAL ({dias_sem_ped} dias sem dados)"
        elif dias_sem_ped > 0:
            status_ped = f"🟢 OK ({dias_sem_ped} dia(s) sem dados - pode ser domingo/feriado)"
        else:
            status_ped = "🟢 COMPLETO"

        print(f"\n📅 {mes_nome} 2026:")
        print(f"  ⛽ Combustível: {status_comb}")
        print(f"     Transações: {trans_comb:,}  |  Valor: R$ {comb_total:,.2f}  |  Litros: {litros_total:,.0f}")
        print(f"     Dias com dados: {dias_com_comb}/{total_dias}")
        print(f"  🛣️  Pedágio: {status_ped}")
        print(f"     Transações: {trans_ped:,}  |  Valor: R$ {ped_total:,.2f}")
        print(f"     Dias com dados: {dias_com_ped}/{total_dias}")

    # ====== 6. LISTAR DIAS SEM DADOS (EXCETO DOMINGOS) ======
    print("\n" + "=" * 70)
    print("🚨 DIAS SEM TRANSAÇÕES DE COMBUSTÍVEL (exceto domingos)")
    print("=" * 70)

    dias_furo_comb = df_cal[(df_cal['comb_transacoes'] == 0) & (~df_cal['eh_domingo'])]
    if len(dias_furo_comb) == 0:
        print("✅ Nenhum furo encontrado (todos os dias úteis e sábados têm dados)")
    else:
        for mes_num, mes_nome in meses.items():
            furos_mes = dias_furo_comb[dias_furo_comb['dia'].dt.month == mes_num]
            if len(furos_mes) > 0:
                print(f"\n  📅 {mes_nome}:")
                for _, row in furos_mes.iterrows():
                    print(f"     ❌ {row['dia'].strftime('%d/%m/%Y')} ({row['dia_semana']})")

    print("\n" + "=" * 70)
    print("🚨 DIAS SEM TRANSAÇÕES DE PEDÁGIO (exceto domingos)")
    print("=" * 70)

    dias_furo_ped = df_cal[(df_cal['ped_transacoes'] == 0) & (~df_cal['eh_domingo'])]
    if len(dias_furo_ped) == 0:
        print("✅ Nenhum furo encontrado (todos os dias úteis e sábados têm dados)")
    else:
        for mes_num, mes_nome in meses.items():
            furos_mes = dias_furo_ped[dias_furo_ped['dia'].dt.month == mes_num]
            if len(furos_mes) > 0:
                print(f"\n  📅 {mes_nome}:")
                for _, row in furos_mes.iterrows():
                    print(f"     ❌ {row['dia'].strftime('%d/%m/%Y')} ({row['dia_semana']})")

    # ====== 7. ANÁLISE DE VOLUME (detectar dias com volume muito baixo) ======
    print("\n" + "=" * 70)
    print("📉 DIAS COM VOLUME ANORMALMENTE BAIXO DE COMBUSTÍVEL")
    print("   (menos de 20% da mediana do mês, excluindo domingos)")
    print("=" * 70)

    for mes_num, mes_nome in meses.items():
        df_mes = df_cal[(df_cal['dia'].dt.month == mes_num) & (~df_cal['eh_domingo']) & (df_cal['comb_transacoes'] > 0)]
        if len(df_mes) == 0:
            print(f"\n  📅 {mes_nome}: ⚠️ SEM DADOS para analisar")
            continue

        mediana = df_mes['comb_transacoes'].median()
        limiar = mediana * 0.2
        dias_baixos = df_mes[df_mes['comb_transacoes'] < limiar]

        if len(dias_baixos) > 0:
            print(f"\n  📅 {mes_nome} (mediana: {mediana:.0f} transações/dia):")
            for _, row in dias_baixos.iterrows():
                print(f"     ⚠️ {row['dia'].strftime('%d/%m/%Y')} ({row['dia_semana']}) - apenas {int(row['comb_transacoes'])} transações ({row['comb_transacoes']/mediana*100:.0f}% da mediana)")

    # ====== 8. RESUMO BIMESTRAL ======
    print("\n" + "=" * 70)
    print("📈 RESUMO BIMESTRAL CONSOLIDADO")
    print("=" * 70)

    bimestres = [
        ("B1", [1, 2], "Jan+Fev"),
        ("B2", [3, 4], "Mar+Abr"),
        ("B3", [5, 6], "Mai+Jun")
    ]

    for bim_nome, meses_list, desc in bimestres:
        df_bim = df_cal[df_cal['dia'].dt.month.isin(meses_list)]
        comb_val = df_bim['comb_valor'].sum()
        ped_val = df_bim['ped_valor'].sum()
        litros = df_bim['comb_litros'].sum()
        trans_c = int(df_bim['comb_transacoes'].sum())
        trans_p = int(df_bim['ped_transacoes'].sum())
        dias_c = len(df_bim[df_bim['comb_transacoes'] > 0])
        dias_p = len(df_bim[df_bim['ped_transacoes'] > 0])
        total_dias = len(df_bim)

        print(f"\n  📊 {bim_nome} ({desc}):")
        print(f"     ⛽ Combustível: R$ {comb_val:,.2f}  |  {trans_c:,} transações  |  {litros:,.0f} litros")
        print(f"        Cobertura: {dias_c}/{total_dias} dias")
        print(f"     🛣️  Pedágio:    R$ {ped_val:,.2f}  |  {trans_p:,} passagens")
        print(f"        Cobertura: {dias_p}/{total_dias} dias")

    print("\n" + "=" * 70)
    print("✅ Diagnóstico finalizado.")
    print("=" * 70)


if __name__ == "__main__":
    diagnosticar_cobertura()
