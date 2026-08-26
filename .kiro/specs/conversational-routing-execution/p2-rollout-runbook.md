# P2 Rollout Runbook：Stage-1 scoped enablement

> 2026-08-26｜語言 zh-TW｜**本檔只是 runbook，寫它不代表執行**。
> 真正碰 staging／production 一律由業主逐條執行（[[feedback_prod_ops_self_run]]）；
> 本檔**不提供打包腳本**，只給逐條指令與**預期輸出**。
> 前置證據：`p3-run3-result.md`（mini true-brain regression A：3/3 PASS、零 fail-open）。

## 〇、這次要上的是什麼、不是什麼

```text
上   pre-commit responsibility resolver，**限這條已驗證鏈**：
     bill_diagnosis → billing_anomaly → contract_closeout
不上 其餘 18 個面向的 delegation；Task 8 的 salvage（見旗標表）；
     Req.10 對話品質改善的任何宣稱
```

⚠️ **Stage-1 的安全觀測已經有，對話品質觀測沒有——兩者不得混為一談：**

```text
resolver telemetry（已落 usage_events，M1 實證）
  candidate_facet／scope／delegate_facet_key／delegate_source／decision_source／
  fail_open／hop_count／fallback_reason／resolver_model_calls／resolver_latency_ms
  ⇒ 足以回答 Stage-1 的安全問題（fail_open 率、switch_without_delegate、hop 異常、
     fallback 暴增、成本／延遲、最後 commit 到哪個 Face）
Req.10 對話品質觀測（**沒有**：turn／transcript／judgeable evidence 皆缺）
  ⇒ 缺它**不擋** Stage-1；但**不得**據此宣稱「整體對話品質已改善」
```

## 一、旗標表（**全部顯式列出，不留環境預設猜測**）

| 旗標 | Stage-1 值 | 作用 | 理由 |
|---|---|---|---|
| `PREENTRY_ROUTABILITY_GATE` | `true` | 啟用 pre-commit resolver | Stage-1 主體 |
| `PREENTRY_ROUTABILITY_FACETS` | `bill_diagnosis,billing_anomaly,contract_closeout` | 面向白名單 | **只開已驗證鏈**；⚠️ GATE=true 但白名單未設 ＝ fail-safe **停用**（`routers/chat.py:831`） |
| `FACET_SCOPE_SALVAGE` | **`false`** | action 越界時是否仍依 scope 行動 | **reason: not part of Stage-1 acceptance scope**——P3 三次執行**零拒絕**，此分支未被真 brain 因果驗證（B 仍 INCONCLUSIVE），不列入本次驗收 |
| `BRAIN_STRICT_SCHEMA` | `true` | conversational-step 的 strict json_schema | P3-A 通過的**必要條件**（A2 由 3/3 → 0/24 靠它）；關掉即回退 json_object |
| `PRESALES_SYNTH_MODEL` | `gpt-4o-mini` | production brain | 業主 2026-08-26 定案統一 mini；P3 即在此組態取證 |
| `USE_MOCK_JGB_API` | `false` | 走真 JGB API | staging／production 的意義所在 |
| `JGB_API_BASE_URL` | preview／prod 對應值 | jgb2 端點 | prod compose 預設 `https://preview.jgbsmart.com` |

⚠️ **前置修正（已於 repo 完成，需隨版更部署）**：`PREENTRY_ROUTABILITY_FACETS`／
`FACET_SCOPE_SALVAGE`／`BRAIN_STRICT_SCHEMA` 原本**未在 compose 宣告**——
compose 不宣告就不會把 `.env` 的值傳進容器，會出現「旗標設了卻沒生效」。
兩份 compose 已補宣告，並納入 `_meta` 的 env parity 契約清單。

## 一之二、P2.1 的前置條件：harness red 已修（**13 → 16 → 0**）

業主裁定「三筆新 red 不得被吸收成新基線」。查證後結論更強：
**原本那 13 筆也全是同一個缺陷**——測試容器看不到 repo 根的檔案。

```text
test_env_parity_req.py        讀 /docker-compose.{prod,dev}.yml   → FileNotFoundError
test_runner_layer_contract_req.py  讀 /scripts/run-tests.sh、/.github/workflows/tests.yml → 同上
```

⚠️ **它們不是「產品既知缺陷」，是測試拿不到它宣稱要驗的證據**。
更嚴重的推論：這些 parity／runner 契約在紅的期間**完全沒有在保護任何東西**——
真的出現宣告分歧也看不到。這正是本專案三次因 runner 保真度不足而結論作廢的同一條裂縫。

處置（沿用 `./docs:/docs:ro`、`./.kiro:/.kiro:ro` 的既有慣例，掛在根層對齊 `/app` 的上兩層）：

```yaml
- ./docker-compose.prod.yml:/docker-compose.prod.yml:ro
- ./docker-compose.dev.yml:/docker-compose.dev.yml:ro
- ./scripts:/scripts:ro
- ./.github:/.github:ro
```

並在 `_env_parity` 加一道 `_require()`：掛載若被拿掉，直接說出「測試環境未掛載 compose」，
而不是丟 FileNotFoundError 讓人誤判成產品紅燈。

```text
現行基線：unit **1423 passed / 0 failed**（_meta 全綠，含新增的三個旗標 parity）
          integration **237 passed / 4 failed**（`tasks.md:1369` 具名 known-red，**性質不同**：
          那 4 筆是 3.4 REFUTED 後轉入 routing-authority-model 的 routing regression，
          屬**產品**已登記缺陷，不得為求綠燈調斷言）
⚠️ 舊文件記載的「unit 13 known-red」自此作廢；再看到該說法即為過期。
```

## 二、⚠️ 一個必須先確認的前提

repo 內**查無獨立的 RAG staging 環境**（`docs/deployment*` 無 staging 章節、
無 staging compose）。本 runbook 因此把 P2.1–P2.6 定義為：

```text
「一個非 production 的 RAG 執行環境（本機容器即可），
  但 USE_MOCK_JGB_API=false、JGB_API_BASE_URL 指向 jgb2 **preview**」
```

**若貴司另有獨立 staging 主機，請告知，本節指令的執行位置改為該主機。**

---

# P2.1 runtime snapshot ＋ **execution guard**

⚠️ **一律從容器內實際值驗，不讀 host `.env` 猜**——本輪才剛抓到
「host 設了、compose 沒宣告 ⇒ 值傳不進容器」這種失效。

## P2.1-a 四個邊界（任一不符 → **STOP**）

```bash
# ① RAG runtime ≠ production：確認你打的是哪一個容器／主機
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep rag-orchestrator
hostname
```
**預期**：容器名／主機**不是** production 那一台。⚠️ 認不出來就 STOP，不要猜。

```bash
# ② RAG DB ≠ production DB
docker exec aichatbot-rag-orchestrator env | grep -E '^DB_(HOST|NAME)='
docker exec aichatbot-postgres psql -U aichatbot -Atc "SELECT current_database();"
```
**預期**：`DB_NAME` 與 production 不同（例如 `aichatbot_admin` 但在非 prod 主機上，
或另立測試庫）。**兩者同時指向 production 即 STOP。**

```bash
# ③④ mock 關閉、端點指向 preview
docker exec aichatbot-rag-orchestrator env | grep -E '^(USE_MOCK_JGB_API|JGB_API_BASE_URL)='
```
**預期**：`USE_MOCK_JGB_API=false`、`JGB_API_BASE_URL=https://preview.jgbsmart.com`
（或貴司的 preview 位址）。⚠️ `USE_MOCK_JGB_API=true` 代表你在驗替身，P2 沒有意義 → STOP。

## P2.1-b 七個旗標逐項印出並斷言

```bash
docker exec aichatbot-rag-orchestrator sh -lc '
for k in PREENTRY_ROUTABILITY_GATE PREENTRY_ROUTABILITY_FACETS FACET_SCOPE_SALVAGE \
         BRAIN_STRICT_SCHEMA PRESALES_SYNTH_MODEL USE_MOCK_JGB_API JGB_API_BASE_URL; do
  v=$(printenv "$k"); printf "%-30s = %s\n" "$k" "${v:-<UNSET>}"
done'
```

**預期輸出（逐字比對，任一不符即 STOP）**：

```text
PREENTRY_ROUTABILITY_GATE      = true
PREENTRY_ROUTABILITY_FACETS    = bill_diagnosis,billing_anomaly,contract_closeout
FACET_SCOPE_SALVAGE            = false
BRAIN_STRICT_SCHEMA            = true
PRESALES_SYNTH_MODEL           = gpt-4o-mini
USE_MOCK_JGB_API               = false
JGB_API_BASE_URL               = https://preview.jgbsmart.com
```

⚠️ **`PREENTRY_ROUTABILITY_FACETS` 為 `<UNSET>` 或空字串一律 STOP，不得只當 warning**——
GATE=true 但白名單未設 ＝ **fail-safe 停用**（`routers/chat.py:831`），
Stage-1 會在「看起來開了、其實沒開」的狀態下被驗成「沒問題」。

```bash
# 帳本可讀（後續 P2.2 的前提）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -Atc \
  "SELECT migration_name, executed_at FROM schema_migrations ORDER BY executed_at DESC LIMIT 5;"
```
**預期**：帳本表存在且可讀（內容視環境而定）。

# P2.2 staging migration（dry-run → apply）

```bash
cd <repo 根目錄>
bash rag-orchestrator/database/migrate.sh
```

**預期輸出**：待辦清單包含 `seed_responsibility_delegates_v1.sql`（尚未記帳者）。

```bash
bash rag-orchestrator/database/migrate.sh --apply
```

**預期輸出**：該支 `APPLIED` 並寫入 `schema_migrations`。⚠️ 冪等，重跑安全。

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -Atc \
  "SELECT generation_metadata->'conversational_config'->'responsibility'->'delegates'
   FROM knowledge_base WHERE category='對話規則'
     AND generation_metadata->'conversational_config'->>'key'='bill_diagnosis';"
```

**預期輸出**：非 NULL，且含 `billing_anomaly` 與 `when` 條件。

# P2.3 staging flags

在 staging 的 `.env` 設定第一節表格的七個值，然後：

```bash
docker compose -f docker-compose.prod.yml up -d rag-orchestrator
docker exec aichatbot-rag-orchestrator env | grep -E 'PREENTRY_ROUTABILITY|FACET_SCOPE_SALVAGE|BRAIN_STRICT_SCHEMA'
```

**預期輸出**：
`PREENTRY_ROUTABILITY_GATE=true`／`PREENTRY_ROUTABILITY_FACETS=bill_diagnosis,billing_anomaly,contract_closeout`／
`FACET_SCOPE_SALVAGE=false`／`BRAIN_STRICT_SCHEMA=true`。

⚠️ 換庫或推版後 **reranker semantic model 需重建**，否則排序與新資料不同步
（[[project_deploy_semantic_model]]）。

# P2.4 staging real API contract smoke（**只驗替身證不到的**）

M0–M2 已把替身能證的證完，此處**不重複** mock assertion。真邊界只驗六項：

```text
① authentication／authorization：帶／不帶 API key、錯 key 的實際回應
② user_id／viewer scope 的真實行為（GAP-B1／B2 只有這裡能證）
③ 真實 contract title／identifier 形狀（口語多詞對 title LIKE 的實際命中率）
④ **contract_ids 重查是否真的收斂到單筆**（v5／v6 vertical slice 最重要的 external assumption）
⑤ response／error envelope（403 與 404 之分、欄位鍵集是否與投影一致）
⑥ timeout／latency 量級
```

```bash
# ④ 的最小驗證：初查 N 筆 → 指定 678 重查 → 應為單筆
curl -s -H "X-API-Key: $JGB_API_KEY" \
  "$JGB_API_BASE_URL/api/external/v1/contracts/status-overview?role_id=<ROLE>" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total=', d['pagination']['total'])"

curl -s -H "X-API-Key: $JGB_API_KEY" \
  "$JGB_API_BASE_URL/api/external/v1/contracts/status-overview?role_id=<ROLE>&contract_ids=678" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total=', d['pagination']['total'], '| ids=', [r['id'] for r in d['data']])"
```

**預期輸出**：第一次 `total=N`（N>1）；第二次 `total=1`、`ids=[678]`。
⚠️ 若第二次**未收斂**，Stage-1 **停止**——vertical slice 的外部前提不成立。

```bash
# ⑤ 鍵集比對：真 API 的鍵集是否與我方投影一致（多一鍵是捏造、少一鍵是失真）
curl -s -H "X-API-Key: $JGB_API_KEY" \
  "$JGB_API_BASE_URL/api/external/v1/contracts/status-overview?role_id=<ROLE>&per_page=1" \
  | python3 -c "import json,sys; print(sorted(json.load(sys.stdin)['data'][0].keys()))"
```

**預期輸出**：與 `services/jgb/contract_fixtures.EXTERNAL_CONTRACT_FIELDS` 逐鍵相同。
差異即為 **D1 漂移**，逐項記錄後再決定是否續行。

# P2.5 staging true-brain vertical acceptance

```bash
# 在 staging 對真 API 跑一次 P3-A 的同一條鏈（真 brain、真 JGB API）
curl -s -X POST "$RAG_BASE_URL/api/v1/message" -H 'Content-Type: application/json' -d '{
  "message":"幫我查點退帳單金額","vendor_id":2,"target_user":"property_manager",
  "mode":"b2b","role_id":"<ROLE>","session_id":"stg-p25-1","stream":false}'
curl -s -X POST "$RAG_BASE_URL/api/v1/message" -H 'Content-Type: application/json' -d '{
  "message":"<真實合約識別碼>","vendor_id":2,"target_user":"property_manager",
  "mode":"b2b","role_id":"<ROLE>","session_id":"stg-p25-1","stream":false}'
```

**預期輸出**：第 2 輪答句含該合約的**現況狀態**與**到期／可點退時點**
（對應 v6 ruler 的兩組必含字面，但字面值改為該真合約的實際值）。

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -Atc \
  "SELECT decision_snapshot->'resolver' FROM usage_events
   WHERE session_id='stg-p25-1' AND decision_snapshot ? 'resolver' ORDER BY id DESC LIMIT 1;"
```

**預期輸出**：`final_committed_facet=contract_closeout`、`fail_open=false`、
`hop_count=3`、`delegate_sources` 為 `model_delegate`／`contract_singleton` 的組合。

# P2.6 rollback rehearsal（**production 之前先演練**）

```bash
# ① 旗標回退（最快、零資料變更）——單獨即可停用整個 Stage-1
#    .env 改 PREENTRY_ROUTABILITY_GATE=false 後：
docker compose -f docker-compose.prod.yml up -d rag-orchestrator
docker exec aichatbot-rag-orchestrator env | grep PREENTRY_ROUTABILITY_GATE
```
**預期輸出**：`PREENTRY_ROUTABILITY_GATE=false`；再打一次 P2.5 第 1 輪，
`decision_snapshot` 應**沒有** `resolver` 鍵（resolver 未參與）。

```bash
# ② 資料回退（僅在需要時）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  < rag-orchestrator/database/migrations/seed_responsibility_delegates_v1_rollback.sql
```
**預期輸出**：兩段 UPDATE 各回報受影響列數；重跑冪等。
⚠️ 回退後 `bill_diagnosis` 的 `responsibility` 鍵消失、規則 answer 的
`delegate_facet_key` 宣告被移除——**delegation 不會再發生**，這正是回退的定義。

# P2.7 production migration

與 P2.2 相同的三條指令，**在 production 執行**（由業主）。
⚠️ 先確認 `schema_migrations` 帳本已 bootstrap（見 `docs/deployment-runbook.md` §17）。

# P2.8 Stage-1 scoped enablement

production `.env` 設定第一節表格的值 → 重啟 rag-orchestrator → 以 P2.1 的指令**回讀確認**。
⚠️ **只開白名單那三個面向**；不因 P3-A 通過就擴其他 Faces。

# P2.9 resolver telemetry 觀察（Stage-1 的安全問題）

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT
  count(*)                                                   AS resolver_requests,
  count(*) FILTER (WHERE (decision_snapshot->'resolver'->>'fail_open')::bool) AS fail_open,
  count(*) FILTER (WHERE decision_snapshot->'resolver'->>'fallback_reason'
                         = 'switch_without_delegate')        AS switch_without_delegate,
  max((decision_snapshot->'resolver'->>'hop_count')::int)                    AS max_hop_count,
  round(avg((decision_snapshot->'resolver'->>'resolver_latency_ms')::int))   AS avg_latency_ms,
  round(avg((decision_snapshot->'resolver'->>'resolver_model_calls')::int),2) AS avg_model_calls
FROM usage_events
WHERE decision_snapshot ? 'resolver' AND created_at > now() - interval '24 hours';"
```

**initial operational stop thresholds（Stage-1 保守停損線，**非已驗證的產品品質門檻**）**：

⚠️ 這些數字**沒有 production baseline 支撐**——它們的用途只有一個：
「Stage-1 出現異常就先停」。**不得**被後人引用成
「`fail_open ≤ 10%` ＝ 品質合格」之類的驗收標準。
真正的品質標準要等 Req.10 baseline（仍 `BLOCKED_BY_OBSERVABILITY`）。

```text
fail_open 率 > 10%                    → 模型或規則供應出問題
switch_without_delegate > 5%          → 委派契約或模型輸出退化（singleton 應已擋掉大部分）
avg_model_calls 明顯 > 3              → 每請求成本異常
avg_latency_ms 較上線前基準 +50%       → 延遲退化
```

## hop_count 是 **invariant**，不是平均值

查清了定義（`routers/chat.py:892` `hop_count = len(hops)`，hops 逐筆來自
`res.chain`）：**它數的是 chain record 數，含 terminal record**
（`cycle`／`unavailable`），不是「evaluator 評估過的 candidate 數」。

理論最大值由 `resolve_entry_candidate` 的結構決定
（`MAX_DELEGATION_HOPS = 3`，迴圈 `range(MAX+1)` ＝ 最多 4 次評估，
最後一次可能再追加 1 筆 terminal）：

```text
理論最大 = 4（評估）+ 1（terminal）= **5**
Stage-1 已驗證鏈的實測值 = **3**（P3 run3 三次皆 3）
```

因此 guard 用 invariant，不用平均：

```text
any hop_count > 5   → **invariant violation**（resolver 或 telemetry 有 bug，非流量特性）
any hop_count >= 4  → 該請求用滿了委派預算，逐筆調閱（非停損，但要看）
```

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT (decision_snapshot->'resolver'->>'hop_count')::int AS hop_count, count(*)
FROM usage_events
WHERE decision_snapshot ? 'resolver' AND created_at > now() - interval '24 hours'
GROUP BY 1 ORDER BY 1;"
```
**預期**：絕大多數為 3；出現 `>5` 即 invariant violation，**立刻回退旗標**。

```bash
# delegate 由誰決定的分布——看得出模型是否退化成全靠契約撐著
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT jsonb_array_elements_text(decision_snapshot->'resolver'->'delegate_sources') AS src,
       count(*)
FROM usage_events
WHERE decision_snapshot ? 'resolver' AND created_at > now() - interval '24 hours'
GROUP BY 1 ORDER BY 2 DESC;"
```

# P2.10 owner release decision

放行需同時成立：

```text
① P2.4 六項真 API 邊界皆有結論（未過者逐項記錄，不得留白）
② P2.5 真 API 下的 vertical slice 成立（含 telemetry 三欄）
③ P2.6 回退演練成功（旗標與資料兩條路都試過）
④ P2.9 觀察窗內五個門檻皆未觸發
⑤ 業主簽核並記錄於本檔尾
```

⚠️ **放行的射程**：只代表「這條鏈在真環境可運作」。
**不得**擴寫成「對話品質已改善」——那需要 Req.10 的 baseline，而它仍
`BLOCKED_BY_OBSERVABILITY`（OBS-1／2／3）。
