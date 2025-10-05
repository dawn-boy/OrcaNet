# Start from an official Python base image
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /orcanet

# Install all system dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    build-essential \
    mafft \
    hmmer \
    diamond-aligner \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition files
COPY requirements.txt ./
COPY package.json package-lock.json ./

# Install Python and Node dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN npm ci

# Now, copy the rest of your application code
COPY . .

EXPOSE 5000

# Set the default command to run Flask. This will be used by our 'web' service.
CMD ["flask", "--app", "app", "run", "--host=0.0.0.0"]