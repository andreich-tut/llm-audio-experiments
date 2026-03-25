#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Building React webapp ==="
bash "$SCRIPT_DIR/build-webapp.sh"

echo "=== Deploying services ==="
bash "$SCRIPT_DIR/update.sh"
