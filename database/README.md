# database/ 目錄指南

> 2026-07-11 重寫（原內容為早期 pgvector 設定快照，前提已失效）。

## 各目錄角色（現況）

| 目錄/檔案 | 角色 | 說明 |
|---|---|---|
| `migrations/` | **活的結構變更**（60+ 支） | schema 與 seed 變更的唯一正式位置；`schema_migrations` 表追蹤；冪等 |
| `run_migrations.sh` | migration 執行器 | dry-run／自動備份／冪等，用法見 `migrations/README.md` |
| `fixes/` | prod 修復暫存（**gitignore 不進版控**） | 一次性線上修復 SQL，由操作者手動執行；執行紀錄見部署 runbook |
| `init-legacy/` | ⚠️ 已除役（2026-07-11） | 早期 bootstrap seed，schema 凍結＋資料過時，勿用（見其 README） |
| `seeds/`、`test_data/`、`tests/` | 開發/測試用 | 非生產資料 |
| `backups/`、`exports/` | 備份與歷史導出 | 依 gitignore 規則，部分不進版控 |

## 新環境怎麼建

**唯一正式路徑：dump 還原**——見 `docs/deployment-runbook.md` 附錄 A（全庫搬遷，2026-07-07 裁定）。不要用 init-legacy。

## 結構要變更時

1. 在 `migrations/` 新增冪等 SQL（破壞性變更獨立分檔＋rollback 檔，prod 由操作者手動執行）
2. dev 套用驗證 → 測試綠 → 進版控
3. 部署步驟記入 `docs/deployment-runbook.md`
