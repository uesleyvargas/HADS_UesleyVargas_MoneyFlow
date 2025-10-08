"""
Arquivo principal do aplicativo MyFinance. Responsável pelo roteamento,
layout principal e gerenciamento de sessões de usuário.
"""
from db import inicializar_app
from dash import html, dcc
import dash
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from app import app
from components import sidebar, dashboards, extratos, login
from db import ler_transacoes, ler_categorias, buscar_usuario_por_id
import pandas as pd

# --- Layout Principal ---
content = html.Div(id="page-content")

app.layout = dbc.Container(children=[
    # Store para gerenciar a sessão do usuário
    dcc.Store(id='store-user-session', data=None, storage_type='session'),
    
    # Stores para dados financeiros (serão preenchidos após login)
    dcc.Store(id='store-receitas', data=None),
    dcc.Store(id='store-despesas', data=None),
    dcc.Store(id='store-cat-receitas', data=None),
    dcc.Store(id='store-cat-despesas', data=None),
    
    # Location para roteamento
    dcc.Location(id='url', refresh=False),
    
    # Conteúdo principal que muda baseado na rota
    html.Div(id="main-content")
], fluid=True)

# --- Callbacks ---

@app.callback(
    Output('main-content', 'children'),
    [Input('url', 'pathname'),
     Input('store-user-session', 'data')]
)
def display_page(pathname, session_data):
    """
    Controla qual página é exibida baseado na rota e status de login.
    
    Args:
        pathname (str): Caminho da URL atual
        session_data (dict): Dados da sessão do usuário
        
    Returns:
        html.Div: Layout da página a ser exibida
    """
    # Verifica se o usuário está logado
    if not session_data or not session_data.get('logged_in'):
        # Se não estiver logado, sempre mostra a tela de login
        return login.layout
    
    # Se estiver logado, mostra o layout principal com sidebar
    return dbc.Row([
        dbc.Col([
            sidebar.layout
        ], md=2),
        dbc.Col([
            content
        ], md=10)
    ])

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('store-user-session', 'data')]
)
def render_page_content(pathname, session_data):
    """
    Renderiza o conteúdo específico da página baseado na rota.
    
    Args:
        pathname (str): Caminho da URL atual
        session_data (dict): Dados da sessão do usuário
        
    Returns:
        html.Div: Conteúdo da página específica
    """
    # Se não estiver logado, não renderiza conteúdo
    if not session_data or not session_data.get('logged_in'):
        return html.Div()
    
    # Roteamento para páginas autenticadas
    if pathname == '/' or pathname == '/dashboards':
        return dashboards.layout
    elif pathname == '/extratos':
        return extratos.layout
    elif pathname == '/logout':
        return html.Div()  # Logout será tratado por outro callback
    else:
        # Página não encontrada
        return dbc.Container([
            dbc.Alert(
                "Página não encontrada. Redirecionando para o dashboard...",
                color="warning"
            )
        ])

@app.callback(
    [Output('store-receitas', 'data', allow_duplicate=True),
     Output('store-despesas', 'data', allow_duplicate=True),
     Output('store-cat-receitas', 'data', allow_duplicate=True),
     Output('store-cat-despesas', 'data', allow_duplicate=True)],
    Input('store-user-session', 'data'),
    prevent_initial_call=True
)
def load_user_data(session_data):
    """
    Carrega os dados financeiros do usuário quando ele faz login.
    
    Args:
        session_data (dict): Dados da sessão do usuário
        
    Returns:
        tuple: (receitas, despesas, cat_receitas, cat_despesas) - Dados financeiros do usuário
    """
    if not session_data or not session_data.get('logged_in'):
        return [], [], [], []
    
    user_id = session_data.get('user_id')
    
    # Carrega dados específicos do usuário
    df_r, df_d = ler_transacoes(user_id)
    cat_r, cat_d = ler_categorias()
    
    # Converte para formato de dicionário para os stores
    data_receitas = df_r.to_dict('records') if not df_r.empty else []
    data_despesas = df_d.to_dict('records') if not df_d.empty else []
    data_cat_receitas = pd.DataFrame(cat_r, columns=['Categoria']).to_dict('records')
    data_cat_despesas = pd.DataFrame(cat_d, columns=['Categoria']).to_dict('records')
    
    return data_receitas, data_despesas, data_cat_receitas, data_cat_despesas

@app.callback(
    [Output('url', 'pathname'),
     Output('store-user-session', 'data', allow_duplicate=True)],
    Input('store-user-session', 'data'),
    prevent_initial_call=True
)
def handle_login_redirect(session_data):
    """
    Redireciona o usuário após login bem-sucedido.
    
    Args:
        session_data (dict): Dados da sessão do usuário
        
    Returns:
        tuple: (pathname, session_data) - Nova rota e dados da sessão
    """
    if session_data and session_data.get('logged_in'):
        # Redireciona para dashboard após login
        return '/dashboards', session_data
    
    # Mantém na página atual se não estiver logado
    return dash.no_update, session_data

# Callback para logout (pode ser acionado por um botão na sidebar)
@app.callback(
    [Output('store-user-session', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True)],
    Input('url', 'pathname'),
    State('store-user-session', 'data'),
    prevent_initial_call=True
)
def handle_logout(pathname, session_data):
    """
    Processa o logout do usuário.
    
    Args:
        pathname (str): Caminho da URL atual
        session_data (dict): Dados da sessão atual
        
    Returns:
        tuple: (session_data, pathname) - Sessão limpa e redirecionamento
    """
    if pathname == '/logout':
        # Limpa a sessão e redireciona para login
        return None, '/'
    
    return dash.no_update, dash.no_update

# --- Execução do App ---
if __name__ == '__main__':
    app.run(port=8050, debug=True, host='127.0.0.1')

inicializar_app()