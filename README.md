# 💰 MoneyFlow

Aplicação web de gestão financeira pessoal: registre receitas e despesas,
acompanhe o fluxo de caixa e visualize para onde seu dinheiro está indo.

Multiusuário, com autenticação e isolamento completo de dados entre contas.

> 📌 **Adicione aqui um print da tela do dashboard.** É a primeira coisa que
> um recrutador olha ao abrir o repositório.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Interface | Dash 3 + Dash Bootstrap Components |
| Gráficos | Plotly |
| Backend | Flask + Flask-Login |
| Banco | SQLAlchemy 2 (SQLite em dev, PostgreSQL em produção) |
| Migrations | Alembic |
| Senhas | bcrypt |
| Testes | pytest |

## Arquitetura

```
moneyflow/
├── config.py          Configuração por variáveis de ambiente
├── database.py        Engine e sessões do SQLAlchemy
├── models.py          Modelos ORM (User, Category, Transaction)
├── security.py        Hashing de senhas
├── auth.py            Sessão e identidade do usuário
├── app.py             Instância do Dash e config do Flask
├── index.py           Layout raiz e roteamento
├── theme.py           Paleta e template dos gráficos
├── repositories/      Acesso a dados (users, categories, transactions)
├── pages/             Telas (login, dashboards, extratos)
└── components/        Componentes reutilizáveis (sidebar)
```

A regra que sustenta o desenho: **a interface nunca fala com o banco**. Os
callbacks chamam os repositórios, e todo repositório exige um `user_id`
explícito, obtido da sessão no servidor. Não existe caminho pelo qual um
usuário alcance os dados de outro.

## Rodando localmente

```bash
# 1. Ambiente virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Dependências
pip install -r requirements.txt -r requirements-dev.txt

# 3. Configuração
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # cole em SECRET_KEY
# para desenvolvimento, defina também DEBUG=1

# 4. Banco de dados
alembic upgrade head

# 5. Subir
python run.py
```

Acesse <http://127.0.0.1:8050>, crie uma conta e comece a usar.

### Testes

```bash
pytest                              # suíte completa
pytest --cov=moneyflow              # com cobertura
ruff check .                        # lint
```

### Migrando dados da versão 1.x

Se você tem um `financas.db` da versão antiga:

```bash
python scripts/migrate_legacy.py --source financas.db --dry-run   # simula
python scripts/migrate_legacy.py --source financas.db             # executa
```

As senhas antigas continuam funcionando e são convertidas para bcrypt
automaticamente no primeiro login de cada usuário. O script é idempotente:
rodar duas vezes não duplica nada.

## Segurança

Decisões que valem registrar:

- **Sessão assinada no servidor.** A identidade vive num cookie assinado com a
  `SECRET_KEY`, `HttpOnly` e `SameSite=Lax`. O cliente não consegue forjá-la.
- **Senhas em bcrypt** com custo configurável. Hashes SHA-256 herdados da
  versão 1.x são aceitos no login e reescritos em bcrypt na hora.
- **Isolamento por usuário** garantido em duas camadas: `user_id` obrigatório
  em toda query, e `ON DELETE CASCADE` no próprio esquema.
- **Valores monetários em `Numeric(12,2)`**, nunca `float` — ponto flutuante
  binário não representa `0,10` exatamente e o erro se acumula nas somas.
- **Nenhum segredo no código.** Tudo vem do ambiente; o `.env` é ignorado pelo
  git, e arquivos `.db` também (contêm hashes de senha e dados financeiros).

## Deploy

A aplicação já está pronta para a nuvem: `Dockerfile` com usuário sem
privilégios, `wsgi.py` para Gunicorn, migrations aplicadas na inicialização e
toda a configuração por variáveis de ambiente.

### Com Docker

```bash
docker compose up --build     # app + PostgreSQL local
```

### Em um provedor (Railway, Render, Fly.io)

1. Suba o repositório para o GitHub.
2. Crie um banco PostgreSQL gerenciado e copie a `DATABASE_URL`.
3. Configure as variáveis de ambiente no painel do provedor:

   | Variável | Valor |
   |---|---|
   | `SECRET_KEY` | uma chave nova, gerada só para produção |
   | `DATABASE_URL` | a URL do PostgreSQL |
   | `DEBUG` | `0` |
   | `SESSION_COOKIE_SECURE` | `1` |

4. Aponte o provedor para o `Dockerfile`. As migrations rodam sozinhas no
   start.

**Nunca** rode em produção com `DEBUG=1`: o Flask expõe um console Python
interativo na web nesse modo.

## Licença

MIT
