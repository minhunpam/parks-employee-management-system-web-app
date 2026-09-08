# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# The build context is the repository root. This keeps the shared Python
# requirements file outside src/backend while still packaging the Django app.
COPY requirements.txt ./requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

# Django expects the frontend templates and static files beside backend.
COPY src/backend ./backend
COPY src/frontend/templates ./frontend/templates
COPY src/frontend/static ./frontend/static

WORKDIR /app/backend

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
