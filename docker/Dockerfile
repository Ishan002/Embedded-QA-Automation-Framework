FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY framework/ ./framework/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY pytest.ini .

ENV MOCK_DEVICE=true
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["pytest"]
CMD ["tests/", "--tb=short", "-v", "--junitxml=/results/test-results.xml"]
