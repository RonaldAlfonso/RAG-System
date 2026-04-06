FROM python:3.11-slim

# Dependencias del sistema necesarias para Playwright y lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias Python primero (aprovecha cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copia el código
COPY crawler_turismo_latam.py .


CMD ["python", "crawler_turismo_latam.py"]