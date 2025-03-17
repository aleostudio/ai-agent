FROM python:3.10-slim

# Just to test connection to Ollama inside the container
# RUN apt-get update && apt-get install -y iputils-ping curl && rm -rf /var/lib/apt/lists/*

ENV APP_HOST="0.0.0.0"
ENV APP_PORT=9201

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}"]
