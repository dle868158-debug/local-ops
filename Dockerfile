FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN mkdir -p /app/data /app/logs

EXPOSE 9600

ENV CONTAINER_ENV=1 \
    CONSOLE_HOST=0.0.0.0 \
    CONSOLE_DATA_DIR=/app/data \
    CONSOLE_LOG_DIR=/app/logs

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9600/api/health', timeout=2)" || exit 1

CMD ["python3", "server.py", "--no-browser"]
