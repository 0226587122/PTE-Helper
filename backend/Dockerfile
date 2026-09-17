# Build from the repository root so the question bank in seed/ is included:
#   docker build -f backend/Dockerfile .
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

FROM base AS dev
COPY backend/requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY backend/ ./
COPY seed/ /app/seed/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
COPY backend/ ./
COPY seed/ /app/seed/
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app
ENV PORT=8080 WEB_CONCURRENCY=2
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT} -w ${WEB_CONCURRENCY} --timeout 150 --access-logfile -"]
