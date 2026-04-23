FROM python:3.12-slim

ENV APP_DIR=/virtual_library_card/ \
    DJANGO_SETTINGS_MODULE=virtual_library_card.settings.prod \
    UV_PROJECT_ENVIRONMENT=/virtual_library_card/.venv

ENV UWSGI_MASTER=1 \
    UWSGI_HTTP_AUTO_CHUNKED=1 \
    UWSGI_HTTP_KEEPALIVE=1 \
    UWSGI_LAZY_APPS=1 \
    UWSGI_WSGI_ENV_BEHAVIOR=holy \
    UWSGI_WORKERS=2 \
    UWSGI_THREADS=4 \
    UWSGI_WSGI_FILE=$APP_DIR/virtual_library_card/wsgi.py \
    UWSGI_HTTP=:8000 \
    UWSGI_UID=999 \
    UWSGI_GID=999 \
    UWSGI_DIE_ON_TERM=true \
    UWSGI_HARAKIRI=20 \
    UWSGI_MAX_REQUESTS=5000 \
    UWSGI_VACUUM=true \
    UWSGI_POST_BUFFERING=1 \
    UWSGI_LOGFORMAT="[pid: %(pid)|app: -|req: -/-] %(addr) (%(user)) {%(vars) vars in %(pktsize) bytes} [%(ctime)] %(method) %(clean_uri) => generated %(rsize) bytes in %(msecs) msecs (%(proto) %(status)) %(headers) headers in %(hsize) bytes (%(switches) switches on core %(core))"

# required for postgres ssl: the crt file doesn't exist
# but the path must point to a visible directory otherwise we
# get a permissions error
ENV PGSSLCERT=/tmp/postgresql.crt

ARG REPO=ThePalaceProject/virtual-library-card

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/

# Install system dependencies
RUN apt-get update -y && \
    apt-get install --no-install-recommends -y \
    curl media-types mailcap libexpat1 && \
    apt-get autoremove -y && \
    rm -Rf /var/lib/apt/lists/*

WORKDIR $APP_DIR

# Do basic python dependency install
# We use curl here to grab our uv.lock and pyproject.toml files from the repo
# so that we can cache the docker layer for the uv sync step.
# If these files change, the later uv sync will handle it.
RUN if curl -fsSL https://raw.githubusercontent.com/${REPO}/main/pyproject.toml -o ${APP_DIR}pyproject.toml \
       && curl -fsSL https://raw.githubusercontent.com/${REPO}/main/uv.lock -o ${APP_DIR}uv.lock; then \
         uv sync --frozen --no-dev --no-install-project \
         && rm -Rf /root/.cache \
         && find /usr -type d -name "__pycache__" -exec rm -rf {} +; \
    fi

# Do final uv sync, when the layers are cached, this is the only step that will run
COPY . $APP_DIR
RUN uv sync --frozen --no-dev && \
    rm -Rf /root/.cache && \
    find /usr -type d -name "__pycache__" -exec rm -rf {} +

EXPOSE 8000

CMD ["./entrypoint.sh"]
