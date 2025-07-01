# Use Python 3.11 slim image for better compatibility
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies and patch vulnerabilities
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get dist-upgrade -y \
    && apt-get autoremove -y \
    && apt-get clean 

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY templates/ templates/
COPY troubleshoot.py .

# Create directory for database and logs
RUN mkdir -p /app/data /app/logs \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/users', timeout=10)" || exit 1

# Command to run the application
CMD ["uvicorn", "main_improved:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]