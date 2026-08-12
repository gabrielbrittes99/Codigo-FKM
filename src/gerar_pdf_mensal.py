"""
Gerador do Relatório Executivo Mensal da Torre de Controle (A4 retrato).

Fecha um mês contra o mês anterior e o posiciona na evolução do ano. Usa a
mesma identidade visual do relatório semestral (`torre_layout.py`) e o mesmo
esquema editorial: todo texto vem de `conteudo_mensal.yaml`.
"""

import os
import warnings

import numpy as np
import yaml
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from src.torre_dados import calcular_dados_mes
from src.torre_layout import (
    AZUL, BRANCO, C_BORDA, C_BRANCO, C_FUNDO, C_MARROM, C_SUAVE, C_TEXTO,
    C_VERDE, C_VERMELHO, C_ZEBRA, LARGURA, LARGURA_UTIL, MARGEM, MARROM, RAIZ,
    ROSA, TEXTO, TEXTO_SUAVE, VERDE, VERMELHO, VERMELHO_MEDIO,
    bloco_observacoes, caixa, cor_sobre, grafico, inteiro, interpolar, km_curto, linha,
    lista_topicos, meses_em_negrito, milhares, moeda, montar_documento,
    nova_figura, pagina_observacoes_gerais, paragrafo, pct, pct_sinal,
    quebrar, rotulos_em_negrito, secao, texto, variacao, y,
)

warnings.filterwarnings("ignore")

CAMINHO_YAML = os.path.join(RAIZ, "conteudo_mensal.yaml")


def _rotulos(d):
    """('Jun', 'Jul') — nomes curtos do mês de comparação e do mês fechado."""
    return d["meta"]["mes_anterior_nome"], d["meta"]["mes_nome"]


def _cores_meses(meses, destaque=2):
    """Meses recentes em tom forte, anteriores em tom claro."""
    cores = [ROSA] * len(meses)
    for i in range(max(0, len(meses) - destaque), len(meses)):
        cores[i] = MARROM if i == len(meses) - 1 else VERMELHO_MEDIO
    return cores


# =======================================================================
# PÁGINAS
# =======================================================================

def _pagina_1(c, d, cont, ctx):
    """Visão executiva: cards do mês vs mês anterior + evolução do ano."""
    pagina = cont["pagina_1_visao_executiva"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    anterior, atual, var = d["anterior"], d["atual"], d["variacao"]
    rot_ant, rot_atual = _rotulos(d)

    cartoes = [
        ("MANUTENÇÃO", "Manutenção total"),
        ("COMBUSTÍVEL", "Combustível total"),
        ("PEDÁGIO", "Pedágio total"),
        ("TOTAL OPERACIONAL", "Total operacional"),
    ]
    largura_cartao = (LARGURA_UTIL - 3 * 10) / 4

    for i, (rotulo, chave) in enumerate(cartoes):
        x = MARGEM + i * (largura_cartao + 10)
        caixa(c, x, 124, largura_cartao, 110, C_FUNDO, raio=6)
        c.setFillColor(C_MARROM)
        c.roundRect(x, y(142), largura_cartao, 18, 6, stroke=0, fill=1)
        c.rect(x, y(142), largura_cartao, 6, stroke=0, fill=1)
        texto(c, x + 12, 137.0, rotulo, 8, C_BRANCO, negrito=True)

        texto(c, x + 12, 155.0, rot_ant, 8, C_SUAVE)
        texto(c, x + 12, 172.9, moeda(anterior[chave]), 15, C_TEXTO, negrito=True)
        texto(c, x + 12, 189.0, rot_atual, 8, C_SUAVE)
        texto(c, x + 12, 206.9, moeda(atual[chave]), 15, C_TEXTO, negrito=True)
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
                fontsize=7.5, fontweight="bold", color=TEXTO)

    limite = max(totais) * 1.20
    ax.set_ylim(0, limite)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.legend(loc="upper left", fontsize=8, frameon=False, bbox_to_anchor=(0.02, 0.99))
    ax.tick_params(axis="x", labelsize=9)
    meses_em_negrito(ax)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 290, 525, 300)


def _pagina_2(c, d, cont, ctx):
    """Custo por km no ano + leitura do mês."""
    pagina = cont["pagina_2_custo_km"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    caixa(c, MARGEM, 120, LARGURA_UTIL, 175, C_BRANCO, C_BORDA, raio=8)

    fig, ax = nova_figura(500, 160)
    meses = d["meta"]["meses"]
    valores = [d["mensal"][m]["Custo/km total"] for m in meses]

    ax.plot(meses, valores, color=MARROM, linewidth=2, marker="o", markersize=6, zorder=3)
    ax.scatter([len(meses) - 1], [valores[-1]], color=MARROM, s=110, zorder=4)
    amplitude = max(max(valores) - min(valores), 0.001)
    for i, valor in enumerate(valores):
        ax.text(i, valor + amplitude * 0.13, f"R$ {valor:.3f}", ha="center",
                fontsize=8, fontweight="bold", color=MARROM)

    ax.set_ylim(min(valores) - amplitude * 0.45, max(valores) + amplitude * 0.45)
    ax.set_ylabel("R$/km", fontsize=8)
    ax.tick_params(axis="x", labelsize=9)
    meses_em_negrito(ax)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 12, 128, 500, 160)

    topo = secao(c, 315, interpolar(pagina.get("subtitulo"), ctx)) + 18
    topo = lista_topicos(c, topo, pagina.get("paragrafos"), ctx)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_3(c, d, cont, ctx):
    """Indicadores operacionais e preço do diesel."""
    pagina = cont["pagina_3_indicadores"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    anterior, atual = d["anterior"], d["atual"]
    rot_ant, rot_atual = _rotulos(d)

    fig, ax = nova_figura(525, 260)
    categorias = ["Combustível\npor km", "Manutenção\npor km", "Total\noperacional/km"]
    chaves = ["Custo/km combustível", "Custo/km manutenção", "Custo/km total"]
    valores_ant = [anterior[k] for k in chaves]
    valores_atual = [atual[k] for k in chaves]
    posicoes = np.arange(len(categorias))

    ax.bar(posicoes - 0.2, valores_ant, 0.38, color=ROSA, label=rot_ant)
    ax.bar(posicoes + 0.2, valores_atual, 0.38, color=MARROM, label=rot_atual)

    teto = max(valores_ant + valores_atual) * 1.35
    for i, (v1, v2) in enumerate(zip(valores_ant, valores_atual)):
        ax.text(i - 0.2, v1 + teto * 0.02, f"R$ {v1:.3f}", ha="center", fontsize=8,
                color=TEXTO_SUAVE)
        ax.text(i + 0.2, v2 + teto * 0.02, f"R$ {v2:.3f}", ha="center", fontsize=8,
                fontweight="bold", color=TEXTO)
        delta = (v2 / v1 - 1) * 100 if v1 else 0
        ax.text(i + 0.2, v2 + teto * 0.10, f"({delta:+.1f}%)", ha="center", fontsize=8,
                fontweight="bold", color=VERDE if delta < 0 else VERMELHO)

    ax.set_xticks(posicoes)
    ax.set_xticklabels(categorias, fontsize=8.5)
    ax.set_ylim(0, teto)
    ax.set_ylabel("R$/km", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 260)

    secao(c, 385, interpolar(pagina.get("subtitulo"), ctx))

    indicadores = [
        ("KM RODADO", f"{rot_ant}: {km_curto(anterior['KM rodado total'])} km",
         f"{rot_atual}: {km_curto(atual['KM rodado total'])} km", False),
        ("LITROS CONSUMIDOS", f"{rot_ant}: {milhares(anterior['Litros consumidos'])} L",
         f"{rot_atual}: {milhares(atual['Litros consumidos'])} L", False),
        ("PREÇO MÉDIO DIESEL S10", f"{rot_ant}: R$ {anterior['Preço médio diesel S10']:.3f}/L",
         f"{rot_atual}: R$ {atual['Preço médio diesel S10']:.3f}/L", True),
        ("CONSUMO MÉDIO FROTA", f"{rot_ant}: {anterior['Consumo médio (km/L)']:.2f} km/L",
         f"{rot_atual}: {atual['Consumo médio (km/L)']:.2f} km/L", False),
    ]
    largura_cartao = (LARGURA_UTIL - 3 * 10) / 4
    for i, (rotulo, linha_ant, linha_atual, destaque) in enumerate(indicadores):
        x = MARGEM + i * (largura_cartao + 10)
        caixa(c, x, 428, largura_cartao, 78, C_FUNDO, C_BORDA)
        texto(c, x + 12, 445, rotulo, 7.5, C_SUAVE)
        texto(c, x + 12, 461, linha_ant, 8, C_SUAVE)
        texto(c, x + 12, 490, linha_atual, 13, C_VERMELHO if destaque else C_TEXTO,
              negrito=True)

    secao(c, 528, interpolar(pagina.get("titulo_diesel"), ctx))

    fig, ax = nova_figura(500, 175)
    meses = d["meta"]["meses"]
    precos = [d["mensal"][m]["Preço médio diesel S10"] for m in meses]
    amplitude = max(max(precos) - min(precos), 0.01)

    ax.plot(meses, precos, color=MARROM, linewidth=2, marker="o", markersize=5, zorder=3)
    ax.fill_between(range(len(meses)), precos, min(precos) * 0.97, color=MARROM, alpha=0.10)
    for i, preco in enumerate(precos):
        ax.text(i, preco + amplitude * 0.13, f"R$ {preco:.3f}/L", ha="center",
                fontsize=7.5, fontweight="bold", color=MARROM)

    ax.set_ylim(min(precos) * 0.97, max(precos) * 1.06)
    ax.set_ylabel("R$/litro", fontsize=8)
    meses_em_negrito(ax)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 12, 562, 500, 175)

    topo = paragrafo(c, MARGEM, 758, LARGURA_UTIL,
                     interpolar(pagina.get("texto_diesel"), ctx), 9, C_SUAVE)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_4(c, d, cont, ctx):
    """Manutenção: natureza e filiais."""
    pagina = cont["pagina_4_manutencao"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    natureza = d["quebras"]["manutencao_natureza"]
    rot_ant, rot_atual = _rotulos(d)

    fig, ax = nova_figura(525, 250)
    categorias = list(natureza["atual"].keys())
    valores_ant = [natureza["anterior"][k] / 1000 for k in categorias]
    valores_atual = [natureza["atual"][k] / 1000 for k in categorias]
    posicoes = np.arange(len(categorias))

    ax.bar(posicoes - 0.2, valores_ant, 0.38, color=ROSA, label=rot_ant)
    ax.bar(posicoes + 0.2, valores_atual, 0.38, color=MARROM, label=rot_atual)

    teto = max(valores_ant + valores_atual + [1]) * 1.32
    for i, (v1, v2) in enumerate(zip(valores_ant, valores_atual)):
        ax.text(i - 0.2, v1 + teto * 0.015, f"R$ {v1:.0f}K", ha="center", fontsize=8,
                color=TEXTO_SUAVE)
        ax.text(i + 0.2, v2 + teto * 0.015, f"R$ {v2:.0f}K", ha="center", fontsize=8,
                fontweight="bold", color=TEXTO)
        delta = (v2 / v1 - 1) * 100 if v1 else 0
        ax.text(i + 0.2, v2 + teto * 0.085, f"({delta:+.1f}%)", ha="center", fontsize=8,
                fontweight="bold", color=VERDE if delta < 0 else VERMELHO)

    ax.set_xticks(posicoes)
    ax.set_xticklabels([k.replace(" de ", " de\n").replace(" e ", " e\n") for k in categorias],
                       fontsize=8.5)
    ax.set_ylim(0, teto)
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
        ax.text(valor + max(valores) * 0.01, i, f" R$ {valor:.0f}K", va="center",
                fontsize=8, color=TEXTO)
    ax.set_xlim(0, max(valores) * 1.16)
    ax.set_xlabel("R$ (milhares)", fontsize=8)
    rotulos_em_negrito(ax)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 408, 525, 270)

    bloco_observacoes(c, 690, pagina, ctx)


def _pagina_5(c, d, cont, ctx):
    """Combustível por tipo + ações de gestão."""
    pagina = cont["pagina_5_combustivel"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    tipos = d["quebras"]["combustivel_tipo"]
    rot_ant, rot_atual = _rotulos(d)

    fig, ax = nova_figura(525, 250)
    categorias = list(tipos["atual"].keys())
    valores_ant = [tipos["anterior"][k] / 1000 for k in categorias]
    valores_atual = [tipos["atual"][k] / 1000 for k in categorias]
    posicoes = np.arange(len(categorias))

    ax.bar(posicoes - 0.2, valores_ant, 0.38, color=ROSA, label=rot_ant)
    ax.bar(posicoes + 0.2, valores_atual, 0.38, color=MARROM, label=rot_atual)

    teto = max(valores_ant + valores_atual + [1]) * 1.30
    for i, (v1, v2) in enumerate(zip(valores_ant, valores_atual)):
        ax.text(i - 0.2, v1 + teto * 0.015, f"R$ {v1:.0f}K", ha="center", fontsize=7.5,
                color=TEXTO_SUAVE)
        ax.text(i + 0.2, v2 + teto * 0.015, f"R$ {v2:.0f}K", ha="center", fontsize=7.5,
                fontweight="bold", color=TEXTO)
        delta = (v2 / v1 - 1) * 100 if v1 else 0
        ax.text(i + 0.2, v2 + teto * 0.085, f"({delta:+.1f}%)", ha="center", fontsize=8,
                fontweight="bold", color=VERDE if delta < 0 else VERMELHO)

    ax.set_xticks(posicoes)
    ax.set_xticklabels([k.replace(" ", "\n") for k in categorias], fontsize=8.5)
    ax.set_ylim(0, teto)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 250)

    topo = secao(c, 378, interpolar(pagina.get("subtitulo"), ctx)) + 18
    topo = lista_topicos(c, topo, pagina.get("topicos"), ctx)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_6(c, d, cont, ctx):
    """Pedágio: evolução no ano, cards e concessionárias."""
    pagina = cont["pagina_6_pedagio"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    meses = d["meta"]["meses"]
    valores = [d["mensal"][m]["Pedágio total"] / 1000 for m in meses]
    passagens = [d["mensal"][m]["Número de passagens pedágio"] for m in meses]

    cores = _cores_meses(meses)
    fig, ax = nova_figura(525, 250)
    ax.bar(meses, valores, color=cores, width=0.62)
    for i, (valor, passagem) in enumerate(zip(valores, passagens)):
        ax.text(i, valor + max(valores) * 0.04, f"R$ {valor:.0f}K", ha="center",
                fontsize=8, fontweight="bold", color=TEXTO)
        ax.text(i, valor - max(valores) * 0.05, inteiro(passagem), ha="center",
                fontsize=6.5, fontweight="bold", color=cor_sobre(cores[i]))

    ax.set_ylim(0, max(valores) * 1.22)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    meses_em_negrito(ax)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 250)

    anterior, atual, var = d["anterior"], d["atual"], d["variacao"]
    rot_ant, rot_atual = _rotulos(d)
    delta_valor = atual["Pedágio total"] - anterior["Pedágio total"]
    delta_passagens = (atual["Número de passagens pedágio"]
                       - anterior["Número de passagens pedágio"])

    cartoes = [
        (rot_ant.upper(), moeda(anterior["Pedágio total"]),
         f"{inteiro(anterior['Número de passagens pedágio'])} passagens", None),
        (rot_atual.upper(), moeda(atual["Pedágio total"]),
         f"{inteiro(atual['Número de passagens pedágio'])} passagens", None),
        ("VARIAÇÃO", moeda(delta_valor), f"{inteiro(delta_passagens)} passagens",
         var["Pedágio total"]),
    ]
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, (rotulo, valor, detalhe, delta) in enumerate(cartoes):
        x = MARGEM + i * (largura_cartao + 12)
        caixa(c, x, 385, largura_cartao, 95, C_FUNDO, C_BORDA)
        texto(c, x + 16, 403, rotulo, 8.5, C_SUAVE)
        texto(c, x + 16, 433, valor, 19, C_TEXTO, negrito=True)
        texto(c, x + 16, 451, detalhe, 8.5, C_SUAVE)
        if delta is not None:
            variacao(c, x + 16, 470, delta, tamanho=10)

    secao(c, 505, interpolar(pagina.get("titulo_concessionarias"), ctx), tamanho=13)

    concessionarias = d["quebras"]["pedagio_concessionaria"]
    fig, ax = nova_figura(490, 200)
    nomes = list(concessionarias.keys())[::-1]
    valores_conc = list(concessionarias.values())[::-1]

    ax.barh(nomes, valores_conc, color=AZUL, height=0.6)
    for i, valor in enumerate(valores_conc):
        ax.text(valor + max(valores_conc) * 0.01, i, f" R$ {inteiro(valor)}", va="center",
                fontsize=7.5, color=TEXTO)
    ax.set_xlim(0, max(valores_conc) * 1.2)
    ax.set_xlabel(f"R$ em {d['meta']['mes_extenso']}", fontsize=8)
    rotulos_em_negrito(ax, 7.5)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 25, 535, 490, 200)

    topo = paragrafo(c, MARGEM, 752, LARGURA_UTIL,
                     interpolar(pagina.get("texto_analise"), ctx), 9, C_SUAVE)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_7(c, d, cont, ctx):
    """Custo por km de combustível por filial."""
    pagina = cont["pagina_7_custo_km_filial"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    filiais = d["quebras"]["custo_km_filial"]
    limite_alto = pagina.get("limite_alto", 1.00)
    limite_baixo = pagina.get("limite_baixo", 0.65)

    fig, ax = nova_figura(510, 545)
    nomes = [f["filial"] for f in filiais][::-1]
    valores = [f["ckm_atual"] for f in filiais][::-1]
    cores = [MARROM if v >= limite_alto else (VERMELHO_MEDIO if v >= limite_baixo else ROSA)
             for v in valores]

    ax.barh(nomes, valores, color=cores, height=0.68)
    for i, valor in enumerate(valores):
        ax.text(valor + max(valores) * 0.008, i, f" R$ {valor:.3f}", va="center",
                fontsize=7.5, color=TEXTO)

    ax.set_xlim(0, max(valores) * 1.18)
    ax.set_xlabel(f"R$/km (Combustível) em {d['meta']['mes_extenso']}", fontsize=8)
    rotulos_em_negrito(ax, 7.5)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color=MARROM, label=f"Acima de R$ {limite_alto:.2f}/km"),
        Patch(color=VERMELHO_MEDIO, label=f"R$ {limite_baixo:.2f} a R$ {limite_alto:.2f}/km"),
        Patch(color=ROSA, label=f"Abaixo de R$ {limite_baixo:.2f}/km"),
    ], loc="lower right", fontsize=7.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 10, 112, 510, 545)

    bloco_observacoes(c, 672, pagina, ctx)


def _pagina_8(c, d, cont, ctx):
    """Tabela detalhada por filial."""
    pagina = cont["pagina_8_detalhamento_filial"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    filiais = d["quebras"]["custo_km_filial"]
    rot_ant, rot_atual = _rotulos(d)
    colunas = [
        ("FILIAL", MARGEM + 12),
        (f"KM ({rot_ant})", MARGEM + 140),
        (f"KM ({rot_atual})", MARGEM + 205),
        (f"R$/km {rot_ant}", MARGEM + 270),
        (f"R$/km {rot_atual}", MARGEM + 340),
        ("VARIAÇÃO", MARGEM + 410),
        ("PLACAS", MARGEM + 480),
    ]

    topo = 132
    for rotulo, x in colunas:
        texto(c, x, topo, rotulo, 8.5, C_SUAVE, negrito=True)

    topo += 8
    linha(c, topo)
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
        texto(c, colunas[3][1], topo, f"R$ {filial['ckm_ref']:.3f}", 9, C_SUAVE)
        texto(c, colunas[4][1], topo, f"R$ {filial['ckm_atual']:.3f}", 9, C_TEXTO, negrito=True)
        texto(c, colunas[5][1], topo, pct_sinal(filial["var"]), 9, cor_var, negrito=True)
        texto(c, colunas[6][1], topo, str(filial["placas"]), 9, C_TEXTO)
        topo += altura_linha

    anterior, atual = d["anterior"], d["atual"]
    var_total = ((atual["Custo/km combustível"] / anterior["Custo/km combustível"] - 1) * 100
                 if anterior["Custo/km combustível"] else 0)

    topo += 2
    linha(c, topo, C_MARROM, 1.2)
    topo += 17

    total = [
        "TOTAL / MÉDIA", km_curto(anterior["KM rodado total"]),
        km_curto(atual["KM rodado total"]),
        f"R$ {anterior['Custo/km combustível']:.3f}",
        f"R$ {atual['Custo/km combustível']:.3f}",
        pct_sinal(var_total), str(sum(f["placas"] for f in filiais)),
    ]
    for (_, x), valor in zip(colunas, total):
        texto(c, x, topo, valor, 9, C_MARROM, negrito=True)

    bloco_observacoes(c, topo + 22, pagina, ctx)


def _pagina_9(c, d, cont, ctx):
    """Hodômetro vs custo de manutenção no mês."""
    pagina = cont["pagina_9_hodometro_manutencao"]
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

    # Alterna o lado do rótulo: os pontos se concentram numa faixa estreita e
    # os nomes das placas se sobrepõem se saírem todos para o mesmo lado
    ordenadas = sorted(placas, key=lambda p: p["odometro"])
    for i, p in enumerate(ordenadas):
        acima = i % 2 == 0
        ax.annotate(p["placa"], (p["odometro"] / 1000, p["valor"] / 1000),
                    xytext=(6, 4 if acima else -9), textcoords="offset points",
                    fontsize=6.5, color=TEXTO)

    ax.margins(x=0.09, y=0.16)
    ax.axvline(corte / 1000, color="#888888", linestyle="--", linewidth=1, zorder=1)
    limite_x = ax.get_xlim()
    ax.axvspan(corte / 1000, limite_x[1], color=MARROM, alpha=0.045, zorder=0)
    ax.set_xlim(limite_x)
    ax.text(corte / 1000, ax.get_ylim()[1], f"{corte // 1000} mil km", ha="center",
            va="bottom", fontsize=7.5, fontweight="bold", color=TEXTO_SUAVE)

    ax.set_xlabel("Hodômetro (milhares de km)", fontsize=8)
    ax.set_ylabel(f"Custo de manutenção em {d['meta']['mes_extenso']} (R$ mil)", fontsize=8)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 5, 112, 520, 285)

    analise = interpolar(pagina.get("texto_analise"), ctx)
    linhas_texto = quebrar(c, analise, LARGURA_UTIL - 40, "Helvetica", 9)
    altura_caixa = 22 + len(linhas_texto) * 14
    caixa(c, MARGEM, 412, LARGURA_UTIL, altura_caixa, C_FUNDO)
    paragrafo(c, MARGEM + 20, 429, LARGURA_UTIL - 40, analise, 9, C_TEXTO, entrelinha=14)

    topo_cartoes = 412 + altura_caixa + 26
    linha(c, topo_cartoes - 14)

    natureza_km = d["quebras"]["manutencao_natureza_km"]
    rot_ant = d["meta"]["mes_anterior_nome"]
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, chave in enumerate(natureza_km["atual"].keys()):
        x = MARGEM + i * (largura_cartao + 12)
        valor_ant = natureza_km["anterior"][chave]
        valor_atual = natureza_km["atual"][chave]
        delta = (valor_atual / valor_ant - 1) * 100 if valor_ant else 0

        caixa(c, x, topo_cartoes, largura_cartao, 88, C_FUNDO, C_BORDA)
        texto(c, x + 16, topo_cartoes + 18, chave.upper(), 8, C_SUAVE)
        texto(c, x + 16, topo_cartoes + 34, f"{rot_ant}: R$ {valor_ant:.3f}/km", 8.5, C_SUAVE)
        texto(c, x + 16, topo_cartoes + 60, f"R$ {valor_atual:.3f}/km", 17, C_TEXTO,
              negrito=True)
        variacao(c, x + 16, topo_cartoes + 78, delta, sufixo=f" vs {rot_ant}", tamanho=9.5)

    bloco_observacoes(c, topo_cartoes + 108, pagina, ctx)


def _pagina_10(c, d, cont, ctx):
    """Acumulado do ano: tabela mês a mês + fechamento."""
    pagina = cont["pagina_10_acumulado"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    meses = d["meta"]["meses"]
    linhas_tabela = [
        ("Manutenção (R$K)", lambda m: inteiro(d["mensal"][m]["Manutenção total"] / 1000), False),
        ("Combustível (R$K)", lambda m: inteiro(d["mensal"][m]["Combustível total"] / 1000), False),
        ("Pedágio (R$K)", lambda m: inteiro(d["mensal"][m]["Pedágio total"] / 1000), False),
        ("KM rodado (M)", lambda m: f"{d['mensal'][m]['KM rodado total'] / 1e6:.2f}", False),
        ("Custo/km (R$)", lambda m: f"{d['mensal'][m]['Custo/km total']:.3f}", True),
    ]

    topo = 128
    altura_cabecalho = 26
    largura_rotulo = 135
    largura_coluna = (LARGURA_UTIL - largura_rotulo) / len(meses)

    c.setFillColor(C_MARROM)
    c.rect(MARGEM, y(topo + altura_cabecalho), LARGURA_UTIL, altura_cabecalho, stroke=0, fill=1)
    texto(c, MARGEM + 12, topo + 17.5, "INDICADOR", 9, C_BRANCO, negrito=True)
    for i, mes in enumerate(meses):
        centro = MARGEM + largura_rotulo + i * largura_coluna + largura_coluna / 2
        texto(c, centro, topo + 17.5, mes.upper(), 8.5, C_BRANCO, negrito=True,
              alinhamento="centro")

    topo += altura_cabecalho
    altura_linha = 24.5
    for i, (rotulo, formatar, destaque) in enumerate(linhas_tabela):
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
            texto(c, centro, topo + 16.5, formatar(mes), 8.5, cor, negrito=destaque,
                  alinhamento="centro")
        topo += altura_linha
        linha(c, topo, espessura=0.6)

    topo += 30
    acumulado, media = d["acumulado"], d["media_mensal"]
    cartoes = [
        ("ACUMULADO DO ANO", moeda(acumulado["Total operacional"]),
         f"{km_curto(acumulado['KM rodado total'])} km rodados",
         f"R$ {acumulado['Custo/km total']:.3f}/km"),
        ("MÉDIA MENSAL", moeda(media["Total operacional"]),
         f"{km_curto(media['KM rodado total'])} km por mês",
         f"{len(meses)} meses fechados"),
        (d["meta"]["mes_extenso"].upper(), moeda(d["atual"]["Total operacional"]),
         f"{km_curto(d['atual']['KM rodado total'])} km rodados",
         f"R$ {d['atual']['Custo/km total']:.3f}/km"),
    ]
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, (rotulo, valor, detalhe, rodape_cartao) in enumerate(cartoes):
        x = MARGEM + i * (largura_cartao + 12)
        caixa(c, x, topo, largura_cartao, 95, C_BRANCO, C_MARROM, raio=8)
        texto(c, x + 16, topo + 20, rotulo, 9.5, C_MARROM, negrito=True)
        texto(c, x + 16, topo + 47, valor, 19, C_TEXTO, negrito=True)
        texto(c, x + 16, topo + 63, detalhe, 8.5, C_SUAVE)
        texto(c, x + 16, topo + 82, rodape_cartao, 11, C_TEXTO, negrito=True)

    topo += 120
    texto(c, MARGEM, topo, interpolar(pagina.get("titulo_analise"), ctx), 11, C_TEXTO,
          negrito=True)
    topo = paragrafo(c, MARGEM, topo + 26, LARGURA_UTIL,
                     interpolar(pagina.get("texto_analise"), ctx), 9.5, C_TEXTO,
                     entrelinha=15.5)
    bloco_observacoes(c, topo + 12, pagina, ctx)


def _pagina_11(c, d, cont, ctx):
    pagina = cont["pagina_11_proximos_passos"]
    topo = secao(c, 81, interpolar(pagina.get("titulo"), ctx)) + 22
    topo = lista_topicos(c, topo, pagina.get("itens"), ctx, espaco=12)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_12(c, d, cont, ctx):
    pagina_observacoes_gerais(c, cont, ctx, "pagina_12_observacoes_gerais")


# =======================================================================
# CONTEXTO PARA OS TEXTOS DO YAML
# =======================================================================

def montar_contexto(d):
    """Valores prontos para uso como {placeholder} nos textos do YAML."""
    meta = d["meta"]
    anterior, atual, var = d["anterior"], d["atual"], d["variacao"]
    acumulado, media = d["acumulado"], d["media_mensal"]

    ctx = {
        "mes": meta["mes_extenso"],
        "mes_curto": meta["mes_nome"],
        "mes_anterior": meta["mes_anterior_extenso"] or "—",
        "mes_anterior_curto": meta["mes_anterior_nome"] or "—",
        "ano": meta["ano"],
        "meses_fechados": len(meta["meses"]),
        "periodo_ano": f"{meta['meses'][0]} a {meta['meses'][-1]} {meta['ano']}",
    }

    for nome, bloco in [("ant", anterior), ("mes", atual), ("acum", acumulado)]:
        ctx.update({
            f"{nome}_total": moeda(bloco["Total operacional"]),
            f"{nome}_manutencao": moeda(bloco["Manutenção total"]),
            f"{nome}_combustivel": moeda(bloco["Combustível total"]),
            f"{nome}_pedagio": moeda(bloco["Pedágio total"]),
            f"{nome}_manutencao_k": f"R$ {bloco['Manutenção total'] / 1000:.0f}K",
            f"{nome}_km": km_curto(bloco["KM rodado total"]),
            f"{nome}_litros": milhares(bloco["Litros consumidos"]),
            f"{nome}_ckm": f"R$ {bloco['Custo/km total']:.3f}",
            f"{nome}_ckm_combustivel": f"R$ {bloco['Custo/km combustível']:.3f}",
            f"{nome}_ckm_manutencao": f"R$ {bloco['Custo/km manutenção']:.3f}",
            f"{nome}_diesel": f"R$ {bloco['Preço médio diesel S10']:.3f}",
            f"{nome}_consumo": f"{bloco['Consumo médio (km/L)']:.2f}",
            f"{nome}_passagens": inteiro(bloco["Número de passagens pedágio"]),
        })

    ctx["media_total"] = moeda(media["Total operacional"])
    ctx["media_km"] = km_curto(media["KM rodado total"])

    variacoes = [
        ("var_total", var["Total operacional"]),
        ("var_ckm", var["Custo/km total"]),
        ("var_manutencao", var["Manutenção total"]),
        ("var_combustivel", var["Combustível total"]),
        ("var_pedagio", var["Pedágio total"]),
        ("var_km", var["KM rodado total"]),
        ("var_diesel", var["Preço médio diesel S10"]),
        ("var_consumo", var["Consumo médio (km/L)"]),
        ("var_ckm_manutencao", var["Custo/km manutenção"]),
        ("var_ckm_combustivel", var["Custo/km combustível"]),
        ("var_passagens", var["Número de passagens pedágio"]),
    ]
    for nome, valor in variacoes:
        ctx[nome] = pct(valor)
        ctx[f"{nome}_sinal"] = pct_sinal(valor)

    ctx["delta_pedagio"] = moeda(atual["Pedágio total"] - anterior["Pedágio total"])
    ctx["delta_passagens"] = inteiro(atual["Número de passagens pedágio"]
                                     - anterior["Número de passagens pedágio"])

    concessionarias = list(d["quebras"]["pedagio_concessionaria"].keys())
    ctx["top_concessionarias"] = ", ".join(concessionarias[:3]) if concessionarias else "—"

    filiais = d["quebras"]["custo_km_filial"]
    ctx["filial_mais_cara"] = filiais[0]["filial"] if filiais else "—"
    ctx["filial_mais_barata"] = filiais[-1]["filial"] if filiais else "—"

    pracas = d["quebras"]["pedagio_passagens"][:3]
    ctx["top_pracas"] = "; ".join(
        f"{p['praca']} (de {p['antes']} para {p['depois']})" for p in pracas) or "—"

    return ctx


# =======================================================================
# MONTAGEM DO RELATÓRIO
# =======================================================================

PAGINAS = [
    (_pagina_1, "pagina_1_visao_executiva"),
    (_pagina_2, "pagina_2_custo_km"),
    (_pagina_3, "pagina_3_indicadores"),
    (_pagina_4, "pagina_4_manutencao"),
    (_pagina_5, "pagina_5_combustivel"),
    (_pagina_6, "pagina_6_pedagio"),
    (_pagina_7, "pagina_7_custo_km_filial"),
    (_pagina_8, "pagina_8_detalhamento_filial"),
    (_pagina_9, "pagina_9_hodometro_manutencao"),
    (_pagina_10, "pagina_10_acumulado"),
    (_pagina_11, "pagina_11_proximos_passos"),
    (_pagina_12, "pagina_12_observacoes_gerais"),
]


def carregar_conteudo(dados):
    """Lê o YAML e resolve o período do cabeçalho a partir do mês fechado."""
    with open(CAMINHO_YAML, "r", encoding="utf-8") as arquivo:
        conteudo = yaml.safe_load(arquivo)

    meta = dados["meta"]
    rel = conteudo["relatorio"]
    rel["periodo"] = rel.get("periodo") or f"{meta['mes_extenso']} {meta['ano']}"
    rel["periodo"] = interpolar(rel["periodo"],
                                {"mes": meta["mes_extenso"], "ano": meta["ano"]})
    rel["data_geracao"] = interpolar(rel.get("data_geracao", ""),
                                     {"mes": meta["mes_extenso"], "ano": meta["ano"]})
    return conteudo


def gerar_pdf_mensal(mes=7, ano=2026, saida=None, usar_cache=True):
    print(f"📄 Iniciando geração do Relatório Executivo Mensal - {mes:02d}/{ano}")

    dados = calcular_dados_mes(mes, ano, usar_cache=usar_cache)
    if dados["anterior"] is None:
        raise SystemExit("❌ Janeiro não tem mês anterior no ano; escolha outro mês.")

    conteudo = carregar_conteudo(dados)
    contexto = montar_contexto(dados)

    saida = saida or os.path.join(RAIZ, f"Torre_Controle_Mensal_{ano}_{mes:02d}.pdf")

    print("🖌️  Montando PDF...")
    c = canvas.Canvas(saida, pagesize=A4)
    c.setTitle(f"{conteudo['relatorio']['titulo']} - {dados['meta']['mes_extenso']} {ano}")
    c.setAuthor(conteudo["relatorio"]["empresa"])

    montar_documento(c, conteudo, PAGINAS, dados, contexto)
    c.save()

    print(f"✅ PDF gerado com sucesso em: {saida}")
    return saida


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Gera o Relatório Executivo Mensal da Torre de Controle.")
    parser.add_argument("--mes", type=int, default=7, help="Mês fechado (1 a 12).")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--saida", type=str, default=None)
    parser.add_argument("--sem-cache", action="store_true",
                        help="Reconsulta os bancos antes de gerar.")
    args = parser.parse_args()

    gerar_pdf_mensal(args.mes, args.ano, args.saida, usar_cache=not args.sem_cache)
