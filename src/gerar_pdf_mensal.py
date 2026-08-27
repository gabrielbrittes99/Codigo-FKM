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
    moeda_cheia, moeda_k, moeda_milhar, nova_figura, numero_br,
    pagina_observacoes_gerais, paragrafo, pct, pct_sinal, preenchido, quebrar,
    rotulos_em_negrito, rotulos_par_de_barras, secao, secao_opcional, tem_blocos, texto, valor_km,
    valor_litro, variacao, y,
)

warnings.filterwarnings("ignore")

CAMINHO_YAML = os.path.join(RAIZ, "conteudo_mensal.yaml")


def _rotulos(d):
    """('Jun', 'Jul') — nomes curtos do mês de comparação e do mês fechado."""
    return d["meta"]["mes_anterior_nome"], d["meta"]["mes_nome"]


def _var_simples(atual, anterior):
    return ((atual / anterior) - 1) * 100 if anterior else 0.0


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

    # Gasto separado por tipo de dia. A média sai sobre o gasto que realmente
    # ocorreu em cada tipo, não sobre o total do mês dividido pelos dias úteis.
    dias = [
        ("GASTO EM DIAS ÚTEIS",
         f"{atual['Dias úteis']} dias úteis em {d['meta']['mes_extenso']}"
         f"  ·  {anterior['Dias úteis']} em {d['meta']['mes_anterior_extenso']}",
         moeda(atual["Gasto em dias úteis"]),
         f"média {moeda(atual['Média por dia útil'])}/dia"
         f"   ·   {rot_ant}: {moeda(anterior['Média por dia útil'])}/dia",
         _var_simples(atual["Média por dia útil"], anterior["Média por dia útil"])),
        ("GASTO EM FINS DE SEMANA E FERIADOS",
         f"{atual['Dias não úteis']} dias em {d['meta']['mes_extenso']}"
         f"  ·  {anterior['Dias não úteis']} em {d['meta']['mes_anterior_extenso']}",
         moeda(atual["Gasto em fins de semana"]),
         f"média {moeda(atual['Média por fim de semana'])}/dia"
         f"   ·   {rot_ant}: {moeda(anterior['Média por fim de semana'])}/dia",
         _var_simples(atual["Média por fim de semana"], anterior["Média por fim de semana"])),
    ]
    largura_dia = (LARGURA_UTIL - 10) / 2
    for i, (rotulo, dias_txt, valor, media, delta) in enumerate(dias):
        x = MARGEM + i * (largura_dia + 10)
        caixa(c, x, 246, largura_dia, 84, C_FUNDO, C_BORDA)
        texto(c, x + 14, 263, rotulo, 8, C_MARROM, negrito=True)
        texto(c, x + 14, 277, dias_txt, 7.5, C_SUAVE)
        texto(c, x + 14, 302, valor, 16, C_TEXTO, negrito=True)
        texto(c, x + 14, 320, media, 7.5, C_SUAVE)
        variacao(c, x + largura_dia - 66, 302, delta, tamanho=9.5)

    secao(c, 350, interpolar(pagina.get("titulo_grafico"), ctx))

    fig, ax = nova_figura(525, 270)
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
    grafico(c, fig, MARGEM, 386, 525, 270)


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
        ax.text(i, valor + amplitude * 0.13, valor_km(valor), ha="center",
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

    fig, ax = nova_figura(525, 235)
    categorias = ["Combustível\npor km", "Manutenção\npor km", "Total\noperacional/km"]
    chaves = ["Custo/km combustível", "Custo/km manutenção", "Custo/km total"]
    valores_ant = [anterior[k] for k in chaves]
    valores_atual = [atual[k] for k in chaves]
    posicoes = np.arange(len(categorias))

    ax.bar(posicoes - 0.2, valores_ant, 0.38, color=ROSA, label=rot_ant)
    ax.bar(posicoes + 0.2, valores_atual, 0.38, color=MARROM, label=rot_atual)

    teto = max(valores_ant + valores_atual) * 1.35
    for i, (v1, v2) in enumerate(zip(valores_ant, valores_atual)):
        ax.text(i - 0.2, v1 + teto * 0.02, valor_km(v1), ha="center", fontsize=8,
                color=TEXTO_SUAVE)
        ax.text(i + 0.2, v2 + teto * 0.02, valor_km(v2), ha="center", fontsize=8,
                fontweight="bold", color=TEXTO)
        delta = (v2 / v1 - 1) * 100 if v1 else 0
        ax.text(i + 0.2, v2 + teto * 0.10, f"({pct_sinal(delta)})", ha="center", fontsize=8,
                fontweight="bold", color=VERDE if delta < 0 else VERMELHO)

    ax.set_xticks(posicoes)
    ax.set_xticklabels(categorias, fontsize=8.5)
    ax.set_ylim(0, teto)
    ax.set_ylabel("R$/km", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 110, 525, 235)

    secao(c, 358, interpolar(pagina.get("subtitulo"), ctx))

    indicadores = [
        ("KM RODADO", f"{rot_ant}: {km_curto(anterior['KM rodado total'])} km",
         f"{rot_atual}: {km_curto(atual['KM rodado total'])} km", False),
        ("LITROS CONSUMIDOS", f"{rot_ant}: {milhares(anterior['Litros consumidos'])} L",
         f"{rot_atual}: {milhares(atual['Litros consumidos'])} L", False),
        ("PREÇO MÉDIO DIESEL S10", f"{rot_ant}: {valor_litro(anterior['Preço médio diesel S10'])}",
         f"{rot_atual}: {valor_litro(atual['Preço médio diesel S10'])}", True),
        ("CONSUMO MÉDIO FROTA", f"{rot_ant}: {numero_br(anterior['Consumo médio (km/L)'])} km/L",
         f"{rot_atual}: {numero_br(atual['Consumo médio (km/L)'])} km/L", False),
    ]
    largura_cartao = (LARGURA_UTIL - 3 * 10) / 4
    for i, (rotulo, linha_ant, linha_atual, destaque) in enumerate(indicadores):
        x = MARGEM + i * (largura_cartao + 10)
        caixa(c, x, 392, largura_cartao, 74, C_FUNDO, C_BORDA)
        texto(c, x + 12, 409, rotulo, 7.5, C_SUAVE)
        texto(c, x + 12, 425, linha_ant, 8, C_SUAVE)
        texto(c, x + 12, 452, linha_atual, 13,
              C_VERMELHO if destaque else C_TEXTO, negrito=True)

    secao(c, 496, interpolar(pagina.get("titulo_diesel"), ctx))

    fig, ax = nova_figura(500, 175)
    meses = d["meta"]["meses"]
    precos = [d["mensal"][m]["Preço médio diesel S10"] for m in meses]
    amplitude = max(max(precos) - min(precos), 0.01)

    ax.plot(meses, precos, color=MARROM, linewidth=2, marker="o", markersize=5, zorder=3)
    ax.fill_between(range(len(meses)), precos, min(precos) * 0.97, color=MARROM, alpha=0.10)
    for i, preco in enumerate(precos):
        ax.text(i, preco + amplitude * 0.13, valor_litro(preco), ha="center",
                fontsize=7.5, fontweight="bold", color=MARROM)

    ax.set_ylim(min(precos) * 0.97, max(precos) * 1.06)
    ax.set_ylabel("R$/litro", fontsize=8)
    meses_em_negrito(ax)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 12, 526, 500, 175)

    topo = paragrafo(c, MARGEM, 720, LARGURA_UTIL,
                     interpolar(pagina.get("texto_diesel"), ctx), 8.5, C_SUAVE,
                     entrelinha=12)
    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_4(c, d, cont, ctx):
    """Manutenção: natureza e filiais."""
    pagina = cont["pagina_4_manutencao"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    natureza = d["quebras"]["manutencao_natureza"]
    atual = d["atual"]
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
        rotulos_par_de_barras(ax, i, v1, v2, teto)

    ax.set_xticks(posicoes)
    ax.set_xticklabels([k.replace(" de ", " de\n").replace(" e ", " e\n") for k in categorias],
                       fontsize=8.5)
    ax.set_ylim(0, teto)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 108, 525, 215)

    secao(c, 338, interpolar(pagina.get("titulo_filiais"), ctx))

    filiais = d["quebras"]["manutencao_top_filiais"]
    fig, ax = nova_figura(525, 215)
    nomes = list(filiais.keys())[::-1]
    valores = [v / 1000 for v in filiais.values()][::-1]

    ax.barh(nomes, valores, color=MARROM, height=0.62)
    for i, valor in enumerate(valores):
        ax.text(valor + max(valores) * 0.01, i, f" {moeda_k(valor)}", va="center",
                fontsize=7.5, color=TEXTO)
    ax.set_xlim(0, max(valores) * 1.18)
    ax.set_xlabel("R$ (milhares)", fontsize=8)
    rotulos_em_negrito(ax, 7.5)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 366, 525, 190)

    # Franquia de seguro (sinistro) dentro do total de manutenção do mês —
    # sinal mais confiável hoje pra separar sinistro de manutenção comum.
    topo = 566
    if atual.get("Manutenção sinistro", 0.0) > 0:
        topo = paragrafo(c, MARGEM, topo, LARGURA_UTIL,
                         interpolar(pagina.get("nota_sinistro"), ctx), 8.5, C_SUAVE,
                         entrelinha=11) + 10
    bloco_observacoes(c, topo, pagina, ctx)


def _pagina_4b(c, d, cont, ctx):
    """Manutenção por modelo: custo médio por veículo, modelos com frota relevante."""
    pagina = cont["pagina_4b_manutencao_modelo"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    modelos = d["quebras"].get("manutencao_modelo", [])[:12]
    topo = 108
    if modelos:
        total_custo = sum(m["custo_total"] for m in modelos)
        total_veiculos = sum(m["veiculos"] for m in modelos)
        media_geral = total_custo / total_veiculos if total_veiculos else 0.0

        fig, ax = nova_figura(525, 380)
        nomes = [f"{m['modelo']}  ({m['veiculos']} veíc.)" for m in modelos][::-1]
        valores = [m["custo_medio"] for m in modelos][::-1]
        cores = [MARROM if v >= media_geral * 1.5 else
                 (VERMELHO_MEDIO if v >= media_geral else ROSA) for v in valores]

        ax.barh(nomes, valores, color=cores, height=0.64)
        for i, valor in enumerate(valores):
            ax.text(valor + max(valores) * 0.012, i, f" {moeda_cheia(valor)}", va="center",
                    fontsize=7.5, color=TEXTO)
        ax.axvline(media_geral, color=TEXTO_SUAVE, linestyle="--", linewidth=1, zorder=0)
        ax.set_xlim(0, max(valores) * 1.24)
        ax.set_xlabel(f"R$ por veículo no período  ·  média da frota: {moeda_cheia(media_geral)}",
                      fontsize=8)
        rotulos_em_negrito(ax, 7.5)
        fig.tight_layout()
        grafico(c, fig, MARGEM, 108, 525, 380)
        topo = 500

    topo = paragrafo(c, MARGEM, topo, LARGURA_UTIL,
                     interpolar(pagina.get("texto_analise"), ctx), 9, C_SUAVE, entrelinha=12)
    bloco_observacoes(c, topo + 10, pagina, ctx)


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
        rotulos_par_de_barras(ax, i, v1, v2, teto)

    ax.set_xticks(posicoes)
    ax.set_xticklabels([k.replace(" ", "\n") for k in categorias], fontsize=8.5)
    ax.set_ylim(0, teto)
    ax.set_ylabel("R$ (milhares)", fontsize=8)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 112, 525, 250)

    # O gráfico acima cobre só o que passou pela TruckPag. Sem esta nota, a soma
    # das barras não fecha com o card de combustível da página 1.
    topo = 372
    fora = d["atual"].get("Combustível por fora", 0)
    if fora:
        topo = paragrafo(c, MARGEM, topo, LARGURA_UTIL,
                         interpolar(pagina.get("nota_fora"), ctx), 8, C_SUAVE,
                         entrelinha=11) + 12

    topo_secao = secao_opcional(c, topo, interpolar(pagina.get("subtitulo"), ctx),
                                pagina.get("topicos"))
    if topo_secao:
        topo = lista_topicos(c, topo_secao + 18, pagina.get("topicos"), ctx)
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
        ax.text(i, valor + max(valores) * 0.04, moeda_k(valor), ha="center",
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

    topo = paragrafo(c, MARGEM, 512, LARGURA_UTIL,
                     interpolar(pagina.get("texto_analise"), ctx), 9, C_SUAVE)
    bloco_observacoes(c, topo + 10, pagina, ctx)


def _pagina_6b(c, d, cont, ctx):
    """Onde o pedágio acontece: filiais que pagam e concessionárias usadas."""
    pagina = cont["pagina_6b_pedagio_detalhe"]
    secao(c, 81, interpolar(pagina.get("titulo_filiais"), ctx))

    filiais = d["quebras"].get("pedagio_filial", [])[::-1]
    if filiais:
        fig, ax = nova_figura(490, 175)
        nomes = [f["filial"] for f in filiais]
        valores = [f["valor"] for f in filiais]

        ax.barh(nomes, valores, color=MARROM, height=0.6)
        for i, valor in enumerate(valores):
            ax.text(valor + max(valores) * 0.012, i, f" {moeda_cheia(valor)}",
                    va="center", fontsize=7.5, color=TEXTO)
        ax.set_xlim(0, max(valores) * 1.26)
        ax.set_xlabel(f"R$ em {d['meta']['mes_extenso']}", fontsize=8)
        rotulos_em_negrito(ax, 7.5)
        fig.tight_layout()
        grafico(c, fig, MARGEM + 15, 112, 500, 175)

    topo = paragrafo(c, MARGEM, 305, LARGURA_UTIL,
                     interpolar(pagina.get("texto_filiais"), ctx), 8.5, C_SUAVE,
                     entrelinha=12) + 16

    secao(c, topo, interpolar(pagina.get("titulo_concessionarias"), ctx), tamanho=13)
    topo += 30

    # A UF entra na segunda linha do rótulo: mostra em que rota o gasto ocorre
    concessionarias = d["quebras"]["pedagio_concessionaria"][::-1]
    fig, ax = nova_figura(490, 215)
    nomes = [f"{x['nome']}\n{x['ufs']}" if x.get("ufs") else x["nome"]
             for x in concessionarias]
    valores_conc = [x["valor"] for x in concessionarias]

    ax.barh(nomes, valores_conc, color=AZUL, height=0.6)
    for i, x in enumerate(concessionarias):
        etiqueta = f" {moeda_cheia(x['valor'])}"
        if x.get("cidades"):
            etiqueta += f"   ·   {x['cidades']}"
        ax.text(x["valor"] + max(valores_conc) * 0.01, i, etiqueta, va="center",
                fontsize=7, color=TEXTO)
    ax.set_xlim(0, max(valores_conc) * 1.55)
    ax.set_xlabel(f"R$ em {d['meta']['mes_extenso']}", fontsize=8)
    rotulos_em_negrito(ax, 7)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 15, topo, 500, 215)
    topo += 228

    topo = paragrafo(c, MARGEM, topo, LARGURA_UTIL,
                     interpolar(pagina.get("texto_concessionarias"), ctx), 8.5,
                     C_SUAVE, entrelinha=12)
    bloco_observacoes(c, topo + 10, pagina, ctx)


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
        ax.text(valor + max(valores) * 0.008, i, f" {valor_km(valor)}", va="center",
                fontsize=7.5, color=TEXTO)

    ax.set_xlim(0, max(valores) * 1.18)
    ax.set_xlabel(f"R$/km (Combustível) em {d['meta']['mes_extenso']}", fontsize=8)
    rotulos_em_negrito(ax, 7.5)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color=MARROM, label=f"Acima de {valor_km(limite_alto, '/km')}"),
        Patch(color=VERMELHO_MEDIO, label=f"{valor_km(limite_baixo)} a {valor_km(limite_alto, '/km')}"),
        Patch(color=ROSA, label=f"Abaixo de {valor_km(limite_baixo, '/km')}"),
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
        texto(c, colunas[3][1], topo, valor_km(filial['ckm_ref']), 9, C_SUAVE)
        texto(c, colunas[4][1], topo, valor_km(filial['ckm_atual']), 9, C_TEXTO, negrito=True)
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
        valor_km(anterior['Custo/km combustível']),
        valor_km(atual['Custo/km combustível']),
        pct_sinal(var_total), str(sum(f["placas"] for f in filiais)),
    ]
    for (_, x), valor in zip(colunas, total):
        texto(c, x, topo, valor, 9, C_MARROM, negrito=True)

    bloco_observacoes(c, topo + 22, pagina, ctx)


def _faixa_idade(idade):
    if idade is None:
        return "—"
    if idade <= 1:
        return f"{idade} ano" if idade == 1 else "novo"
    return f"{idade} anos"


def _cor_faixa_idade(idade):
    """Mesma escala de cor usada no gráfico: quanto mais velho, mais escuro."""
    if idade is not None and idade <= 2:
        return ROSA
    if idade is not None and idade <= 4:
        return VERMELHO_MEDIO
    return MARROM


def _tabela_placas(c, d, topo, placas, corte):
    """Lista as placas em coluna única, na mesma numeração do gráfico."""
    altura_linha = 17
    x_num, x_placa, x_modelo = MARGEM, MARGEM + 22, MARGEM + 92
    x_idade, x_km = MARGEM + 300, MARGEM + 380
    x_custo = LARGURA - MARGEM

    texto(c, x_num, topo, "#", 7.5, C_SUAVE, negrito=True)
    texto(c, x_placa, topo, "PLACA", 7.5, C_SUAVE, negrito=True)
    texto(c, x_modelo, topo, "MODELO", 7.5, C_SUAVE, negrito=True)
    texto(c, x_idade, topo, "IDADE", 7.5, C_SUAVE, negrito=True)
    texto(c, x_km, topo, "HODÔMETRO", 7.5, C_SUAVE, negrito=True, alinhamento="direita")
    texto(c, x_custo, topo, "CUSTO NO MÊS", 7.5, C_SUAVE, negrito=True,
          alinhamento="direita")

    linha(c, topo + 5)

    y_linha = topo + 19
    for i, p in enumerate(placas):
        if i % 2 == 1:
            c.setFillColor(C_ZEBRA)
            c.rect(MARGEM - 4, y(y_linha + 5), LARGURA_UTIL + 8, altura_linha,
                   stroke=0, fill=1)

        # bolinha numerada, na cor da faixa de idade — é a ligação com o gráfico
        c.setFillColor(HexColor(_cor_faixa_idade(p["idade"])))
        c.circle(x_num + 5, y(y_linha) + 2.8, 6, stroke=0, fill=1)
        texto(c, x_num + 5, y_linha, str(p["posicao"]), 6.5,
              C_TEXTO if p["idade"] is not None and p["idade"] <= 2 else C_BRANCO,
              negrito=True, alinhamento="centro")

        # acima do corte de hodômetro o custo tende a subir: destaca em marrom
        acima_do_corte = p["odometro"] >= corte
        texto(c, x_placa, y_linha, p["placa"], 9, C_TEXTO, negrito=True)
        texto(c, x_modelo, y_linha, str(p.get("modelo") or "—")[:32], 8, C_SUAVE)
        texto(c, x_idade, y_linha, _faixa_idade(p["idade"]), 8, C_SUAVE)
        texto(c, x_km, y_linha, f"{p['odometro'] / 1000:.0f}K km", 8,
              C_MARROM if acima_do_corte else C_SUAVE, negrito=acima_do_corte,
              alinhamento="direita")
        texto(c, x_custo, y_linha, moeda_cheia(p["valor"]), 9, C_TEXTO,
              negrito=True, alinhamento="direita")
        y_linha += altura_linha

    return topo + 19 + len(placas) * altura_linha + 8


def _tem_justificativa(pagina):
    """True se alguma placa tem justificativa escrita — condição da página 10."""
    return any(str(v or "").strip() for v in (pagina.get("justificativas") or {}).values())


def _placas_justificadas(placas, pagina):
    """Placas do top que têm justificativa escrita no YAML, na ordem do ranking."""
    escritas = {
        str(k).strip().upper(): str(v).strip()
        for k, v in (pagina.get("justificativas") or {}).items()
        if str(v or "").strip()
    }
    return [(p, escritas[p["placa"].upper()])
            for p in placas if p["placa"].upper() in escritas]


def _justificativas_placas(c, topo, placas, pagina, ctx):
    """Explica, placa por placa, o que puxou a manutenção — texto do YAML.

    Só imprime as placas que têm justificativa escrita, na mesma ordem e com o
    mesmo número do gráfico e da tabela da página anterior.
    """
    comentadas = _placas_justificadas(placas, pagina)
    if not comentadas:
        return topo

    for p, corpo_texto in comentadas:
        cor_ponto = HexColor(_cor_faixa_idade(p["idade"]))
        c.setFillColor(cor_ponto)
        c.circle(MARGEM + 5, y(topo) + 2.6, 5.4, stroke=0, fill=1)
        texto(c, MARGEM + 5, topo, str(p["posicao"]), 6,
              C_TEXTO if p["idade"] is not None and p["idade"] <= 2 else C_BRANCO,
              negrito=True, alinhamento="centro")

        cabeca = f"{p['placa']}  ·  {moeda_cheia(p['valor'])}"
        texto(c, MARGEM + 18, topo, cabeca, 8.5, C_TEXTO, negrito=True)
        largura_cabeca = c.stringWidth(cabeca, "Helvetica-Bold", 8.5)

        corpo = interpolar(corpo_texto, ctx)
        # primeira linha na sobra ao lado do cabeçalho, o resto abaixo
        recuo = MARGEM + 18
        linhas = quebrar(c, corpo, LARGURA_UTIL - 18 - largura_cabeca - 14, "Helvetica", 8.5)
        texto(c, recuo + largura_cabeca + 10, topo, linhas[0], 8.5, C_SUAVE)
        topo += 12
        if len(linhas) > 1:
            topo = paragrafo(c, recuo, topo, LARGURA_UTIL - 18,
                             " ".join(linhas[1:]), 8.5, C_SUAVE, entrelinha=12)
        topo += 7

    return topo + 6


def _pagina_10(c, d, cont, ctx):
    """Justificativa das manutenções mais pesadas, placa por placa."""
    pagina = cont["pagina_10_justificativas_placas"]
    placas = d["quebras"]["top_placas_manutencao"]

    topo = secao(c, 81, interpolar(pagina.get("titulo"), ctx)) + 16

    intro = interpolar(pagina.get("texto_intro"), ctx)
    if intro:
        topo = paragrafo(c, MARGEM, topo + 4, LARGURA_UTIL, intro, 9, C_SUAVE,
                         entrelinha=13) + 14

    comentadas = _placas_justificadas(placas, pagina)
    topo = _justificativas_placas(c, topo, placas, pagina, ctx)

    # deixa claro que a numeração é a mesma da página anterior
    if comentadas:
        texto(c, MARGEM, topo + 8, interpolar(pagina.get("nota_numeracao"), ctx),
              7.5, C_SUAVE)
        topo += 24

    bloco_observacoes(c, topo, pagina, ctx)


def _tabela_recorrentes(c, topo, placas):
    """Lista as placas recorrentes, uma por linha."""
    altura_linha = 18
    x_placa, x_modelo = MARGEM, MARGEM + 90
    x_meses, x_posicao = MARGEM + 320, MARGEM + 410
    x_custo = LARGURA - MARGEM

    texto(c, x_placa, topo, "PLACA", 7.5, C_SUAVE, negrito=True)
    texto(c, x_modelo, topo, "MODELO", 7.5, C_SUAVE, negrito=True)
    texto(c, x_meses, topo, "MESES NO TOP 10", 7.5, C_SUAVE, negrito=True, alinhamento="direita")
    texto(c, x_posicao, topo, "MELHOR POSIÇÃO", 7.5, C_SUAVE, negrito=True, alinhamento="direita")
    texto(c, x_custo, topo, "CUSTO NOS MESES", 7.5, C_SUAVE, negrito=True, alinhamento="direita")
    linha(c, topo + 5)

    y_linha = topo + 20
    for i, p in enumerate(placas):
        if i % 2 == 1:
            c.setFillColor(C_ZEBRA)
            c.rect(MARGEM - 4, y(y_linha + 5), LARGURA_UTIL + 8, altura_linha, stroke=0, fill=1)

        texto(c, x_placa, y_linha, p["placa"], 9, C_TEXTO, negrito=True)
        texto(c, x_modelo, y_linha, str(p.get("modelo") or "—")[:26], 8, C_SUAVE)
        texto(c, x_meses, y_linha, str(p["meses_no_top"]), 9, C_MARROM, negrito=True,
              alinhamento="direita")
        texto(c, x_posicao, y_linha, f"{p['melhor_posicao']}º", 8.5, C_SUAVE,
              alinhamento="direita")
        texto(c, x_custo, y_linha, moeda_cheia(p["custo_nos_meses_top"]), 9, C_TEXTO,
              negrito=True, alinhamento="direita")
        y_linha += altura_linha

    return y_linha + 8


def _pagina_10b(c, d, cont, ctx):
    """Placas que se repetem no top 10 de manutenção ao longo do período."""
    pagina = cont["pagina_10b_placas_recorrentes"]
    topo = secao(c, 81, interpolar(pagina.get("titulo"), ctx)) + 16

    intro = interpolar(pagina.get("texto_intro"), ctx)
    if intro:
        topo = paragrafo(c, MARGEM, topo + 4, LARGURA_UTIL, intro, 9, C_SUAVE,
                         entrelinha=13) + 14

    placas = d["quebras"].get("manutencao_recorrentes", [])
    topo = _tabela_recorrentes(c, topo, placas)

    bloco_observacoes(c, topo + 6, pagina, ctx)


def _pagina_9(c, d, cont, ctx):
    """Hodômetro vs custo de manutenção no mês."""
    pagina = cont["pagina_9_hodometro_manutencao"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    placas = d["quebras"]["top_placas_manutencao"]
    corte = pagina.get("corte_hodometro", 200_000)

    # O gráfico mostra só o padrão (custo x km x idade). Identificar cada ponto
    # exigia 20 rótulos numa faixa estreita, que se sobrepunham — quem é quem
    # está na tabela logo abaixo.
    fig, ax = nova_figura(520, 235)
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
                       color=cor, s=150, label=rotulo, zorder=3,
                       edgecolors="white", linewidths=0.9)

    # O número dentro do ponto é a chave para a tabela: quem olha o gráfico
    # acha a placa, o modelo e o valor exato logo abaixo.
    for p in placas:
        ax.text(p["odometro"] / 1000, p["valor"] / 1000, str(p["posicao"]),
                ha="center", va="center", fontsize=5.5, fontweight="bold",
                color=TEXTO if (p["idade"] is not None and p["idade"] <= 2) else BRANCO,
                zorder=4)

    ax.margins(x=0.06, y=0.18)
    ax.axvline(corte / 1000, color="#888888", linestyle="--", linewidth=1, zorder=1)
    limite_x = ax.get_xlim()
    ax.axvspan(corte / 1000, limite_x[1], color=MARROM, alpha=0.045, zorder=0)
    ax.set_xlim(limite_x)
    ax.text(corte / 1000, ax.get_ylim()[1], f"{corte // 1000} mil km", ha="center",
            va="bottom", fontsize=7.5, fontweight="bold", color=TEXTO_SUAVE)

    ax.set_xlabel("Hodômetro (milhares de km)", fontsize=8)
    ax.set_ylabel(f"Custo de manutenção (R$ mil)", fontsize=8)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    ax.grid(axis="y", color="#EEEEEE", linewidth=0.8, zorder=0)
    fig.tight_layout()
    grafico(c, fig, MARGEM + 5, 108, 520, 235)

    # --- tabela das placas, em duas colunas para caber na página ---
    # As justificativas por placa ficam na página seguinte: com a lista cheia
    # elas não caberiam aqui junto do gráfico, da tabela e dos indicadores.
    topo_tabela = _tabela_placas(c, d, 356, placas, corte)

    analise = interpolar(pagina.get("texto_analise"), ctx)
    if analise:
        linhas_texto = quebrar(c, analise, LARGURA_UTIL - 40, "Helvetica", 8.5)
        altura_caixa = 20 + len(linhas_texto) * 13
        caixa(c, MARGEM, topo_tabela, LARGURA_UTIL, altura_caixa, C_FUNDO)
        paragrafo(c, MARGEM + 20, topo_tabela + 16, LARGURA_UTIL - 40, analise, 8.5,
                  C_TEXTO, entrelinha=13)
        topo_tabela += altura_caixa + 14

    topo_cartoes = topo_tabela + 12
    linha(c, topo_cartoes - 14)

    # Manutenção geral do mês. O detalhamento por natureza fica na página 4, em
    # reais: por km cada natureza vira centavo e a leitura não ajuda ninguém.
    anterior, atual, var = d["anterior"], d["atual"], d["variacao"]
    rot_ant = d["meta"]["mes_anterior_nome"]

    soma_top = sum(p["valor"] for p in placas)
    peso_top = soma_top / atual["Manutenção total"] * 100 if atual["Manutenção total"] else 0

    cartoes = [
        ("MANUTENÇÃO POR KM", f"{rot_ant}: {valor_km(anterior['Custo/km manutenção'], '/km')}",
         valor_km(atual["Custo/km manutenção"], "/km"), var["Custo/km manutenção"]),
        ("MANUTENÇÃO NO MÊS", f"{rot_ant}: {moeda(anterior['Manutenção total'])}",
         moeda(atual["Manutenção total"]), var["Manutenção total"]),
        (f"CONCENTRAÇÃO NO TOP {len(placas)}", f"{numero_br(peso_top, 1)}% da manutenção do mês",
         moeda(soma_top), None),
    ]
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, (rotulo, comparacao, valor, delta) in enumerate(cartoes):
        x = MARGEM + i * (largura_cartao + 12)
        caixa(c, x, topo_cartoes, largura_cartao, 88, C_FUNDO, C_BORDA)
        texto(c, x + 16, topo_cartoes + 18, rotulo, 8, C_SUAVE)
        texto(c, x + 16, topo_cartoes + 34, comparacao, 8.5, C_SUAVE)
        texto(c, x + 16, topo_cartoes + 60, valor, 17, C_TEXTO, negrito=True)
        if delta is not None:
            variacao(c, x + 16, topo_cartoes + 78, delta, sufixo=f" vs {rot_ant}", tamanho=9.5)

    bloco_observacoes(c, topo_cartoes + 108, pagina, ctx)


def _pagina_11(c, d, cont, ctx):
    """Acumulado do ano: tabela mês a mês + fechamento."""
    pagina = cont["pagina_11_acumulado"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    meses = d["meta"]["meses"]
    # A unidade fica numa coluna própria: "(R$K)" e "(M)" no meio do nome
    # obrigavam o leitor a decodificar três escalas diferentes na mesma tabela.
    linhas_tabela = [
        ("Manutenção", "R$ mil",
         lambda m: numero_br(d["mensal"][m]["Manutenção total"] / 1000), False),
        ("Combustível", "R$ mil",
         lambda m: numero_br(d["mensal"][m]["Combustível total"] / 1000), False),
        ("Pedágio", "R$ mil",
         lambda m: numero_br(d["mensal"][m]["Pedágio total"] / 1000), False),
        ("KM rodado", "milhões",
         lambda m: numero_br(d["mensal"][m]["KM rodado total"] / 1e6), False),
        ("Custo por km", "R$",
         lambda m: numero_br(d["mensal"][m]["Custo/km total"]), True),
    ]

    topo = 128
    altura_cabecalho = 26
    largura_rotulo = 105
    largura_unidade = 48
    inicio_meses = MARGEM + largura_rotulo + largura_unidade
    largura_coluna = (LARGURA - MARGEM - inicio_meses) / len(meses)

    c.setFillColor(C_MARROM)
    c.rect(MARGEM, y(topo + altura_cabecalho), LARGURA_UTIL, altura_cabecalho, stroke=0, fill=1)
    texto(c, MARGEM + 12, topo + 17.5, "INDICADOR", 9, C_BRANCO, negrito=True)
    texto(c, MARGEM + largura_rotulo + 4, topo + 17.5, "UNIDADE", 7.5,
          HexColor("#D9BFC1"), negrito=True)
    for i, mes in enumerate(meses):
        direita = inicio_meses + (i + 1) * largura_coluna - 6
        texto(c, direita, topo + 17.5, mes.upper(), 8.5, C_BRANCO, negrito=True,
              alinhamento="direita")

    topo += altura_cabecalho
    altura_linha = 24.5
    for i, (rotulo, unidade, formatar, destaque) in enumerate(linhas_tabela):
        if destaque:
            c.setFillColor(HexColor("#F7F2F2"))
            c.rect(MARGEM, y(topo + altura_linha), LARGURA_UTIL, altura_linha, stroke=0, fill=1)
        elif i % 2 == 1:
            c.setFillColor(C_ZEBRA)
            c.rect(MARGEM, y(topo + altura_linha), LARGURA_UTIL, altura_linha, stroke=0, fill=1)

        cor = C_MARROM if destaque else C_TEXTO
        texto(c, MARGEM + 12, topo + 16.5, rotulo, 9.5, cor, negrito=destaque)
        texto(c, MARGEM + largura_rotulo + 4, topo + 16.5, unidade, 7.5, C_SUAVE)
        # números à direita: alinha a casa decimal e deixa comparar mês a mês
        for j, mes in enumerate(meses):
            direita = inicio_meses + (j + 1) * largura_coluna - 6
            texto(c, direita, topo + 16.5, formatar(mes), 8.5, cor, negrito=destaque,
                  alinhamento="direita")
        topo += altura_linha
        linha(c, topo, espessura=0.6)

    topo += 30
    acumulado, media = d["acumulado"], d["media_mensal"]
    cartoes = [
        ("ACUMULADO DO ANO", moeda(acumulado["Total operacional"]),
         f"{km_curto(acumulado['KM rodado total'])} km rodados",
         valor_km(acumulado['Custo/km total'], '/km')),
        ("MÉDIA MENSAL", moeda(media["Total operacional"]),
         f"{km_curto(media['KM rodado total'])} km por mês",
         f"{len(meses)} meses fechados"),
        (d["meta"]["mes_extenso"].upper(), moeda(d["atual"]["Total operacional"]),
         f"{km_curto(d['atual']['KM rodado total'])} km rodados",
         valor_km(d['atual']['Custo/km total'], '/km')),
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
    analise = interpolar(pagina.get("texto_analise"), ctx)
    if analise:
        texto(c, MARGEM, topo, interpolar(pagina.get("titulo_analise"), ctx), 11, C_TEXTO,
              negrito=True)
        topo = paragrafo(c, MARGEM, topo + 26, LARGURA_UTIL, analise, 9.5, C_TEXTO,
                         entrelinha=15.5)
    bloco_observacoes(c, topo + 12, pagina, ctx)


def _pagina_12(c, d, cont, ctx):
    """Centralização do abastecimento: quanto ainda é comprado fora da TruckPag."""
    pagina = cont["pagina_12_centralizacao_truckpag"]
    secao(c, 81, interpolar(pagina.get("titulo"), ctx))

    meses = d["meta"]["meses"]
    fora = [d["mensal"][m]["Combustível por fora"] / 1000 for m in meses]
    pct_centralizado = [
        (d["mensal"][m]["Combustível TruckPag"] / d["mensal"][m]["Combustível total"] * 100)
        if d["mensal"][m]["Combustível total"] > 0 else 0
        for m in meses
    ]

    # O % centralizado entra como segunda linha do rótulo do mês. Numa faixa
    # estreita (95%-98%) uma linha em eixo próprio colidia com os rótulos das
    # barras e não acrescentava leitura.
    rotulos = [f"{m}\n{numero_br(p, 1)}%" for m, p in zip(meses, pct_centralizado)]

    fig, ax = nova_figura(525, 148)
    ax.bar(rotulos, fora, color=_cores_meses(meses), width=0.6)
    for i, valor in enumerate(fora):
        ax.text(i, valor + max(fora) * 0.04, moeda(valor * 1000), ha="center",
                fontsize=7.5, fontweight="bold", color=TEXTO)
    ax.set_ylim(0, max(fora) * 1.22)
    ax.set_ylabel("Compra fora da TruckPag (R$ mil)", fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
    for etiqueta in ax.get_xticklabels():
        etiqueta.set_color(TEXTO)
    ax.grid(axis="y", color="#EEEEEE", linewidth=0.8, zorder=0)
    fig.tight_layout()
    grafico(c, fig, MARGEM, 104, 525, 148)
    texto(c, MARGEM + 12, 268, "O percentual abaixo de cada mês é a parcela do "
          "combustível que passou pela TruckPag.", 7.5, C_SUAVE)

    atual = d["atual"]
    acumulado = d["acumulado"]
    pct_mes = (atual["Combustível TruckPag"] / atual["Combustível total"] * 100
               if atual["Combustível total"] > 0 else 0)

    # Parte do que o financeiro lança como "combustível" é Arla: o terceiro card
    # abre essa divisão para não ler o valor inteiro como diesel comprado fora.
    natureza = d["quebras"].get("combustivel_fora", {}).get("natureza", {})
    arla = natureza.get("Arla", 0.0)
    combustivel_puro = natureza.get("Combustível", 0.0)
    base_natureza = arla + combustivel_puro

    cartoes = [
        ("CENTRALIZADO NA TRUCKPAG", f"{numero_br(pct_mes, 1)}%",
         f"do combustível de {d['meta']['mes_extenso']}"),
        (f"COMPRADO FORA EM {d['meta']['mes_nome'].upper()}", moeda(atual["Combustível por fora"]),
         f"de {moeda(atual['Combustível total'])} no mês"),
        ("DESTE VALOR, É ARLA",
         f"{numero_br(arla / base_natureza * 100, 1)}%" if base_natureza else "—",
         f"{moeda(arla)} de {moeda(base_natureza)} no mês"),
    ]
    largura_cartao = (LARGURA_UTIL - 2 * 12) / 3
    for i, (rotulo, valor, detalhe) in enumerate(cartoes):
        x = MARGEM + i * (largura_cartao + 12)
        caixa(c, x, 284, largura_cartao, 74, C_FUNDO, C_BORDA)
        texto(c, x + 14, 300, rotulo, 7.5, C_SUAVE)
        texto(c, x + 14, 327, valor, 17, C_TEXTO, negrito=True)
        texto(c, x + 14, 344, detalhe, 8, C_SUAVE)

    topo = 378
    filiais = d["quebras"].get("combustivel_fora", {}).get("filiais", [])
    if filiais:
        secao(c, topo, interpolar(pagina.get("titulo_filiais"), ctx), tamanho=11)
        topo += 26

        x_fora, x_tp, x_pct = MARGEM + 250, MARGEM + 380, MARGEM + 500
        texto(c, MARGEM + 12, topo, "FILIAL", 7.5, C_SUAVE, negrito=True)
        texto(c, x_fora, topo, "COMPRA DIRETA", 7.5, C_SUAVE, negrito=True,
              alinhamento="direita")
        texto(c, x_tp, topo, "VIA TRUCKPAG", 7.5, C_SUAVE, negrito=True,
              alinhamento="direita")
        texto(c, x_pct, topo, "% FORA NA FILIAL", 7.5, C_SUAVE, negrito=True,
              alinhamento="direita")
        topo += 6
        linha(c, topo)
        topo += 14

        # notas por filial escritas no YAML, marcadas com asterisco na tabela
        notas = {str(k).strip().upper(): str(v).strip()
                 for k, v in (pagina.get("notas_filiais") or {}).items()
                 if str(v or "").strip()}
        marcadas = []

        for i, f in enumerate(filiais[:5]):
            if i % 2 == 1:
                c.setFillColor(C_ZEBRA)
                c.rect(MARGEM, y(topo + 4.5), LARGURA_UTIL, 16, stroke=0, fill=1)

            operacional = f.get("operacional", True)
            nota = notas.get(f["filial"].upper())
            rotulo_filial = f["filial"][:40] + (" *" if nota else "")
            if nota:
                marcadas.append((f["filial"], nota))
            texto(c, MARGEM + 12, topo, rotulo_filial, 8.5,
                  C_TEXTO if operacional else C_SUAVE)
            texto(c, x_fora, topo, moeda_cheia(f["fora"]), 8.5, C_TEXTO,
                  negrito=True, alinhamento="direita")
            # rateio e centro sem equivalência não têm filial para comparar
            texto(c, x_tp, topo, moeda_cheia(f["truckpag"]) if operacional else "—",
                  8.5, C_SUAVE, alinhamento="direita")
            texto(c, x_pct, topo,
                  f"{numero_br(f['pct_fora'], 1)}%" if f.get("pct_fora") is not None else "—",
                  8.5, C_MARROM, negrito=True, alinhamento="direita")
            topo += 16
        topo += 6

        for filial_nota, nota in marcadas:
            topo = paragrafo(c, MARGEM + 12, topo, LARGURA_UTIL - 24,
                             f"*  {filial_nota}: {interpolar(nota, ctx)}", 7.5,
                             C_SUAVE, entrelinha=10) + 4
        topo += 8

    topo_secao = secao_opcional(c, topo, interpolar(pagina.get("subtitulo"), ctx),
                                pagina.get("topicos"), tamanho=11)
    if topo_secao:
        topo = lista_topicos(c, topo_secao + 12, pagina.get("topicos"), ctx,
                             tamanho_titulo=8.5, tamanho_texto=8, espaco=6)
    bloco_observacoes(c, topo + 6, pagina, ctx)


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
            f"{nome}_manutencao_k": moeda_milhar(bloco['Manutenção total']),
            f"{nome}_km": km_curto(bloco["KM rodado total"]),
            f"{nome}_litros": milhares(bloco["Litros consumidos"]),
            f"{nome}_ckm": valor_km(bloco['Custo/km total']),
            f"{nome}_ckm_combustivel": valor_km(bloco['Custo/km combustível']),
            f"{nome}_ckm_manutencao": valor_km(bloco['Custo/km manutenção']),
            f"{nome}_diesel": moeda_cheia(bloco['Preço médio diesel S10']),
            f"{nome}_consumo": numero_br(bloco['Consumo médio (km/L)']),
            f"{nome}_passagens": inteiro(bloco["Número de passagens pedágio"]),
            f"{nome}_combustivel_truckpag": moeda(bloco.get("Combustível TruckPag", 0)),
            f"{nome}_combustivel_fora": moeda(bloco.get("Combustível por fora", 0)),
            f"{nome}_pct_centralizado": numero_br(
                bloco.get("Combustível TruckPag", 0) / bloco["Combustível total"] * 100, 1
            ) + "%" if bloco["Combustível total"] else "—",
            f"{nome}_pct_fora": numero_br(
                bloco.get("Combustível por fora", 0) / bloco["Combustível total"] * 100, 1
            ) + "%" if bloco["Combustível total"] else "—",
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

    # Dias úteis e o gasto separado por tipo de dia
    for nome, bloco in [("ant", anterior), ("mes", atual)]:
        ctx[f"{nome}_dias_uteis"] = str(bloco.get("Dias úteis", "—"))
        ctx[f"{nome}_dias_fds"] = str(bloco.get("Dias não úteis", "—"))
        ctx[f"{nome}_gasto_util"] = moeda(bloco.get("Gasto em dias úteis", 0))
        ctx[f"{nome}_gasto_fds"] = moeda(bloco.get("Gasto em fins de semana", 0))
        ctx[f"{nome}_media_dia_util"] = moeda(bloco.get("Média por dia útil", 0))
        ctx[f"{nome}_media_fds"] = moeda(bloco.get("Média por fim de semana", 0))
        ctx[f"{nome}_km_dia_util"] = km_curto(bloco.get("KM por dia útil", 0))

    delta_dias = atual.get("Dias úteis", 0) - anterior.get("Dias úteis", 0)
    ctx["delta_dias_uteis"] = f"{delta_dias:+d}"
    for chave, campo in [("media_dia_util", "Média por dia útil"),
                         ("media_fds", "Média por fim de semana")]:
        var_dia = _var_simples(atual.get(campo, 0), anterior.get(campo, 0))
        ctx[f"var_{chave}"] = pct(var_dia)
        ctx[f"var_{chave}_sinal"] = pct_sinal(var_dia)

    # Arla dentro do que o financeiro lança como combustível comprado fora
    natureza = d["quebras"].get("combustivel_fora", {}).get("natureza", {})
    arla = natureza.get("Arla", 0.0)
    base = arla + natureza.get("Combustível", 0.0)
    ctx["mes_arla"] = moeda(arla)
    ctx["mes_arla_pct"] = f"{numero_br(arla / base * 100, 1)}%" if base else "—"

    # Sinistro (franquia de seguro) dentro da manutenção do mês
    ctx["mes_sinistro"] = moeda(atual.get("Manutenção sinistro", 0.0))
    ctx["mes_sinistro_pct"] = f"{numero_br(atual.get('Manutenção sinistro %', 0.0), 1)}%"

    # acompanha TOP_PLACAS_MANUTENCAO: o título não fica preso a um número fixo
    ctx["top_placas"] = str(len(d["quebras"].get("top_placas_manutencao", [])))

    ctx["delta_pedagio"] = moeda(atual["Pedágio total"] - anterior["Pedágio total"])
    ctx["delta_passagens"] = inteiro(atual["Número de passagens pedágio"]
                                     - anterior["Número de passagens pedágio"])

    concessionarias = [x["nome"] for x in d["quebras"]["pedagio_concessionaria"]]
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
    (_pagina_4b, "pagina_4b_manutencao_modelo",
     lambda p, d: bool(d["quebras"].get("manutencao_modelo"))),
    (_pagina_5, "pagina_5_combustivel"),
    (_pagina_6, "pagina_6_pedagio"),
    (_pagina_6b, "pagina_6b_pedagio_detalhe"),
    (_pagina_7, "pagina_7_custo_km_filial"),
    (_pagina_8, "pagina_8_detalhamento_filial"),
    (_pagina_9, "pagina_9_hodometro_manutencao"),
    (_pagina_10, "pagina_10_justificativas_placas", lambda p, d: _tem_justificativa(p)),
    (_pagina_10b, "pagina_10b_placas_recorrentes",
     lambda p, d: bool(d["quebras"].get("manutencao_recorrentes"))),
    (_pagina_11, "pagina_11_acumulado"),
    (_pagina_12, "pagina_12_centralizacao_truckpag"),
    # Páginas puramente editoriais só entram quando o YAML tem conteúdo:
    # enquanto estiverem em branco, somem do PDF em vez de sair uma folha vazia.
    (_pagina_13, "pagina_13_proximos_passos", lambda p, d: preenchido(p.get("itens"))),
    (_pagina_14, "pagina_14_observacoes_gerais", lambda p, d: tem_blocos(p)),
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
