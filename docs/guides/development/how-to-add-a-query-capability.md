# 怎麼加一個查詢能力（新 face / 新域）

**最後對碼：2026-09-12**

寫這份的原因：2026-09-12 的動作測試裡，一位只讀文件的工程師被問「加一個查案場公設
報修統計的能力要怎麼做」，他答成「加一個 face 鍵」——**那是錯的**，而且做出來
測試不會紅（形狀合法），只是永遠答不出統計。正確步驟得拼湊三份文件才組得出來。

---

## 第 0 步：先問這是哪一種

| 你要的東西 | 這是什麼 | 往哪走 |
|---|---|---|
| 同一筆資料換個講法／換組欄位（例：帳單的「條件診斷」vs「繳費金流排障」） | **新 face** | §1 |
| 全新的資料領域（例：車位 `parking`） | **新域** | §2 |
| **跨列彙總**（「這戶今年收了幾期」「這案場報修統計」） | ⛔ **現行形狀表達不出來** | §3 |
| 寫入／建單 | 走 `jgb2.action.*` ＋確認卡，不是 query | `services/agent/tools/action.py` |

---

## §1 加一個 face（同域內）

**一句話**：在該域的 `*_FACE_BUILDERS` 加一個鍵＋寫一支 builder。

1. `rag-orchestrator/services/jgb/<域>.py` 的 `*_FACE_BUILDERS` 加鍵，值是 builder 函式。
2. builder 簽名是**單列**：收一列資料、回 facts 文字。
3. 完成。`_jgb2_spec(domain, sorted(builders.keys()))` 在註冊時**現算** enum，
   `tools/list` 自動看得到——⛔ 不必改 registry、不必改 spec。

**⛔ 三個陷阱**

- **face 只選 builder，⛔ 不選資料源。** 資料源硬編在 `services/agent/tools/jgb2.py`
  的 `query_<域>` 裡。加 face 不會讓它去查別張表。
- **builder 簽名是單列** ⇒ 要多列一起算的東西，加 face 解不了（見 §3）。
- **參數列被凍死**：`_jgb2_spec` 的 properties 就是 `face`（必填 enum）／`ref`／`keyword`，
  `additionalProperties: False`。守它的測試是
  `tests/unit/agent/test_session_confirm_tools_req.py`（對真 spec 斷言）；
  ⚠️ `test_to_openai_tools_strict_req.py` 測的是**假 spec 的 strict 轉換形狀**，⛔ 不是參數列本身。
  ⛔ 想多收一個參數要先過那支測試，且只有 `repairs` 有例外
  （`JGB2_EXTRA_PROPERTIES` 多收 `estate_id`，那張表是唯一來源）。

查證：`grep -n "_FACE_BUILDERS" rag-orchestrator/services/jgb/*.py`；
`grep -n "def _jgb2_spec" rag-orchestrator/services/agent/mcp_facade.py`。

---

## §2 加一個新域

**第一步不是寫程式，是查 jgb2 有沒有這個資料源。**

1. 查 `.kiro/specs/agentic-mcp-orchestration/jgb2-source-index.md`（24 支端點逐條）。
   ⚠️ `docs/api/jgb_external_api_spec.md` 只列 14 支，⛔ 不是窮舉清單。
   沒有端點 ⇒ 這是排給 jgb2 的需求，不是本 repo 的工作。
2. 建 `services/jgb/<域>.py`：狀態常數 ＋ 決定性判斷 ＋ `<域>_FACE_BUILDERS`
   （比照 `bills.py`／`contracts.py`）。
3. 在 `services/agent/tools/jgb2.py` 加 `query_<域>`：身分閘、候選列表、
   查無回 `_no_match()`。
4. 在 `mcp_facade.build_registry` 的 `domains` tuple 加一列 `(域, BUILDERS, query_fn)`。
5. **顯式決定 `stage`**——⛔ 不要照抄。預設會讓 `tenant` 也看得到；
   `AGENT_TURN_SPEC` 沒有 tenant 鍵，但 `jgb2.query.*` 有。
6. **無物件維度的域 ⛔ 不得帶 `scope` 鍵**。
7. **同 PR 改測試**：`tests/unit/agent/test_mcp_facade_unit_req.py::test_build_registry_registers_expected_tools`
   對工具名做**集合等值**斷言（`names == {...}`），加一支必紅。

**⛔ 安全必讀**：只有 `bills`／`contracts` 有 jgb2 側的 `viewer_user_id` 範圍限制；
`repairs`／`meters`／`accounts`／`estates` 靠本地的
`services/agent/runtime.py::_enforce_tool_scope`（範圍值來自 `_scope_estate_id`
讀 `agent_state` 的 `SELECT_SCOPE_KEY`），而那個值**只有使用者點過 `select:` 之後才存在**。
查證：`grep -n "def _enforce_tool_scope\|def _scope_estate_id" rag-orchestrator/services/agent/runtime.py`。
新域落在哪一邊要先想清楚。見 `docs/architecture/SYSTEM_ARCHITECTURE.md` §3 的隔離不對稱表。

---

## §3 跨列彙總：現行形狀表達不出來

builder 簽名是單列；多列一律走 `_ok_candidates` 變成候選清單讓使用者選一列。
所以「這戶今年收了幾期」「這案場報修統計」這類**不是加 face 能解的**。

三條路，都要裁決：

- **(a) jgb2 端加統計端點**，本 repo 只做一支單列 builder 讀它 —— 最乾淨。
- **(b) 本地在 `query_<域>` 裡彙總**後餵單列 builder —— 資料源與形狀都要改，屬架構變更。
- **(c) 不做**，改成列候選讓使用者自己看 —— 零成本但答不到問題。

⛔ 不要在沒裁決前先寫 builder：寫出來能跑、測試會綠，但語意是錯的。

---

## 相關

- 全景：[`docs/architecture/SYSTEM_ARCHITECTURE.md`](../../architecture/SYSTEM_ARCHITECTURE.md) §3
- 面向責任分層：[`docs/architecture/facet-architecture.md`](../../architecture/facet-architecture.md)
- `/mcp` 契約：[`docs/api/mcp-facade.md`](../../api/mcp-facade.md)
