# CLAUDE.md

Este arquivo orienta o Claude Code (claude.ai/code) ao trabalhar com o código deste repositório.

MoneyFlow v2: aplicativo web de finanças pessoais (Dash 3 + Flask + SQLAlchemy 2). Código, comentários e interface estão em português (pt-BR); siga esse padrão. O layout da v1 (`app.py`, `db.py`, `components/` na raiz do repositório) foi removido em favor do pacote `moneyflow/`.

## Comandos

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # defina SECRET_KEY; adicione DEBUG=1 para desenvolvimento
alembic upgrade head          # cria/atualiza o schema
python run.py                 # servidor de desenvolvimento, http://127.0.0.1:8050

pytest                        # suíte completa
pytest tests/test_users.py::test_name   # um único teste
pytest --cov=moneyflow
ruff check .                  # lint (inclui as regras "S" do bandit)

alembic revision --autogenerate -m "msg"   # após alterar models.py
alembic check                              # o CI falha se models e migrations divergirem
python scripts/migrate_legacy.py --source financas.db --dry-run   # importa dados da v1
docker compose up --build     # app + PostgreSQL local
```

O ponto de entrada em produção é `gunicorn wsgi:server` (veja o `Dockerfile`, que executa `alembic upgrade head` antes). `run.py` serve apenas para desenvolvimento.

## Arquitetura

- **A configuração é resolvida na importação.** `moneyflow/config.py` monta um singleton imutável `settings` a partir das variáveis de ambiente (e do `.env`). Sem `SECRET_KEY` ele lança erro, a menos que `DEBUG=1` (nesse caso é gerada uma chave efêmera). `DATABASE_URL` assume por padrão o SQLite `moneyflow.db`; `postgres://`/`postgresql://` são reescritos para `postgresql+psycopg://`. O `engine` em `database.py` também é criado na importação, então o ambiente precisa estar definido antes de importar `moneyflow` (veja `tests/conftest.py`).
- **Cookie de sessão em HTTP:** `SESSION_COOKIE_SECURE` assume por padrão `not DEBUG`, mas o `.env.example` o define como `1`. No desenvolvimento local em `http://127.0.0.1`, defina `SESSION_COOKIE_SECURE=0`; caso contrário o navegador descarta o cookie e o login parece falhar sem nenhuma mensagem.
- **A direção das importações é única:** `app.py` (instância do Dash + configuração do cookie do Flask) não importa nada de páginas/componentes; páginas e componentes importam `app` dele. `index.py` é a raiz: define `app.layout`, roteia pelo pathname e importa as páginas. Tanto `run.py` quanto `wsgi.py` precisam importar `moneyflow.index` para que layout e callbacks sejam registrados.
- **A UI nunca toca no banco.** Os callbacks do Dash chamam `moneyflow/repositories/*` (users, categories, transactions); toda função de repositório recebe um `user_id` explícito, que os callbacks devem obter de `auth.current_user_id()` (cookie de sessão assinado do Flask), nunca de valores enviados pelo cliente. Preserve isso ao adicionar consultas — o isolamento entre usuários também é garantido por `ON DELETE CASCADE`.
- **Fluxo de dados para a UI:** `index.load_user_data` preenche `store-receitas`/`store-despesas` (`dcc.Store`) a partir de `transactions.load_dashboard_data`. `store-data-version` é um contador que qualquer página incrementa após uma escrita para fazer tudo recarregar. As colunas do DataFrame são fixadas por `transactions.COLUMNS` (nomes em português: `Data, Valor, Categoria, ...`).
- **Dinheiro é `Numeric(12,2)` / `Decimal`, nunca float.** As escritas passam por `database.session_scope()` (commit em caso de sucesso, rollback em caso de erro).
- **Senhas:** bcrypt (`security.py`, custo definido por `BCRYPT_ROUNDS`); hashes SHA-256 legados da v1 são aceitos no login e re-hasheados.
- Os gráficos usam o template Plotly compartilhado, registrado por `theme.register_template()`.

## Testes

`tests/conftest.py` define as variáveis de ambiente (arquivo SQLite temporário, `BCRYPT_ROUNDS=4`) antes de importar `moneyflow`, cria o schema com `create_all` (não com Alembic) e apaga todas as tabelas após cada teste. Use a fixture `user_factory` para criar usuários. `test_isolation.py` cobre o acesso a dados entre usuários — estenda-o ao adicionar funções de repositório.
