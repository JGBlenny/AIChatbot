# database/ 目錄指南

> 2026-07-11 重寫；2026-07-22 更新（migration 兩套體系收斂，編號系列除役——見 runbook §17）。

## 各目錄角色（現況）

| 目錄/檔案 | 角色 | 說明 |
|---|---|---|
| `migrations-legacy/` | ⚠️ 已除役（2026-07-22） | 編號系列（000_〜）＋原 `run_migrations.sh` 服務對象；schema 效果已活在 prod，勿重放（見其 DEPRECATED.md） |
| `run_migrations.sh` | ⚠️ 已除役（2026-07-22） | 執行即擋並指路；除役原因見檔頭 |
| `fixes/` | prod 修復暫存（**gitignore 不進版控**） | 一次性線上修復 SQL，由操作者手動執行；執行紀錄見部署 runbook |
| `init-legacy/` | ⚠️ 已除役（2026-07-11） | 早期 bootstrap seed，schema 凍結＋資料過時，勿用（見其 README） |
| `seeds/`、`test_data/`、`tests/` | 開發/測試用 | 非生產資料 |
| `backups/`、`exports/` | 備份與歷史導出 | 依 gitignore 規則，部分不進版控 |

## migration 現行唯一正統

**`rag-orchestrator/database/migrations/`** ＋ `docs/deployment-runbook.md` 逐節手動執行：

- 檔名 `YYYYMMDD_` 前綴；rollback 檔放 `migrations/rollback/` 子目錄
- 執行帳本＝`schema_migrations` 表（每支跑完補一行，範式見 runbook §17）
- 破壞性支獨立分檔＋rollback 檔，押煙囪驗證後由操作者手動執行

## 新環境怎麼建

**唯一正式路徑：dump 還原**——見 `docs/deployment-runbook.md` 附錄 A（全庫搬遷，2026-07-07 裁定）。不要用 init-legacy。

## 結構要變更時

1. 在 `rag-orchestrator/database/migrations/` 新增冪等 SQL（破壞性獨立分檔＋rollback 檔入 rollback/）
2. dev 套用驗證 → 測試綠 → 進版控 → dev 帳本記一行
3. 部署步驟記入 `docs/deployment-runbook.md` 對應節（含記帳指令）
