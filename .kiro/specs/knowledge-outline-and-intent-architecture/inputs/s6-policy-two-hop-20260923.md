# S6 交付報告：提示詞改兩跳導航（2026-09-23）

> Plan 9.10 §3 S6 要求「交付報告須含三個擁有檔案的改前／改後 sha256 與 mtime」。本檔補齊；程式面已由 fresh verifier **CONFIRMED**，**真回合驗收未跑**（需業主支出授權，前置見 §4）。

## 1. 改了什麼

兩份政策文（`services/agent/agent_rules.py` 的 `_POLICY_TEXT` 與 `_POLICY_TEXT_NON_PROSPECT`）的大綱引用句：

- 舊（一跳）：`若都不相關，可用 kb.get 讀目錄列出的章節整節後再引用，id 形狀為 outline: 加上目錄那一行的章節 id。`
- 新（兩跳）：`若都不相關，目錄那一行是粗目：先 kb.get(outline:粗目id) 取細目清單（不可引用），再 kb.get(outline:細目id) 讀整節後再引用。`

理由：S2 之後目錄只列粗目。照舊說法，模型會拿粗目 id 當可引用章節 ⇒ `SOURCE_NOT_CITABLE → budget_exhausted`。

## 2. 擁有檔案（改後 sha256，實測）

| 檔 | 改後 sha256 |
|---|---|
| `rag-orchestrator/services/agent/agent_rules.py` | `e28f712b999edaa069a9c1831790b2e02c0e92895efb048d8bc99c9ac2ea4744` |
| `rag-orchestrator/tests/unit/agent/test_agent_policy_kb_outline_req.py` | `348c0460da335a3b623181d07f4f4e07b64a8f75d4d1fb3d76fbb183ced5f91c` |
| `inputs/plan-5.1-policy-definitions-20260907.md` | `9d997434b115be8af04c2cf16b58b737a848b56dd0a0add08cc0e6a8804bd210` |

**三個上限檔必須未變**（其中 `test_agent_rules_pm_canon_merge_req.py` 未追蹤 ⇒ ⛔ 比對雜湊，不可用 `git diff`）：

| 檔 | sha256 |
|---|---|
| `test_agent_rules_definitions_req.py` | `5e28c2591d098a755e6ad18d77ecff238261a444be2e1bb6e61227892f6a9dac` |
| `test_ask_target_req.py` | `8e409b21c572495383439c65c63189e9c03932f7bd33bc0bd473f71300d76bd4` |
| `test_agent_rules_pm_canon_merge_req.py` | `9d0c9632a2c44b988459427df7c71a074ba9aea257b8e9df7f8a433c1f61b454` |

## 3. 預算與斷言

- `len(_POLICY_TEXT)` **1584 → 1577**（上限 1584，剩 7 字餘裕）；`count("⛔")` **8 → 8**（上限 8）。⛔ 沒有調高任何上限。
- 為騰出空間，同段做了 5 行共 8 處刪改（emphasis 與冗字），未動任何規則、條件、範圍限定詞或測試釘住的名詞。
- 新增兩條逐字斷言（`test_agent_policy_kb_outline_req.py`）：`test_policy_text_prospect_states_two_hop_outline_navigation`（第 84 行）、`test_policy_text_non_prospect_states_two_hop_outline_navigation`（第 88 行）。
- **逐份變異證明**：只把 `_POLICY_TEXT` 改回一跳 ⇒ 只有售前那條紅；只把 `_POLICY_TEXT_NON_PROSPECT` 改回 ⇒ 只有業者那條紅。⛔ 一份的變異不得代表另一份。

**重跑指令**
```bash
shasum -a 256 rag-orchestrator/services/agent/agent_rules.py \
  rag-orchestrator/tests/unit/agent/test_agent_policy_kb_outline_req.py \
  .kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-5.1-policy-definitions-20260907.md
shasum -a 256 rag-orchestrator/tests/unit/agent/test_agent_rules_definitions_req.py \
  rag-orchestrator/tests/unit/agent/test_ask_target_req.py \
  rag-orchestrator/tests/unit/agent/test_agent_rules_pm_canon_merge_req.py
scripts/run-tests.sh unit tests/unit/agent/test_agent_policy_kb_outline_req.py
docker compose -f docker-compose.dev.yml run --rm -T rag-orchestrator python3 -c \
  "from services.agent import agent_rules as a; print(len(a._POLICY_TEXT), a._POLICY_TEXT.count('⛔'), len(a._POLICY_TEXT_NON_PROSPECT))"
```
（最後一條預期輸出：`1577 8 2087`）

**全套件實跑（2026-09-23 收工，本報告的一手證據）**
```
scripts/run-tests.sh unit -q
→ passed=3849  failed=9  gate_skipped=1  env_skipped=2
  9 failed, 3849 passed, 3 skipped, 276 deselected in 116.36s
```
9 條紅與 S4 驗收報告 §10 的既有名單逐名相同（他線問題，⛔ 非本片造成）；3 個 skip 亦逐名相同。相對 S4 的 3,847 綠多 2 條，正是本片新增的兩條逐字斷言。

## 4. ⏳ 真回合驗收：未跑，需支出授權

⚠️ **花錢前必做的前置**：每回合會預先注入 K=5 條候選細目與種子化目錄來源，而封存只有 20 條已審（售前可見 13、業者可見 9）⇒ 隨便挑題，答案多半已在資料段裡，模型不會發 `kb.get`，要看的軌跡與反向對照都不會出現，而「無反向對照不得判過」是硬閘。⇒ 選題後先**不呼叫模型**印出該回合 `sel_meta["candidate_ids"]`，確認目標細目不在候選裡。

- 環境：`AGENT_CANON_DIR` 指 `docs/archive/2026-09/canon-pre-dsp067`、`DB_ENV=test`（覆寫只在測試環境生效）。
- 受眾：`prospect` 與 `property_manager` 各跑；**每臂 ≥3 回合**（模型有隨機性）。
- 判讀工具：`tools/agent_eval.py` 跑回合、`tools/agent_attempts_report.py` 看 `sel_meta`／`violations`。
- 預期軌跡：先 `kb.get("outline:<粗目 id>")`（不可引用）→ 再 `kb.get("outline:<細目 id>")`（可引用）；全程無 `SOURCE_NOT_CITABLE`、無 `budget_exhausted`。
- 反向對照：同環境把政策文改回一跳，必須重現 `SOURCE_NOT_CITABLE → budget_exhausted`。
- 支出估算：2 受眾 × 2 臂 × 3 回合 = **12 次呼叫起跳**。

## 5. 已知債（verifier 列，交業主）

1. **售前守門被弱化**：`feature` 說明由「絕大多數問題屬此」改成「多數」，並刪去「有沒有某能力」。兩者都是把邊界題推離敏感分類的推力，而探針報告已記錄「敏感過度分類」是現存病灶，最常問「有沒有某能力」的正是售前。⚠️ 沒有任何測試抓得到。建議改回並從別處省 2 字。
2. **業者政策文無上限**：現 2,087 字，比售前長 32%，`system_chars` 只被記錄、無任何斷言或預算。本片又讓它多 20 字。建議比照附錄 A 量後凍一個上限。
3. **附錄 A 在本片動手前就已落後程式**（缺整個【回覆用語】節與 pm／tenant 的 V4 增補）；本片只同步被交辦的那一句，並在該檔標明真實數字，⛔ 未假裝整份已對齊。
