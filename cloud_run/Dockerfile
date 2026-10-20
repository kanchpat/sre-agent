FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOOGLE_CLOUD_PROJECT=your-gcp-project-id \
    GOOGLE_CLOUD_LOCATION=us-central1 \
    BIGQUERY_DATASET=sre_workshop \
    VERTEX_AGENT_ENGINE_ID=0000000000000000000

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY chat_ux.py /app/chat_ux.py
COPY overview.html /app/overview.html
COPY server.py /app/server.py

EXPOSE 8080

CMD ["python3", "/app/server.py"]
