# ⚠️ 本文件已作廢（2026-07-11）

原內容（2025-11-03）宣稱「migrations 已歸檔、最終結果整合進 `database/init/`、結構變更請改 init 腳本」——**此前提已完全反轉**：

- ~~`database/migrations/` 是活的變更管理~~ → **2026-07-22 再收斂**：編號系列已除役改名 `migrations-legacy/`、`run_migrations.sh` 停用；結構變更一律在 **`rag-orchestrator/database/migrations/`** 新增，照 `docs/deployment-runbook.md` 逐節執行，帳本沿用 `schema_migrations` 表（runbook §17）
- `database/init/` 已除役改名 `init-legacy/`（schema 凍結於早期＋seed 資料過時），勿用於任何建置
- 新環境建置＝**dump 還原**（`docs/deployment-runbook.md` 附錄 A）

現行指南見 `database/README.md`。本檔保留僅為避免舊連結 404。
