"""
Hashing e verificação de senhas.

A versão anterior usava ``sha256(senha + salt)``. SHA-256 é uma função de hash
rápida por design: uma GPU comum testa bilhões de candidatas por segundo, então
um vazamento do banco entregaria as senhas em poucas horas.

Aqui usamos bcrypt, que é deliberadamente lento e tem custo ajustável.

Hashes antigos continuam sendo aceitos no login (para não travar quem já tem
conta), mas são convertidos para bcrypt de forma transparente no primeiro login
bem-sucedido. Veja `needs_rehash`.
"""

from __future__ import annotations

import hashlib
import hmac

import bcrypt

from moneyflow.config import settings

LEGACY_PREFIX = "sha256$"


def hash_password(password: str) -> str:
    """Gera um hash bcrypt. O salt fica embutido no próprio hash."""
    if not password:
        raise ValueError("A senha não pode ser vazia")
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Confere a senha contra o hash armazenado.

    Aceita tanto bcrypt quanto o formato legado ``sha256$<salt>$<hash>``.
    """
    if not password or not stored_hash:
        return False

    if stored_hash.startswith(LEGACY_PREFIX):
        return _verify_legacy(password, stored_hash)

    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        # Hash malformado no banco — trata como falha, nunca como sucesso.
        return False


def _verify_legacy(password: str, stored_hash: str) -> bool:
    """Verifica o formato antigo, usado só durante a transição."""
    try:
        _, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    candidate = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    # compare_digest evita vazar informação pelo tempo de comparação.
    return hmac.compare_digest(candidate, digest)


def needs_rehash(stored_hash: str) -> bool:
    """
    Indica se o hash deve ser regravado com os parâmetros atuais.

    Vale para hashes legados e para bcrypt gerado com custo menor que o
    configurado hoje (útil quando aumentamos `bcrypt_rounds` no futuro).
    """
    if stored_hash.startswith(LEGACY_PREFIX):
        return True
    try:
        rounds = int(stored_hash.split("$")[2])
    except (IndexError, ValueError):
        return True
    return rounds < settings.bcrypt_rounds


def build_legacy_hash(salt: str, digest: str) -> str:
    """Monta o formato legado a partir do esquema antigo (usado na migração)."""
    return f"{LEGACY_PREFIX}{salt}${digest}"
