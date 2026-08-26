# P2.4 real API smoke（jgb2 **preview**）：**STOP** — 合約端點 500

> 2026-08-26｜`USE_MOCK_JGB_API=false`、`JGB_API_BASE_URL=https://preview.jgbsmart.com`
> 這是本線第一次真的打外部 API。P2.1–P2.3 全數通過後才發出請求。

## 一、結果總表

| 探針 | 結果 | 判讀 |
|---|---|---|
| 無 API key | **401** `{"success":false,"error":{"code":401,"message":"API Key 未提供"}}` | ✅ 認證有擋，envelope 與我方假設一致 |
| 缺 `role_id` | **400** `role_id 為必填參數` | ✅ 與 controller 契約一致 |
| `GET /bills?role_id=…` | **200**，含 `mapping`／`data`／`pagination` | ✅ 帳單端點正常 |
| `GET /contracts/status-overview?role_id=…` | ❌ **500** | **硬阻斷，見下** |

## 二、500 的根因（jgb2 端，非我方）

```text
Illuminate\Database\QueryException: SQLSTATE[42S22]:
Column not found: 1054 Unknown column 'early_termination_notice_date' in 'field list'
(SQL: select `id`, `status`, `bit_status`, ... )
```

⇒ **preview 上跑的 jgb2 程式仍在 select 一個已被 DROP 的主表欄位**。

對照我方稽核所用的 checkout（`jgb_1/jgb2` master `5eaebb7f0a`）：
該版本的 `ContractApiController.php:42` 已明確註記——

> `early_termination_notice_date` 已隨拆表移至 `contract_lifecycle` 衛星表（主表欄位已 DROP），
> **不可列入 select**；由 Contract proxy 自衛星表供應

也就是 **master 已修，preview 未同步**。這是版本漂移，不是我方設定或替身問題。

## 三、對 Stage-1 的影響：**P2.5 無法進行**

已驗證的 vertical slice 終點是 `contract_closeout`，其 grounding 走
`GET /contracts/status-overview`。該端點在 preview 500 ⇒

```text
· P2.5（真 brain vertical acceptance）在 preview 上**不可能通過**
· P2.4 的其餘四項（viewer scope、真實標題形狀、**contract_ids 重查收斂**、
  timeout/latency）**全部無法取證**——它們都要打同一支端點
```

⚠️ 依 runbook §P2.4：「若 `contract_ids` 重查未收斂，Stage-1 停止」。
現在的情況更前面一步：**連第一次查詢都拿不到 200**。

## 四、解除條件（**在 jgb2 端，不是我方**）

```text
① preview 部署到含該修正的 jgb2 版本（master 5eaebb7f0a 或更新）
   —— 或 preview 的 DB 補回該欄位（不建議：那是往回走）
② 重跑 P2.4 的四項合約探針
③ 通過後才續行 P2.5
```

## 五、已經取得、不必重跑的結論

```text
✅ 認證（401）與必填參數（400）的 envelope 與我方折疊假設一致
✅ /bills 端點在 preview 正常，回應含 mapping／data／pagination 三段
✅ 我方 Stage-1 組態（七旗標）在容器內實測全數正確
✅ P2.2 migration 已套用並記帳，delegates 兩條皆帶 when
```

## 六、順帶修掉的兩個部署 runner 缺陷（P2.2 dry-run 抓到）

```text
① `migrate.sh` 會把 **rollback 檔當成 migration 套用**
   —— `seed_responsibility_delegates_v1_rollback.sql` 落在 migrations/ 主目錄，
      dry-run 顯示它會在 seed 之後**立刻被套用**：淨效果是什麼都沒發生，
      而帳本卻記成兩支都已套。
   處置：檔案移入 `migrations/rollback/`（既有慣例）＋ runner 加一層
        `*rollback*` 跳過（放錯位置不該造成錯誤結果）。
② `--apply` 會連帶跑 seeds.manifest 的 **always 支**（`regenerate_all_embeddings.py`）
   與兩支與 P2 無關的 migration。
   處置：P2.2 **不用 `--apply`**，改為單檔套用＋手動記帳
        （`created_by='p2.2-manual-scoped'`，帳本可稽核）。
```
