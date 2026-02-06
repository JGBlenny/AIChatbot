# 語義模型服務 Docker 配置
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements
COPY requirements.txt .

# 分步安裝 Python 套件以避免錯誤
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir torch>=2.1.0
RUN pip install --no-cache-dir sentence-transformers>=2.5.0
RUN pip install --no-cache-dir transformers scikit-learn numpy
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
RUN pip install --no-cache-dir fastapi==0.104.1 uvicorn==0.24.0 pydantic==2.4.2

# 預先下載模型（暫時註解避免建置失敗）
# RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-base')"

# 複製應用程式碼
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY data/ ./data/

# 設定環境變數
ENV PYTHONPATH=/app
ENV MODEL_CACHE_DIR=/app/models
ENV LOG_LEVEL=INFO

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# 預設執行 API 服務
CMD ["python", "scripts/api_server.py"]