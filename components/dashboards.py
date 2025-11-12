"""
Componente responsável pelos dashboards e gráficos do aplicativo MyFinance.
Exibe cards com resumos financeiros e gráficos interativos para análise de dados.
"""

from dash import html, dcc
from dash.dependencies import Input, Output, State
from datetime import date, datetime, timedelta
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar
from app import app

# --- Estilos ---
card_icon = {
    "color": "white",
    "textAlign": "center",
    "fontSize": 30,
    "margin": "auto",
}

graph_margin = dict(l=25, r=25, t=25, b=0)

# --- Layout Principal ---
layout = dbc.Col([
    dbc.Row([
        # Saldo
        dbc.Col([
            dbc.CardGroup([
                dbc.Card([
                    html.Legend("Saldo"),
                    html.H5("R$ -", id="p-saldo-dashboards", style={}),
                ], style={"padding-left": "20px", "padding-top": "10px"}),
                dbc.Card(
                    html.Div(className="fa fa-university", style=card_icon), 
                    color="warning",
                    style={"maxWidth": 75, "height": 100, "margin-left": "-10px"},
                )])
        ], width=4),
        # Receita
        dbc.Col([
            dbc.CardGroup([
                dbc.Card([
                    html.Legend("Receita"),
                    html.H5("R$ -", id="p-receita-dashboards"),
                ], style={"padding-left": "20px", "padding-top": "10px"}),
                dbc.Card(
                    html.Div(className="fa fa-smile-o", style=card_icon), 
                    color="success",
                    style={"maxWidth": 75, "height": 100, "margin-left": "-10px"},
                )])
        ], width=4),
        # Despesa
        dbc.Col([
            dbc.CardGroup([
                dbc.Card([
                    html.Legend("Despesas"),
                    html.H5("R$ -", id="p-despesa-dashboards"),
                ], style={"padding-left": "20px", "padding-top": "10px"}),
                dbc.Card(
                    html.Div(className="fa fa-meh-o", style=card_icon), 
                    color="danger",
                    style={"maxWidth": 75, "height": 100, "margin-left": "-10px"},
                )])
            ], width=4),
    ], style={"margin": "10px"}),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                html.Legend("Filtrar lançamentos", className="card-title"),
                html.Label("Categorias das receitas"),
                dcc.Dropdown(
                    id="dropdown-receita", clearable=False, style={"width": "100%"},
                    persistence=True, persistence_type="session", multi=True
                ),
                html.Label("Categorias das despesas", style={"margin-top": "10px"}),
                dcc.Dropdown(
                    id="dropdown-despesa", clearable=False, style={"width": "100%"},
                    persistence=True, persistence_type="session", multi=True
                ),
                html.Legend("Período de Análise", style={"margin-top": "10px"}),
                dcc.DatePickerRange(
                    id='date-picker-config', month_format='Do MMM, YY',
                    end_date_placeholder_text='Data...',
                    start_date=datetime.now().date() - timedelta(days=30),
                    end_date=datetime.now().date(),
                    style={'z-index': '100'}
                )
            ], style={"height": "100%", "padding": "20px"}), 
        ], width=4),
        dbc.Col(dbc.Card(dcc.Graph(id="graph1"), style={"height": "100%", "padding": "10px"}), width=8),
    ], style={"margin": "10px"}),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id="graph2"), style={"padding": "10px"}), width=6),
        dbc.Col(dbc.Card(dcc.Graph(id="graph3"), style={"padding": "10px"}), width=3),
        dbc.Col(dbc.Card(dcc.Graph(id="graph4"), style={"padding": "10px"}), width=3),
    ], style={"margin": "10px"})
])

# --- Callbacks ---

# Callbacks dos Cards (Receita, Despesa, Saldo)
@app.callback(
    [Output("dropdown-receita", "options"), Output("dropdown-receita", "value"), Output("p-receita-dashboards", "children")],
    Input("store-receitas", "data")
)
def update_receitas_cards(data):
    """
    Atualiza o dropdown de receitas e o card de total de receitas.
    
    """
    if not data: return [], [], "R$ 0.00"
    df = pd.DataFrame(data)
    valor = df['Valor'].sum()
    categorias = df['Categoria'].unique().tolist()
    options = [{"label": cat, "value": cat} for cat in categorias]
    return options, categorias, f"R$ {valor:.2f}"

@app.callback(
    [Output("dropdown-despesa", "options"), Output("dropdown-despesa", "value"), Output("p-despesa-dashboards", "children")],
    Input("store-despesas", "data")
)
def update_despesas_cards(data):
    if not data: return [], [], "R$ 0.00"
    df = pd.DataFrame(data)
    valor = df['Valor'].sum()
    categorias = df['Categoria'].unique().tolist()
    options = [{"label": cat, "value": cat} for cat in categorias]
    return options, categorias, f"R$ {valor:.2f}"

@app.callback(
    Output("p-saldo-dashboards", "children"),
    [Input("store-receitas", "data"), Input("store-despesas", "data")]
)
def update_saldo_total(receitas_data, despesas_data):
    total_receitas = pd.DataFrame(receitas_data)['Valor'].sum() if receitas_data else 0
    total_despesas = pd.DataFrame(despesas_data)['Valor'].sum() if despesas_data else 0
    saldo = total_receitas - total_despesas
    return f"R$ {saldo:.2f}"

# Gráfico 1: Fluxo de Caixa
@app.callback(
    Output('graph1', 'figure'),
    [input('store-receitas', 'data'), input('store-despesas', 'data'),
     input("dropdown-receitas", "value"), input("dropdown-despesas", "value")]
)
def update_graph1(data_receita, data_despesa, receita_selecionada, despesa_selecionada):

    # Garante que os seletores não sejam None para o filtro
    receita_selecionada = receita_selecionada or []
    despesa_selecionada = despesa_selecionada or []

    # Cria DataFrames vazios com colunas se não houver dados
    df_receitas = pd.DataFrame(data_receita) if data_receita else pd.DataFrame({'Categoria': [], 'Data': [], 'Valor': []})
    df_despesas = pd.DataFrame(data_despesa) if data_despesa else pd.DataFrame({'Categoria': [], 'Data': [], 'Valor': []})

    # Filtra pelos valores selecionados nos dropdowns
    df_receitas = df_receitas[df_receitas['Categoria'].isin(receita_selecionada)]
    df_despesas = df_despesas[df_despesas['Categoria'].isin(despesa_selecionada)] 

    #Agrupa os Dados
    df_rc = df_receitas.set_index("Data")[["Valor"]].groupby("Data").sum().rename(columns={"Valor": "Receita"}) if not df_receitas.empty else pd.DataFrame()
    df_ds = df_despesas.set_index("Data")[["Valor"]].groupby("Data").sum().rename(columns={"Valor": "Despesa"}) if not df_despesas.empty else pd.DataFrame()

    # Junta os dois dataFrames
    df_acum = df_rc.join(df_ds, how="outer").fillna(0)

    # Garante que ambas as colunas 'Receita' e 'Despesa' existam após o join
    if 'Receita' not in df_acum:
        df_acum['Receita'] = 0
    if 'Despesa' not in df_acum:
        df_acum['Despesa'] = 0
    
    
    df_acum["Acum"] = (df_acum["Receita"] - df_acum["Despesa"]).cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(name="Fluxo de caixa", x=df_acum.index, y=df_acum["Acum"], mode="lines"))
    fig.update_layout(margin=graph_margin, height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig