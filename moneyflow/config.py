"""
Configuração da aplicação.

Todos os parâmetros sensíveis ou que variam entre ambientes vêm de variáveis
de ambiente. Nenhum segredo é escrito no código — veja `.env.example`.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    """Lê uma variável de ambiente booleana aceitando 1/true/yes/on."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(url: str) -> str:
    """
    Normaliza a URL do banco.

    Provedores de nuvem (Heroku, Railway, Render) entregam a URL do Postgres
    com o esquema `postgres://`, que o SQLAlchemy 2.x não reconhece.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@dataclass(frozen=True)
class Settings:
    """Configuração imutável, resolvida uma vez na inicialização."""

    secret_key: str
    database_url: str
    debug: bool
    host: str
    port: int
    session_lifetime_days: int
    session_cookie_secure: bool

    # Regras de negócio
    min_password_length: int = 8
    # Custo do bcrypt. 12 é o padrão recomendado hoje; os testes baixam para 4
    # via BCRYPT_ROUNDS para não pagar o custo proposital do algoritmo.
    bcrypt_rounds: int = 12

    default_income_categories: tuple[str, ...] = field(
        default=("Salário", "Investimentos", "Comissão", "Outras receitas")
    )
    default_expense_categories: tuple[str, ...] = field(
        default=(
            "Alimentação",
            "Aluguel",
            "Transporte",
            "Saúde",
            "Educação",
            "Lazer",
            "Outras despesas",
        )
    )

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def load_settings() -> Settings:
    """Constrói as configurações a partir do ambiente."""
    debug = _env_bool("DEBUG", default=False)

    secret_key = os.getenv("SECRET_KEY", "").strip()
    if not secret_key:
        if not debug:
            raise RuntimeError(
                "SECRET_KEY não definida. Sem ela as sessões podem ser forjadas.\n"
                "Gere uma com: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                "e coloque no arquivo .env"
            )
        # Em desenvolvimento geramos uma chave efêmera: as sessões caem a cada
        # reinício, mas nunca rodamos com um segredo previsível e público.
        secret_key = secrets.token_hex(32)

    raw_database_url = os.getenv("DATABASE_URL")
    if raw_database_url is None:
        raw_database_url = f"sqlite:///{BASE_DIR / 'moneyflow.db'}"
    database_url = _normalize_database_url(raw_database_url.strip())
    try:
        make_url(database_url)
    except ArgumentError:
        # Mostra só o início (esquema): a senha nunca vai para o log. Casos
        # comuns: variável vazia ou referência do provedor não resolvida,
        # como o texto literal "${{ Postgres.DATABASE_URL }}".
        raise RuntimeError(
            "DATABASE_URL inválida: não é uma URL de banco de dados. "
            f"Valor recebido começa com {database_url[:14]!r} "
            f"({len(database_url)} caracteres). "
            "Esperado algo como postgresql://usuario:senha@host:5432/banco. "
            "Se usa referência do Railway, confira o nome do serviço e da variável."
        ) from None

    return Settings(
        secret_key=secret_key,
        database_url=database_url,
        debug=debug,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8050")),
        session_lifetime_days=int(os.getenv("SESSION_LIFETIME_DAYS", "7")),
        bcrypt_rounds=int(os.getenv("BCRYPT_ROUNDS", "12")),
        # Cookie só por HTTPS em produção; em dev rodamos em http://localhost.
        session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", default=not debug),
    )


settings = load_settings()
