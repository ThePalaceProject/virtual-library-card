FROM python:3.10-slim

ENV APP_DIR=/virtual_library_card/ \
    DJANGO_SETTINGS_MODULE=virtual_library_card.settings.prod \
    POETRY_VIRTUALENVS_CREATE=false

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

ARG POETRY_VERSION=1.7.1
ARG REPO=ThePalaceProject/virtual-library-card

# Install system
RUN apt-get update -y && \
    apt-get install --no-install-recommends -y \
    curl mime-support && \
    curl -sSL https://install.python-poetry.org | POETRY_HOME="/opt/poetry" python3 - --yes --version "$POETRY_VERSION" && \
    ln -s /opt/poetry/bin/poetry /bin/poetry && \
    apt-get autoremove -y && \
    rm -Rf /var/lib/apt/lists/* && \
    rm -Rf /root/.cache && \
    find /opt /usr -type d -name "__pycache__" -exec rm -rf {} +

WORKDIR $APP_DIR

# Do basic python dependency install
# We use curl here to grab our poetry.lock and pyproject.toml files from the repo
# so that we can cache the docker layer for the poetry install step.
# If these files change, the later poetry install will handle it.
RUN curl -fsSL https://raw.githubusercontent.com/${REPO}/main/pyproject.toml -o ${APP_DIR}pyproject.toml && \
    curl -fsSL https://raw.githubusercontent.com/${REPO}/main/poetry.lock -o ${APP_DIR}poetry.lock && \
     poetry install --sync --only main --no-root --no-interaction && \
    poetry cache clear -n --all pypi && \
    rm -Rf /root/.cache && \
    find /opt /usr -type d -name "__pycache__" -exec rm -rf {} +

# Do final poetry install, when the layers are cached, this is the only step that will run
COPY . $APP_DIR
RUN POETRY_VIRTUALENVS_CREATE=false poetry install --sync --only main --no-interaction && \
    poetry cache clear -n --all pypi && \
    rm -Rf /root/.cache && \
    find /opt /usr -type d -name "__pycache__" -exec rm -rf {} +

EXPOSE 8000

CMD ["./entrypoint.sh"]
