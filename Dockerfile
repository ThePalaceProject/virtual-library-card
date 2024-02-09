FROM python:3

ENV APP_DIR=/virtual_library_card \
    DJANGO_SETTINGS_MODULE=virtual_library_card.settings.prod

ENV UWSGI_MASTER=1 \
    UWSGI_HTTP_AUTO_CHUNKED=1 \
    UWSGI_HTTP_KEEPALIVE=1 \
    UWSGI_LAZY_APPS=1 \
    UWSGI_WSGI_ENV_BEHAVIOR=holy \
    UWSGI_WORKERS=2 \
    UWSGI_THREADS=4 \
    UWSGI_STATIC_EXPIRES_URI="/(static|media)/.*\.[a-f0-9]{12,}\.(css|js|png|jpg|jpeg|gif|ico|woff|ttf|otf|svg|scss|map|txt) 315360000" \
    UWSGI_WSGI_FILE=$APP_DIR/virtual_library_card/wsgi.py \
    UWSGI_HTTP=:8000 \
    UWSGI_UID=999 \
    UWSGI_GID=999

COPY . $APP_DIR
WORKDIR $APP_DIR
RUN apt-get update -y && \
    apt-get install --no-install-recommends -y \
    vim gettext \
    && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["./entrypoint.sh"]
