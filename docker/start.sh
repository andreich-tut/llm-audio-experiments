#!/bin/bash
set -e

COMPOSE="docker compose -f $(dirname "$0")/docker-compose.yml"

mkdir -p ./data ./logs

$COMPOSE up -d --build

echo "All services started."
$COMPOSE ps
