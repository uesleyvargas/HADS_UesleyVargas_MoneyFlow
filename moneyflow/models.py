"""
Modelos ORM da aplicação.

Regras estruturais importantes:

* Valores monetários usam ``Numeric(12, 2)``, nunca ``Float``. Ponto flutuante
  binário não representa 0,10 exatamente e os erros se acumulam nas somas —
  inaceitável num sistema financeiro.
* Toda tabela de dados carrega ``user_id`` com ``ondelete="CASCADE"``: o
  isolamento entre usuários é garantido pelo próprio esquema, não só pelo
  código da aplicação.
* Categorias pertencem a um usuário. Na versão anterior eram globais, então
  qualquer pessoa podia apagar as categorias de todo mundo.
"""

from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os modelos."""


class TransactionType(enum.StrEnum):
    """
    Natureza de um lançamento financeiro.

    ``StrEnum`` faz os membros se comportarem como as strings "receita" e
    "despesa", o que mantém a compatibilidade com os dados já gravados.
    """

    RECEITA = "receita"
    DESPESA = "despesa"


def _utcnow() -> datetime:
    """Timestamp com fuso explícito — `utcnow()` gera datetimes ingênuos."""
    return datetime.now(UTC)


class User(Base, UserMixin):
    """Usuário da aplicação."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active_flag: Mapped[bool] = mapped_column(
        "is_active", Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    categories: Mapped[list[Category]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        """Flask-Login usa esta propriedade para bloquear contas desativadas."""
        return self.is_active_flag

    def __repr__(self) -> str:  # pragma: no cover - only for debugging
        return f"<User id={self.id} username={self.username!r}>"


class Category(Base):
    """Categoria de receita ou despesa, própria de cada usuário."""

    __tablename__ = "categories"
    __table_args__ = (
        # Um usuário pode ter "Transporte" como receita e como despesa,
        # mas não duas despesas com o mesmo nome.
        UniqueConstraint("user_id", "name", "type", name="uq_category_user_name_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user: Mapped[User] = relationship(back_populates="categories")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover - only for debugging
        return f"<Category id={self.id} name={self.name!r} type={self.type.value}>"


class Transaction(Base):
    """Lançamento financeiro — uma receita ou uma despesa."""

    __tablename__ = "transactions"
    __table_args__ = (
        # Os dashboards sempre filtram por usuário e período; este índice
        # composto cobre exatamente esse padrão de consulta.
        Index("ix_transaction_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # "efetuado": a receita já caiu na conta / a despesa já foi paga.
    is_settled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # "fixo": lançamento recorrente (aluguel, salário...).
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    user: Mapped[User] = relationship(back_populates="transactions")
    category: Mapped[Category] = relationship(back_populates="transactions")

    def __repr__(self) -> str:  # pragma: no cover - only for debugging
        return f"<Transaction id={self.id} type={self.type.value} amount={self.amount}>"
