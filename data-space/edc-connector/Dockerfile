FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY config/ ./config/

EXPOSE 8080

CMD ["python", "server.py"]
