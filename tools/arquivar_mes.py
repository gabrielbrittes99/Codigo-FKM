"""
Script para Arquivamento Mensal dos Arquivos de Entrada e Retorno.
Move os arquivos processados do mês atual para a pasta de histórico.
"""

import os
import glob
import shutil
from src import config

def main():
    print("=" * 80)
    print(f"📦 ARQUIVAMENTO MENSAL - FECHAMENTO DE {config.MES}/{config.ANO}")
    print("=" * 80)
    
    # Pasta de destino no histórico
    pasta_destino = os.path.join(config.PROJECT_ROOT, "dados", "historico", f"{config.MES} {config.ANO}")
    os.makedirs(pasta_destino, exist_ok=True)
    
    # Padrão do mês (ex: "0626" para Junho 2026)
    mes_num = config.obter_numero_mes()
    ano_short = config.ANO[-2:]
    suffix = f"{mes_num}{ano_short}"
    
    # 1. Mover arquivos de dados/entrada/
    entrada_dir = os.path.join(config.PROJECT_ROOT, "dados", "entrada")
    # Busca arquivos que contenham o sufixo (ex: "Combustivel 0626.xlsx")
    arquivos_entrada = glob.glob(os.path.join(entrada_dir, f"*{suffix}*"))
    
    print("\n1. Arquivos de Entrada:")
    if not arquivos_entrada:
        print("  ∅ Nenhum arquivo de entrada encontrado para o período.")
    else:
        for arq in arquivos_entrada:
            nome = os.path.basename(arq)
            dest = os.path.join(pasta_destino, nome)
            shutil.move(arq, dest)
            print(f"  ➡️  {nome} -> dados/historico/{config.MES} {config.ANO}/")
            
    # 2. Mover arquivos de dados/retornados/
    retornados_dir = os.path.join(config.PROJECT_ROOT, "dados", "retornados")
    # Mover todos os arquivos .xls, .xlsx, .csv e backups (.bak) do diretório de retornos
    arquivos_retorno = []
    for ext in ["*.xls", "*.xlsx", "*.csv", "*.bak"]:
        arquivos_retorno.extend(glob.glob(os.path.join(retornados_dir, ext)))
        
    print("\n2. Arquivos Retornados pelas Filiais:")
    if not arquivos_retorno:
        print("  ∅ Nenhum arquivo de retorno encontrado em dados/retornados/.")
    else:
        for arq in arquivos_retorno:
            # Pula metadados do sistema ou arquivos de zone identifier
            if "Zone.Identifier" in arq:
                os.remove(arq)
                continue
            nome = os.path.basename(arq)
            dest = os.path.join(pasta_destino, nome)
            shutil.move(arq, dest)
            print(f"  ➡️  {nome} -> dados/historico/{config.MES} {config.ANO}/")
            
    print("\n" + "=" * 80)
    print(f"✅ Arquivos de {config.MES}/{config.ANO} arquivados com sucesso!")
    print(f"Pasta de destino: dados/historico/{config.MES} {config.ANO}/")
    print("=" * 80)

if __name__ == "__main__":
    main()
