# Plan：舊鏈隔離與共用詞彙歸位（2026-09-10；第 2 稿——security-reviewer 八條處置已併入）

**基準 HEAD**：`d1e46afb`（main＝feat）。**分支**：`feat/agentic-mcp`。
**上位 spec**：`.kiro/specs/agentic-mcp-orchestration`（需求 12.1「agent 路徑不呼叫的舊鏈符號」）。
**⛔ 本 Plan 只含 S1／S2 兩片；砍舊鏈（S3）不在範圍**，理由見 §5 裁決單。

---

## 0. 問題陳述（業主 2026-09-10：「換成新架構，那些就是潛在誤導的因素」）

repo 現在同時住著兩條對話線，靜態 import 可達性實算（腳本 `scratchpad/import_graph.py`，
進入點：新線 `services.agent.mcp_facade`／`runtime`；舊線 `routers.chat`＋SOP＋intents）：

| 集合 | 模組數 | 代表 |
|---|---|---|
| 舊線獨有 | 36（20,694 行） | `routers/chat.py` 5,107 行、SOP 5 支、intent 2 支、表單／responsibility 系列 |
| 兩線共用 | 43 | `presales_gate`、`conversational_engine`、`decision_layer`、檢索三支、`jgb.*` |
| 新線獨有 | 40 | `services/agent/**` |

**誤導的來源不是舊線那 36 個，是共用那 43 個。** 新線有 16 處 import 落在名字指向舊線的模組上；
讀碼的人（與子代理）看到 `from services.presales_gate import SENSITIVE` 會以為敏感類是售前限定，
實際上它治四個受眾。這是「機制正確、命名說謊」，比死碼更貴。

**目標形態**：repo 只有一條活線；舊線不是刪掉就是關進可辨識的隔離區且有機制擋新線碰它；
共用詞彙住在名副其實、由存活線擁有的模組。S1／S2 是往目標形態的兩步，兩步都行為不變。

---

## 1. S1｜舊線隔離與絆線（行為不變）

**成果**：舊線 36 個模組被明確標記，且新線再度指向舊線時 `make audit` 會紅。

**範圍**
1. 36 個舊線獨有模組加統一檔頭：`⚠️ 舊鏈（REST /api/v1/message）・維護級・⛔ 新工作不得擴充`，
   指向 `.claude/MAP.md#legacy-rest-chat` 與本 Plan。
2. `.claude/MAP.md` 新增功能鍵 `#legacy-rest-chat`，列出 36 模組與唯一進入點。
3. `tests/unit/conversational/`（125 檔）、`tests/unit/sop/`、`tests/unit/forms/`、`tests/unit/chat_flow/`
   加 `README.md`「維護級：只保綠、不擴充」，比照既有 `tests/unit/decision/`／`tests/unit/backtest/` 的寫法。
4. **不變量 35（新機制）**：新線 import 閉包 ∩ 舊線獨有模組 ＝ ∅。
   - 檢查器 `scripts/audit/agent_import_closure.py`（**進版控**，⛔ 不留在 scratchpad）：
     以 `ast` 由新線進入點做可達性，與凍結的舊線獨有清單取交集，非空即 FAIL 並印出違規邊。
   - **進入點集合（F4-c①）**：`services.agent.mcp_facade`、`services.agent.runtime`、
     **`routers.agent_entry`**（新線的 REST 入口，§5 D-C 那條）。⛔ 漏第三個等於證不到 REST 那半。
   - **解析形狀（F4-c②③）**：必須 `ast.walk` 整棵樹（新線函式內 import 大量存在，`mcp_facade` 約 30 處）；
     必須處理 `from <套件> import <子模組>`（如 `from services.agent.tools import action as action_tools`、
     `from services import usage_metering as um`），先試 `<模組>.<名字>` 是否為模組再當符號。
   - **自我測試（正對照）**：檢查器內建「植入一條假的新線→舊線邊」自測，
     自測不紅就整條判 FAIL（比照不變量 34 的「自我測試未過 ⇒ 其 PASS 不可信」）。
   - 清單以檔案凍結、漂移即紅；新增舊線模組要顯式加清單。
   - **檢查器同時吐 §0 的三個數字**（各桶模組數與行數），Plan 與 MAP 引用它的輸出（F7）。

5. **⛔ 射程聲明（F4，本片最重要的一條）**：不變量 35 **只覆蓋 import 邊**。
   檢查器 docstring 與 `.claude/MAP.md#legacy-rest-chat` 都要明文寫死兩句：
   **(a) 它不覆蓋 `app.state` 注入的執行期耦合；(b) 它綠不構成「該模組可安全刪除」的授權。**

6. **執行期耦合帳（F4-a／新第四桶）**：三分法之外開第四類「**靠注入共用**」，
   首筆登記 `services/conversational_engine.py`——新線每一回合的會話狀態讀寫都經過它：
   `services/agent/state_store.py` 的 `load`／`start`／`save`／`close` 轉呼
   `ConversationalEngine.get_state`／`_start`／`_save`／`_close`，引擎實例由
   `mcp_facade._open_state_store` 經 `_app_state(deps, "conversational_engine")` 從 `app.state` 取得；
   REST 側由 `routers/agent_entry.py` 的 `EngineStateStore` 取得。**import 圖上完全看不到這條邊。**
   ⛔ `conversational_engine` 不得進舊線獨有清單。

**非範圍**：⛔ 不改任何舊線程式邏輯、⛔ 不刪任何檔、⛔ 不動測試斷言。

**驗收**
- `scripts/run-tests.sh unit tests/unit/agent tests/unit/audit` ＝ 2411 passed（基準同 R3 實測值）。
- `make audit` OVERALL PASS，且不變量 35 出現在輸出、判 PASS。
- **正對照（F4-c④：要植在真的進入點可達處，兩條都要跑）**：
  ① 暫時在 `services/agent/runtime.py` 加 `from services.sop_orchestrator import SOPOrchestrator`；
  ② 暫時在 `routers/agent_entry.py` 加同一行。
  兩條都必須讓不變量 35 FAIL 並印出該邊；還原後回綠。⛔ 少跑任一條，S1 不得收案。
- golden 28 條逐位相同（`tests/fixtures/agent/pipeline_golden.json`）。

**回滾**：`git revert` 單一 commit；無資料面副作用。

---

## 2. S2｜共用詞彙歸位（行為不變）

**成果**：新線不再從名字說謊的模組取核心詞彙；跨套件的私有名 import 消失。

### 2.1 搬（Group A：轉人與敏感詞彙）

來源 `services/presales_gate.py`（357 行，混住兩類東西）。**搬走**下列 **7** 個符號到
新模組 `services/handoff_contract.py`（名稱待 plan-verifier 挑戰）：

`FactClass`、`SENSITIVE`、`HANDOFF_WORDS`、`HandoffReason`、`Handoff`、`parse_fact_class`、
`scan_handoff_mentions`

**⛔ 三支 `build_*` 不搬（F2，第 1 稿誤劃）**：`build_handoff`、`build_llm_mention_handoff`、
`build_partial_handoff` 在 `services/agent/**` **零 import**，只出現在散文裡，而且是**刻意迴避**的：
`services/agent/tools/handoff.py` 檔頭寫「⛔ 不呼叫 `presales_gate.build_handoff`：那支由
`fact_class` 的敏感性…會把模型講的原因悄悄改寫成另一個原因」。
`build_handoff` 是全 repo 唯一把 `fact_class ∈ SENSITIVE` 推導成 `sensitive_no_grounding` 的地方；
搬進存活線的正門口，等於讓日後有人重新引入一個被設計否決的改寫。它隨舊鏈生死。
（唯一牽連：`tests/unit/agent/test_session_confirm_tools_req.py` 仍 import 它，測試檔照舊路徑不動。）

**留在原地**（確為售前限定或刻意迴避，隨舊鏈生死）：`build_handoff`、`build_llm_mention_handoff`、
`build_partial_handoff`、`extractive_enabled`、`presales_threshold`、
`analyze_ask`、`ask_is_answering`、`looks_like_question`、`split_declaratives`、
`strip_declarative_clauses`、`is_multi_item_question`、`IDENTITY_REASK_PATTERNS`、`reask_hits`
及其詞表常數。

新線消費端 6 檔改 import：`turn_context.py`、`exit_gates.py`、`verifier.py`、`runtime.py`、
`tools/handoff.py`、`agent_rules.py`。
舊位置 `presales_gate.py` **逐名 re-export**（`from services.handoff_contract import FactClass, SENSITIVE, …`，
並保留既有 `__all__` 逐名列出）。⛔ **不得用 `from … import *`**（F8：與「明列」互斥，
且 §1 的靜態閉包檢查器碰上 wildcard 最沒轍）。
舊線消費端一字不改——**集合定義寫死**（F7）：產品碼 13 處（`services/conversational_engine.py` ×10、
`routers/chat.py` ×2、`services/llm_answer_optimizer.py` ×1），測試與 `tools/` 另計。

### 2.2 搬（Group C：確認卡與表單常數）

來源 `services/conversational_engine.py`：`CONVERSATIONAL_FORM_ID`、`_QR_SUBMIT`、`_QR_EDIT`、
`_QR_CANCEL`、`_DEFAULT_QR_LABELS`。**這五個是底線開頭的私有名被跨套件 import**
（`services/agent/tools/confirm.py:85-88`、`tools/session.py:50`），是真的味道。
搬到 `services/form_contract.py`，去底線改公開名，兩邊 import 改指新家、舊位置 re-export。

**順帶修一個漂移風險（F3，處置由「改 import」改為「刪除」）**：`routers/agent_entry.py` 自己寫了
`CONVERSATIONAL_FORM_ID = "conversational"`，但該檔**零使用點**，也沒有任何模組從它 import。
改成 import 等於替一個目前只依賴 `services.agent.identity` 的 router 憑空新增依賴邊。
⇒ **直接刪掉那一行**。執行者先跑
`git log -S'CONVERSATIONAL_FORM_ID' --oneline -- rag-orchestrator/routers/agent_entry.py rag-orchestrator/services/conversational_engine.py`
確認歷史是否曾分歧，結果記進 commit message。

**同步命名（F1 附帶）**：`services/agent/verifier.py` 檔頭寫「只 import `presales_gate`／`conversational_config`」，
S2 後這句字面上為假；`.kiro/specs/agentic-mcp-orchestration/design.md` 的紅線清單也以
`services/presales_gate.py:SENSITIVE` 表述。兩處都要同步改，否則本 Plan 消滅一個「命名說謊」又造一個。

### 2.3 不搬，且寫下理由

| 模組 | 為何不搬 |
|---|---|
| `services/conversational_config.py` | 名副其實（兩線共用的對話組態），27 處非 agent 引用；改名收益低於風險 |
| `services/decision_layer.py` | 不變量 8 釘住「門檻唯一讀值點」，搬動要同步改不變量；名稱不誤導 |
| `services/vendor_knowledge_retriever_v2.py` | 不變量 29 釘住「可見性謂詞單一來源」；`_v2` 命名確實不佳，列 S3 一併處理 |

**⚠️ S3 的前置（F5 前瞻 P2，本 Plan 只登記不處理）**：不變量 29 對**找不到的 target 是靜默略過**
（`scripts/audit/checks/agent_boundary.py`：「尚未建立，略過」／「找不到此函式，略過」，只要 `checked > 0` 仍回 True）。
S3 若更名 `vendor_knowledge_retriever_v2.py`，隔離謂詞的唯一來源不變量會**綠但瞎**。
⇒ S3 更名的前置是**先讓不變量 29 對缺失 target 大聲失敗**。

**S2 收尾必做（F4-c⑤）**：S2 拆掉 `services/agent/tools/confirm.py`／`session.py` 對
`conversational_engine` 的兩條 import 邊之後，S1 凍結的那張圖就漂了——
`conversational_engine` 會從「共用」掉進「舊線獨有」桶。**必須顯式更新凍結清單，
並把它記進 §1 第 6 點的「靠注入共用」第四桶**，⛔ 不得讓它被貼上「新工作不得擴充」的檔頭。

### 驗收
- `scripts/run-tests.sh unit tests/unit/agent tests/unit/audit` ＝ 2411 passed；`unit tests/unit/api` ＝ 318 passed。
- golden 28 條**逐位相同**（本片主驗收：純搬家，任何位元差異即為缺陷）。
- `make audit` OVERALL PASS，不變量 8／29／35 皆綠。
- `grep -rn "from services.presales_gate\|from services.conversational_engine" rag-orchestrator/services/agent`
  ＝ 0 命中；**正對照**：同一支 grep 對 `services/conversational_config` 仍應有命中（證明 grep 沒壞）。
- 舊線消費端一字未改：`git diff --stat` 不得出現 `routers/chat.py`、`services/conversational_engine.py`
  的**邏輯行**變更（只准新增 re-export 與移除被搬走的定義）。

**回滾**：`git revert`；re-export 層保證即使 revert 順序顛倒也不會 ImportError。

---

## 3. 擁有權與派工

| 片 | 執行者 | 工作樹 | 前置 |
|---|---|---|---|
| S1 | `executor` | worktree A | 無 |
| S2 | `executor` | worktree B | **S1 先併回**（S2 要靠不變量 35 證明自己沒新增違規邊） |

⛔ 兩片不得並行同一檔；S1 只加檔頭與新檔，S2 動 import。
⛔ 派工 brief 必含：不得 `git stash`；不得讀 `.env`；不得 push。

---

## 4. 停止門檻

- golden 出現任何位元差異且 30 分鐘內無法歸因為「搬家以外的行為改變」⇒ 停下交業主。
- 不變量 35 的自我測試（正對照）跑不出紅 ⇒ 檢查器本身失效，該片不得收案。
- S2 若發現某符號同時被兩線以**不同語義**使用 ⇒ 停下，這是設計問題不是搬家問題。

---

## 5. 交業主裁決（S3 的前置，⛔ 本 Plan 不自行選邊）

砍舊鏈會推翻兩條已核可的文件內容。依 CLAUDE.md 事實紀律第 4 條，列出反證、不選邊：

**D-A｜`spec.json` 的遷移策略寫「M3 prospect 切換、**舊鏈可回切**」。**
砍掉舊鏈＝放棄回切能力。要砍，需業主明示放棄，並在 `agentic-mcp-orchestration` 加一個
里程碑（暫稱 M6 舊鏈退役）與 `DECISIONS.md` 一條。

**D-B｜`roadmap.md` 寫「呼叫方走 `POST /rag-api/v1/message`＋`trigger_facet_key`，⛔ 不走 `/mcp`」**
（理由：母 design 1.4「jgb2／LINE 走 REST，MCP 是 server-to-server」）。
但實際交付給 line-bot 的契約走的是 `/mcp` 的 `agent.turn`。**這句 spec 與現況已不符**，
砍 REST 之前要先改對，否則等於照著一份說反話的文件動刀。

**D-C｜`/api/v1/message` 不是純舊線**：`routers/chat.py` 在該端點內分流到
`agent_entry.handle_agent_entry`（新線的 REST 入口，目前睡著——`AGENT_AUDIENCES` 預設空），
`app.py` 的計量中介層也以該路徑字串判斷是否計量。砍之前要決定這條 REST 入口搬走還是一起砍。

**D-C 補（F6，計量的三個具體形狀）**：
1. **漏計**：`usage_metering_middleware` 用的是**字串等值**不是前綴（`path == "/api/v1/message"`）。
   S3 若把 agent 的 REST 入口搬到任何別的路徑或加版號，計量會**靜默停止**；
   查無任何測試或不變量把這個字面量釘住（不變量 5 只抓得到全面停擺）。
2. **雙計／歸錯屬**：`services/usage_metering.py` 的 `begin` 無條件 `_ctx.set(...)`，**無巢狀防護**。
   今天不可達（`/mcp` 在 `begin` 之前就 return）；S3 一旦合併入口，第二次 `begin()` 會覆蓋第一個 context
   ⇒ 第一個永不 finalize（漏一列），外層 `finalize()` 去結內層（歸錯屬）。
   ⇒ 合併入口前必須先給 `begin()` 加**大聲失敗**的重入防護。
3. **計費單位不同**（最根本）：業主定案「額度按訊息計」。一則訊息在 REST 是 **1 列**，
   在 MCP 是 **N 列**（N＝工具呼叫數，不變量 31）。砍 REST 不只是搬路徑，是換計費單位。
   ⇒ S3 的前置裁決要包含「計費單位」。

**D-E｜S3 的意義被一條看不見的依賴改寫（security-reviewer F4，我已自行重驗）**：
**新線每一回合的會話狀態讀寫，都跑在舊鏈引擎上。**
`services/agent/state_store.py` 的 `load`／`start`／`save`／`close` 轉呼
`ConversationalEngine.get_state`／`_start`／`_save`／`_close`（同一張 `form_sessions`、同一組 SQL）；
引擎實例由 `mcp_facade._open_state_store` 經 `_app_state(deps, "conversational_engine")` 從
`app.state` 取得。**這條邊在 import 圖上完全看不到**（依賴注入＋鴨子型別）。

⇒ **`conversational_engine.py` 不能砍，也不能標成舊線**。S3 不是「刪掉舊鏈」這麼單純，
它至少要拆成兩件：**(a) 先把會話狀態持久化從 `ConversationalEngine` 剝離成新線自有的實作**，
(b) 才談砍 `routers/chat.py` 與 SOP。(a) 動的是每一回合都在跑的路徑，風險等級與 S1／S2 完全不同，
必須獨立立案、獨立驗收。

⇒ 連帶：本 Plan §0 的「舊線獨有 36 模組」是 **import 意義下**的獨有，
⛔ 不等於「可安全刪除的 36 個」。真正可刪的集合要等 (a) 完成後重算。

**D-D｜業主 2026-09-10 已述事實**：jgb2 的 `HelpAssistantController@chat` 代理到
`https://chatai.jgbsmart.com/rag-api/v1/message`，但該功能仍在測試期
（佐證：`config/services.php` 的 `ASSISTANT_CHAT_TEST_ALLOW_SOCIAL_IDS`「測試期暫用白名單」）。
⇒ 產品面不再是阻擋，剩下的是 D-A／D-B／D-C 三條文件與技術裁決。

---

## 6. 本 Plan 未做的量測

- 舊線在線上的真實流量（`/api/v1/message` 近 14 天）未查——需業主跑線上 SQL。
  S1／S2 不依賴此數字；S3 依賴。

---

## 7. security-reviewer 處置表（2026-09-10，第 1 稿 → 第 2 稿）

| 編號 | 優先級 | 內容 | 處置 | 落點 |
|---|---|---|---|---|
| F1 | P4＋P3 | 拒答政策序列化面無發現；但 `verifier.py` docstring 與 design 紅線清單會變成假話 | **FIX** | §2.2 末段 |
| F2 | P2 | 三支 `build_*` 被誤劃為共用（新線零 import、且刻意迴避） | **FIX**（搬 10 改搬 7） | §2.1 |
| F3 | P3 | `agent_entry` 的重複常數是死常數，改 import 反而新增依賴邊 | **FIX**（改為刪除） | §2.2 |
| F4 | **P1** | 靜態閉包看不見 `app.state` 注入；S2 會把每回合都在跑的引擎推進舊線桶 | **FIX**（進入點＋解析形狀＋射程聲明＋第四桶＋清單更新時序） | §1.4–1.6、§2.3、§5 D-E |
| F5 | P4＋P2 前瞻 | 不變量 8／29／27–31 不被 S1／S2 弱化；但不變量 29 對缺失 target 靜默略過 | 本體無需動；前瞻 **DEFER 並登記** | §2.3 |
| F6 | P2（S3） | 計量漏計／雙計／計費單位三形狀 | **DEFER 到 S3，登記** | §5 D-C 補 |
| F7 | P3 | §0 數字不可重跑（腳本在 scratchpad） | **FIX**（檢查器進版控並吐數字） | §1.4 |
| F8 | P3 | re-export 寫法自相矛盾（`import *` vs 明列） | **FIX**（逐名，⛔ 不用 wildcard） | §2.1 |

**我自行重驗過的三條**（⛔ 不憑代理單一說法）：F4-a 的 `state_store.py` 轉呼四個引擎方法與
`mcp_facade._open_state_store` 取 `app.state` 屬實；F2 的三支 `build_*` 在 `services/agent/**`
確為零 import、只在散文（正對照：`FactClass` 同一支 grep 命中三檔以上）；
F3 的 `CONVERSATIONAL_FORM_ID` 在 `agent_entry.py` 確為零使用點。
