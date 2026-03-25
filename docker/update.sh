#!/bin/bash
set -e

COMPOSE="docker compose -f $(dirname "$0")/docker-compose.yml"

echo "Rebuilding and restarting..."
$COMPOSE build --pull
$COMPOSE up -d

echo "Cleaning up old images..."
docker image prune -f

echo "Done."
$COMPOSE ps
