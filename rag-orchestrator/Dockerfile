FROM python:3.11-slim

WORKDIR /app

# 安裝 Pillow 所需系統依賴
# deb.debian.org 的 http CDN 偶發 404（快取陳舊），改走 https 提高建置穩定性
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev zlib1g-dev libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式（含 artifacts/responsibility/ 的 R10P sealed replica）
COPY . .

# S1-A／R2：sealed artifact 完整性在 **build 期**就驗——缺漏／竄改／epoch 不符即建置失敗。
# ⛔ 不得放行到 runtime 才發現；⛔ 不得 fallback DB mapping。
RUN python -c "import sys; sys.path.insert(0,'/app'); \
    from services.responsibility_artifacts import validate; r = validate(); \
    print('[build] R10P artifacts OK registry=%s active=%s dim=%s' % \
          (r['registry_digest'][:16], r['embedding_count'], r['embedding_dimension']))"

# 暴露埠號
EXPOSE 8100

# 啟動應用
CMD ["python", "app.py"]
