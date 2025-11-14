FROM python:3.11-slim

# install ffmpeg for moviepy + fonts
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxrender1 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app
COPY app ./app

WORKDIR /app/app

EXPOSE 80

# uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]
