# Publicação do MoneyFlow

## 1. Subir o código para o GitHub

```bash
git add -A
git commit -m "v2: pacote moneyflow, deploy e PWA"
git branch -M main
git remote add origin https://github.com/<seu-usuario>/moneyflow.git
git push -u origin main
```

O `.env` e o `moneyflow.db` estão no `.gitignore`; confira com `git status` que nenhum dos dois será enviado.

## 2. Hospedar no Railway (web)

1. Crie conta em railway.com e faça login com o GitHub.
2. **New Project → Deploy from GitHub repo** e escolha o repositório. O Railway detecta o `Dockerfile` sozinho.
3. No mesmo projeto: **New → Database → PostgreSQL**.
4. No serviço do app, aba **Variables**:

   | Variável | Valor |
   |---|---|
   | `SECRET_KEY` | saída de `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referência ao banco) |
   | `DEBUG` | `0` |
   | `SESSION_COOKIE_SECURE` | `1` |

   Não defina `PORT`: o Railway injeta o dele e o `Dockerfile` já o usa.
5. Aba **Settings → Networking → Generate Domain**. Você recebe uma URL `https://...up.railway.app`.
6. Domínio próprio (opcional): registre um `.com.br` no registro.br e aponte o CNAME indicado pelo Railway.

O `Dockerfile` roda `alembic upgrade head` antes de iniciar, então o schema do banco é criado no primeiro deploy.

**Dados da v1:** para trazer o `financas.db` antigo, rode localmente
`DATABASE_URL=<url pública do Postgres> python scripts/migrate_legacy.py --source financas.db --dry-run`
e, se o resultado estiver certo, sem o `--dry-run`.

## 3. Android e iOS (PWA)

O app já é um PWA instalável: manifesto, ícones e service worker estão em `moneyflow/assets/`. Depois do deploy, **precisa estar em HTTPS** (o domínio do Railway já está).

- **Android (Chrome):** abra o site → menu ⋮ → **Instalar app**.
- **iOS (Safari):** abra o site → botão Compartilhar → **Adicionar à Tela de Início**. Tem que ser o Safari; outros navegadores no iOS não instalam PWA.

O app abre em tela cheia, com ícone próprio. O service worker só mostra uma página "sem conexão"; não guarda dados financeiros em cache de propósito.

### Se quiser estar nas lojas

- **Google Play:** empacote o PWA como TWA com o [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap). Taxa única de US$ 25.
- **App Store:** a Apple costuma rejeitar apps que são só um site embrulhado (diretriz 4.2). Exige conta Apple Developer (US$ 99/ano) e um Mac. Só vale a pena se o app ganhar algo nativo.

Para portfólio, o PWA instalável já cobre os dois sistemas sem custo.

## 4. Depois de publicar

- **Monitoramento:** UptimeRobot (grátis) apontando para a URL, e Sentry para erros.
- **Backup:** ative os backups do Postgres no Railway ou rode `pg_dump` periodicamente.
- **Testar no celular de verdade:** login (o cookie `Secure` exige HTTPS), criar uma transação e instalar o app.
