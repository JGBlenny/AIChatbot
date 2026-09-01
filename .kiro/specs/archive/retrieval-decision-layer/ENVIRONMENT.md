# 環境重建 runbook｜量測有效性的前置條件

> **為什麼需要這份**：本線的四個關鍵檔是用 `docker cp` 進容器的，**不在 image 裡**。
> 容器一重建就全毀，而 `make audit` 不變量 3 會 FAIL，**該輪回測所有結論整批作廢**
> （前科：20260810 第一輪 107 輪重播全被舊 image 污染）。
> 依業主偏好：逐條指令＋預期輸出，不打包腳本。

## 開工前檢查（每次動手前跑，30 秒）

```bash
cd /Users/lenny/jgb/AIChatbot
make audit 2>&1 | grep -A1 "不變量 3"
```
預期：`✅ PASS`。若 FAIL → 執行下節「重建後必做」。

```bash
docker exec aichatbot-rag-orchestrator printenv CACHE_ENABLED KB_SIMILARITY_THRESHOLD FORM_TRIGGER_THRESHOLD
```
預期逐行：`false` / `0.65` / `0.75`。**任一項不同，前後數據即不可比**（D-16 鐵則）。

## 容器重建後必做（否則量測無效）

```bash
docker cp rag-orchestrator/routers/chat.py                    aichatbot-rag-orchestrator:/app/routers/chat.py
docker cp rag-orchestrator/services/conversational_engine.py  aichatbot-rag-orchestrator:/app/services/conversational_engine.py
docker cp rag-orchestrator/services/decision_layer.py         aichatbot-rag-orchestrator:/app/services/decision_layer.py
docker cp rag-orchestrator/services/usage_metering.py         aichatbot-rag-orchestrator:/app/services/usage_metering.py
docker restart aichatbot-rag-orchestrator
```
等 12 秒後驗：
```bash
make audit 2>&1 | grep -A1 "不變量 3"
```
預期：`✅ PASS`。**未過就別跑任何回測。**

> 註：`scripts/backtest/decision_replay.py` **不在容器裡**，harness 跑在 host 打容器 API。
> 改它不需要 docker cp（改容器內的副本無效）。

## DB 前置

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
 "SELECT count(*) FROM information_schema.columns WHERE table_name='usage_events' AND column_name IN ('decision_snapshot','facet_event')"
```
預期：`2`。若為 0，套 migration：
```bash
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
 < rag-orchestrator/database/migrations/20260811_usage_events_decision_snapshot.sql
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
 "INSERT INTO schema_migrations(migration_name,created_by) VALUES('20260811_usage_events_decision_snapshot','runbook') ON CONFLICT DO NOTHING;"
```

## 語料前置

逐字稿與 run 目錄受 `.gitignore`，需自 S3 取回：
```bash
aws s3 sync s3://jgb2-production-upload/assistant-reports/ \
  docs/backtest/corpus-20260810/reports/ --exclude '*' --include '*.md'
find docs/backtest/corpus-20260810/reports -name '*.md' | wc -l
```
預期：`37`。

凍結語料本體（run1/2/3）取回指令見 `docs/backtest/corpus-20260810/README.md`。
⚠ 現行完整性閘門是**自簽自證**（比對本機樹雜湊，同時改語料與雜湊即通過）——
任務 0.3 補 S3 SHA-256 實比對前，語料被動過不會被發現。

## 已知的坑

| 坑 | 後果 | 處置 |
|---|---|---|
| 容器重建未 docker cp 四檔 | 整輪回測結論作廢 | 上節指令 |
| 重播 tag 用 `rdl`（預設值） | `rdl` 不在 `INTERNAL_RULES` → 自己的重播污染覆蓋率母體，量出的 99% 是假的 | 用 `backtest_` 前綴；任務 0.1 驗收④要改預設 |
| `--skip-audit` 跑出的結果 | `_run_meta.json` 記了「不具回歸效力」但**全 repo 無消費者**，沒有機制阻止它被當正式證據 | 任務 0.4 補；在那之前人工把關 |
| `make audit` 不變量 8 顯示 PASS | **假綠**——八種規避寫法只擋一種，多一個空格就過。它證明的是「現在沒洩漏」，不是「鎖得住」 | 任務 0.2 改 AST |
| 本機 `create_digression_config` migration 未套 | 無 | **別條工作線的既有落差，不是本線造成，勿順手修** |
| untracked：`ghostty`、`rag-orchestrator/tools/` 三支 | 無 | 別條工作線，**勿動** |
