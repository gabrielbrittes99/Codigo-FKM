"""
Configuração Automática e Baseada em YAML para Geração de FKMs
"""

import glob
import os
from datetime import datetime, timedelta

import yaml
from dotenv import load_dotenv

# Carrega variáveis de ambiente (DB_HOST, DB_USER, etc.) do arquivo .env
load_dotenv()

# ==================== CAMINHOS BASE ====================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carregar config.yaml
YAML_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
with open(YAML_PATH, "r", encoding="utf-8") as f:
    config_yaml = yaml.safe_load(f)

DIRETORIO_ENTRADA = os.path.join(PROJECT_ROOT, config_yaml["paths"]["input_dir"])
DIRETORIO_BASE_SAIDA = os.path.join(PROJECT_ROOT, config_yaml["paths"]["output_dir"])

# ==================== CONFIGURAÇÕES AUTOMÁTICAS ====================

def obter_mes_ano_fechamento():
    agora = datetime.now()
    primeiro_dia_mes_atual = agora.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    meses_pt = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    mes = meses_pt[ultimo_dia_mes_anterior.month]
    ano = str(ultimo_dia_mes_anterior.year)
    return mes, ano


def encontrar_arquivo_entrada(padrao):
    caminho_busca = os.path.join(DIRETORIO_ENTRADA, padrao)
    arquivos_encontrados = glob.glob(caminho_busca)
    if not arquivos_encontrados:
        return None
    if len(arquivos_encontrados) > 1:
        arquivos_encontrados.sort(key=os.path.getmtime, reverse=True)
    return arquivos_encontrados[0]


# ==================== VARIÁVEIS PRINCIPAIS ====================

MES, ANO = obter_mes_ano_fechamento()

ARQUIVO_ENTRADA_COMBUSTIVEL = encontrar_arquivo_entrada(config_yaml["patterns"]["fuel"])
ARQUIVO_ENTRADA_MANUTENCAO = encontrar_arquivo_entrada(
    config_yaml["patterns"]["maintenance"]
)
ARQUIVO_ENTRADA_FROTA = encontrar_arquivo_entrada(config_yaml["patterns"]["fleet"])

PASTA_PERIODO = f"{MES} {ANO}"

# ==================== FUNÇÕES AUXILIARES ====================


def obter_numero_mes():
    meses = {
        "Janeiro": "01",
        "Fevereiro": "02",
        "Março": "03",
        "Abril": "04",
        "Maio": "05",
        "Junho": "06",
        "Julho": "07",
        "Agosto": "08",
        "Setembro": "09",
        "Outubro": "10",
        "Novembro": "11",
        "Dezembro": "12",
    }
    return meses.get(MES, "00")


def obter_caminho_saida_filial(nome_filial):
    nome_limpo = "".join(
        c for c in str(nome_filial) if c.isalnum() or c in (" ", "_", "-")
    ).strip()
    return os.path.join(DIRETORIO_BASE_SAIDA, PASTA_PERIODO, nome_limpo)


def obter_caminho_saida_combustivel():
    return os.path.join(DIRETORIO_BASE_SAIDA, PASTA_PERIODO)


def obter_caminho_saida_manutencao():
    return os.path.join(DIRETORIO_BASE_SAIDA, PASTA_PERIODO)


def validar_configuracao():
    print("=" * 80)
    print(
        f"VALIDAÇÃO DE CONFIGURAÇÃO - {config_yaml['project']['name']} v{config_yaml['project']['version']}"
    )
    print("=" * 80)
    agora = datetime.now()
    meses_pt = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    mes_atual = meses_pt[agora.month]
    print(f"\n📅 Mês Atual: {mes_atual}/{agora.year}")
    print(f"📊 Processando Fechamento de: {MES}/{ANO}")
    valido = True
    if ARQUIVO_ENTRADA_COMBUSTIVEL and os.path.exists(ARQUIVO_ENTRADA_COMBUSTIVEL):
        print(
            f"\n✅ Arquivo de combustível encontrado: {os.path.basename(ARQUIVO_ENTRADA_COMBUSTIVEL)}"
        )
    else:
        print(f"\n❌ Arquivo de combustível não encontrado.")
        valido = False
    if ARQUIVO_ENTRADA_MANUTENCAO and os.path.exists(ARQUIVO_ENTRADA_MANUTENCAO):
        print(
            f"✅ Arquivo de manutenção encontrado: {os.path.basename(ARQUIVO_ENTRADA_MANUTENCAO)}"
        )
    else:
        print(f"⚠️ Arquivo de manutenção não encontrado.")
        valido = False
    if ARQUIVO_ENTRADA_FROTA and os.path.exists(ARQUIVO_ENTRADA_FROTA):
        print(
            f"✅ Arquivo de frota encontrado: {os.path.basename(ARQUIVO_ENTRADA_FROTA)}"
        )
    else:
        print(f"⚠️ Nenhum arquivo de frota encontrado.")
    print("=" * 80)
    return valido

    return valido

if __name__ == "__main__":
    validar_configuracao()
