FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY packages ./packages
COPY apps ./apps
COPY infra ./infra
COPY alembic.ini ./
RUN pip install --no-cache-dir .
CMD ["sh", "-c", "alembic upgrade head && python -m apps.worker.main"]
