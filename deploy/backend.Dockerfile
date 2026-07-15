FROM python:3.11-slim

WORKDIR /app

# System deps: ca-certs + mtr (for traceroute/MTR feature)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates mtr-tiny iputils-ping && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

# Bind to 0.0.0.0:8001 (matches the app's convention)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
