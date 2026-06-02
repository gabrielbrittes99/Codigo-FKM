"""
Script FINAL CORRIGIDO - Gerador de Resumos de Combustível
Versão com separação por tipo de combustível e hodômetros corretos
Com priorização de filial de manutenção sobre garagem
"""

import os

import numpy as np
import pandas as pd
from src.loaders.excel_loader import salvar_resumos_filial_excel
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Importar módulo de mapeamento de filiais
from src.filial_mapping import (
    aplicar_filial_manutencao,
    criar_mapa_filiais,
    normalizar_filial,
)


def limpar_e_converter_numero(valor):
    """
    Converte valores com vírgula decimal para float
    """
    if pd.isna(valor):
        return np.nan

    if isinstance(valor, (int, float)):
        return float(valor)

    valor_str = str(valor).strip()
    valor_str = valor_str.replace("R$", "").replace(" ", "")

    if "." in valor_str and "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    elif "," in valor_str:
        valor_str = valor_str.replace(",", ".")
    elif "." in valor_str:
        # Remove ponto (separador de milhar) para manter apenas dígitos
        valor_str = valor_str.replace(".", "")

    try:
        return float(valor_str)
    except:
        return np.nan


def limpar_e_converter_hodometro(valor):
    """
    Converte hodômetros - multiplica por 1000 se for decimal (corrige leitura do Excel)
    Exemplo: 120.655 vira 120655
    NÃO multiplica valores que já são inteiros (ex: 576.0 → 576)
    """
    if pd.isna(valor):
        return np.nan

    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and valor < 1000000 and valor != int(valor):
            return int(valor * 1000)
        return int(valor)

    valor_str = str(valor).strip()
    valor_str = valor_str.replace("R$", "").replace(" ", "")

    # Remove pontos e vírgulas
    valor_str = valor_str.replace(".", "").replace(",", "")

    try:
        return int(valor_str)
    except:
        return np.nan


def tratar_dados(df):
    """
    Trata os dados do DataFrame convertendo colunas numéricas corretamente
    """
    print("🔧 Tratando dados...")

    # Colunas de valores monetários e litragem
    colunas_numericas = ["Litragem", "Valor total", "Preco"]

    for col in colunas_numericas:
        if col in df.columns:
            print(f"   Convertendo: {col}")
            df[col] = df[col].apply(limpar_e_converter_numero)

    # Hodômetros precisam de tratamento especial
    colunas_hodometro = ["Hodometro/Horimetro", "Hodometro/Horimetro anterior"]

    for col in colunas_hodometro:
        if col in df.columns:
            print(f"   Convertendo hodômetro: {col}")
            df[col] = df[col].apply(limpar_e_converter_hodometro)

    print("✅ Dados tratados com sucesso!")
    return df


def substituir_freguesia_por_perus(df, coluna="Garagem"):
    """
    Substitui SAO (FREGUESIA) por SAO (PERUS) na coluna especificada
    """
    if coluna in df.columns:
        df[coluna] = df[coluna].str.replace(
            "SAO (FREGUESIA)", "SAO (PERUS)", regex=False
        )
        df[coluna] = df[coluna].str.replace("SAO FREGUESIA", "SAO PERUS", regex=False)
        print("🔄 SAO (FREGUESIA) substituído por SAO (PERUS)")
    return df


def corrigir_filial_por_posto(
    df, coluna_filial="Filial_Final", coluna_estabelecimento="Estabelecimento"
):
    """
    Corrige a filial com base no posto de abastecimento
    APENAS para registros que estão em CSC
    Postos específicos de CSC devem ser realocados para filiais corretas
    """
    # Mapeamento de postos para filiais
    MAPA_POSTOS_GERAL = {
        "AUTO POSTO PRA FRENTE BRASIL": "GRITSCH - CWB (BASE)",
    }

    # Mapeamento de postos para filiais (APENAS quando estiver em CSC)
    MAPA_POSTOS_CSC = {
        "GP POSTOS - POSTO SAO JOSE": "GRITSCH - CWB (BASE)",
        "GP POSTOS - POSTO TREVO": "GRITSCH - PBC",
        "POSTO BARAO MATRIZ|| REDE BARAO": "GRITSCH - CWB (BASE)",
        "POSTO COPA": "GRITSCH - GPA",
        "SIM REDE - CAMAQUA PARADOURO 0071-94 - CENTRO RS": "GRITSCH - POA",
        "SIM REDE - TC LITORAL 0040-98 - SC SUL": "GRITSCH - POA",
    }

    if coluna_estabelecimento not in df.columns or coluna_filial not in df.columns:
        return df

    registros_corrigidos = 0

    # 1. Aplicar correções gerais (independente da filial atual)
    for posto, filial_correta in MAPA_POSTOS_GERAL.items():
        mask = df[coluna_estabelecimento] == posto
        registros_afetados = mask.sum()
        if registros_afetados > 0:
            df.loc[mask, coluna_filial] = filial_correta
            registros_corrigidos += registros_afetados
            print(
                f"   📍 GERAL: {posto[:35]}... → {filial_correta} ({registros_afetados} reg)"
            )

    # 2. Aplicar correções específicas de CSC
    for posto, filial_correta in MAPA_POSTOS_CSC.items():
        # Aplica APENAS quando a filial atual é CSC E o posto bate
        mask = (df[coluna_filial] == "GRITSCH - CSC") & (
            df[coluna_estabelecimento] == posto
        )

        registros_afetados = mask.sum()
        if registros_afetados > 0:
            df.loc[mask, coluna_filial] = filial_correta
            registros_corrigidos += registros_afetados
            print(
                f"   📍 CSC: {posto[:35]}... → {filial_correta} ({registros_afetados} reg)"
            )

    if registros_corrigidos > 0:
        print(f"🔄 {registros_corrigidos} registros de CSC realocados por posto")

    return df


def gerar_resumos_filial(df_filial, nome_filial, caminho_saida):
    return salvar_resumos_filial_excel(df_filial, nome_filial, caminho_saida)


from src import config


def main():
    # ==================== CONFIGURAÇÕES ====================
    print("=" * 80)
    print(f"GERADOR DE RESUMOS DE COMBUSTÍVEL - {config.MES}/{config.ANO}")
    print("=" * 80)

    arquivo_excel = config.ARQUIVO_ENTRADA_COMBUSTIVEL
    nome_coluna_filial = "Garagem"
    prefixo_saida = "Combustivel - "
    nome_da_aba = "Sheet1"

    print(f"\n📁 Arquivo de entrada: {os.path.basename(arquivo_excel)}")
    print(
        f"📁 Pasta de destino: {os.path.join(config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO)}"
    )

    # ==================== PROCESSAMENTO ====================

    if not os.path.exists(arquivo_excel):
        print(f"\n❌ ERRO: O arquivo '{arquivo_excel}' não foi encontrado.")
        print("Verifique se o nome do arquivo está correto no config.py")
    else:
        try:
            print(f"\n🔄 Lendo o arquivo '{os.path.basename(arquivo_excel)}'...")
            df = pd.read_excel(arquivo_excel, sheet_name=nome_da_aba)
            print("✅ Leitura concluída com sucesso.")

            df = tratar_dados(df)

            # ==================== MAPEAMENTO DE FILIAIS ====================
            print("\n" + "=" * 80)
            print("APLICANDO PRIORIZAÇÃO DE FILIAL DE MANUTENÇÃO COM LÓGICA TEMPORAL")
            print("=" * 80)

            # Criar mapa de filiais a partir da planilha de manutenção
            arquivo_manutencao = config.ARQUIVO_ENTRADA_MANUTENCAO
            if arquivo_manutencao and os.path.exists(arquivo_manutencao):
                historico_filiais = criar_mapa_filiais(arquivo_manutencao)

                # Aplicar filial de manutenção com lógica temporal
                df = aplicar_filial_manutencao(
                    df,
                    historico_filiais,
                    coluna_placa="Placa",
                    coluna_garagem="Garagem",
                    coluna_data="Data da transacao",
                )

                # Aplicar correções por posto (Ex: AUTO POSTO PRA FRENTE BRASIL)
                df = corrigir_filial_por_posto(df)

                # Usar Filial_Final para agrupamento
                nome_coluna_filial = "Filial_Final"

            else:
                print(f"⚠️ Arquivo de manutenção não encontrado.")
                print("   Usando coluna 'Garagem' original.")
                nome_coluna_filial = "Garagem"

            # Substituir SAO FREGUESIA por SAO PERUS
            df = substituir_freguesia_por_perus(df, nome_coluna_filial)

            if nome_coluna_filial not in df.columns:
                print(f"\n❌ ERRO: A coluna '{nome_coluna_filial}' não foi encontrada.")
            else:
                filiais_unicas = df[nome_coluna_filial].dropna().unique()

                if len(filiais_unicas) == 0:
                    print("\n⚠️ AVISO: Nenhuma filial encontrada.")
                else:
                    print(f"\n✅ {len(filiais_unicas)} filiais únicas encontradas")
                    print("\n" + "=" * 80)
                    print("GERANDO ARQUIVOS POR FILIAL")
                    print("=" * 80)

                    for idx, filial in enumerate(filiais_unicas, 1):
                        df_filial = df[df[nome_coluna_filial] == filial].copy()

                        # Criar pasta da filial
                        pasta_filial = config.obter_caminho_saida_filial(filial)
                        os.makedirs(pasta_filial, exist_ok=True)

                        nome_filial_limpo = "".join(
                            c for c in str(filial) if c.isalnum() or c in (" ", "_")
                        ).rstrip()
                        nome_arquivo_saida = f"{prefixo_saida}{nome_filial_limpo}.xlsx"
                        caminho_completo_saida = os.path.join(
                            pasta_filial, nome_arquivo_saida
                        )

                        print(f"\n[{idx}/{len(filiais_unicas)}] 📊 {filial}")
                        print(f"      Registros: {len(df_filial)}")
                        print(f"      Pasta: {filial}/")
                        print(f"      Gerando: {nome_arquivo_saida}")

                        if os.path.exists(caminho_completo_saida):
                            try:
                                os.remove(caminho_completo_saida)
                                print(f"      🗑️  Arquivo antigo removido")
                            except Exception as e:
                                print(f"      ⚠️  Não foi possível remover: {e}")
                                continue

                        gerar_resumos_filial(df_filial, filial, caminho_completo_saida)
                        print(f"      ✅ Concluído!")

                    print("\n" + "=" * 80)
                    print("SALVANDO ARQUIVO GERAL")
                    print("=" * 80)

                    # Nome dinâmico: MMAA COMBUSTIVEL...
                    mes_num = config.obter_numero_mes()
                    ano_short = config.ANO[-2:]
                    nome_arquivo_geral = f"{mes_num}{ano_short} COMBUSTIVEL GRITSCH TRANSPORTES GERAL.xlsx"
                    pasta_periodo = os.path.join(
                        config.DIRETORIO_BASE_SAIDA, config.PASTA_PERIODO
                    )
                    os.makedirs(pasta_periodo, exist_ok=True)
                    caminho_completo_geral = os.path.join(
                        pasta_periodo, nome_arquivo_geral
                    )

                    print(f"\n🔄 Salvando arquivo geral...")
                    df.to_excel(caminho_completo_geral, index=False, engine="openpyxl")
                    print(f"✅ Arquivo geral salvo!")

                    print("\n" + "=" * 80)
                    print("🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
                    print("=" * 80)
                    print(f"\n📁 Arquivos salvos em: {pasta_periodo}")
                    print(f"\n✨ Estrutura:")
                    print(f"   📂 {config.PASTA_PERIODO}/")
                    for filial in sorted(filiais_unicas):
                        nome_limpo = "".join(
                            c
                            for c in str(filial)
                            if c.isalnum() or c in (" ", "_", "-")
                        ).strip()
                        print(f"      📂 {nome_limpo}/")
                        print(f"         📋 Combustivel - *.xlsx")

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
