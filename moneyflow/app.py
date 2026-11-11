"""
Instância da aplicação Dash e configuração do servidor Flask subjacente.

Este módulo não importa nenhuma página nem componente: são eles que importam
``app`` daqui. Manter a dependência em mão única evita importação circular.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from flask import send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from moneyflow.config import settings

EXTERNAL_STYLESHEETS = [
    dbc.themes.COSMO,
    dbc.icons.FONT_AWESOME,
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css",
]

app = dash.Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    # O layout é montado dinamicamente conforme a rota, então nem todos os
    # ids existem no carregamento inicial.
    suppress_callback_exceptions=True,
    # Marcação responsiva: sem isto o app fica ilegível no celular.
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content": "MoneyFlow — gestão financeira pessoal"},
    ],
    title="MoneyFlow",
    update_title=None,
)

# PWA: manifesto, ícones e registro do service worker. O iOS ignora parte do
# manifesto, por isso as meta tags "apple-*" são necessárias.
app.index_string = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    <link rel="manifest" href="/assets/manifest.webmanifest">
    <link rel="apple-touch-icon" href="/assets/icons/apple-touch-icon.png">
    <meta name="theme-color" content="#008300">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="MoneyFlow">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    {%css%}
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
        <script>
            if ("serviceWorker" in navigator) {
                navigator.serviceWorker.register("/sw.js").catch(function () {});
            }
        </script>
    </footer>
</body>
</html>"""

server = app.server

# Atrás do proxy do provedor (Railway etc.) o Flask só vê HTTP. O ProxyFix lê
# X-Forwarded-* para que esquema e IP do cliente fiquem corretos.
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1, x_host=1)


@server.route("/sw.js")
def service_worker():
    """Serve o service worker na raiz: um SW em /assets/ só controlaria /assets/."""
    resposta = send_from_directory(Path(app.config.assets_folder), "sw.js")
    resposta.headers["Content-Type"] = "application/javascript"
    # O navegador precisa revalidar o SW a cada visita para pegar atualizações.
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta


server.config.update(
    SECRET_KEY=settings.secret_key,
    # Bloqueia o acesso ao cookie de sessão por JavaScript, reduzindo o
    # impacto de um eventual XSS.
    SESSION_COOKIE_HTTPONLY=True,
    # Em produção o cookie só trafega por HTTPS.
    SESSION_COOKIE_SECURE=settings.session_cookie_secure,
    # Mitiga CSRF: o cookie não é enviado em navegações vindas de outros sites.
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=settings.session_lifetime_days),
)
