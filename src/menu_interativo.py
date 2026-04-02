#!/usr/bin/env python3
"""
Menu Interativo - Sistema de Geração de FKMs
Automatiza o processamento de fechamento mensal
"""

import os
import subprocess
import sys
from datetime import datetime

# Importar configurações
from src import config


def limpar_tela():
    """Limpa a tela do terminal"""
    os.system("cls" if os.name == "nt" else "clear")


def exibir_cabecalho():
    """Exibe o cabeçalho do menu"""
    print("=" * 80)
    print(" " * 20 + "SISTEMA DE GERAÇÃO DE FKMs - GRITSCH")
    print("=" * 80)
    print(f"\n📅 Processando Fechamento: {config.MES}/{config.ANO}")
    print(f"📆 Data Atual: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 80)


def verificar_arquivos():
    """Verifica se os arquivos de entrada estão disponíveis"""
    print("\n🔍 VERIFICAÇÃO DE ARQUIVOS")
    print("-" * 80)

    arquivos_ok = True

    # Verificar combustível
    if config.ARQUIVO_ENTRADA_COMBUSTIVEL:
        if os.path.exists(config.ARQUIVO_ENTRADA_COMBUSTIVEL):
            tamanho = os.path.getsize(config.ARQUIVO_ENTRADA_COMBUSTIVEL) / 1024  # KB
            print(
                f"✅ Combustível: {config.ARQUIVO_ENTRADA_COMBUSTIVEL} ({tamanho:.1f} KB)"
            )
        else:
            print(
                f"❌ Combustível: {config.ARQUIVO_ENTRADA_COMBUSTIVEL} - NÃO ENCONTRADO"
            )
            arquivos_ok = False
    else:
        print(f"❌ Combustível: Nenhum arquivo encontrado (padrão: Combustivel*.xlsx)")
        arquivos_ok = False

    # Verificar manutenção
    if config.ARQUIVO_ENTRADA_MANUTENCAO:
        if os.path.exists(config.ARQUIVO_ENTRADA_MANUTENCAO):
            tamanho = os.path.getsize(config.ARQUIVO_ENTRADA_MANUTENCAO) / 1024  # KB
            print(
                f"✅ Manutenção: {config.ARQUIVO_ENTRADA_MANUTENCAO} ({tamanho:.1f} KB)"
            )
        else:
            print(
                f"❌ Manutenção: {config.ARQUIVO_ENTRADA_MANUTENCAO} - NÃO ENCONTRADO"
            )
            arquivos_ok = False
    else:
        print(f"❌ Manutenção: Nenhum arquivo encontrado (padrão: Manutencao*.xlsx)")
        arquivos_ok = False

    print("-" * 80)

    return arquivos_ok


def executar_script(nome_script, descricao):
    """Executa um script Python e aguarda a conclusão"""
    print(f"\n{'=' * 80}")
    print(f"🚀 EXECUTANDO: {descricao}")
    print(f"{'=' * 80}\n")

    try:
        # Executar o script
        resultado = subprocess.run(
            [sys.executable, nome_script],
            check=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        print(f"\n{'=' * 80}")
        print(f"✅ {descricao} - CONCLUÍDO COM SUCESSO!")
        print(f"{'=' * 80}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n{'=' * 80}")
        print(f"❌ ERRO ao executar {descricao}")
        print(f"Código de erro: {e.returncode}")
        print(f"{'=' * 80}")
        return False
    except Exception as e:
        print(f"\n{'=' * 80}")
        print(f"❌ ERRO INESPERADO: {e}")
        print(f"{'=' * 80}")
        return False


def menu_principal():
    """Exibe o menu principal e processa a escolha"""
    while True:
        limpar_tela()
        exibir_cabecalho()

        # Verificar arquivos
        arquivos_ok = verificar_arquivos()

        print("\n📋 OPÇÕES DISPONÍVEIS")
        print("-" * 80)
        print("1. Processar COMBUSTÍVEL")
        print("2. Processar MANUTENÇÃO")
        print("3. Processar TUDO (Combustível + Manutenção)")
        print("4. Verificar Configuração")
        print("5. Alterar Mês/Ano de Fechamento")
        print("6. Gerar RELATÓRIO DE KPIs")
        print("0. Sair")
        print("-" * 80)

        if not arquivos_ok:
            print("\n⚠️  ATENÇÃO: Alguns arquivos não foram encontrados!")
            print("   Verifique se os arquivos Excel estão na pasta do projeto.\n")

        escolha = input("\n👉 Escolha uma opção: ").strip()

        if escolha == "1":
            if not config.ARQUIVO_ENTRADA_COMBUSTIVEL or not os.path.exists(
                config.ARQUIVO_ENTRADA_COMBUSTIVEL
            ):
                print("\n❌ Arquivo de combustível não encontrado!")
                input("\nPressione ENTER para continuar...")
                continue

            executar_script("executar_resumos.py", "Processamento de Combustível")
            input("\n\nPressione ENTER para voltar ao menu...")

        elif escolha == "2":
            if not config.ARQUIVO_ENTRADA_MANUTENCAO or not os.path.exists(
                config.ARQUIVO_ENTRADA_MANUTENCAO
            ):
                print("\n❌ Arquivo de manutenção não encontrado!")
                input("\nPressione ENTER para continuar...")
                continue

            executar_script("executar_manutencao.py", "Processamento de Manutenção")
            input("\n\nPressione ENTER para voltar ao menu...")

        elif escolha == "3":
            if not arquivos_ok:
                print("\n❌ Não é possível processar: arquivos ausentes!")
                input("\nPressione ENTER para continuar...")
                continue

            print("\n" + "=" * 80)
            print("🚀 PROCESSAMENTO COMPLETO")
            print("=" * 80)
            print("\nSerão executados:")
            print("  1. Processamento de Combustível")
            print("  2. Processamento de Manutenção")

            confirmar = input("\nDeseja continuar? (S/N): ").strip().upper()

            if confirmar == "S":
                sucesso_combustivel = executar_script(
                    "executar_resumos.py", "Processamento de Combustível"
                )

                if sucesso_combustivel:
                    print("\n" + "=" * 80)
                    print("Aguardando 2 segundos antes de iniciar manutenção...")
                    print("=" * 80)
                    import time

                    time.sleep(2)

                    executar_script(
                        "executar_manutencao.py", "Processamento de Manutenção"
                    )

                print("\n" + "=" * 80)
                print("✅ PROCESSAMENTO COMPLETO FINALIZADO!")
                print("=" * 80)

            input("\n\nPressione ENTER para voltar ao menu...")

        elif escolha == "4":
            limpar_tela()
            config.validar_configuracao()

            print("\n📁 Pastas de saída:")
            print(f"   Combustível: {config.obter_caminho_saida_combustivel()}")
            print(f"   Manutenção: {config.obter_caminho_saida_manutencao()}")

            input("\n\nPressione ENTER para voltar ao menu...")

        elif escolha == "5":
            limpar_tela()
            print("=" * 80)
            print("ALTERAR MÊS/ANO DE FECHAMENTO")
            print("=" * 80)
            print(f"\nAtual: {config.MES}/{config.ANO}")
            print("\n⚠️  Para alterar o mês/ano, edite o arquivo 'config.py'")
            print("    Descomente e modifique as linhas:")
            print('    MES = "Janeiro"')
            print('    ANO = "2026"')

            input("\n\nPressione ENTER para voltar ao menu...")

        elif escolha == "6":
            if not arquivos_ok:
                print("\n❌ Não é possível gerar KPIs: arquivos ausentes!")
                input("\nPressione ENTER para continuar...")
                continue

            executar_script("gerar_relatorio_kpis.py", "Geração de Relatório de KPIs")
            input("\n\nPressione ENTER para voltar ao menu...")

        elif escolha == "0":
            print("\n👋 Encerrando o sistema. Até logo!")
            break

        else:
            print("\n❌ Opção inválida! Escolha uma opção válida.")
            input("\nPressione ENTER para continuar...")


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n👋 Sistema interrompido pelo usuário. Até logo!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
