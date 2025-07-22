# authservice/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .


RUN apt-get update && \
    apt-get install -y curl gnupg apt-transport-https \
    unixodbc-dev gcc g++ libssl-dev libffi-dev \
    libpq-dev libxml2-dev libxslt1-dev libodbc1 odbcinst \
    iputils-ping netcat-openbsd && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools && \
    echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc && \
    export PATH="$PATH:/opt/mssql-tools/bin" && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
