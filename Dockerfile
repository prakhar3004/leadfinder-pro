# Official Microsoft Playwright image with Python & Chromium pre-installed
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Upgrade pip and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .

# Expose default port
EXPOSE 8000

# Start server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
