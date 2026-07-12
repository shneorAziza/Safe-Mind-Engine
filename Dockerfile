FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system safemind && adduser --system --ingroup safemind safemind

COPY pyproject.toml README.md ./
COPY safe_mind ./safe_mind
COPY scripts ./scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[server]"

USER safemind

EXPOSE 8000

CMD ["sh", "-c", "uvicorn safe_mind.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
