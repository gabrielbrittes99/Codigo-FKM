"""
Identidade visual e primitivas de desenho dos relatórios da Torre de Controle.

Concentra cores, formatação de números, blocos de página (cabeçalho, rodapé,
cards, listas, caixa de observações) e a configuração dos gráficos, para que o
relatório semestral (`gerar_pdf_torre.py`) e o mensal (`gerar_pdf_mensal.py`)
saiam com a mesma cara.
"""

import io
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_ASSETS = os.path.join(RAIZ, "assets")

# =======================================================================
# IDENTIDADE VISUAL
# =======================================================================

MARROM = "#5A181C"          # cor institucional — período atual, títulos
ROSA = "#F4C7C8"            # período de comparação
VERMELHO_MEDIO = "#C33D45"  # faixa intermediária e indicadores de alta
AZUL = "#3D5A73"            # pedágio
VERDE = "#2E8B57"           # variação favorável
VERMELHO = "#C33D45"        # variação desfavorável
CINZA_FUNDO = "#F7F7F7"     # faixa do cabeçalho e fundo dos cards
CINZA_BORDA = "#E0E0E0"
CINZA_ZEBRA = "#FAFAFA"
TEXTO = "#2D2D2D"
TEXTO_SUAVE = "#5A6270"
BRANCO = "#FFFFFF"

C_MARROM, C_ROSA = HexColor(MARROM), HexColor(ROSA)
C_AZUL, C_VERDE, C_VERMELHO = HexColor(AZUL), HexColor(VERDE), HexColor(VERMELHO)
C_FUNDO, C_BORDA = HexColor(CINZA_FUNDO), HexColor(CINZA_BORDA)
C_ZEBRA = HexColor(CINZA_ZEBRA)
C_TEXTO, C_SUAVE, C_BRANCO = HexColor(TEXTO), HexColor(TEXTO_SUAVE), HexColor(BRANCO)

LARGURA, ALTURA = A4              # 595.28 x 841.89
MARGEM = 35
LARGURA_UTIL = LARGURA - 2 * MARGEM
ALTURA_CABECALHO = 72

plt.rcParams.update({
    # "R$ 0,65 a R$ 1,00" seria lido como fórmula entre cifrões sem isto
    "text.parse_math": False,
    "font.size": 8,
    "text.color": TEXTO,
    "axes.labelcolor": TEXTO_SUAVE,
    "axes.edgecolor": "#BBBBBB",
    "xtick.color": TEXTO_SUAVE,
    "ytick.color": TEXTO_SUAVE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "none",
    "axes.facecolor": "none",
})


# =======================================================================
# FORMATAÇÃO
# =======================================================================

def moeda(valor, casas=2):
    """R$ 1.47M / R$ 354K — escala automática, como no relatório de referência."""
    if abs(valor) >= 1_000_000:
        return f"R$ {valor / 1_000_000:.{casas}f}M"
    if abs(valor) >= 1_000:
        return f"R$ {valor / 1_000:.0f}K"
    return f"R$ {valor:.0f}"


def milhares(valor):
    return f"{valor / 1_000:.0f}K"


def km_curto(valor):
    if abs(valor) >= 1_000_000:
        return f"{valor / 1_000_000:.2f}M"
    return f"{valor / 1_000:.0f}K"


def pct(valor, casas=1):
    return f"{abs(valor):.{casas}f}%"


def pct_sinal(valor, casas=1):
    return f"{valor:+.{casas}f}%"


def inteiro(valor):
    return f"{int(round(valor)):,}"


class _DicionarioTolerante(dict):
    """Mantém intacto qualquer {placeholder} desconhecido no texto do YAML."""

    def __missing__(self, chave):
        return "{" + chave + "}"


def interpolar(texto_bruto, contexto):
    if not texto_bruto:
        return ""
    try:
        return str(texto_bruto).format_map(_DicionarioTolerante(contexto))
    except (ValueError, IndexError):
        return str(texto_bruto)


# =======================================================================
# PRIMITIVAS DE DESENHO
# =======================================================================

def y(topo):
    """Converte coordenada medida a partir do topo da página."""
    return ALTURA - topo


def texto(c, x, topo, conteudo, tamanho=9, cor=C_TEXTO, negrito=False,
          fonte=None, alinhamento="esquerda"):
    c.setFont(fonte or ("Helvetica-Bold" if negrito else "Helvetica"), tamanho)
    c.setFillColor(cor)
    posicao_y = y(topo)
    if alinhamento == "direita":
        c.drawRightString(x, posicao_y, str(conteudo))
    elif alinhamento == "centro":
        c.drawCentredString(x, posicao_y, str(conteudo))
    else:
        c.drawString(x, posicao_y, str(conteudo))


def caixa(c, x, topo, largura, altura, preenchimento=None, borda=None, raio=6):
    if preenchimento:
        c.setFillColor(preenchimento)
    if borda:
        c.setStrokeColor(borda)
        c.setLineWidth(0.8)
    c.roundRect(x, y(topo + altura), largura, altura, raio,
                stroke=1 if borda else 0, fill=1 if preenchimento else 0)


def linha(c, topo, cor=C_BORDA, espessura=0.8, x0=None, x1=None):
    c.setStrokeColor(cor)
    c.setLineWidth(espessura)
    c.line(x0 if x0 is not None else MARGEM, y(topo),
           x1 if x1 is not None else LARGURA - MARGEM, y(topo))


def secao(c, topo, titulo, tamanho=15):
    """Título de seção: barra vertical marrom + texto."""
    altura_barra = tamanho + 4
    c.setFillColor(C_MARROM)
    c.rect(MARGEM, y(topo + altura_barra), 4, altura_barra, stroke=0, fill=1)
    texto(c, MARGEM + 14, topo + tamanho - 1.1, titulo, tamanho, C_TEXTO, negrito=True)
    return topo + altura_barra


def quebrar(c, conteudo, largura, fonte="Helvetica", tamanho=9):
    """Quebra o texto em linhas que cabem em `largura`."""
    linhas, atual = [], []
    for palavra in str(conteudo).split():
        atual.append(palavra)
        if c.stringWidth(" ".join(atual), fonte, tamanho) > largura and len(atual) > 1:
            atual.pop()
            linhas.append(" ".join(atual))
            atual = [palavra]
    if atual:
        linhas.append(" ".join(atual))
    return linhas


def paragrafo(c, x, topo, largura, conteudo, tamanho=9, cor=C_TEXTO,
              entrelinha=None, negrito=False):
    fonte = "Helvetica-Bold" if negrito else "Helvetica"
    entrelinha = entrelinha or tamanho * 1.55
    linhas = quebrar(c, conteudo, largura, fonte, tamanho)
    for i, conteudo_linha in enumerate(linhas):
        texto(c, x, topo + i * entrelinha, conteudo_linha, tamanho, cor, negrito=negrito)
    return topo + len(linhas) * entrelinha


def triangulo(c, x, topo, largura, altura, para_cima, cor):
    """Desenhado como vetor: a ZapfDingbats não é embutida e sai como quadrado."""
    c.setFillColor(cor)
    base = y(topo)
    caminho = c.beginPath()
    if para_cima:
        caminho.moveTo(x, base)
        caminho.lineTo(x + largura, base)
        caminho.lineTo(x + largura / 2, base + altura)
    else:
        caminho.moveTo(x, base + altura)
        caminho.lineTo(x + largura, base + altura)
        caminho.lineTo(x + largura / 2, base)
    caminho.close()
    c.drawPath(caminho, stroke=0, fill=1)


def variacao(c, x, topo, valor, sufixo="", tamanho=11, menor_e_melhor=True, neutro=False):
    """Triângulo + percentual. Queda de custo em verde, alta em vermelho.

    `neutro=True` para indicadores sem leitura de bom/ruim (km rodado, preço
    de mercado do diesel): mostra a direção sem julgar o resultado.
    """
    subiu = valor > 0
    favoravel = (not subiu) if menor_e_melhor else subiu
    cor = C_TEXTO if neutro else (C_VERDE if favoravel else C_VERMELHO)
    largura_seta = tamanho * 0.60
    triangulo(c, x, topo - tamanho * 0.08, largura_seta, tamanho * 0.58, subiu, cor)
    texto(c, x + largura_seta + tamanho * 0.30, topo, f"{pct(valor)}{sufixo}",
          tamanho, cor, negrito=True)


def marcador(c, x, topo, tamanho=8, cor=None):
    c.setFillColor(cor or C_MARROM)
    c.circle(x + tamanho * 0.28, y(topo) + tamanho * 0.30, tamanho * 0.28, stroke=0, fill=1)


def lista_topicos(c, topo, itens, contexto, largura=None, tamanho_titulo=9.5,
                  tamanho_texto=9, espaco=11):
    """Blocos 'título em negrito + descrição', usados nas páginas editoriais."""
    largura = largura or (LARGURA_UTIL - 22)
    for item in itens or []:
        marcador(c, MARGEM + 4, topo - 0.5)
        texto(c, MARGEM + 22, topo, interpolar(item.get("titulo", ""), contexto),
              tamanho_titulo, C_TEXTO, negrito=True)
        topo += tamanho_titulo * 1.6
        topo = paragrafo(c, MARGEM + 22, topo, largura,
                         interpolar(item.get("texto", ""), contexto),
                         tamanho_texto, C_SUAVE)
        topo += espaco
    return topo


# =======================================================================
# GRÁFICOS
# =======================================================================

def grafico(c, figura, x, topo, largura, altura):
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png", dpi=200, transparent=True)
    plt.close(figura)
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), x, y(topo + altura), width=largura,
                height=altura, mask="auto")


def nova_figura(largura, altura):
    """Figura dimensionada em pontos: fontes do gráfico ficam na mesma escala da página."""
    return plt.subplots(figsize=(largura / 72, altura / 72))


def separadores(ax, posicoes):
    """Linhas tracejadas separando blocos de períodos no eixo de meses."""
    for posicao in posicoes:
        ax.axvline(posicao, color="#AAAAAA", linestyle="--", linewidth=0.8, zorder=0)


def cor_sobre(cor_barra):
    """Cor de texto legível sobre a barra: branco nos tons escuros, escuro no rosa."""
    return BRANCO if cor_barra in (MARROM, AZUL, VERMELHO_MEDIO) else TEXTO


def meses_em_negrito(ax):
    for etiqueta in ax.get_xticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)


def rotulos_em_negrito(ax, tamanho=8):
    for etiqueta in ax.get_yticklabels():
        etiqueta.set_fontweight("bold")
        etiqueta.set_color(TEXTO)
        etiqueta.set_fontsize(tamanho)


# =======================================================================
# CABEÇALHO, RODAPÉ E OBSERVAÇÕES
# =======================================================================

def cabecalho(c, cont, numero, total):
    rel = cont["relatorio"]
    c.setFillColor(C_FUNDO)
    c.rect(0, y(ALTURA_CABECALHO), LARGURA, ALTURA_CABECALHO, stroke=0, fill=1)
    linha(c, ALTURA_CABECALHO, x0=0, x1=LARGURA)

    logo = os.path.join(DIR_ASSETS, "logo_gritsch.png")
    if os.path.exists(logo):
        c.drawImage(logo, 35, y(64), width=105, height=52, mask="auto")

    texto(c, 150, 35.9, rel["titulo"], 20, C_TEXTO, negrito=True)
    texto(c, 150, 54.0, f"{rel['subtitulo']}  ·  {rel['periodo']}", 11, C_SUAVE)

    marca = os.path.join(DIR_ASSETS, "logo_g.png")
    if os.path.exists(marca):
        c.drawImage(marca, 535, y(50), width=20, height=22, mask="auto")
    texto(c, 540, 57.9, rel["empresa"], 6.5, C_SUAVE, alinhamento="centro")
    texto(c, LARGURA - MARGEM, 13.9, f"{numero}/{total}", 7, C_SUAVE, alinhamento="direita")


def rodape(c, cont):
    linha(c, 808)
    texto(c, MARGEM, 821.8, cont["relatorio"]["rodape"], 7, C_SUAVE)
    texto(c, LARGURA - MARGEM, 821.8, cont["relatorio"]["data_geracao"], 7, C_SUAVE,
          alinhamento="direita")


def bloco_observacoes(c, topo, pagina, contexto):
    """Caixa opcional 'Observações da Torre', preenchida pelo YAML."""
    itens = [i for i in (pagina.get("observacoes") or []) if i.get("titulo") or i.get("texto")]
    if not itens:
        return topo

    titulo = pagina.get("titulo_observacoes", "Observações da Torre")
    linhas_totais = 0
    for item in itens:
        linhas_totais += len(quebrar(c, interpolar(item.get("texto", ""), contexto),
                                     LARGURA_UTIL - 40, "Helvetica", 8.5))
    altura = 30 + len(itens) * 14 + linhas_totais * 12

    caixa(c, MARGEM, topo, LARGURA_UTIL, altura, C_FUNDO, C_BORDA)
    texto(c, MARGEM + 16, topo + 19, titulo, 9.5, C_MARROM, negrito=True)

    interno = topo + 38
    for item in itens:
        rotulo = interpolar(item.get("titulo", ""), contexto)
        if rotulo:
            marcador(c, MARGEM + 16, interno - 0.5, 7)
            texto(c, MARGEM + 30, interno, rotulo, 8.5, C_TEXTO, negrito=True)
            interno += 13
        corpo = interpolar(item.get("texto", ""), contexto)
        if corpo:
            interno = paragrafo(c, MARGEM + 30, interno, LARGURA_UTIL - 46, corpo, 8.5,
                                C_SUAVE, entrelinha=12)
        interno += 4

    return topo + altura + 16


def pagina_observacoes_gerais(c, cont, contexto, chave="pagina_observacoes_gerais"):
    """Página livre: observações, ações e melhorias escritas pela Torre."""
    pagina = cont.get(chave, {})
    topo = secao(c, 81, interpolar(pagina.get("titulo", "Observações da Torre"), contexto)) + 20

    for bloco in pagina.get("blocos") or []:
        itens = [i for i in (bloco.get("itens") or []) if i.get("titulo") or i.get("texto")]
        if not itens:
            continue
        texto(c, MARGEM, topo + 11, interpolar(bloco.get("titulo", ""), contexto), 11,
              C_MARROM, negrito=True)
        topo += 26
        topo = lista_topicos(c, topo, itens, contexto, espaco=10) + 10

        if topo > 760:
            break


def montar_documento(canvas_obj, conteudo, paginas, dados, contexto):
    """Desenha cabeçalho/rodapé em volta de cada página habilitada."""
    ativas = [(func, chave) for func, chave in paginas
              if conteudo.get(chave, {}).get("habilitada", False)]

    for numero, (func, _) in enumerate(ativas, start=1):
        cabecalho(canvas_obj, conteudo, numero, len(ativas))
        func(canvas_obj, dados, conteudo, contexto)
        rodape(canvas_obj, conteudo)
        canvas_obj.showPage()

    return len(ativas)
