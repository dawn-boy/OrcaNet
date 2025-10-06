# Dockerfile

# Use a specific Python version
FROM python:3.10-slim-bookworm

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

WORKDIR /app

# Install Node.js for the Tailwind build step
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*

# Copy dependency files first to leverage Docker layer caching
COPY requirements.txt package.json package-lock.json* ./

# Install Python and Node.js dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN npm ci

# Create a non-root user for the application
RUN addgroup --system app && adduser --system --ingroup app app

# Copy the entire application code
COPY . .

# Build the production CSS file, which populates the static/css folder
RUN npm run build

# --- START OF MODIFICATIONS ---

# 1. Move the fully built static folder to a source location.
#    This is because the volume will hide the original /app/static directory.
RUN mv /app/static /app/static_assets_source

# 2. Copy the startup script and make it executable
COPY start.sh .
RUN chmod +x start.sh

# --- END OF MODIFICATIONS ---

# Switch to the non-root user
USER app

# --- UPDATE ENTRYPOINT AND CMD ---

# 3. Set the ENTRYPOINT to our new script.
#    This script will now run on every container start.
ENTRYPOINT ["./start.sh"]

CMD ["gunicorn", "-c", "gunicorn_conf.py", "wsgi:app"]