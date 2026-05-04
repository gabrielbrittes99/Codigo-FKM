#!/usr/bin/env python3
"""
Script Orquestrador do Fechamento Mensal
Executa todas as etapas do fechamento de ponta a ponta.
"""

import os
import subprocess
import sys

from src import config


def executar_comando(comando, descricao):
    print("\n" + "=" * 80)
    print(f"🚀 INICIANDO: {descricao}")
    print("=" * 80)

    try:
        # Usa o python do ambiente virtual (.venv)
        python_exe = (
            os.path.join(".venv", "bin", "python")
            if os.path.exists(".venv")
            else sys.executable
        )

        # Executa o comando
        cmd = [python_exe, "-m", comando]
        processo = subprocess.run(cmd, check=True)

        print(f"\n✅ SUCESSO: {descricao}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERRO FATAL: Falha ao executar {descricao}.")
        print(f"Comando: {' '.join(cmd)}")
        print(f"Código de saída: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO durante {descricao}: {e}")
        return False


def main():
    print("=" * 80)
    print(f"🌟 INICIANDO FECHAMENTO MENSAL - {config.MES}/{config.ANO} 🌟")
    print("=" * 80)

    etapas = [
        (
            "src.extrair_dados_bluefleet",
            "1. Extração de Dados do Banco Bluefleet (Manutenção e Frota)",
        ),
        ("src.executar_resumos", "2. Geração dos Resumos de Combustível por Filial"),
        ("src.executar_manutencao", "3. Geração dos Resumos de Manutenção por Filial"),
        ("src.executar_frota", "4. Geração dos Resumos de Frota por Filial"),
        ("src.gerar_relatorio_kpis", "5. Geração do Relatório Consolidado de KPIs"),
    ]

    for modulo, descricao in etapas:
        sucesso = executar_comando(modulo, descricao)
        if not sucesso:
            print("\n⚠️ O processo de fechamento foi interrompido devido a um erro.")
            sys.exit(1)

    print("\n" + "=" * 80)
    print(f"🎉 FECHAMENTO DE {config.MES}/{config.ANO} CONCLUÍDO COM SUCESSO! 🎉")
    print("=" * 80)
    print(
        f"Todos os relatórios foram gerados na pasta: Dados Tratados/{config.MES} {config.ANO}/"
    )
    print(
        "================================================================================\n"
    )


if __name__ == "__main__":
    main()
