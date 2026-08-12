#!/usr/bin/env python3
"""
Script para Restaurar Backups dos FKMs
Restaura os arquivos .bak para .xls originais
"""

import os
import shutil
import glob

def main():
    print("=" * 80)
    print("🔄 RESTAURADOR DE BACKUPS - FKMs Originais")
    print("=" * 80)

    pasta_retornos = "dados/retornados"

    if not os.path.exists(pasta_retornos):
        print(f"❌ Pasta não encontrada: {pasta_retornos}")
        return

    # Encontrar todos os arquivos .bak
    backups = glob.glob(os.path.join(pasta_retornos, "*.bak"))

    if not backups:
        print(f"⚠️  Nenhum backup (.bak) encontrado em {pasta_retornos}")
        print("   Os arquivos já podem estar no estado original.")
        return

    print(f"\n📦 Encontrados {len(backups)} arquivos de backup:")

    restaurados = 0

    for backup_path in sorted(backups):
        # Nome do arquivo original (sem .bak)
        original_path = backup_path[:-4]  # Remove .bak
        nome_backup = os.path.basename(backup_path)
        nome_original = os.path.basename(original_path)

        print(f"\n  📄 {nome_backup}")
        print(f"    ➜ Restaurando para: {nome_original}")

        try:
            # Copiar backup para arquivo original
            shutil.copy2(backup_path, original_path)
            print(f"    ✅ Restaurado com sucesso!")
            restaurados += 1
        except Exception as e:
            print(f"    ❌ Erro ao restaurar: {e}")

    print("\n" + "=" * 80)
    print(f"🎉 RESTAURAÇÃO CONCLUÍDA!")
    print(f"   {restaurados} de {len(backups)} arquivos restaurados")
    print("=" * 80)

    # Perguntar se quer remover os backups
    print("\n💡 Os arquivos .bak ainda estão lá (caso precise restaurar novamente)")
    print("   Para removê-los, execute: rm dados/retornados/*.bak")

if __name__ == "__main__":
    main()
