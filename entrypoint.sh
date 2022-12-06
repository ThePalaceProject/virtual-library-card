#!/bin/bash

# Create User
groupadd -r -g $UWSGI_GID vlc
useradd -r -s /bin/false -g vlc -u $UWSGI_UID vlc

# Collect static files
python manage.py collectstatic --no-input

# The 2 rename_app commands are idempotent, and can be run multiple times without consequence
# Once all deployments have been updated with the renamed app, the commands should be removed from this file
python manage.py rename_app "VirtualLibraryCard" "virtuallibrarycard"
python manage.py rename_app_permissions "VirtualLibraryCard" "virtuallibrarycard"

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
