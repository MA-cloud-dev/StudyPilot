FROM python:3.12-slim

WORKDIR /app

COPY apps/api /app/apps/api
RUN pip install --no-cache-dir -e /app/apps/api[dev]

COPY storage /app/storage

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic -c /app/apps/api/alembic.ini upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir /app/apps/api"]
