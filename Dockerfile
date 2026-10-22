FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VTG_NO_ASR=1 \
    PORT=8000

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
COPY policy ./policy
COPY web ./web

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
