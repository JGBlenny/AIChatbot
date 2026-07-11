# ⚠️ 已除役（2026-07-11）——勿用於任何環境建置

本目錄是專案早期的資料庫 bootstrap seed，**凍結於早期架構**：

- schema 止於 13 檔，缺表單系統、form_sessions、usage_events、對話面向等後續所有結構（那些在 `../migrations/`）——以此建庫會得到**跑不起來的半套系統**
- 資料 seed 過時（`06-vendors-and-configs.sql` 的業者名單與現實脫節，曾造成誤引）

**新環境建置的唯一正式路徑：dump 還原**——見 `docs/deployment-runbook.md` 附錄 A（全庫搬遷，2026-07-07 裁定）。

docker-compose.prod.yml 的 `/docker-entrypoint-initdb.d` 掛載已同步移除（2026-07-11），避免空 volume 首啟時靜默灌入過時 seed。保留本目錄僅供歷史考據。
