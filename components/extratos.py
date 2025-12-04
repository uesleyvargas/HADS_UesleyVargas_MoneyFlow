"""
Componente responsável pela exibição de extratos e relatórios detalhados
das transações financeiras do aplicativo.
"""

import dash
from dash.dependencies import Input, Output
from dash import dash_table
from dash.dash_table.Format import Group
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

from app import app

# =========  Layout  =========== #
layout = dbc.Col([
    dbc.Row([
        html.Legend("Tabela de despesas"),
        html.Div(id="tabela-despesas", className="dbc"),
    ]),
    
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='bar-graph', style={"margin-right": "20px"}),
        ], width=9),
        
        dbc.Col([
            dbc.Card(
                dbc.CardBody([
                    html.H4("Despesas"),
                    html.Legend("R$ -", id="valor_despesa_card", style={'font-size': '60px'}),
                    html.H6("Total de despesas"),
                ], style={'text-align': 'center', 'padding-top': '30px'}))
        ], width=3),
    ]),
], style={"padding": "10px"})

# --- Callbacks ---

# Tabela
@app.callback(
    Output('tabela-despesas', 'children'),
    Input('store-despesas', 'data')
)
def imprimir_tabela(data):
    """
    Gera e exibe a tabela de despesas com os dados mais recentes.
    
    """
    if not data:
        return html.Div("Nenhuma despesa encontrada.")
    
    df = pd.DataFrame(data)
    df['Data'] = pd.to_datetime(df['Data']).dt.date
    df = df.fillna('-')
    df = df.sort_values(by='Data', ascending=False)

    tabela = dash_table.DataTable(
        data=df.to_dict('records'), 
        columns=[{"name": i, "id": i} for i in df.columns],
        style_cell={'textAlign': 'left'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        page_size=10,
        sort_action="native",
        filter_action="native"
    )

    return tabela

            
@app.callback(
    Output('bar-graph', 'figure'),
    [Input('store-despesas', 'data'),]
)
def bar_chart(data):
    """
    Gera o gráfico de barras das despesas agrupadas por categoria.
   
    """
    if not data:
        fig = px.bar(title="Nenhuma despesa para exibir")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig
    
    df = pd.DataFrame(data)   
    df_grouped = df.groupby("Categoria").sum()[["Valor"]].reset_index()
    graph = px.bar(df_grouped, x='Categoria', y='Valor', title="Despesas por Categoria")
    graph.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return graph

# Simple card
@app.callback(
    Output('valor_despesa_card', 'children'),
    Input('store-despesas', 'data')
)
def display_desp(data):
    """
    Calcula e exibe o total de despesas no card.
   
    """
    if not data:
        return "R$ 0.00"
    
    df = pd.DataFrame(data)
    valor = df['Valor'].sum()
    return f"R$ {valor:.2f}"