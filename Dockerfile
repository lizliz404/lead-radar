FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY lead_radar ./lead_radar
COPY examples ./examples
COPY config.example.yaml app.py ./

RUN python -m pip install --upgrade pip \
    && python -m pip install .

EXPOSE 8000

CMD ["uvicorn", "lead_radar.api:app", "--host=0.0.0.0", "--port=8000"]
