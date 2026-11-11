"""Operações de usuário: cadastro, autenticação e consulta."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from moneyflow.config import settings
from moneyflow.database import session_scope
from moneyflow.models import User
from moneyflow.repositories.categories import seed_default_categories
from moneyflow.security import hash_password, needs_rehash, verify_password

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
# `\w` em Unicode cobre letras acentuadas — "José" e "Conceição" precisam ser
# nomes válidos. Espaço interno é permitido (nomes completos são comuns), mas
# as pontas são removidas antes da validação.
USERNAME_PATTERN = re.compile(r"^[\w.\- ]{3,50}$", re.UNICODE)


@dataclass(frozen=True)
class RegistrationResult:
    """Resultado de uma tentativa de cadastro."""

    success: bool
    message: str
    user_id: int | None = None


def validate_registration(
    username: str, email: str, password: str, confirm_password: str
) -> str | None:
    """
    Valida os dados de cadastro.

    Retorna a mensagem de erro, ou ``None`` se estiver tudo certo.
    """
    if not all([username, email, password, confirm_password]):
        return "Preencha todos os campos."

    if not USERNAME_PATTERN.match(username.strip()):
        return (
            "O nome de usuário deve ter de 3 a 50 caracteres e conter apenas "
            "letras, números, espaço, ponto, hífen ou underscore."
        )

    if not EMAIL_PATTERN.match(email):
        return "Informe um e-mail válido."

    if password != confirm_password:
        return "As senhas não coincidem."

    if len(password) < settings.min_password_length:
        return f"A senha deve ter pelo menos {settings.min_password_length} caracteres."

    if password.lower() in {"12345678", "senha123", "password"}:
        return "Essa senha é fácil demais de adivinhar. Escolha outra."

    return None


def create_user(username: str, email: str, password: str) -> RegistrationResult:
    """Cria um usuário e já semeia as categorias padrão dele."""
    username = username.strip()
    email = email.strip().lower()

    try:
        with session_scope() as session:
            # Comparação case-insensitive: "Uesley" e "uesley" são o mesmo login.
            existing = session.scalar(
                select(User).where(
                    (func.lower(User.username) == username.lower())
                    | (func.lower(User.email) == email)
                )
            )
            if existing is not None:
                return RegistrationResult(False, "Usuário ou e-mail já cadastrado.")

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
            )
            session.add(user)
            session.flush()  # atribui o id sem encerrar a transação

            seed_default_categories(session, user.id)

            return RegistrationResult(
                True,
                f"Conta criada com sucesso. Bem-vindo(a) ao MoneyFlow, {username}!",
                user.id,
            )
    except IntegrityError:
        # Corrida entre dois cadastros simultâneos: o índice único no banco é
        # a garantia final, a checagem acima é só para dar mensagem melhor.
        return RegistrationResult(False, "Usuário ou e-mail já cadastrado.")


def authenticate(identifier: str, password: str) -> User | None:
    """
    Autentica por nome de usuário ou e-mail.

    Retorna o usuário, ou ``None`` se as credenciais forem inválidas.
    Atualiza o hash para bcrypt se ele ainda estiver no formato antigo.
    """
    if not identifier or not password:
        return None

    identifier = identifier.strip().lower()

    with session_scope() as session:
        user = session.scalar(
            select(User).where(
                (func.lower(User.username) == identifier)
                | (func.lower(User.email) == identifier),
                User.is_active_flag.is_(True),
            )
        )

        if user is None or not verify_password(password, user.password_hash):
            return None

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        user.last_login_at = datetime.now(UTC)
        session.flush()
        return user


def get_by_id(user_id: int | str) -> User | None:
    """Busca um usuário ativo pelo id. Usado pelo user_loader do Flask-Login."""
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    with session_scope() as session:
        return session.scalar(
            select(User).where(User.id == user_id, User.is_active_flag.is_(True))
        )
