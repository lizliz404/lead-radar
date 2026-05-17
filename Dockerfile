FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

COPY pyproject.toml README.md ./
COPY lead_radar ./lead_radar
COPY examples ./examples
COPY config.example.yaml app.py ./

RUN python -m pip install --upgrade pip \
    && python -m pip install '.[ui]'

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
