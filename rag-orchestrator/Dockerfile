FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 暴露埠號
EXPOSE 8100

# 啟動應用
CMD ["python", "app.py"]
