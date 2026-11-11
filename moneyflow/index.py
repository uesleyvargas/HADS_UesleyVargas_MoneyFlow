"""
Layout raiz e roteamento.

Ponto de entrada da interface: monta o layout, decide qual página exibir e
alimenta os ``dcc.Store`` com os dados do usuário autenticado.

A autorização acontece aqui, no servidor. Um usuário não autenticado recebe a
tela de login independentemente da rota pedida, e os stores permanecem vazios
— não existe caminho pelo qual o navegador consiga pedir dados de outra conta.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html
from flask_login import logout_user

from moneyflow.app import app
from moneyflow.auth import current_user_id, is_authenticated
from moneyflow.components import sidebar
from moneyflow.pages import dashboards, extratos, login
from moneyflow.repositories import transactions as transactions_repo
from moneyflow.theme import register_template

register_template()

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),

        # Dados do usuário autenticado, preenchidos pelo servidor.
        dcc.Store(id="store-receitas", data=[]),
        dcc.Store(id="store-despesas", data=[]),

        # Contador incrementado a cada alteração nos dados. Serve como sinal
        # único de "recarregue": qualquer tela que altere algo o incrementa, e
        # todas as demais reagem.
        dcc.Store(id="store-data-version", data=0),

        html.Div(id="app-container"),
    ]
)


def _authenticated_shell(pathname: str) -> dbc.Container:
    """Casca do app autenticado: sidebar + conteúdo da rota."""
    if pathname in ("/", "/dashboards"):
        content = dashboards.layout
    elif pathname == "/extratos":
        content = extratos.layout
    else:
        content = dbc.Alert(
            [
                html.H5("Página não encontrada", className="alert-heading"),
                html.P("O endereço acessado não existe.", className="mb-0"),
                dbc.Button(
                    "Ir para o dashboard",
                    href="/dashboards",
                    color="primary",
                    size="sm",
                    className="mt-3",
                ),
            ],
            color="warning",
        )

    return dbc.Container(
        dbc.Row(
            [
                dbc.Col(
                    sidebar.build_layout(),
                    xs=12, md=4, lg=3, xl=2,
                    className="border-end bg-white",
                ),
                dbc.Col(
                    content,
                    xs=12, md=8, lg=9, xl=10,
                    className="p-3 p-md-4",
                    style={"backgroundColor": "#f9f9f7", "minHeight": "100vh"},
                ),
            ],
            className="g-0",
        ),
        fluid=True,
        className="px-0",
    )


@app.callback(
    Output("app-container", "children"),
    Input("url", "pathname"),
)
def route(pathname: str):
    """Decide o que renderizar, sempre validando a sessão no servidor."""
    if pathname == "/logout":
        logout_user()
        return login.layout

    if not is_authenticated():
        return login.layout

    return _authenticated_shell(pathname or "/")


@app.callback(
    Output("store-receitas", "data"),
    Output("store-despesas", "data"),
    Input("url", "pathname"),
    Input("store-data-version", "data"),
)
def load_user_data(_pathname, _version):
    """
    Carrega os lançamentos do usuário autenticado.

    O id vem de ``current_user_id()`` — derivado do cookie assinado — e nunca
    de um parâmetro enviado pelo cliente.
    """
    user_id = current_user_id()
    if user_id is None:
        return [], []

    return transactions_repo.load_dashboard_data(user_id)
