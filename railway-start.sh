#!/usr/bin/env bash
# Railway: one image, three services. ATTENDEE_ROLE picks what this one runs.
#   web   - the API (private network only)
#   bots  - meeting bots, ONE per container so audio of two meetings never mixes
#   tasks - light work: webhooks, captions, launches (queue "tasks")
set -euo pipefail
cd /attendee
case "${ATTENDEE_ROLE:-web}" in
  web)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput >/dev/null
    exec gunicorn attendee.wsgi --bind "[::]:${PORT:-8000}" --workers 2 --timeout 120
    ;;
  bots)
    exec celery -A attendee worker -l info -Q celery --concurrency 1 -n "bots@%h"
    ;;
  tasks)
    exec celery -A attendee worker -l info -Q tasks --concurrency 4 -n "tasks@%h"
    ;;
  *)
    echo "Unknown ATTENDEE_ROLE=${ATTENDEE_ROLE}" >&2
    exit 1
    ;;
esac
