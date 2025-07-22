# splitservice/Dockerfile
FROM python:3.10-slim


WORKDIR /app

COPY . .

RUN apt-get update && \
    apt-get install -y curl gnupg2 unixodbc-dev gcc g++ libgl1 libglib2.0-0 && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*


# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose split service port
EXPOSE 5005

# Run the Flask app
CMD ["python", "app.py"]
