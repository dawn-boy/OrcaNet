# Dockerfile

# 1. Base image and environment
FROM python:3.10-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

WORKDIR /app

# 2. Install Node.js for Tailwind build
RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs npm \
 && rm -rf /var/lib/apt/lists/*

# 3. Copy and install dependencies
COPY requirements.txt package.json package-lock.json* ./
RUN pip install --no-cache-dir -r requirements.txt
RUN npm ci

# 4. Add non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# 5. Copy application code and build CSS into /app/static/css
COPY . .
RUN npm run build

# 6. Preserve built static assets under a different path
RUN mv app/static ./app/static_assets_source

RUN mkdir -p app/static \
 && chown -R app:app app/static \

# 7. Copy entrypoint script and Gunicorn config
COPY start.sh gunicorn_conf.py ./
RUN chmod +x start.sh

# 8. Switch to non-root
USER app

# 9. Expose a default port (documentation only)
EXPOSE 8080

# 10. Entrypoint and default command
ENTRYPOINT ["./start.sh"]
CMD ["gunicorn", "-c", "gunicorn_conf.py", "wsgi:app"]
