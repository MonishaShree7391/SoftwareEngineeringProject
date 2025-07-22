
# frontend_ui/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .
# Install OS dependencies
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5001

CMD ["python", "app.py"]

