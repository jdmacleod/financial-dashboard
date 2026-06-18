FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libffi-dev \
    libcairo2 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.21
COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .
RUN chmod +x start.sh

CMD ["./start.sh"]
