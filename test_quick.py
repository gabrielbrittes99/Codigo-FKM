#!/usr/bin/env python3
"""
Teste Rápido - Validação do Sistema
Executa validações básicas sem processar dados
"""

import config

print("=" * 80)
print("TESTE RÁPIDO - SISTEMA DE GERAÇÃO DE FKMs")
print("=" * 80)

# Executar validação
config.validar_configuracao()

print("\n" + "=" * 80)
print("INFORMAÇÕES ADICIONAIS")
print("=" * 80)

print(f"\n📊 Mês de Fechamento: {config.MES}")
print(f"📊 Ano: {config.ANO}")
print(f"📊 Número do Mês: {config.obter_numero_mes()}")

print(f"\n📁 Arquivos de Entrada:")
print(f"   - Combustível: {config.ARQUIVO_ENTRADA_COMBUSTIVEL}")
print(f"   - Manutenção: {config.ARQUIVO_ENTRADA_MANUTENCAO}")

print(f"\n📁 Pastas de Saída:")
print(f"   - Combustível: {config.obter_caminho_saida_combustivel()}")
print(f"   - Manutenção: {config.obter_caminho_saida_manutencao()}")

print(f"\n📂 Estrutura de Pastas:")
print(f"   {config.DIRETORIO_BASE_SAIDA}/")
print(f"   └── {config.MES}/")
print(f"       ├── {config.PASTA_SAIDA_COMBUSTIVEL}/")
print(f"       └── {config.PASTA_SAIDA_MANUTENCAO}/")

print("\n" + "=" * 80)
print("✅ TESTE CONCLUÍDO")
print("=" * 80)
print("\n💡 Dica: Execute 'python menu_interativo.py' para processar os dados")
