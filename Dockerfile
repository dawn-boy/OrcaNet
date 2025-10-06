# Use a specific Python version
FROM python:3.10-slim-bookworm

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Install Node.js for the Tailwind build step
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first to leverage Docker layer caching
COPY requirements.txt package.json package-lock.json* ./

# Install Python and Node.js dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN npm ci

RUN addgroup --system app && adduser --system --ingroup app app

# Copy the rest of your application code
COPY . .


# Build the production CSS file
RUN npm run build

ENV PORT=8080
EXPOSE 8080

USER app

# Start the application with Gunicorn
# Railway automatically provides and exposes the $PORT variable

CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 4 wsgi:app

