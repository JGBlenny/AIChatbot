# 統一部署 Runbook

> 涵蓋：對話式診斷＋五域對話面向（contract/billing/account/iot/estate）＋帳單診斷＋回測新架構＋
> 知識盤查修正＋使用量計量＋額度管制＋參數分工——**一批上**。依序執行 §0–§10，§11 為部署後掛帳。

---
## 🚩 現行部署路徑（先讀這個，不必往下翻）

**既有 prod 的增量部署＝只做這條（2026-07-22 §17 收斂後正統）：**
1. `git push origin main` → prod `git pull`（碼）
2. **帳本 bootstrap（§17-1，一次）→ `migrate.sh` dry-run 確認 → `--apply`**：自動跑 migration＋seed 並記帳（見 §17-2；本次＝§12–§15 的 8 支）
3. §4 重建（`up -d --build`，含 reranker）→ §5 煙囪 → §10 `make audit`
4. 破壞性 M2（`drop_knowledge_trigger_dead_columns`）**煙囪全過後才手動**

**🚫 勿執行（非增量部署路徑）：**
- **§1–§3**＝facet 大批逐支明細，**07-07 已整批上線**（prod 現有 facet 資料）→ 已移至文末 **附錄 Z**，僅供新環境建置參考。
- **附錄 A 全庫搬遷**＝**僅新環境建置**（空庫從 dump 還原）；drop-restore 會蓋掉 prod-only 計量歷史，勿用於既有 prod。

---

| § | 步驟 | 性質 |
|---|---|---|
| 0 | 前置（備份＋安全開關） | 必做 |
| 1–3 | facet 大批（migration 36 支＋知識 12 份＋路由微調）→ **已封存於附錄 Z** | 🚫 增量勿執行（歷史/建置專用） |
| 4 | 重建服務（含 semantic model 重抽） | 必做 |
| 5 | 煙囪驗證（20 面向） | 必做 |
| 6 | 回測新架構說明＋正式基準 | 部署後 |
| 7–9 | 計量／額度／參數分工（env 與驗證；migration 已併 §1） | 必做（隨版更） |
| 10 | `make audit` 不變量稽核 | **收尾必跑** |
| 11 | 部署後掛帳 | 追蹤 |
| 12 | trigger-vocabulary-debt（觸發語彙還債 P0） | 隨版更（2026-07-11 增補） |
| 13 | conversational-repair（對話式報修面向） | 隨版更（2026-07-12 增補） |
| 14 | brain-kb-grounding（Brain 掛 search_kb） | 隨版更（2026-07-21 增補） |
| 15 | 進場路由基準調校（keywords 衛生） | 隨版更（2026-07-22 增補） |
| 17 | **migration 帳本與體系收斂（現行正統：runner `migrate.sh`＋`schema_migrations` 記帳）** | **2026-07-22 定** |
| 19 | agentic-mcp（M0–M1）部署：相依升級、五支 migration、內部 MCP key、售前池審核、env、煙囪、回切、監控 | 隨版更（2026-09-05 增補） |
| 附錄A | 全庫搬遷路徑（**僅新環境建置**：空庫從 dump 還原） | 建置專用 |

> **⚠️ 部署路徑（現行正統，2026-07-22 §17 收斂後）——先讀這段，勿被下方歷史紀錄誤導：**
> - **既有 prod 增量部署（一般情況、本批適用）**：migration／seed 一律走 **runner `migrate.sh`**（dry-run→`--apply`，自動記帳；見 §17）。`run_migrations.sh`／`migrations-legacy` 已於 07-22 除役，勿用。
> - **附錄 A 全庫搬遷＝僅限新環境建置**（空庫從 dump 還原）；**不用於既有 prod 增量更新**（drop-restore 會覆蓋 prod-only 資料，如計量歷史）。
> - §1–§3 為 **facet 大批**的逐支明細（歷史參考；該批已於 07-07 以全庫搬遷上線完成，prod 現有 facet 資料）。
>
> ~~2026-07-07 裁定走全庫搬遷、§1–§3 跳過~~ ← **已被 §17 取代**：該裁定專指 07-07 的 facet 大批（已完成），**非往後通則**。往後新 migration 走 §17 逐支＋帳本。
> 更新：2026-07-22（§17 兩套體系收斂；本段路徑說明改寫）
> 原則：全部指令由使用者在 prod 執行（[[feedback_prod_ops_self_run]]）；migration 皆冪等，重跑安全。
> 前提：`feature/category-two-level` 已併入 **main**（bf67fba，2026-07-07）——**版更以 main 為準**
> （含 `services/jgb/bills.py` status 讀取優先序修正——**jgb2 prod 補正 bills 欄位前後皆相容**，fallback 保舊行為）。

## 0. 前置

```bash
# 0-1 確認起點 commit（核對部署範圍；記下來供追溯）
git rev-parse --short HEAD
```

```bash
# 0-2 備份 prod DB（動任何 DB 前必做；災難快照）
mkdir -p backups
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin | gzip > backups/pre_deploy_$(date +%Y%m%d_%H%M).sql.gz
ls -lh backups/pre_deploy_*.sql.gz | tail -1   # 驗證：檔案在、大小非 0（幾十 MB 才正常；0/幾 KB＝dump 失敗）
# 還原（萬一）：gunzip -c backups/pre_deploy_<時間戳>.sql.gz | docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin
```

```bash
# 0-3 安全開關（上線必開）：RAG API 認證——未開時任何人可帶任意 role_id 直打我們的 API，
#     role 隔離只剩 jgb2 白名單單層。確認 prod env 有：
grep RAG_API_AUTH_ENFORCE <prod env>   # 應為已開；未開請設定後再部署
```

> **⚠️ 驗證用 curl 一律要帶金鑰（因 0-3 認證已開）**：本 runbook 所有「直接打 rag（`localhost:8100`）」的驗證 curl（§5 煙囪／§12-3／§13／§14…），因 `RAG_API_AUTH_ENFORCE=true`，**未帶 `X-API-Key` 會被 401**（非功能故障，是認證擋下）。跑任何驗證前先設一次金鑰變數：
> ```bash
> K=$(grep '^RAG_ADMIN_API_KEY=' .env | cut -d= -f2-)   # §16 發行的後台代理金鑰
> ```
> 然後每個驗證 curl 補上 `-H "X-API-Key: $K"`。（若改走 UI／jgb2 前端測則免帶——nginx 會自動注入。）

順帶檢查兩件先前掛帳（與本批無關但同機會處理）：chatflow 重構那批的 prod migration、`form_sessions.pending_question` 欄位 migration 是否已跑。

## 1–3. facet 大批逐支明細 → 已移至【附錄 Z】

> 🚫 **既有 prod 增量部署勿執行**。§1–§3 是 facet 大批（合約/帳單/帳號/IoT/物件面向）的逐支 migration／知識匯入／路由微調明細，**07-07 已整批上線**（prod 現有 facet 資料）。完整內容封存於文末 **附錄 Z：歷史批次（勿執行，僅新環境建置參考）**。增量部署請照頂部「🚩 現行部署路徑」。

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

## 12. trigger-vocabulary-debt（觸發語彙還債 P0）（2026-07-11）

修斷鏈（檢索層透傳 `trigger_mode`/`trigger_keywords`/`immediate_prompt`——manual 觸發配置終於生效，
命中先等關鍵詞確認、不再直觸發表單）＋ `usage_events` 檢索仲裁分數埋點
（`knowledge_score`/`sop_score`/`decision_case`，灰帶分析原料）＋ `knowledge_base` 三個死欄位清理。
零行為改變原則：仲裁邏輯/門檻（0.55/0.6/0.75）/消費邏輯一行未動；分數是計量加值欄位——
欄位偵測保護，M1 未跑時事件本體照舊完整寫入。

**部署順序：M1 → 重建 rag-orchestrator → 煙囪 → M2（破壞性，操作者確認煙囪全過後手動執行）**

```bash
# 12-1 M1（加性、冪等）：usage_events 加三個分數欄
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/add_usage_events_scores.sql
# 結尾自檢 RAISE NOTICE 應為「✅ … 3 / 3 欄就緒」

# 12-2 重建 rag-orchestrator image
docker compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator
```

> ⚠️ **常駐 rag 容器是舊 image，本案生效必須重建**（不重建＝透傳與埋點皆不上線，
> manual 知識靜默降級為直觸發；`make audit` 不變量 3 也會抓到容器/本地不一致）。
> **semantic-model 免重建**：本案不動 embedding／知識語料（透傳＋計量欄＋刪零資訊死欄位），
> reranker 的模型與輸入無變化——與 §4 換庫情境不同，不適用重抽規則。

**12-3 煙囪**（M2 之前必過）：

```bash
# ① 一則真 b2c 請求（走 SOP↔知識檢索仲裁）→ 事件帶分數
SID="smoke_tvd_$(date +%s)"
curl -sS -X POST http://localhost:8100/api/v1/message -H "Content-Type: application/json" \
  -d "{\"message\": \"我要繳房租\", \"vendor_id\": 2, \"mode\": \"b2c\", \"target_user\": \"tenant\", \"session_id\": \"$SID\"}"
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT knowledge_score, sop_score, decision_case FROM usage_events ORDER BY id DESC LIMIT 1;"
# 期望：分數欄帶 0–1 數值、decision_case 為既有仲裁識別字串
# （knowledge_significantly_higher / sop_significantly_higher / only_knowledge_qualified …）

# ② 短路路徑（b2b 請求，早退不經仲裁）→ 分數 NULL、事件其餘欄位照舊完整
SID="smoke_tvd_b2b_$(date +%s)"
curl -sS -X POST http://localhost:8100/api/v1/message -H "Content-Type: application/json" \
  -d "{\"message\": \"我要繳房租\", \"vendor_id\": 2, \"mode\": \"b2b\", \"target_user\": \"property_manager\", \"role_id\": \"37305\", \"session_id\": \"$SID\"}"
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT knowledge_score, sop_score, decision_case FROM usage_events ORDER BY id DESC LIMIT 1;"
# 期望：三欄皆 NULL（vendor/token/成本等本體欄位仍齊全）
```

③（可選，完整驗證 manual 觸發全流程）——自動化 e2e 已於開發環境收案
（`tests/e2e/chat_flow/test_trigger_manual_flow_e2e_req.py`，task 5.1，fixture 自建自清；
需宿主直跑 pytest＋另起臨時 rag 容器，不適合照搬 prod 現場）。現場驗證照 e2e 同流程手動走：
建一筆 `trigger_mode='manual'`＋`trigger_keywords` 的表單測試知識（後台建立即含 embedding）→
問句命中 → 應**等待確認**（不直觸發表單、回應含關鍵詞引導）→ 回覆關鍵詞 → 表單觸發 →
另起 session 命中後回非關鍵詞 → 不觸發 → **驗畢刪除該測試知識**。

```bash
# 12-4 M2（⚠️ 破壞性：DROP COLUMN ×3——由操作者確認煙囪全過後手動執行，不得由自動化流程觸發）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/drop_knowledge_trigger_dead_columns.sql
# 自檢 RAISE NOTICE「✅ M2 完成」；刪除對象 trigger_form_condition / trigger_conditions / auto_keywords
# （全庫 grep 零引用＋資料全為預設值零資訊，雙重盤點見 spec gap-analysis）

# 反悔：rollback 可回復欄位/約束/索引結構——資料不可回復（已接受，原內容零資訊）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/rollback/rollback_drop_knowledge_trigger_dead_columns.sql
```

收尾照 §10 `make audit`（新增的知識 dict 契約測試在 unit 套件，隨 `make test`/CI 自動把關）。

## 13. conversational-repair（對話式報修面向）（2026-07-12）

對話式報修：引擎新增 confirm/execute 語義分支＋接線（image 辨識併槽／插點 A 預填／埋點）＋
面向配置與意圖錨點知識資料＋3 支 migration（M2 停租客修繕 SOP、M3 埋點兩欄）。
唯一新 chat API 選填參數 `trigger_facet_key`（命中 config registry 即直達面向）。
零回歸原則：既有 FAQ 快路徑／五域診斷面向／prospect／非修繕表單邏輯一行未動。

**部署順序：M3 → 面向配置＋知識 seeds → 推程式（image rebuild）→ 煙囪 → M2（破壞性，操作者手動）→ 四業者驗收矩陣**

> **M1 免辦**：原規劃 `form_schemas` vendor_id 2→NULL 的 migration，經 dev DB ＋ prod dump
> （`aichatbot_full_20260707.dump`）雙查證，vendor_id 均已為 NULL＝目標態，**不需執行**（tasks.md 收案註記同）。

```bash
# 13-1 M3（加性、冪等）：usage_events 加 facet_key/turn_number 兩欄
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/20260711_usage_events_facet_columns.sql
# 自檢：SELECT column_name FROM information_schema.columns
#       WHERE table_name='usage_events' AND column_name IN ('facet_key','turn_number'); → 兩列
# （欄位偵測保護：M3 未套時計量事件本體照舊完整寫入，僅兩欄略過。）

# 13-2 面向配置＋意圖錨點知識 seeds
#   ① 面向對話規則列＋grounding_scope 全鍵（execute_endpoint/required_slots/confirm_template/
#      inference_confidence/prefill_api/degraded_messages/candidate_max/enabled_gate/facet_key）
#      ——已含 e2e 輪修正版本（target_user @> persona_role 撈規則、扁平標量槽映射）。
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/seed_repair_facet_config.sql
#   ② 意圖錨點知識＋查進度知識（embedding 走 embedding-api，須先在線）。
docker exec aichatbot-rag-orchestrator python3 tools/seed_repair_facet_knowledge.py

# 13-3 推程式（常駐 rag 容器是 baked image；本案生效必須重建）
docker compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator
```

> ⚠️ **常駐 rag 容器是舊 image，本案生效必須重建**（不重建＝confirm/execute 分支、預填、埋點皆不上線；
> `make audit` 不變量 3 也會抓到 `services/conversational_engine.py`／`routers/chat.py`／
> `services/usage_metering.py`／`services/jgb_system_api.py`／`services/llm_answer_optimizer.py` 容器/本地不一致）。

> **semantic-model／reranker 免重建——查證結論（不抄任務假設）**：
> semantic-model 是 **stateless cross-encoder**（BAAI/bge-reranker-base）：rag-orchestrator 呼 `/rerank`，
> 把候選的 `question_summary` 隨請求本體送去，模型逐 `[query, question_summary]` pair 即時 `model.predict` 打分——
> **不持有語料庫、不持索引、不存預算文件向量**（`/search` 端點才吃啟動載入的 knowledge_base JSON，本系統不走該端點）。
> 故新增錨點知識**不需重抽/重建 reranker**，也**不需 `/reload`**——與 §4 換庫「reranker 與新庫不同步」情境本質不同。
>
> **但要清 redis 檢索快取**：rag-orchestrator 的 `CacheService`（`services/cache_service.py`）以
> `rag:question:{vendor_id}:{target_user}:{hash}` 快取整包 RAG 答案（question_cache TTL 3600s＝1h）。
> 不清的話，錨點知識入庫前已被快取的報修觸發問句會續發**舊答案**最長 1 小時。上線後對受影響業者清一次：
> ```bash
> # 逐業者失效（建議）——只清該 vendor 的檢索快取，不動其他
> docker exec aichatbot-rag-orchestrator python3 scripts/clear_vendor_cache.py <vendor_id>
> # 或整包 question 命名空間 flush（急用）：redis DEL rag:question:*
> ```
> 附註：`conversational_config` 另有進程級快取（`_cache`，啟動載入一次）——13-3 重建 image＝全新進程，seed 自動生效，無需額外處置。

**13-4 煙囪**（M2 之前必過）：情境 A（單一租約、圖片高信心）真跑一輪，確認①面向接管報修對話②埋點入庫。

```bash
SID="smoke_repair_$(date +%s)"
# 直達面向：trigger_facet_key=repair_create（或以報修意圖問句命中錨點；正確鍵以 config registry 為準）
curl -sS -X POST http://localhost:8100/api/v1/message -H "Content-Type: application/json" \
  -d "{\"message\": \"我家冷氣壞了要報修\", \"vendor_id\": 1, \"mode\": \"b2c\", \"target_user\": \"tenant\", \"role_id\": \"<真租客 role>\", \"session_id\": \"$SID\", \"trigger_facet_key\": \"repair_create\"}"
# 期望：回應為報修面向對話（澄清/確認摘要），非 FAQ 直答。
# 埋點入庫確認：
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT facet_key, turn_number, session_id FROM usage_events WHERE session_id='$SID' ORDER BY id DESC LIMIT 3;"
# 期望：facet_key='repair'、turn_number 有值（隨輪次遞增）。
```

```bash
# 13-5 M2（⚠️ 破壞性可逆：停 vendor 24 租客修繕 SOP，改由對話面向接管——
#       由操作者確認 13-4 煙囪全過後手動執行，不得由自動化流程觸發；rollback 備妥）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/20260711_disable_repair_sop_vendor24.sql

# 反悔：回復停用的 SOP 觸發
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/rollback/20260711_disable_repair_sop_vendor24.rollback.sql
```

**13-6 四業者驗收矩陣**：宿主直跑 `RUN_E2E=1`（fixture 自建自清，需臨時 rag 容器；不照搬 prod 現場）——

```bash
RUN_E2E=1 scripts/run-tests.sh e2e tests/e2e/conversational/test_repair_vendor_matrix_e2e_req.py
```

### 13-7 prod 部署另需盤查（環境相依，非 migration）

- **`vendor_configs.repair_enabled`**：面向進場 gate（`enabled_gate`）讀此鍵，**預設開、不需建**（缺鍵＝視同開）。
  要對特定業者關閉才需顯式設 false。
- **客服管道參數 `service_hotline`**：任何報修回應模板引用「客服專線／`{service_hotline}`」時由此鍵替換。
  **dev 現況：active 業者 1／2／3 已有，業者 4（JGB TW-住宅）缺**——prod 上線前對缺鍵業者補齊，
  否則引用該鍵的答案會渲染未解析佔位字。查法：
  ```bash
  docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
    "SELECT v.id, v.name, EXISTS(SELECT 1 FROM vendor_configs vc WHERE vc.vendor_id=v.id AND vc.param_key='service_hotline' AND vc.is_active) AS has_hotline FROM vendors v WHERE v.is_active ORDER BY v.id;"
  ```
- **E1（JGB 真 API）是上線 gate**：現以 `USE_MOCK_JGB_API=true` 驗流程；`get_tenant_contracts` 等真端點
  對接前，插點 A 租約預填走 mock。真端點需求已列 J 清單（掛帳待 jgb2）。

### 13-8 輪數承諾與覆核觸發

上線後 SLO：**P50 ≤ 4／P90 ≤ 6**（含岔題）。未達標＝面向對話發散，觸發設計覆核。以埋點 SQL 週期量測：

```sql
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY mx) AS p50,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY mx) AS p90
FROM (SELECT MAX(turn_number) mx FROM usage_events WHERE facet_key='repair' GROUP BY session_id) t;
```

收尾照 §10 `make audit`（不變量 4 對 `修繕報修` category 會 WARN「查無系統脈絡知識」——
本面向為交易型／輕引導型：靠意圖錨點＋config＋表單填槽推進，**不需**「系統脈絡：」長文脈絡，屬**預期免脈絡**，非缺漏）。

## 14. brain-kb-grounding（Brain 掛載 search_kb 工具）（2026-07-20）

對話面向 Brain（`conversational_step`）改 async 並掛載 OpenAI function calling 工具 `search_kb`：
交易面向（`_tx`，目前＝修繕）對話中遇事實性岔題（費用/時程/規定）時，Brain 呼叫既有知識庫
檢索（pgvector＋reranker 零改動、脈絡與 FAQ 主路徑同源）查了再答，使 `inline_answer` 從
憑印象升級為知識庫背書。診斷面向不掛工具（行為與現狀完全一致）。純唯讀、寫入 gate 不動。

**部署順序：M（search_kb_status 欄，加性）→ 推程式（rebuild）→ 煙囪（費用岔題）→ 驗收 SQL**

```bash
# 14-1 M（加性、冪等）：usage_events 加 search_kb_status 單欄
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/20260720_usage_events_search_kb_status.sql
# 自檢：SELECT column_name FROM information_schema.columns
#       WHERE table_name='usage_events' AND column_name='search_kb_status'; → 一列
# （欄位偵測保護：M 未套時計量事件本體照舊完整寫入，僅此欄略過 → 部署順序皆安全。）
# 反悔：< rag-orchestrator/database/migrations/rollback/20260720_usage_events_search_kb_status_rollback.sql

# 14-2 推程式（常駐 rag 容器是 baked image；本案生效必須重建）
docker compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator
```

> ⚠️ **常駐 rag 容器不重建＝工具圈不上線**（`conversational_step` 仍為舊 sync 版、Brain 不掛工具；
> `make audit` 不變量 3 也會抓 `services/llm_answer_optimizer.py`／`services/conversational_engine.py`／
> `services/usage_metering.py` 容器/本地不一致）。**semantic-model／reranker 免重建**（檢索管線零改動，
> 同 §13 查證結論）。**redis 檢索快取免特別清**（本案不改知識內容、不改檢索結果，只多一個內部呼叫方）。

**14-3 煙囪**（費用岔題實跑一輪，確認查庫落地＋埋點）：

```bash
SID="smoke_kbtool_$(date +%s)"
# 修繕面向對話中岔題問費用（先進面向、再岔題）——此處直接以直達參數進面向後問費用
curl -sS -X POST http://localhost:8100/api/v1/message -H "Content-Type: application/json" \
  -d "{\"message\": \"馬桶不通，這修理要收費嗎\", \"vendor_id\": 1, \"mode\": \"b2c\", \"target_user\": \"tenant\", \"role_id\": \"<真租客 role>\", \"session_id\": \"$SID\", \"trigger_facet_key\": \"repair_create\"}"
# 期望：回應先答費用（與知識庫費用歸屬知識一致、非憑印象），再接回槽位收集。
# 埋點入庫確認：
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT search_kb_status, facet_key, session_id FROM usage_events WHERE session_id='$SID' ORDER BY id DESC LIMIT 3;"
# 期望：該岔題輪 search_kb_status='hit'（庫中有費用知識時）或 'miss'（查無時誠實回退）。
```

### 14-4 環境變數與快速回退

- **`KB_SIMILARITY_THRESHOLD`**（沿用既有，預設 0.55）：`search_kb` 與 FAQ 主路徑同源閾值，不另設。
- **`SEARCH_KB_ENABLED`**（可選，預設 true）：設 `false` → 交易面向不注入工具＝**即時回退現行行為**（Brain 憑規則答岔題），
  免重推程式、免 migration 回復。prod 若發現工具圈延遲或幻覺異常，先關此開關止血再排查。

### 14-5 驗收 SQL（R5.2/R5.3：呼叫率／命中率／P90 延遲增量）

```sql
-- 岔題輪工具呼叫率＋命中率（切分鍵＝search_kb_status）
SELECT facet_key,
       count(*) FILTER (WHERE search_kb_status IS NOT NULL)::float / NULLIF(count(*),0) AS call_rate,
       count(*) FILTER (WHERE search_kb_status = 'hit')::float
         / NULLIF(count(*) FILTER (WHERE search_kb_status IS NOT NULL), 0) AS hit_rate
FROM usage_events WHERE facet_key IS NOT NULL GROUP BY facet_key;

-- 工具輪 vs 一般輪 P90 延遲（增量＝前者−後者，目標 ≤3s；超標觸發設計覆核）
SELECT percentile_disc(0.9) WITHIN GROUP (ORDER BY duration_ms)
         FILTER (WHERE search_kb_status IS NOT NULL) AS p90_tool_turn,
       percentile_disc(0.9) WITHIN GROUP (ORDER BY duration_ms)
         FILTER (WHERE search_kb_status IS NULL) AS p90_plain_turn
FROM usage_events WHERE facet_key IS NOT NULL;
```

收尾照 §10 `make audit`。B 區數據（call_rate/hit_rate/事實一致性）供 A 區（進場路由 agent 化，
前置於回測現代化，另案）評估引用。

## 15. 路由調校：keywords 衛生＋口語錨點（2026-07-22）

進場路由 13 案誤路由修正（根因＝關鍵字加成飽和塌陷：裸泛詞 keywords 對整族問句
加成 ×1.1–1.3 並 cap 於 1.0，多列同分後排序亂決）。純資料調校，**零程式改動**：
21 列 keywords 修剪＋4053 補 IoT設定引導＋口語錨點 4 筆＋2 筆測試期望更新
（帳單為什麼發不出去 改判進帳單診斷——7/6 面向立案後的歸屬）。

**部署順序：M（資料調校）→ 重嵌 4 錨點 → 清檢索快取 → 路由回歸驗證**

```bash
# 15-1 M（冪等；id＋question_summary 雙重定位，錯位即 no-op 安全跳過）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/20260722_routing_keyword_hygiene.sql
# 自檢：NOTICE 顯示「路由調校錨點：4 筆」
# 反悔：< rag-orchestrator/database/migrations/rollback/20260722_routing_keyword_hygiene_rollback.sql

# 15-2 重嵌 4 筆錨點（migration 不填 embedding；到知識後台把 4 筆各重存一次，
#      或跑缺嵌補算——錨點 question_summary：
#      註冊名字跟證件不符 要怎麼改資料／想改合約租期 租金要調整／
#      合約狀態怪怪的 不太對勁／租客儲值了電還是沒有來 沒復電）

# 15-3 清檢索快取（keywords 變更影響加成計分，舊快取答案作廢）
python3 scripts/clear_vendor_cache.py   # 或照既有清快取慣例

# 15-4 驗證：路由回歸 83 案全綠
RUN_INTEGRATION=1 ... pytest tests/integration/conversational/test_facet_entry_routing_req.py
```

> ⚠️ **既有列免重嵌**（只動 keywords/categories，不參與向量）；**reranker 照 §4 認知**
> （/rerank 為 request-time 打分，不吃快照；本案無 image 推版則免動）。
> 教訓入庫：新知識批次補入時 **categories 標注與 keywords 衛生是路由的一部分**——
> 裸泛詞（合約/帳單/租客/點退/註冊/物件/儲值）不得單獨作 keyword（jieba 斷詞交集匹配，
> 一個裸詞=整族問句加成 30%）；掛面向分類的列＝路由器，教學列亂掛=誤進場。

## 16. 後台「登入即被踢」修復：/rag-api 認證通道（2026-07-22）

**根因**：7/7 部署同時上了後台 JWT 認證與 `RAG_API_AUTH_ENFORCE=true`，但後台頁面
會呼叫 `/rag-api/*`（nginx 轉發 rag）——無金鑰被 rag 拒 401，前端全域 401 攔截器誤判
為登入過期 → 清 token 踢回登入頁。**每次登入必踢**（rag log 與登入時刻逐秒對齊坐實）。
dev 未開強制所以測不到。

**修法**：nginx `auth_request` 以後台 JWT（前端本就自動附帶）向 admin-api `/api/auth/me`
驗身分，驗過才轉發 rag 並於**伺服器端**注入 `X-API-Key`（api_keys 表發行；金鑰只存
.env 與 nginx 記憶體，不進版控/瀏覽器；未登入與掃描器 403）。
改動：`nginx.conf` → `nginx.conf.template`（envsubst）＋compose 掛載/環境變數＋
`main.js` fetch 包裝器補 `/rag-api` 前綴（影片上傳走裸 fetch）。

**部署（jgb2-ai-chatbot 主機）：**

```bash
cd /home/ec2-user/AIChatbot && git pull

# 16-1 發行金鑰（產生→入庫→寫 .env）
KEY=$(python3 -c "import secrets;print('rgk_'+secrets.token_urlsafe(32))")
HASH=$(python3 -c "import hashlib;print(hashlib.sha256('$KEY'.encode()).hexdigest())")
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "INSERT INTO api_keys (name, key_hash, key_prefix, description, is_active)
   VALUES ('admin-web-proxy', '$HASH', '${KEY:0:8}', '後台 nginx /rag-api 代理注入', TRUE);"
echo "RAG_ADMIN_API_KEY=$KEY" >> .env

# 16-2 金鑰自檢（直打 rag，強制開啟下應 200）
curl -s http://localhost:8100/api/v1/business-types-config -H "X-API-Key: $KEY" \
  -o /dev/null -w '%{http_code}\n'   # 期望 200

# 16-3 重建前端 dist（main.js fetch 修正）＋重開 admin-web（載入模板）
cd knowledge-admin/frontend && npm ci && npm run build && cd ../..
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps knowledge-admin-web

# 16-4 驗收
docker exec aichatbot-knowledge-admin-web grep -c auth_request /etc/nginx/conf.d/default.conf  # ≥2
curl -s http://localhost/rag-api/v1/business-types-config -o /dev/null -w '%{http_code}\n'      # 403（未登入擋下）
# 瀏覽器登入後台 → 不再被踢、知識頁業態/表單正常載入、影片上傳可用
```

**回退**：compose 還原 nginx.conf 掛載（git 歷史有原檔）重開 admin-web；或暫關
`RAG_API_AUTH_ENFORCE`（同 7/7 前風險：rag 對 nginx 通道無保護）。
已於本機同款 compose 端到端驗證（無 token 403／帶 JWT 200＋金鑰注入）。

## 17. migration 帳本與體系收斂（2026-07-22 裁定）

**收斂為一版**：唯一正統＝`rag-orchestrator/database/migrations/`（SQL）＋`rag-orchestrator/database/seeds.manifest`（需 embedding 的知識 seed）＋**帳本感知 runner `rag-orchestrator/database/migrate.sh`**；執行帳本＝`schema_migrations` 表。編號系列（`database/migrations-legacy/`）與 `run_migrations.sh` 於 2026-07-22 除役；**「逐支手動貼 psql／手動 INSERT 記帳」的舊做法亦於 2026-07-25 由 runner 取代——migration/seed 一律走 runner**（解決「prod 套了沒」不可考：pending_question／search_kb_status 皆踩過）。

### 17-1 帳本 bootstrap（既有 prod 首次上 runner 前跑一次；全新環境免此步）
prod 的 facet 大批早於帳本存在，需先回填標記為已套，runner 才不會誤重跑：
```bash
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/20260722_schema_migrations_ledger.sql
# 預期 NOTICE:✅ migration 帳本就緒
```

### 17-2 用 runner 部署 SQL＋seed（現行正統，取代逐支手動貼）
```bash
# ① dry-run：看 SQL＋seed 待辦，不寫任何東西
bash rag-orchestrator/database/migrate.sh
# ② 確認清單無誤 → 真跑（seed 批需 DB 密碼＋embedding 網址）
export DB_HOST=localhost DB_PORT=5432 DB_PASSWORD=<prod密碼>
export EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings
bash rag-orchestrator/database/migrate.sh --apply
```
runner 行為：讀帳本 → 只跑未套 `.sql`（逐支 `ON_ERROR_STOP`、成功即自動記帳）→ 跑 `seeds.manifest`（`once` 記帳／`always` 每次跑）；**破壞性支（DROP/TRUNCATE）自動跳過**，留待 17-3 手動。出錯即停、失敗不記帳——修好重跑即可（冪等，已成功的自動跳過）。

### 17-3 破壞性支手動收尾（runner 跳過的；煙囪全過後才跑）
```bash
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin -v ON_ERROR_STOP=1 \
  < rag-orchestrator/database/migrations/drop_knowledge_trigger_dead_columns.sql
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "INSERT INTO schema_migrations(migration_name,created_by) VALUES('drop_knowledge_trigger_dead_columns','runbook') ON CONFLICT DO NOTHING;"
```

### 17-4 查帳（某支套了沒）
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT migration_name, executed_at, created_by FROM schema_migrations ORDER BY executed_at DESC LIMIT 10;"
```

**衛生規則**：新 migration 檔名一律 `YYYYMMDD_` 前綴（runner 靠檔名排序＝時序）；需 embedding 的知識 seed 宣告於 `seeds.manifest`（一行一支：`模式<TAB>帳本名<TAB>指令`，`once`＝跑一次記帳／`always`＝每次跑不記帳）；rollback 檔放 `migrations/rollback/`；帳本只記前向支，rollback 執行時 DELETE 對應帳紀錄。runner 四路徑＋seed 批已於 2026-07-25 以丟棄庫驗證。

## 18. 客服回報修正批 20260731（assistant-reports R-31~R-37）

依據：`docs/backtest/assistant-report-regression.md`（批次 20260731，本機 10 測全綠）。
內容：①R-33 知識錯誤修正（已發送應到帳可收回）②T-1 查資料型知識補面向分類＋收據錨點 ③R-32/34/36 新知識三筆 ④B-1 fallback 缺 `service_hotline` 不吐佔位符（程式修正，含在 image 重建）。

### 18-1. 碼與 migration

```bash
cd /home/ec2-user/AIChatbot
git pull   # 需含 20260731 客服回報修正批 commit

# dry-run 確認列出三支（create_digression_config 為已記帳 legacy，不應再列）
bash rag-orchestrator/database/migrate.sh
# 預期：🔸 待跑：20260731_assistant_report_fixes ＋ 20260803_batch24_standard_answers
#              ＋ 20260803_variant_robustness（共三支，依檔名序執行）

bash rag-orchestrator/database/migrate.sh --apply
# 預期：20260731 支＝UPDATE 1 / UPDATE 1 / UPDATE 3 / UPDATE 1 ＋ INSERT 0 1 × 5；
#       20260803_batch24 支＝INSERT 0 1 × 16 ＋ UPDATE 1 × 2（雙人簽約矛盾調和）
#         ＋末段三筆摘要口語化 UPDATE（對本批新插列可能顯示 UPDATE 0，正常）；
#       20260803_variant_robustness 支＝UPDATE 1 × 10 ＋ INSERT 0 1 × 1；皆記帳
```

### 18-2. 補嵌（約 24 筆新知識/錨點/改名列，容器內跑）

```bash
docker cp rag-orchestrator/tools/embed_missing.py aichatbot-rag-orchestrator:/app/tools_embed_missing.py
docker exec aichatbot-rag-orchestrator python3 /app/tools_embed_missing.py
# 預期：缺 embedding 的列約 24 筆（新增 21＋既有列改名清嵌 3406/3926＋續約錨點）→ 完成
```

### 18-3. 重建服務（載入 chat.py fallback 修正）

```bash
docker compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator
```

### 18-4. 業者 service_hotline 補值（資料側，B-1 第二層）

```bash
# 查缺值的 active 業者
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT v.id, v.name FROM vendors v WHERE v.is_active AND NOT EXISTS \
   (SELECT 1 FROM vendor_configs c WHERE c.vendor_id=v.id AND c.param_key='service_hotline' AND c.is_active);"
# 缺的向業者取得實際專線後補（範例，號碼換成真值）：
# INSERT INTO vendor_configs (vendor_id, param_key, param_value, data_type, display_name, category, is_active)
# VALUES (<vendor_id>, 'service_hotline', '<專線號碼>', 'string', '客服專線', 'contact', true);
```

### 18-5. 驗證（帶 X-API-Key，見 §0）

```bash
# ① T-1：應進面向（回追問/查無或實值，不能是通用知識條目）
curl -s -X POST https://chatai.jgbsmart.com/rag-api/v1/message -H "Content-Type: application/json" -H "X-API-Key: $KEY" \
  -d '{"message":"合約822032點退帳單金額為多少?","vendor_id":4,"mode":"b2b","role_id":"<真role>","user_id":"<真user>","session_id":"verify-18-1"}'
# ② B-1：無知識題 fallback 不得含 {{service_hotline}} 字樣
# ③ R-33：問「已發送的帳單可以取消嗎」不得再答「無法撤回」
```

**prod 待驗（真 API 才能確認）**：bill_diagnosis 以合約編號搜帳單的實際效果（R-35 期望找到關帳帳單）、bill_detail 是否含收據金額（R-31）。驗完把登錄簿對應案例標「已入回測」。

```bash
# ④ 合約端點健康（登錄簿 J-2：preview 已因部署落後 500，prod 需確認無此問題）
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://www.jgbsmart.com/api/external/v1/contracts/status-overview?role_id=<真role>" -H "X-API-Key: $JGB_KEY"
# 預期 200；若 500 且錯誤含 early_termination_notice_date → 同 J-2，轉 jgb2 處理
```

## 19. agentic-mcp（M0–M1）部署（2026-09-05）

> spec `agentic-mcp-orchestration` 任務 5.3｜依賴 M0–M1 全部任務已收案（1.x–4.x）。
> ⛔ 本節只給逐條指令＋預期輸出；線上執行一律由業主親自操作
> （[[feedback_prod_ops_self_run]]／[[feedback_no_deploy_scripts]]）。金鑰一律用
> `$KEY`／`$MCP_KEY` 等 shell 變數表示，⛔ 不得出現在本文件任何位置。

### 19-0 相依升級提醒（**image 必重建，不可 `docker cp`**）

`rag-orchestrator/requirements.txt` 這批相依已隨 M0–M1 任務升版（非本節新增，是既有 M0
任務落地的結果，此處僅列出供部署前確認）：

| 套件 | 版本（實際解析） | 可能影響 |
|---|---|---|
| `fastapi` | `0.115.14` | 既有路由行為不變；隨 `starlette` 升版 |
| `starlette` | `>=0.46,<1.0`（實際解出 `0.46.2`） | 0.46 起部分棄用警告轉嚴——重建後看 log 有無新 DeprecationWarning |
| `pydantic` | `>=2.13,<3`（實際解出 `2.13.5`） | **2.13 起 strict 模式行為變嚴**：既有 model 若依賴寬鬆型別轉換（如字串轉 int）可能在 strict 路徑報錯；M0–M1 測試已綠不代表涵蓋所有既有端點，重建後跑一輪 §5 煙囪 |
| `anyio` | `>=4.9`（實際解出 `4.15.0`） | `mcp` SDK 要求；既有 async 路徑相依 anyio 3.x 行為者需留意（本專案未偵測到） |
| `uvicorn` | `>=0.31.1`（實際解出 `0.52.4`） | 版距較大，重建後確認啟動 log 無新警告 |
| `mcp` | `2.1.1` | 新增依賴，`/mcp` 門面用；不可用時 `AGENT_UNAVAILABLE`（不影響既有路徑，見 §19-6） |
| `tiktoken` | `0.14.0` | 新增依賴，售前大綱 token 預算檢查用（R5.5） |

驗證（重建後）：
```bash
docker exec aichatbot-rag-orchestrator python3 -c \
  "import fastapi,starlette,pydantic,anyio,mcp,tiktoken; \
   print(fastapi.__version__, starlette.__version__, pydantic.VERSION, anyio.__version__, mcp.__version__)"
```
預期：`0.115.14 0.46.2 2.13.5 4.15.0 2.1.1`（版號隨解析結果可能微幅浮動，但主版號需一致）。

⚠️ **這批相依只能靠重建 image 生效**（`up -d --build`，同 §4）；`docker cp` 進容器
不會更新 `pip` 安裝的套件版本，且 pyc 快取會讓「看起來沒事」但實際跑舊碼——
線上曾因此類操作誤判過（見 §4 標題本身的教訓）。

### 19-1 五支 migration

依 `schema_migrations` 帳本以 `migrate.sh` dry-run → `--apply`（同 §17 用法，⛔ 不逐支手貼）：

```bash
cd /home/ec2-user/AIChatbot
bash rag-orchestrator/database/migrate.sh
```
預期（dry-run）：`═══ A. SQL migrations ═══` 區塊列出五支待跑
（`20260904_create_help_center_pages`、`20260904_api_keys_agent_scope`、
`20260905_knowledge_base_outline_approval`、`20260905_agent_confirmation_tokens`、
`20260905_agent_shadow_texts`；五支互不依賴，runner 依檔名字母序執行，順序不影響結果）。

```bash
bash rag-orchestrator/database/migrate.sh --apply
```
預期：五支各印一行 `✅ 已套並記帳`；再跑一次不帶 `--apply` 應全部顯示已套（冪等）。

各表驗證：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='api_keys' AND column_name IN ('is_internal','vendor_ids') ORDER BY 1;"
# 預期：兩行 is_internal、vendor_ids

docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='knowledge_base' AND column_name IN ('outline_approved_by','outline_approved_at') ORDER BY 1;"
# 預期：兩行 outline_approved_at、outline_approved_by

docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT count(*) FROM help_center_pages;"
# 預期：0（表已建、尚無資料——D3 裁後才匯入，本節不匯入）

docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT count(*) FROM agent_confirmation_tokens;"
# 預期：0

docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT count(*) FROM agent_shadow_texts;"
# 預期：0
```

⚠️ `agent_shadow_texts` 只收 prospect 全文、30 天清；清理指令（業主排程執行，本節不建 cron）：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "DELETE FROM agent_shadow_texts WHERE created_at < now() - interval '30 days';"
```

### 19-2 內部 MCP API key 發行（比照 §16-1，多 `is_internal`／`vendor_ids`）

```bash
KEY=$(python3 -c "import secrets;print('rgk_'+secrets.token_urlsafe(32))")
HASH=$(python3 -c "import hashlib;print(hashlib.sha256('$KEY'.encode()).hexdigest())")
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "INSERT INTO api_keys (name, key_hash, key_prefix, description, is_active, is_internal, vendor_ids)
   VALUES ('mcp-internal-prod', '$HASH', '${KEY:0:8}', 'agentic-mcp 內部呼叫者（回測／MCP client）', TRUE, TRUE, NULL);"
echo "MCP_INTERNAL_API_KEY=$KEY" >> .env
```
預期：`INSERT 0 1`。`is_internal=TRUE` ⇒ `/mcp` 流量計量標內部、不計入額度；
`vendor_ids NULL` ⇒ 不限業者（⛔ 若要限定業者，改傳 `ARRAY[<vendor_id>,...]`，
`vendor_ids='{}'`（空陣列）則是全拒——兩者語義不可混用，見 migration
`20260904_api_keys_agent_scope.sql` 註解）。⛔ `$KEY` 不進版控、不貼進對話、不進日誌。

自檢（帶 key 直打，無 key 應 401）：
```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8100/api/v1/agent/health
# 預期：401（無 key）

curl -s http://localhost:8100/api/v1/agent/health -H "X-API-Key: $KEY" | head -c 800; echo
# 預期：HTTP 200，body JSON status 欄非例外；含 checks.api_keys_agent_scope_ready=true
```

### 19-3 `MCP_ALLOWED_ORIGINS` 設定

`docker-compose.prod.yml` 已宣告 `MCP_ALLOWED_ORIGINS: ${MCP_ALLOWED_ORIGINS:--}`（1.7 落地）。
`/mcp` 僅供 **server-to-server**（Claude Code、jgb2 後端等不帶 Origin 的呼叫者），
⛔ 不供裝置／瀏覽器直連：

- `.env` **未設定此鍵** ⇒ app 啟動即 `raise`（必須明示，見 `mcp_facade.py:load_allowed_origins`）。
- 設為 `-`（compose 預設值）⇒ 空集合＝「任何帶 `Origin` header 的請求都拒」——這是
  server-to-server 門面的正確預設，**多數情況維持這個值即可**。
- 缺 `Origin` header 的請求（server-to-server client 本就不送）不受影響、照放行。
- 若日後真有瀏覽器/裝置需求，設為逗號分隔白名單（如 `https://a.example.com,https://b.example.com`）
  才放行對應來源——⛔ 目前無此需求，不建議設定。

驗證三態（見 §19-6 煙囪 4）。

### 19-4 售前池標記已審核（M1 前置，R11.6）

> 背景：`build_prospect_outline` 只取 `outline_approved_by IS NOT NULL` 的列；上線前
> 需先把現有售前池標記為已審核，否則大綱組裝取不到任何來源。腳本：
> `.kiro/specs/agentic-mcp-orchestration/sql/mark-prospect-pool-approved-20260905.sql`
> （`git add -f`，WHERE 條件逐條翻自 `build_visibility_predicate` 的 b2c 分支）。

先預覽要標記的列數（Step 1，⛔ 不執行 UPDATE）：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -f \
  <(sed -n '/^SELECT count(\*) AS matched/,/^-- 預期：31$/p' \
    .kiro/specs/agentic-mcp-orchestration/sql/mark-prospect-pool-approved-20260905.sql | sed '$d')
```
預期：`31`。⚠️ **若不是 31，⛔ 立刻停止，不得往下執行 UPDATE**——回報實際數字，
回到 SQL 檔核對 `build_visibility_predicate` 條件是否與 prod 售前池現況仍一致
（本機驗證時的 31 是本機庫的快照，prod 資料量可能不同，這是預期會需要人工核對的一步，
不是腳本錯誤）。

確認數字後執行標記與驗證（Step 2、3 皆在同一檔內）：
```bash
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  < .kiro/specs/agentic-mcp-orchestration/sql/mark-prospect-pool-approved-20260905.sql
```
預期：`UPDATE <與預覽相同的數字>`；檔案最後一段驗證 SQL 印出
`SELECT count(*) FROM knowledge_base WHERE outline_approved_by IS NOT NULL;` ＝相同數字。

Rollback（僅標記錯誤時使用，只還原本次以 `owner-20260905` 寫入的列）：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "UPDATE knowledge_base SET outline_approved_by = NULL, outline_approved_at = NULL WHERE outline_approved_by = 'owner-20260905';"
```


> ⚠️ **連鎖（2026-09-05 本機實跑抓到）**：上述 UPDATE 會觸發 `update_kb_updated_at`，讓標記列的 `updated_at` 變成當日；未宣告 `instance_applicability` 的列會讓 `make audit` 不變量 10 紅。線上執行後請照 DSP-019 同法補宣告（`UPDATE knowledge_base SET generation_metadata = coalesce(generation_metadata,'{}'::jsonb) || '{"instance_applicability":"general"}' WHERE outline_approved_by='owner-<日期>' AND NOT coalesce(generation_metadata ? 'instance_applicability', false);`），並把補宣告的 id 登記進 `.kiro/specs/conversational-routing-execution/r10p/v1-scope-exclusions.txt`（不變量 17）。
### 19-5 env 一覽（名稱／預設／作用／開啟時機）

⛔ 以下皆以程式實際讀取為準（`os.getenv`／`os.environ.get`，逐一 grep 核對，見各列查證指令）；
`docker-compose.prod.yml`／`docker-compose.dev.yml` 目前只以**註解**列出（不新增會改變行為的鍵，
`MCP_ALLOWED_ORIGINS` 已於 1.7 落地為真正的宣告鍵，見 §19-3）。

| env | 預設 | 作用 | 何時才開 | 查證 |
|---|---|---|---|---|
| `AGENT_STAGE` | `M0`（非法值／未設回退 `M0`） | 部署里程碑；工具 `stage[audience] <= AGENT_STAGE` 才可見 | 隨 M0→M1→…推進逐步調高，⛔ 不超前實際完成的里程碑 | `services/agent/mcp_facade.py:current_stage` |
| `AGENT_AUDIENCES` | 空（逗號分隔清單） | REST 入口（`/api/v1/message`）哪些 audience 走 agent 鏈 | **M3 才開 `AGENT_AUDIENCES=prospect`**（5.1 切換演練後） | `routers/agent_entry.py:agent_audiences` |
| `AGENT_TURN_ENABLED` | `false` | `agent.turn` MCP 工具是否註冊；關閉時 `tools/list` 看不到它 | 只在需要 MCP client 對話（Claude Code／jgb2 後端經 `/mcp` 跑整回合）時開；⛔ 與 `AGENT_AUDIENCES` 互不管轄 | `services/agent/mcp_facade.py:_AGENT_TURN_ENABLED_ENV` |
| `AGENT_TURN_TIMEOUT_S` | `30.0` 秒 | `agent.turn` 單次呼叫逾時（刻意大於 `Budget.deadline_s`=20） | 隨 `AGENT_TURN_ENABLED` 一併評估，預設值通常免調 | `services/agent/mcp_facade.py:agent_turn_timeout_s` |
| `AGENT_TURN_CAP` | `120`／小時／`(api_key_id, vendor_id)` | `agent.turn` 速率上限 | 同上；⚠️ 行程內記憶體，多 worker 部署時實際上限＝此值 × worker 數 | `services/agent/mcp_facade.py:agent_turn_cap` |
| `AGENT_SHADOW_AUDIENCES` | 空（逗號分隔清單） | 影子跑動的 audience 白名單 | M2 影子評估開始時開（如 `AGENT_SHADOW_AUDIENCES=prospect`），M2 完成或未使用時關 | `services/agent/shadow.py:_shadow_audiences` |
| `AGENT_SHADOW_MONTHLY_USD_CAP` | `50.0`（USD） | 影子月成本上限，超過自動關並告警 | 隨 `AGENT_SHADOW_AUDIENCES` 一併開 | `services/agent/shadow.py:_monthly_cap_usd` |
| `AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT` | `10000` | 售前大綱 token 預算上限 | 全程有效（M1 起，非里程碑開關） | `services/agent/outline.py:OUTLINE_TOKEN_LIMIT_ENV` |
| `AGENT_OUTLINE_TOKEN_LIMIT_PM` | `8000` | pm 目錄 token 預算上限（子 spec 用） | 同上，M1 尚未消費（pm 另案） | 同上 |
| `AGENT_OUTLINE_TOKEN_LIMIT_TENANT` | `8000` | tenant 目錄 token 預算上限（子 spec 用） | 同上 | 同上 |
| `AGENT_MODEL` | 未設 ⇒ 退回 `OPENAI_MODEL` ⇒ 再無則 `gpt-4o-mini` | agent runtime 呼叫的模型名 | 全程有效；未設時沿用專案既有 `OPENAI_MODEL` 慣例 | `services/agent/runtime.py`（`self._model = model or os.environ.get("AGENT_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")`） |
| `AGENT_TRACE_WINDOW_DAYS` | `7`（非法／非正數回退） | `agent_trace` 查詢與 CLI 的時間窗上限 | 全程有效 | `services/agent/trace_view.py:window_days` |
| `MCP_ALLOWED_ORIGINS` | **無**（未設＝啟動即 raise） | `/mcp` 的 Origin 白名單三態判定 | 已於 1.7 落地必填，維持 `-`（見 §19-3） | `services/agent/mcp_facade.py:load_allowed_origins` |
| `RATE_PER_MIN` | `60`／分鐘／`(api_key_id, vendor_id)` | 一般 MCP 工具（非 `agent.turn`）速率限制 | 全程有效，既有工具通用旋鈕 | `services/agent/tools/registry.py:_DEFAULT_RATE_PER_MIN` |
| `KB_GET_CAP` | `300`／小時／key | `kb.get` 呼叫上限 | 全程有效 | `services/agent/tools/registry.py:_DEFAULT_KB_GET_CAP` |
| `JGB2_CANDIDATE_CAP` | `5` | `jgb2.query.*` 候選列筆數上限 | 全程有效 | `services/agent/tools/jgb2.py:_candidate_cap` |

ℹ️ `AGENT_BUDGET_TOOL_CALLS`／`AGENT_BUDGET_REWRITES`／`AGENT_BUDGET_DEADLINE_S`（預設 4／2／20.0）由 `services/agent/bootstrap.py:budget_from_env` 讀取（2026-09-05 補上），壞值／≤0 退回預設；一般不需宣告。

`docker-compose.prod.yml`／`docker-compose.dev.yml` 對照：本節新增的鍵**只加註解**列出
上表（`MCP_ALLOWED_ORIGINS` 除外——它已是既有宣告鍵），不新增會改變行為的鍵；若某個
里程碑要開某個開關，屆時在 `.env` 直接加該鍵覆寫預設值即可，不需要改 compose 檔。

### 19-6 煙囪驗證

```bash
# ① 既有健檢（不動）
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8100/api/v1/health
# 預期：200

# ② agent 健檢（帶 key＋身分 header）
curl -s http://localhost:8100/api/v1/agent/health \
  -H "X-API-Key: $MCP_INTERNAL_API_KEY" \
  -H 'X-JGB-Identity: {"mode":"b2c","target_user":"tenant","vendor_id":1,"session_id":"backtest_session_smoke"}' \
  | python3 -m json.tool
# 預期：status 非例外；checks.api_keys_agent_scope_ready == true（19-1 兩支 migration 已套）；
#   checks.mcp_sdk 非 "unavailable (DSP-014)"（mcp 套件已隨 19-0 重建進 image）

# ③ /mcp 無 key ⇒ 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8100/mcp \
  -H 'Content-Type: application/json' -d '{}'
# 預期：401

# ③b /mcp 帶 key 但帶不在白名單的 Origin ⇒ 403（驗證 MCP_ALLOWED_ORIGINS 三態，見 §19-3）
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8100/mcp \
  -H "X-API-Key: $MCP_INTERNAL_API_KEY" -H 'Origin: https://not-allowed.example.com' \
  -H 'Content-Type: application/json' -d '{}'
# 預期：403

# ④ 不變量稽核（含不變量 27–31、不變量 3 整目錄 digest）
docker exec aichatbot-rag-orchestrator make audit
# 預期：PASS（見 §10 既有用法；agentic-mcp 新增 5 條不變量隨此指令一併跑）
```

### 19-7 回切

```bash
# .env：AGENT_AUDIENCES 設為空、AGENT_TURN_ENABLED=false
sed -i 's/^AGENT_AUDIENCES=.*/AGENT_AUDIENCES=/' .env
sed -i 's/^AGENT_TURN_ENABLED=.*/AGENT_TURN_ENABLED=false/' .env
docker compose -f docker-compose.prod.yml up -d   # ⛔ 不加 --build，回切不需要重建 image
```
預期：≤5 分鐘內完成，走舊鏈（無資料修復——agent 路徑的表如 `agent_confirmation_tokens`／
`agent_shadow_texts` 保留但不再寫入，不影響舊鏈）。驗證：

```bash
curl -s http://localhost:8100/mcp -X POST -H "X-API-Key: $MCP_INTERNAL_API_KEY" \
  -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  | grep -o '"agent.turn"'
# 預期：無輸出（AGENT_TURN_ENABLED=false ⇒ 工具未註冊，⛔ 不是「註冊了但拒絕」）
```

### 19-8 監控告警

以下四項屬觀測/告警設計，本任務只記錄判準與查詢方式，**不在本任務內接線到既有告警系統**
（⛔ 不改 `.py`；接線屬另案）：

1. **每回合成本 > 現行（舊鏈同類回合）×3**：查 `usage_events.processing_path LIKE 'mcp:agent.turn'`
   或 `'shadow:agent'` 的 `cost_usd`／`total_tokens`，與同期舊鏈（`decision_snapshot` 的既有
   路徑）比較均值。
2. **影子月上限**：`AGENT_SHADOW_MONTHLY_USD_CAP` 觸發後 `shadow.py` 會自動關（見
   `services/agent/shadow.py:_monthly_cap_usd`）並告警——告警落點需人工看 log
   （`shadow disabled: monthly cap exceeded` 類字串，實際訊息以程式為準）。
3. **Verifier 拒率**：`decision_snapshot.agent`（或 `agent_trace`）裡的拒因分佈
   （`tools/agent_trace.py`）——拒率異常升高代表知識供給或大綱組裝出問題。
4. **`tool_unavailable` 率**與**p95**：`usage_events` 的 `channel='mcp'` 或 `agent` 相關列，
   依 `processing_path` 分組看延遲分佈與 `AGENT_UNAVAILABLE`／`TOOL_TIMEOUT` 出現率。
5. **DSP-011 前提偵測四旗**：`GET /api/v1/agent/health` 的 `checks.premise.red_flags`
   （見 `docs/api/mcp-facade.md` §8）——任一非零即代表「`/mcp` 只有內部呼叫者」這個前提
   可能已破，需重新評估是否要補真正的認證層。

## 附錄 A：全庫搬遷路徑（**僅新環境建置**：空庫從 dump 還原）

> **⚠️ 2026-07-22 §17 後正名**：本路徑**不用於既有 prod 增量部署**（drop-restore 會覆蓋 prod-only 計量歷史）。07-07 曾以此路徑把 facet 大批整批上線（已完成）；往後既有 prod 增量一律走頂部「🚩 現行部署路徑」＝逐支 migration＋§17 記帳。

> **新環境建置的唯一正式路徑＝本附錄的 dump 還原**。`database/init-legacy/`（原 `database/init/`）
> 已於 2026-07-11 除役——schema 凍結於早期架構、seed 過時，compose 掛載已移除，勿用於任何建置。

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


---

## 附錄 Z：歷史批次（勿執行，僅新環境建置逐支重放參考）

> 🚫 **既有 prod 增量部署勿跑本附錄**——以下 §1–§3 為 facet 大批，07-07 已以全庫搬遷整批上線於 prod。僅在**從空庫建置新環境**時，作為逐支重放的明細參考（另見附錄 A 的 dump 還原路徑）。

## 1. Migrations（依序 36 支，皆冪等；按 commit 時序排列——後出的 seed 覆蓋先出的，順序不可換）

> **⚠️ 適用範圍（2026-07-22 補注）**：本節 36 支＝**facet 大批**，**07-07 已以全庫搬遷整批上線於 prod**（prod 現有 21 筆對話規則/面向資料可驗）。**既有 prod 的增量部署不需重跑本節**；只需跑 facet 之後新增的 migration（§12–§15 的 8 支），並依 §17 記帳。本節保留供**新環境建置**逐支重放參考。

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

## 20. LINE OA demo 版部署（2026-09-08；業主：正式站直接換成 demo 版、目前無線上使用者、DB 直接取代）

> 前提：`feat/agentic-mcp` 已 push 到 origin（業主決定）；正式站 DB 已由本機 dev DB dump 取代（含 `20260908_agent_confirmation_tokens_pending_id`、pm 正本知識；dump 前 dev key id 98 已停用）。demo 期間整站跑替身（`USE_MOCK_JGB_API=true`），網頁客服也會看到替身資料。逐條跑、每步看預期輸出，⛔ 任一步不符即停。

> ⚠️ **2026-09-08 實跑修正（jgb2-ai-chatbot）**：(1) 這台伺服器只有獨立二進位 `docker-compose`（v2.40），`docker compose` 會把 `-f` 當 docker 本體參數報錯——本節所有 `docker compose` 讀成 `docker-compose`；(2) ssh 使用者是 `ec2-user`，key 檔放 `/home/ec2-user/.curl-mcp-key`（600）而非 `/root`；(3) `schema_migrations` 的欄位是 `migration_name`；(4) 換庫指令一律 `set -e` 串接、驗證通過才刪 dump——⛔ 不要用 `;` 接刪檔（第一次跑 compose 失敗後仍把 dump 刪了）；(5) prod compose 預設 `IMAGE_RECOGNITION_MODEL=gpt-4o-mini`（08-26「統一 mini」），demo 依 R12 在 `.env` 加 `IMAGE_RECOGNITION_MODEL=gpt-4o` 覆寫，其餘 mini 不動；(6) dev dump 帶進來的 `mcp-internal-local`（id 97）已在線上停用，demo key 名 `line-bot-oa-demo`（id 依序）。
### 20-0 換庫（本次實跑順序；舊庫先備 `backups/pre_demo_<ts>.dump`，pg_dump -Fc -Z 6 約 15 MB）
```bash
# 本機
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin -Fc -Z 6 -f /tmp/dev.dump && docker cp aichatbot-postgres:/tmp/dev.dump /tmp/dev.dump && scp /tmp/dev.dump jgb2-ai-chatbot:/home/ec2-user/
# 伺服器（set -e：任一步失敗即停、dump 留著）
ssh jgb2-ai-chatbot 'set -e; cd /home/ec2-user/AIChatbot; mkdir -p backups; docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin -Fc -Z 6 > backups/pre_demo_$(date +%Y%m%d_%H%M).dump; docker-compose -f docker-compose.prod.yml stop rag-orchestrator; docker cp /home/ec2-user/dev.dump aichatbot-postgres:/tmp/dev.dump; docker exec aichatbot-postgres psql -U aichatbot -d postgres -c "DROP DATABASE aichatbot_admin;" -c "CREATE DATABASE aichatbot_admin OWNER aichatbot;"; docker exec aichatbot-postgres pg_restore -U aichatbot -d aichatbot_admin --no-owner /tmp/dev.dump 2>&1 | grep -ci error || true; docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -At -c "select count(*) from schema_migrations where migration_name like '"'"'%pending_id%'"'"';"; docker exec aichatbot-postgres rm -f /tmp/dev.dump; rm -f /home/ec2-user/dev.dump'
```
預期：error 計數 `0`、migration 計數 `1`。回復：`pg_restore -U aichatbot -d aichatbot_admin --clean --no-owner backups/pre_demo_<ts>.dump`。
### 20-1 碼
```bash
cd /home/ec2-user/AIChatbot && git fetch origin && git checkout main && git pull   # main 已 fast-forward＝feat/agentic-mcp
git log --oneline -1          # 預期：demo 版 HEAD（帳本 §0 記錄的 hash）
```

### 20-2 env（`.env`，只加／改這幾行；其餘不動）
```
USE_MOCK_JGB_API=true
UVICORN_WORKERS=1
AGENT_STAGE=M1
AGENT_TURN_ENABLED=true
AGENT_WRITE_TOOLS_ENABLED=true
AGENT_VERIFIER_MODE=grounding_observe
AGENT_BUDGET_DEADLINE_S=45
AGENT_TURN_TIMEOUT_S=60
AGENT_MODEL=gpt-5-mini
AGENT_REASONING_EFFORT=low
USE_SEMANTIC_RERANK=false
RAG_API_AUTH_ENFORCE=true        # 應已是 true
```
⛔ 不設 `AGENT_BUDGET_REWRITES=0`、不設 `AGENT_ATTEMPT_LOG_PATH`（W6-b3 起 attempt log 會多記引文原文 `resolved_unit`，供極性誤殺量測用；**線上一律不設**）。`MCP_ALLOWED_ORIGINS` 照 §19-3（伺服器對伺服器不送 Origin 即可）。

⚠️ **W6-b3（DSP-040 正式參數）**：`AGENT_VERIFIER_MODE` 取代 `AGENT_VERIFIER_OBSERVE_ONLY`。
- `grounding_observe`＝**引用解析與涵蓋類只記錄**（`UNCITED_ASSERTION`／`QUOTE_TOO_SHORT`／`QUOTE_NOT_COVERING`／`SOURCE_NOT_CITABLE`＋`SCHEMA` 的 `ref_*`／`unit_out_of_range`），**極性類與機敏類（`POLARITY_MISMATCH`／`SENSITIVE_TOPIC`／`ROUTE_NOT_ALLOWED`／`FORBIDDEN_TERM`／`SCHEMA` 的 `marker_in_answer`／`handoff_reason_*`／`ask_target_invalid`／`empty_*`）照擋**——這是 demo 線上值。
- `enforce`＝全部照擋（預設，⛔ 沒設就是它）。
- `observe_only`＝全部只記錄（＝舊旗語義，連機敏類都不擋），**只准配 `USE_MOCK_JGB_API=true`，否則啟動直接 raise**。
- 舊旗 `AGENT_VERIFIER_OBSERVE_ONLY=true` **仍被接受一版**（解析成 `observe_only`），下一版移除；兩旗同時設以 `AGENT_VERIFIER_MODE` 為準，⛔ 打錯字一律退回 `enforce`。

### 20-3 重建＋起
```bash
docker compose -f docker-compose.prod.yml build rag-orchestrator
docker compose -f docker-compose.prod.yml up -d rag-orchestrator
docker compose -f docker-compose.prod.yml logs --since 2m rag-orchestrator | grep -E "agent runtime 已初始化|AGENT_VERIFIER_MODE|Uvicorn running"
```
預期：`✅ agent runtime 已初始化（… audiences=['property_manager', 'prospect']）`、`ℹ️ [agent] AGENT_VERIFIER_MODE=grounding_observe：引用解析與涵蓋類只記錄…（DSP-040 正式組態）`、Uvicorn 單 worker。

### 20-4 demo 用 MCP key（§19-2 手工 SQL，`is_internal`＋`vendor_ids`）
照 §19-2；⛔ 不重用本機測試的 `line-bot-oa-demo-local`（已停用）。明文只交 line-bot。

### 20-5 煙囪（帶 key；⛔ 明文不進 argv：用 `-K` 檔或 `--data @`）
```bash
# health（需 X-API-Key 與 X-JGB-Identity）
curl -s -K /root/.curl-mcp-key -H 'X-JGB-Identity: {"mode":"b2b","target_user":"property_manager","vendor_id":4,"role_id":"20151","user_id":"12291","session_id":"smoke-1"}' http://localhost:8100/api/v1/agent/health | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["status"],{k:d["checks"].get(k) for k in ("write_tools_enabled","use_mock_jgb_api","verifier_observe_only","verifier_mode")})'
```
預期：`ok {'write_tools_enabled': True, 'use_mock_jgb_api': True, 'verifier_observe_only': False, 'verifier_mode': 'grounding_observe'}`。
⚠️ `verifier_observe_only` 在 `grounding_observe` 下是 **False**（這個鍵的語義是「整把尺是不是關掉」，⛔ 不是「有沒有在觀察」）——要看模式一律讀 `verifier_mode`。舊鍵**保留一版**供既有斷言相容。
MCP `tools/list` 由 line-bot 端第一次串接時確認含 `agent.turn`、`jgb2.action.bill_due_extend`、`jgb2.action.repair_create`。

### 20-6 稽核（§10）
```bash
make audit    # 預期 OVERALL: PASS
```

### 20-7 回切
`.env` 把 §20-2 那幾行拿掉或改回（`AGENT_TURN_ENABLED=false`、`AGENT_WRITE_TOOLS_ENABLED=false`、`AGENT_VERIFIER_MODE=enforce`（或整行刪掉，預設就是 `enforce`）、`USE_MOCK_JGB_API=false`＋`JGB_API_KEY` 必須在，否則啟動直接 raise——S-5 刻意）→ `up -d rag-orchestrator`。替身狀態在行程記憶體，重啟即歸零。

⚠️ **`grounding_observe` × 真 JGB API 是刻意但危險的組合**（W6-b3／security-reviewer r1 F3）：它是第一個**能在真 API 上把引用檢查關掉**的組態——那時模型講的事實不再被要求對得上引文（機敏類與極性類仍擋）。程式**不阻止**這個組合起來，但健檢會在 `checks.premise.red_flags` 記一支 `verifier_grounding_observe_on_real_api` 並讓 `status` 轉 `red`。所以回切時 `USE_MOCK_JGB_API=false` 與 `AGENT_VERIFIER_MODE` **要一起改**：只改替身、忘了改模式 ⇒ 健檢紅、且線上答案沒有引用檢查。
⚠️ `observe_only` 配非 mock 是**啟動 raise**（連機敏類都不擋，⛔ 不給它上真 API 的機會）——回切時若沿用舊旗 `AGENT_VERIFIER_OBSERVE_ONLY=true` 又把替身關掉，服務會起不來，這是刻意的失敗方向。

### 20-8 env 一覽補充（接 §19-5）
| 名稱 | 預設 | 作用 | demo 值 |
|---|---|---|---|
| `UVICORN_WORKERS` | 4 | worker 數；`/mcp` 需 1 | 1 |
| `AGENT_WRITE_TOOLS_ENABLED` | false | `jgb2.action.*` 可見（AND stage） | true |
| `AGENT_VERIFIER_MODE` | enforce | Verifier 模式：`enforce`／`grounding_observe`（引用類只記錄、極性與機敏類照擋）／`observe_only`（全部只記錄，僅 mock 可開，否則啟動 raise） | grounding_observe |
| `AGENT_VERIFIER_OBSERVE_ONLY` | false | **相容旗（一版後移除）**：truthy ⇒ 解析成 `observe_only`；`AGENT_VERIFIER_MODE` 有設時它說了不算 | 不設 |
| `AGENT_BUDGET_DEADLINE_S`／`AGENT_TURN_TIMEOUT_S` | 20／30 | 回合預算／門面逾時 | 45／60 |
| `AGENT_MODEL`／`AGENT_REASONING_EFFORT` | 空（退 `OPENAI_MODEL`）／空（不送） | 模型與推理等級 | gpt-5-mini／low |
| `USE_SEMANTIC_RERANK` | true | 舊鏈 reranker | false（demo 不用） |
| `AGENT_ATTEMPT_LOG_PATH` | 空 | 開發量測草稿落檔（W6-b3 起每句多記 `resolved_unit`＝引文原文與 `observed`＝被觀察而未擋的類別；⛔ 線上不設） | 不設 |
