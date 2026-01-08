FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有應用程式文件
COPY *.py .

# 暴露埠號
EXPOSE 8000

# 啟動應用
CMD ["python", "app.py"]
