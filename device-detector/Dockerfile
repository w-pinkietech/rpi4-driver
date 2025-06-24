FROM python:3.11-slim

# Install system dependencies for udev access
RUN apt-get update && apt-get install -y \
    libudev1 \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY tests/ tests/

# Create non-root user for improved security
RUN groupadd -r detector && useradd -r -g detector detector
RUN chown -R detector:detector /app

# Switch to non-root user
USER detector

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import redis; redis.Redis(host='redis').ping()" || exit 1

# Set entrypoint
ENTRYPOINT ["python", "-m", "src.main"]