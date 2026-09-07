# Plan：LINE OA demo 的 `/mcp` 開關、憑證與 pm 大綱注入（security-sensitive）——2026-09-07 第 2 稿（plan-verifier r1 REVISE 4 條全 FIX）

> 依據：`inputs/security-review-mcp-demo-key-20260907.md`、`inputs/dsp-draft-agent-turn-stage-pm-20260907.md`（待裁）、`inputs/mcp-client-contract-line-bot-20260907.md`。執行路由：`security-executor`（S1、S3 SQL 稿）＋業主親跑（S2 重建、S3 發 key）。⛔ 本 Plan 不含金鑰值；⛔ 不 push、不動線上；⛔ 業主未核前不改受版控程式。
> r1 處置：P1「pm 回合今天拿到售前大綱」→ **FIX，S1 擴為 S1a＋S1b**；P2「S3 明文進 argv／寫 .env」→ FIX，S3 逐條改寫；P2「S4 漏 `agent_index_red`」→ FIX，S4 列全部致紅來源；P2「S2 缺前置清單」→ FIX。

## 0. 目標與非目標

- **目標**：line-bot 後端以一把 `is_internal` key 打本機 dev `POST /mcp` 的 `agent.turn`，受眾 `property_manager`，回合使用 **pm 正本**（trace 的 `outline_sha` ＝ `canon/property_manager.md` 的 sha），留一列 `usage_events`，`/api/v1/agent/health` 的每一個紅都對得上清單。
- **非目標**：上線；額度；③④⑤ LIFF 線；寫入工具；`RAG_API_AUTH_ENFORCE` 全面回歸（另案）。

## 1. 切片

### S1a stage 開 pm（程式 1 行＋測試）——前置：DSP 裁定
- `mcp_facade.AGENT_TURN_SPEC["stage"]` 加 `"property_manager": "M1"`。
- 測試：pm 身分 `specs_for(for_model=False)` 含 `agent.turn`；tenant 不含；prospect 不變；`test_mcp_facade_req` 全綠。
- 回滾：revert 該行。

### S1b pm 大綱載入與依受眾選大綱（程式；r1 P1）
- **現況（plan-verifier 查證）**：`app.py:_init_agent_runtime` 只 `build_prospect_outline`、`make_outline_resolver({"prospect": …})`；`mcp_facade._agent_turn` 取 `_app_state(deps, "agent_outline")` 後**無受眾判斷**直接塞 `agent_state["outline"]`；`runtime._select_outline` 受眾不符只是原樣 ⇒ pm 回合今天拿到**售前大綱**（＝DSP 草案否決的替代 (a)）。
- 改動（最小）：
  1. `outline.py`：新增 `build_audience_outline("property_manager")`（或把 `build_prospect_outline` 泛化為 `build_outline(audience)`）：`load_canon_or_die(resolve_canon_dir(), "property_manager")` → `register_canon("property_manager", …)` → 依 `AGENT_OUTLINE_TOKEN_LIMIT_PM`（預設 8000）組 outline doc；正本檔缺席 ⇒ **fail-closed**（該受眾不註冊、`agent.turn` 對該受眾回 `AGENT_UNAVAILABLE`），⛔ 不退回 prospect 大綱。
  2. `app.py:_init_agent_runtime`：`app.state.agent_outlines = {"prospect": …, "property_manager": …}`（缺者不放）；`make_outline_resolver(...)` 收兩份。
  3. `mcp_facade._agent_turn`：以 `identity.resolved_audience()` 從 `agent_outlines` 取；取不到 ⇒ `AGENT_UNAVAILABLE`。REST 入口 `routers/agent_entry.py` 同步改讀 `agent_outlines`（行為對 prospect 不變）。
  4. **候選索引（r2 P2；業主 2026-09-07 更正：大綱是組合式，⛔ 不得讓 pm 永遠走「整份大綱」降級 ⇒ 選 (b)）**：為 pm 正本建自己的 `FineIndex`（`register_index("property_manager", …)`，鍵＝標題＋講法＋內文句，同 prospect），runtime 改為**依 `identity.resolved_audience()` 取對應的 selector／索引**（`app.state` 存 `{"prospect": …, "property_manager": …}`；缺者走既有降級＝可見細目全集＋toc）；`health.py` 的索引狀態映射含 pm（`agent_index_red` 對每個已註冊受眾各判）。常態路徑＝每回合只注入前 K=5 細目＋toc（`CandidateOutlineDoc`），整份大綱只是索引 `absent`／`not_ready` 時的退路。
  4′. **預算仍要過（不是可選）**：`outline.check_budget` 在啟動時對**整份**受眾大綱檢查 `doc.token_count > min(env 上限, 正本 budget_tokens)` ⇒ **raise、啟動即紅、⛔ 不靜默截斷**（`OutlineBudgetExceeded`）。pm 草稿現約 3.4 萬 token、`budget_tokens` 8000 ⇒ 6.2 必須先把 F 粗目改目錄式砍進預算（或業主改 `AGENT_OUTLINE_TOKEN_LIMIT_PM`＋正本 `budget_tokens`，同 1.12 對 prospect 的處置）。S2 前置加一項：`build_outline('property_manager')` 在容器內不 raise。
  5. **檔名（r2 P1）**：`load_canon_or_die` 只認 `canon/<audience>.md`／`.json` ⇒ 正本檔已由 `property_manager-line.*` 改名為 **`canon/property_manager.md`／`.json`**（`git mv`＋`export_json` 重導出，同源測試綠；容器內 `load_canon_or_die(resolve_canon_dir(),'property_manager')` 實跑成功，正對照 `'prospect'` 亦成功）。
- 測試：pm 身分回合 `trace.outline_sha == build_outline(load_canon_or_die(dir,'property_manager')).sha256`（`OutlineDoc.sha256`＝`sha256(version\x00text)`，⛔ 不是 `canon_sha256`；當下現算、不寫死）且 **≠ prospect 大綱 sha**；prospect 回合 sha 逐位元不變；正本檔缺席時 pm 回合回 `AGENT_UNAVAILABLE`、prospect 不受影響；`/api/v1/agent/health` 的 `canon.sha256` 映射含 pm。
- 依賴（r3 P1 補）：**pm 正本細目已由業主補 `reviewed: {by, at}`**——`canon_visible` 第一條 `if fine.reviewed_by is None: return False`、`build_outline` 對未審節填 `text=""`／`citable=False` ⇒ 現況 37 細目 0 個 reviewed（正對照 prospect 38）⇒ pm 大綱只剩空 toc、`visible_subset` 空、selector 回 `none_visible`。先後序：**6.2 砍 F 改目錄式 → 業主逐細目審（reviewed）→ 容器內現算 `token_count>0`、至少一節 `citable=True`、pm 身分 `visible_subset` 非空 → 才判 4′ 預算**（未審內容不進 text，所以預算檢查在審核前不會 raise）。P3-b 已收（`3c15d322`）。S2 前置加：「pm 大綱 `token_count>0` 且可見細目數 >0」。
- 回滾：revert 該 commit；`agent_outlines` 只剩 prospect 時行為等同現況。
- 派工：`security-executor`（可見性／受眾邊界觸發），完成後 fresh `verifier`。

### S2 啟動安全演練（本機、不改程式；G1）
- **前置檢查（r1 P2，未過先補前置、不算 G1）**：
  ```bash
  docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tAc "select count(*) from knowledge_base where outline_approved_by is not null"   # 應 > 0（runbook §19-4）
  grep -c '^MCP_ALLOWED_ORIGINS=' .env          # 0 或 1 皆可：compose 已有預設 `${MCP_ALLOWED_ORIGINS:--}`（r2 P3），只確認值不是空字串
  grep -E '^(AGENT_AUDIENCES|AGENT_SHADOW_AUDIENCES)=' .env   # 應為空或不存在——⛔ 不誤開另兩把旗標
  grep -c '^OPENAI_API_KEY=' .env                # 應 1（只數不印；`llm_provider.py` 未設即 ValueError，旗標開後升為啟動紅）
  ls rag-orchestrator/canon/property_manager.md rag-orchestrator/canon/property_manager.json   # S1b 依賴（已改名）
  ```
- 最小組態（`.env` 只加這四行）：`AGENT_TURN_ENABLED=true`、`AGENT_MODEL=gpt-5-mini`、`AGENT_REASONING_EFFORT=low`、`AGENT_BUDGET_REWRITES=0`。
- 重建：`docker compose -f docker-compose.prod.yml up -d --build rag-orchestrator`；驗收：容器 `Up`、`docker logs` 無 `RuntimeError`／Traceback、`docker exec … python3 -c "from services.agent.mcp_facade import agent_turn_enabled; print(agent_turn_enabled())"` 印 `True`。
- 停下：仍 raise 且日誌指向 agent 組裝（正本／token／Verifier 自證）⇒ G1 成立，回主 session，⛔ 不改 `app.py`。
- 回滾：`.env` 去掉四行、重建。

### S3 發 key（業主親跑；r1 P2 逐條改寫，⛔ 明文不進 argv、⛔ 不寫本 repo `.env`）
runbook §19-2 的 `HASH=$(python3 -c "...'$KEY'...")` 與 `echo "MCP_INTERNAL_API_KEY=$KEY" >> .env` **兩行不照抄**（待裁後修文件；G9 一併）。改為：

```bash
# ① 產 key、hash、prefix——明文只印到終端一次，⛔ 不進 argv、不進檔
python3 - <<'PY'
import secrets, hashlib
k = 'rgk_' + secrets.token_urlsafe(32)
print('KEY_PREFIX=' + k[:8])
print('KEY_HASH='   + hashlib.sha256(k.encode()).hexdigest())
print('==== 下面這行是明文 key，只顯示一次，貼到 line-bot 側的環境變數 ====')
print(k)
PY
# ② INSERT（只用 hash／prefix；vendor_ids ⛔ 不留 NULL）——把 ① 印出的 KEY_HASH／KEY_PREFIX 貼進去
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin <<'SQL'
INSERT INTO api_keys (name, key_hash, key_prefix, description, is_active, is_internal, vendor_ids)
VALUES ('line-bot-oa-demo', '<KEY_HASH>', '<KEY_PREFIX>', 'LINE OA demo（agent.turn，pm）', TRUE, TRUE, ARRAY[<demo vendor_id>]);
SELECT id, name, key_prefix, is_internal, vendor_ids FROM api_keys WHERE name = 'line-bot-oa-demo';
SQL
# ③ 自檢：header 放檔案，⛔ 不用 -H "X-API-Key: $KEY"
#   line-bot 側或本機以 `curl -H @/path/to/headers.txt`（檔內含 X-API-Key 與 X-JGB-Identity，檔案權限 600、用完刪）打 /mcp tools/list
# ④ 撤銷：UPDATE api_keys SET is_active = FALSE WHERE name = 'line-bot-oa-demo';   -- verify_api_key 無快取，即時生效
```
- 驗收：`ps`／shell history 只出現 hash 與 prefix；`SELECT` 回一列 `is_internal=t`、`vendor_ids={<id>}`；`tools/list` 含 `agent.turn`（S1a、S2 後）。
- AIChatbot 這側**不保存明文**；若 line-bot 側需要 `.env` 鍵名，用 compose 未引用的名字（如 `ASSISTANT_MCP_API_KEY`），那是另一個 repo 的檔。

### S4 健檢與計量對帳（驗收；r1 P2 列全）
開旗標＋打一回合後 `/api/v1/agent/health` 的**全部致紅來源**（`health.py:_premise_flags`＋`agent_index_red`＋`api_keys_agent_scope_ready`）逐項判：

| 來源 | 預期 | 判定 |
|---|---|---|
| `mcp_calls_flagged_by_api_key` | 空（key 是 internal） | **不可紅** ⇒ 紅即停（代表 key 不是 internal） |
| `vendor_not_in_table` | 0 | 不可紅 |
| `origin_not_allowed` | 0（不送 Origin） | 不可紅 |
| `enforce_off_with_mcp_traffic` | 若本機 `RAG_API_AUTH_ENFORCE` 未開 ⇒ **會紅** | **業主裁**：demo 期間接受此一紅，或本機開 `RAG_API_AUTH_ENFORCE=true`（需確認所有 REST 呼叫方帶 key） |
| `agent_index_red`（`agent_configured()` 且 prospect index 非 ready） | 冷啟可能 `absent` | 等 index ready（同 5c 暖機）；持續非 ready ⇒ 停 |
| `api_keys_agent_scope_ready` | true | 不可紅 |
| `tools.spec_count`（r2 P2） | >0 | 不可紅（＝0 代表 registry 沒建） |
| `kb_reachable`（r2 P2） | true | 不可紅（DB 不可達） |
| pm 索引狀態（S1b (b) 後 `agent_index_red` 對每個已註冊受眾各判） | `ready`（冷啟 `absent` 可暖機） | 持續非 ready ⇒ 紅、停 |
| `usage_events` | 新一列 `processing_path='mcp:agent.turn'`、`channel='mcp'` | 不可缺 |

`health.py:compute_agent_health` 的 `red = spec_count == 0 or not kb_reachable or bool(flags) or not scope_ready or agent_index_red`——表列已涵蓋每一項。

`make audit` 不變量 28／31 為靜態檢查，預期不變。

## 2. 風險處置（對 security review G1–G9）

| # | P | 處置 | 落在 |
|---|---|---|---|
| G1 啟動 raise | P1 | FIX：S2 前置清單＋本機演練＋回切 | S2 |
| pm 拿售前大綱（r1 P1） | P1 | FIX：S1b | S1b |
| G2 health 紅 | P2 | 業主裁（S4 表格明列哪條可紅） | S4 |
| G3 key 可打 REST | P2 | DEFER（DSP-011 已 REJECT 授權層）；`vendor_ids` 收斂＋監控 | S3 |
| G4 header 改受眾 | P2 | 改讀為需求；`vendor_ids` 單業者 | S1／S3 |
| G5 額度歸零 | P2 | DEFER 並明說：唯一節流 `AGENT_TURN_CAP`（行程內，多 worker ×N）；本機單 worker | S4 |
| G6 公網暴露 | P2 | 業主部署層確認 `/mcp` 不對公網 | 部署 |
| G7 session_id 裸值 | P3 | FIX（line-bot 側 HMAC 假名，契約 §4） | 契約 |
| G8 argv 明文 | P3 | FIX：S3 逐條 | S3 |
| G9 runbook §19-2 自檢矛盾 | P3 | 交裁決後修文件（實作：`GATED_PREFIXES` 含 `/api/v1/agent` ⇒ 缺身分 header 400） | 文件 |

## 3. 驗收（primary，派 fresh verifier）

pm 身分（`role_id=20151`、`user_id=12291`、demo vendor）以 header 檔打 `/mcp` `tools/call agent.turn {"message": "<pm 正本涵蓋的一句>"}`：`ok=true`、`answer` 非空、`GET /api/v1/agent/trace/{trace_id}`（帶身分 header）回傳的 **`outline_sha` 等於「與 pm 啟動組裝同式」的現算值**（r3 P2：`_build_doc(audience, build_outline(canon).sections + [build_canon_toc(canon, 靜態 pm 身分, …)], canon.version).sha256`——因 `build_prospect_outline` 在 `build_outline` 之後又加 toc 節重算 sha、`CandidateOutlineDoc` 沿用 `full.sha256`；⛔ 不是 `build_outline(...).sha256`；或直接比對啟動日誌／health 印出的 pm `outline_sha`）、且 ≠ prospect 值、不寫死；trace **`miss_kind='hit'`、候選 ≤K=5、無 `candidate_selector_error`／`candidate_none_visible`**（S1b (b)）；`usage_events` 多一列；health 紅來源全部落在 S4 表「預期紅」內。

> 處置紀錄：r2——P1 檔名 FIX（已改名、loader 實測）；P2 sha 種類 FIX；P2 S4 漏兩項 FIX；P2 pm 索引先窄化 (a)，**業主 2026-09-07 更正為 (b)**（大綱組合式、pm 建索引）；P3 FIX。r3（收尾輪）——P1「pm 正本 0 個 reviewed ⇒ 全不可見」→ FIX 為前置與先後序；P2 (a) 殘留措辭 → FIX；P2 sha 等式漏 toc → FIX。依規則兩次自動 REVISE 後只開一輪收尾，r3 仍 REVISE ⇒ **暫停自動重審，交業主**：本稿第 4 版已含三條處置，是否再開一輪由業主指示。

## 4. 停下條件

S2 前置檢查未過（先補、非 G1）；S2 仍 raise 且歸因 agent 組裝；S3 後 `mcp_calls_flagged_by_api_key` 非空；S1a／S1b 後 prospect 既有測試任何一案變紅；S4 出現表外的紅。
