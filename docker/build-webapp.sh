#!/bin/bash
set -e

echo "=== Building React Mini App ==="
cd "$(dirname "$0")/../webapp"
npm install
npm run build
echo "=== Webapp built to webapp/dist/ ==="
