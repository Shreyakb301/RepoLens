# Stage 1 — build the SPA. Vite writes it to `backend/static`, which the
# FastAPI app serves at `/` so one container ships the frontend and the API.
FROM node:22-slim AS frontend

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts postcss.config.mjs index.html ./
COPY src ./src
COPY public ./public
RUN npm run build


# Stage 2 — the runtime. `git` is required: the analyzer shells out to it to
# clone the repositories it inspects (see `backend/app/ingestion.py`).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY --from=frontend /build/backend/static ./backend/static

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
