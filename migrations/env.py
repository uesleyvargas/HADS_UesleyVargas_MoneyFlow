"""
Ambiente do Alembic.

A URL do banco vem da configuração da aplicação (variável de ambiente), não do
alembic.ini — assim a mesma migration roda em SQLite no desenvolvimento e em
PostgreSQL na nuvem sem editar arquivo nenhum.
"""

from logging.config import fileConfig

from alembic import context

from moneyflow.config import settings
from moneyflow.database import engine
from moneyflow.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadados usados pelo autogenerate para comparar modelos e banco.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar ao banco."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite não suporta ALTER TABLE completo; o batch mode recria a
        # tabela por baixo dos panos para viabilizar as alterações.
        render_as_batch=settings.is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica as migrations conectado ao banco."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=settings.is_sqlite,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
