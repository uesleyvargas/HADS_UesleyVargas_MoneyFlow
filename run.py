"""
Servidor de desenvolvimento.

Uso: ``python run.py``

Em produção **não** use este arquivo — o servidor embutido do Flask atende uma
requisição por vez e não foi feito para exposição pública. Use
``gunicorn wsgi:server`` (veja o Dockerfile).
"""

from moneyflow.config import settings
from moneyflow.index import app

if __name__ == "__main__":
    print(f"MoneyFlow rodando em http://{settings.host}:{settings.port}")
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
