# 部署指南

本專案支援多種部署方式，適合不同的使用場景。

## 📋 目錄

- [開發環境](#開發環境)
- [生產環境](#生產環境)
- [快速更新前端](#快速更新前端)
- [常見問題](#常見問題)

---

## 🛠️ 開發環境

### 方案一：使用 Volume 掛載（推薦）

**當前配置已啟用**，`docker-compose.yml` 中已配置 volume 掛載。

#### 優點
- ✅ 修改程式碼後只需本地編譯（無需重建 Docker）
- ✅ 更新快速（1-2 秒）
- ✅ 接近生產環境

#### 使用步驟

1. **首次設定或依賴變更後**
   ```bash
   cd knowledge-admin/frontend
   npm install
   ```

2. **修改程式碼後**
   ```bash
   cd knowledge-admin/frontend
   npm run build
   ```
   刷新瀏覽器即可看到變更

3. **如果需要重啟容器**
   ```bash
   docker-compose restart knowledge-admin-web
   ```

### 方案二：開發模式 + 熱重載

使用 Vite 開發伺服器，支援熱重載。

```bash
# 停止生產環境前端
docker-compose stop knowledge-admin-web

# 啟動開發環境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d knowledge-admin-web-dev

# 查看日誌
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f knowledge-admin-web-dev
```

修改程式碼後會自動重新編譯和刷新瀏覽器。

### 方案三：完全本地開發

```bash
cd knowledge-admin/frontend
npm install
npm run dev
```

訪問 http://localhost:5173

---

## 🚀 生產環境

### 當前配置（Volume 掛載模式）

`docker-compose.yml` 已配置為使用 volume 掛載，適合：
- ✅ 快速更新前端
- ✅ 零停機部署
- ✅ 節省構建時間

#### 部署流程

**選項 A：使用部署腳本（推薦）**
```bash
./deploy-frontend.sh
```

**選項 B：手動部署**
```bash
# 1. 編譯前端
cd knowledge-admin/frontend
npm install
npm run build

# 2. 重新載入 nginx
docker exec aichatbot-knowledge-admin-web nginx -s reload
```

### 傳統 Docker 構建模式

如果你想要完全獨立的 Docker 映像檔（不依賴 host 的檔案）：

1. **移除 docker-compose.yml 中的 volume 配置**

   註解或刪除：
   ```yaml
   # volumes:
   #   - ./knowledge-admin/frontend/dist:/usr/share/nginx/html
   #   - ./knowledge-admin/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
   ```

2. **重新構建映像檔**
   ```bash
   docker-compose build --no-cache knowledge-admin-web
   docker-compose up -d knowledge-admin-web
   ```

3. **後續更新**

   每次修改程式碼都需要重新構建：
   ```bash
   docker-compose build knowledge-admin-web
   docker-compose up -d knowledge-admin-web
   ```

---

## ⚡ 快速更新前端

### 使用 Volume 掛載模式（當前）

```bash
# 一行指令完成部署
./deploy-frontend.sh
```

或手動執行：
```bash
cd knowledge-admin/frontend
npm run build
cd ../..
docker exec aichatbot-knowledge-admin-web nginx -s reload
```

### 不使用 Volume 掛載

```bash
docker-compose build knowledge-admin-web
docker-compose up -d knowledge-admin-web
```

---

## 🔧 後端開發

### Python 後端也支援 Volume 掛載

在 `docker-compose.dev.yml` 中已配置後端的開發模式。

#### 使用開發模式

```bash
# 停止生產環境的後端
docker-compose stop knowledge-admin-api rag-orchestrator

# 啟動開發環境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d \
  knowledge-admin-api-dev rag-orchestrator-dev
```

修改 Python 程式碼後，FastAPI 會自動重新載入（支援熱重載）。

---

## 📊 部署模式比較

| 特性 | Volume 掛載 | 完整 Docker 構建 |
|------|------------|-----------------|
| 更新速度 | ⚡️ 快（1-2秒） | 🐌 慢（1-2分鐘） |
| 部署複雜度 | 簡單 | 較複雜 |
| 容器可攜性 | 需要同步 dist | 完全獨立 |
| 適合場景 | 開發、快速迭代 | CI/CD、K8s 部署 |
| 生產環境 | ✅ 可用 | ✅ 推薦 |

---

## ❓ 常見問題

### Q: 修改程式碼後沒有變化？

**使用 Volume 掛載時：**
```bash
# 1. 確認已重新編譯
cd knowledge-admin/frontend
npm run build

# 2. 檢查 dist 目錄更新時間
ls -la dist/

# 3. 重新載入 nginx
docker exec aichatbot-knowledge-admin-web nginx -s reload

# 4. 清除瀏覽器快取
Ctrl+Shift+R（強制重新整理）
```

**不使用 Volume 時：**
```bash
# 重新構建並啟動
docker-compose build --no-cache knowledge-admin-web
docker-compose up -d knowledge-admin-web
```

### Q: 容器啟動失敗？

```bash
# 檢查容器日誌
docker-compose logs knowledge-admin-web

# 檢查 dist 目錄是否存在
ls -la knowledge-admin/frontend/dist/

# 如果不存在，先編譯
cd knowledge-admin/frontend
npm run build
```

### Q: 線上環境應該用哪種方式？

**推薦方案：**
- **小型專案/快速迭代**：使用 Volume 掛載
- **大型專案/多機器部署**：使用完整 Docker 構建
- **K8s 環境**：使用完整 Docker 構建 + CI/CD

**當前配置適合：**
- ✅ 單機部署
- ✅ 快速更新需求
- ✅ 小型到中型專案

### Q: 如何切換到完整 Docker 構建模式？

1. 編輯 `docker-compose.yml`，註解掉 volume 配置：
   ```yaml
   knowledge-admin-web:
     build: ./knowledge-admin/frontend
     # volumes:  # 註解這兩行
     #   - ./knowledge-admin/frontend/dist:/usr/share/nginx/html
   ```

2. 重新構建：
   ```bash
   docker-compose build knowledge-admin-web
   docker-compose up -d knowledge-admin-web
   ```

### Q: 可以混用嗎？

可以！你可以在 `docker-compose.yml` 中使用 volume 掛載方便開發，但在 CI/CD 或生產環境使用覆蓋配置：

```bash
# 生產環境部署（使用完整構建）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

其中 `docker-compose.prod.yml` 可以覆蓋掉 volume 配置。

---

## 📚 更多資訊

詳細的開發工作流程請參考：[docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md)

---

## 🎯 推薦工作流程

1. **日常開發**：使用 Volume 掛載或開發模式
2. **測試驗證**：使用 Volume 掛載 + 本地編譯
3. **部署更新**：使用 `./deploy-frontend.sh`
4. **重大版本**：使用完整 Docker 構建

選擇適合你的方式，提升開發和部署效率！
