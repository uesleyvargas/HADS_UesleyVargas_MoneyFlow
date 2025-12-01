"""
Componente responsável pela interface de login e registro de usuários
do aplicativo MyFinance. Inclui layouts e callbacks para autenticação.
"""
from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from app import app
from db import autenticar_usuario, criar_usuario

# --- Estilos CSS ---
login_card_style = {
    'width': '400px',
    'margin': '0 auto',
    'margin-top': '100px',
    'padding': '30px',
    'border-radius': '15px',
    'box-shadow': '0 4px 6px rgba(0, 0, 0, 0.1)'
}

input_style = {
    'margin-bottom': '15px'
}

button_style = {
    'width': '100%',
    'margin-bottom': '10px'
}
# --- Layout da Tela de Login ---
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    # Logo e título
                    html.Div([
                        html.H2("MoneyFlow", className="text-center text-primary mb-4"),
                        html.P("Gerencie suas finanças de forma inteligente", 
                               className="text-center text-muted mb-4")
                    ]),
                    
                    # Alertas para feedback
                    html.Div(id="login-alert", className="mb-3"),
                    
                    # Formulário de Login
                    html.Div([
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fa fa-user")),
                            dbc.Input(
                                id="login-username",
                                placeholder="Usuário ou Email",
                                type="text",
                                style=input_style
                            )
                        ], className="mb-3"),
                        
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fa fa-lock")),
                            dbc.Input(
                                id="login-password",
                                placeholder="Senha",
                                type="password",
                                style=input_style
                            )
                        ], className="mb-3"),
                        
                        dbc.Button(
                            "Entrar",
                            id="login-button",
                            color="primary",
                            style=button_style
                        ),
                        
                        html.Hr(),
                        
                        html.P("Não tem uma conta?", className="text-center mb-2"),
                        dbc.Button(
                            "Criar Conta",
                            id="show-register-button",
                            color="outline-primary",
                            style=button_style
                        )
                    ], id="login-form"),
                    
                    # Formulário de Registro (inicialmente oculto)
                    html.Div([
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fa fa-user")),
                            dbc.Input(
                                id="register-username",
                                placeholder="Nome de Usuário",
                                type="text",
                                style=input_style
                            )
                        ], className="mb-3"),
                        
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fa fa-envelope")),
                            dbc.Input(
                                id="register-email",
                                placeholder="Email",
                                type="email",
                                style=input_style
                            )
                        ], className="mb-3"),
                        
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fa fa-lock")),
                            dbc.Input(
                                id="register-password",
                                placeholder="Senha",
                                type="password",
                                style=input_style
                            )
                        ], className="mb-3"),
                        
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fa fa-lock")),
                            dbc.Input(
                                id="register-confirm-password",
                                placeholder="Confirmar Senha",
                                type="password",
                                style=input_style
                            )
                        ], className="mb-3"),
                        
                        dbc.Button(
                            "Criar Conta",
                            id="register-button",
                            color="success",
                            style=button_style
                        ),
                        
                        html.Hr(),
                        
                        html.P("Já tem uma conta?", className="text-center mb-2"),
                        dbc.Button(
                            "Fazer Login",
                            id="show-login-button",
                            color="outline-success",
                            style=button_style
                        )
                    ], id="register-form", style={"display": "none"})
                ])
            ], style=login_card_style)
        ], width=12)
    ], justify="center")
], fluid=True, style={"min-height": "100vh", "background-color": "#f8f9fa"})

# --- Callbacks ---#

@app.callback(
    [Output("login-form", "style"),
     Output("register-form", "style")],
    [Input("show-register-button", "n_clicks"),
     Input("show-login-button", "n_clicks")]
)
def toggle_forms(show_register_clicks, show_login_clicks):
    """
    Alterna entre os formulários de login e registro.

    """
    ctx = callback_context
    
    if not ctx.triggered:
        return {"display": "block"}, {"display": "none"}
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "show-register-button":
        return {"display": "none"}, {"display": "block"}
    elif button_id == "show-login-button":
        return {"display": "block"}, {"display": "none"}
    
    return {"display": "block"}, {"display": "none"}

@app.callback(
    [Output("login-alert", "children"),
     Output("store-user-session", "data")],
    Input("login-button", "n_clicks"),
    [State("login-username", "value"),
     State("login-password", "value")],
    prevent_initial_call=True
)
def process_login(n_clicks, username, password):
    """
    Processa o login do usuário.
    
    """
    if not n_clicks or not username or not password:
        return "", None
    
    # Tenta autenticar o usuário
    usuario = autenticar_usuario(username, password)
    
    if usuario:
        # Login bem-sucedido
        alert = dbc.Alert(
            "Login realizado com sucesso! Redirecionando...",
            color="success",
            dismissable=True
        )
        
        # Retorna dados da sessão
        session_data = {
            'logged_in': True,
            'user_id': usuario['id'],
            'username': usuario['username'],
            'email': usuario['email']
        }
        
        return alert, session_data
    else:
        # Login falhou
        alert = dbc.Alert(
            "Usuário ou senha incorretos. Tente novamente.",
            color="danger",
            dismissable=True
        )
        return alert, None
    
@app.callback(
    Output("login-alert", "children", allow_duplicate=True),
    Input("register-button", "n_clicks"),
    [State("register-username", "value"),
     State("register-email", "value"),
     State("register-password", "value"),
     State("register-confirm-password", "value")],
     prevent_initial_call=True
)
def process_register(n_clicks, username, email, password, confirm_password):
    """
     Processa o registro de um novo usuário.

    """
    if not n_clicks:
        return ""
    
    # Validações básicas
    if not all([username, email, password, confirm_password]):
        return dbc.Alert(
            "Todos os campos são obrigatórios.",
            color="warning",
            dismissable=True
        )
    
    if password != confirm_password:
        return dbc.Alert(
            "As senhas não coincidem.",
            color="warning",
            dismissable=True
        )
    
    if len(password) < 6:
        return dbc.Alert(
            "A senha deve ter pelo menos 6 caracteres.",
            color="warning",
            dismissable=True
        )
    
    #tenta criar o usuário
    sucesso, mensagem = criar_usuario(username, email, password)

    if sucesso:
        return dbc.Alert(
            f"{mensagem}. Agora você pode fazer login.",
            color="success",
            dismissable=True
        )
    else:
        return dbc.Alert(
            mensagem,
            color="danger",
            dismissable=True
        )
    
@app.callback(
    Output("login-button", "n_clicks"),
    [Input("login-username", "n_submit"),
     Input("login-password", "n_submit")],
    [State("login-button", "n_clicks"),
     State("login-username", "value"),
     State("login-password", "value")],
    prevent_initial_call=True
)
def submit_on_enter(username_submit, password_submit, current_clicks, username, password):
    """
    Permite fazer login pressionando Enter nos campos de entrada.
    Só permite se ambos os campos estiverem preenchidos.
    """
    if (username_submit or password_submit) and username and password:
        return (current_clicks or 0) + 1
    return current_clicks or 0