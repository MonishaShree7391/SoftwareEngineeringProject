# invoiceservice/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

# Install system dependencies for OCR and PyMuPDF
# Install system packages for pyodbc + OCR + image tools

RUN apt-get update && \
    apt-get install -y libgl1 libglib2.0-0 gnupg curl unixodbc-dev gcc g++ netcat-openbsd && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5002

CMD ["python", "app.py"]
