"""
Importa os dados do banco antigo (``financas.db``) para o esquema novo.

Uso::

    python scripts/migrate_legacy.py --source financas.db
    python scripts/migrate_legacy.py --source financas.db --dry-run

O que acontece com cada coisa:

* **Usuários** — as senhas não podem ser reconvertidas (hash é via de mão
  única), então o hash SHA-256 antigo é preservado no formato
  ``sha256$salt$digest``. O login continua funcionando normalmente e, no
  primeiro acesso bem-sucedido, a senha é regravada em bcrypt automaticamente.
* **Categorias** — eram globais. Cada usuário recebe a sua própria cópia, que
  passa a ser dele.
* **Transações** — o nome da categoria vira uma chave estrangeira de verdade,
  e o valor em ponto flutuante vira ``Decimal``.

O script é idempotente: rodar duas vezes não duplica nada.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Permite executar o script direto da raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from moneyflow.database import session_scope  # noqa: E402
from moneyflow.models import Category, Transaction, TransactionType, User  # noqa: E402
from moneyflow.security import build_legacy_hash  # noqa: E402


def _connect_legacy(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _parse_type(raw: str) -> TransactionType | None:
    value = (raw or "").strip().lower()
    if value == "receita":
        return TransactionType.RECEITA
    if value == "despesa":
        return TransactionType.DESPESA
    return None


def _parse_date(raw):
    """Aceita os formatos de data que o banco antigo pode ter gravado."""
    if raw is None:
        return None
    if isinstance(raw, (datetime,)):
        return raw.date()
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
    return None


def migrate(source: Path, dry_run: bool = False) -> None:
    """Executa a importação."""
    if not source.exists():
        raise SystemExit(f"Banco de origem não encontrado: {source}")

    legacy = _connect_legacy(source)

    stats = {"usuarios": 0, "categorias": 0, "transacoes": 0, "ignoradas": 0}

    with session_scope() as session:
        # ------------------------------------------------------------------ #
        # Usuários
        # ------------------------------------------------------------------ #
        # Mapeia id antigo -> id novo, para religar as transações depois.
        id_map: dict[int, int] = {}

        for row in legacy.execute("SELECT * FROM usuarios"):
            username = (row["username"] or "").strip()
            email = (row["email"] or "").strip().lower()
            if not username or not email:
                continue

            existing = session.scalar(select(User).where(User.username == username))
            if existing is not None:
                id_map[row["id"]] = existing.id
                continue

            user = User(
                username=username,
                email=email,
                password_hash=build_legacy_hash(
                    row["salt"] or "", row["password_hash"] or ""
                ),
                is_active_flag=bool(row["ativo"]) if row["ativo"] is not None else True,
                created_at=datetime.now(UTC),
            )
            session.add(user)
            session.flush()
            id_map[row["id"]] = user.id
            stats["usuarios"] += 1

        if not id_map:
            print("Nenhum usuário encontrado no banco antigo. Nada a importar.")
            return

        # ------------------------------------------------------------------ #
        # Categorias — de globais para privadas de cada usuário
        # ------------------------------------------------------------------ #
        legacy_categories = [
            (row["nome"], _parse_type(row["tipo"]))
            for row in legacy.execute("SELECT nome, tipo FROM categorias")
        ]

        # (user_id, nome_minusculo, tipo) -> objeto Category
        category_index: dict[tuple[int, str, TransactionType], Category] = {}

        for new_user_id in id_map.values():
            for name, type_ in legacy_categories:
                if not name or type_ is None:
                    continue
                key = (new_user_id, name.strip().lower(), type_)
                if key in category_index:
                    continue

                existing = session.scalar(
                    select(Category).where(
                        Category.user_id == new_user_id,
                        Category.name == name.strip(),
                        Category.type == type_,
                    )
                )
                if existing is None:
                    existing = Category(
                        name=name.strip(), type=type_, user_id=new_user_id
                    )
                    session.add(existing)
                    session.flush()
                    stats["categorias"] += 1

                category_index[key] = existing

        # ------------------------------------------------------------------ #
        # Transações
        # ------------------------------------------------------------------ #
        for row in legacy.execute("SELECT * FROM transacoes"):
            legacy_user_id = row["usuario_id"]
            new_user_id = id_map.get(legacy_user_id)
            type_ = _parse_type(row["tipo"])
            transaction_date = _parse_date(row["data"])

            # Registros órfãos (sem usuário, sem tipo ou sem data válida) não
            # têm como ser atribuídos com segurança — são relatados, não
            # adivinhados.
            if new_user_id is None or type_ is None or transaction_date is None:
                stats["ignoradas"] += 1
                continue

            category_name = (row["categoria"] or "Sem categoria").strip()
            key = (new_user_id, category_name.lower(), type_)
            category = category_index.get(key)
            if category is None:
                category = Category(
                    name=category_name, type=type_, user_id=new_user_id
                )
                session.add(category)
                session.flush()
                category_index[key] = category
                stats["categorias"] += 1

            already_exists = session.scalar(
                select(Transaction).where(
                    Transaction.user_id == new_user_id,
                    Transaction.date == transaction_date,
                    Transaction.amount == Decimal(str(row["valor"])).quantize(
                        Decimal("0.01")
                    ),
                    Transaction.description == (row["descricao"] or None),
                    Transaction.category_id == category.id,
                )
            )
            if already_exists is not None:
                continue

            session.add(
                Transaction(
                    type=type_,
                    description=(row["descricao"] or None),
                    # str() antes de Decimal evita herdar o erro do float.
                    amount=Decimal(str(row["valor"])).quantize(Decimal("0.01")),
                    date=transaction_date,
                    is_settled=bool(row["efetuado"]),
                    is_recurring=bool(row["fixo"]),
                    user_id=new_user_id,
                    category_id=category.id,
                )
            )
            stats["transacoes"] += 1

        if dry_run:
            print("[simulação] Nada foi gravado.")
            session.rollback()

    legacy.close()

    print("\nImportação concluída:")
    print(f"  usuários novos ..... {stats['usuarios']}")
    print(f"  categorias criadas . {stats['categorias']}")
    print(f"  transações ......... {stats['transacoes']}")
    if stats["ignoradas"]:
        print(f"  ignoradas .......... {stats['ignoradas']} (sem usuário/tipo/data válidos)")
    print(
        "\nAs senhas antigas continuam válidas e serão convertidas para bcrypt "
        "no próximo login de cada usuário."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("financas.db"),
        help="caminho do banco antigo (padrão: financas.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="simula a importação sem gravar nada",
    )
    args = parser.parse_args()
    migrate(args.source, args.dry_run)


if __name__ == "__main__":
    main()
