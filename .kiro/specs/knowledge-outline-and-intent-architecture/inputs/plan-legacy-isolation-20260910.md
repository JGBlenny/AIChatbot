# Plan：舊鏈隔離與共用詞彙歸位（2026-09-10；第 3 稿）

**審查歷程**：第 1 稿 → security-reviewer 八條（處置見 §7）→ 第 2 稿 → plan-verifier **REVISE** 八條
（2 BLOCKER／4 MAJOR／2 MINOR，處置見 §8）→ 本稿。
**基準 HEAD**：`1ef9b68e`（main＝feat；⛔ 第 2 稿誤寫 `d1e46afb`，已更正）。**分支**：`feat/agentic-mcp`。
**上位 spec**：`.kiro/specs/agentic-mcp-orchestration`（需求 12.1「agent 路徑不呼叫的舊鏈符號」）。
**⛔ 本 Plan 只含 S1a／S1b／S2；砍舊鏈（S3）不在範圍**，理由見 §5。

---

## 0. 問題陳述

repo 同時住著兩條對話線。新線 16 處 import 落在名字指向舊線的模組上：讀碼的人（與子代理）
看到 `from services.presales_gate import SENSITIVE` 會以為敏感類是售前限定，實際上它治四個受眾。
這是「機制正確、命名說謊」，比死碼更貴。

**⛔ 本節不放模組數與行數。** 第 2 稿曾放 36／43／40／20,694，那組數字出自一支只存在於
scratchpad 的腳本，且用的分桶算法本身有缺陷（見 §8 B1）。**範圍以 S1a 產出的清單為準**，
⛔ 不以任何預先寫在 Plan 裡的數字為準。

**目標形態**：repo 只有一條活線；舊線關進可辨識的隔離區且有機制擋新線碰它；
共用詞彙住在名副其實、由存活線擁有的模組。

---

## 1. S1a｜產清單（唯讀，⛔ 不動任何既有檔）

**成果**：一支進版控的檢查器，與四份凍結清單，交主執行緒核可。

### 1.1 分桶算法（寫死，⛔ 不得由執行者自行決定）

**新線集合是宣告式，⛔ 不用可達性算。** 理由：`services/agent/shadow.py`、`agent_rules.py`、
`bootstrap.py`、`canon/**` 由 `app.py` 接線而非由 facade／runtime import，可達性算會把它們漏掉
（第 2 稿的缺陷）。

```
新線集合   := services/agent/**  ∪  {routers/agent_entry.py}          # 宣告
新線閉包   := reach(新線集合)                                          # 不變量 35 的左邊
舊線進入點 := {routers/chat.py, routers/platform_sop.py, routers/intents.py,
              routers/suggested_intents.py, services/sop_orchestrator.py}
舊線可達   := reach(舊線進入點)
第四桶     := 執行期耦合帳（見 1.3），人工維護、獨立檔
舊線獨有   := 舊線可達 − 新線集合 − 新線閉包 − 第四桶                  # 不變量 35 的右邊，也是上檔頭的集合
共用       := 舊線可達 ∩ 新線閉包 − 第四桶
```

`reach()` 的解析規則：`ast.walk` 整棵樹（函式內 import 大量存在，`mcp_facade` 約 30 處）；
處理 `from <套件> import <子模組>`（如 `from services.agent.tools import action as action_tools`、
`from services import usage_metering as um`），先試 `<模組>.<名字>` 是否為模組再當符號。
⛔ 只走 `tree.body` 會大量低估。

### 1.2 檢查器落點與註冊

- 檔案：`scripts/audit/checks/agent_import_closure.py`（⛔ 不是 `scripts/audit/` 根，比照既有 13 支 checks）。
- 註冊進 `scripts/audit/check_invariants.sh`，比照不變量 33／34 的寫法：
  先跑 `--self-test`，自測不過即印「檢查器本身失效，其 PASS 不可信」並 FAIL。
- 輸出四份清單到 `scripts/audit/data/`：`legacy_only.txt`、`shared.txt`、`agent_line.txt`、
  `runtime_coupled.txt`，各檔一行一模組、排序固定。

### 1.3 第四桶＝執行期耦合帳（BLOCKER 2 的處置）

**規則寫死**：
- 第四桶成員 **⛔ 不入 `legacy_only.txt`**、**⛔ 不上「舊鏈維護級」檔頭**、**⛔ 不參與不變量 35 的交集判定**。
- 檢查器加自我一致性判定：**同一模組同時出現在兩份清單 ⇒ FAIL**。
- 首筆登記 `services/conversational_engine.py`。理由：新線每一回合的會話狀態讀寫都經過它——
  `services/agent/state_store.py` 的 `load`／`start`／`save`／`close` 轉呼
  `ConversationalEngine.get_state`／`_start`／`_save`／`_close`（同一張 `form_sessions`、同一組 SQL）；
  引擎實例由 `mcp_facade._open_state_store` 經 `_app_state(deps, "conversational_engine")` 從
  `app.state` 取得，REST 側由 `routers/agent_entry.py` 的 `EngineStateStore` 取得。
  **這條邊在 import 圖上完全看不到**（依賴注入＋鴨子型別）。

### 1.4 ⛔ 射程聲明

不變量 35 **只覆蓋 import 邊**。檢查器 docstring 與 `.claude/MAP.md#legacy-rest-chat` 明文寫死兩句：
**(a) 它不覆蓋 `app.state` 注入的執行期耦合；(b) 它綠不構成「該模組可安全刪除」的授權。**

### 1.5 S1a 驗收

1. 檢查器 `--self-test` 通過。
2. **負對照（BLOCKER 1 的處置）**：`legacy_only.txt` 中 ⛔ 不得出現任何 `services/agent/**`
   或 `routers/agent_entry.py`；出現即 FAIL。
3. **正對照**：`legacy_only.txt` 必須含 `services/sop_orchestrator.py`（已知必然的舊線模組）；
   它若沒中，就是算法或路徑壞了，不是「舊線很乾淨」。
4. **清單交主執行緒核可才進 S1b。** 差異處置門檻：清單若含任何我判斷不該在裡面的模組 ⇒
   停下改算法，⛔ 不得先上檔頭再說。

**S1a 非範圍**：⛔ 不加任何檔頭、⛔ 不改任何既有檔（只新增檢查器、清單、`check_invariants.sh` 註冊行）。

---

## 2. S1b｜上檔頭與絆線（依 S1a 核可的清單）

1. `legacy_only.txt` 列出的每個模組加統一檔頭：
   `⚠️ 舊鏈（REST /api/v1/message）・維護級・⛔ 新工作不得擴充`，指向 `.claude/MAP.md#legacy-rest-chat`。
2. `.claude/MAP.md` 新增功能鍵 `#legacy-rest-chat`，含 §1.4 射程聲明兩句。
3. `tests/unit/conversational/`、`tests/unit/sop/`、`tests/unit/forms/`、`tests/unit/chat_flow/`
   加 `README.md`「維護級：只保綠、不擴充」，比照既有 `tests/unit/decision/`／`tests/unit/backtest/`。
4. 不變量 35 正式啟用。

**驗收**
- `scripts/run-tests.sh unit tests/unit/agent tests/unit/audit` ＝ 2411 passed。
- `make audit` OVERALL PASS，輸出中出現不變量 35 且判 PASS。
- **正對照兩條都要跑**：① 暫時在 `services/agent/runtime.py` 加
  `from services.sop_orchestrator import SOPOrchestrator`；② 暫時在 `routers/agent_entry.py` 加同一行。
  兩條都必須 FAIL 並印出違規邊；還原後回綠。⛔ 少跑任一條，S1b 不得收案。
- golden 28 條逐位相同。

---

## 3. S2｜共用詞彙歸位（行為不變）

### 3.1 搬 7 個符號

來源 `services/presales_gate.py`（357 行，混住兩類東西）。**搬走 7 個**到
`services/handoff_contract.py`：`FactClass`、`SENSITIVE`、`HANDOFF_WORDS`、`HandoffReason`、
`Handoff`、`parse_fact_class`、`scan_handoff_mentions`。

**⛔ 三支 `build_*` 不搬**：`build_handoff`、`build_llm_mention_handoff`、`build_partial_handoff`
在 `services/agent/**` 零 import，只出現在散文裡，而且是**刻意迴避**的：
`services/agent/tools/handoff.py` 檔頭寫「⛔ 不呼叫 `presales_gate.build_handoff`：那支由
`fact_class` 的敏感性…會把模型講的原因悄悄改寫成另一個原因」。
`build_handoff` 是全 repo 唯一把 `fact_class ∈ SENSITIVE` 推導成 `sensitive_no_grounding` 的地方。

**留在原地**：三支 `build_*`、`extractive_enabled`、`presales_threshold`、`analyze_ask`、
`ask_is_answering`、`looks_like_question`、`split_declaratives`、`strip_declarative_clauses`、
`is_multi_item_question`、`IDENTITY_REASK_PATTERNS`、`reask_hits` 及其詞表常數。

新線消費端 6 檔改 import：`turn_context.py`、`exit_gates.py`、`verifier.py`、`runtime.py`、
`tools/handoff.py`、`agent_rules.py`。

`presales_gate.py` **逐名 re-export**，並保留既有 `__all__` 逐名列出。
⛔ **不得用 `from … import *`**（與「明列」互斥，且靜態閉包檢查器碰上 wildcard 最沒轍）。

### 3.2 搬確認卡與表單常數

`services/conversational_engine.py` 的 `CONVERSATIONAL_FORM_ID`、`_QR_SUBMIT`、`_QR_EDIT`、
`_QR_CANCEL`、`_DEFAULT_QR_LABELS` 搬到 `services/form_contract.py`，去底線改公開名
（這五個是底線開頭的私有名被跨套件 import，見 `services/agent/tools/confirm.py`、`tools/session.py`）。
舊位置逐名 re-export。

**刪一個死常數**：`routers/agent_entry.py` 的 `CONVERSATIONAL_FORM_ID = "conversational"`
零使用點、零外部 import ⇒ **直接刪那一行**（⛔ 不是改成 import——那會替一個只依賴
`services.agent.identity` 的 router 憑空新增依賴邊）。執行者先跑
`git log -S'CONVERSATIONAL_FORM_ID' --oneline -- rag-orchestrator/routers/agent_entry.py rag-orchestrator/services/conversational_engine.py`
確認歷史是否曾分歧，結果記進 commit message。

### 3.3 引用同步集合（MAJOR 3 的處置）

**定義**（可重跑）：
```
grep -rn "presales_gate\|conversational_engine" rag-orchestrator/services/agent rag-orchestrator/routers/agent_entry.py
```
扣掉 import 述句後的散文命中（現況 32 處，含 `agent_rules.py`、`question_sensitivity.py`、
`output_schema.py`、`confirm_card.py`、`runtime.py`、`tools/handoff.py`、`tools/registry.py`、
`verifier.py` 檔頭那句「只 import `presales_gate`／`conversational_config`」），**逐一改成新出處**。
`.kiro/specs/agentic-mcp-orchestration/design.md` 的紅線清單同步。

**舊線側的具名例外**：`routers/chat.py` 那句
「⚠️ 本 Literal 的值域必須與 `services/presales_gate.py:HandoffReason` 逐值相同」
**不動**——逐名 re-export 之後 `presales_gate.HandoffReason` 仍解析到同一個物件，該句仍為真。
記進 commit message，⛔ 不列為債。

### 3.4 不搬，且寫下理由

| 模組 | 為何不搬 |
|---|---|
| `services/conversational_config.py` | 名副其實（兩線共用的對話組態），27 處非 agent 引用；改名收益低於風險 |
| `services/decision_layer.py` | 不變量 8 釘住「門檻唯一讀值點」（`scripts/audit/checks/decision_threshold_ast.py` 的 `ALLOWED_FILE` 是路徑字面量）；名稱不誤導 |
| `services/vendor_knowledge_retriever_v2.py` | 不變量 29 釘住「可見性謂詞單一來源」；`_v2` 命名確實不佳，列 S3 |

**⚠️ S3 的前置（登記不處理）**：不變量 29 對**找不到的 target 靜默略過**
（`scripts/audit/checks/agent_boundary.py`：「尚未建立，略過」／「找不到此函式，略過」，
只要 `checked > 0` 仍回 True）。S3 若更名 `vendor_knowledge_retriever_v2.py`，
隔離謂詞的唯一來源不變量會**綠但瞎**。⇒ S3 更名的前置是先讓不變量 29 對缺失 target 大聲失敗。

### 3.5 清單更新（BLOCKER 2 的處置）

S2 拆掉 `tools/confirm.py`／`session.py` 對 `conversational_engine` 的兩條 import 邊後，
它會從「共用」掉出來。**處置寫死：把它加進 `runtime_coupled.txt`（第四桶），
⛔ 不得加進 `legacy_only.txt`、⛔ 不得上檔頭。** 檢查器的「同一模組不得出現在兩份清單」自我一致性判定會擋住做錯。

### 3.6 S2 驗收

1. `scripts/run-tests.sh unit tests/unit/agent tests/unit/audit` ＝ 2411 passed；`unit tests/unit/api` ＝ 318 passed。
2. **golden 28 條逐位相同**（本片主驗收：純搬家，任何位元差異即為缺陷）。
3. `make audit` OVERALL PASS，不變量 8／29／35 皆綠。
4. **殘留引用改用 S1a 的 AST 檢查器判，⛔ 不用 grep**（grep 抓不到
   `from services import presales_gate` 與 `import services.presales_gate` 兩種形狀）：
   新線閉包中 `services/agent/**` 對 `presales_gate`／`conversational_engine` 的 import 邊 ＝ 0。
   **正對照**：同一支檢查器對 `services/conversational_config` 仍應報出邊（證明它看得見這類邊）。
5. **舊線消費端的逐檔判準**（MAJOR 4 的處置，取代「一字未改」這個測不到的說法）：
   - `services/conversational_engine.py`：**允許**的 hunk 只有兩種——移除被搬走的五個常數定義、
     新增逐名 re-export。出現其他形狀即為缺陷。
   - `routers/chat.py`、`services/llm_answer_optimizer.py`：`git diff -- <path>` 必須為空。
   - ⛔ 不用 `git diff --stat` 的行數判斷（分不出邏輯行與 re-export 行）。

---

## 4. 擁有權、派工、停止門檻

| 片 | 執行者 | 工作樹 | 前置 |
|---|---|---|---|
| S1a | `executor` | worktree A | 無 |
| S1b | 同 A（S1a 核可後續作） | worktree A | **S1a 清單經主執行緒核可** |
| S2 | `executor` | worktree B | **S1a＋S1b 併回** |

⛔ 派工 brief 必含：不得 `git stash`；不得讀 `.env`；不得 push；不得改 `services/agent/runtime.py`
以外的舊線邏輯。

**停止門檻**（觸發即停下交主執行緒，並**記錄已排除的假設**）：
- golden 出現任何位元差異且 30 分鐘內無法歸因為「搬家以外的行為改變」。
- 不變量 35 的自我測試或任一正／負對照跑不出預期結果 ⇒ 檢查器本身失效，該片不得收案。
- S1a 產出的 `legacy_only.txt` 含 `services/agent/**` 或 `routers/agent_entry.py`。
- S2 發現某符號同時被兩線以**不同語義**使用 ⇒ 停下，這是設計問題不是搬家問題。

---

## 5. 交業主裁決（S3 的前置，⛔ 本 Plan 不自行選邊）

**D-A｜`spec.json` 的遷移策略寫「M3 prospect 切換、舊鏈可回切」。** 砍掉舊鏈＝放棄回切能力。
要砍，需業主明示放棄，並在 `agentic-mcp-orchestration` 加里程碑（暫稱 M6）與 `DECISIONS.md` 一條。

**D-B｜`roadmap.md` 寫「呼叫方走 `POST /rag-api/v1/message`，⛔ 不走 `/mcp`」**
（理由：母 design 1.4「jgb2／LINE 走 REST，MCP 是 server-to-server」）。
但實際交付給 line-bot 的契約走的是 `/mcp` 的 `agent.turn`。**這句 spec 與現況已不符**，
砍 REST 之前要先改對，否則等於照著一份說反話的文件動刀。

**D-C｜`/api/v1/message` 不是純舊線**：`routers/chat.py` 在該端點內分流到
`agent_entry.handle_agent_entry`（新線的 REST 入口，目前睡著——`AGENT_AUDIENCES` 預設空），
`app.py` 的計量中介層也以該路徑字串判斷是否計量。三個計量形狀：
1. **漏計**：middleware 用**字串等值**不是前綴。入口一改路徑，計量**靜默停止**；
   查無任何測試或不變量釘住這個字面量（不變量 5 只抓得到全面停擺）。
2. **雙計／歸錯屬**：`services/usage_metering.py` 的 `begin` 無條件 `_ctx.set(...)`、**無巢狀防護**。
   今天不可達；合併入口後第二次 `begin()` 會覆蓋第一個 context ⇒ 第一個永不 finalize（漏一列），
   外層 `finalize()` 去結內層（歸錯屬）。⇒ 合併入口前先給 `begin()` 加**大聲失敗**的重入防護。
3. **計費單位不同**：業主定案「額度按訊息計」。一則訊息在 REST 是 **1 列**，
   在 MCP 是 **N 列**（N＝工具呼叫數，不變量 31）。砍 REST 是換計費單位，不只是搬路徑。

**D-D｜業主 2026-09-10 已述**：jgb2 的 `HelpAssistantController@chat` 代理到
`https://chatai.jgbsmart.com/rag-api/v1/message`，但該功能仍在測試期
（佐證：`config/services.php` 的 `ASSISTANT_CHAT_TEST_ALLOW_SOCIAL_IDS`「測試期暫用白名單」）。
⇒ 產品面不再阻擋。

**D-E｜S3 的意義被一條看不見的依賴改寫**：見 §1.3。
**`conversational_engine.py` 不能砍，也不能標成舊線。** S3 至少拆成兩件：
**(a) 先把會話狀態持久化從 `ConversationalEngine` 剝離成新線自有的實作**，(b) 才談砍
`routers/chat.py` 與 SOP。(a) 動的是每一回合都在跑的路徑，風險等級與 S1／S2 完全不同，必須獨立立案。
⇒ 真正可刪的集合要等 (a) 完成後由 S1a 的檢查器重算。

---

## 6. 本 Plan 未做的量測

- 舊線在線上的真實流量（`/api/v1/message` 近 14 天）未查——需業主跑線上 SQL。
  S1a／S1b／S2 不依賴此數字；S3 依賴。

---

## 7. security-reviewer 處置表（第 1 稿 → 第 2 稿）

| 編號 | 優先級 | 內容 | 處置 |
|---|---|---|---|
| F1 | P4＋P3 | 拒答政策序列化面無發現；但 `verifier.py` docstring 與 design 紅線清單會變成假話 | **FIX**（§3.3） |
| F2 | P2 | 三支 `build_*` 被誤劃為共用（新線零 import、且刻意迴避） | **FIX**（搬 10 改搬 7，§3.1） |
| F3 | P3 | `agent_entry` 的重複常數是死常數，改 import 反而新增依賴邊 | **FIX**（改為刪除，§3.2） |
| F4 | **P1** | 靜態閉包看不見 `app.state` 注入；S2 會把每回合都在跑的引擎推進舊線桶 | **FIX**（§1.1／1.3／1.4／3.5／5 D-E） |
| F5 | P4＋P2 前瞻 | 不變量 8／29／27–31 不被弱化；但不變量 29 對缺失 target 靜默略過 | 本體無需動；前瞻 **DEFER 並登記**（§3.4） |
| F6 | P2（S3） | 計量漏計／雙計／計費單位三形狀 | **DEFER 到 S3，登記**（§5 D-C） |
| F7 | P3 | §0 數字不可重跑 | **FIX**（§0 拿掉數字，範圍改以 S1a 清單為準） |
| F8 | P3 | re-export 寫法自相矛盾 | **FIX**（逐名，⛔ 不用 wildcard，§3.1） |

## 8. plan-verifier 處置表（第 2 稿 → 第 3 稿）

| 編號 | 嚴重度 | 內容 | 處置 |
|---|---|---|---|
| B1 | **BLOCKER** | §0 分桶用兩個進入點、§1.4 用三個，互斥；`routers/agent_entry.py` 會落進「舊線獨有」並被蓋上「⛔ 新工作不得擴充」檔頭；`shadow`／`agent_rules`／`bootstrap`／`canon` 兩邊都不可達 | **FIX**：§1.1 改為**宣告式新線集合**＋寫死分桶算法；§1.5 加**負對照**（清單不得含 `services/agent/**`／`agent_entry`）。⚠️ 我自行重驗過此缺陷確實存在 |
| B2 | **BLOCKER** | §1.6 與 §2.3 對 `conversational_engine` 歸屬字面互斥；第四桶邊界未定義 | **FIX**：§1.3 寫死第四桶規則（不入 legacy、不上檔頭、不參與交集）＋檢查器加「同一模組不得在兩份清單」自我一致性判定；§3.5 明訂處置 |
| M3 | MAJOR | S2 消滅一個命名說謊卻留下 9＋處新的；`routers/chat.py` 那處撞上「舊線一字不改」 | **FIX**：§3.3 用可重跑 grep 定義引用同步集合（現況 32 處散文命中）；`chat.py` 那句**判為不動**——re-export 後 `presales_gate.HandoffReason` 仍解析到同一物件、該句仍為真 |
| M4 | MAJOR | 「舊線消費端一字未改」測不到；漏 `llm_answer_optimizer.py`；與 §2.2 自相矛盾 | **FIX**：§3.6 第 5 點改為逐檔 hunk 形狀判準，三個檔全列 |
| M5 | MAJOR | grep 驗收只覆蓋一種 import 形狀 | **FIX**：§3.6 第 4 點改用 S1a 的 AST 檢查器判，附正對照 |
| M6 | MAJOR | §0 數字既是範圍又不可重跑，且無差異處置門檻 | **FIX**：§0 拿掉數字；S1a 拆成獨立一片、清單先核可才動檔頭；§1.5 第 4 點定門檻 |
| M7 | MINOR | 檢查器落點與註冊未寫明 | **FIX**：§1.2（`scripts/audit/checks/`＋註冊進 `check_invariants.sh`，比照 33／34） |
| M8 | MINOR | 停止門檻缺記錄要求 | **FIX**：§4 加「記錄已排除的假設」 |
| — | — | 基準 HEAD 誤寫 | **FIX**：檔頭改 `1ef9b68e` |

**我自行重驗過的四條**（⛔ 不憑代理單一說法）：B1 的分桶缺陷（我自己那份輸出裡
`routers.agent_entry` 確在 legacy-only、`services.agent.shadow` 等四個在「兩邊皆不可達」桶）；
F4-a 的 `state_store.py` 轉呼四個引擎方法；F2 的三支 `build_*` 在 `services/agent/**` 零 import
（正對照：`FactClass` 同一支 grep 命中三檔以上）；F3 的 `CONVERSATIONAL_FORM_ID` 零使用點。
