# 統一部署 Runbook

> 涵蓋：對話式診斷＋五域對話面向（contract/billing/account/iot/estate）＋帳單診斷＋回測新架構＋
> 知識盤查修正＋使用量計量＋額度管制＋參數分工——**一批上**。依序執行 §0–§10，§11 為部署後掛帳。

| § | 步驟 | 性質 |
|---|---|---|
| 0 | 前置（備份＋安全開關） | 必做 |
| 1 | Migrations 36 支（單一序列，含計量/額度/盤查修正）＋資料修復＋知識補強重放 | 必做 |
| 2 | 知識批次匯入（12 份） | 必做 |
| 3 | 進場路由微調 | 必做 |
| 4 | 重建服務（含 semantic model 重抽） | 必做 |
| 5 | 煙囪驗證（20 面向） | 必做 |
| 6 | 回測新架構說明＋正式基準 | 部署後 |
| 7–9 | 計量／額度／參數分工（env 與驗證；migration 已併 §1） | 必做（隨版更） |
| 10 | `make audit` 不變量稽核 | **收尾必跑** |
| 11 | 部署後掛帳 | 追蹤 |
| 附錄A | **全庫搬遷路徑**（本機庫整顆搬 prod，取代 §1–§3） | 二選一 |

> **路徑二選一**：①逐支重放（§1–§3，prod 現庫上疊加）②全庫搬遷（附錄 A，本機庫即真相直接換庫）。
> 2026-07-07 使用者裁定走**全庫搬遷**——§1–§3 跳過，§0/§4–§10 照做。
> 更新：2026-07-07（migration 序列補全 36 支＋批次補列 12 份＋分支併版＋附錄 A 全庫搬遷）
> 原則：全部指令由使用者在 prod 執行（[[feedback_prod_ops_self_run]]）；migration 皆冪等，重跑安全。
> 前提：`feature/category-two-level` 已併入 **main**（bf67fba，2026-07-07）——**版更以 main 為準**
> （含 `services/jgb/bills.py` status 讀取優先序修正——**jgb2 prod 補正 bills 欄位前後皆相容**，fallback 保舊行為）。

## 0. 前置

```bash
# 0-1 備份 prod DB
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin | gzip > backups/pre_facets_$(date +%Y%m%d_%H%M).sql.gz
```

```bash
# 0-2 安全開關（上線必開）：RAG API 認證——未開時任何人可帶任意 role_id 直打我們的 API，
#     role 隔離只剩 jgb2 白名單單層。確認 prod env 有：
grep RAG_API_AUTH_ENFORCE <prod env>   # 應為已開；未開請設定後再部署
```

順帶檢查兩件先前掛帳（與本批無關但同機會處理）：chatflow 重構那批的 prod migration、`form_sessions.pending_question` 欄位 migration 是否已跑。

## 1. Migrations（依序 36 支，皆冪等；按 commit 時序排列——後出的 seed 覆蓋先出的，順序不可換）

> 2026-07-07 補全：原序列漏列 4 支合約/售前時代 migration（`backfill_contract_knowledge_diagnosis_category`／
> `seed_conversational_diagnosis_contract_rule`／`backfill_presales_synth_rules`／`seed_contract_entry_anchor_colloquial`），
> 並將 §7/§8 的計量/額度兩支與盤查修正一支併入單一序列。若 prod 曾跑過其中幾支，冪等重跑安全。

```bash
cd rag-orchestrator/database/migrations
for f in \
  split_base_system_context_extract_presales.sql \
  backfill_contract_knowledge_diagnosis_category.sql \
  seed_conversational_diagnosis_contract_rule.sql \
  seed_domain_contract_system_context.sql \
  add_contract_facet_categories.sql \
  backfill_presales_synth_rules.sql \
  seed_contract_entry_anchor_colloquial.sql \
  add_contract_facet_categories_v2.sql \
  seed_contract_facet_system_context.sql \
  seed_contract_facet_configs.sql \
  add_closeout_secondary_call.sql \
  update_closeout_archive_answer_rule.sql \
  backfill_contract_knowledge_facet_categories.sql \
  add_billing_facet_categories.sql \
  seed_billing_facet_system_context.sql \
  seed_billing_facet_configs.sql \
  backfill_billing_knowledge_facet_categories.sql \
  add_account_facet_categories.sql \
  seed_account_facet_system_context.sql \
  seed_account_facet_configs.sql \
  backfill_account_knowledge_facet_categories.sql \
  add_iot_facet_categories.sql \
  seed_iot_facet_system_context.sql \
  seed_iot_facet_configs.sql \
  backfill_iot_knowledge_facet_categories.sql \
  add_estate_facet_categories.sql \
  seed_estate_facet_system_context.sql \
  seed_estate_facet_configs.sql \
  backfill_estate_knowledge_facet_categories.sql \
  add_test_scenario_audience.sql \
  backfill_test_scenario_audience.sql \
  add_test_scenario_gold_checks.sql \
  seed_bill_diagnosis_facet.sql \
  audit_20260706_knowledge_fixes.sql \
  add_usage_events.sql \
  add_vendor_quotas.sql \
; do echo "== $f"; docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 < "$f" || break; done
```

每支結尾有 `RAISE NOTICE ✅` 自檢（計數／互斥），看到非預期數字先停。
（`create_digression_config.sql` 屬表單 v1.1 舊版更，prod 應已存在——§0 先前掛帳一併確認即可，不在本序列。）

**1.1 資料修復（一次性，冪等）**：歷史迴圈回測的 evaluation 雙重編碼（backtest_client 包兩層 JSON，
評級/逐字稿讀不到；2026-07-05 已修寫入端）——prod 套用：

```sql
UPDATE backtest_results SET evaluation = (evaluation #>> '{}')::jsonb
WHERE jsonb_typeof(evaluation)='string' AND left(evaluation #>> '{}',1)='{';
```

**1.2 金標改判（帳單診斷收編）**：已併入 `audit_20260706_knowledge_fixes.sql`（見 1.3）。

**1.3 盤查 2026-07-06 知識補強重放**（資料修正已由序列內 `audit_20260706_knowledge_fixes.sql` 完成——
錯誤知識 5 筆修正/3367 轉直答/金標改判等）。新知識 INSERT 需 embedding，用 import 工具重放：

```bash
# 檢索補強 2 筆（簽約前狀態差別＋取消點交邀請錨點）
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/audit/reports/audit-additions-import.json
# 缺口 3 主題（收款方式調整/發票時點/通知排查——通知排查列已由 migration 轉入 3367，import 會自動跳過重複）
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/audit/reports/gap-batch-import.json
# 錨點補欄位（import 工具 anchors 不帶 form_id）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
UPDATE knowledge_base SET categories=ARRAY['條件診斷：合約','狀態判斷'],
  target_user=ARRAY['property_manager','tenant'], form_id='jgb_contract_query', action_type='form_fill'
WHERE question_summary='取消點交邀請 取消點退邀請 收回邀請' AND form_id IS NULL;"
```

匯入後 semantic model 重抽（§4 已含）。盤查報告與豁免依據：`scripts/audit/reports/jgb-knowledge-audit-20260706.md`。

## 2. 知識批次匯入（12 份，均已人工審核通過）

工具：`rag-orchestrator/tools/import_facet_knowledge.py`（冪等；updates 重算 embedding、新知識/錨點含 embedding）。連線走環境變數，prod 主機上視實際埠位覆寫（tune_routing.py 同）：

```bash
export DB_HOST=localhost DB_PORT=5432 DB_PASSWORD=<prod密碼>
export EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings
```

```bash
# 先 dry-run 看清單，再真跑
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/contract-knowledge-batch.json --dry-run
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/contract-knowledge-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/contract-knowledge-batch-2.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/billing-knowledge-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/account-knowledge-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/account-anchors-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/iot-knowledge-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/iot-anchors-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/estate-knowledge-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/b2b-knowledge-batch.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/b2b-knowledge-batch-2.json
python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/askbad-rootfix-batch.json
```

（末兩份為 2026-07-05 閘門批：51 題抽驗長尾 7 筆＋ASK_BAD 根因批 1 修 3 補——2026-07-07 補列，原 runbook 漏收。）

（IoT 批次無後置步驟：雙角色單發維持 system_provider 業態——b2b 檢索為嚴格業態過濾、NULL 會隱形；先例 3435/3458 同慣例。）

註：3531/3532 滯納金修正在 billing 批次、3435-3439 帳號口徑修正在 account 批次的 updates 內，不用另跑。

## 3. 進場路由微調（合約 4 紅案資料側修正）

```bash
# 3388 untag／3402、3530 question 重嵌（需 EMBEDDING_API_URL 與 DB 環境變數）
python3 scripts/knowledge-batches/tune_routing.py
```

## 4. 重建服務（reranker 必重建——2026-06-21 教訓）

```bash
docker compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator semantic-model embedding-api
```

rag-orchestrator 重啟即清掉 in-process 的系統脈絡/config 快取。

semantic-model 重建說明（校正認知）：`/rerank`（檢索排序主路徑）是 request-time 對傳入候選打分，**不吃快照**——重建的目的是模型/程式版本與新 image 一致（2026-06-21 教訓）。快照 `data/knowledge_base.json` 僅餵 `/search`（目前 codebase 零呼叫者，死碼）且被 gitignore（建置產物）——若要讓它不腐，重建前在 prod 現場重抽（腳本已修復 vendor_ids schema，2026-07-04）：

```bash
cd semantic_model && DB_HOST=localhost DB_NAME=aichatbot_admin DB_USER=aichatbot DB_PASSWORD=<prod密碼> python3 scripts/extract_knowledge.py
```

## 5. 煙囪驗證（20 面向各一句，走正式入口真跑）

| 面向 | 驗證句 | 期望 |
|---|---|---|
| 合約異動 | 我想改合約 內容要修改 | 進對話追問識別 |
| 退租收尾 | 租客要退租了 接下來我要做什麼 | 進對話；ground 後含封存/點退步驟 |
| 續約 | 合約快到期了要怎麼續約 | 進對話 |
| 建約引導 | 我要簽新合約 怎麼開始建 | 進對話輕引導 |
| 簽署排障 | 租客一直簽不了約怎麼辦 | 進對話；ground 後帶效期判斷 |
| 狀態判斷 | 幫我看 {合約ID} 現在什麼狀態 | 直查機械解碼 |
| 繳費金流排障 | 租客說錢繳了 可是帳一直沒進來 | 進對話；給帳單號後按狀態分支、金額原樣 |
| 帳單異常 | 租客說他在系統裡看不到這期帳單 | 進對話；可見性機械判 |
| 發票 | 這期的發票一直沒開出來 | 進對話；按 invoice_status 判 |
| 滯納金 | 為什麼這個月滯納金收這麼多 | 進對話；兩機制講解 |
| 帳單設定引導 | 我要怎麼設定每個月幾號出帳單 | 進對話兩輪分流 |
| 註冊驗證排障 | 租客一直沒辦法註冊 卡住了 | 進對話分流；不得輸出驗證碼值 |
| 登入排障 | 租客說他登不進去系統 | 進對話；給合約號後照帳號現值判分支 |
| 帳號綁定異動 | 手機被綁定過了 要解綁換綁 | 進對話；收斂到申請書（service@jgbsmart.com） |
| 團隊成員權限 | 加了團隊成員 他什麼都看不到 | 進對話；指向成員列表「變更角色」 |
| 電表排障 | 電表一直離線 度數不動 | 進對話；照現值判因、不代操作 |
| IoT設定引導 | 電表要怎麼串接進系統 | 進對話輕引導 |
| 物件操作引導 | 改了對外顯示地址 怎麼還是顯示完整地址 | 進對話直答雙層行為（後台恆完整/對外頁才生效） |
| 物件現況診斷 | 物件為什麼不能建立合約 缺什麼欄位 | 進對話追問識別；給物件名後照現值列缺欄；查無走「非刊登中」口徑不斷言刪除 |
| 帳單診斷 | 帳單為什麼一直發不出去 | 進對話（**不得**觸發 v1.1 表單）；無編號→物件名→帳單候選→選序號→決定性判定（可否發送/取消/手動到帳） |

對照組（不得誤進對話）：「點退押金的找補費用在哪裡操作」「帳單可以批次匯入嗎 怎麼操作」「帳號要怎麼註冊 流程是什麼」「門鎖可以用悠遊卡嗎」「進階搜尋怎麼用」→ 單發直答。
物件域邊界對照：「這份合約的物件地址錯了要怎麼改」→ 不得進物件面向（合約域/資料異動方向）。

## 6. 回測新架構（部署後任跑）

前端需重建（dist 不入版控）：`cd knowledge-admin/frontend && npm run build`——8087 的「建立迴圈」表單才會出現「題庫（受眾）」選擇與回測結果的評級 UI。題庫選擇設計：建迴圈時選（業者=JGB知識/租客/售前），該迴圈的固定測試集即按題庫抽樣、下一批次自動繼承同題庫；回測請求形狀按題自動對應。

程式版更後 8087 後台「回測」按鈕即走新架構（v3 多輪感知評審＋按題受眾形狀——上兩支 migration 提供題庫標注）。建議部署後對 4,643 全庫跑一次建立正式基準線；舊 run 的 pass_rate 與新語義不可比。

## 7. usage-metering 使用量計量（2026-07-06）

migration（`add_usage_events.sql`）已含於 §1 序列尾端，本節只剩 env 與驗證。

- **env（皆有預設可不設）**：`USAGE_METERING_ENABLED`（預設 true；關=零行為差異）、
  `LLM_PRICING_PATH`（外部單價 JSON，缺省用內建表）、`USAGE_RETENTION_MONTHS`（預設 18）
- **版更檔**：app.py（middleware）、routers/chat.py（路徑標記）、services/llm_provider.py（token 鉤）、
  services/usage_metering.py（新）、admin app.py（/api/usage/* 端點，掛載即生效）、前端 npm run build
- **驗證**：真打一句 →`SELECT * FROM usage_events ORDER BY id DESC LIMIT 1` 事件到位（vendor/user_type/token/成本）；
  跑一題回測 → `is_internal=true, internal_kind='backtest'`；後台「使用量統計」頁有數字；`make audit` 不變量 5 綠
- **治理 SQL**：`scripts/usage/`（被遺忘權/內部重標/保留期清理，排程化掛帳）

## 8. quota-management 額度管制（2026-07-06）

migration（`add_vendor_quotas.sql`）已含於 §1 序列尾端。
疊在 usage-metering 上，opt-in——**未設額度的團隊零行為差異**。版更檔：app.py（middleware 擴充）、
services/usage_metering.py（quota 區段）、admin app.py（/api/usage/quotas CRUD）、前端 build。

驗證（可選，用測試額度）：對某 vendor 設低額度（後台「使用量統計→額度管理」）→ 真打三段：
正常→警示（b2b 回答尾端附 📊 額度提示）→ 達限（pm 加值引導/租客中性文案、action_type=quota_blocked、
事件 status='blocked' 不計額度）→ 調高額度下一句即恢復 → **驗畢停用測試額度**。
快取語義：warn/blocked 轉換最多延遲 60 秒；加值恢復即時（blocked 不走快取）。
**警示通知（2026-07-06 改判）**：警示不進對話、改寄信——prod 需設 `QUOTA_SMTP_HOST/PORT/USER/PASS/FROM`
＋`QUOTA_WARN_EMAIL_TO`（營運收件，逗號分隔；vendor 的 contact_email 有值會一併收）；
未設 SMTP 僅記 log 不寄。每 vendor 每月首次跨閾值寄一次（vendor_quotas.last_warned_month 防重）。
`QUOTA_WARN_IN_CHAT=true` 可重新啟用對話內附註（預設關）。

## 9. 參數分工定案＋lookup 錨點（盤查 20260706）

**分工**：`vendor_configs`＝通用資料（電話/LINE/營業時間等 vendor 級單值，param 模板注入）；
`lookup_tables`＝案場級/清單級（管理費/電費/包裹/廠商，Excel 統一匯入，錨點消費）。

- 版更檔：api_call_handler（key 空＋key2=全部＝整分類列出）、routers/lookup（匯入拒收「範例：」列）、
  vendor_parameter_resolver（預設讀 configs；`VENDOR_PARAMS_FROM_LOOKUP=true` 保留切換能力）
- **lookup 錨點 33 筆**：`python3 scripts/audit/reports/lookup-anchors-import.py`（冪等；需 embedding-api）
  → semantic model 重抽（§4 已含）；知識 1403 客服專線已改 configs 模板直答（隨知識批次）
- ⚠️ 前置：lookup 資料須業者核實（vendor 2 客服類疑似污染、vendor 3 configs demo 值），
  且重匯時依分工歸位——lookup 內的通用類殘留（LINE/服務中心/服務時間/繳費方式）移 configs 或刪除
- 驗證：「客服專線電話」→ configs 模板值；「管理員會代收包裹嗎」→ 該業者 lookup 明細

## 10. 不變量稽核（部署收尾必跑）

```bash
make audit   # = scripts/audit/check_invariants.sh，exit 非 0 = 有違規，修完重跑
```

六條不變量：動作知識必有面向接管（防「開關漏插」再犯——帳單診斷案根因）／
backtest evaluation 必為 JSON 物件／服務容器關鍵檔與 repo 一致（防舊引擎）／
面向必有系統脈絡／計量健全（內部流量漏標 FAIL、vendor 缺失 WARN）／
額度一致（幽靈攔截 FAIL、寬限燒錢 WARN）。
維護準則在腳本頭：修一類 bug＝加一條不變量；WARN 清單只准變短。

## 11. 部署後掛帳（不阻塞）

- **jgb2 串接規格 v3 的 AI 側配套**（`docs/jgb2-chat-integration.md` §8.1，2026-07-07 定案）：
  jgb2 端一律只送 `role_id` 不送 `vendor_id`——AI 側需 ①放寬 b2c 驗證層 `vendor_id` 必填
  ②新增 `role_id`→`vendor_id` 反查（`vendors.settings->>'jgb_role_id'`）。**jgb2 前端按 v3 改版前必須完成**，
  否則 b2c 請求會被 422 擋掉；現行 b2b（不帶 target_user）行為不受影響。前提：各業者 `jgb_role_id` 建妥。
- jgb2 **preview→master 併版**（G1–G4＋帳務欄位）：存在性驅動，併上當天對應分支自動增強，不用配合改版。
- G-gated 補測：billing 8.2*（VA 效期/取號狀態；滯納金屬客製排除）。contract 7.4（G5）與帳號 grounded 均已收案——**完整啟用共同條件：JGB Web 把登入成員 user_id 傳入 AI session**（viewer 整合議題）。
- 設定引導「調整語族」錨點：等知識缺口管線收真實 miss 句再補（已決議）。
- 帳號 G-A1/A2＋J 清單（5 條缺陷）已交付 jgb2（account-api-contract.md）：J1/J2 修復後帳號知識口徑可簡化。
- IoT J 清單已交付 jgb2（iot-api-contract.md）：J-I0 已修復並驗畢（2026-07-04）；J-I1~I3 依排程。
- estate G 清單已交付 jgb2（estate-api-contract.md）：G-E1（estates 放寬 is_open 過濾——現況診斷弱信號升級正面判定）選配；批次上傳範圍外（使用者裁定 2026-07-04，J-E1 已撤）。
- 物件域掛帳：3861 vs 3862 建約前提表面矛盾（續約/上傳既存合約可能不走 pick 入口）待 jgb2 盤查釐清；3357 舊批次知識含過時口徑（批次範圍外掛帳不動）。
- **SOP 角色隔離——已改判撤案（2026-07-05）**：原立案「租客向 SOP 攔截業者問句」經查為測試 harness 未帶 mode 的 artifact——生產隔離本已存在（jgb2 後台帶 mode='b2b'，chat.py:1633 b2b 不走 SOP；租客 b2c 走 SOP 受眾正確）。轉出並已收：錨點單發防呆（P0 程式修正）、e2e harness 全面補 mode='b2b'、b2b 知識補齊 3 件（3408 口徑補強＋退房換約＋電費六模式）。殘餘 G 掛帳：b2c＋property_manager 矛盾組合的呼叫端防呆警示（低優先）。煙囪驗證請以 mode='b2b' 發送業者句。

## 附錄 A：全庫搬遷路徑（2026-07-07 裁定採用；取代 §1–§3）

> 本機開發庫（知識/embedding/面向規則/系統脈絡/題庫/lookup/configs 全在裡面）即真相，
> 整顆搬上 prod。優點：不用逐支重放、不需 prod 跑 embedding；代價：**prod 現庫上、
> 本機沒有的資料會被蓋掉**。
> **2026-07-07 使用者裁定簡化：prod 備份後直接覆蓋**——A-1 盤點/A-5 回灌省略、A-4 藍綠換庫
> 簡化為 drop-restore（見 A-4 簡化版）；prod-only 資料若事後要撈，從 pre_swap 備份檔取。

### A-1. 盤點 prod-only 資料（prod 上跑，決定保留清單）

```sql
-- prod 與本機各跑一次，對比計數；prod > 本機的表就是要保留/回灌的候選
SELECT 'unclear_questions' t, count(*) FROM unclear_questions
UNION ALL SELECT 'vendor_sop_items', count(*) FROM vendor_sop_items
UNION ALL SELECT 'vendor_configs', count(*) FROM vendor_configs
UNION ALL SELECT 'lookup_tables', count(*) FROM lookup_tables
UNION ALL SELECT 'knowledge_base', count(*) FROM knowledge_base
UNION ALL SELECT 'conversation_logs', count(*) FROM conversation_logs
UNION ALL SELECT 'form_sessions', count(*) FROM form_sessions
UNION ALL SELECT 'usage_events', count(*) FROM (SELECT 1 FROM usage_events LIMIT 1) s;  -- prod 未上計量時此表不存在，報錯即 0
```

重點三類：①**unclear_questions**（prod 真人 miss 句，知識缺口管線的原料——prod 較多必先導出）
②**SOP／configs／lookup**（若 prod 後台在本機快照後有人工編修——比對 updated_at 最大值）
③form_sessions 屬暫態可棄。有差異的表先導出：

```bash
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin \
  -t unclear_questions --data-only -Fc -f /tmp/prod_only.dump   # 視盤點結果加 -t
```

### A-2. 本機出貨前清理（在本機庫執行，дump 前）

```sql
-- 計量歸零：本機測試事件不得成為 prod 計費痕跡（額度月計數也隨之乾淨）
TRUNCATE usage_events;
-- 測試額度清掉（prod 要用時由後台重設）
DELETE FROM vendor_quotas;
-- 暫態表
TRUNCATE form_sessions;
```

回測歷史（backtest_runs/results、迴圈）**保留**——搬上去即 8087 的基準線延續，內部流量標記完備不影響統計。

### A-3. 本機 dump → 傳輸

```bash
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin -Fc -f /tmp/aichatbot_full.dump
docker cp aichatbot-postgres:/tmp/aichatbot_full.dump ./aichatbot_full_$(date +%Y%m%d).dump
scp aichatbot_full_*.dump <prod主機>:~/
```

### A-4 簡化版（裁定採用）：備份後直接覆蓋

```bash
# 1) 備份現行（唯一回滾點，必做）
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin | gzip > backups/pre_swap_$(date +%Y%m%d_%H%M).sql.gz

# 2) 停打 DB 的服務（restore 期間停機）
docker stop aichatbot-rag-orchestrator aichatbot-knowledge-admin

# 3) 覆蓋：斷連線 → drop → 重建 → restore
docker cp aichatbot_full_*.dump aichatbot-postgres:/tmp/full.dump
docker exec aichatbot-postgres psql -U aichatbot -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='aichatbot_admin' AND pid<>pg_backend_pid();"
docker exec aichatbot-postgres dropdb -U aichatbot aichatbot_admin
docker exec aichatbot-postgres createdb -U aichatbot aichatbot_admin
docker exec aichatbot-postgres pg_restore -U aichatbot -d aichatbot_admin --no-owner /tmp/full.dump

# 4) 抽驗 → 起服務（§4 重建含重啟，可直接接 §4）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT count(*) FROM knowledge_base; SELECT count(*) FROM knowledge_base WHERE category='對話規則' AND is_active;"
```

回滾＝`dropdb`＋`createdb`＋灌回 pre_swap 備份檔。

### A-4 原案（藍綠換庫，停機窗＝rename 一瞬；備查不採用）

```bash
# 備份現行（回滾保險）
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin | gzip > backups/pre_swap_$(date +%Y%m%d_%H%M).sql.gz

# 還原到新庫（不動現庫，服務照跑）
docker cp aichatbot_full_*.dump aichatbot-postgres:/tmp/full.dump
docker exec aichatbot-postgres createdb -U aichatbot aichatbot_admin_new
docker exec aichatbot-postgres pg_restore -U aichatbot -d aichatbot_admin_new --no-owner /tmp/full.dump

# 抽驗新庫（knowledge_base 計數/對話規則 22 筆/pgvector 可查）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin_new -c \
  "SELECT count(*) FROM knowledge_base; SELECT count(*) FROM knowledge_base WHERE category='對話規則' AND is_active;"

# 換庫（先停打 DB 的服務 → 斷連線 → rename → 起服務）
docker stop aichatbot-rag-orchestrator aichatbot-knowledge-admin
docker exec aichatbot-postgres psql -U aichatbot -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname IN ('aichatbot_admin','aichatbot_admin_new') AND pid<>pg_backend_pid();
   ALTER DATABASE aichatbot_admin RENAME TO aichatbot_admin_old_20260707;
   ALTER DATABASE aichatbot_admin_new RENAME TO aichatbot_admin;"
```

回滾＝反向 rename（old 庫原封不動留著，確認穩定一週後再刪）。

### A-5. prod-only 資料回灌（A-1 有導出才做）

```bash
docker exec aichatbot-postgres pg_restore -U aichatbot -d aichatbot_admin --data-only /tmp/prod_only.dump
```

### A-6. 後續照本 runbook 主線

- **§4 重建服務＋semantic model 重抽**——換庫必做（[[project_deploy_semantic_model]]：reranker 與新庫不同步＝排序失真）
- §0-2 安全開關、§5 煙囪 20 面向、§7/§8 env（計量預設即開；SMTP 要寄警示信才設）、§10 `make audit`
- **跳過**：§1 migrations／§2 知識批次／§3 tune_routing（全在庫裡）；§9 只剩「業者資料核實」仍有效
