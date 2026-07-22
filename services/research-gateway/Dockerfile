FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system ailab && adduser --system --ingroup ailab --home /nonexistent ailab

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

USER ailab
EXPOSE 8000

CMD ["uvicorn", "ailab_research_gateway.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]

