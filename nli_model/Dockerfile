# nli-model 服務（DSP-033）——中文 NLI 蘊涵分數，Verifier 步③用。
#
# ⛔ 不掛在 semantic-model：其 /rerank 是 async def 內同步 predict、單 worker，
#    掛進去會 head-of-line blocking（DSP-033 P1-3）。
#
# 建置（首次沒有指紋期望值時，第 2 步會印出實得值後失敗，照它說的重跑）：
#   docker build -t aichatbot-nli-model \
#     --build-arg NLI_MODEL_SHA256=<模型目錄指紋> nli_model/
#
FROM python:3.9-slim

WORKDIR /app

# ---------------------------------------------------------------------------
# 1. 相依（torch 走 CPU-only index：PyPI 的 linux wheel 會拖進整套 CUDA，
#    在 1 GB mem_limit 的容器裡是純粹的浪費，且與部署機無 GPU 的事實不符）
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.2.2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# 2. 建置期下載權重 + 目錄指紋比對（P2-10／r18 F-7）
#    ⚠️ 這一層刻意在 COPY 應用程式碼**之前**：改 api_server.py 不必重下 409 MB。
#    ⚠️ NLI_MODEL_SHA256 未提供 ⇒ model_fingerprint.py 印出實得值後 exit 1，
#       ⛔ 不預設放行——沒有期望值也建得起來的檢查是裝飾品。
# ---------------------------------------------------------------------------
ARG NLI_MODEL_REVISION=864d25be3ce5e90d9193cb49d9fbd52722cdc6b0
ARG NLI_MODEL_SHA256="405d2ae08e70cd36bb2f42b4c9b39ca5cf65a50b982694199cd3009b5eb72f79"
ENV NLI_MODEL_DIR=/models/erlangshen-110m-nli
ENV NLI_MODEL_REVISION=${NLI_MODEL_REVISION}
ENV NLI_MODEL_SHA256=${NLI_MODEL_SHA256}

COPY scripts/model_fingerprint.py scripts/download_model.py /app/scripts/
RUN python3 /app/scripts/download_model.py \
 && python3 /app/scripts/model_fingerprint.py "$NLI_MODEL_DIR" "$NLI_MODEL_SHA256"

# ---------------------------------------------------------------------------
# 3. 應用程式碼與 canary
# ---------------------------------------------------------------------------
COPY scripts/ /app/scripts/
COPY canary.json /app/canary.json

ENV PYTHONPATH=/app
ENV NLI_CANARY_PATH=/app/canary.json
ENV LOG_LEVEL=INFO
# 離線硬保險：權重已在映像內，執行期 ⛔ 不得再連 HF（P2-10）。
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# ⚠️ 映像無 curl（與 semantic-model 2026-07-07 部署實測同一個坑）→ 用 python urllib。
# ⚠️ 探的是 /health 回得出東西，**不是** nli_ready——nli_ready=false 時我們要的是
#    「容器活著、health 說得出為什麼」，而不是 compose 把它反覆重啟。
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD python3 -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health',timeout=5)" || exit 1

CMD ["python3", "scripts/api_server.py"]
