# 🚀 快速部署指南

## 1️⃣ 啟動服務
```bash
# 設置環境變數
echo "OPENAI_API_KEY=your_key_here" > .env

# 啟動所有服務
docker-compose up -d --build

# 等待服務就緒（約 2-3 分鐘）
docker-compose ps
```

## 2️⃣ 創建管理員帳號
```bash
# 方法 1：交互式（推薦）
docker-compose exec knowledge-admin-api python create_admin.py

# 方法 2：命令行參數
docker-compose exec knowledge-admin-api python create_admin.py \
  --username admin \
  --password your_password \
  --email admin@example.com \
  --full-name "管理員"
```

## 3️⃣ 登入使用
訪問：`http://your-server-ip:8087`

使用剛創建的帳號登入。

---

📖 **完整文檔**：見 `docs/DEPLOYMENT_GUIDE.md`
