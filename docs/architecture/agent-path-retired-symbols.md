# agent 路徑不使用清單

> 依據 spec `agentic-mcp-orchestration` 任務 5.2（退休標記與相容文件）。對照
> `.kiro/specs/agentic-mcp-orchestration/design.md` 的「退休／保留」段（R12.1）。
> 稽核測試：`rag-orchestrator/tests/unit/agent/test_retired_symbols_req.py`
> （以 `ast` 掃描 `services/agent/**/*.py` 的 import／屬性存取，斷言以下符號不得出現）。

agent 路徑（`services/agent/**`，由 `routers/agent_entry.py` 進入的 `AgentRuntime`
迴圈）不共用以下舊鏈（`routers/chat.py` 為主的既有對話管線）符號：

| 舊鏈符號 | 舊鏈用途 | 定義位置（可 grep） | agent 路徑以什麼取代 |
| --- | --- | --- | --- |
| `_top1_relevance_gate` | 舊鏈在 rerank 之後對 top-1 知識列做相關性二次把關，決定是否納入答題 | `routers/chat.py`：`async def _top1_relevance_gate` | agent 路徑不做知識列表相關性重判；`kb.search`／`kb.get` 回傳的證據取用與引用資格改由 `services/agent/verifier.py`（引用驗證 11 拒因）與 `Provenance.citable` 決定 |
| `decide_arbitration` | 舊鏈六 case 答題仲裁（SOP／知識分數門檻與硬編碼常數 0.15／0.55／0.6） | `services/decision_layer.py`：`def decide_arbitration` | agent 路徑不跑舊鏈六 case 決策樹；工具是否可用、要不要呼叫由模型（function calling）配合 `services/agent/agent_rules.py`／`services/agent/mcp_facade.py` 的 Registry 白名單與 scope 決定，非決定性仲裁分支 |
| `select_nominated` | 舊鏈 categories 面向提名管線（collapse → admissibility → top-N distinct responsibilities） | `services/responsibility_collapse.py`：`def select_nominated`（另見 `is_nomination_admissible`、`routers/chat.py:_nominate_face_candidates`） | agent 路徑不做面向候選提名；`kb.search` 直接回傳 `retrieve()` 現況的檢索結果列，工具選擇/知識取用交給模型與 Registry，不經過舊鏈面向提名/collapse 步驟 |

## `instance_applicability` / `retrieval_representation` 欄位

> 依據：`.kiro/specs/agentic-mcp-orchestration/design.md` 第 399 行：
> 「`kb.search` 照 `retrieve()` 現況（含 reranker 與 `retrieval_representation.scoring_surface`）；
> agent 自身不讀 `instance_applicability`／`retrieval_representation` 欄位；除役另案，
> 不變量 10／12／17 不動。」

- **`instance_applicability`**：消費者已退休（舊鏈面向提名/仲裁不再是 agent 路徑的消費者），
  待除役——除役工作另案 `retrieval-metadata-retire`（見
  `.kiro/specs/agentic-mcp-orchestration/roadmap.md` 「後」列）。agent 路徑本身
  **不讀**這個欄位，因此本任務不動它，也不代替另案宣告除役已完成。
- **`retrieval_representation`**：agent 路徑透過 `kb.search` 間接吃到 `retrieve()`
  既有輸出（含 `scoring_surface` 排序），但 agent 自身不讀這個欄位——只留 D3
  provenance 紀律的註記：任何往模型呈現的證據仍須經 `Provenance` 的 `citable`／
  `source_ids` 規則把關（見 design.md 第 234、402 行「保留分類永不當答案回傳」），
  不因走 agent 路徑而放寬。不變量 10／12／17（`docs/` 對應稽核體系）維持不動。

## 查證指令

```bash
grep -n "async def _top1_relevance_gate" rag-orchestrator/routers/chat.py
grep -n "def decide_arbitration" rag-orchestrator/services/decision_layer.py
grep -n "def select_nominated" rag-orchestrator/services/responsibility_collapse.py
grep -rn "_top1_relevance_gate\|decide_arbitration\|select_nominated" rag-orchestrator/services/agent/
# 應無輸出（agent 路徑不引用舊鏈符號）
```
