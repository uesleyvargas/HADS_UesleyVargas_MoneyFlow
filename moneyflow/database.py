"""
Camada de acesso ao banco de dados.

Centraliza a engine e a fábrica de sessões do SQLAlchemy. Trocar SQLite por
PostgreSQL é só mudar a variável de ambiente DATABASE_URL — nenhuma linha de
código precisa mudar.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from moneyflow.config import settings


def _build_engine() -> Engine:
    """Cria a engine com os parâmetros adequados ao banco em uso."""
    if settings.is_sqlite:
        engine = create_engine(
            settings.database_url,
            # O Dash atende callbacks em várias threads; o SQLite exige
            # este flag para permitir que a conexão cruze threads.
            connect_args={"check_same_thread": False},
            echo=settings.debug and False,
        )

        @event.listens_for(engine, "connect")
        def _enable_sqlite_pragmas(dbapi_connection, _connection_record):
            """SQLite ignora chaves estrangeiras por padrão — precisa ligar."""
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        return engine

    # PostgreSQL e afins: pool com reciclagem para sobreviver a conexões
    # derrubadas por proxies/idle timeout dos provedores de nuvem.
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
    )


engine = _build_engine()

SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Fornece uma sessão transacional.

    Faz commit no sucesso, rollback em qualquer exceção e sempre fecha a
    conexão — evitando os vazamentos que aconteciam com o padrão manual de
    conectar/fechar espalhado pelo código.
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
