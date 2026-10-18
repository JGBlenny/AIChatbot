# 🚀 標準部署檢查清單

> **重要**：每次部署都必須按照此清單執行，不要跳過任何步驟

## ✅ 部署前檢查

### 1. 代碼檢查
```bash
# 在服務器上執行
cd /path/to/AIChatbot
git status
git log --oneline -5
```

**檢查項目：**
- [ ] 當前分支是 `main`
- [ ] 工作目錄乾淨（沒有未提交的修改）
- [ ] 查看最近 5 個提交，確認要部署的更新

---

## 📦 部署步驟

### 步驟 1：拉取最新代碼
```bash
git pull origin main
```

**預期結果：**
- 看到 "Already up to date" 或顯示拉取的文件列表
- 沒有合併衝突

---

### 步驟 2：檢查是否需要重新構建前端

**判斷標準：**
- 如果 `knowledge-admin/frontend/src/` 下的文件有變更 → 需要
- 如果只有後端或配置變更 → 不需要

**需要重新構建時執行（在服務器上）：**
```bash
cd knowledge-admin/frontend
npm install
npm run build
cd ../..
```

**檢查項目：**
- [ ] 前端構建成功
- [ ] dist 目錄已更新

---

### 步驟 3：檢查 Dockerfile 是否變更

```bash
git diff HEAD~1 knowledge-admin/backend/Dockerfile
```

**如果 Dockerfile 有變更 → 需要重新構建**

---

### 步驟 4：決定部署策略

| 變更類型 | 需要重新構建 | 只需重啟 |
|---------|------------|---------|
| 前端文件（.vue, .js） | ✅ 是 | ❌ 否 |
| Dockerfile | ✅ 是 | ❌ 否 |
| requirements.txt | ✅ 是 | ❌ 否 |
| 後端 Python 文件 | ✅ 是（`up -d --build`） | ❌ 否 |
| 配置文件（docker-compose.yml） | ❌ 否 | ✅ 是 |

> 2026-10-18 對碼：`docker-compose.prod.yml` 的 `rag-orchestrator` **沒有原始碼掛載**，`.py` 改動必須 `up -d --build` 才進容器；`knowledge-admin-api` 只掛載 `app.py`、`create_admin.py`、`scripts`，所以 `routes_*.py`、`auth_utils.py` 等其他後端檔改動也要 `up -d --build`（只改 `app.py` 時重啟即可生效）。

**選擇執行：**

#### 方案 A：完整重新構建（有 Dockerfile 或依賴變更）
```bash
cd /path/to/AIChatbot
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

#### 方案 B：重啟服務（只有掛載檔變更：`app.py`、`scripts/`、前端 `dist`、nginx 設定；後端其他 `.py` 與 `rag-orchestrator` 不適用，須走方案 A 或 `up -d --build <服務>`）
```bash
docker-compose -f docker-compose.prod.yml restart knowledge-admin-api
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
```

**檢查項目：**
- [ ] 執行了正確的方案
- [ ] 命令沒有錯誤

---

### 步驟 5：驗證部署

#### 5.1 檢查服務狀態
```bash
docker-compose -f docker-compose.prod.yml ps
```

**預期結果：**
- 所有服務狀態都是 `Up`
- 沒有服務在 `Restarting`

**如果有服務在重啟，執行：**
```bash
docker-compose -f docker-compose.prod.yml logs --tail=50 [service_name]
```

#### 5.2 檢查 API 健康
```bash
curl -s http://localhost:8000/docs | grep "FastAPI" || echo "API 未正常運行"
```

**預期結果：**
- 看到 "FastAPI" 字樣

#### 5.3 檢查前端
```bash
curl -s http://localhost:80 | grep "<!DOCTYPE html>" || echo "前端未正常運行"
```

**預期結果：**
- 看到 HTML 內容

#### 5.4 測試登入
- 訪問：`http://your-domain` 或 `http://your-server-ip`
- 使用管理員帳號登入
- 檢查更新的功能是否正常

**檢查項目：**
- [ ] 所有服務正常運行
- [ ] API 可訪問
- [ ] 前端可訪問
- [ ] 可以登入
- [ ] 新功能正常

---

## 🚨 常見問題處理

### 問題 1：服務不斷重啟
```bash
# 查看日誌
docker-compose -f docker-compose.prod.yml logs --tail=100 [service_name]
```

**常見原因：**
- 缺少 Python 模組 → 需要重新構建
- 配置錯誤 → 檢查環境變數
- 數據庫連接失敗 → 檢查數據庫服務

### 問題 2：前端顯示舊版本
```bash
# 強制重啟並清除瀏覽器緩存
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
# 在瀏覽器按 Ctrl+Shift+R 強制刷新
```

### 問題 3：API 回應 404
```bash
# 檢查路由文件是否存在
docker-compose -f docker-compose.prod.yml exec knowledge-admin-api ls -la /app/routes_*.py
```

**如果文件不存在 → Dockerfile 沒有正確複製**

---

## 📋 部署後檢查

### 必做檢查
- [ ] 所有服務狀態正常
- [ ] 可以登入系統
- [ ] 測試本次更新的功能
- [ ] 查看錯誤日誌（如有）

### 記錄
```bash
# 記錄部署版本
git log --oneline -1 > /tmp/deploy_version.txt
echo "部署時間: $(date)" >> /tmp/deploy_version.txt
cat /tmp/deploy_version.txt
```

---

## 🔄 回滾步驟（如果部署失敗）

```bash
# 1. 查看上一個版本
git log --oneline -5

# 2. 回滾代碼
git checkout [previous_commit_hash]

# 3. 重新構建
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 4. 驗證服務
docker-compose -f docker-compose.prod.yml ps
```

---

## 📝 標準輸出範例

### 成功的部署應該看到：
```
✅ 代碼已更新到最新版本
✅ 前端已重新構建並上傳（如需要）
✅ 服務已重新構建（如需要）
✅ 所有服務狀態：Up
✅ API 健康檢查通過
✅ 前端可訪問
✅ 登入測試通過
✅ 功能測試通過
```

---

## ⚠️ 重要提醒

1. **不要跳過任何檢查步驟**
2. **不要在生產環境做實驗性修改**
3. **每次部署都記錄版本和時間**
4. **有問題立即回滾，不要嘗試在線修復**
5. **部署前在本地或測試環境驗證**

---

## 🆘 緊急聯絡

如果部署過程中遇到無法解決的問題：
1. 立即回滾到上一個穩定版本
2. 記錄完整的錯誤日誌
3. 不要重複嘗試失敗的操作
