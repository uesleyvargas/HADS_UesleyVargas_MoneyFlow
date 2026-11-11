"""
Camada de acesso a dados.

Isola completamente a interface (Dash) do banco. Nenhum callback monta SQL
nem abre conexão: eles chamam estas funções, que sempre exigem um
``user_id`` explícito e filtram por ele.
"""

from moneyflow.repositories import categories, transactions, users

__all__ = ["categories", "transactions", "users"]
