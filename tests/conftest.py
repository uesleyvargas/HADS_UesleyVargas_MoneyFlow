"""
Configuração compartilhada dos testes.

As variáveis de ambiente são definidas **antes** de qualquer import de
``moneyflow``, porque ``moneyflow.config`` resolve as configurações no momento
do import. Assim os testes jamais tocam o banco de desenvolvimento.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TEST_DB = Path(tempfile.gettempdir()) / "moneyflow_test.db"

os.environ["DEBUG"] = "1"
os.environ["SECRET_KEY"] = "chave-de-teste-nao-usada-em-producao"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
# bcrypt com custo alto deixaria a suíte lenta sem ganho de cobertura.
os.environ["BCRYPT_ROUNDS"] = "4"

from moneyflow.database import SessionFactory, engine  # noqa: E402
from moneyflow.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Cria o esquema uma vez e remove o arquivo ao final."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    _TEST_DB.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _clean_tables():
    """
    Zera as tabelas entre os testes.

    Cada teste começa de um estado conhecido, então a ordem de execução não
    influencia o resultado.
    """
    yield
    with SessionFactory() as session:
        # Ordem inversa das dependências, para não violar chave estrangeira.
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture
def user_factory():
    """Cria usuários de teste com dados válidos por padrão."""
    from moneyflow.repositories import users

    created = 0

    def _create(username: str | None = None, password: str = "senha-segura-123"):
        nonlocal created
        created += 1
        username = username or f"usuario{created}"
        result = users.create_user(username, f"{username}@exemplo.com", password)
        assert result.success, result.message
        return result.user_id

    return _create
