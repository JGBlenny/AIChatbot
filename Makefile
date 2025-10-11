# AI Chatbot - 快捷命令
# 使用方式: make <command>

.PHONY: help prod-up prod-down prod-build prod-logs dev-up dev-down dev-logs frontend-build frontend-dev

# 默認顯示幫助
help:
	@echo "🤖 AI Chatbot 知識庫系統 - 快捷命令"
	@echo ""
	@echo "📦 生產環境命令:"
	@echo "  make prod-up          - 啟動生產環境"
	@echo "  make prod-down        - 停止生產環境"
	@echo "  make prod-build       - 重建生產環境"
	@echo "  make prod-logs        - 查看生產環境日誌"
	@echo "  make prod-restart-web - 重啟前端服務（生產）"
	@echo ""
	@echo "🔧 開發環境命令:"
	@echo "  make dev-up           - 啟動開發環境"
	@echo "  make dev-down         - 停止開發環境"
	@echo "  make dev-logs         - 查看開發環境日誌"
	@echo "  make frontend-build   - 編譯前端（開發模式用）"
	@echo ""
	@echo "⚡ 快速開發命令:"
	@echo "  make backend-only     - 只啟動後端服務"
	@echo "  make frontend-dev     - 啟動前端 Vite 開發服務器"
	@echo ""
	@echo "🗑️  清理命令:"
	@echo "  make clean            - 停止所有容器並清理"
	@echo "  make clean-all        - 停止所有容器、清理並刪除 volumes"
	@echo ""
	@echo "📖 詳細說明請查看: DOCKER_COMPOSE_GUIDE.md"

# ==================== 生產環境 ====================

prod-up:
	@echo "🚀 啟動生產環境..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	@echo "🛑 停止生產環境..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-build:
	@echo "🔨 重建生產環境..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-logs:
	@echo "📋 查看生產環境日誌（Ctrl+C 退出）..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

prod-restart-web:
	@echo "🔄 重建並重啟前端服務（生產）..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build knowledge-admin-web
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d knowledge-admin-web
	@echo "✅ 前端服務已重啟"

# ==================== 開發環境 ====================

dev-up:
	@echo "🔧 啟動開發環境..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-down:
	@echo "🛑 停止開發環境..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

dev-logs:
	@echo "📋 查看開發環境日誌（Ctrl+C 退出）..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

frontend-build:
	@echo "📦 編譯前端..."
	cd knowledge-admin/frontend && npm run build
	@echo "✅ 前端編譯完成"

# ==================== 快速開發 ====================

backend-only:
	@echo "🚀 啟動後端服務（不含前端容器）..."
	docker-compose up -d postgres redis embedding-api knowledge-admin-api rag-orchestrator
	@echo "✅ 後端服務已啟動"
	@echo "💡 現在可以執行: make frontend-dev"

frontend-dev:
	@echo "⚡ 啟動前端 Vite 開發服務器..."
	@echo "📍 訪問: http://localhost:8080"
	cd knowledge-admin/frontend && npm run dev

# ==================== 清理 ====================

clean:
	@echo "🗑️  停止所有容器..."
	docker-compose down
	@echo "✅ 清理完成"

clean-all:
	@echo "🗑️  停止所有容器並刪除 volumes..."
	docker-compose down -v
	@echo "✅ 完全清理完成"

# ==================== 快捷狀態查看 ====================

status:
	@echo "📊 容器狀態:"
	@docker-compose ps

ps:
	@docker-compose ps
