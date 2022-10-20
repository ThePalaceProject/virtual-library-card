#!/bin/bash

# Create User
groupadd -r -g $UWSGI_GID vlc
useradd -r -s /bin/false -g vlc -u $UWSGI_UID vlc

# Collect static files
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Create the superuser
if [[ -z "${SUPERUSER_EMAIL}" ]]; then
  echo "SUPERUSER_EMAIL env must be set." && exit 127
fi
if [[ -z "${SUPERUSER_PASSWORD}" ]]; then
  echo "SUPERUSER_PASSWORD env must be set." && exit 127
fi
python manage.py createsuperusernoninteractive --email $SUPERUSER_EMAIL --password $SUPERUSER_PASSWORD

exec uwsgi --show-config
