# Use Microsoft's official Playwright Python image — Chromium pre-installed,
# eliminating the longest build step (playwright install --with-deps chromium).
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# Only missing system dep: Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies (cloud backend) — cached layer when requirements unchanged
COPY cloud/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install AAT core from project root
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Copy cloud application
COPY cloud/app/ ./app/
COPY cloud/scripts/ ./scripts/

# Runtime directories
RUN mkdir -p screenshots uploads

# Non-root user for security
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
