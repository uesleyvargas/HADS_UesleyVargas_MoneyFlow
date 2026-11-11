"""
Ponto de entrada WSGI para servidores de produção.

Uso: ``gunicorn wsgi:server``

Importar ``moneyflow.index`` registra o layout e todos os callbacks; ``server``
é a aplicação Flask que o Dash usa por baixo.
"""

from moneyflow.app import server
from moneyflow.index import app  # noqa: F401  (registra layout e callbacks)

__all__ = ["server"]
