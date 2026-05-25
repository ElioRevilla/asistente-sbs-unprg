FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY sbs_assistant ./sbs_assistant

RUN uv sync --no-dev

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "sbs_assistant.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
