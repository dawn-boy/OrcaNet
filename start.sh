#!/bin/sh
# start.sh

# Exit immediately if a command fails
set -e

# Define the source directory (where we bake assets into the image)
# and the destination directory (the persistent volume)
SOURCE_DIR="/app/static/"
DEST_DIR="/app/static/"

# Check if the destination directory (the volume) is empty.
# If it is, copy the assets from our baked-in source directory.
if [ -z "$(ls -A $DEST_DIR 2>/dev/null)" ]; then
  echo "Volume is empty. Initializing static assets..."
  # The '/.' is crucial: it copies the *contents* of the source directory
  cp -r $SOURCE_DIR/. $DEST_DIR/
  echo "Initialization complete."
else
  echo "Volume is not empty, skipping initialization."
fi

# Finally, execute the main command passed to this script (our gunicorn server)
exec "$@"