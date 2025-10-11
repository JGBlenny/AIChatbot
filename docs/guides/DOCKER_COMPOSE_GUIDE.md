# Docker Compose 環境配置指南

本專案提供三種 Docker Compose 配置文件，適用於不同的開發和部署場景。

## 📁 配置文件說明

```
docker-compose.yml       # 基礎配置（所有服務的共同配置）
docker-compose.prod.yml  # 生產環境配置（疊加）
docker-compose.dev.yml   # 開發環境配置（疊加）
```

## 🚀 使用方式

### **1. 生產環境（Production）**

適用於：正式部署、測試環境、CI/CD

```bash
# 啟動生產環境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 重建並啟動
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 停止
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 查看日誌
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

**特點**：
- ✅ 前端使用 Docker image 內編譯的文件
- ✅ 更穩定、更安全
- ✅ 不依賴主機文件系統
- ✅ 自動重啟（restart: unless-stopped）

**前端修改流程**：
```bash
# 1. 修改代碼
vim knowledge-admin/frontend/src/views/KnowledgeView.vue

# 2. 重建前端 image
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build knowledge-admin-web

# 3. 重啟前端容器
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d knowledge-admin-web
```

---

### **2. 開發環境（Development）**

適用於：日常開發、快速迭代

```bash
# 啟動開發環境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 停止
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 查看日誌
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f knowledge-admin-web
```

**特點**：
- ✅ 前端掛載本地 dist 目錄
- ✅ 修改後只需 `npm run build`，無需重建 Docker
- ✅ 開發效率高
- ⚠️ 不自動重啟（restart: no）

**前端修改流程**：
```bash
# 1. 修改代碼
vim knowledge-admin/frontend/src/views/KnowledgeView.vue

# 2. 本地編譯（容器會立即看到更新）
cd knowledge-admin/frontend
npm run build

# ✅ 刷新瀏覽器即可看到更新
```

---

### **3. 純開發模式（Vite Dev Server）**⚡

適用於：前端開發、熱重載

```bash
# 只啟動後端服務
docker-compose up -d postgres redis embedding-api knowledge-admin-api rag-orchestrator

# 本地啟動前端開發服務器
cd knowledge-admin/frontend
npm install  # 首次需要
npm run dev  # 啟動 Vite 開發服務器
```

**特點**：
- ✅ 熱模組替換（HMR）- 修改代碼立即生效
- ✅ 最快的開發體驗
- ✅ 不需要 Docker 前端容器
- ✅ 支持 Source Map 調試

訪問：http://localhost:8080

---

## 🔄 常用命令對比

| 操作 | 生產模式 | 開發模式 |
|------|---------|---------|
| **啟動** | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d` | `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d` |
| **停止** | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml down` | `docker-compose -f docker-compose.yml -f docker-compose.dev.yml down` |
| **重建** | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml build` | `cd knowledge-admin/frontend && npm run build` |
| **查看日誌** | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f` | `docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f` |

---

## 💡 快捷命令別名（可選）

為了方便使用，可以在 `~/.bashrc` 或 `~/.zshrc` 添加別名：

```bash
# 生產環境
alias dc-prod='docker-compose -f docker-compose.yml -f docker-compose.prod.yml'
alias dc-prod-up='docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d'
alias dc-prod-down='docker-compose -f docker-compose.yml -f docker-compose.prod.yml down'
alias dc-prod-build='docker-compose -f docker-compose.yml -f docker-compose.prod.yml build'
alias dc-prod-logs='docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f'

# 開發環境
alias dc-dev='docker-compose -f docker-compose.yml -f docker-compose.dev.yml'
alias dc-dev-up='docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d'
alias dc-dev-down='docker-compose -f docker-compose.yml -f docker-compose.dev.yml down'
alias dc-dev-logs='docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f'

# 前端開發
alias frontend-build='cd knowledge-admin/frontend && npm run build && cd ../..'
alias frontend-dev='cd knowledge-admin/frontend && npm run dev'
```

使用別名後：
```bash
# 生產環境
dc-prod-up
dc-prod-build knowledge-admin-web
dc-prod-logs

# 開發環境
dc-dev-up
frontend-build  # 前端本地編譯
dc-dev-logs

# 純開發模式
docker-compose up -d postgres redis embedding-api knowledge-admin-api rag-orchestrator
frontend-dev  # 啟動 Vite
```

---

## 📊 三種模式對比

| 特性 | 生產模式 | 開發模式（Docker） | 純開發模式（Vite） |
|------|---------|-------------------|-------------------|
| **前端文件來源** | Docker image 內 | 本地 dist 目錄 | Vite Dev Server |
| **修改後** | 重建 Docker | `npm run build` | 自動熱重載 |
| **速度** | 重建較慢 | 編譯快速 | 最快（秒級） |
| **適用場景** | 生產、測試 | 快速開發 | 前端開發 |
| **一致性** | 最高 | 中等 | 僅前端 |
| **調試** | 困難 | 中等 | 最佳（Source Map） |

---

## 🛠️ 故障排除

### 問題 1：前端顯示舊內容

**開發模式**：
```bash
cd knowledge-admin/frontend
npm run build
# 清除瀏覽器緩存（Cmd+Shift+R 或 Ctrl+Shift+R）
```

**生產模式**：
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build knowledge-admin-web
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d knowledge-admin-web
```

### 問題 2：開發模式下 dist 目錄不存在

```bash
cd knowledge-admin/frontend
npm install
npm run build
```

### 問題 3：Vite 開發服務器無法連接後端

確保後端服務已啟動：
```bash
docker-compose ps | grep knowledge-admin-api
```

檢查 `vite.config.js` 的 proxy 配置是否正確。

---

## 📝 建議工作流程

### **日常前端開發**：
1. 使用 Vite Dev Server（最快）
   ```bash
   docker-compose up -d postgres redis embedding-api knowledge-admin-api rag-orchestrator
   cd knowledge-admin/frontend && npm run dev
   ```

### **測試完整流程**：
2. 使用開發模式
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   cd knowledge-admin/frontend && npm run build
   ```

### **部署前測試**：
3. 使用生產模式
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

---

## 📖 更多資訊

- Docker Compose 文檔: https://docs.docker.com/compose/
- Vite 文檔: https://vitejs.dev/
- Vue.js 文檔: https://vuejs.org/
