"""Testes de cadastro e autenticação."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import select

from moneyflow.database import session_scope
from moneyflow.models import Category, User
from moneyflow.repositories import users
from moneyflow.security import build_legacy_hash


def test_cadastro_cria_usuario_e_categorias_padrao(user_factory):
    user_id = user_factory("joana")

    with session_scope() as session:
        categories = session.scalars(
            select(Category).where(Category.user_id == user_id)
        ).all()

    # Um usuário novo já começa com categorias utilizáveis.
    assert len(categories) > 0


def test_nao_permite_username_duplicado():
    users.create_user("repetido", "a@exemplo.com", "senha-segura-123")
    result = users.create_user("repetido", "b@exemplo.com", "senha-segura-123")

    assert not result.success
    assert "já cadastrado" in result.message


def test_username_duplicado_ignora_maiusculas():
    """'Joana' e 'joana' são a mesma conta — senão dá para se passar por outro."""
    users.create_user("Joana", "joana@exemplo.com", "senha-segura-123")
    result = users.create_user("joana", "outra@exemplo.com", "senha-segura-123")

    assert not result.success


def test_autenticacao_com_username_e_com_email(user_factory):
    user_factory("carlos", password="senha-segura-123")

    assert users.authenticate("carlos", "senha-segura-123") is not None
    assert users.authenticate("carlos@exemplo.com", "senha-segura-123") is not None


def test_autenticacao_falha_com_senha_errada(user_factory):
    user_factory("bruno", password="senha-correta-123")

    assert users.authenticate("bruno", "senha-errada") is None


def test_autenticacao_falha_para_usuario_inexistente():
    assert users.authenticate("ninguem", "qualquer-senha") is None


def test_senha_legada_e_convertida_para_bcrypt_no_login():
    """
    Quem tinha conta no sistema antigo continua entrando, e o hash SHA-256 é
    substituído por bcrypt de forma transparente.
    """
    salt = "salt-antigo"
    digest = hashlib.sha256(("senha-antiga" + salt).encode("utf-8")).hexdigest()

    with session_scope() as session:
        session.add(
            User(
                username="veterano",
                email="veterano@exemplo.com",
                password_hash=build_legacy_hash(salt, digest),
            )
        )

    assert users.authenticate("veterano", "senha-antiga") is not None

    with session_scope() as session:
        user = session.scalar(select(User).where(User.username == "veterano"))
        assert not user.password_hash.startswith("sha256$")
        assert user.password_hash.startswith("$2")

    # E o login segue funcionando depois da conversão.
    assert users.authenticate("veterano", "senha-antiga") is not None


def test_usuario_inativo_nao_autentica(user_factory):
    user_id = user_factory("desativado", password="senha-segura-123")

    with session_scope() as session:
        user = session.get(User, user_id)
        user.is_active_flag = False

    assert users.authenticate("desativado", "senha-segura-123") is None


class TestValidacaoDeCadastro:
    def test_rejeita_senha_curta(self):
        erro = users.validate_registration("ana", "ana@exemplo.com", "1234", "1234")
        assert erro is not None and "8 caracteres" in erro

    def test_rejeita_senhas_diferentes(self):
        erro = users.validate_registration(
            "ana", "ana@exemplo.com", "senha-segura-123", "outra-senha-123"
        )
        assert erro is not None and "não coincidem" in erro

    def test_rejeita_email_invalido(self):
        erro = users.validate_registration(
            "ana", "nao-e-email", "senha-segura-123", "senha-segura-123"
        )
        assert erro is not None and "e-mail" in erro

    def test_rejeita_campos_vazios(self):
        assert users.validate_registration("", "", "", "") is not None

    @pytest.mark.parametrize(
        "nome", ["uesley de vargas", "José Conceição", "ana.silva", "user_123"]
    )
    def test_aceita_nomes_reais(self, nome):
        """Nomes com espaço e acento são comuns em português e devem passar."""
        assert (
            users.validate_registration(
                nome, "a@exemplo.com", "senha-segura-123", "senha-segura-123"
            )
            is None
        )

    @pytest.mark.parametrize("nome", ["ab", "usuario<script>", "a" * 51])
    def test_rejeita_nomes_invalidos(self, nome):
        assert (
            users.validate_registration(
                nome, "a@exemplo.com", "senha-segura-123", "senha-segura-123"
            )
            is not None
        )

    def test_aceita_cadastro_valido(self):
        assert (
            users.validate_registration(
                "ana", "ana@exemplo.com", "senha-segura-123", "senha-segura-123"
            )
            is None
        )
