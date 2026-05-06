FROM python:3.11-slim

WORKDIR /app

# 安裝 Pillow 所需系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev zlib1g-dev libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 暴露埠號
EXPOSE 8100

# 啟動應用
CMD ["python", "app.py"]
