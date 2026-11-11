"""
Operações de lançamentos financeiros.

Todas as consultas recebem ``user_id`` e filtram por ele. Não existe caminho
neste módulo que devolva dados de um usuário para outro.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from moneyflow.database import session_scope
from moneyflow.models import Transaction, TransactionType
from moneyflow.repositories.categories import get_or_create

# Esquema único do DataFrame consumido pela interface. Centralizado aqui para
# que gráficos e tabelas nunca divirjam sobre os nomes das colunas.
COLUMNS = ["id", "Data", "Valor", "Categoria", "Descrição", "Efetuado", "Fixo", "Tipo"]

MAX_AMOUNT = Decimal("99999999.99")


@dataclass(frozen=True)
class TransactionResult:
    """Resultado de uma operação de escrita em lançamentos."""

    success: bool
    message: str
    transaction_id: int | None = None


def _empty_frame() -> pd.DataFrame:
    """DataFrame vazio, mas com as colunas certas.

    Sem isso, a interface quebraria ao acessar ``df['Valor']`` de um usuário
    que ainda não tem lançamentos.
    """
    return pd.DataFrame({column: pd.Series(dtype="object") for column in COLUMNS})


def parse_amount(raw: object) -> Decimal | None:
    """
    Converte a entrada do formulário em ``Decimal``.

    Aceita o formato brasileiro ("1.234,56") e o americano ("1234.56").
    Retorna ``None`` se não for um número válido e positivo.
    """
    if raw is None or raw == "":
        return None

    if isinstance(raw, (int, float, Decimal)):
        text = str(raw)
    else:
        text = str(raw).strip().replace("R$", "").strip()
        if "," in text:
            # "1.234,56" -> "1234.56"
            text = text.replace(".", "").replace(",", ".")

    try:
        amount = Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None

    if amount <= 0 or amount > MAX_AMOUNT:
        return None
    return amount


def create(
    user_id: int,
    type_: TransactionType,
    description: str | None,
    amount: object,
    transaction_date: date | str | None,
    category_name: str | None,
    is_settled: bool,
    is_recurring: bool,
) -> TransactionResult:
    """Cria um lançamento após validar todos os campos."""
    parsed_amount = parse_amount(amount)
    if parsed_amount is None:
        return TransactionResult(False, "Informe um valor válido, maior que zero.")

    if not category_name:
        return TransactionResult(False, "Selecione uma categoria.")

    parsed_date = _coerce_date(transaction_date)
    if parsed_date is None:
        return TransactionResult(False, "Informe uma data válida.")

    description = (description or "").strip()[:255] or None

    with session_scope() as session:
        category = get_or_create(session, user_id, category_name, type_)
        transaction = Transaction(
            type=type_,
            description=description,
            amount=parsed_amount,
            date=parsed_date,
            is_settled=is_settled,
            is_recurring=is_recurring,
            user_id=user_id,
            category_id=category.id,
        )
        session.add(transaction)
        session.flush()

        label = "Receita" if type_ is TransactionType.RECEITA else "Despesa"
        return TransactionResult(True, f"{label} salva com sucesso.", transaction.id)


def update(
    user_id: int,
    transaction_id: int,
    *,
    description: str | None = None,
    amount: object = None,
    transaction_date: date | str | None = None,
    category_name: str | None = None,
    is_settled: bool | None = None,
    is_recurring: bool | None = None,
) -> TransactionResult:
    """
    Atualiza um lançamento existente.

    O filtro por ``user_id`` no SELECT é o que impede um usuário de editar o
    lançamento de outro passando um id qualquer.
    """
    with session_scope() as session:
        transaction = session.scalar(
            select(Transaction).where(
                Transaction.id == transaction_id, Transaction.user_id == user_id
            )
        )
        if transaction is None:
            return TransactionResult(False, "Lançamento não encontrado.")

        if amount is not None:
            parsed_amount = parse_amount(amount)
            if parsed_amount is None:
                return TransactionResult(False, "Informe um valor válido.")
            transaction.amount = parsed_amount

        if transaction_date is not None:
            parsed_date = _coerce_date(transaction_date)
            if parsed_date is None:
                return TransactionResult(False, "Informe uma data válida.")
            transaction.date = parsed_date

        if category_name:
            category = get_or_create(session, user_id, category_name, transaction.type)
            transaction.category_id = category.id

        if description is not None:
            transaction.description = description.strip()[:255] or None
        if is_settled is not None:
            transaction.is_settled = is_settled
        if is_recurring is not None:
            transaction.is_recurring = is_recurring

        return TransactionResult(True, "Lançamento atualizado.", transaction.id)


def delete(user_id: int, transaction_id: int) -> TransactionResult:
    """Exclui um lançamento do usuário."""
    with session_scope() as session:
        transaction = session.scalar(
            select(Transaction).where(
                Transaction.id == transaction_id, Transaction.user_id == user_id
            )
        )
        if transaction is None:
            return TransactionResult(False, "Lançamento não encontrado.")

        session.delete(transaction)
        return TransactionResult(True, "Lançamento excluído.")


def list_as_frame(
    user_id: int,
    type_: TransactionType,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> pd.DataFrame:
    """
    Retorna os lançamentos do usuário como DataFrame.

    O filtro de datas é aplicado no banco, não em memória: com o passar dos
    anos, carregar todo o histórico só para descartar quase tudo no pandas
    fica caro.
    """
    with session_scope() as session:
        statement = (
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(Transaction.user_id == user_id, Transaction.type == type_)
            .order_by(Transaction.date.desc())
        )

        parsed_start = _coerce_date(start_date)
        parsed_end = _coerce_date(end_date)
        if parsed_start is not None:
            statement = statement.where(Transaction.date >= parsed_start)
        if parsed_end is not None:
            statement = statement.where(Transaction.date <= parsed_end)

        rows = list(session.scalars(statement))

        if not rows:
            return _empty_frame()

        return pd.DataFrame(
            [
                {
                    "id": row.id,
                    "Data": row.date,
                    # Decimal é exato no banco, mas os gráficos precisam de
                    # float. A conversão acontece só aqui, na saída.
                    "Valor": float(row.amount),
                    "Categoria": row.category.name,
                    "Descrição": row.description or "—",
                    "Efetuado": bool(row.is_settled),
                    "Fixo": bool(row.is_recurring),
                    "Tipo": row.type.value,
                }
                for row in rows
            ],
            columns=COLUMNS,
        )


def load_dashboard_data(user_id: int) -> tuple[list[dict], list[dict]]:
    """Carrega receitas e despesas no formato usado pelos ``dcc.Store``."""
    incomes = list_as_frame(user_id, TransactionType.RECEITA)
    expenses = list_as_frame(user_id, TransactionType.DESPESA)
    return _frame_to_records(incomes), _frame_to_records(expenses)


def _frame_to_records(frame: pd.DataFrame) -> list[dict]:
    """Serializa o DataFrame para JSON, com datas em ISO."""
    if frame.empty:
        return []
    serializable = frame.copy()
    serializable["Data"] = pd.to_datetime(serializable["Data"]).dt.strftime("%Y-%m-%d")
    return serializable.to_dict("records")


def _coerce_date(value: date | str | None) -> date | None:
    """Converte string ISO ou datetime em ``date``, tolerando valor ausente."""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except (ValueError, TypeError):
        return None
