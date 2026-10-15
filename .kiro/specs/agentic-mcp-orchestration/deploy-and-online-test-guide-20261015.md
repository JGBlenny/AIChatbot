# 站內幫手：部署與上線測試指南（業主照做版）（2026-10-15）

> 業主原話（2026-10-15）：「幫我整理 相關的文件 都完成我要準備 部署線上 開始測試 且目前是用 gpt-6-luna 吧」。
> 紀律：push、部署、正式機操作**一律由業主自己跑**；本文件只給逐條指令與預期輸出，⛔ 不含任何金鑰值、⛔ 不含正式機 IP、⛔ 不含真實個資。
> 來源（逐一對碼，查證指令附在各處）：`docs/api/jgb2-web-assistant-integration.md`（接口 A）、`.kiro/specs/agentic-mcp-orchestration/jgb2-api-requests.md`（接口 B #16～#24、§1b）、`jgb-acceptance-checklist-20261015.md`（接測清單）、`plan-assistant-11-items-20261014.md`（計畫，§7 為執行紀錄）、`docs/deployment-runbook.md`（§4、§17、§19、§20）、`docker-compose.prod.yml`、`.claude/DECISIONS.md` DSP-073／074／075／076。
> 標記約定：**【runbook 未載，需業主確認】**＝runbook 沒有這一步，本文件不編指令，只寫需要確認什麼。**【待決定】**＝業主或 JGB 要拍板，彙整在第 8 章。

---

## 0. 業主已裁定（2026-10-15）

- D1 `AGENT_VERIFIER_MODE=grounding_observe`：部署前裁 `enforce`（與驗收一致），上線後實測知識題 `enforce` 答 1／5、`grounding_observe` 答 3／5，業主 2026-10-15 改裁「改回 grounding_observe」；健檢會因 `verifier_grounding_observe_on_real_api` 亮紅旗，屬已知。
- D2 與 LINE OA demo 同機一起切，不另排時段。
- D3 接真 JGB（www）：`USE_MOCK_JGB_API=false`，先測既有 API 撐得起的部分；接口 B 新增端點未完成前，統計與建物件／合約／手動帳單回「暫不支援」降級。
- D4 commit：`runtime.py`／`turn_context.py`／`exit_gates.py` 整檔進站內幫手 commit（訊息註明含 Plan 9.11）；其他線各自 commit；他人未追蹤檔不進。
- D5 已處理：`docker-compose.prod.yml` 已宣告 5 個新 env 鍵（`IMAGE_URL_ALLOWLIST` 預設 `relay.jgbsmart.com`，因空字串＝全擋）；`DOCUMIND_ALLOW_INSECURE_TEST_HOST`、`DOCUMIND_INSECURE_TEST_HOST`、`JGB_MOCK_WRITE_LOG` 為測試專用，正式機不宣告也不設。
- 其餘 D6～D10 照本指南建議值，業主可改。

## 1. 一句話現況

**AIChatbot 端 10 項（原 11 項，(7) 記憶 2026-10-15 業主「先不用記住 這項不用」已撤除）以計畫 §7 為準：**

| 狀態 | 項目 | 依據（計畫 §7） |
|---|---|---|
| 已驗證（替身環境，fresh verifier CONFIRMED） | (1) 查詢、(2) 修改前先確認、(3) 依權限操作、(4) 未收帳單加總、(5) 執行中修繕清單、(8) N 個月內到期合約、(10) 建立合約 | S0、S1、S2、S5 各片驗證；S1＝4 項、S2 加 (2)(10)、S5 加 (3) |
| 已驗證（替身環境，S3 fresh verifier CONFIRMED） | (6) 修繕單、(9) 建立物件、(11) 手動帳單——文字與照片／PDF 兩半（照片分類到葉節點、謄本走 DocuMind、收據民國日期換算） | 計畫 §7「S3 收尾」：全 8 劇本 8／8 PASS |
| 撤除 | (7) 記憶 | 計畫 §3g |

**「替身驗收 ≠ 接上真 JGB」**：上表全部是在我方模擬的 jgb2（替身，`USE_MOCK_JGB_API=true` 的 fixture）上驗的。接口 B 的 #16～#21 在 JGB 尚未實作，**非 mock 模式下這 6 支我方一律回降級、不發請求**（`services/jgb_system_api.py` `_proposed_not_available`；查證：`grep -n "_proposed_not_available" rag-orchestrator/services/jgb_system_api.py`）。所以「正式機 `USE_MOCK_JGB_API=false`」時，(4)(5)(8) 由程式直接回固定句「這項統計目前還不支援：JGB 系統尚未開放這個查詢，開放後就能直接查。」（`jgb2_stats.NOT_SUPPORTED_TEXT`），建立物件／合約／手動帳單**不出確認卡**、程式直接回「這個動作目前還不支援：…」（`confirm.WRITE_NOT_SUPPORTED_TEXT`）——**不是壞掉，是 JGB 端點還不存在**（2026-10-15 首次上線實測：改前統計題被模型改成轉人或反問「想處理哪一件事？」，寫入類要按完確認才失敗）。細節見第 5 章。

**上線前的三個阻擋項（2026-10-15 皆已解決）：**

1. 程式已 commit 並 push（`1bbab7a7`，含 `jgb2_stats.py`、`documind_client.py`、`assistant_demo_vendor4.json` 三個新檔）。
2. `docker-compose.prod.yml` 已宣告站內幫手新增的 env 鍵（compose 沒有 `env_file`，只有 `environment:` 宣告的鍵才會從 `.env` 傳進容器）；正式容器實測 `AGENT_ASSISTANT_KEY_IDS`、`IMAGE_URL_ALLOWLIST`、`DOCUMENT_EXTRACTION_MODEL` 等鍵都讀得到。
3. LINE OA demo 與站內幫手同機：業主裁「一起切，不另排時段」，2026-10-15 已一起切到接真 JGB（www）、`gpt-6-luna`、`enforce`。

---

## 2. 模型設定

對話與兩支多模態功能統一 `gpt-6-luna`（DSP-075：業主 2026-10-15「不是統一改成 gpt-6-lun〔a〕」；⛔ 再以 gpt-5-mini、gpt-4o-mini 當驗收或基線）。

| 鍵 | 目標值 | 說明 |
|---|---|---|
| `AGENT_MODEL` | `gpt-6-luna` | 對話模型。未設時退回 `OPENAI_MODEL`（compose 預設 `gpt-4o-mini`），驗收結果不可比 |
| `AGENT_REASONING_EFFORT` | `none` | gpt-6-luna **帶工具呼叫時只能 `none`**；沿用 runbook §20-2 的 `low` 會回 400（runbook §20-2 自己的警語） |
| `IMAGE_RECOGNITION_MODEL` | `gpt-6-luna` | 照片辨識（修繕照片）。compose 預設 `gpt-4o-mini`，runbook §20 demo 曾覆寫成 `gpt-4o` |
| `DOCUMENT_EXTRACTION_MODEL` | `gpt-6-luna` | 文件擷取（收據）。程式預設 `gpt-5.6-luna`（`services/agent/document_extract.py` `DEFAULT_DOCUMENT_EXTRACTION_MODEL`）；compose 已宣告（2026-10-15） |

**正式機 `.env` 目前是否已切換：未查證**（DSP-075 明寫「截至 2026-10-15 未查證已切」；runbook §20-2 記的 demo 值仍是 `AGENT_MODEL=gpt-5-mini`、`AGENT_REASONING_EFFORT=low`）。⇒ **部署時由業主在正式機自己確認並設定**，確認指令見第 4 章 步驟 5。

⚠️ `gpt-5-mini` 於 2026-12-11 停用（runbook §20-2、DSP-072），這也是必須切的理由之一。
⚠️ 本文件只寫鍵名與目標值；`OPENAI_API_KEY` 等金鑰 ⛔ 出現在任何文件、指令參數或對話。

---

## 3. 正式機 env 清單

「未設的後果」欄寫的是**程式實際行為**（附查證處）。目標值以「接真 JGB 的第一階段」為準（見第 5、6 章）；與 runbook §20-2 demo 值不同者以粗體標出。

| 鍵 | 目標值或填法 | 為何需要 | 未設的後果 |
|---|---|---|---|
| `AGENT_TURN_ENABLED` | `true` | `agent.turn` 才會註冊（`tools/list` 看得到）；現為 `agent_configured()` 唯一判準（runbook §19-5） | `tools/list` 沒有 `agent.turn`，站內幫手與 LINE OA 都沒有對話工具 |
| `AGENT_STAGE` | `M1` | 工具 `stage[audience] <= AGENT_STAGE` 才可見；接口 A §2「達 M1」 | 預設 `M0`，`agent.turn` 與寫入工具不可見 |
| `AGENT_WRITE_TOOLS_ENABLED` | `true`（要測寫入才開；只測讀取可先 `false`） | 寫入動作（確認後建立）才可見，需同時滿足 stage（DSP-038） | 預設 `false`，所有 `jgb2.action.*` 不可見，確認卡兌現不了 |
| `UVICORN_WORKERS` | `1` | MCP session 存在行程記憶體；多 worker 約一半請求回 404「unknown or expired session ID」（2026-10-15 實測，接口 A §2）。同時限流計數器也在行程記憶體 | compose 預設 `4`，**不可用**。runbook §20-2 已設 `1`，確認沒被改回 |
| `USE_MOCK_JGB_API` | `false`（接真 JGB） | `true` 時走我方替身，不會打到 jgb2 | compose 預設 `true`＝**全假資料上線**（總帳 §0 明寫「忘了設就是全假資料上線」）。⚠️ 設 `false` 時 `JGB_API_KEY` 必須在，否則啟動直接 raise（runbook §20-7；`services/jgb_system_api.py` 建構時檢查） |
| `JGB_API_BASE_URL`／`JGB_API_KEY` | URL：【待決定】接哪一個 JGB 環境（compose 預設 `https://preview.jgbsmart.com`）；KEY：由 JGB 提供，⛔ 不寫在任何文件 | 真 API 的位址與憑證 | 位址錯＝打到錯的環境；`JGB_API_KEY` 空＋非 mock＝啟動 raise |
| `AGENT_MODEL`／`AGENT_REASONING_EFFORT` | **`gpt-6-luna`／`none`**（見第 2 章） | DSP-075 | 退回 `OPENAI_MODEL`；`low` 帶工具回 400 |
| `IMAGE_RECOGNITION_MODEL`／`DOCUMENT_EXTRACTION_MODEL` | **`gpt-6-luna`**（見第 2 章） | 照片與收據功能 | 舊預設，（compose 已宣告） |
| `AGENT_TURN_TIMEOUT_S` | **建議 `90`**（驗證用建議值，不是定案；runbook demo 為 `60`，程式預設 `30`） | 文件回合預算＝`min(DOCUMENT_MAX_BUDGET_S=45, AGENT_TURN_TIMEOUT_S / 2)`（`services/agent/mcp_facade.py`）；DocuMind 可用時間＝此值扣已耗時再扣 20 秒模型迴圈保留，不足 1 秒不送（接口 A §2）。照片 OCR 約 15～21 秒／頁。要讓文件預算拿滿 45 秒需 ≥ 90。**實測關係屬 S3 修正輪待確認項（接口 A §13）** | 預設 30 ⇒ 文件預算 15 秒，謄本／收據回合容易 `TOOL_TIMEOUT`。⚠️ JGB 代理的逾時必須大於此值【待告知 JGB】 |
| `AGENT_BUDGET_DEADLINE_S` | runbook §20-2 demo 值 `45`（預設 `20`）；【待決定】是否沿用 | 回合預算。runbook 註：`rewrites=2` 路徑 >20 s | 預設 20 秒，較長的回合被預算截斷 |
| `OPENAI_TIMEOUT_S` | `25`（runbook §20-2 建議） | agent 每次模型呼叫的 SDK 逾時 | 空＝SDK 預設 600 秒，一個掛住的請求只能等門面逾時 |
| `AGENT_VERIFIER_MODE` | 驗收用 **`enforce`**（程式預設）。**【待決定】**：runbook §20 記正式為 `grounding_observe`（DSP-039／040），該值**未經查證**；接口 A §2 要求接測以 `enforce` 為準 | 驗證器模式：`enforce` 全部照擋；`grounding_observe` 引用與涵蓋類只記錄（極性與機敏類照擋）；`observe_only` 只准配 mock，否則啟動 raise | 未設＝`enforce`。⚠️ `grounding_observe` × `USE_MOCK_JGB_API=false` 會讓 `/api/v1/agent/health` 的 `status` 轉 `red`（`checks.premise.red_flags` 記 `verifier_grounding_observe_on_real_api`，runbook §20-7）；真 API 上等於關掉引用檢查 |
| `AGENT_ASSISTANT_KEY_IDS` | 站內幫手那把金鑰的 `api_key_id`（整數，逗號分隔）；**金鑰建好才有 id**（第 4 章 步驟 4）。compose 已宣告（2026-10-15） | 列入的金鑰，`X-JGB-Identity` 缺 `user_id` 即 400 `IDENTITY_MISSING_USER_ID`（`services/agent/mcp_facade.py` `_ASSISTANT_KEY_IDS_ENV`） | **未設或空字串＝不對任何金鑰啟用，不報錯**（站內幫手缺 `user_id` 也不會被拒，靜默失效）；含非整數＝服務啟動失敗並印原因 |
| `IMAGE_URL_ALLOWLIST` | JGB 專用上傳網域（逗號分隔 host）；**【待 JGB 回覆網域】，回覆前不設**。compose 已宣告（2026-10-15） | 抓圖白名單（照片與 PDF）。限定專用上傳網域，⛔ `www`／API 主機（DSP-073、F9）。白名單內除 `relay.jgbsmart.com` 外每個 host 都必帶單一整數 `exp` | 未設＝預設 `relay.jgbsmart.com`（`image_fetch.py` `DEFAULT_IMAGE_URL_ALLOWLIST`），JGB 上傳網域的檔案抓不到（照片／文件測試延後）。⚠️ **有設值時是取代預設、不是附加**；設成空字串＝任何網址都抓不到 |
| `DOCUMIND_BASE_URL`／`DOCUMIND_TOKEN` | **正式機先不設＝謄本功能關閉**。日後只准 `https://…`＋Token（暫以 `Authorization: Bearer` 送出，待 DocuMind 確認格式）。compose 已宣告（2026-10-15） | 謄本解析由 DocuMind 負責（接口 A §7.3）。線上 DocuMind 目前明文 http、無認證，**不得用於正式** | 未設／任何不合規組合一律視同關閉：謄本回合不放行建立物件，使用者看到「未啟用」固定句（`services/documind_client.py`） |
| `DOCUMIND_ALLOW_INSECURE_TEST_HOST`／`DOCUMIND_INSECURE_TEST_HOST` | **正式機 ⛔ 設**（確認未設） | 只限測試的明文 http 後門（兩者同時設且主機逐字相符才放行） | 未設＝不允許明文 http（目標狀態） |
| `JGB_MOCK_WRITE_LOG` | **正式機 ⛔ 設**（確認未設） | 替身寫入紀錄（把請求 body 落檔），只用於臨時測試容器（計畫 §3f） | 未設＝完全不寫（目標狀態） |
| `RAG_API_AUTH_ENFORCE` | `true`（應已是） | `/mcp` 無金鑰須 401（runbook §0-3、§20-2） | 預設 `false`＝任何人可直打 |
| `MCP_ALLOWED_ORIGINS` | `-`（維持，runbook §19-3） | 瀏覽器不得直連 `/mcp`（F2-4） | 未設＝啟動 raise |

**不要出現的鍵**：`AGENT_ATTEMPT_LOG_PATH`（線上 ⛔ 不設）、`AGENT_BUDGET_REWRITES=0`（探針量測組態，⛔）、舊旗 `AGENT_VERIFIER_OBSERVE_ONLY`（已除役，留著只會每次啟動印警告）、`AGENT_TURN_CAP` 等除役鍵（設了也不讀，限流為封閉表 `LIMITS.turns_per_hour=1200`）。

**限流提醒（接口 A §6 F2-5）**：每小時 1200 次，計數鍵 `(api_key_id, vendor_id)`，同一業者所有成員共用一桶，計數器在行程記憶體 ⇒ 重啟歸零。

---

## 4. 部署步驟（業主逐條執行）

指令皆取自 runbook；兩個提醒：(a) 這台伺服器只有獨立二進位 `docker-compose`（v2.40），`docker compose` 會報錯，所以下面一律寫 `docker-compose`（runbook §20 實跑修正）；(b) 任一步預期輸出不符就停，不往下。

### 步驟 0：部署前（本機，業主決定後執行）

1. 【待決定】commit 範圍：站內幫手線與 9.11 線的拆法。⛔ 漏掉 untracked 新檔：`rag-orchestrator/services/agent/tools/jgb2_stats.py`、`rag-orchestrator/services/documind_client.py`、`rag-orchestrator/services/jgb/fixture_data/assistant_demo_vendor4.json`（`registry`／`mcp_facade` 會 import 前兩者，漏了容器起不來）。
2. `docker-compose.prod.yml` 已宣告站內幫手新增的 env 鍵（2026-10-15，commit `1bbab7a7`）；dev compose 有 `env_file`，免宣告。
3. `git push origin main`（正式機部署以 main 為準，runbook §20-1）。

### 步驟 1：登入正式機、記下起點 commit

```bash
cd /home/ec2-user/AIChatbot
git rev-parse --short HEAD        # 記下來，回退用（runbook §0-1）
git status --short | head         # 預期：無輸出（工作樹乾淨）
```
預期：印出一個 7 碼 hash；`git status` 無輸出。有未提交修改 ⇒ 先停，弄清楚再拉。

### 步驟 2：備份（建議）

本次不跑 migration，但步驟 4 會 INSERT 一列 `api_keys`，runbook §0-2「動任何 DB 前必做」：
```bash
mkdir -p backups
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot_admin | gzip > backups/pre_deploy_$(date +%Y%m%d_%H%M).sql.gz
ls -lh backups/pre_deploy_*.sql.gz | tail -1
```
預期：檔案存在、大小為幾十 MB（0 或幾 KB ＝ dump 失敗，停）。

### 步驟 3：拉碼，確認沒有待跑的 migration

```bash
git pull
git log --oneline -1               # 預期：步驟 0 push 的那個 commit
bash rag-orchestrator/database/migrate.sh      # dry-run，不寫任何東西（runbook §17-2 ①）
```
預期：**本次沒有 DB migration**（S4 記憶表已撤除；計畫 §3g）。dry-run 若列出待跑項，先看是不是別條線遺留的：非本次範圍者 ⛔ 不要順手 `--apply`，回報後再決定。

### 步驟 4：建立站內幫手專用金鑰

**runbook 沒有「站內幫手金鑰」的專用步驟**。最接近的是 §19-2（內部 MCP key，`is_internal=TRUE`、`vendor_ids NULL`）。站內幫手那把必須**限定 vendor、非內部**（接口 A §6 F2-1：`vendor_ids` 只含展示團隊的 vendor、非 `is_internal`）。【runbook 未載，需業主確認】以下是把 §19-2 的 INSERT 改成 `is_internal=FALSE`＋`vendor_ids=ARRAY[...]` 的版本（§19-2 註記已說明 `ARRAY[<vendor_id>,...]` 是限定業者的寫法；`vendor_ids='{}'` 是全拒，⛔ 不要誤用）：

```bash
# ① 先確認展示團隊所屬 vendor 的 id（本機測試庫是 4｜JGB_TW_RESIDENTIAL；正式庫未查證，以此查詢為準）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT id, code FROM vendors ORDER BY id;"

# ② 產生金鑰並入庫（<vendor_id> 換成 ① 確認的值；金鑰只留在這個 shell 變數）
KEY=$(python3 -c "import secrets;print('rgk_'+secrets.token_urlsafe(32))")
HASH=$(python3 -c "import hashlib;print(hashlib.sha256('$KEY'.encode()).hexdigest())")
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "INSERT INTO api_keys (name, key_hash, key_prefix, description, is_active, is_internal, vendor_ids)
   VALUES ('assistant-jgb2-prod', '$HASH', '${KEY:0:8}', '站內幫手 jgb2 代理（限定 vendor）', TRUE, FALSE, ARRAY[<vendor_id>]);"
# 預期：INSERT 0 1

# ③ 取得這把金鑰的 id（要填進 AGENT_ASSISTANT_KEY_IDS）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT id, is_internal, vendor_ids FROM api_keys WHERE name='assistant-jgb2-prod';"
# 預期：一列；is_internal 為 f；vendor_ids 為 {<vendor_id>}
```
- 金鑰明文怎麼交給 JGB：【runbook 未載，需業主確認】（runbook §20-4 只寫「明文只交 line-bot」）。原則：⛔ 不貼進對話、⛔ 不進版控、⛔ 不進日誌、⛔ 不寫進 `.env`（JGB 持有明文，我方庫只存雜湊）；交付後 `unset KEY HASH`。
- 失敗時：`INSERT` 報重複名稱 ⇒ 該名稱已存在，先查 ③，不要重發；報欄位不存在 ⇒ `api_keys` 缺 `is_internal`／`vendor_ids`（19-1 的 `20260904_api_keys_agent_scope` 未套），停下回報。

### 步驟 5：改 `.env`（逐項對第 3 章表）

先備份再改；runbook §20-2 的 demo 值有幾行要**改掉**，不是只加：

```bash
cp -p .env .env.bak_$(date +%Y%m%d_%H%M)      # 【runbook 未載此備份動作，為本指南補充】備份檔含機密，權限維持與 .env 相同
# 只看非機密的行（⛔ 不要 cat .env、不要 grep 金鑰類鍵）：
grep -nE '^(USE_MOCK_JGB_API|UVICORN_WORKERS|AGENT_[A-Z_]+|IMAGE_RECOGNITION_MODEL|DOCUMENT_EXTRACTION_MODEL|OPENAI_MODEL|OPENAI_TIMEOUT_S|JGB_API_BASE_URL|RAG_API_AUTH_ENFORCE|MCP_ALLOWED_ORIGINS|DOCUMIND_[A-Z_]+|JGB_MOCK_[A-Z_]+|IMAGE_URL_ALLOWLIST|USE_SEMANTIC_RERANK)=' .env | grep -v TOKEN
```
逐項處理（編輯器改，不要用會把值印出來的指令）：

| 動作 | 鍵 |
|---|---|
| **改** | `USE_MOCK_JGB_API=false`（原 demo 為 `true`）；`AGENT_MODEL=gpt-6-luna`（原 `gpt-5-mini`）；`AGENT_REASONING_EFFORT=none`（原 `low`）；`AGENT_VERIFIER_MODE`（原 `grounding_observe`，【待決定】驗收用 `enforce`）；`AGENT_TURN_TIMEOUT_S`（原 `60`，建議 `90`）；`IMAGE_RECOGNITION_MODEL=gpt-6-luna` |
| **加** | `DOCUMENT_EXTRACTION_MODEL=gpt-6-luna`；`AGENT_ASSISTANT_KEY_IDS=<步驟 4③ 的 id>`；`JGB_API_KEY`（由 JGB 提供，業主自己貼，⛔ 本文件不寫）；`JGB_API_BASE_URL`（【待決定】） |
| **保持** | `AGENT_TURN_ENABLED=true`、`AGENT_STAGE=M1`、`AGENT_WRITE_TOOLS_ENABLED=true`、`UVICORN_WORKERS=1`、`OPENAI_TIMEOUT_S=25`、`RAG_API_AUTH_ENFORCE=true`、`MCP_ALLOWED_ORIGINS=-` |
| **確認沒有** | `JGB_MOCK_WRITE_LOG`、`JGB_MOCK_FIXTURE`、`DOCUMIND_ALLOW_INSECURE_TEST_HOST`、`DOCUMIND_INSECURE_TEST_HOST`、`AGENT_ATTEMPT_LOG_PATH`、`AGENT_BUDGET_REWRITES=0`、`AGENT_VERIFIER_OBSERVE_ONLY`；`DOCUMIND_BASE_URL`／`DOCUMIND_TOKEN` 先不設；`IMAGE_URL_ALLOWLIST` 等 JGB 回覆網域後再設 |

### 步驟 6：重建並啟動 rag-orchestrator

```bash
docker-compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator
```
（runbook §4／§18-3 的指令；§20-3 是分開的 `build` 加 `up -d`，效果相同。）semantic-model 免重建（本次不動檢索／知識，runbook §13 查證結論）。⛔ 不要用 `docker cp` 代替重建（runbook §19-0）。重啟會清掉行程內的 MCP session 與限流計數，LINE OA 那條線會短暫中斷。

### 步驟 7：看啟動 log

```bash
docker-compose -f docker-compose.prod.yml logs --since 2m rag-orchestrator | grep -E "agent runtime 已初始化|AGENT_VERIFIER_MODE|Uvicorn running|Traceback|Error"
```
預期（runbook §20-3）：出現 `✅ agent runtime 已初始化（… audiences=['property_manager', 'prospect']）`；`Uvicorn running` 單 worker；若 `AGENT_VERIFIER_MODE=enforce` 不會有 `grounding_observe` 的 ℹ️ 那行；**不應出現 Traceback**。
失敗時：
- 啟動 raise 且訊息含 `AGENT_ASSISTANT_KEY_IDS`：值含非整數，改成純數字逗號分隔。
- raise 與 `JGB_API_KEY` 有關：`USE_MOCK_JGB_API=false` 但沒設金鑰。
- raise 與 `observe_only`：該模式只准配 mock，改回 `enforce`。
- `ModuleNotFoundError`（`jgb2_stats`／`documind_client`）：步驟 0 漏 commit 新檔，回步驟 0。

### 步驟 8：確認容器真的拿到這些設定（不印機密值）

```bash
docker exec aichatbot-rag-orchestrator sh -c 'for k in AGENT_ASSISTANT_KEY_IDS IMAGE_URL_ALLOWLIST DOCUMIND_BASE_URL DOCUMIND_TOKEN DOCUMIND_ALLOW_INSECURE_TEST_HOST DOCUMIND_INSECURE_TEST_HOST JGB_MOCK_WRITE_LOG JGB_MOCK_FIXTURE JGB_API_KEY DOCUMENT_EXTRACTION_MODEL; do if [ -n "$(printenv $k)" ]; then echo "$k=已設"; else echo "$k=未設"; fi; done; for k in AGENT_MODEL AGENT_REASONING_EFFORT IMAGE_RECOGNITION_MODEL USE_MOCK_JGB_API AGENT_VERIFIER_MODE AGENT_TURN_TIMEOUT_S UVICORN_WORKERS AGENT_STAGE AGENT_WRITE_TOOLS_ENABLED AGENT_TURN_ENABLED; do echo "$k=$(printenv $k)"; done'
```
預期：`AGENT_ASSISTANT_KEY_IDS=已設`、`JGB_API_KEY=已設`、`DOCUMENT_EXTRACTION_MODEL=已設`；`DOCUMIND_BASE_URL`／`DOCUMIND_TOKEN`／`DOCUMIND_ALLOW_INSECURE_TEST_HOST`／`DOCUMIND_INSECURE_TEST_HOST`／`JGB_MOCK_WRITE_LOG`／`JGB_MOCK_FIXTURE`＝**未設**；`IMAGE_URL_ALLOWLIST` 依是否已有 JGB 網域；第二段印出 `gpt-6-luna`、`none`、`gpt-6-luna`、`false`、`enforce`（或業主決定值）、`90`、`1`、`M1`、`true`、`true`。
失敗時：`AGENT_ASSISTANT_KEY_IDS=未設` 但 `.env` 有 ⇒ compose 沒宣告該鍵（檢查 `docker-compose.prod.yml`）；**這個鍵漏了不會有任何錯誤訊息**，所以這步不可省。

### 步驟 9：health

```bash
# 前置：K 檔放 /home/ec2-user/.curl-mcp-key（curl 設定檔格式 header = "X-API-Key: …"，不是裸 key；runbook §20-3b）
curl -s -K /home/ec2-user/.curl-mcp-key \
  -H 'X-JGB-Identity: {"mode":"b2b","target_user":"property_manager","vendor_id":<vendor_id>,"role_id":"<測試團隊 role_id>","user_id":"<測試成員 user_id>","session_id":"smoke-1"}' \
  http://localhost:8100/api/v1/agent/health | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["status"],{k:d["checks"].get(k) for k in ("write_tools_enabled","use_mock_jgb_api","verifier_mode")}); print(d["checks"].get("premise"))'
```
預期（改寫 runbook §20-5）：`ok {'write_tools_enabled': True, 'use_mock_jgb_api': False, 'verifier_mode': 'enforce'}`；`premise.red_flags` 為空。若 `status` 為 `red` 且有 `verifier_grounding_observe_on_real_api` ⇒ 你把 `AGENT_VERIFIER_MODE` 留在 `grounding_observe`，改 `enforce` 後重跑步驟 6。
註：`K` 檔用的是內部金鑰（runbook §20-4／§19-2 的 `mcp-internal-prod` 之類）；不是步驟 4 的站內幫手金鑰。【runbook 未載】正式機現有的內部金鑰檔名與位置，請業主確認。

### 步驟 10：`/mcp` 煙囪（runbook §5、§19-6）

```bash
curl -sS -o /dev/null -w "no-key -> %{http_code} (期望 401)\n" -X POST http://localhost:8100/mcp -H "Content-Type: application/json" -d '{}'
curl -sS -o /dev/null -w "bad-origin -> %{http_code} (期望 403)\n" -X POST http://localhost:8100/mcp -K /home/ec2-user/.curl-mcp-key -H 'Origin: https://not-allowed.example.com' -H "Content-Type: application/json" -d '{}'
curl -sS -X POST http://localhost:8100/mcp -K /home/ec2-user/.curl-mcp-key -H "Content-Type: application/json" \
  -H 'X-JGB-Identity: {"vendor_id":<vendor_id>,"session_id":"smoke_'"$(date +%s)"'","mode":"b2b","target_user":"property_manager"}' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | grep -o '"agent.turn"'
```
⚠️ 2026-10-15 實測：第三條直接打 `tools/list` 回 400「Missing session ID」——要先 `initialize`（加 `-H 'Accept: application/json, text/event-stream'`，從回應標頭取 `Mcp-Session-Id`），再帶 `-H "Mcp-Session-Id: <id>"` 打 `tools/list`；`/api/v1/agent/health` 也必須帶完整 `X-JGB-Identity`（含 `vendor_id`），否則 400 `IDENTITY_MALFORMED`。
預期：401、403，第三條印出 `"agent.turn"`。（若第三條回 4xx，對照 runbook §5 ② 的原指令。）`tools/list` 回 403 `VENDOR_*` ＝ 金鑰與 vendor 沒對上，檢查步驟 4 的 `vendor_ids`。

### 步驟 11：暖機（runbook §20-3b）

`up -d` 後第一則模型回合會撞逾時（容器要建細目索引並首呼模型）。打一回合暖機，確認 log 出現 `agent_turn trace_id=…` 再開始測。
**用什麼 client 打 `tools/call agent.turn`：【runbook 未載，需業主確認】**——runbook 只有 `tools/list` 的 curl；`tools/call` 需要先 `initialize` 取得 MCP session 再帶 session header，runbook 與 `docs/api/mcp-facade.md` 都沒有現成範例。可選：Claude Code 的 MCP client、line-bot 端的 harness（runbook §20-3b 提到「用 `.curl-mcp-key` 的 harness」）、或等 JGB 代理接上。

### 步驟 12：不變量稽核（runbook §19-6 ④、§10）

```bash
cd /home/ec2-user/AIChatbot && bash scripts/audit/check_invariants.sh 2>&1 | grep -E "❌|OVERALL"
```
⚠️ 容器內沒有 `make`（2026-10-15 實測 `exec: "make": executable file not found`），改在主機 repo 目錄跑腳本。預期：只剩不變量 44 失敗（題目原文檔只在開發機 `~/jgb-archive/ruler-9.13/questions.json`，正式機沒有，屬前置條件），其餘通過（2026-10-15：43 項 PASS）。不變量 3 會比對「容器內關鍵檔 digest 與 repo 一致」，所以容器必須是剛重建的、工作樹乾淨。若不變量 7（金額語義層）或 10 報紅，先停下回報（計畫 §3e 提過替身直接寫 `final_total` 的歷史）。

---

## 5. 功能 × 依賴對照表

「現在能用嗎」欄指**正式機 `USE_MOCK_JGB_API=false`（接真 JGB）**時；`替身` 指 `true` 時（只能驗流程，不代表接真 JGB 會過）。接口 B 各列細節與等誰見 `jgb2-api-requests.md` §1、§1b。

| 項 | 子項 | 接真 JGB 需要的 jgb2 API | 現在能用嗎（接真 JGB） | 等誰／缺什麼 |
|---|---|---|---|---|
| (1) | 查詢帳單、合約、修繕 | 既有 `GET /bills`、`GET /contracts/status-overview`、`GET /repairs`（帶 `viewer_user_id`）；#24（依成員可見範圍過濾、新增單筆 `GET /estates/{id}`） | **既有端點可用**；「依成員可見範圍過濾」的 JGB 端語義未確認（#24） | JGB 回 #24 |
| (2) | 修改前先確認 | 取決於被確認的動作（見 (6)(9)(10)(11) 與「改帳單到期日」）；#23（寫入 body 身分、冪等） | 確認卡流程本身是我方邏輯、可用；兌現看各動作 | JGB 回 #23 |
| (2) | 改帳單到期日 | 現行 `PATCH /agent/v1/bills/{id}`（同事產測試資料的造假資料工具、ssh-ed25519 簽章）；#23(e) 請 JGB 給正式對外路徑 | **只有替身走得通**；⛔ 真 API 先不測 | JGB 回 #23(e) |
| (3) | 依權限操作 | #23（能力檢查、越權 403／404 全站一致並附 `error.code`）、#24（讀取過濾、越權與不存在回應時間不可區分） | 我方側（身分 header、金鑰、session 綁定、固定句）**可測**；JGB 側過濾語義待回覆 | JGB 回 #23、#24 |
| (4) | 未收帳單加總（本月／逾期） | **#16** `GET /api/external/v1/bills/summary/unpaid` | **不可用**：非 mock 回降級、不發請求；使用者應看到固定句，⛔ 不印 0 筆 | JGB 實作 #16；回「未收是否含 status 8」 |
| (5) | 執行中修繕清單 | **#17** `GET /api/external/v1/repairs/in-progress` | **不可用**（同上） | JGB 實作 #17；回「執行中＝status 1／2／16」是否正確 |
| (6-1) | 自然語言新增修繕單 | 既有 `POST /repairs`；#2（`contract_id` nullable 等，**JGB 端主張未經驗證**）；#3（`emergency_status` 值域，**上線前必答**）；#23（body 帶 `role_id`＋`user_id`） | **可試**（測試團隊）；#3 答覆前 `emergency_status` 不得自動帶值（缺值留空讓人選） | JGB 回 #3；#2 我方實打驗證 |
| (6-2) | 照片新增修繕單 | **#22**（照片位元組如何交給 jgb2：(a) multipart 或 (b) 預簽上傳＋識別碼，我方建議 (b)）；JGB 專用上傳網域（`IMAGE_URL_ALLOWLIST`）；#23 | **照片進不來**（網域未定）；且我方目前只送 `broken_photos` 中繼資料，jgb2 端看不到影像內容 | JGB 回 #22 與上傳網域 |
| (8) | N 個月內到期合約 | **#18** `GET /api/external/v1/contracts/expiring` | **不可用**（同 (4)） | JGB 實作 #18；回月底夾法是否與畫面一致 |
| (9-1) | 自然語言新增物件 | **#19** `POST /api/external/v1/estates`；#24（建立後單筆物件讀取）；#23 | **不可用**（非 mock 降級） | JGB 實作 #19；回 `space_type`／`building` 值域、「台／臺」是否視同 |
| (9-2) | 謄本 PDF／照片新增物件 | #19、#23；JGB 專用上傳網域；**DocuMind**（非接口 B）：https＋Token＋DocuMind 端三項前提（S3 物件關 public-read、複核佇列認證、few-shot 留存） | **不可用**（#19 缺、網域未定、DocuMind 正式前提未解；正式機先不設 `DOCUMIND_BASE_URL`，使用者看到「未啟用」固定句） | JGB（#19、網域）、DocuMind 端 |
| (10-1) | 自然語言建立新合約 | **#20** `POST /api/external/v1/contracts`；#24（單筆物件讀取，含已出租）；#23 | **不可用**（非 mock 降級） | JGB 實作 #20；回 status／bit_status 初值 |
| (11-1) | 自然語言新增手動帳單 | **#21** `POST /api/external/v1/bills/manual`；#24；#23 | **不可用**（非 mock 降級） | JGB 實作 #21；回初始 status（替身 1 待發送） |
| (11-2) | 發票／收據照片新增手動帳單 | #21、#23；JGB 專用上傳網域；收據擷取用我方 `gpt-6-luna`，**不經 DocuMind** | **不可用**（#21 缺、網域未定） | JGB（#21、網域） |
| — | 站內幫手入口 | JGB 把 `HelpAssistantController@chat` 改成呼叫 `/mcp`（接口 A）；JGB 端功能開關與白名單 | 我方側就緒後仍需 JGB 接上才有使用者入口 | JGB |

**結論**：接真 JGB 的第一階段，能完整驗到的只有 (1)(3 的我方側)(2 的確認卡流程) 與 (6-1)；其餘 7 項要等 JGB 實作接口 B 才有真 API 可接。

---

## 6. 線上測試步驟

### 6.0 原則

- **先測不依賴新接口的**（第 5 章「現在能用」那幾列），其餘在 JGB 實作並回覆後，照 `jgb-acceptance-checklist-20261015.md` 的 A4／A5／A9／A10～A14 補測（該清單就是「換成真 API 後再驗一次」的版本）。
- 帳號與身分：JGB **測試團隊**（替身用的是展示團隊 role 20151；以 JGB 提供的測試團隊為準【待確認正式機測試團隊的 role_id、vendor_id、成員 user_id】）。接測清單要求**至少兩位成員**（成員甲看得到全部、成員乙只看得到一部分，且乙看不到的帳單／合約／修繕／物件各至少一筆），另備**另一個團隊**的成員一位。測試資料用合成資料，⛔ 真實客戶名、⛔ 真實個資。
- 每個劇本存：請求 header（去金鑰）、每回合 `message`、完整回應 JSON、`trace_id`。看 `outcome.state`／`expects`／`quick_replies`，⛔ 解析 `answer` 字串。模型措辭每次不同，判的是**事實值與流程狀態**，每個劇本建議跑 3 次記失敗數。
- 期望值由 JGB 資料算出來，**先寫下再測**；不以我方回答推回去。
- 寫入類：**先在測試團隊**；每個寫入動作先跑「確認卡按取消」確認 JGB 資料不變，再跑「按確認」。確認鍵 `confirm_submit:…`／`confirm_cancel:…` 的 `value` 原字串當下一回合 `message` 送回，⛔ 自己組。
- 測試單／測試物件事後怎麼清：【runbook 未載，需業主確認】（本文件不編刪除指令）。
- 帶 `attachment_purpose=document` 與 `image_urls`／`file_urls` 的劇本，要等 `IMAGE_URL_ALLOWLIST` 有 JGB 網域才測（第 6.3）。

### 6.1 第一關：部署煙囪（不需要任何 JGB 新接口）

做完第 4 章 步驟 7～12 並全部通過才往下。這關過 ＝ 服務起來了、設定對了、金鑰與 vendor 對上了。

### 6.2 第二關：接真 JGB，不依賴新接口（`USE_MOCK_JGB_API=false`）

| 劇本 | 做法 | 看什麼才算過 | 對應清單 |
|---|---|---|---|
| 身分與金鑰（我方側，最先測） | 1. 站內幫手金鑰、`X-JGB-Identity` **缺 `user_id`**；2. `user_id="anonymous"`；3. `vendor_id` 不在金鑰範圍；4. 人為在工具參數塞身分鍵 | 1. HTTP 400 `IDENTITY_MISSING_USER_ID`（**這條同時證明 `AGENT_ASSISTANT_KEY_IDS` 真的生效**）；2. 400 `IDENTITY_MALFORMED`；3. 403 `VENDOR_NOT_IN_KEY_SCOPE`；4. `INVALID_INPUT` | A3(c) |
| 同 session 換人 | 成員甲開一段對話並讓確認卡停在待確認；以**同一 `session_id`** 換成員乙發話，再按甲的 `confirm_submit` | 乙看不到甲的對話內容；按甲的鍵得到「這筆確認已失效，請重新確認一次。」；JGB 沒有寫入；另測同 user 換 role 也重置 | A3(d) |
| 查詢三域 | 成員甲各問一句帳單、合約、修繕（用 JGB 測試資料的真實編號）；成員乙問甲看得到而乙看不到的三筆；成員甲問不存在的編號 | 甲：單號、金額、日期、狀態與 JGB 資料逐欄一致。乙：回答**不含該筆任何欄位值**，且與「不存在編號」是**同一句**「系統裡查不到這個編號或名稱。」。JGB 端請求紀錄：每個讀取請求都帶 `role_id` 與 `viewer_user_id` | A1、A3(a)(b) |
| 他團隊對照 | 他團隊成員（`role_id` 為他團隊）問本團隊的帳單與合約 | 同上固定句、不含欄位值 | A3(b) |
| 降級行為（#16～#18 還沒有） | 問「本月未收帳單」「執行中修繕單」「三個月內到期合約」 | 看到固定句「這項統計目前還不支援：JGB 系統尚未開放這個查詢，開放後就能直接查。」；**⛔ 不得印「共 0 筆」「0 元」**（F7）。這同時天然驗證了接測清單 A4(4)「上游錯誤走固定句而非 0」 | A4(4) |
| 文字報修（寫入類，測試團隊） | 一句話描述問題＋物件 ⇒ 確認卡 ⇒ **先按取消** ⇒ 再來一次 ⇒ 按確認 | 出卡時 `outcome.state=confirm_pending`、`expects=button`，欄位逐欄列出、未給的選填欄不出現；取消後 JGB 資料不變；確認後 JGB 多一張修繕單，欄位＝卡片；**`emergency_status` 在 #3 答覆前不得自動帶值**；重按同一顆確認鍵不重複建立（真 JGB 的冪等要等接測才算數，在那之前當作「可能重複建立」，接口 A §6 F2-6） | A2、A6 |
| 「不用確認直接建」 | 說「不用確認直接建」 | 仍出確認卡、不直接寫入 | A2(c) |
| 確認回合逾時 | 若確認那一回合逾時 | 前端／測試者 ⛔ 自動重送；先到 JGB 確認是否已建立（F2-6） | F2-6 |
| 不可見物件建修繕單 | 成員乙對甲才看得到的物件報修 | 不得出確認卡（S5 修正輪項，計畫 §7 延後註記：回覆可能是轉人或反問而非固定句，屬已知 P3） | A3(e) |

⛔ 這一關**不測**：「改帳單到期日」（真路徑是造假資料工具）、任何要 #16～#21 的功能、照片／PDF。

### 6.3 第三關：JGB 回覆並實作後（照接測清單補測）

| 解鎖條件 | 補測 |
|---|---|
| JGB 實作 #16、#17、#18 | A4、A5（多於 20 筆分頁）、A9，兩位成員結果必須不同 |
| JGB 實作 #19、#20、#21、#24 | A10、A12、A13（含「卡上那一筆＝寫入那一筆」、物件多筆／零筆不出卡）、A3(e) |
| JGB 回覆 #22 與上傳網域，我方設 `IMAGE_URL_ALLOWLIST` | A7（照片進修繕單，含 `exp`、5 MB、轉址、非白名單的負例）、A14（收據，含非台幣與內嵌指示的負例） |
| DocuMind 完成 https＋Token 與三項前提 | A11（謄本；只用合成或去識別素材，**⛔ 所有權人姓名、統編、住址不得出現在卡片、送給 JGB 的 body、對話回答**） |
| JGB 回覆 #23(e) | 「改帳單到期日」走正式路徑後再測 |
| S3 修正輪／S5 修正輪實測完成 | 接口 A §13 的 8 條待確認項由我方補實測結果，之前請勿當作已保證 |

測 A16：全程只用測試團隊與測試資料，⛔ 在正式資料上寫入。

---

## 7. 回退

### 7.1 先看這個：共用服務的風險

這台 `rag-orchestrator` 同時服務 LINE OA demo（runbook §20）。runbook §19-7 紅框明寫：**舊對話鏈已於 2026-09-11 整條刪除，關掉 `AGENT_TURN_ENABLED` 之後不會退回任何東西，而是完全沒有對話服務**。所以功能開關是「止血」，不是「回到舊的」；真正的回退是回滾版本。

### 7.2 功能開關（改 `.env` 後 `up -d`，免重建 image）

```bash
# 一鍵關閉寫入（讀取與對話仍可用）：.env 設 AGENT_WRITE_TOOLS_ENABLED=false
sed -i 's/^AGENT_WRITE_TOOLS_ENABLED=.*/AGENT_WRITE_TOOLS_ENABLED=false/' .env
docker-compose -f docker-compose.prod.yml up -d --no-deps rag-orchestrator      # 不加 --build（runbook §19-7）

# 關閉整個 agent.turn（站內幫手與 LINE OA 都會沒有對話工具）：
sed -i 's/^AGENT_TURN_ENABLED=.*/AGENT_TURN_ENABLED=false/' .env
docker-compose -f docker-compose.prod.yml up -d --no-deps rag-orchestrator
```
驗證（runbook §19-7）：
```bash
curl -s -X POST http://localhost:8100/mcp -K /home/ec2-user/.curl-mcp-key -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | grep -o '"agent.turn"'
```
預期：`AGENT_TURN_ENABLED=false` 後**無輸出**（工具未註冊，不是「註冊了但拒絕」）。關寫入後 `/api/v1/agent/health` 的 `write_tools_enabled` 應為 `False`。
另一個選項：只把 `USE_MOCK_JGB_API` 改回 `true`＋同時把 `AGENT_VERIFIER_MODE` 改回 `grounding_observe`（runbook §20-7：兩者要一起改，只改替身、忘了改模式 ⇒ 健檢紅且沒有引用檢查；`observe_only` 配非 mock 會啟動 raise）。此舉會讓整站回到替身資料，LINE OA 與網頁客服都會看到替身資料。

### 7.3 程式回到前一版（回滾版本）

```bash
cd /home/ec2-user/AIChatbot
git checkout <步驟 1 記下的 hash>          # runbook §19-7 的寫法；不要用 reset --hard
docker-compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator
```
再跑第 4 章 步驟 7、9、12 確認（稽核腳本不變量 3 會抓容器與工作樹不一致）。`.env` 退回：`cp -p .env.bak_<時間戳> .env` 後 `up -d`。
本次**沒有 DB migration**，所以沒有 schema 要回復；步驟 4 新增的那一列 `api_keys` 無害，要停用就把該金鑰 `is_active` 設 false 【runbook 未載停用金鑰的標準指令，需業主確認，本文件不編】。
回退後 `git status` 會處於 detached HEAD；之後要回到 main 再 `git checkout main`。

---

## 8. 待 JGB／待業主決定

### 8.1 待 JGB 回答（接口 B §1b 彙整，詳見 `jgb2-api-requests.md` §1b）

| 列 | 問題 | 阻擋 |
|---|---|---|
| #16 | 「未收」是否含 `status` 8 待對帳（現行假設 2 待繳費＋8 待對帳） | 否（影響數字） |
| #16～#18 | 路徑、參數、回應欄位是否接受；#17 執行中＝`status` 1／2／16 是否正確；#18 `active=1、is_newest=1、is_history=0` 與月底夾法是否與畫面「即將到期」一致 | 是 |
| #19 | `space_type`、`building` 值域；`district` 對不到的錯誤形狀；建物件 `city` 的「台／臺」是否視同 | 否 |
| #19／#24 | 帶 viewer 的單筆 `GET /estates/{id}`（含已出租）；現行 `GET /estates` 只回刊登中，已出租物件會被誤判查無 | 是（建合約／手動帳單依賴） |
| #20、#21 | 合約初值 `status`／`bit_status`、`deposit_amount` 未給預設 0；手動帳單初始 `status` | 否 |
| #22 | 照片上傳方式 (a)／(b)（我方建議 (b)）；JGB 專用上傳網域名稱；該網域是否與憑 IP 信任主機共用；每單 5 張是否一致 | 是 |
| #23 | `user_id` 是否驗屬於 `role_id` 團隊；成員能力檢查現況；歸屬欄位清單與 422 訊息；越權回 403 或 404（二擇一全站一致並附 `error.code`）；**改帳單到期日的正式對外路徑** | 是 |
| #24 | `viewer_user_id` 過濾語義（過濾而非圈定成空）；單筆讀取；越權與不存在回應時間不可區分 | 是 |
| #3 | `emergency_status` 值域（1＝緊急還是相反） | 上線前必答 |
| 另 | JGB 代理逾時須大於 `AGENT_TURN_TIMEOUT_S`；JGB 端功能開關與測試期白名單（接口 A §14）；`HelpAssistantController@chat` 改呼叫 `/mcp` | — |

### 8.2 待業主決定

| 編號 | 決定項 | 背景與建議（建議不代表已決） |
|---|---|---|
| D1 | `AGENT_VERIFIER_MODE` 正式機用 `enforce` 還是 `grounding_observe` | runbook §20 記正式為 `grounding_observe`（DSP-039／040），**未查證正式機現值**；接口 A §2 要求接測以 `enforce` 為準；`grounding_observe` × 真 API 會讓健檢轉紅並關掉引用檢查。建議驗收期用 `enforce` |
| D2 | 與 LINE OA demo 的關係：同機同時切換，或另排時段／另一套 | 見第 1 章阻擋項 3；runbook §20 demo 整站跑替身，改 `USE_MOCK_JGB_API=false` 影響 LINE OA 與網頁客服 |
| D3 | `JGB_API_BASE_URL` 接哪個 JGB 環境；`JGB_API_KEY` 由誰提供 | compose 預設 `https://preview.jgbsmart.com`；測試團隊所在環境【待確認】 |
| D4 | commit／push 範圍與拆法（站內幫手線 vs 9.11 線） | 計畫 §7 記「commit 時再跟業主確認兩條線怎麼拆」；新檔不可漏 |
| D5 | 是否在兩份 compose 宣告新增的 7 個 env 鍵 | 不宣告 ⇒ 站內幫手的 key 白名單、DocuMind、抓圖白名單、文件模型都無法經 `.env` 設定 |
| D6 | `AGENT_TURN_TIMEOUT_S`（建議 90）與 `AGENT_BUDGET_DEADLINE_S`（demo 45）的值 | 文件預算上限 `min(45, 逾時/2)`；實測關係屬 S3 修正輪待確認項 |
| D7 | DocuMind 上線前提 | 正式機先不設＝謄本關閉。要開須 DocuMind 端：① S3 物件關 public-read ② 複核佇列認證（現無） ③ few-shot 留存處理；並確認認證格式（暫用 `Authorization: Bearer`）與 https。三項未解前，謄本只限測試期、合成素材 |
| D8 | 照片上傳方式與 `IMAGE_URL_ALLOWLIST` | 等 JGB 回 #22 與網域；有設值時取代預設（含 `relay.jgbsmart.com` 與否需明列） |
| D9 | 站內幫手金鑰明文交付 JGB 的管道；測試資料事後清除方式；停用金鑰的標準指令 | runbook 未載（第 4 章 步驟 4、第 6 章 6.0、第 7 章 7.3） |
| D10 | `tools/call agent.turn` 用哪個 client 做暖機與線上測試 | runbook 未載（第 4 章 步驟 11） |
