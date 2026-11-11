"""
Identidade visual dos gráficos.

Centralizar a paleta aqui garante que todos os gráficos leiam como um sistema
só, e que a troca de uma cor aconteça em um lugar apenas.

A paleta foi validada para daltonismo (protanopia, deuteranopia, tritanopia)
antes de ser adotada. Verde e vermelho — a convenção universal para dinheiro
que entra e que sai — ficam na faixa limítrofe de separação sob protanopia
(ΔE 7.2), então **sempre** acompanham codificação secundária: legenda,
rótulo direto e posição fixa. Nunca dependem só da cor.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# --- Superfícies e tinta ---------------------------------------------------- #
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"

# --- Cores das séries ------------------------------------------------------- #
INCOME = "#008300"   # receitas
EXPENSE = "#e34948"  # despesas
NEUTRAL = "#2a78d6"  # série única (fluxo de caixa)

# Ordem categórica fixa. As cores seguem a identidade da categoria, nunca a
# sua posição no ranking — filtrar o gráfico não pode repintar quem sobrou.
CATEGORICAL = [
    "#2a78d6",  # azul
    "#008300",  # verde
    "#e87ba4",  # magenta
    "#eda100",  # amarelo
    "#1baf7a",  # água
    "#eb6834",  # laranja
    "#4a3aa7",  # violeta
    "#e34948",  # vermelho
]

FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# Além deste limite as fatias adjacentes de uma pizza deixam de ser
# distinguíveis; o excedente vira "Outras".
MAX_PIE_SLICES = 6


def register_template() -> None:
    """Registra o template padrão do Plotly e o define como ativo."""
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT_FAMILY, size=12, color=TEXT_SECONDARY),
        title=dict(
            font=dict(size=15, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
            pad=dict(l=8, t=8),
        ),
        margin=dict(l=48, r=24, t=56, b=48),
        colorway=CATEGORICAL,
        xaxis=dict(
            showgrid=False,
            linecolor=AXIS_LINE,
            linewidth=1,
            ticks="outside",
            tickcolor=AXIS_LINE,
            tickfont=dict(color=TEXT_MUTED, size=11),
        ),
        yaxis=dict(
            # Hairline sólido — tracejado adiciona ruído e sugere "projeção".
            showgrid=True,
            gridcolor=GRIDLINE,
            gridwidth=1,
            zeroline=True,
            zerolinecolor=AXIS_LINE,
            zerolinewidth=1,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=TEXT_MUTED, size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.0,
            xanchor="right",
            x=1,
            font=dict(color=TEXT_SECONDARY, size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor=SURFACE,
            bordercolor=AXIS_LINE,
            font=dict(family=FONT_FAMILY, size=12, color=TEXT_PRIMARY),
        ),
    )

    pio.templates["moneyflow"] = template
    pio.templates.default = "moneyflow"


def format_brl(value: float) -> str:
    """
    Formata um valor em reais no padrão brasileiro (R$ 1.234,56).

    O Python formata com vírgula de milhar e ponto decimal; a troca abaixo
    inverte os dois separadores.
    """
    formatted = f"{abs(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    sign = "-" if value < 0 else ""
    return f"{sign}R$ {formatted}"


def empty_figure(message: str = "Sem dados para exibir") -> go.Figure:
    """
    Figura de estado vazio.

    Um gráfico em branco deixa o usuário sem saber se está carregando, se
    quebrou ou se realmente não há dados — a mensagem responde isso.
    """
    figure = go.Figure()
    figure.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=13, color=TEXT_MUTED),
            )
        ],
    )
    return figure
