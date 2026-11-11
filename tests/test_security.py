"""Testes de hashing e verificação de senha."""

from __future__ import annotations

import hashlib

from moneyflow.security import (
    build_legacy_hash,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_e_verificacao_bcrypt():
    hashed = hash_password("minha-senha-secreta")

    assert verify_password("minha-senha-secreta", hashed)
    assert not verify_password("senha-errada", hashed)


def test_hashes_iguais_geram_saidas_diferentes():
    """O salt aleatório impede identificar senhas iguais comparando hashes."""
    assert hash_password("mesma-senha") != hash_password("mesma-senha")


def test_hash_nunca_contem_a_senha():
    hashed = hash_password("senha-super-secreta")
    assert "senha-super-secreta" not in hashed


def test_verificacao_de_hash_legado():
    """O formato antigo continua sendo aceito durante a transição."""
    salt = "abc123"
    digest = hashlib.sha256(("senha-antiga" + salt).encode("utf-8")).hexdigest()
    legacy = build_legacy_hash(salt, digest)

    assert verify_password("senha-antiga", legacy)
    assert not verify_password("outra-senha", legacy)


def test_hash_legado_precisa_ser_atualizado():
    legacy = build_legacy_hash("sal", "digest")
    assert needs_rehash(legacy)


def test_hash_bcrypt_atual_nao_precisa_atualizacao():
    assert not needs_rehash(hash_password("qualquer-senha"))


def test_entradas_invalidas_nao_autenticam():
    """Valores vazios ou hash corrompido nunca podem resultar em sucesso."""
    hashed = hash_password("senha")

    assert not verify_password("", hashed)
    assert not verify_password("senha", "")
    assert not verify_password("senha", "hash-corrompido")
