FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VANTAGE_V5_HOST=0.0.0.0
ENV VANTAGE_V5_PORT=8005
ENV VANTAGE_V5_REPO_ROOT=/data

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY canonical ./canonical

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

COPY docker/entrypoint.sh /usr/local/bin/vantage-entrypoint

EXPOSE 8005
VOLUME ["/data"]

ENTRYPOINT ["vantage-entrypoint"]
CMD ["vantage-v5-web"]
