#!/usr/bin/env python3
"""
Diagnóstico de Placa - Mostra a lógica aplicada
"""

import os

import pandas as pd

import config
from filial_mapping import (
    EXCECOES_FORCADAS,
    aplicar_filial_manutencao,
    criar_mapa_filiais,
)


def diagnosticar_placa(placa_busca):
    """
    Mostra toda a lógica aplicada a uma placa específica
    """
    # Normalizar placa
    placa_normalizada = placa_busca.upper().replace("-", "").strip()

    print("=" * 80)
    print(f"DIAGNÓSTICO DE PLACA: {placa_busca}")
    print("=" * 80)
    print(f"\n🔍 Placa normalizada: {placa_normalizada}")

    # ETAPA 1: Verificar se é exceção forçada
    print("\n" + "=" * 80)
    print("ETAPA 1: EXCEÇÕES FORÇADAS")
    print("=" * 80)

    if placa_normalizada in EXCECOES_FORCADAS:
        filial_excecao = EXCECOES_FORCADAS[placa_normalizada]
        print(f"✅ ENCONTRADA em exceções forçadas!")
        print(f"   Filial definida: {filial_excecao}")
        print(f"\n📌 PRIORIDADE MÁXIMA: Esta placa SEMPRE vai para '{filial_excecao}'")
        print(f"   ⚠️  Ignora garagem original")
        print(f"   ⚠️  Ignora mapeamento de manutenção")
        print(f"   ⚠️  Ignora postos de abastecimento")
        return filial_excecao
    else:
        print(f"❌ NÃO encontrada em exceções forçadas")
        print(f"   → Continua para próxima etapa...")

    # ETAPA 2: Verificar mapeamento de manutenção
    print("\n" + "=" * 80)
    print("ETAPA 2: MAPEAMENTO DE MANUTENÇÃO")
    print("=" * 80)

    arquivo_manutencao = config.ARQUIVO_ENTRADA_MANUTENCAO

    if not os.path.exists(arquivo_manutencao):
        print(f"⚠️  Arquivo de manutenção não encontrado: {arquivo_manutencao}")
        print(f"   → Usaria garagem original")
        return None

    # Ler arquivo de manutenção
    df_manut = pd.read_excel(arquivo_manutencao)
    df_manut["Placa_Clean"] = (
        df_manut["Placa"]
        .astype(str)
        .str.replace("-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    # Buscar placa
    df_placa = df_manut[df_manut["Placa_Clean"] == placa_normalizada]

    if len(df_placa) == 0:
        print(f"❌ Placa NÃO encontrada no arquivo de manutenção")
        print(f"   → Usaria garagem original")
        return None

    print(f"✅ Placa encontrada no arquivo de manutenção!")
    print(f"   Registros: {len(df_placa)}")

    # Mostrar todas as filiais que aparecem
    filiais_manutencao = df_placa["FILIAL"].value_counts()
    print(f"\n   Distribuição de filiais nos registros de manutenção:")
    for filial, count in filiais_manutencao.items():
        print(f"      - {filial}: {count} registros")

    # Filial mais frequente (mode)
    filial_mode = df_placa["FILIAL"].mode()
    if len(filial_mode) > 0:
        filial_manutencao = filial_mode.iloc[0]
        print(f"\n   📊 Filial mais frequente (mode): {filial_manutencao}")

        # Verificar se é REFERÊNCIA
        if str(filial_manutencao).upper().startswith("REFERÊNCIA") or str(
            filial_manutencao
        ).upper().startswith("REFERENCIA"):
            print(f"\n   ⚠️  Filial é do tipo REFERÊNCIA")
            print(f"   → Estas filiais são IGNORADAS (empresa não usa Truckpag)")

            # Verificar exceção TBU9D20
            if (
                placa_normalizada == "TBU9D20"
                and "CURITIBA" in str(filial_manutencao).upper()
            ):
                print(
                    f"   ✅ EXCEÇÃO: Placa TBU9D20 pode ir para REFERÊNCIA CURITIBA (veículo compartilhado)"
                )
                return filial_manutencao
            else:
                print(f"   → Usaria garagem original")
                return None
        else:
            print(f"\n   ✅ Filial válida (GRITSCH, RATEIO, etc.)")
            print(f"   → Esta filial SUBSTITUI a garagem original")
            return filial_manutencao

    return None


def buscar_em_combustivel(placa_busca):
    """
    Busca a placa no arquivo de combustível
    """
    placa_normalizada = placa_busca.upper().replace("-", "").strip()

    print("\n" + "=" * 80)
    print("DADOS NO ARQUIVO DE COMBUSTÍVEL")
    print("=" * 80)

    arquivo_combustivel = config.ARQUIVO_ENTRADA_COMBUSTIVEL

    if not os.path.exists(arquivo_combustivel):
        print(f"⚠️  Arquivo de combustível não encontrado: {arquivo_combustivel}")
        return

    df_comb = pd.read_excel(arquivo_combustivel)
    df_comb["Placa_Clean"] = (
        df_comb["Placa"]
        .astype(str)
        .str.replace("-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    df_placa = df_comb[df_comb["Placa_Clean"] == placa_normalizada]

    if len(df_placa) == 0:
        print(f"❌ Placa NÃO encontrada no arquivo de combustível")
        return

    print(f"✅ Placa encontrada no arquivo de combustível!")
    print(f"   Registros de abastecimento: {len(df_placa)}")

    # Garagem original
    if "Garagem" in df_placa.columns:
        garagens = df_placa["Garagem"].value_counts()
        print(f"\n   Garagem(s) original(is):")
        for garagem, count in garagens.items():
            print(f"      - {garagem}: {count} registros")

    # Postos
    if "Estabelecimento" in df_placa.columns:
        postos = df_placa["Estabelecimento"].value_counts()
        print(f"\n   Posto(s) de abastecimento:")
        for posto, count in postos.head(5).items():
            print(f"      - {posto[:60]}: {count}x")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        placa = sys.argv[1]
    else:
        placa = "SFA6I76"  # Placa padrão para teste

    print(f"\n📋 Processando fechamento de: {config.MES}/{config.ANO}\n")

    filial_final = diagnosticar_placa(placa)
    buscar_em_combustivel(placa)

    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)

    if filial_final:
        print(f"\n✅ Filial Final Aplicada: {filial_final}")
        print(f"\n📌 Motivo: Exceção forçada (prioridade máxima)")
        print(f"   Definido em: filial_mapping.py → EXCECOES_FORCADAS")
    else:
        print(f"\n⚠️  Nenhuma filial especial aplicada")
        print(f"   → Seria usada a garagem original do arquivo de combustível")

    print("\n" + "=" * 80)
