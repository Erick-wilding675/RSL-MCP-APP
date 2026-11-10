# D-011, D-017: Imagem Docker do RSL.app para execução em modo HTTP atrás de proxy HTTPS (Caddy).
# Nenhuma chave de API ou segredo entra na imagem (NFR-03, D-013).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RSL_DATA_DIR=/data \
    RSL_HTTP_HOST=0.0.0.0 \
    RSL_HTTP_PORT=8000

# D-017: Cria usuário sem privilégio e pasta /data com permissão antes de declarar o volume
RUN groupadd --system --gid 10001 rslapp \
    && useradd --system --uid 10001 --gid rslapp --home-dir /data --no-create-home --shell /usr/sbin/nologin rslapp \
    && mkdir -p /data \
    && chown -R rslapp:rslapp /data

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN pip install --no-cache-dir . \
    && rm -rf /app

VOLUME ["/data"]
USER rslapp
WORKDIR /data
EXPOSE 8000

# D-017: Healthcheck em /health usando a biblioteca padrão do Python sob o usuário sem privilégio
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; port = os.environ.get('RSL_HTTP_PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3).read()"]

CMD ["rslapp", "serve"]
