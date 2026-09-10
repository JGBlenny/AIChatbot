# Plan：舊鏈隔離與共用詞彙歸位（2026-09-10；草案第 1 稿）

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
   - 檢查器 `scripts/audit/agent_import_closure.py`：以 `ast` 由新線進入點做可達性，
     與檢查器內的舊線獨有清單取交集，非空即 FAIL 並印出違規邊（`來源模組 → 舊線模組`）。
   - **自我測試（正對照）**：檢查器內建一組「植入一條假的新線→舊線邊」的自測，
     自測不紅就整條判 FAIL（比照不變量 34 的 `自我測試未過 ⇒ 其 PASS 不可信` 寫法）。
   - 清單以檔案凍結、漂移即紅；新增舊線模組要顯式加清單（讓「悄悄長大」看得見）。

**非範圍**：⛔ 不改任何舊線程式邏輯、⛔ 不刪任何檔、⛔ 不動測試斷言。

**驗收**
- `scripts/run-tests.sh unit tests/unit/agent tests/unit/audit` ＝ 2411 passed（基準同 R3 實測值）。
- `make audit` OVERALL PASS，且不變量 35 出現在輸出、判 PASS。
- **正對照**：暫時在 `services/agent/runtime.py` 加一行 `from services.sop_orchestrator import SOPOrchestrator`
  ⇒ 不變量 35 必 FAIL 且印出該邊；還原後回綠。⛔ 沒跑出這條紅，S1 不得收案。
- golden 28 條逐位相同（`tests/fixtures/agent/pipeline_golden.json`）。

**回滾**：`git revert` 單一 commit；無資料面副作用。

---

## 2. S2｜共用詞彙歸位（行為不變）

**成果**：新線不再從名字說謊的模組取核心詞彙；跨套件的私有名 import 消失。

### 2.1 搬（Group A：轉人與敏感詞彙）

來源 `services/presales_gate.py`（357 行，混住兩類東西）。**搬走**下列 10 個符號到
新模組 `services/handoff_contract.py`（名稱待 plan-verifier 挑戰）：

`FactClass`、`SENSITIVE`、`HANDOFF_WORDS`、`HandoffReason`、`Handoff`、`parse_fact_class`、
`build_handoff`、`build_llm_mention_handoff`、`build_partial_handoff`、`scan_handoff_mentions`

**留在原地**（確為售前限定、隨舊鏈生死）：`extractive_enabled`、`presales_threshold`、
`analyze_ask`、`ask_is_answering`、`looks_like_question`、`split_declaratives`、
`strip_declarative_clauses`、`is_multi_item_question`、`IDENTITY_REASK_PATTERNS`、`reask_hits`
及其詞表常數。

新線消費端 6 檔改 import：`turn_context.py`、`exit_gates.py`、`verifier.py`、`runtime.py`、
`tools/handoff.py`、`agent_rules.py`。
舊位置 `presales_gate.py` 留 re-export（`from services.handoff_contract import *` 明列），
舊線 15 處 import 一字不改。

### 2.2 搬（Group C：確認卡與表單常數）

來源 `services/conversational_engine.py`：`CONVERSATIONAL_FORM_ID`、`_QR_SUBMIT`、`_QR_EDIT`、
`_QR_CANCEL`、`_DEFAULT_QR_LABELS`。**這五個是底線開頭的私有名被跨套件 import**
（`services/agent/tools/confirm.py:85-88`、`tools/session.py:50`），是真的味道。
搬到 `services/form_contract.py`，去底線改公開名，兩邊 import 改指新家、舊位置 re-export。

**順帶修一個漂移風險**：`routers/agent_entry.py:39` 自己寫了
`CONVERSATIONAL_FORM_ID = "conversational"` 字面量重複定義，改為 import 單一來源。

### 2.3 不搬，且寫下理由

| 模組 | 為何不搬 |
|---|---|
| `services/conversational_config.py` | 名副其實（兩線共用的對話組態），27 處非 agent 引用；改名收益低於風險 |
| `services/decision_layer.py` | 不變量 8 釘住「門檻唯一讀值點」，搬動要同步改不變量；名稱不誤導 |
| `services/vendor_knowledge_retriever_v2.py` | 不變量 29 釘住「可見性謂詞單一來源」；`_v2` 命名確實不佳，列 S3 一併處理 |

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

**D-C｜`/api/v1/message` 不是純舊線**：`routers/chat.py:695` 在該端點內分流到
`agent_entry.handle_agent_entry`（新線的 REST 入口，目前睡著——`AGENT_AUDIENCES` 預設空），
`app.py:406` 的計量中介層也以該路徑字串判斷是否計量。砍之前要決定這條 REST 入口搬走還是一起砍。

**D-D｜業主 2026-09-10 已述事實**：jgb2 的 `HelpAssistantController@chat` 代理到
`https://chatai.jgbsmart.com/rag-api/v1/message`，但該功能仍在測試期
（佐證：`config/services.php` 的 `ASSISTANT_CHAT_TEST_ALLOW_SOCIAL_IDS`「測試期暫用白名單」）。
⇒ 產品面不再是阻擋，剩下的是 D-A／D-B／D-C 三條文件與技術裁決。

---

## 6. 本 Plan 未做的量測

- 舊線在線上的真實流量（`/api/v1/message` 近 14 天）未查——需業主跑線上 SQL。
  S1／S2 不依賴此數字；S3 依賴。
