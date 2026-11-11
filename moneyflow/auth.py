"""
Autenticação baseada em sessão assinada no servidor.

O modelo anterior guardava ``{"logged_in": True, "user_id": N}`` num
``dcc.Store``, ou seja, no sessionStorage do navegador — e confiava nesse
valor para liberar o acesso. Qualquer pessoa podia abrir o console do
navegador, escrever esse objeto e entrar como qualquer usuário.

Agora a identidade vive num cookie assinado com a SECRET_KEY. O navegador
consegue apagá-lo, mas não forjá-lo. Todo callback que lê ou escreve dados
obtém o id através de :func:`current_user_id`, nunca de um valor vindo do
cliente.
"""

from __future__ import annotations

from flask_login import LoginManager, current_user

from moneyflow.app import server
from moneyflow.models import User
from moneyflow.repositories import users

login_manager = LoginManager()
login_manager.init_app(server)
# "strong" invalida a sessão quando o navegador de origem muda, dificultando
# o reuso de um cookie roubado.
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Recarrega o usuário a cada requisição a partir do id no cookie."""
    return users.get_by_id(user_id)


def current_user_id() -> int | None:
    """
    Devolve o id do usuário autenticado, ou ``None``.

    Esta é a única fonte de identidade aceita pelos callbacks.
    """
    if not current_user or not current_user.is_authenticated:
        return None
    return int(current_user.id)


def current_username() -> str:
    """Nome do usuário autenticado, para exibição na interface."""
    if not current_user or not current_user.is_authenticated:
        return ""
    return current_user.username


def is_authenticated() -> bool:
    """Indica se há um usuário autenticado na requisição atual."""
    return bool(current_user and current_user.is_authenticated)
