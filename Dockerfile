# syntax=docker/dockerfile:1

# =============================================================================
# Build em dois estágios: as dependências são compiladas num estágio separado,
# e só os pacotes prontos entram na imagem final. Isso mantém compiladores e
# headers fora da imagem publicada — menor e com menos superfície de ataque.
# =============================================================================

FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.13-slim

# Rodar como root dentro do contêiner transforma um bug da aplicação em
# comprometimento do host. Este usuário não tem privilégios.
RUN useradd --create-home --shell /bin/bash moneyflow

WORKDIR /app

COPY --from=builder /root/.local /home/moneyflow/.local

COPY --chown=moneyflow:moneyflow moneyflow/ ./moneyflow/
COPY --chown=moneyflow:moneyflow migrations/ ./migrations/
COPY --chown=moneyflow:moneyflow scripts/ ./scripts/
COPY --chown=moneyflow:moneyflow alembic.ini wsgi.py ./

USER moneyflow

ENV PATH=/home/moneyflow/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8050

EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/')" || exit 1

# Aplica as migrations antes de subir: o esquema do banco nunca fica atrás
# do código recém-publicado.
CMD alembic upgrade head && \
    gunicorn wsgi:server \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --threads 4 \
        --timeout 60 \
        --access-logfile - \
        --error-logfile -
