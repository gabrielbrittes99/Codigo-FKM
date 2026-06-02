import os
import sys

import pandas as pd

from src import config
from src.executar_resumos import (
    corrigir_filial_por_posto,
    gerar_resumos_filial,
    substituir_freguesia_por_perus,
    tratar_dados,
)
from src.filial_mapping import aplicar_filial_manutencao, criar_mapa_filiais


def gerar_relatorio_extra():
    print("=" * 80)
    print("GERANDO RELATÓRIO EXTRA - PADRÃO OFICIAL")
    print("=" * 80)

    placas_alvo = [
        "SFN2E86",
        "TAP2C35",
        "SEL5J84",
        "SFF9H69",
        "SFF9H68",
        "SFD5C31",
        "SFF9H66",
        "TAZ7D65",
        "TAV9E96",
        "UBO8H30",
        "SDU9F67",
        "SFM3H30",
        "SFI4A34",
        "UAV5J73",
        "TAP2C40",
        "SEK9C81",
        "UBR9B24",
        "TBI2068",
        "TBI2067",
        "UBR9B25",
        "RHQ4D40",
        "UBH2J71",
        "SEY5E62",
        "SDW8B50",
        "TBK1J24",
        "UBC1A56",
        "TBK1J46",
        "BDU6J33",
        "SFD5C32",
    ]

    arquivo_excel = config.ARQUIVO_ENTRADA_COMBUSTIVEL

    if not arquivo_excel or not os.path.exists(arquivo_excel):
        print(f"❌ Arquivo de combustível não encontrado.")
        return

    print(f"🔄 Lendo '{os.path.basename(arquivo_excel)}'...")
    df = pd.read_excel(arquivo_excel)

    # Aplicar o mesmo tratamento de dados oficial
    df = tratar_dados(df)

    # Mapeamento de Filiais oficial
    arquivo_manutencao = config.ARQUIVO_ENTRADA_MANUTENCAO
    if arquivo_manutencao and os.path.exists(arquivo_manutencao):
        print("🔄 Aplicando mapeamento de filiais...")
        historico_filiais = criar_mapa_filiais(arquivo_manutencao)
        df = aplicar_filial_manutencao(
            df,
            historico_filiais,
            coluna_placa="Placa",
            coluna_garagem="Garagem",
            coluna_data="Data da transacao",
        )
        df = corrigir_filial_por_posto(df)
        nome_coluna_filial = "Filial_Final"
    else:
        nome_coluna_filial = "Garagem"

    df = substituir_freguesia_por_perus(df, nome_coluna_filial)

    # Normalizar placa para filtragem
    if "Placa" in df.columns:
        df["Placa_Clean"] = (
            df["Placa"].astype(str).str.replace("-", "").str.strip().str.upper()
        )
    else:
        print("❌ Coluna 'Placa' não encontrada.")
        return

    # Filtrar pelas placas alvo
    df_filtrado = df[df["Placa_Clean"].isin(placas_alvo)].copy()

    if df_filtrado.empty:
        print("⚠️ Nenhuma transação encontrada para as placas alvo.")
        return

    # Remover a coluna auxiliar de Placa_Clean se não for do padrão original
    df_filtrado = df_filtrado.drop(columns=["Placa_Clean"])

    print(
        f"✅ Encontradas {len(df_filtrado)} transações para as {len(placas_alvo)} placas alvo."
    )

    # Caminho de saída
    pasta_saida = os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO)
    os.makedirs(pasta_saida, exist_ok=True)
    caminho_saida = os.path.join(
        pasta_saida, "Combustivel - PLACAS SELECIONADAS (Oficial).xlsx"
    )

    print(f"🔄 Gerando arquivo Excel com formatação oficial...")

    # Reutiliza a função oficial para gerar o excel com todas as abas e formatações exatas
    sucesso = gerar_resumos_filial(df_filtrado, "Placas Selecionadas", caminho_saida)

    if sucesso:
        print("=" * 80)
        print(f"🎉 RELATÓRIO EXTRA GERADO COM SUCESSO!")
        print(f"📁 Salvo em: {caminho_saida}")
        print("=" * 80)


if __name__ == "__main__":
    gerar_relatorio_extra()
