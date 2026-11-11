"""
Tela de login e cadastro.

O sucesso do login é registrado por ``flask_login.login_user``, que grava um
cookie assinado. A interface não recebe nem guarda nenhum indicador de
"está logado" que o cliente possa alterar.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback_context, html, no_update
from flask_login import login_user

from moneyflow.app import app
from moneyflow.repositories import users

CARD_STYLE = {
    "maxWidth": "440px",
    "width": "100%",
    "borderRadius": "16px",
    "boxShadow": "0 10px 30px rgba(0, 0, 0, 0.08)",
    "border": "none",
}

PAGE_STYLE = {
    "minHeight": "100vh",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "padding": "20px",
}


def _input_group(icon: str, **input_kwargs) -> dbc.InputGroup:
    """Monta um campo com ícone à esquerda."""
    return dbc.InputGroup(
        [dbc.InputGroupText(html.I(className=icon)), dbc.Input(**input_kwargs)],
        className="mb-3",
    )


def _header() -> html.Div:
    return html.Div(
        [
            html.H2("MoneyFlow", className="text-center text-primary fw-bold mb-1"),
            html.P(
                "Gerencie suas finanças de forma inteligente",
                className="text-center text-muted mb-4",
            ),
        ]
    )


login_form = html.Div(
    [
        _input_group(
            "fa-solid fa-user",
            id="login-username",
            placeholder="Usuário ou e-mail",
            type="text",
            autoFocus=True,
        ),
        _input_group(
            "fa-solid fa-lock",
            id="login-password",
            placeholder="Senha",
            type="password",
        ),
        dbc.Button("Entrar", id="login-button", color="primary", className="w-100 mb-3"),
        html.Hr(),
        html.P("Ainda não tem uma conta?", className="text-center text-muted mb-2"),
        dbc.Button(
            "Criar conta",
            id="show-register-button",
            color="primary",
            outline=True,
            className="w-100",
        ),
    ],
    id="login-form",
)

register_form = html.Div(
    [
        _input_group(
            "fa-solid fa-user",
            id="register-username",
            placeholder="Nome de usuário",
            type="text",
        ),
        _input_group(
            "fa-solid fa-envelope",
            id="register-email",
            placeholder="E-mail",
            type="email",
        ),
        _input_group(
            "fa-solid fa-lock",
            id="register-password",
            placeholder="Senha (mínimo 8 caracteres)",
            type="password",
        ),
        _input_group(
            "fa-solid fa-lock",
            id="register-confirm-password",
            placeholder="Confirmar senha",
            type="password",
        ),
        dbc.Button(
            "Criar conta", id="register-button", color="success", className="w-100 mb-3"
        ),
        html.Hr(),
        html.P("Já tem uma conta?", className="text-center text-muted mb-2"),
        dbc.Button(
            "Fazer login",
            id="show-login-button",
            color="success",
            outline=True,
            className="w-100",
        ),
    ],
    id="register-form",
    style={"display": "none"},
)

layout = html.Div(
    dbc.Card(
        dbc.CardBody(
            [
                _header(),
                html.Div(id="login-alert"),
                login_form,
                register_form,
            ],
            className="p-4",
        ),
        style=CARD_STYLE,
    ),
    style=PAGE_STYLE,
)


@app.callback(
    Output("login-form", "style"),
    Output("register-form", "style"),
    Output("login-alert", "children", allow_duplicate=True),
    Input("show-register-button", "n_clicks"),
    Input("show-login-button", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_forms(_register_clicks, _login_clicks):
    """Alterna entre os formulários, limpando o alerta anterior."""
    triggered = callback_context.triggered_id

    if triggered == "show-register-button":
        return {"display": "none"}, {"display": "block"}, None
    return {"display": "block"}, {"display": "none"}, None


@app.callback(
    Output("login-alert", "children"),
    Output("url", "pathname", allow_duplicate=True),
    Input("login-button", "n_clicks"),
    Input("login-password", "n_submit"),
    Input("login-username", "n_submit"),
    State("login-username", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def process_login(_clicks, _password_submit, _username_submit, username, password):
    """Autentica o usuário e abre a sessão no servidor."""
    if not username or not password:
        return _alert("Preencha usuário e senha.", "warning"), no_update

    user = users.authenticate(username, password)

    if user is None:
        # Mensagem genérica de propósito: dizer "usuário não existe" permitiria
        # descobrir quais contas estão cadastradas.
        return _alert("Usuário ou senha incorretos.", "danger"), no_update

    login_user(user, remember=True)
    return None, "/dashboards"


@app.callback(
    Output("login-alert", "children", allow_duplicate=True),
    Input("register-button", "n_clicks"),
    State("register-username", "value"),
    State("register-email", "value"),
    State("register-password", "value"),
    State("register-confirm-password", "value"),
    prevent_initial_call=True,
)
def process_register(_clicks, username, email, password, confirm_password):
    """Valida e cria uma conta nova."""
    error = users.validate_registration(
        username or "", email or "", password or "", confirm_password or ""
    )
    if error:
        return _alert(error, "warning")

    result = users.create_user(username, email, password)
    if not result.success:
        return _alert(result.message, "danger")

    return _alert(f"{result.message} Faça login para começar.", "success")


def _alert(message: str, color: str) -> dbc.Alert:
    return dbc.Alert(message, color=color, dismissable=True, className="mb-3")
