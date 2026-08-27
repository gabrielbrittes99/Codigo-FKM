"""
Gerador do Relatório Torre de Controle semestral em PDF (A4 retrato).

Combina os indicadores calculados em `torre_dados.py` com o conteúdo editorial
de `conteudo_torre.yaml`. Todo texto do relatório — títulos, leituras, ações,
observações e próximos passos — vem do YAML; este módulo cuida apenas do
layout, dos gráficos e da formatação dos números.
"""

import os
import warnings

import numpy as np
import yaml
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from src.torre_dados import calcular_dados_torre
from src.torre_layout import (
    ALTURA, AZUL, BRANCO, CINZA_ZEBRA, C_BORDA, C_BRANCO, C_FUNDO, C_MARROM,
    C_SUAVE, C_TEXTO, C_VERDE, C_VERMELHO, C_ZEBRA, LARGURA, LARGURA_UTIL,
    MARGEM, MARROM, RAIZ, ROSA, TEXTO, TEXTO_SUAVE, VERDE, VERMELHO,
    VERMELHO_MEDIO, bloco_observacoes, caixa, cor_sobre, grafico, inteiro, interpolar,
    km_curto, linha, lista_topicos, marcador, meses_em_negrito, milhares,
    moeda, moeda_cheia, moeda_k, moeda_milhar, montar_documento,
    nova_figura, numero_br, pagina_observacoes_gerais, paragrafo, pct,
    pct_sinal, quebrar, rotulos_em_negrito, rotulos_par_de_barras, secao, valor_km, valor_litro,
    separadores, texto, triangulo, variacao, y,
)

warnings.filterwarnings("ignore")

CAMINHO_YAML = os.path.join(RAIZ, "conteudo_torre.yaml")


def separadores_bimestre(ax, quantidade=6):
    """Divide B1 | B2 | B3 no eixo de meses."""
    separadores(ax, [p for p in (1.5, 3.5) if p < quantidade])


# =======================================================================
# PÁGINAS
# =======================================================================

def _pagina_1(c, d, cont, ctx):
    pagina = cont["pagina_1_visao_executiva"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    b2, b3 = d["bimestral"]["B2"], d["bimestral"]["B3"]
    var = d["variacoes"]["B3 vs B2"]
    rot_b2 = f"B2 ({d['meta']['bimestres']['B2']})"
    rot_b3 = f"B3 ({d['meta']['bimestres']['B3']})"

    cartoes = [
        ("MANUTENÇÃO", "Manutenção total"),
        ("COMBUSTÍVEL", "Combustível total"),
        ("PEDÁGIO", "Pedágio total"),
        ("TOTAL OPERACIONAL", "Total operacional"),
    ]
    largura_cartao = (LARGURA_UTIL - 3 * 10) / 4
    passo = largura_cartao + 10

    for i, (rotulo, chave) in enumerate(cartoes):
        x = MARGEM + i * passo
        caixa(c, x, 124, largura_cartao, 110, C_FUNDO, raio=6)
        c.setFillColor(C_MARROM)
        c.roundRect(x, y(142), largura_cartao, 18, 6, stroke=0, fill=1)
        c.rect(x, y(142), largura_cartao, 6, stroke=0, fill=1)
        texto(c, x + 12, 137.0, rotulo, 8, C_BRANCO, negrito=True)

        texto(c, x + 12, 155.0, rot_b2, 8, C_SUAVE)
        texto(c, x + 12, 172.9, moeda(b2[chave]), 15, C_TEXTO, negrito=True)
        texto(c, x + 12, 189.0, rot_b3, 8, C_SUAVE)
        texto(c, x + 12, 206.9, moeda(b3[chave]), 15, C_TEXTO, negrito=True)
        variacao(c, x + 12, 225.0, var[chave])

    secao(c, 251, interpolar(pagina.get("titulo_grafico"), ctx))

    fig, ax = nova_figura(525, 300)
    meses = d["meta"]["meses"]
    manut = [d["mensal"][m]["Manutenção total"] / 1000 for m in meses]
    comb = [d["mensal"][m]["Combustível total"] / 1000 for m in meses]
    ped = [d["mensal"][m]["Pedágio total"] / 1000 for m in meses]

    ax.bar(meses, manut, color=ROSA, label="Manutenção", width=0.62)
    ax.bar(meses, comb, bottom=manut, color=MARROM, label="Combustível", width=0.62)
    ax.bar(meses, ped, bottom=np.add(manut, comb), color=AZUL, label="Pedágio", width=0.62)

    totais = np.add(np.add(manut, comb), ped)
    for i, total in enumerate(totais):
        ax.text(i, total + max(totais) * 0.02, moeda(total * 1000), ha="center",
                fontsize=8, fontweight="bold", color=TEXTO)

    separadores_bimestre(ax)
    limite = max(totais) * 1.22
    ax.set_ylim(0, limite)
    for posicao, rotulo in [(0.5, "B1"), (2.5, "B2"), (4.5, "B3")]:
        ax.text(posicao, limite * 0.97, rotulo, ha="center", fontsize=10,
                fontweight="bold", color=MARROM)

    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.legend(loc="upper left", fontsize=8, frameon=False, bbox_to_anchor=(0.02, 0.99))
    ax.tick_params(axis="x", labelsize=9)
    for etiqueta in ax.get_xticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 290, 525, 300)


def _pagina_2(c, d, cont, ctx):
    pagina = cont["pagina_2_evolucao_custo_km"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    caixa(c, MARGEM, 120, LARGURA_UTIL, 175, C_BRANCO, C_BORDA, raio=8)

    fig, ax = nova_figura(500, 160)
    meses = d["meta"]["meses"]
    valores = [d["mensal"][m]["Custo/km total"] * 1000 for m in meses]

    ax.plot(meses, valores, color=MARROM, linewidth=2, marker="o", markersize=6, zorder=3)
    for i, valor in enumerate(valores):
        ax.text(i, valor + (max(valores) - min(valores)) * 0.12, valor_km(valor / 1000),
                ha="center", fontsize=8, fontweight="bold", color=MARROM)

    separadores_bimestre(ax)
    folga = (max(valores) - min(valores)) * 0.45
    ax.set_ylim(min(valores) - folga, max(valores) + folga)
    ax.set_ylabel("R$/km × 1000", fontsize=8)
    ax.tick_params(axis="x", labelsize=9)
    for etiqueta in ax.get_xticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 12, 128, 500, 160)

    topo = secao(c, 315, interpolar(pagina.get("subtitulo"), ctx)) + 18
    topo = lista_topicos(c, topo, pagina.get("paragrafos"), ctx)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_3(c, d, cont, ctx):
    pagina = cont["pagina_3_indicadores_operacionais"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    b2, b3 = d["bimestral"]["B2"], d["bimestral"]["B3"]
    rot_b2 = f"B2 ({d['meta']['bimestres']['B2']})"
    rot_b3 = f"B3 ({d['meta']['bimestres']['B3']})"

    fig, ax = nova_figura(525, 260)
    categorias = ["Combustível\npor km", "Manutenção\npor km", "Total\noperacional/km"]
    chaves = ["Custo/km combustível", "Custo/km manutenção", "Custo/km total"]
    valores_b2 = [b2[k] for k in chaves]
    valores_b3 = [b3[k] for k in chaves]

    posicoes = np.arange(len(categorias))
    ax.bar(posicoes - 0.2, valores_b2, 0.38, color=ROSA, label=rot_b2)
    ax.bar(posicoes + 0.2, valores_b3, 0.38, color=MARROM, label=rot_b3)

    topo_grafico = max(valores_b2 + valores_b3) * 1.35
    for i, (v2, v3) in enumerate(zip(valores_b2, valores_b3)):
        ax.text(i - 0.2, v2 + topo_grafico * 0.02, valor_km(v2), ha="center",
                fontsize=8, color=TEXTO_SUAVE)
        ax.text(i + 0.2, v3 + topo_grafico * 0.02, valor_km(v3), ha="center",
                fontsize=8, fontweight="bold", color=TEXTO)
        delta = (v3 / v2 - 1) * 100 if v2 else 0
        ax.text(i + 0.2, v3 + topo_grafico * 0.10, f"({pct_sinal(delta)})", ha="center",
                fontsize=8, fontweight="bold", color=VERDE if delta < 0 else VERMELHO)

    ax.set_xticks(posicoes)
    ax.set_xticklabels(categorias, fontsize=8.5)
    ax.set_ylim(0, topo_grafico)
    ax.set_ylabel("R$/km", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 260)

    secao(c, 385, interpolar(pagina.get("subtitulo"), ctx))

    indicadores = [
        ("KM RODADO", f"B2: {km_curto(b2['KM rodado total'])} km",
         f"B3: {km_curto(b3['KM rodado total'])} km", False),
        ("LITROS CONSUMIDOS", f"B2: {milhares(b2['Litros consumidos'])} L",
         f"B3: {milhares(b3['Litros consumidos'])} L", False),
        ("PREÇO MÉDIO DIESEL S10", f"B2: {valor_litro(b2['Preço médio diesel S10'])}",
         f"B3: {valor_litro(b3['Preço médio diesel S10'])}", True),
        ("CONSUMO MÉDIO FROTA", f"B2: {numero_br(b2['Consumo médio (km/L)'])} km/L",
         f"B3: {numero_br(b3['Consumo médio (km/L)'])} km/L", False),
    ]
    largura_cartao = (LARGURA_UTIL - 3 * 10) / 4
    for i, (rotulo, linha_b2, linha_b3, destaque) in enumerate(indicadores):
        x = MARGEM + i * (largura_cartao + 10)
        caixa(c, x, 428, largura_cartao, 78, C_FUNDO, C_BORDA)
        texto(c, x + 12, 445, rotulo, 7.5, C_SUAVE)
        texto(c, x + 12, 461, linha_b2, 8, C_SUAVE)
        texto(c, x + 12, 490, linha_b3, 13, C_VERMELHO if destaque else C_TEXTO, negrito=True)

    secao(c, 528, interpolar(pagina.get("titulo_diesel"), ctx))

    fig, ax = nova_figura(500, 175)
    meses = d["meta"]["meses"]
    precos = [d["mensal"][m]["Preço médio diesel S10"] for m in meses]
    ax.plot(meses, precos, color=MARROM, linewidth=2, marker="o", markersize=5, zorder=3)
    ax.fill_between(range(len(meses)), precos, min(precos) * 0.97, color=MARROM, alpha=0.10)
    for i, preco in enumerate(precos):
        ax.text(i, preco + (max(precos) - min(precos)) * 0.13, valor_litro(preco),
                ha="center", fontsize=7.5, fontweight="bold", color=MARROM)

    separadores_bimestre(ax)
    ax.set_ylim(min(precos) * 0.97, max(precos) * 1.06)
    ax.set_ylabel("R$/litro", fontsize=8)
    for etiqueta in ax.get_xticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 12, 562, 500, 175)

    topo = paragrafo(c, MARGEM, 758, LARGURA_UTIL,
                     interpolar(pagina.get("texto_diesel"), ctx), 9, C_SUAVE)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_4(c, d, cont, ctx):
    pagina = cont["pagina_4_manutencao"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    natureza = d["quebras"]["manutencao_natureza"]
    rot_b2 = f"B2 ({d['meta']['bimestres']['B2']})"
    rot_b3 = f"B3 ({d['meta']['bimestres']['B3']})"

    fig, ax = nova_figura(525, 250)
    categorias = list(natureza["atual"].keys())
    valores_b2 = [natureza["anterior"][k] / 1000 for k in categorias]
    valores_b3 = [natureza["atual"][k] / 1000 for k in categorias]
    posicoes = np.arange(len(categorias))

    ax.bar(posicoes - 0.2, valores_b2, 0.38, color=ROSA, label=rot_b2)
    ax.bar(posicoes + 0.2, valores_b3, 0.38, color=MARROM, label=rot_b3)

    topo_grafico = max(valores_b2 + valores_b3 + [1]) * 1.32
    for i, (v2, v3) in enumerate(zip(valores_b2, valores_b3)):
        rotulos_par_de_barras(ax, i, v2, v3, topo_grafico)

    ax.set_xticks(posicoes)
    ax.set_xticklabels([k.replace(" de ", " de\n").replace(" e ", " e\n") for k in categorias],
                       fontsize=8.5)
    ax.set_ylim(0, topo_grafico)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 250)

    secao(c, 378, interpolar(pagina.get("titulo_filiais"), ctx))

    filiais = d["quebras"]["manutencao_top_filiais"]
    fig, ax = nova_figura(525, 270)
    nomes = list(filiais.keys())[::-1]
    valores = [v / 1000 for v in filiais.values()][::-1]

    ax.barh(nomes, valores, color=MARROM, height=0.62)
    for i, valor in enumerate(valores):
        ax.text(valor + max(valores) * 0.01, i, f" {moeda_k(valor)}", va="center",
                fontsize=8, color=TEXTO)
    ax.set_xlim(0, max(valores) * 1.16)
    ax.set_xlabel("R$ (milhares)", fontsize=8)
    for etiqueta in ax.get_yticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 408, 525, 270)

    bloco_observacoes(c, 690, pagina, ctx)


def _pagina_5(c, d, cont, ctx):
    pagina = cont["pagina_5_combustivel"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    tipos = d["quebras"]["combustivel_tipo"]
    rot_b2 = f"B2 ({d['meta']['bimestres']['B2']})"
    rot_b3 = f"B3 ({d['meta']['bimestres']['B3']})"

    fig, ax = nova_figura(525, 250)
    categorias = list(tipos["atual"].keys())
    valores_b2 = [tipos["anterior"][k] / 1000 for k in categorias]
    valores_b3 = [tipos["atual"][k] / 1000 for k in categorias]
    posicoes = np.arange(len(categorias))

    ax.bar(posicoes - 0.2, valores_b2, 0.38, color=ROSA, label=rot_b2)
    ax.bar(posicoes + 0.2, valores_b3, 0.38, color=MARROM, label=rot_b3)

    topo_grafico = max(valores_b2 + valores_b3 + [1]) * 1.30
    for i, (v2, v3) in enumerate(zip(valores_b2, valores_b3)):
        rotulos_par_de_barras(ax, i, v2, v3, topo_grafico)

    ax.set_xticks(posicoes)
    ax.set_xticklabels([k.replace(" ", "\n") for k in categorias], fontsize=8.5)
    ax.set_ylim(0, topo_grafico)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 250)

    topo = secao(c, 378, interpolar(pagina.get("subtitulo"), ctx)) + 18
    topo = lista_topicos(c, topo, pagina.get("topicos"), ctx)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_6(c, d, cont, ctx):
    pagina = cont["pagina_6_pedagio"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    meses = d["meta"]["meses"]
    valores = [d["mensal"][m]["Pedágio total"] / 1000 for m in meses]
    passagens = [d["mensal"][m]["Número de passagens pedágio"] for m in meses]
    cores = [ROSA, ROSA, VERMELHO_MEDIO, VERMELHO_MEDIO, MARROM, MARROM]

    fig, ax = nova_figura(525, 285)
    ax.bar(meses, valores, color=cores[:len(meses)], width=0.62)
    for i, (valor, passagem) in enumerate(zip(valores, passagens)):
        ax.text(i, valor + max(valores) * 0.04, moeda_k(valor), ha="center",
                fontsize=9, fontweight="bold", color=TEXTO)
        ax.text(i, valor - max(valores) * 0.045, inteiro(passagem), ha="center",
                fontsize=7.5, fontweight="bold", color=cor_sobre(cores[i]))

    separadores_bimestre(ax)
    ax.set_ylim(0, max(valores) * 1.22)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.tick_params(axis="x", labelsize=9)
    for etiqueta in ax.get_xticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 285)

    b2, b3 = d["bimestral"]["B2"], d["bimestral"]["B3"]
    var = d["variacoes"]["B3 vs B2"]
    delta_valor = b3["Pedágio total"] - b2["Pedágio total"]
    delta_passagens = b3["Número de passagens pedágio"] - b2["Número de passagens pedágio"]

    cartoes = [
        (f"B2 ({d['meta']['bimestres']['B2'].upper()})", moeda(b2["Pedágio total"]),
         f"{inteiro(b2['Número de passagens pedágio'])} passagens", None),
        (f"B3 ({d['meta']['bimestres']['B3'].upper()})", moeda(b3["Pedágio total"]),
         f"{inteiro(b3['Número de passagens pedágio'])} passagens", None),
        ("VARIAÇÃO", moeda(delta_valor), f"{inteiro(delta_passagens)} passagens",
         var["Pedágio total"]),
    ]
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, (rotulo, valor, detalhe, delta) in enumerate(cartoes):
        x = MARGEM + i * (largura_cartao + 12)
        caixa(c, x, 420, largura_cartao, 95, C_FUNDO, C_BORDA)
        texto(c, x + 16, 438, rotulo, 8.5, C_SUAVE)
        texto(c, x + 16, 468, valor, 19, C_TEXTO, negrito=True)
        texto(c, x + 16, 486, detalhe, 8.5, C_SUAVE)
        if delta is not None:
            variacao(c, x + 16, 505, delta, tamanho=10)

    topo = paragrafo(c, MARGEM, 540, LARGURA_UTIL,
                     interpolar(pagina.get("texto_analise"), ctx), 9.5, C_SUAVE)
    bloco_observacoes(c, topo + 10, pagina, ctx)


def _pagina_7(c, d, cont, ctx):
    pagina = cont["pagina_7_pedagio_detalhe"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    # A UF entra na segunda linha do rótulo: mostra em que rota o gasto ocorre
    concessionarias = d["quebras"]["pedagio_concessionaria"][::-1]
    fig, ax = nova_figura(500, 215)
    nomes = [f"{x['nome']}\n{x['ufs']}" if x.get("ufs") else x["nome"]
             for x in concessionarias]
    valores = [x["valor"] for x in concessionarias]

    ax.barh(nomes, valores, color=AZUL, height=0.6)
    for i, valor in enumerate(valores):
        ax.text(valor + max(valores) * 0.01, i, f" {moeda_cheia(valor)}", va="center",
                fontsize=7.5, color=TEXTO)
    ax.set_xlim(0, max(valores) * 1.2)
    ax.set_xlabel(f"R$ total no bimestre B3 ({d['meta']['bimestres']['B3']})", fontsize=8)
    for etiqueta in ax.get_yticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
        etiqueta.set_fontsize(8)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 20, 112, 500, 215)

    paragrafo(c, MARGEM + 10, 348, LARGURA_UTIL - 20,
              interpolar(pagina.get("texto_concessionarias"), ctx), 9, C_SUAVE)

    secao(c, 395, interpolar(pagina.get("titulo_pracas"), ctx), tamanho=14)

    pracas = d["quebras"]["pedagio_passagens"]
    mes_ini, mes_fim = d["meta"]["meses"][4], d["meta"]["meses"][5]

    fig, ax = nova_figura(500, 230)
    nomes = [p["praca"] for p in pracas][::-1]
    antes = [p["antes"] for p in pracas][::-1]
    depois = [p["depois"] for p in pracas][::-1]
    posicoes = np.arange(len(nomes))

    ax.barh(posicoes + 0.19, antes, 0.36, color=ROSA, label=mes_ini)
    ax.barh(posicoes - 0.19, depois, 0.36, color=AZUL, label=mes_fim)
    maximo = max(depois + antes + [1])
    for i, (a, dp) in enumerate(zip(antes, depois)):
        ax.text(a + maximo * 0.012, i + 0.19, str(a), va="center", fontsize=7.5, color=TEXTO_SUAVE)
        ax.text(dp + maximo * 0.012, i - 0.19, str(dp), va="center", fontsize=7.5,
                fontweight="bold", color=TEXTO)

    ax.set_yticks(posicoes)
    ax.set_yticklabels(nomes, fontweight="bold", color=TEXTO, fontsize=8)
    ax.set_xlim(0, maximo * 1.12)
    ax.set_xlabel("Nº de passagens", fontsize=8)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 20, 425, 500, 230)

    topo = paragrafo(c, MARGEM + 10, 676, LARGURA_UTIL - 20,
                     interpolar(pagina.get("texto_pracas"), ctx), 9, C_SUAVE)
    bloco_observacoes(c, topo + 8, pagina, ctx)


def _pagina_8(c, d, cont, ctx):
    pagina = cont["pagina_8_custo_km_filial"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    filiais = d["quebras"]["custo_km_filial"]
    limite_alto = pagina.get("limite_alto", 1.00)
    limite_baixo = pagina.get("limite_baixo", 0.65)

    fig, ax = nova_figura(510, 560)
    nomes = [f["filial"] for f in filiais][::-1]
    valores = [f["ckm_atual"] for f in filiais][::-1]
    cores = [MARROM if v >= limite_alto else (VERMELHO_MEDIO if v >= limite_baixo else ROSA)
             for v in valores]

    ax.barh(nomes, valores, color=cores, height=0.68)
    for i, valor in enumerate(valores):
        ax.text(valor + max(valores) * 0.008, i, f" {valor_km(valor)}", va="center",
                fontsize=7.5, color=TEXTO)

    ax.set_xlim(0, max(valores) * 1.18)
    ax.set_xlabel(f"R$/km (Combustível), B3 ({d['meta']['bimestres']['B3']})", fontsize=8)
    for etiqueta in ax.get_yticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
        etiqueta.set_fontsize(7.5)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color=MARROM, label=f"Acima de {valor_km(limite_alto, '/km')}"),
        Patch(color=VERMELHO_MEDIO, label=f"{valor_km(limite_baixo)} a {valor_km(limite_alto, '/km')}"),
        Patch(color=ROSA, label=f"Abaixo de {valor_km(limite_baixo, '/km')}"),
    ], loc="lower right", fontsize=7.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 10, 112, 510, 560)

    bloco_observacoes(c, 686, pagina, ctx)


def _pagina_9(c, d, cont, ctx):
    pagina = cont["pagina_9_custo_km_detalhado"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    filiais = d["quebras"]["custo_km_filial"]
    colunas = [
        ("FILIAL", MARGEM + 12),
        ("KM (B2)", MARGEM + 140),
        ("KM (B3)", MARGEM + 205),
        ("R$/km B2", MARGEM + 270),
        ("R$/km B3", MARGEM + 340),
        ("VAR B2→B3", MARGEM + 410),
        ("PLACAS", MARGEM + 480),
    ]

    topo = 132
    for rotulo, x in colunas:
        texto(c, x, topo, rotulo, 8.5, C_SUAVE, negrito=True)

    topo += 8
    c.setStrokeColor(C_BORDA)
    c.setLineWidth(0.8)
    c.line(MARGEM, y(topo), LARGURA - MARGEM, y(topo))

    topo += 15
    altura_linha = 19.5
    for i, filial in enumerate(filiais):
        if i % 2 == 1:
            c.setFillColor(C_ZEBRA)
            c.rect(MARGEM, y(topo + 5.5), LARGURA_UTIL, altura_linha, stroke=0, fill=1)

        cor_var = C_VERDE if filial["var"] <= -5 else (C_VERMELHO if filial["var"] >= 1 else C_TEXTO)
        texto(c, colunas[0][1], topo, filial["filial"][:22], 9, C_TEXTO)
        texto(c, colunas[1][1], topo, km_curto(filial["km_ref"]), 9, C_SUAVE)
        texto(c, colunas[2][1], topo, km_curto(filial["km_atual"]), 9, C_SUAVE)
        texto(c, colunas[3][1], topo, valor_km(filial['ckm_ref']), 9, C_SUAVE)
        texto(c, colunas[4][1], topo, valor_km(filial['ckm_atual']), 9, C_TEXTO, negrito=True)
        texto(c, colunas[5][1], topo, pct_sinal(filial["var"]), 9, cor_var, negrito=True)
        texto(c, colunas[6][1], topo, str(filial["placas"]), 9, C_TEXTO)
        topo += altura_linha

    b2, b3 = d["bimestral"]["B2"], d["bimestral"]["B3"]
    var_total = (b3["Custo/km combustível"] / b2["Custo/km combustível"] - 1) * 100 \
        if b2["Custo/km combustível"] else 0

    topo += 2
    c.setStrokeColor(C_MARROM)
    c.setLineWidth(1.2)
    c.line(MARGEM, y(topo), LARGURA - MARGEM, y(topo))
    topo += 17

    total = [
        "TOTAL / MÉDIA", km_curto(b2["KM rodado total"]), km_curto(b3["KM rodado total"]),
        valor_km(b2['Custo/km combustível']), valor_km(b3['Custo/km combustível']),
        pct_sinal(var_total), str(sum(f["placas"] for f in filiais)),
    ]
    for (_, x), valor in zip(colunas, total):
        texto(c, x, topo, valor, 9, C_MARROM, negrito=True)

    bloco_observacoes(c, topo + 22, pagina, ctx)


def _pagina_10(c, d, cont, ctx):
    pagina = cont["pagina_10_hodometro_manutencao"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    placas = d["quebras"]["top_placas_manutencao"]
    corte = pagina.get("corte_hodometro", 200_000)

    fig, ax = nova_figura(520, 285)
    faixas = [
        ("Até 2 anos", ROSA, lambda i: i is not None and i <= 2),
        ("3 a 4 anos", VERMELHO_MEDIO, lambda i: i is not None and 3 <= i <= 4),
        ("5 anos ou mais", MARROM, lambda i: i is None or i >= 5),
    ]
    for rotulo, cor, filtro in faixas:
        grupo = [p for p in placas if filtro(p["idade"])]
        if grupo:
            ax.scatter([p["odometro"] / 1000 for p in grupo],
                       [p["valor"] / 1000 for p in grupo],
                       color=cor, s=42, label=rotulo, zorder=3, edgecolors="none")

    for p in placas:
        ax.annotate(p["placa"], (p["odometro"] / 1000, p["valor"] / 1000),
                    xytext=(5, 2), textcoords="offset points", fontsize=6.5, color=TEXTO)

    ax.margins(x=0.09, y=0.16)
    ax.axvline(corte / 1000, color="#888888", linestyle="--", linewidth=1, zorder=1)
    limite_x = ax.get_xlim()
    ax.axvspan(corte / 1000, limite_x[1], color=MARROM, alpha=0.045, zorder=0)
    ax.set_xlim(limite_x)
    ax.text(corte / 1000, ax.get_ylim()[1], f"{corte // 1000} mil km", ha="center",
            va="bottom", fontsize=7.5, fontweight="bold", color=TEXTO_SUAVE)

    ax.set_xlabel("Hodômetro (milhares de km)", fontsize=8)
    ax.set_ylabel(f"Custo de manutenção B3 (R$ mil)", fontsize=8)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 5, 112, 520, 285)

    analise = interpolar(pagina.get("texto_analise"), ctx)
    linhas = quebrar(c, analise, LARGURA_UTIL - 40, "Helvetica", 9)
    altura_caixa = 22 + len(linhas) * 14
    caixa(c, MARGEM, 412, LARGURA_UTIL, altura_caixa, C_FUNDO)
    paragrafo(c, MARGEM + 20, 429, LARGURA_UTIL - 40, analise, 9, C_TEXTO, entrelinha=14)

    topo_cartoes = 412 + altura_caixa + 26
    c.setStrokeColor(C_BORDA)
    c.setLineWidth(0.8)
    c.line(MARGEM, y(topo_cartoes - 14), LARGURA - MARGEM, y(topo_cartoes - 14))

    natureza_km = d["quebras"]["manutencao_natureza_km"]
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, chave in enumerate(natureza_km["atual"].keys()):
        x = MARGEM + i * (largura_cartao + 12)
        valor_b2 = natureza_km["anterior"][chave]
        valor_b3 = natureza_km["atual"][chave]
        delta = (valor_b3 / valor_b2 - 1) * 100 if valor_b2 else 0

        caixa(c, x, topo_cartoes, largura_cartao, 88, C_FUNDO, C_BORDA)
        texto(c, x + 16, topo_cartoes + 18, chave.upper(), 8, C_SUAVE)
        texto(c, x + 16, topo_cartoes + 34, f"B2: {valor_km(valor_b2, '/km')}", 8.5, C_SUAVE)
        texto(c, x + 16, topo_cartoes + 60, valor_km(valor_b3, '/km'), 17, C_TEXTO, negrito=True)
        variacao(c, x + 16, topo_cartoes + 78, delta, sufixo=" vs B2", tamanho=9.5)

    bloco_observacoes(c, topo_cartoes + 108, pagina, ctx)


def _pagina_11(c, d, cont, ctx):
    pagina = cont["pagina_11_resumo_semestre"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    meses = d["meta"]["meses"]
    linhas = [
        ("Manutenção (R$K)", lambda m: numero_br(d["mensal"][m]["Manutenção total"] / 1000), False),
        ("Combustível (R$K)", lambda m: numero_br(d["mensal"][m]["Combustível total"] / 1000), False),
        ("Pedágio (R$K)", lambda m: numero_br(d["mensal"][m]["Pedágio total"] / 1000), False),
        ("KM rodado (M)", lambda m: numero_br(d['mensal'][m]['KM rodado total'] / 1e6), False),
        ("Custo/km (R$)", lambda m: numero_br(d['mensal'][m]['Custo/km total']), True),
    ]

    topo = 128
    altura_cabecalho = 26
    largura_rotulo = 145
    largura_coluna = (LARGURA_UTIL - largura_rotulo) / len(meses)

    c.setFillColor(C_MARROM)
    c.rect(MARGEM, y(topo + altura_cabecalho), LARGURA_UTIL, altura_cabecalho, stroke=0, fill=1)
    texto(c, MARGEM + 12, topo + 17.5, "INDICADOR", 9, C_BRANCO, negrito=True)
    for i, mes in enumerate(meses):
        centro = MARGEM + largura_rotulo + i * largura_coluna + largura_coluna / 2
        texto(c, centro, topo + 17.5, mes.upper(), 9, C_BRANCO, negrito=True,
              alinhamento="centro")

    topo += altura_cabecalho
    altura_linha = 24.5
    for i, (rotulo, formatar, destaque) in enumerate(linhas):
        if destaque:
            c.setFillColor(HexColor("#F7F2F2"))
            c.rect(MARGEM, y(topo + altura_linha), LARGURA_UTIL, altura_linha, stroke=0, fill=1)
        elif i % 2 == 1:
            c.setFillColor(C_ZEBRA)
            c.rect(MARGEM, y(topo + altura_linha), LARGURA_UTIL, altura_linha, stroke=0, fill=1)

        cor = C_MARROM if destaque else C_TEXTO
        texto(c, MARGEM + 12, topo + 16.5, rotulo, 9.5, cor, negrito=destaque)
        for j, mes in enumerate(meses):
            centro = MARGEM + largura_rotulo + j * largura_coluna + largura_coluna / 2
            texto(c, centro, topo + 16.5, formatar(mes), 9.5, cor, negrito=destaque,
                  alinhamento="centro")
        topo += altura_linha

        c.setStrokeColor(C_BORDA)
        c.setLineWidth(0.6)
        c.line(MARGEM, y(topo), LARGURA - MARGEM, y(topo))

    topo += 32
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, nome in enumerate(["B1", "B2", "B3"]):
        bim = d["bimestral"][nome]
        x = MARGEM + i * (largura_cartao + 12)
        caixa(c, x, topo, largura_cartao, 95, C_BRANCO, C_MARROM, raio=8)
        texto(c, x + 16, topo + 20, f"{nome} · {d['meta']['bimestres'][nome]}", 10.5,
              C_MARROM, negrito=True)
        texto(c, x + 16, topo + 47, moeda(bim["Total operacional"]), 19, C_TEXTO, negrito=True)
        texto(c, x + 16, topo + 63, f"{km_curto(bim['KM rodado total'])} km rodados", 8.5, C_SUAVE)
        texto(c, x + 16, topo + 82, valor_km(bim['Custo/km total'], '/km'), 11, C_TEXTO, negrito=True)

    bloco_observacoes(c, topo + 118, pagina, ctx)


def _pagina_12(c, d, cont, ctx):
    pagina = cont["pagina_12_fechamento"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    b1, b3 = d["bimestral"]["B1"], d["bimestral"]["B3"]
    var = d["variacoes"]["B3 vs B1"]

    caixa(c, MARGEM, 125, LARGURA_UTIL, 148, C_FUNDO, C_MARROM, raio=8)
    texto(c, MARGEM + 20, 152, interpolar(pagina.get("subtitulo"), ctx), 12, C_MARROM,
          negrito=True)

    # Diesel e km rodado são contexto de mercado e de volume: mostramos a
    # direção em preto. Só custo/km e manutenção/km recebem verde ou vermelho.
    indicadores = [
        ("DIESEL MÉDIO", f"B1: {valor_litro(b1['Preço médio diesel S10'])}",
         f"B3: {valor_litro(b3['Preço médio diesel S10'])}",
         var["Preço médio diesel S10"], True),
        ("KM RODADO", f"B1: {km_curto(b1['KM rodado total'])}",
         f"B3: {km_curto(b3['KM rodado total'])}", var["KM rodado total"], True),
        ("CUSTO/KM TOTAL", f"B1: {valor_km(b1['Custo/km total'])}",
         f"B3: {valor_km(b3['Custo/km total'])}", var["Custo/km total"], False),
        ("MANUTENÇÃO/KM", f"B1: {valor_km(b1['Custo/km manutenção'])}",
         f"B3: {valor_km(b3['Custo/km manutenção'])}", var["Custo/km manutenção"], False),
    ]
    largura_coluna = (LARGURA_UTIL - 40) / 4
    for i, (rotulo, linha_b1, linha_b3, delta, neutro) in enumerate(indicadores):
        x = MARGEM + 20 + i * largura_coluna
        texto(c, x, 175, rotulo, 8.5, C_SUAVE)
        texto(c, x, 192, linha_b1, 8.5, C_SUAVE)
        texto(c, x, 215, linha_b3, 14, C_TEXTO, negrito=True)
        variacao(c, x, 240, delta, tamanho=11, neutro=neutro)

    texto(c, MARGEM, 305, interpolar(pagina.get("titulo_analise"), ctx), 11, C_TEXTO,
          negrito=True)
    topo = paragrafo(c, MARGEM, 332, LARGURA_UTIL,
                     interpolar(pagina.get("texto_analise"), ctx), 10, C_TEXTO,
                     entrelinha=16.5)
    bloco_observacoes(c, topo + 14, pagina, ctx)


def _pagina_13(c, d, cont, ctx):
    pagina = cont["pagina_13_proximos_passos"]
    topo = secao(c, 81, interpolar(pagina.get("titulo"), ctx)) + 22
    topo = lista_topicos(c, topo, pagina.get("itens"), ctx, espaco=12)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_14(c, d, cont, ctx):
    pagina_observacoes_gerais(c, cont, ctx, "pagina_14_observacoes_gerais")


# =======================================================================
# CONTEXTO PARA OS TEXTOS DO YAML
# =======================================================================

def montar_contexto(d):
    """Valores prontos para uso como {placeholder} nos textos do YAML."""
    b1, b2, b3 = d["bimestral"]["B1"], d["bimestral"]["B2"], d["bimestral"]["B3"]
    v32, v31 = d["variacoes"]["B3 vs B2"], d["variacoes"]["B3 vs B1"]
    meta = d["meta"]

    ctx = {
        "periodo": f"{meta['meses'][0]} a {meta['meses'][-1]} {meta['ano']}",
        "ano": meta["ano"],
        "mes_inicial": meta["meses"][0],
        "mes_final": meta["meses"][-1],
        "b1_meses": meta["bimestres"]["B1"],
        "b2_meses": meta["bimestres"]["B2"],
        "b3_meses": meta["bimestres"]["B3"],
        "mes_b3_inicial": meta["meses"][4],
        "mes_b3_final": meta["meses"][5],
    }

    for nome, bim in [("b1", b1), ("b2", b2), ("b3", b3)]:
        ctx.update({
            f"{nome}_total": moeda(bim["Total operacional"]),
            f"{nome}_manutencao": moeda(bim["Manutenção total"]),
            f"{nome}_combustivel": moeda(bim["Combustível total"]),
            f"{nome}_pedagio": moeda(bim["Pedágio total"]),
            f"{nome}_manutencao_k": moeda_milhar(bim['Manutenção total']),
            f"{nome}_km": km_curto(bim["KM rodado total"]),
            f"{nome}_litros": milhares(bim["Litros consumidos"]),
            f"{nome}_ckm": valor_km(bim['Custo/km total']),
            f"{nome}_ckm_combustivel": valor_km(bim['Custo/km combustível']),
            f"{nome}_ckm_manutencao": valor_km(bim['Custo/km manutenção']),
            f"{nome}_diesel": moeda_cheia(bim['Preço médio diesel S10']),
            f"{nome}_consumo": numero_br(bim['Consumo médio (km/L)']),
            f"{nome}_passagens": inteiro(bim["Número de passagens pedágio"]),
        })

    # Cada variação vem em duas formas: sem sinal (para frases como "14.3% mais
    # caro") e com sinal, sufixo _sinal (para valores entre parênteses).
    variacoes = [
        ("var_total", v32["Total operacional"]),
        ("var_ckm", v32["Custo/km total"]),
        ("var_manutencao", v32["Manutenção total"]),
        ("var_combustivel", v32["Combustível total"]),
        ("var_pedagio", v32["Pedágio total"]),
        ("var_km", v32["KM rodado total"]),
        ("var_diesel", v32["Preço médio diesel S10"]),
        ("var_ckm_manutencao", v32["Custo/km manutenção"]),
        ("var_total_b1", v31["Total operacional"]),
        ("var_ckm_b1", v31["Custo/km total"]),
        ("var_km_b1", v31["KM rodado total"]),
        ("var_diesel_b1", v31["Preço médio diesel S10"]),
        ("var_ckm_manutencao_b1", v31["Custo/km manutenção"]),
    ]
    for nome, valor in variacoes:
        ctx[nome] = pct(valor)
        ctx[f"{nome}_sinal"] = pct_sinal(valor)

    ctx.update({
        "delta_passagens": inteiro(
            b3["Número de passagens pedágio"] - b2["Número de passagens pedágio"]),
        "delta_pedagio": moeda(b3["Pedágio total"] - b2["Pedágio total"]),
    })

    concessionarias = [x["nome"] for x in d["quebras"]["pedagio_concessionaria"]]
    ctx["top_concessionarias"] = ", ".join(concessionarias[:3]) if concessionarias else "—"

    pracas = d["quebras"]["pedagio_passagens"][:3]
    ctx["top_pracas"] = "; ".join(
        f"{p['praca']} (de {p['antes']} para {p['depois']})" for p in pracas) or "—"

    return ctx


# =======================================================================
# MONTAGEM DO RELATÓRIO
# =======================================================================

PAGINAS = [
    (_pagina_1, "pagina_1_visao_executiva"),
    (_pagina_2, "pagina_2_evolucao_custo_km"),
    (_pagina_3, "pagina_3_indicadores_operacionais"),
    (_pagina_4, "pagina_4_manutencao"),
    (_pagina_5, "pagina_5_combustivel"),
    (_pagina_6, "pagina_6_pedagio"),
    (_pagina_7, "pagina_7_pedagio_detalhe"),
    (_pagina_8, "pagina_8_custo_km_filial"),
    (_pagina_9, "pagina_9_custo_km_detalhado"),
    (_pagina_10, "pagina_10_hodometro_manutencao"),
    (_pagina_11, "pagina_11_resumo_semestre"),
    (_pagina_12, "pagina_12_fechamento"),
    (_pagina_13, "pagina_13_proximos_passos"),
    (_pagina_14, "pagina_14_observacoes_gerais"),
]


def carregar_conteudo():
    with open(CAMINHO_YAML, "r", encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def gerar_pdf_torre(semestre=1, ano=2026, saida=None, usar_cache=True):
    print(f"📄 Iniciando geração do PDF Torre de Controle - {semestre}S/{ano}")

    conteudo = carregar_conteudo()
    dados = calcular_dados_torre(semestre, ano, usar_cache=usar_cache)
    contexto = montar_contexto(dados)

    saida = saida or os.path.join(RAIZ, f"Torre_Controle_{ano}_S{semestre}.pdf")

    print("🖌️  Montando PDF...")
    c = canvas.Canvas(saida, pagesize=A4)
    c.setTitle(f"{conteudo['relatorio']['titulo']} - {ano} S{semestre}")
    c.setAuthor(conteudo["relatorio"]["empresa"])

    montar_documento(c, conteudo, PAGINAS, dados, contexto)
    c.save()
    print(f"✅ PDF gerado com sucesso em: {saida}")
    return saida


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gera o Relatório Torre de Controle.")
    parser.add_argument("--semestre", type=int, default=1)
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--saida", type=str, default=None)
    parser.add_argument("--sem-cache", action="store_true",
                        help="Reconsulta os bancos antes de gerar.")
    args = parser.parse_args()

    gerar_pdf_torre(args.semestre, args.ano, args.saida, usar_cache=not args.sem_cache)
