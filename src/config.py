"""
Configuração Automática para Geração de FKMs
Detecta automaticamente mês, ano e arquivos de entrada

IMPORTANTE: Este sistema processa o FECHAMENTO do mês anterior.
Exemplo: Rodando em Fevereiro/2026 → Processa dados de Janeiro/2026
"""

import glob
import os
from datetime import datetime, timedelta

# ==================== CONFIGURAÇÕES AUTOMÁTICAS ====================


def obter_mes_ano_fechamento():
    """
    Retorna mês (nome completo em português) e ano do FECHAMENTO

    LÓGICA: Retorna o mês ANTERIOR ao atual
    - Rodando em Fevereiro/2026 → Retorna Janeiro/2026
    - Rodando em Janeiro/2026 → Retorna Dezembro/2025
    """
    agora = datetime.now()

    # Calcular primeiro dia do mês atual e subtrair 1 dia = último dia do mês anterior
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


def encontrar_arquivo_entrada(padrao, diretorio_base=None):
    """
    Busca automaticamente o arquivo de entrada mais recente que corresponde ao padrão

    Args:
        padrao: Padrão do arquivo (ex: "Combustivel*.xlsx", "Manutencao*.xlsx")
        diretorio_base: Diretório onde procurar (padrão: root do projeto)

    Returns:
        Nome do arquivo encontrado ou None
    """
    if diretorio_base is None:
        # Diretório root do projeto (um nível acima de src/)
        diretorio_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Buscar arquivos que correspondem ao padrão
    caminho_busca = os.path.join(diretorio_base, padrao)
    arquivos_encontrados = glob.glob(caminho_busca)

    if not arquivos_encontrados:
        return None

    # Se houver múltiplos arquivos, pegar o mais recente
    if len(arquivos_encontrados) > 1:
        arquivos_encontrados.sort(key=os.path.getmtime, reverse=True)

    # Retornar apenas o nome do arquivo (sem caminho)
    return os.path.basename(arquivos_encontrados[0])


# ==================== VARIÁVEIS PRINCIPAIS ====================

# Detectar mês e ano do FECHAMENTO (mês anterior) automaticamente
MES, ANO = obter_mes_ano_fechamento()

# Se quiser forçar um mês/ano específico de fechamento, descomente e edite as linhas abaixo:
# MES = "Janeiro"
# ANO = "2026"

# Diretório base de saída
DIRETORIO_BASE_SAIDA = "/home/gabriel/projetos/Arquivos FKMs"

# Detectar automaticamente os arquivos de entrada
ARQUIVO_ENTRADA_COMBUSTIVEL = encontrar_arquivo_entrada("Combustivel*.xlsx")
ARQUIVO_ENTRADA_MANUTENCAO = encontrar_arquivo_entrada("Manutencao*.xlsx")
ARQUIVO_ENTRADA_FROTA = encontrar_arquivo_entrada("Frota*.xlsx")

# Nomes das pastas de saída
PASTA_SAIDA_COMBUSTIVEL = f"COMBUSTIVEL {MES} {ANO}"
PASTA_SAIDA_MANUTENCAO = f"MANUTENÇÃO {MES} {ANO}"


# ==================== FUNÇÕES AUXILIARES (NÃO EDITAR) ====================


def obter_numero_mes():
    """Retorna o número do mês (01-12) baseado no nome do mês"""
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


def obter_caminho_saida_combustivel():
    """Retorna o caminho completo da pasta de saída para combustível"""
    return os.path.join(DIRETORIO_BASE_SAIDA, MES, PASTA_SAIDA_COMBUSTIVEL)


def obter_caminho_saida_manutencao():
    """Retorna o caminho completo da pasta de saída para manutenção"""
    return os.path.join(DIRETORIO_BASE_SAIDA, MES, PASTA_SAIDA_MANUTENCAO)


def validar_configuracao():
    """
    Valida se todas as configurações estão corretas
    Retorna True se OK, ou imprime avisos/erros
    """
    print("=" * 80)
    print("VALIDAÇÃO DE CONFIGURAÇÃO - FECHAMENTO MENSAL")
    print("=" * 80)

    # Mostrar mês atual vs mês de fechamento
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

    # Validar arquivo de combustível
    if ARQUIVO_ENTRADA_COMBUSTIVEL:
        if os.path.exists(ARQUIVO_ENTRADA_COMBUSTIVEL):
            print(
                f"\n✅ Arquivo de combustível encontrado: {ARQUIVO_ENTRADA_COMBUSTIVEL}"
            )
        else:
            print(
                f"\n⚠️  Arquivo de combustível não encontrado: {ARQUIVO_ENTRADA_COMBUSTIVEL}"
            )
            valido = False
    else:
        print(
            f"\n❌ Nenhum arquivo de combustível encontrado (padrão: Combustivel*.xlsx)"
        )
        valido = False

    # Validar arquivo de manutenção
    if ARQUIVO_ENTRADA_MANUTENCAO:
        if os.path.exists(ARQUIVO_ENTRADA_MANUTENCAO):
            print(f"✅ Arquivo de manutenção encontrado: {ARQUIVO_ENTRADA_MANUTENCAO}")
        else:
            print(
                f"⚠️  Arquivo de manutenção não encontrado: {ARQUIVO_ENTRADA_MANUTENCAO}"
            )
            valido = False
    else:
        print(f"❌ Nenhum arquivo de manutenção encontrado (padrão: Manutencao*.xlsx)")
        valido = False

    # Validar arquivo de frota (opcional mas recomendado)
    if ARQUIVO_ENTRADA_FROTA:
        if os.path.exists(ARQUIVO_ENTRADA_FROTA):
            print(f"✅ Arquivo de frota encontrado: {ARQUIVO_ENTRADA_FROTA}")
        else:
            print(f"⚠️  Arquivo de frota não encontrado: {ARQUIVO_ENTRADA_FROTA}")
    else:
        print(f"⚠️  Nenhum arquivo de frota encontrado (padrão: Frota*.xlsx) - KPIs por grupo indisponíveis")

    # Validar diretório de saída
    print(f"\n📁 Diretórios de saída:")
    print(f"   - Combustível: {obter_caminho_saida_combustivel()}")
    print(f"   - Manutenção: {obter_caminho_saida_manutencao()}")

    if valido:
        print(
            f"\n✅ Configuração válida! Pronto para processar fechamento de {MES}/{ANO}"
        )
    else:
        print(f"\n⚠️  Verifique os arquivos de entrada antes de continuar.")

    print("=" * 80)

    return valido


# ==================== AUTO-VALIDAÇÃO (OPCIONAL) ====================

if __name__ == "__main__":
    # Se executar este arquivo diretamente, mostra a configuração
    validar_configuracao()
