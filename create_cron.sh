#!/bin/bash
set -e

SCHEDULE="${CRON_SCHEDULE:-0/15 * * * *}"
PLEX_URL="${PLEX_URL?Error: PLEX_URL is required}"
PLEX_TOKEN="${PLEX_TOKEN?Error: PLEX_TOKEN is required}"
JELLYFIN_URL="${JELLYFIN_URL?Error: JELLYFIN_URL is required}"
JELLYFIN_TOKEN="${JELLYFIN_TOKEN?Error: JELLYFIN_TOKEN is required}"
JELLYFIN_USER="${JELLYFIN_USER?Error: JELLYFIN_USER is required}"
ADDITIONAL_ARGS="${ADDITIONAL_ARGS:-}"

SCRIPT_PATH="/usr/src/app/migrate.py"
CMD="python3 $SCRIPT_PATH $ADDITIONAL_ARGS --plex-url $PLEX_URL --plex-token $PLEX_TOKEN --jellyfin-url $JELLYFIN_URL --jellyfin-token $JELLYFIN_TOKEN --jellyfin-user $JELLYFIN_USER"

(crontab -l 2>/dev/null; echo "$SCHEDULE $CMD") | crontab -

echo "Cron job added successfully:"
crontab -l | grep migrate.py

eval "$CMD"

echo "Starting cron daemon..."
exec crond -f -l 2