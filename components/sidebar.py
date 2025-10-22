"""
Componente da barra lateral do aplicativo .
Responsável pela navegação, formulários de transações e upload de foto de perfil.
"""

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
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
UPLOAD_FOLDER = 'assets/profile_pics'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
    html.H1("MyFinance", className="text-primary"),
    html.P("By Uesley", className="text-info"),
    html.Hr(),
    
    # Seção de Perfil com Upload de Foto
    html.Div([
        # Store para manter o estado do avatar
        dcc.Store(id='store-avatar', data={'src': '/assets/img_hom.png'}),
        
        # Container do Avatar com dcc.Upload customizado
        html.Div([
            html.Div([
                # Imagem do Avatar
                html.Img(
                    src='/assets/img_hom.png', 
                    id='avatar_image',
                    alt='Avatar', 
                    className='perfil_avatar'
                ),
                # Overlay com Ícone de Câmera
                html.Div([
                    html.I(className="fa fa-camera")
                ], className='avatar-overlay'),
                
                # dcc.Upload customizado
                dcc.Upload(
                    id='upload_avatar',
                    children=html.Div(),
                    style={
                        'position': 'absolute',
                        'width': '100%',
                        'height': '100%',
                        'top': '0',
                        'left': '0',
                        'opacity': '0',
                        'cursor': 'pointer',
                        'zIndex': '10'
                    },
                    multiple=False
                )
            ], className='avatar-wrapper', style={'position': 'relative'})
        ], style={'textAlign': 'center'}),
        
        # Texto de Ajuda
        html.P("Clique para alterar foto", className="avatar-click-text")
    ], className='avatar-container'),
    
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