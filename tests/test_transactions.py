"""Testes de lançamentos financeiros: validação, CRUD e precisão monetária."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from moneyflow.database import session_scope
from moneyflow.models import Transaction, TransactionType
from moneyflow.repositories import categories, transactions


@pytest.fixture
def usuario(user_factory):
    return user_factory()


def _criar(user_id, **overrides):
    parametros = dict(
        user_id=user_id,
        type_=TransactionType.DESPESA,
        description="Almoço",
        amount="42.50",
        transaction_date=date(2026, 5, 10),
        category_name="Alimentação",
        is_settled=True,
        is_recurring=False,
    )
    parametros.update(overrides)
    return transactions.create(**parametros)


class TestConversaoDeValor:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("1234.56", Decimal("1234.56")),
            ("1.234,56", Decimal("1234.56")),  # formato brasileiro
            ("R$ 1.234,56", Decimal("1234.56")),
            (1234.56, Decimal("1234.56")),
            ("0.01", Decimal("0.01")),
        ],
    )
    def test_aceita_formatos_validos(self, entrada, esperado):
        assert transactions.parse_amount(entrada) == esperado

    @pytest.mark.parametrize(
        "entrada", ["", None, "abc", "0", "-50", "99999999999.00"]
    )
    def test_rejeita_entradas_invalidas(self, entrada):
        assert transactions.parse_amount(entrada) is None


def test_criacao_com_dados_validos(usuario):
    resultado = _criar(usuario)

    assert resultado.success
    assert resultado.transaction_id is not None


def test_criacao_falha_sem_valor(usuario):
    resultado = _criar(usuario, amount=None)

    assert not resultado.success
    assert "valor" in resultado.message.lower()


def test_criacao_falha_com_valor_negativo(usuario):
    resultado = _criar(usuario, amount="-100")
    assert not resultado.success


def test_criacao_falha_sem_categoria(usuario):
    resultado = _criar(usuario, category_name=None)

    assert not resultado.success
    assert "categoria" in resultado.message.lower()


def test_valor_e_armazenado_com_precisao_exata(usuario):
    """
    0,1 + 0,2 em ponto flutuante dá 0,30000000000000004. Com Decimal o
    resultado é exato — num sistema financeiro esse erro não é aceitável.
    """
    _criar(usuario, amount="0.10")
    _criar(usuario, amount="0.20")

    with session_scope() as session:
        total = sum(
            session.scalars(
                select(Transaction.amount).where(Transaction.user_id == usuario)
            )
        )

    assert total == Decimal("0.30")


def test_categoria_nova_e_criada_ao_salvar(usuario):
    _criar(usuario, category_name="Categoria Inédita")

    nomes = categories.list_names(usuario, TransactionType.DESPESA)
    assert "Categoria Inédita" in nomes


def test_atualizacao_altera_os_campos(usuario):
    transaction_id = _criar(usuario).transaction_id

    resultado = transactions.update(
        usuario, transaction_id, amount="99.90", description="Jantar"
    )

    assert resultado.success

    frame = transactions.list_as_frame(usuario, TransactionType.DESPESA)
    assert frame.iloc[0]["Valor"] == 99.90
    assert frame.iloc[0]["Descrição"] == "Jantar"


def test_atualizacao_com_valor_invalido_e_recusada(usuario):
    transaction_id = _criar(usuario).transaction_id

    resultado = transactions.update(usuario, transaction_id, amount="abc")

    assert not resultado.success
    frame = transactions.list_as_frame(usuario, TransactionType.DESPESA)
    assert frame.iloc[0]["Valor"] == 42.50


def test_exclusao_remove_o_lancamento(usuario):
    transaction_id = _criar(usuario).transaction_id

    assert transactions.delete(usuario, transaction_id).success
    assert transactions.list_as_frame(usuario, TransactionType.DESPESA).empty


def test_exclusao_de_id_inexistente_falha_sem_quebrar(usuario):
    resultado = transactions.delete(usuario, 999999)
    assert not resultado.success


def test_filtro_por_periodo(usuario):
    _criar(usuario, transaction_date=date(2026, 1, 15))
    _criar(usuario, transaction_date=date(2026, 6, 15))

    frame = transactions.list_as_frame(
        usuario, TransactionType.DESPESA,
        start_date=date(2026, 6, 1), end_date=date(2026, 6, 30),
    )

    assert len(frame) == 1


def test_dataframe_vazio_mantem_as_colunas(usuario):
    """
    A interface acessa df['Valor'] direto; sem as colunas, um usuário novo
    veria a aplicação quebrar em vez de um painel zerado.
    """
    frame = transactions.list_as_frame(usuario, TransactionType.RECEITA)

    assert frame.empty
    assert "Valor" in frame.columns
    assert "Categoria" in frame.columns


class TestCategorias:
    def test_nao_permite_categoria_duplicada(self, usuario):
        categories.add(usuario, "Viagem", TransactionType.DESPESA)
        resultado = categories.add(usuario, "Viagem", TransactionType.DESPESA)

        assert not resultado.success

    def test_duplicidade_ignora_maiusculas(self, usuario):
        categories.add(usuario, "Viagem", TransactionType.DESPESA)
        resultado = categories.add(usuario, "viagem", TransactionType.DESPESA)

        assert not resultado.success

    def test_rejeita_nome_vazio(self, usuario):
        assert not categories.add(usuario, "   ", TransactionType.DESPESA).success

    def test_categoria_em_uso_nao_e_removida(self, usuario):
        """Remover uma categoria com lançamentos deixaria o histórico órfão."""
        _criar(usuario, category_name="Alimentação")

        resultado = categories.remove(
            usuario, ["Alimentação"], TransactionType.DESPESA
        )

        assert not resultado.success
        assert "Alimentação" in categories.list_names(usuario, TransactionType.DESPESA)

    def test_categoria_sem_uso_e_removida(self, usuario):
        categories.add(usuario, "Descartável", TransactionType.DESPESA)

        resultado = categories.remove(
            usuario, ["Descartável"], TransactionType.DESPESA
        )

        assert resultado.success
        assert "Descartável" not in categories.list_names(
            usuario, TransactionType.DESPESA
        )
