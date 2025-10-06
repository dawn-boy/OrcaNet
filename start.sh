#!/usr/bin/env bash
set -e

# 1. Ensure the static directory exists and is empty
mkdir -p app/static
rm -rf app/static/*

# 2. Copy the prebuilt assets into the volume-mounted /app/static
cp -R app/static_assets_source/. app/static/

# 3. Execute the final command (CMD)
exec "$@"
