"""
Script para disparo automático dos e-mails de fechamento (FKM) por filial.
Lê a configuração de e-mails de 'dados/emails_filiais.csv' e anexa os relatórios gerados.
"""

import os
import sys
import smtplib
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

from src import config

load_dotenv()

# Caminho para o CSV de e-mails
CSV_EMAILS_PATH = os.path.join(config.PROJECT_ROOT, "dados", "emails_filiais.csv")


def obter_conexao_smtp():
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT", "587")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    if not all([host, user, password]):
        raise EnvironmentError(
            "Configurações SMTP incompletas no arquivo .env. "
            "Garanta que SMTP_HOST, SMTP_USER e SMTP_PASSWORD estão definidos."
        )

    server = smtplib.SMTP(host, int(port))
    server.starttls()
    server.login(user, password)
    return server


def enviar_email_filial(server, filial_folder_name, nome_exibicao, responsavel, destinatarios_str, cc_str, pasta_periodo):
    # Destinatários e Cc como listas
    destinatarios = [d.strip() for d in destinatarios_str.split(";") if d.strip()]
    cc = [c.strip() for c in cc_str.split(";") if c.strip()]

    # Adicionar destinatários do e-mail de envio no To / Cc
    remetente = os.getenv("SMTP_USER")

    # Criar mensagem
    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = ", ".join(destinatarios)
    if cc:
        msg['Cc'] = ", ".join(cc)

    msg['Subject'] = f"Fechamento FKM - {config.MES}/{config.ANO} - {nome_exibicao}"

    corpo = f"""
    <html>
        <body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #333333;">
            <p>Olá,</p>
            <p>Seguem em anexo os relatórios de fechamento mensal (FKM) referentes ao período de <strong>{config.MES}/{config.ANO}</strong> da filial <strong>{nome_exibicao}</strong>.</p>
            <p><strong>Arquivos enviados:</strong></p>
            <ul>
                <li>Resumo do combustível (TruckPag)</li>
                <li>Resumo das manutenções (BlueFleet)</li>
                <li>Inventário da frota</li>
            </ul>
            <p>Lembramos que o FKM validado deve ser enviado para: <strong>torredecontrole@gritsch.com.br</strong>.</p>
            <br>
            <p style="font-size: 12px; color: #777777;">Este é um e-mail automático enviado pelo Sistema de Fechamento FKM. Por favor, não responda diretamente a este remetente.</p>
            <p style="font-size: 14px; margin-top: 20px;">Atenciosamente,<br><strong>Torre de Controle</strong><br>GRITSCH Transportes</p>
        </body>
    </html>
    """

    msg.attach(MIMEText(corpo, 'html'))

    # Pasta física da filial
    caminho_filial = config.obter_caminho_saida_filial(filial_folder_name)
    if not os.path.exists(caminho_filial):
        print(f"   ⚠️ Pasta não encontrada para a filial '{filial_folder_name}' em '{caminho_filial}'. Pulando...")
        return False

    arquivos = [f for f in os.listdir(caminho_filial) if f.endswith(".xlsx")]
    if not arquivos:
        print(f"   ⚠️ Nenhum arquivo Excel encontrado na pasta de '{filial_folder_name}'. Pulando...")
        return False

    for arq in arquivos:
        caminho_arq = os.path.join(caminho_filial, arq)
        with open(caminho_arq, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {arq}",
            )
            msg.attach(part)

    # Todos os e-mails (To + Cc) para o SMTP
    todos_destinatarios = destinatarios + cc

    server.sendmail(remetente, todos_destinatarios, msg.as_string())
    print(f"   ✅ E-mail enviado com sucesso para {destinatarios_str} (Cc: {cc_str}) - {len(arquivos)} anexos.")
    return True


def main():
    print("=" * 80)
    print(f"DISPARO AUTOMÁTICO DE E-MAILS DE FECHAMENTO - {config.MES}/{config.ANO}")
    print("=" * 80)

    if not os.path.exists(CSV_EMAILS_PATH):
        print(f"❌ ERRO: Arquivo de e-mails não encontrado em '{CSV_EMAILS_PATH}'")
        sys.exit(1)

    try:
        print("🔌 Conectando ao servidor SMTP...")
        server = obter_conexao_smtp()
        print("✅ Conectado com sucesso!")
    except Exception as e:
        print(f"❌ Falha ao conectar ao SMTP: {e}")
        sys.exit(1)

    enviados = 0
    falhas = 0

    with open(CSV_EMAILS_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, 1):
            filial = row['Filial']
            nome_exib = row['Nome_Exibicao']
            responsavel = row['Responsavel']
            email = row['Email']
            cc = row['Cc']

            print(f"\n[{idx}] Processando {nome_exib} ({filial})...")
            if not email:
                print("   ⚠️ Sem e-mail destinatário configurado. Pulando...")
                continue

            try:
                sucesso = enviar_email_filial(server, filial, nome_exib, responsavel, email, cc, config.PASTA_PERIODO)
                if sucesso:
                    enviados += 1
                else:
                    falhas += 1
            except Exception as e:
                print(f"   ❌ Erro ao enviar e-mail: {e}")
                falhas += 1

    server.quit()
    print("\n" + "=" * 80)
    print(f"🎉 DISPARO DE E-MAILS CONCLUÍDO!")
    print(f"   E-mails enviados: {enviados}")
    print(f"   Falhas/Ignorados: {falhas}")
    print("=" * 80)


if __name__ == "__main__":
    main()
