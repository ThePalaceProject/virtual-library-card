#!/bin/bash

set -ex

container="vlc"

# Wait for uWSGI to be ready to accept connections.
timeout 120s grep -q 'WSGI app .* ready in [0-9]* seconds' <(docker compose logs "$container" -f 2>&1)

# Make sure the app server is running and returning JSON from /version.json.
content_type=$(docker compose exec "$container" curl --write-out "%{content_type}" --silent --output /dev/null http://localhost:8000/version.json)
if ! [[ ${content_type} == "application/json" ]]; then
  echo "FAIL: Expected application/json but got ${content_type}"
  exit 1
else
  echo "  OK"
fi

exit 0
