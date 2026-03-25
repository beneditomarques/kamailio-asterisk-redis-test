FROM python:3.12-slim

WORKDIR /app

# Instala dependências do sistema (necessárias para asterisk-ami)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY listener.py .

CMD ["python", "listener.py"]