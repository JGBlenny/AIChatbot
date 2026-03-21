FROM python:3.11-slim

WORKDIR /app

# 安裝 Docker CLI（用於執行 docker exec 觸發回測）
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有應用程式文件
COPY *.py .

# 暴露埠號
EXPOSE 8000

# 啟動應用
CMD ["python", "app.py"]
