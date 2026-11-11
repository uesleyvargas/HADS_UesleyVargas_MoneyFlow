"""
Operações de categoria.

Toda função exige ``user_id``: categorias são privadas de cada usuário. Na
versão anterior a tabela era global e um usuário conseguia apagar as
categorias de todos os outros.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from moneyflow.config import settings
from moneyflow.database import session_scope
from moneyflow.models import Category, Transaction, TransactionType


@dataclass(frozen=True)
class CategoryOperationResult:
    """Resultado de uma alteração em categorias."""

    success: bool
    message: str


def seed_default_categories(session: Session, user_id: int) -> None:
    """
    Cria as categorias iniciais de um usuário novo.

    Recebe a sessão de fora para participar da mesma transação do cadastro:
    ou o usuário e suas categorias são criados juntos, ou nada é criado.
    """
    defaults = [
        (name, TransactionType.RECEITA) for name in settings.default_income_categories
    ] + [
        (name, TransactionType.DESPESA) for name in settings.default_expense_categories
    ]

    session.add_all(
        Category(name=name, type=type_, user_id=user_id) for name, type_ in defaults
    )


def list_names(user_id: int, type_: TransactionType) -> list[str]:
    """Lista os nomes das categorias do usuário, em ordem alfabética."""
    with session_scope() as session:
        return list(
            session.scalars(
                select(Category.name)
                .where(Category.user_id == user_id, Category.type == type_)
                .order_by(Category.name)
            )
        )


def list_options(user_id: int, type_: TransactionType) -> list[dict[str, str]]:
    """Lista as categorias no formato de opções dos componentes do Dash."""
    return [{"label": name, "value": name} for name in list_names(user_id, type_)]


def add(user_id: int, name: str, type_: TransactionType) -> CategoryOperationResult:
    """Adiciona uma categoria para o usuário."""
    name = (name or "").strip()

    if not name:
        return CategoryOperationResult(False, "Informe o nome da categoria.")
    if len(name) > 60:
        return CategoryOperationResult(False, "O nome deve ter no máximo 60 caracteres.")

    with session_scope() as session:
        exists = session.scalar(
            select(Category).where(
                Category.user_id == user_id,
                Category.type == type_,
                func.lower(Category.name) == name.lower(),
            )
        )
        if exists is not None:
            return CategoryOperationResult(False, f"A categoria “{name}” já existe.")

        session.add(Category(name=name, type=type_, user_id=user_id))
        return CategoryOperationResult(True, f"Categoria “{name}” adicionada.")


def remove(
    user_id: int, names: list[str], type_: TransactionType
) -> CategoryOperationResult:
    """
    Remove categorias do usuário.

    Categorias com lançamentos vinculados não são removidas — apagá-las
    deixaria transações órfãs e distorceria os relatórios históricos.
    """
    if not names:
        return CategoryOperationResult(False, "Selecione ao menos uma categoria.")

    with session_scope() as session:
        categories = list(
            session.scalars(
                select(Category).where(
                    Category.user_id == user_id,
                    Category.type == type_,
                    Category.name.in_(names),
                )
            )
        )

        removed: list[str] = []
        blocked: list[str] = []

        for category in categories:
            in_use = session.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(Transaction.category_id == category.id)
            )
            if in_use:
                blocked.append(category.name)
            else:
                session.delete(category)
                removed.append(category.name)

        if not removed and blocked:
            return CategoryOperationResult(
                False,
                "Não foi possível remover: "
                f"{', '.join(blocked)} possui lançamentos vinculados.",
            )

        message = f"{len(removed)} categoria(s) removida(s)."
        if blocked:
            message += f" Mantidas por terem lançamentos: {', '.join(blocked)}."
        return CategoryOperationResult(True, message)


def get_or_create(session: Session, user_id: int, name: str, type_: TransactionType) -> Category:
    """
    Busca a categoria pelo nome, criando-a se não existir.

    Usado ao salvar um lançamento, para que a interface trabalhe com nomes
    enquanto o banco mantém a integridade referencial por id.
    """
    category = session.scalar(
        select(Category).where(
            Category.user_id == user_id,
            Category.type == type_,
            func.lower(Category.name) == name.strip().lower(),
        )
    )
    if category is None:
        category = Category(name=name.strip(), type=type_, user_id=user_id)
        session.add(category)
        session.flush()
    return category
