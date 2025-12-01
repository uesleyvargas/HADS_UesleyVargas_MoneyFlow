"""
Componente da barra lateral do aplicativo.
Responsável pela navegação, formulários de transações e upload de foto de perfil.
"""

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import random
import dash_bootstrap_components as dbc
from app import app
from datetime import datetime, date
import pandas as pd
import sqlite3
import base64
import os

# Importa as funções do banco de dados
from db import (
    conectar_bd, 
    ler_transacoes, 
    ler_categorias, 
    cat_receita, 
    cat_despesa,
    salvar_transacao
)

# ========= CONFIGURAÇÕES ========= #

# Frases motivacionais 
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
    "💎 Sua jornada financeira única"
]

def get_frase_motivacional():
    """Retorna uma frase motivacional aleatória."""
    return random.choice(FRASES_MOTIVACIONAIS)

# ========= FUNÇÕES AUXILIARES ========= #
def create_receita_modal_body():
    """Cria o corpo do modal de receita."""
    return [
        # Linha 1: Descrição e Valor
        dbc.Row([
            dbc.Col([
                dbc.Label('📝 Descrição'),
                dbc.Input(
                    placeholder="Ex.: Salário, Freelance, Dividendos...", 
                    id="txt-receita",
                    className="modal-input"
                )
            ], width=6), 
            dbc.Col([
                dbc.Label("💰 Valor"),
                dbc.Input(
                    placeholder="R$ 0,00", 
                    id="valor-receita", 
                    value="",
                    type="number",
                    className="modal-input"
                )
            ], width=6)
        ]),
        
        # Linha 2: Data, Extras e Categoria
        dbc.Row([
            dbc.Col([
                dbc.Label("📅 Data"),
                dcc.DatePickerSingle(
                    id='date-receitas',
                    min_date_allowed=date(2020, 1, 1),
                    max_date_allowed=date(2030, 12, 31),
                    date=datetime.today(),
                    className="date-picker"
                )
            ], width=4),
            dbc.Col([
                dbc.Label("⚙️ Extras"),
                dbc.Checklist(
                    options=[
                        {"label": "💰 Foi recebida", "value": 1}, 
                        {"label": "🔄 Receita Recorrente", "value": 2}
                    ], 
                    value=[1], 
                    id='switches-input-receita', 
                    switch=True,
                    className="checklist-custom"
                )
            ], width=4),
            dbc.Col([
                dbc.Label('📂 Categoria'),
                dbc.Select(
                    id='select_receita', 
                    options=[{'label': i, 'value': i} for i in cat_receita],
                    value=cat_receita[0] if cat_receita else None,
                    className="modal-select"
                )
            ], width=4)
        ], className="modal-row-spaced"),
        
        # Acordeão para Gerenciar Categorias
        dbc.Accordion([
            dbc.AccordionItem(
                children=[create_category_management_section('receita')],
                title='🔧 Gerenciar Categorias de Receita'
            )
        ], flush=True, start_collapsed=True, id='accordion-receita'),
        
        html.Div(id='id_teste_receita')
    ]

def create_despesa_modal_body():
    """Cria o corpo do modal de despesa."""
    return [
        # Linha 1: Descrição e Valor
        dbc.Row([
            dbc.Col([
                dbc.Label('📝 Descrição'),
                dbc.Input(
                    placeholder="Ex.: Aluguel, Supermercado, Transporte...", 
                    id="txt-despesa",
                    className="modal-input"
                )
            ], width=6), 
            dbc.Col([
                dbc.Label("💰 Valor"),
                dbc.Input(
                    placeholder="R$ 0,00", 
                    id="valor-despesa", 
                    value="",
                    type="number",
                    className="modal-input"
                )
            ], width=6)
        ]),
        
        # Linha 2: Data, Extras e Categoria
        dbc.Row([
            dbc.Col([
                dbc.Label("📅 Data"),
                dcc.DatePickerSingle(
                    id='date-despesas',
                    min_date_allowed=date(2020, 1, 1),
                    max_date_allowed=date(2030, 12, 31),
                    date=datetime.today(),
                    className="date-picker"
                )
            ], width=4),
            dbc.Col([
                dbc.Label("⚙️ Extras"),
                dbc.Checklist(
                    options=[
                        {"label": "💳 Foi paga", "value": 1}, 
                        {"label": "🔄 Despesa Recorrente", "value": 2}
                    ], 
                    value=[1], 
                    id='switches-input-despesa', 
                    switch=True,
                    className="checklist-custom"
                )
            ], width=4),
            dbc.Col([
                dbc.Label('📂 Categoria'),
                dbc.Select(
                    id='select_despesa', 
                    options=[{'label': i, 'value': i} for i in cat_despesa],
                    value=cat_despesa[0] if cat_despesa else None,
                    className="modal-select"
                )
            ], width=4)
        ], className="modal-row-spaced"),
        
        # Acordeão para Gerenciar Categorias
        dbc.Accordion([
            dbc.AccordionItem(
                children=[create_category_management_section('despesa')],
                title='🔧 Gerenciar Categorias de Despesa'
            )
        ], flush=True, start_collapsed=True, id='accordion-despesa'),
        
        html.Div(id='id_teste_despesa')
    ]

def create_category_management_section(tipo):
    """Cria a seção de gerenciamento de categorias."""
    return dbc.Row([
        dbc.Col([
            html.Legend("➕ Adicionar Categoria", className="category-section-title"),
            dbc.Input(
                type="text", 
                placeholder="Nova categoria...", 
                id=f"input-add-{tipo}",
                className="category-input"
            ),
            html.Br(), 
            dbc.Button(
                "Adicionar", 
                className="btn btn-success", 
                id=f"add-category-{tipo}", 
                style={"margin-top": "10px"}
            )
        ], width=6),
        dbc.Col([
            html.Legend("🗑️ Excluir Categorias", className="category-section-title"),
            dbc.Checklist(
                id=f"checklist-selected-style-{tipo}", 
                options=[],
                value=[],
                label_checked_style={"color": "red"},
                input_checked_style={"backgroundColor": "#fa7268", "borderColor": "#ea6258"}
            ),
            dbc.Button(
                "Remover Selecionadas", 
                color="warning", 
                id=f"remove-category-{tipo}", 
                style={"margin-top": "10px"}
            )
        ], width=6)
    ])

# ========= LAYOUT PRINCIPAL ========= #
layout = dbc.Col([
    # Cabeçalho
    html.H1("MoneyFlow", className="text-primary"),
    html.P("By Uesley", className="text-info"),
    html.Hr(),
    
    # Seção com Mensagem Motivacional
    html.Div([
        # Store para manter o estado da frase
        dcc.Store(id='store-frase-motivacional', data={'frase': get_frase_motivacional()}),
        
        # Mensagem Motivacional
        html.Div([
            html.P(
                id="frase-motivacional",
                children=get_frase_motivacional(),
                style={
                    'font-size': '14px',
                    'font-weight': '500',
                    'color': '#2c3e50',
                    'text-align': 'center',
                    'margin': '10px 0',
                    'padding': '10px 15px',
                    'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    'color': 'white',
                    'border-radius': '8px',
                    'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'min-height': '50px',
                    'display': 'flex',
                    'align-items': 'center',
                    'justify-content': 'center'
                }
            ),
            # Botão para nova frase
            dbc.Button(
                "🔄 Nova Inspiração",
                id="btn-nova-frase",
                color="outline-primary",
                size="sm",
                style={
                    'width': '100%',
                    'margin-top': '5px',
                    'font-size': '12px'
                }
            )
        ], style={'margin-bottom': '15px'})
    ], style={
        'textAlign': 'center',
        'padding': '15px',
        'background': '#f8f9fa',
        'border-radius': '10px',
        'margin-bottom': '20px'
    }),
    
    # Botões de Ação Rápida
    dbc.Row([
        dbc.Col([
            dbc.Button(
                color='success', 
                id='open-novo-receita', 
                children=['+ Receita'],
                className="action-button"
            )
        ], width=6), 
        dbc.Col([
            dbc.Button(
                color='danger', 
                id='open-novo-despesa', 
                children=['- Despesa'],
                className="action-button"
            )
        ], width=6)
    ], className="action-buttons-row"),
    
    # Modal para Adicionar Receita
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle('➕ Adicionar Receita')),
        dbc.ModalBody(create_receita_modal_body()),
        dbc.ModalFooter([
            dbc.Button("Adicionar Receita", id="salvar_receita", color="success"),
            dbc.Popover(
                dbc.PopoverBody("✅ Receita Salva com Sucesso!"),
                target="salvar_receita",
                placement="left",
                trigger="click"
            )
        ])
    ], id="modal-novo-receita", size="lg", is_open=False, centered=True, backdrop=True),
    
    # Modal para Adicionar Despesa
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle('➖ Adicionar Despesa')),
        dbc.ModalBody(create_despesa_modal_body()),
        dbc.ModalFooter([
            dbc.Button("Adicionar Despesa", id="salvar_despesa", color="danger"),
            dbc.Popover(
                dbc.PopoverBody("✅ Despesa Salva com Sucesso!"),
                target="salvar_despesa",
                placement="left",
                trigger="click"
            )
        ])
    ], id="modal-novo-despesa", size="lg", is_open=False, centered=True, backdrop=True),
    
    html.Hr(),
    
    # Navegação Principal
    dbc.Nav([
        dbc.NavLink("📊 Dashboard", href="/dashboards", active="exact", className="nav-link-custom"), 
        dbc.NavLink("📋 Extratos", href="/extratos", active="exact", className="nav-link-custom"),
        dbc.NavLink("🚪 Sair", href="/logout", active="exact", className="nav-link-custom")
    ], vertical=True, pills=True, id='nav_buttons')
], id='sidebar_completa')

# ========= CALLBACKS ========= #

# CALLBACK: Controle dos Modais
@app.callback(
    Output('modal-novo-receita', 'is_open'),
    [Input('open-novo-receita', 'n_clicks'),
     Input('salvar_receita', 'n_clicks')],
    State('modal-novo-receita', 'is_open')
)
def toggle_receita_modal(open_clicks, save_clicks, is_open):
    """Abre/fecha o modal de receita."""
    if open_clicks or save_clicks:
        return not is_open
    return is_open

@app.callback(
    Output('modal-novo-despesa', 'is_open'),
    [Input('open-novo-despesa', 'n_clicks'),
     Input('salvar_despesa', 'n_clicks')],
    State('modal-novo-despesa', 'is_open')
)
def toggle_despesa_modal(open_clicks, save_clicks, is_open):
    """Abre/fecha o modal de despesa."""
    if open_clicks or save_clicks:
        return not is_open
    return is_open

# CALLBACK: Salvar Transações
@app.callback(
    Output('store-receitas', 'data'),
    Input('salvar_receita', 'n_clicks'),
    [State("txt-receita", "value"),
     State("valor-receita", "value"),
     State("date-receitas", "date"),
     State("switches-input-receita", "value"),
     State("select_receita", "value"),
     State("store-user-session", "data")],
    prevent_initial_call=True
)
def save_receita(n_clicks, descricao, valor, data_str, switches, categoria, session_data):
    """Salva uma nova receita no banco de dados."""
    if not n_clicks or not valor:
        return dash.no_update
    
    try:
        # Prepara os dados
        data = pd.to_datetime(data_str).date() if data_str else datetime.today().date()
        efetuado = 1 if switches and 1 in switches else 0
        fixo = 1 if switches and 2 in switches else 0
        usuario_id = session_data.get('user_id') if session_data else None
        
        # Salva no banco
        salvar_transacao('receita', descricao, float(valor), data, categoria, efetuado, fixo, usuario_id)
        
        # Recarrega os dados
        df_receitas, _ = ler_transacoes(usuario_id)
        return df_receitas.to_dict('records') if not df_receitas.empty else []
        
    except Exception as e:
        print(f"❌ Erro ao salvar receita: {e}")
        return dash.no_update

@app.callback(
    Output('store-despesas', 'data'),
    Input('salvar_despesa', 'n_clicks'),
    [State("txt-despesa", "value"),
     State("valor-despesa", "value"),
     State("date-despesas", "date"),
     State("switches-input-despesa", "value"),
     State("select_despesa", "value"),
     State("store-user-session", "data")],
    prevent_initial_call=True
)
def save_despesa(n_clicks, descricao, valor, data_str, switches, categoria, session_data):
    """Salva uma nova despesa no banco de dados."""
    if not n_clicks or not valor:
        return dash.no_update
    
    try:
        # Prepara os dados
        data = pd.to_datetime(data_str).date() if data_str else datetime.today().date()
        efetuado = 1 if switches and 1 in switches else 0
        fixo = 1 if switches and 2 in switches else 0
        usuario_id = session_data.get('user_id') if session_data else None
        
        # Salva no banco
        salvar_transacao('despesa', descricao, float(valor), data, categoria, efetuado, fixo, usuario_id)
        
        # Recarrega os dados
        _, df_despesas = ler_transacoes(usuario_id)
        return df_despesas.to_dict('records') if not df_despesas.empty else []
        
    except Exception as e:
        print(f"❌ Erro ao salvar despesa: {e}")
        return dash.no_update
    
# CALLBACK: Gerenciamento de Categorias
@app.callback(
    [Output("select_receita", "options"),
     Output('checklist-selected-style-receita', 'options')],
    [Input("add-category-receita", "n_clicks"),
     Input("remove-category-receita", 'n_clicks')],
    [State("input-add-receita", "value"),
     State('checklist-selected-style-receita', 'value')],
    prevent_initial_call=True
)
def manage_receita_categories(add_clicks, remove_clicks, nova_categoria, categorias_remover):
    """Gerencia categorias de receita (adicionar/remover)."""
    return manage_categories('receita', add_clicks, remove_clicks, nova_categoria, categorias_remover)

@app.callback(
    [Output("select_despesa", "options"),
     Output('checklist-selected-style-despesa', 'options')],
    [Input("add-category-despesa", "n_clicks"),
     Input("remove-category-despesa", 'n_clicks')],
    [State("input-add-despesa", "value"),
     State('checklist-selected-style-despesa', 'value')],
    prevent_initial_call=True
)
def manage_despesa_categories(add_clicks, remove_clicks, nova_categoria, categorias_remover):
    """Gerencia categorias de despesa (adicionar/remover)."""
    return manage_categories('despesa', add_clicks, remove_clicks, nova_categoria, categorias_remover)

def manage_categories(tipo, add_clicks, remove_clicks, nova_categoria, categorias_remover):
    """Função genérica para gerenciar categorias."""
    # Adicionar nova categoria
    if add_clicks and nova_categoria:
        conn = conectar_bd()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO categorias (nome, tipo) VALUES (?, ?)", 
                          (nova_categoria.strip(), tipo))
            conn.commit()
        except Exception as e:
            print(f"❌ Erro ao adicionar categoria: {e}")
        finally:
            conn.close()
    
    # Remover categorias selecionadas
    if remove_clicks and categorias_remover:
        conn = conectar_bd()
        cursor = conn.cursor()
        try:
            placeholders = ', '.join('?' for _ in categorias_remover)
            cursor.execute(f"DELETE FROM categorias WHERE nome IN ({placeholders}) AND tipo = ?", 
                          categorias_remover + [tipo])
            conn.commit()
        except Exception as e:
            print(f"❌ Erro ao remover categorias: {e}")
        finally:
            conn.close()
    
    # Atualiza a lista de categorias
    categorias_receita, categorias_despesa = ler_categorias()
    categorias = categorias_receita if tipo == 'receita' else categorias_despesa
    options = [{'label': cat, 'value': cat} for cat in categorias]
    
    return options, options

# CALLBACK: Nova frase motivacional
@app.callback(
    Output('frase-motivacional', 'children'),
    Input('btn-nova-frase', 'n_clicks'),
    prevent_initial_call=True
)
def update_frase_motivacional(n_clicks):
    """Atualiza a frase motivacional quando o botão é clicado."""
    if n_clicks:
        return get_frase_motivacional()
    return dash.no_update