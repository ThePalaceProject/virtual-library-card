FROM python:3.10-slim

ENV APP_DIR=/virtual_library_card/ \
    DJANGO_SETTINGS_MODULE=virtual_library_card.settings.prod

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

# Install system
RUN apt-get update -y && \
    apt-get install --no-install-recommends -y \
    curl mime-support && \
    curl -sSL https://install.python-poetry.org | POETRY_HOME="/opt/poetry" python3 - --yes --version "1.3.2" && \
    ln -s /opt/poetry/bin/poetry /bin/poetry && \
    apt-get remove curl -y && \
    apt-get autoremove -y && \
    rm -Rf /var/lib/apt/lists/* && \
    rm -Rf /root/.cache && \
    find /opt /usr -type d -name "__pycache__" -exec rm -rf {} +

# Install Python dependencies
COPY pyproject.toml poetry.lock $APP_DIR
WORKDIR $APP_DIR
RUN POETRY_VIRTUALENVS_CREATE=false poetry install --only main --no-interaction && \
    poetry cache clear -n --all pypi && \
    rm -Rf /root/.cache && \
    find /opt /usr -type d -name "__pycache__" -exec rm -rf {} +

# Install code
COPY . $APP_DIR

EXPOSE 8000

CMD ["./entrypoint.sh"]
