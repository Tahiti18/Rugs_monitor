# Railway-compatible image with Playwright + Python
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Ensure browsers are installed (already in base image but safe)
RUN playwright install --with-deps chromium

COPY . .

# Default start is API; override for scraper
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]
