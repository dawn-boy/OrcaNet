FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/orcanet

ARG UID=1000
ARG GID=1000

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    nodejs \
    npm \
    mafft \
    hmmer \
    diamond-aligner \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g $GID appgroup && \
    useradd -u $UID -g $GID -ms /bin/bash appuser && \
    usermod -aG sudo appuser

WORKDIR /orcanet

RUN chown appuser:appgroup /orcanet

USER appuser

COPY --chown=appuser:appgroup requirements.txt package-lock.json* package.json ./

RUN pip install --no-cache-dir --user -r requirements.txt
RUN npm ci

ENV PATH="/home/appuser/.local/bin:${PATH}"

COPY --chown=appuser:appgroup . ./

CMD ["flask", "--app", "wsgi", "--debug", "run", "--host=0.0.0.0"]
