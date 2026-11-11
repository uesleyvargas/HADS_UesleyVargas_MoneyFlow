"""
Painel principal: indicadores e gráficos.

Duas mudanças estruturais em relação à versão anterior:

* A filtragem (período + categorias) virou uma função única, ``_apply_filters``.
  Antes o mesmo bloco estava copiado em quatro callbacks, e cada cópia
  divergiu um pouco — o gráfico de pizza, por exemplo, chegou a ignorar o
  filtro de data.
* Os filtros ficam numa linha acima de todos os gráficos, e não dentro do card
  de um deles, deixando explícito que valem para o painel inteiro.
"""

from __future__ import annotations

from datetime import date, timedelta

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from moneyflow.app import app
from moneyflow.theme import (
    CATEGORICAL,
    EXPENSE,
    INCOME,
    MAX_PIE_SLICES,
    NEUTRAL,
    SURFACE,
    TEXT_MUTED,
    empty_figure,
    format_brl,
)

CARD_STYLE = {"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"}


def _stat_tile(title: str, value_id: str, icon: str, color: str) -> dbc.Card:
    """
    Indicador numérico.

    Um número isolado não precisa de gráfico — o número é a visualização.
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Small(title, className="text-muted d-block"),
                        html.H3(
                            "R$ 0,00",
                            id=value_id,
                            className="fw-bold mb-0 mt-1",
                            # Figuras proporcionais: `tabular-nums` deixa
                            # números grandes com espaçamento frouxo.
                            style={"fontSize": "clamp(1.25rem, 2.5vw, 1.75rem)"},
                        ),
                    ],
                    className="flex-grow-1",
                ),
                html.Div(
                    html.I(className=icon),
                    style={
                        "backgroundColor": color,
                        "color": "white",
                        "borderRadius": "12px",
                        "width": "48px",
                        "height": "48px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "fontSize": "20px",
                        "flexShrink": "0",
                    },
                ),
            ],
            className="d-flex align-items-center gap-3",
        ),
        style=CARD_STYLE,
        className="h-100",
    )


def _chart_card(graph_id: str, height: int = 320) -> dbc.Card:
    """
    Card contendo um gráfico.

    A altura inclui a faixa do eixo X; fixar só a área de plotagem faz os
    rótulos do eixo ficarem de fora e criarem um scroll interno no card.
    """
    return dbc.Card(
        dbc.CardBody(
            dcc.Graph(
                id=graph_id,
                style={"height": f"{height}px"},
                config={"displayModeBar": False, "responsive": True},
            ),
            className="p-2",
        ),
        style=CARD_STYLE,
        className="h-100",
    )


layout = html.Div(
    [
        # --- Indicadores --- #
        dbc.Row(
            [
                dbc.Col(
                    _stat_tile("Saldo do período", "stat-saldo", "fa-solid fa-wallet", NEUTRAL),
                    xs=12, md=4, className="mb-3",
                ),
                dbc.Col(
                    _stat_tile("Receitas", "stat-receitas", "fa-solid fa-arrow-up", INCOME),
                    xs=12, md=4, className="mb-3",
                ),
                dbc.Col(
                    _stat_tile("Despesas", "stat-despesas", "fa-solid fa-arrow-down", EXPENSE),
                    xs=12, md=4, className="mb-3",
                ),
            ]
        ),

        # --- Linha única de filtros, válida para todos os gráficos --- #
        dbc.Card(
            dbc.CardBody(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Período", className="small text-muted"),
                                html.Div(
                                    dcc.DatePickerRange(
                                        id="filtro-periodo",
                                        start_date=date.today() - timedelta(days=90),
                                        end_date=date.today(),
                                        display_format="DD/MM/YYYY",
                                        className="w-100",
                                    )
                                ),
                            ],
                            xs=12, lg=4, className="mb-2",
                        ),
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Categorias de receita", className="small text-muted"
                                ),
                                dcc.Dropdown(
                                    id="filtro-cat-receita",
                                    multi=True,
                                    placeholder="Todas",
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                            xs=12, lg=4, className="mb-2",
                        ),
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Categorias de despesa", className="small text-muted"
                                ),
                                dcc.Dropdown(
                                    id="filtro-cat-despesa",
                                    multi=True,
                                    placeholder="Todas",
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                            xs=12, lg=4, className="mb-2",
                        ),
                    ],
                    className="g-3",
                )
            ),
            style=CARD_STYLE,
            className="mb-3",
        ),

        # --- Gráficos --- #
        dbc.Row(
            dbc.Col(_chart_card("graph-fluxo", height=300), xs=12),
            className="mb-3",
        ),
        dbc.Row(
            dbc.Col(_chart_card("graph-comparativo", height=340), xs=12),
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(_chart_card("graph-pizza-receitas", height=320), xs=12, lg=6, className="mb-3"),
                dbc.Col(_chart_card("graph-pizza-despesas", height=320), xs=12, lg=6, className="mb-3"),
            ]
        ),
    ]
)


# --------------------------------------------------------------------------- #
# Lógica de filtragem — fonte única de verdade
# --------------------------------------------------------------------------- #


def _to_frame(records: list[dict] | None) -> pd.DataFrame:
    """Converte os registros do store em DataFrame, com tipos normalizados."""
    if not records:
        return pd.DataFrame(columns=["Data", "Valor", "Categoria", "Descrição"])

    frame = pd.DataFrame(records)
    frame["Data"] = pd.to_datetime(frame["Data"], errors="coerce")
    frame["Valor"] = pd.to_numeric(frame["Valor"], errors="coerce").fillna(0.0)
    return frame.dropna(subset=["Data"])


def _apply_filters(
    records: list[dict] | None,
    categories: list[str] | None,
    start_date: str | None,
    end_date: str | None,
) -> pd.DataFrame:
    """
    Aplica período e categorias.

    Lista de categorias vazia significa "todas" — e não "nenhuma". Na versão
    anterior o dropdown vazio zerava os gráficos, o que parecia um bug.
    """
    frame = _to_frame(records)
    if frame.empty:
        return frame

    if start_date:
        frame = frame[frame["Data"] >= pd.to_datetime(start_date)]
    if end_date:
        frame = frame[frame["Data"] <= pd.to_datetime(end_date)]

    if categories:
        frame = frame[frame["Categoria"].isin(categories)]

    return frame


def _category_options(records: list[dict] | None) -> list[dict[str, str]]:
    """Opções de categoria presentes nos dados carregados."""
    frame = _to_frame(records)
    if frame.empty:
        return []
    return [
        {"label": name, "value": name}
        for name in sorted(frame["Categoria"].dropna().unique())
    ]


# --------------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------------- #


@app.callback(
    Output("filtro-cat-receita", "options"),
    Output("filtro-cat-despesa", "options"),
    Input("store-receitas", "data"),
    Input("store-despesas", "data"),
)
def update_filter_options(incomes, expenses):
    """Preenche os filtros com as categorias efetivamente usadas."""
    return _category_options(incomes), _category_options(expenses)


@app.callback(
    Output("stat-receitas", "children"),
    Output("stat-despesas", "children"),
    Output("stat-saldo", "children"),
    Output("stat-saldo", "className"),
    Input("store-receitas", "data"),
    Input("store-despesas", "data"),
    Input("filtro-cat-receita", "value"),
    Input("filtro-cat-despesa", "value"),
    Input("filtro-periodo", "start_date"),
    Input("filtro-periodo", "end_date"),
)
def update_stats(incomes, expenses, cat_income, cat_expense, start_date, end_date):
    """Atualiza os três indicadores conforme os filtros ativos."""
    income_frame = _apply_filters(incomes, cat_income, start_date, end_date)
    expense_frame = _apply_filters(expenses, cat_expense, start_date, end_date)

    total_income = float(income_frame["Valor"].sum()) if not income_frame.empty else 0.0
    total_expense = float(expense_frame["Valor"].sum()) if not expense_frame.empty else 0.0
    balance = total_income - total_expense

    # Saldo negativo recebe cor de alerta — acompanhada do próprio sinal "-",
    # então a informação nunca depende só da cor.
    balance_class = "fw-bold mb-0 mt-1 " + ("text-danger" if balance < 0 else "")

    return (
        format_brl(total_income),
        format_brl(total_expense),
        format_brl(balance),
        balance_class,
    )


@app.callback(
    Output("graph-fluxo", "figure"),
    Input("store-receitas", "data"),
    Input("store-despesas", "data"),
    Input("filtro-cat-receita", "value"),
    Input("filtro-cat-despesa", "value"),
    Input("filtro-periodo", "start_date"),
    Input("filtro-periodo", "end_date"),
)
def update_cash_flow(incomes, expenses, cat_income, cat_expense, start_date, end_date):
    """Fluxo de caixa acumulado — série única, sem legenda."""
    income_frame = _apply_filters(incomes, cat_income, start_date, end_date)
    expense_frame = _apply_filters(expenses, cat_expense, start_date, end_date)

    if income_frame.empty and expense_frame.empty:
        return empty_figure("Nenhum lançamento no período selecionado")

    daily_income = income_frame.groupby("Data")["Valor"].sum() if not income_frame.empty else pd.Series(dtype=float)
    daily_expense = expense_frame.groupby("Data")["Valor"].sum() if not expense_frame.empty else pd.Series(dtype=float)

    combined = pd.DataFrame({"Receita": daily_income, "Despesa": daily_expense}).fillna(0.0)
    combined = combined.sort_index()
    combined["Acumulado"] = (combined["Receita"] - combined["Despesa"]).cumsum()

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=combined.index,
            y=combined["Acumulado"],
            mode="lines",
            name="Saldo acumulado",
            line=dict(color=NEUTRAL, width=2),
            fill="tozeroy",
            fillcolor="rgba(42, 120, 214, 0.08)",
            hovertemplate="%{x|%d/%m/%Y}<br><b>%{y:,.2f}</b><extra></extra>",
        )
    )

    # Rótulo direto no último ponto: o valor mais importante da série fica
    # legível sem depender do tooltip.
    last_value = combined["Acumulado"].iloc[-1]
    figure.add_annotation(
        x=combined.index[-1],
        y=last_value,
        text=f"<b>{format_brl(last_value)}</b>",
        showarrow=False,
        yshift=16,
        font=dict(size=12, color=NEUTRAL),
    )

    figure.update_layout(
        title="Fluxo de caixa acumulado",
        hovermode="x unified",
        showlegend=False,
    )
    return figure


@app.callback(
    Output("graph-comparativo", "figure"),
    Input("store-receitas", "data"),
    Input("store-despesas", "data"),
    Input("filtro-cat-receita", "value"),
    Input("filtro-cat-despesa", "value"),
    Input("filtro-periodo", "start_date"),
    Input("filtro-periodo", "end_date"),
)
def update_comparison(incomes, expenses, cat_income, cat_expense, start_date, end_date):
    """
    Receitas x despesas por mês.

    A agregação é mensal, não diária: com lançamentos espalhados, barras por
    dia viram uma serrilha ilegível e escondem a tendência.
    """
    income_frame = _apply_filters(incomes, cat_income, start_date, end_date)
    expense_frame = _apply_filters(expenses, cat_expense, start_date, end_date)

    if income_frame.empty and expense_frame.empty:
        return empty_figure("Nenhum lançamento no período selecionado")

    def by_month(frame: pd.DataFrame) -> pd.Series:
        if frame.empty:
            return pd.Series(dtype=float)
        return frame.groupby(frame["Data"].dt.to_period("M"))["Valor"].sum()

    monthly = pd.DataFrame(
        {"Receitas": by_month(income_frame), "Despesas": by_month(expense_frame)}
    ).fillna(0.0)
    monthly = monthly.sort_index()
    labels = [period.strftime("%b/%y") for period in monthly.index]

    figure = go.Figure()
    for name, color in (("Receitas", INCOME), ("Despesas", EXPENSE)):
        figure.add_trace(
            go.Bar(
                x=labels,
                y=monthly[name],
                name=name,
                marker=dict(
                    color=color,
                    # Cantos arredondados na ponta do dado, ancorados na base.
                    cornerradius=4,
                    # Anel da cor da superfície separa barras adjacentes sem
                    # desenhar uma borda escura ao redor delas.
                    line=dict(color=SURFACE, width=2),
                ),
                # Rótulo direto: a codificação secundária que torna o par
                # verde/vermelho seguro para daltônicos.
                text=[format_brl(v) for v in monthly[name]],
                textposition="outside",
                textfont=dict(size=10, color=TEXT_MUTED),
                cliponaxis=False,
                hovertemplate=f"<b>{name}</b><br>%{{x}}<br>%{{y:,.2f}}<extra></extra>",
            )
        )

    figure.update_layout(
        title="Receitas x Despesas por mês",
        barmode="group",
        bargap=0.28,
        bargroupgap=0.08,
        showlegend=True,
    )
    return figure


def _donut(records, categories, start_date, end_date, title: str, empty_text: str) -> go.Figure:
    """
    Monta a rosca de participação por categoria.

    Acima de ``MAX_PIE_SLICES`` fatias as cores adjacentes deixam de ser
    distinguíveis, então a cauda é agrupada em "Outras" em vez de gerar
    cores novas.
    """
    frame = _apply_filters(records, categories, start_date, end_date)
    if frame.empty:
        return empty_figure(empty_text)

    totals = frame.groupby("Categoria")["Valor"].sum().sort_values(ascending=False)

    if len(totals) > MAX_PIE_SLICES:
        head = totals.iloc[: MAX_PIE_SLICES - 1]
        others = totals.iloc[MAX_PIE_SLICES - 1 :].sum()
        totals = pd.concat([head, pd.Series({"Outras": others})])

    figure = go.Figure(
        go.Pie(
            labels=totals.index,
            values=totals.values,
            hole=0.55,
            marker=dict(
                colors=CATEGORICAL[: len(totals)],
                line=dict(color=SURFACE, width=2),
            ),
            textinfo="percent",
            textposition="inside",
            insidetextorientation="horizontal",
            hovertemplate="<b>%{label}</b><br>%{value:,.2f}<br>%{percent}<extra></extra>",
            sort=False,
        )
    )

    total = float(totals.sum())
    figure.update_layout(
        title=title,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
        margin=dict(l=16, r=16, t=56, b=16),
        annotations=[
            dict(
                text=f"<b>{format_brl(total)}</b>",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14),
            )
        ],
    )
    return figure


@app.callback(
    Output("graph-pizza-receitas", "figure"),
    Input("store-receitas", "data"),
    Input("filtro-cat-receita", "value"),
    Input("filtro-periodo", "start_date"),
    Input("filtro-periodo", "end_date"),
)
def update_income_donut(records, categories, start_date, end_date):
    return _donut(
        records, categories, start_date, end_date,
        "Receitas por categoria", "Nenhuma receita no período",
    )


@app.callback(
    Output("graph-pizza-despesas", "figure"),
    Input("store-despesas", "data"),
    Input("filtro-cat-despesa", "value"),
    Input("filtro-periodo", "start_date"),
    Input("filtro-periodo", "end_date"),
)
def update_expense_donut(records, categories, start_date, end_date):
    return _donut(
        records, categories, start_date, end_date,
        "Despesas por categoria", "Nenhuma despesa no período",
    )
