"""
Barra lateral: navegação e formulários de lançamento.

Diferença central em relação à versão anterior: as categorias são carregadas
por callback, a partir do usuário autenticado. Antes elas eram lidas do banco
no momento do import e ficavam congeladas na memória do processo — categorias
novas só apareciam depois de reiniciar o app, e a lista era a mesma para todos
os usuários.
"""

from __future__ import annotations

import random
from datetime import date

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback_context, dcc, html, no_update

from moneyflow.app import app
from moneyflow.auth import current_user_id, current_username
from moneyflow.models import TransactionType
from moneyflow.repositories import categories as categories_repo
from moneyflow.repositories import transactions as transactions_repo

FRASES_MOTIVACIONAIS = [
    "💰 Seu futuro financeiro começa hoje!",
    "📈 Cada centavo conta para seus objetivos",
    "🎯 Controle suas finanças, conquiste sua liberdade",
    "💪 Organização financeira é autocuidado",
    "🚀 Rumo à independência financeira!",
    "🌟 Pequenas economias, grandes conquistas",
    "📊 Domine seu dinheiro, transforme sua vida",
    "🔥 Seu progresso financeiro inspira!",
    "🌈 Planeje hoje, colha amanhã",
    "💎 Sua jornada financeira é única",
]


def get_frase_motivacional() -> str:
    # Sorteio puramente decorativo — não protege nada, então o gerador
    # pseudoaleatório comum é adequado aqui.
    return random.choice(FRASES_MOTIVACIONAIS)  # noqa: S311


def _category_manager(kind: str) -> dbc.Accordion:
    """Seção de gerenciamento das categorias de um tipo de lançamento."""
    label = "Receita" if kind == "receita" else "Despesa"
    return dbc.Accordion(
        [
            dbc.AccordionItem(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Small(
                                    "Adicionar", className="text-muted fw-bold d-block mb-2"
                                ),
                                dbc.InputGroup(
                                    [
                                        dbc.Input(
                                            id=f"input-add-{kind}",
                                            placeholder="Nova categoria...",
                                        ),
                                        dbc.Button(
                                            "Adicionar",
                                            id=f"add-category-{kind}",
                                            color="success",
                                        ),
                                    ]
                                ),
                            ],
                            xs=12,
                            md=6,
                            className="mb-3",
                        ),
                        dbc.Col(
                            [
                                html.Small(
                                    "Remover", className="text-muted fw-bold d-block mb-2"
                                ),
                                dbc.Checklist(
                                    id=f"checklist-remove-{kind}",
                                    options=[],
                                    value=[],
                                    style={"maxHeight": "140px", "overflowY": "auto"},
                                ),
                                dbc.Button(
                                    "Remover selecionadas",
                                    id=f"remove-category-{kind}",
                                    color="warning",
                                    size="sm",
                                    className="mt-2",
                                ),
                            ],
                            xs=12,
                            md=6,
                        ),
                    ]
                ),
                title=f"🔧 Gerenciar categorias de {label.lower()}",
            )
        ],
        flush=True,
        start_collapsed=True,
    )


def _transaction_modal(kind: str) -> dbc.Modal:
    """Modal de novo lançamento (receita ou despesa)."""
    is_income = kind == "receita"
    label = "Receita" if is_income else "Despesa"
    settled_label = "💰 Já foi recebida" if is_income else "💳 Já foi paga"

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(f"{'➕' if is_income else '➖'} Nova {label}")),
            dbc.ModalBody(
                [
                    html.Div(id=f"alert-{kind}"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("📝 Descrição"),
                                    dbc.Input(
                                        id=f"txt-{kind}",
                                        placeholder=(
                                            "Ex.: Salário, Freelance..."
                                            if is_income
                                            else "Ex.: Aluguel, Mercado..."
                                        ),
                                    ),
                                ],
                                xs=12,
                                md=6,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("💰 Valor"),
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText("R$"),
                                            dbc.Input(
                                                id=f"valor-{kind}",
                                                placeholder="0,00",
                                                type="number",
                                                min=0,
                                                step=0.01,
                                            ),
                                        ]
                                    ),
                                ],
                                xs=12,
                                md=6,
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("📅 Data"),
                                    dcc.DatePickerSingle(
                                        id=f"date-{kind}",
                                        date=date.today(),
                                        display_format="DD/MM/YYYY",
                                        className="d-block",
                                    ),
                                ],
                                xs=12,
                                md=4,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("📂 Categoria"),
                                    dbc.Select(id=f"select-{kind}", options=[]),
                                ],
                                xs=12,
                                md=4,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("⚙️ Opções"),
                                    dbc.Checklist(
                                        options=[
                                            {"label": settled_label, "value": "settled"},
                                            {"label": "🔄 Recorrente", "value": "recurring"},
                                        ],
                                        value=["settled"],
                                        id=f"switches-{kind}",
                                        switch=True,
                                    ),
                                ],
                                xs=12,
                                md=4,
                                className="mb-3",
                            ),
                        ]
                    ),
                    _category_manager(kind),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancelar",
                        id=f"cancel-{kind}",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        f"Salvar {label}",
                        id=f"salvar-{kind}",
                        color="success" if is_income else "danger",
                    ),
                ]
            ),
        ],
        id=f"modal-{kind}",
        size="lg",
        is_open=False,
        centered=True,
    )


def build_layout() -> dbc.Col:
    """
    Monta a sidebar.

    É uma função, não uma constante de módulo, porque o nome do usuário só é
    conhecido durante a requisição.
    """
    return dbc.Col(
        [
            html.Div(
                [
                    html.H3("MoneyFlow", className="text-primary fw-bold mb-0"),
                    html.Small(
                        f"Olá, {current_username()}", className="text-muted"
                    ),
                ],
                className="mb-3",
            ),
            html.Hr(),
            html.Div(
                [
                    html.P(
                        id="frase-motivacional",
                        children=get_frase_motivacional(),
                        className="text-white text-center mb-2",
                        style={
                            "fontSize": "13px",
                            "fontWeight": "500",
                            "padding": "12px",
                            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                            "borderRadius": "8px",
                            "minHeight": "56px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                    ),
                    dbc.Button(
                        "🔄 Nova inspiração",
                        id="btn-nova-frase",
                        color="primary",
                        outline=True,
                        size="sm",
                        className="w-100",
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            "+ Receita",
                            id="open-receita",
                            color="success",
                            className="w-100",
                        ),
                        xs=6,
                    ),
                    dbc.Col(
                        dbc.Button(
                            "- Despesa",
                            id="open-despesa",
                            color="danger",
                            className="w-100",
                        ),
                        xs=6,
                    ),
                ],
                className="g-2 mb-4",
            ),
            _transaction_modal("receita"),
            _transaction_modal("despesa"),
            html.Hr(),
            dbc.Nav(
                [
                    dbc.NavLink("📊 Dashboard", href="/dashboards", active="exact"),
                    dbc.NavLink("📋 Extratos", href="/extratos", active="exact"),
                    dbc.NavLink("🚪 Sair", href="/logout", id="logout-link"),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        id="sidebar",
        className="p-3",
    )


# --------------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------------- #


def _register_modal_toggle(kind: str) -> None:
    """Registra o callback que abre/fecha o modal de um tipo de lançamento."""

    @app.callback(
        Output(f"modal-{kind}", "is_open"),
        Input(f"open-{kind}", "n_clicks"),
        Input(f"cancel-{kind}", "n_clicks"),
        Input("store-data-version", "data"),
        State(f"modal-{kind}", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_modal(_open_clicks, _cancel_clicks, _version, is_open):
        triggered = callback_context.triggered_id
        if triggered == f"open-{kind}":
            return True
        if triggered == f"cancel-{kind}":
            return False
        # Um lançamento foi salvo: fecha o modal apenas se ele estiver aberto,
        # para não reagir a alterações feitas em outra tela.
        return False if is_open else no_update


for _kind in ("receita", "despesa"):
    _register_modal_toggle(_kind)


@app.callback(
    Output("select-receita", "options"),
    Output("select-receita", "value"),
    Output("checklist-remove-receita", "options"),
    Output("select-despesa", "options"),
    Output("select-despesa", "value"),
    Output("checklist-remove-despesa", "options"),
    Input("store-data-version", "data"),
)
def refresh_category_options(_version):
    """Recarrega as categorias do usuário autenticado."""
    user_id = current_user_id()
    if user_id is None:
        return [], None, [], [], None, []

    income = categories_repo.list_options(user_id, TransactionType.RECEITA)
    expense = categories_repo.list_options(user_id, TransactionType.DESPESA)

    return (
        income,
        income[0]["value"] if income else None,
        income,
        expense,
        expense[0]["value"] if expense else None,
        expense,
    )


def _register_save_callback(kind: str) -> None:
    """Registra o callback de gravação de um lançamento."""
    type_ = TransactionType.RECEITA if kind == "receita" else TransactionType.DESPESA

    @app.callback(
        Output("store-data-version", "data", allow_duplicate=True),
        Output(f"alert-{kind}", "children"),
        Output(f"txt-{kind}", "value"),
        Output(f"valor-{kind}", "value"),
        Input(f"salvar-{kind}", "n_clicks"),
        State(f"txt-{kind}", "value"),
        State(f"valor-{kind}", "value"),
        State(f"date-{kind}", "date"),
        State(f"select-{kind}", "value"),
        State(f"switches-{kind}", "value"),
        State("store-data-version", "data"),
        prevent_initial_call=True,
    )
    def save_transaction(
        _clicks, description, amount, transaction_date, category, switches, version
    ):
        user_id = current_user_id()
        if user_id is None:
            return no_update, _alert("Sessão expirada. Faça login novamente."), no_update, no_update

        switches = switches or []
        result = transactions_repo.create(
            user_id=user_id,
            type_=type_,
            description=description,
            amount=amount,
            transaction_date=transaction_date,
            category_name=category,
            is_settled="settled" in switches,
            is_recurring="recurring" in switches,
        )

        if not result.success:
            return no_update, _alert(result.message), no_update, no_update

        # Incrementar a versão avisa todas as telas de que os dados mudaram.
        return (version or 0) + 1, None, "", None


for _kind in ("receita", "despesa"):
    _register_save_callback(_kind)


def _register_category_callbacks(kind: str) -> None:
    """Registra os callbacks de adicionar/remover categorias."""
    type_ = TransactionType.RECEITA if kind == "receita" else TransactionType.DESPESA

    @app.callback(
        Output("store-data-version", "data", allow_duplicate=True),
        Output(f"alert-{kind}", "children", allow_duplicate=True),
        Output(f"input-add-{kind}", "value"),
        Input(f"add-category-{kind}", "n_clicks"),
        Input(f"remove-category-{kind}", "n_clicks"),
        State(f"input-add-{kind}", "value"),
        State(f"checklist-remove-{kind}", "value"),
        State("store-data-version", "data"),
        prevent_initial_call=True,
    )
    def manage_categories(_add, _remove, new_name, to_remove, version):
        user_id = current_user_id()
        if user_id is None:
            return no_update, _alert("Sessão expirada."), no_update

        triggered = callback_context.triggered_id

        if triggered == f"add-category-{kind}":
            result = categories_repo.add(user_id, new_name or "", type_)
        else:
            result = categories_repo.remove(user_id, to_remove or [], type_)

        if not result.success:
            return no_update, _alert(result.message), no_update

        return (version or 0) + 1, _alert(result.message, "success"), ""


for _kind in ("receita", "despesa"):
    _register_category_callbacks(_kind)


@app.callback(
    Output("frase-motivacional", "children"),
    Input("btn-nova-frase", "n_clicks"),
    prevent_initial_call=True,
)
def update_frase(_clicks):
    return get_frase_motivacional()


def _alert(message: str, color: str = "warning") -> dbc.Alert:
    return dbc.Alert(message, color=color, dismissable=True, duration=4000)
