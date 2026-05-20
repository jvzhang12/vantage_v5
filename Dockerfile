FROM node:22-slim AS frontend-builder

WORKDIR /app

COPY package.json package-lock.json ./
COPY vite.config.ts tsconfig.json tailwind.config.js postcss.config.js ./
COPY src/vantage_v5/webapp_react ./src/vantage_v5/webapp_react

RUN npm ci && npm run build


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
COPY --from=frontend-builder /app/src/vantage_v5/webapp/generated ./src/vantage_v5/webapp/generated

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

COPY docker/entrypoint.sh /usr/local/bin/vantage-entrypoint

EXPOSE 8005
VOLUME ["/data"]

ENTRYPOINT ["vantage-entrypoint"]
CMD ["vantage-v5-web"]
