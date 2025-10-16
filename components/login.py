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