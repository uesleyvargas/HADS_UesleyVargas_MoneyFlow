"""
Isolamento entre usuários — a garantia mais importante do sistema.

Cada teste aqui representa uma forma pela qual um usuário poderia ver ou
alterar os dados de outro. Todos devem falhar do lado do atacante.
"""

from __future__ import annotations

from datetime import date

import pytest

from moneyflow.models import TransactionType
from moneyflow.repositories import categories, transactions


@pytest.fixture
def dois_usuarios(user_factory):
    """Dois usuários independentes: a vítima e quem tenta bisbilhotar."""
    return user_factory("vitima"), user_factory("intruso")


def _criar_despesa(user_id: int, valor: str = "150.00", categoria: str = "Alimentação"):
    resultado = transactions.create(
        user_id=user_id,
        type_=TransactionType.DESPESA,
        description="Compra no mercado",
        amount=valor,
        transaction_date=date(2026, 3, 15),
        category_name=categoria,
        is_settled=True,
        is_recurring=False,
    )
    assert resultado.success, resultado.message
    return resultado.transaction_id


def test_usuario_nao_ve_lancamentos_de_outro(dois_usuarios):
    vitima, intruso = dois_usuarios
    _criar_despesa(vitima)

    do_intruso = transactions.list_as_frame(intruso, TransactionType.DESPESA)

    assert do_intruso.empty


def test_usuario_nao_consegue_excluir_lancamento_de_outro(dois_usuarios):
    vitima, intruso = dois_usuarios
    transaction_id = _criar_despesa(vitima)

    # O intruso conhece o id e tenta apagar mesmo assim.
    resultado = transactions.delete(intruso, transaction_id)

    assert not resultado.success
    # E o lançamento continua lá.
    assert len(transactions.list_as_frame(vitima, TransactionType.DESPESA)) == 1


def test_usuario_nao_consegue_editar_lancamento_de_outro(dois_usuarios):
    vitima, intruso = dois_usuarios
    transaction_id = _criar_despesa(vitima, valor="150.00")

    resultado = transactions.update(intruso, transaction_id, amount="999999.00")

    assert not resultado.success

    frame = transactions.list_as_frame(vitima, TransactionType.DESPESA)
    assert frame.iloc[0]["Valor"] == 150.00


def test_categorias_sao_privadas_de_cada_usuario(dois_usuarios):
    vitima, intruso = dois_usuarios

    categories.add(vitima, "Categoria Secreta", TransactionType.DESPESA)

    nomes_do_intruso = categories.list_names(intruso, TransactionType.DESPESA)
    assert "Categoria Secreta" not in nomes_do_intruso


def test_remover_categoria_nao_afeta_outro_usuario(dois_usuarios):
    """
    No sistema antigo as categorias eram globais: qualquer usuário podia
    apagar as categorias de todo mundo.
    """
    vitima, intruso = dois_usuarios

    antes = categories.list_names(vitima, TransactionType.DESPESA)
    assert "Alimentação" in antes

    categories.remove(intruso, ["Alimentação"], TransactionType.DESPESA)

    depois = categories.list_names(vitima, TransactionType.DESPESA)
    assert "Alimentação" in depois


def test_dados_do_dashboard_sao_isolados(dois_usuarios):
    vitima, intruso = dois_usuarios
    _criar_despesa(vitima)

    receitas, despesas = transactions.load_dashboard_data(intruso)

    assert receitas == []
    assert despesas == []
