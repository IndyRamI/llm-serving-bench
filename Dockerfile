FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir httpx pyyaml

COPY bench/ bench/
COPY cli.py .
COPY configs/ configs/

ENTRYPOINT ["python", "cli.py"]
