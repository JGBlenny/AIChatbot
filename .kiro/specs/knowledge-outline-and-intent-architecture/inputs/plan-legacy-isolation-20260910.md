# Plan：舊鏈隔離與共用詞彙歸位（2026-09-10；第 5 稿・就緒）

**審查歷程**：第 1 稿 → security-reviewer 八條（處置見 §7）→ 第 2 稿 → plan-verifier **REVISE** 八條
（2 BLOCKER／4 MAJOR／2 MINOR，處置見 §8）→ 第 3 稿 → 收尾複審再判 **REVISE**
（1 BLOCKER／2 MAJOR／3 MINOR，處置見 §9）→ 第 4 稿 → **業主指示再審一輪**：
1 BLOCKER（兩句可收）＋3 MINOR，且**獨立推導確認 C1 修正成立、無殘留恆真路徑**（處置見 §10）→ 本稿。
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
新線閉包   := reach(新線集合)
舊線進入點 := {routers/chat.py, routers/platform_sop.py, routers/intents.py,
              routers/suggested_intents.py, services/sop_orchestrator.py}
舊線可達   := reach(舊線進入點)
第四桶     := 執行期耦合帳（見 1.3），人工維護、獨立檔
舊線獨有   := 舊線可達 − 新線集合 − 新線閉包 − 第四桶                  # S1a 產清單時用
共用       := 舊線可達 ∩ 新線閉包 − 第四桶
```

### ⛔ 不變量 35 的兩邊（BLOCKER 1 的處置，第 3 稿的致命缺陷）

第 3 稿把兩邊寫成同一次計算的兩個輸出，而右邊已顯式扣掉左邊
⇒ `新線閉包 ∩ 舊線獨有 ≡ ∅`，**恆真**。正對照在該定義下也永遠跑不出 FAIL：
植入的 `sop_orchestrator` 會被吸進左邊、同時從右邊扣掉。這與 §3.4 指出的
不變量 29「綠但瞎」是同型病灶，只是發生在我自己的檢查器上。

**修正後的定義**：

```
不變量 35 的左邊 := reach(新線集合)                        # audit 當下即時算
不變量 35 的右邊 := scripts/audit/data/legacy_only.txt      # S1a 產出、主執行緒核可、⛔ 進版控凍結
不變量 35        := 左邊 ∩ 右邊 = ∅
```

**⛔ audit 模式只比對、不改寫凍結清單。** 重算清單需另一個顯式旗標
（`--regenerate`）且必須重走 §1.5 的核可流程。⛔ 檢查器不得在 audit 路徑上自我對帳。

`reach()` 的解析規則：`ast.walk` 整棵樹（函式內 import 大量存在，`mcp_facade` 約 30 處）；
處理 `from <套件> import <子模組>`（如 `from services.agent.tools import action as action_tools`、
`from services import usage_metering as um`），先試 `<模組>.<名字>` 是否為模組再當符號。
⛔ 只走 `tree.body` 會大量低估。

### 1.2 檢查器落點與註冊

- 檔案：`scripts/audit/checks/agent_import_closure.py`（⛔ 不是 `scripts/audit/` 根，比照既有 13 支 checks）。
- 註冊進 `scripts/audit/check_invariants.sh`，比照不變量 33／34 的寫法：
  先跑 `--self-test`，自測不過即印「檢查器本身失效，其 PASS 不可信」並 FAIL。
- 四份清單落 `scripts/audit/data/`：`legacy_only.txt`、`shared.txt`、`agent_line.txt`、
  `runtime_coupled.txt`，各檔一行一模組、排序固定、**進版控**。
  ⛔ 只有 `--regenerate` 會寫這些檔；audit 路徑一律唯讀比對。

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
3. **正對照兩條**（MINOR 5 的處置：只驗進入點種子測不到遞移與解析形狀）：
   - ① `legacy_only.txt` 必須含 `services/sop_orchestrator.py`（進入點種子；驗路徑正規化沒壞）。
   - ② 必須含一個**只能經遞移邊到達、且其中一段是函式內 import 或 `from <套件> import <子模組>`**
     的已知舊線模組（執行者從 S1a 的實算輸出裡挑一個，記進 commit message）。
     **反向自測（依所選形狀對應，M-a）**：挑到**函式內 import** ⇒ 把 `reach()` 改回只走 `tree.body`
     時該模組必須消失；挑到 **`from <套件> import <子模組>`** ⇒ 關掉子模組解析時必須消失。
     ⛔ 兩者不可互套，否則會誤觸 §4 停止門檻。
   它們若沒中，就是算法或解析壞了，不是「舊線很乾淨」。
4. **清單交主執行緒核可才進 S1b。** 差異處置門檻：清單若含任何我判斷不該在裡面的模組 ⇒
   停下改算法，⛔ 不得先上檔頭再說。

5. **`make audit` OVERALL PASS**（MINOR 6 的處置：S1a 若動了共用 audit 閘門，收案就得證明閘門沒壞）。

**S1a 非範圍**：⛔ 不加任何檔頭、⛔ 不改任何既有檔。只新增檢查器與四份清單；
`check_invariants.sh` 的註冊行**留到 S1b**（S1a 併回後 audit 閘門維持原狀，⛔ 不進未定義狀態）。

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
- **檔頭覆蓋率判定（MAJOR 3 的處置：S1b 的主交付原本無人驗）**：逐列讀 `legacy_only.txt`，
  每個檔案都必須含統一檔頭字串與 `.claude/MAP.md#legacy-rest-chat` 指標，**命中數＝清單行數、缺 0**。
  **負對照**：清單外的檔案不得帶該檔頭。
  **反向自測**：刻意移除任一檔頭，該判定必須 FAIL。
- **§2 第 2／3 項的驗收（M-c，第 4 稿只驗了第 1 項）**：
  `.claude/MAP.md` 必須存在 `#legacy-rest-chat` 錨點（⛔ 錨點不在＝所有檔頭指標懸空）
  且含 §1.4 射程聲明兩句；四個 `tests/unit/{conversational,sop,forms,chat_flow}/README.md` 皆存在
  且含「維護級」字樣。

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
`_QR_CANCEL`、`_DEFAULT_QR_LABELS` 搬到 `services/form_contract.py`；**其中四個底線開頭的**
在新家改公開名（`CONVERSATIONAL_FORM_ID` 本來就是公開名，M-b 更正第 4 稿的誤述）。
搬的理由是那四個私有名正被跨套件 import（見 `services/agent/tools/confirm.py`、`tools/session.py`）。

**⛔ re-export 必須綁回原名（含底線名）**（M-b）：`conversational_engine.py` 內部有十餘處使用
`_QR_CANCEL`／`CONVERSATIONAL_FORM_ID` 等舊名，re-export 不綁回原名會 NameError。
把這件事寫死，⛔ 不靠測試炸出來。

**刪一個死常數**：`routers/agent_entry.py` 的 `CONVERSATIONAL_FORM_ID = "conversational"`
零使用點、零外部 import ⇒ **直接刪那一行**（⛔ 不是改成 import——那會替一個只依賴
`services.agent.identity` 的 router 憑空新增依賴邊）。執行者先跑
`git log -S'CONVERSATIONAL_FORM_ID' --oneline -- rag-orchestrator/routers/agent_entry.py rag-orchestrator/services/conversational_engine.py`
確認歷史是否曾分歧，結果記進 commit message。

### 3.3 引用同步集合（MAJOR 3 的處置）

**⚠️ 第 3 稿此節寫「32 處逐一改」是錯的**（MAJOR 2）：那個集合掃進了不能動的東西——
`services/agent/mcp_facade.py` 的 `_app_state(deps, "conversational_engine")` 是
**`app.state` 屬性名的字串字面量**（由 `app.py` 掛上去），改它＝執行期 AttributeError；
同檔還有 `app.state.conversational_engine` 的散文兩處；`state_store.py` 的散文指的是
`get_state`／`_save` 等**沒有被搬走**的方法。`presales_gate` 側同理有大量指向**留在原地**符號
（三支 `build_*`、`extractive_enabled` 等）的散文，它們沒有「新出處」。

**修正後的集合定義**（可重跑）：
```
grep -rn "presales_gate\|conversational_engine" rag-orchestrator/services/agent rag-orchestrator/routers/agent_entry.py
```
的命中中，**只有指涉本片實際搬走的符號者才改**——即 §3.1 的 7 個與 §3.2 的 5 個。

**⛔ 明列不動的排除項**：
- `app.state` 的鍵字串（`_app_state(deps, "conversational_engine")`）與 `app.state.conversational_engine`。
- 指涉未搬符號的散文（三支 `build_*`、`extractive_enabled`、`presales_threshold`、
  `get_state`／`_save`／`_start`／`_close` 等引擎方法）。

**必改的**：`services/agent/verifier.py` 檔頭那句「只 import `presales_gate`／`conversational_config`」
（S2 後字面為假），以及其他確實指涉那 12 個符號出處的散文。
`.kiro/specs/agentic-mcp-orchestration/design.md` 的紅線清單同步。

**驗收**：`git diff` 中 `mcp_facade.py`／`state_store.py` **不得出現任何
`"conversational_engine"` 字串字面量的變更**；golden 28 條逐位相同。

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

⚠️ 第 3 稿此節說「它會從共用掉出來 ⇒ 加進第四桶」是第 2 稿的殘留敘述（MINOR 4）：
依 §1.1 的 `共用 := 舊線可達 ∩ 新線閉包 − 第四桶`，`conversational_engine` 在 S1a 當下
就**只出現在 `runtime_coupled.txt`**，從來不在 `shared.txt` 裡。照字面執行會重複登記。

**修正後的處置**：S2 拆掉 `tools/confirm.py`／`session.py` 那兩條 import 邊之後，
`shared.txt` 不再出現該模組屬**預期**；`runtime_coupled.txt` 的首筆登記**維持不變、⛔ 不重複登記**。
**驗收**：S2 後 `runtime_coupled.txt` 中 `services/conversational_engine.py` 恰一列。
檢查器的「同一模組不得出現在兩份清單」自我一致性判定仍在，擋住把它誤加進 `legacy_only.txt`。

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
6. **散文同步的正／負對照**（R1 的處置：第 4 稿的 §3.3 有清單、無驗收，S2 可以全綠收案卻留下一句假話）：
   - **負對照**（必須 0 命中）：
     ```
     grep -rn "presales_gate\.\(FactClass\|SENSITIVE\|HANDOFF_WORDS\|HandoffReason\|Handoff\|parse_fact_class\|scan_handoff_mentions\)\|conversational_engine\._\?\(CONVERSATIONAL_FORM_ID\|QR_SUBMIT\|QR_EDIT\|QR_CANCEL\|DEFAULT_QR_LABELS\)" rag-orchestrator/services/agent rag-orchestrator/routers/agent_entry.py
     ```
   - **正對照**（必須仍有命中，證明尺沒瞎）：同一支 grep 對**未搬**符號
     `presales_gate.build_handoff`／`presales_gate.extractive_enabled` 應照樣命中。
   - 逐項確認 §3.3「必改的」清單：`services/agent/verifier.py` 檔頭那句
     「只 import `presales_gate`／`conversational_config`」與 `design.md` 紅線清單已指向新出處。
   - 已知待改的散文至少五處（執行者以上列 grep 取全集）：`verifier.py` 檔頭、
     `question_sensitivity.py` 的 `presales_gate.SENSITIVE`、`output_schema.py` 的 `presales_gate.SENSITIVE`、
     `tools/handoff.py` 的 `presales_gate.HandoffReason`／`parse_fact_class`、
     `confirm_card.py` 的 `conversational_engine._DEFAULT_QR_LABELS`。

---

## 4. 擁有權、派工、停止門檻

| 片 | 執行者 | 工作樹 | 前置 |
|---|---|---|---|
| S1a | `executor` | worktree A | 無 |
| S1b | 同 A（S1a 核可後續作） | worktree A | **S1a 清單經主執行緒核可** |
| S2 | `executor` | worktree B | **S1a＋S1b 併回** |

⛔ 派工 brief 必含：不得 `git stash`；不得讀 `.env`；不得 push；
**只准動 §3.1／§3.2 列出的 import 與 re-export、以及 §3.3 明列的散文／docstring 同步，
⛔ 不得改任何舊線邏輯**
（第 3 稿此處誤寫成「不得改 `services/agent/runtime.py` 以外的舊線邏輯」——`runtime.py` 是新線，
照字面讀反而像是允許改它裡面的邏輯，MINOR 6）。

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

## 9. 收尾複審處置表（第 3 稿 → 第 4 稿；⛔ 已達兩輪 REVISE 上限，本稿不再送審）

| 編號 | 嚴重度 | 內容 | 處置 |
|---|---|---|---|
| C1 | **BLOCKER** | 不變量 35 兩邊出自同一次計算、右邊已扣掉左邊 ⇒ **恆真**；兩條正對照在數學上跑不出 FAIL | **FIX**：§1.1 新增「不變量 35 的兩邊」——右邊改為 S1a 核可後**進版控凍結**的 `legacy_only.txt`；audit 路徑只比對、重算需 `--regenerate` 並重走核可。⚠️ 我自行複核過此推導成立，是我自己的缺陷 |
| C2 | MAJOR | §3.3「32 處逐一改」掃進 `_app_state(deps, "conversational_engine")` 字串字面量（改了＝執行期 AttributeError）與指涉未搬符號的散文 | **FIX**：§3.3 集合收斂為「只改指涉本片實際搬走的 12 個符號者」＋明列排除項＋加 diff 驗收。⚠️ 我自行重驗 `mcp_facade.py` 確有該字面量 |
| C3 | MAJOR | S1b 主交付（上檔頭）無任何驗收條款證明做完 | **FIX**：§2 驗收加檔頭覆蓋率判定（命中數＝清單行數、缺 0）＋負對照＋反向自測 |
| C4 | MINOR | §3.5 殘留第 2 稿敘述，照字面會重複登記 | **FIX**：§3.5 改寫，首筆登記維持不變 |
| C5 | MINOR | 正對照選了進入點種子，測不到遞移與解析形狀 | **FIX**：§1.5 第 3 點加第二條正對照（遞移＋函式內／子模組 import）＋反向自測 |
| C6 | MINOR | 派工約束把 `runtime.py` 寫成舊線；S1a 動 audit 閘門卻無 `make audit` 驗收 | **FIX**：§4 改寫約束；§1.5 加第 5 條驗收，註冊行改留到 S1b |

**收尾複審獨立核可、⛔ 不列缺陷的兩點**：
① §3.3 對 `routers/chat.py` 那句註解「不動」的判斷**正確**——逐名 re-export 後
`presales_gate.HandoffReason` 是模組屬性、綁到同一個 enum 物件，值域命題仍為真。
② 擁有權與工作樹可操作，S1a→S1b 同 worktree 續作、S2 另一 worktree，無並行寫入重疊；
§3.6 第 4／5 點的判準與正對照皆成立。

**現況**：六條全部 FIX 完畢，但**本稿未經任何獨立審查者蓋章**（兩輪上限已達，依規矩不自動再送）。
⇒ 交業主裁決：(a) 就這樣派工；(b) 授權再跑一輪收尾複審；(c) 縮小範圍（例如只做 S1a＋S1b、S2 另案）。

## 10. 業主指示的額外一輪處置表（第 4 稿 → 第 5 稿）

| 編號 | 嚴重度 | 內容 | 處置 |
|---|---|---|---|
| R1 | **BLOCKER** | §4 的約束改寫與 §3.3 的交付字面互斥（散文既非 import 也非 re-export ⇒ 執行者正確做法是不動它），且 §3.3 **無任何驗收**——五條驗收全是負向檢查，S2 可以全綠收案卻留下一句假話 | **FIX**（兩句）：§4 約束加「以及 §3.3 明列的散文／docstring 同步」；§3.6 加第 6 條驗收，含負對照（已搬符號 0 命中）與正對照（未搬的 `build_handoff`／`extractive_enabled` 仍命中，證明尺沒瞎） |
| M-a | MINOR | 正對照②的反向自測只覆蓋「函式內 import」一支；若執行者挑子模組 import，反向自測不會消失 ⇒ 依 §4 停止門檻**誤停** | **FIX**：反向自測改為依所選形狀對應 |
| M-b | MINOR | 第 4 稿誤述五個常數皆為底線私有名（`CONVERSATIONAL_FORM_ID` 本來就公開）；且 §3.6.5 隱含要求 re-export 綁回舊底線名，否則 `conversational_engine.py` 內部使用點 NameError | **FIX**：更正描述；把「re-export 綁回原名」從隱含改為寫死 |
| M-c | MINOR | 檔頭覆蓋率只證 §2 第 1 項；MAP 錨點與四個 README 無驗收，而所有檔頭都指向那個錨點 | **FIX**：§2 加第 2／3 項驗收 |

**本輪的獨立推導結論（⛔ 這是第 5 稿可以收案的關鍵）**：審查者自行推導 C1，確認新定義下
左邊即時算、右邊凍結，兩條正對照**真的會 FAIL**，**無殘留恆真路徑**；並實查
`services/sop_orchestrator.py` 在 `services/agent/**` 零 import（正對照組：`app.py` 有模組級 import、命中）
⇒ 推導前提成立。另確認七個待搬符號對留下的符號零依賴 ⇒ `handoff_contract` → `presales_gate`
**無循環 import**，S2 可執行。

**已知且接受的射程收窄（P4，非缺陷）**：右邊凍結 ⇒ S1a 之後才變成「舊線獨有」的模組
（例如 S2 之後的 `presales_gate.py`）不受不變量 35 覆蓋，直到 `--regenerate` 並重走核可。
這是換取可證偽性的正確取捨。

**現況**：R1 與三條 MINOR 全部 FIX 完畢。審查者對第 4 稿的原話是「補完即可交業主核可派工」，
本稿即為補完版。**⛔ 依規矩不再自動送審**（三輪已跑，第三輪由業主指示）。
