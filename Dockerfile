FROM python:3.12-slim

WORKDIR /app

# Copy all project files
COPY . .

# Create entrypoint script using RUN with shell
RUN cat > /app/docker-run.sh << 'EOF' && chmod +x /app/docker-run.sh
#!/bin/bash
set -e

# Patch server.py to bind to 0.0.0.0 for Docker
python3 << 'PYTHON'
import re
with open('/app/server.py', 'r') as f:
    content = f.read()

# Replace HOST binding for Docker
content = re.sub(
    r"HOST = ['\"]127\.0\.0\.1['\"]",
    "HOST = '0.0.0.0'",
    content
)

# Write patched version
with open('/app/server_docker.py', 'w') as f:
    f.write(content)
print("Server patched for Docker (0.0.0.0 binding)")
PYTHON

# Run the patched server
python3 /app/server_docker.py --no-browser
EOF

# Install optional dependencies  
RUN pip install --no-cache-dir pillow >/dev/null 2>&1 || true

# Create data directories
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE 9600

# Environment variables
ENV CONTAINER_ENV=1 \
    CONSOLE_DATA_DIR=/app/data \
    CONSOLE_LOG_DIR=/app/logs

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9600/api/health', timeout=2)" || exit 1

# Run
CMD ["/app/docker-run.sh"]
