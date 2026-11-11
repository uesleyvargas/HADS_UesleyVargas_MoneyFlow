"""
Extratos: a visão tabular dos lançamentos.

Cumpre dois papéis. É a "table view" que acompanha os gráficos — todo valor
mostrado num gráfico precisa estar acessível em texto, sem depender de cor ou
de tooltip — e é onde se corrige e se exclui um lançamento. A versão anterior
não tinha nenhuma forma de editar ou apagar: um valor digitado errado ficava
no banco para sempre, distorcendo todos os relatórios.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dash_table, dcc, html, no_update

from moneyflow.app import app
from moneyflow.auth import current_user_id
from moneyflow.repositories import transactions as transactions_repo
from moneyflow.theme import (
    EXPENSE,
    INCOME,
    SURFACE,
    TEXT_MUTED,
    empty_figure,
    format_brl,
)

CARD_STYLE = {"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"}

# Colunas apresentadas. `id` fica oculto, mas é o que permite localizar o
# registro no banco quando uma linha é editada ou excluída.
TABLE_COLUMNS = [
    {"name": "Data", "id": "Data", "editable": True},
    {"name": "Descrição", "id": "Descrição", "editable": True},
    {"name": "Categoria", "id": "Categoria", "editable": True},
    {
        "name": "Valor",
        "id": "Valor",
        "editable": True,
        "type": "numeric",
    },
    {"name": "Pago/Recebido", "id": "Efetuado", "editable": False},
    {"name": "Recorrente", "id": "Fixo", "editable": False},
]


layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.H4("Extratos", className="fw-bold mb-0"),
                    xs=12, md="auto",
                ),
                dbc.Col(
                    dbc.RadioItems(
                        id="extrato-tipo",
                        options=[
                            {"label": "Despesas", "value": "despesa"},
                            {"label": "Receitas", "value": "receita"},
                        ],
                        value="despesa",
                        inline=True,
                        className="btn-group",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-primary btn-sm",
                        labelCheckedClassName="active",
                    ),
                    xs=12, md="auto", className="ms-md-auto",
                ),
            ],
            className="align-items-center mb-3 g-2",
        ),

        html.Div(id="extrato-feedback"),

        dbc.Card(
            dbc.CardBody(
                [
                    html.Small(
                        "Clique em uma célula para editar. Use o ✕ à esquerda "
                        "para excluir o lançamento.",
                        className="text-muted d-block mb-2",
                    ),
                    html.Div(
                        dash_table.DataTable(
                            id="tabela-extrato",
                            columns=TABLE_COLUMNS,
                            data=[],
                            editable=True,
                            row_deletable=True,
                            page_size=15,
                            sort_action="native",
                            filter_action="native",
                            style_as_list_view=True,
                            style_table={"overflowX": "auto"},
                            style_cell={
                                "textAlign": "left",
                                "padding": "10px",
                                "fontFamily": "system-ui, -apple-system, sans-serif",
                                "fontSize": "13px",
                                "border": "none",
                                "borderBottom": "1px solid #e1e0d9",
                            },
                            style_header={
                                "backgroundColor": SURFACE,
                                "fontWeight": "600",
                                "borderBottom": "2px solid #c3c2b7",
                                "color": "#52514e",
                            },
                            style_data_conditional=[
                                {
                                    "if": {"column_id": "Valor"},
                                    # Colunas numéricas alinham verticalmente,
                                    # então aqui `tabular-nums` é o correto.
                                    "fontVariantNumeric": "tabular-nums",
                                    "textAlign": "right",
                                }
                            ],
                        ),
                        className="dbc",
                    ),
                ]
            ),
            style=CARD_STYLE,
            className="mb-3",
        ),

        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    id="extrato-grafico",
                    style={"height": "340px"},
                    config={"displayModeBar": False, "responsive": True},
                )
            ),
            style=CARD_STYLE,
        ),
    ]
)


def _records_for(tipo: str, incomes, expenses):
    return incomes if tipo == "receita" else expenses


@app.callback(
    Output("tabela-extrato", "data"),
    Input("extrato-tipo", "value"),
    Input("store-receitas", "data"),
    Input("store-despesas", "data"),
)
def fill_table(tipo, incomes, expenses):
    """Carrega a tabela com o tipo de lançamento selecionado."""
    records = _records_for(tipo, incomes, expenses) or []
    if not records:
        return []

    frame = pd.DataFrame(records)
    frame["Data"] = pd.to_datetime(frame["Data"]).dt.strftime("%d/%m/%Y")
    frame["Efetuado"] = frame["Efetuado"].map({True: "Sim", False: "Não"})
    frame["Fixo"] = frame["Fixo"].map({True: "Sim", False: "Não"})

    return frame.to_dict("records")


@app.callback(
    Output("store-data-version", "data", allow_duplicate=True),
    Output("extrato-feedback", "children"),
    Input("tabela-extrato", "data_previous"),
    State("tabela-extrato", "data"),
    State("extrato-tipo", "value"),
    State("store-data-version", "data"),
    prevent_initial_call=True,
)
def persist_table_changes(previous, current, tipo, version):
    """
    Persiste exclusões e edições feitas na tabela.

    O DataTable entrega o estado anterior em ``data_previous``; comparar os
    dois estados revela o que mudou. Toda operação passa pelo repositório com
    o id do usuário autenticado, então editar a linha de outra pessoa é
    impossível mesmo que o cliente adultere o payload.
    """
    if previous is None or current is None:
        return no_update, None

    user_id = current_user_id()
    if user_id is None:
        return no_update, _alert("Sessão expirada. Faça login novamente.", "warning")

    previous_by_id = {row["id"]: row for row in previous if row.get("id") is not None}
    current_by_id = {row["id"]: row for row in current if row.get("id") is not None}

    # --- Exclusões --- #
    deleted_ids = set(previous_by_id) - set(current_by_id)
    for transaction_id in deleted_ids:
        result = transactions_repo.delete(user_id, transaction_id)
        if not result.success:
            return no_update, _alert(result.message, "danger")

    if deleted_ids:
        count = len(deleted_ids)
        return (version or 0) + 1, _alert(
            f"{count} lançamento(s) excluído(s).", "success"
        )

    # --- Edições --- #
    for transaction_id, row in current_by_id.items():
        old = previous_by_id.get(transaction_id)
        if old is None or old == row:
            continue

        result = transactions_repo.update(
            user_id,
            transaction_id,
            description=row.get("Descrição"),
            amount=row.get("Valor"),
            transaction_date=_parse_br_date(row.get("Data")),
            category_name=row.get("Categoria"),
        )
        if not result.success:
            # Devolver a versão anterior faz a tabela recarregar do banco,
            # descartando visualmente a edição inválida.
            return (version or 0) + 1, _alert(result.message, "danger")

        return (version or 0) + 1, _alert("Lançamento atualizado.", "success")

    return no_update, None


@app.callback(
    Output("extrato-grafico", "figure"),
    Input("extrato-tipo", "value"),
    Input("store-receitas", "data"),
    Input("store-despesas", "data"),
)
def update_chart(tipo, incomes, expenses):
    """
    Total por categoria, em barras horizontais.

    Barras horizontais comportam nomes de categoria longos sem girar o texto,
    e a ordenação por valor deixa a leitura imediata.
    """
    records = _records_for(tipo, incomes, expenses)
    label = "receita" if tipo == "receita" else "despesa"

    if not records:
        return empty_figure(f"Nenhuma {label} registrada")

    frame = pd.DataFrame(records)
    totals = frame.groupby("Categoria")["Valor"].sum().sort_values()

    figure = go.Figure(
        go.Bar(
            x=totals.values,
            y=totals.index,
            orientation="h",
            # Categoria nominal não tem ordem natural: uma cor só para todas
            # as barras. Colorir por tamanho duplicaria o que o comprimento
            # já mostra.
            marker=dict(
                color=INCOME if tipo == "receita" else EXPENSE,
                cornerradius=4,
                line=dict(color=SURFACE, width=2),
            ),
            text=[format_brl(v) for v in totals.values],
            textposition="outside",
            textfont=dict(size=11, color=TEXT_MUTED),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x:,.2f}<extra></extra>",
        )
    )

    figure.update_layout(
        title=f"Total de {label}s por categoria",
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="#e1e0d9"),
        yaxis=dict(showgrid=False),
        margin=dict(l=8, r=80, t=56, b=40),
    )
    return figure


def _parse_br_date(value) -> str | None:
    """Converte 'DD/MM/AAAA' para ISO; devolve None se não reconhecer."""
    if not value:
        return None
    try:
        return pd.to_datetime(value, format="%d/%m/%Y").date().isoformat()
    except (ValueError, TypeError):
        try:
            return pd.to_datetime(value).date().isoformat()
        except (ValueError, TypeError):
            return None


def _alert(message: str, color: str) -> dbc.Alert:
    return dbc.Alert(message, color=color, dismissable=True, duration=4000, className="mb-3")
