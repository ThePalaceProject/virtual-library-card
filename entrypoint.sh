#!/bin/bash

# Create User
groupadd -r -g $UWSGI_GID vlc
useradd -r -s /bin/false -g vlc -u $UWSGI_UID vlc

# Collect static files
runuser -u vlc -- python manage.py collectstatic --no-input

runuser -u vlc -- python manage.py migrate --no-input

# Ensure the uploadable folder (MEDiA_ROOT) is owned entirely by the vlc user
mkdir -p compiled/media
chown $UWSGI_UID:$UWSGI_GID -R compiled/media

# Create the superuser
if [[ -z "${SUPERUSER_EMAIL}" ]]; then
  echo "SUPERUSER_EMAIL env must be set." && exit 127
fi
if [[ -z "${SUPERUSER_PASSWORD}" ]]; then
  echo "SUPERUSER_PASSWORD env must be set." && exit 127
fi
runuser -u vlc -- python manage.py createsuperusernoninteractive --email $SUPERUSER_EMAIL --password $SUPERUSER_PASSWORD

exec uwsgi --show-config
