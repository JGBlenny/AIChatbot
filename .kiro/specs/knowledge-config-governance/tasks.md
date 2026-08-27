# 任務：knowledge-config-governance

> 2026-08-26｜語言 zh-TW
> ⚠️ **這是本線的唯一施工帳本**。教訓來自 conversational-routing-execution：
> 該線的 `tasks.approved` 長期為 false，於是「現在能做、看起來有價值」的工作可以隨時插隊，
> 最後主線被 discovery／fidelity 工作擠到後面。本檔一開始就要求核准。
>
> 標記：`[x]` 完成｜`[~]` 實作完成但待裁定／待授權｜`[ ]` 未開始

## 1. 契約與掃描（**已完成**）

- [x] 1.1 machine-readable 契約 registry：`rag-orchestrator/database/config_contracts.yaml`
  12 條規則，分 L1／L2／L3；支援**條件式**（role-routed 的 presales 無 topic_scope／
  無 endpoint 屬合法變體，不得判錯）。
  _Requirements: 1.1, 1.2_

- [x] 1.2 全庫掃描器：`rag-orchestrator/tools/audit_config.py` ＋ `make audit-config`
  唯讀、不依賴應用程式啟動；依 L1／L2／L3 分段；**L3 不進 FAIL**。
  _Requirements: 2.1, 2.2, 2.3_

- [x] 1.3 兩條規則的自我修正（**寫規則當下就被資料打臉，逐條記錄**）
  · C9 初版立在 `trigger_facet_key`——那是 **request 參數**不是欄位 → 改為
    `knowledge_base.api_config->>'endpoint'`；
  · C10 初版只讀 Python registry → **10 筆裡 8 筆誤報**（dynamic 端點在 `api_endpoints` 表），
    改為 `registry ∪ api_endpoints`。依 R5.1，誤報是缺陷。
  _Requirements: 5.1_

## 2. 掃描器自身的回歸（**下一步，零授權**）

- [x] 2.1 **⚡F** 把 1.3 的兩次錯誤變成測試（「修一類 bug ＝ 加一條不變量」）：
  · 合法變體不得被判違規：role-routed config（無 topic_scope／無 endpoint）→ 0 findings；
  · dynamic 端點（`api_endpoints` 有、Python registry 無）→ 0 findings；
  · 真違規必須被抓到：endpoint 兩邊都沒有 → 1 finding。
  以**注入的假資料**驗規則，不依賴當下 DB 內容（否則資料一變測試就漂）。
  _Requirements: 5.1_

- [x] 2.2 **⚡F** 契約檔與掃描器的一致性測試：`config_contracts.yaml` 列出的每條 rule id
  必須在掃描器中有對應實作（或明確標 `not_implemented`），反之亦然。
  **防的是**：契約寫了一條漂亮的規則，但沒有人在跑它。
  → 實作 `tests/unit/_meta/test_config_audit_rules_req.py`（**15 passed**）；
    掃描器先抽出**純規則層** `scan(configs, endpoints, kb_endpoints, form_endpoints)`
    ——規則要能用注入的假資料驗，否則測試會跟著當下 DB 內容漂。
    比對實況：契約宣告 12 條、掃描器實作 10 條、L3 兩條（C11／C12）依定義不由掃描器判定，
    兩向差集皆空。
  _Requirements: 1.1_

## 3. `fix-config`（L1 決定性修正）

- [x] 3.1 **🧠主** `make fix-config --dry-run`：輸出**將要執行**的變更，不寫入。
  _Requirements: 3.1_

- [x] 3.2 **🧠主** 每一筆寫入產生對應 rollback SQL（沿用 `seed_*_rollback.sql` 慣例）。
  _Requirements: 3.2_

- [x] 3.3 **🧠主 🔍V** autofix 範圍**只限 L1**，且逐條列出「可修」與「不可修」的理由；
  L2 需先寫得出明確規則才可自動化，寫不出來就降 L3。
  → 實作 `rag-orchestrator/tools/fix_config.py` ＋ `make fix-config`（預設 dry-run，
    `APPLY=1` 才真跑並同步產生 rollback SQL）。
    **可自動修的只有 C10**（active 表單指向不存在的 endpoint → is_active=false）——
    其餘 C1／C2／C3／C4／C5／C6／C8／C9 逐條寫明**為何不可修**（都要猜語義）。
  _Requirements: 3.1, 3.2, 3.3, 2.2_

## 4. 現存 L1 findings 的處置（**需業主裁定：這是資料變更**）

- [x] 4.1 **🧠主**（**業主 2026-08-26 裁定，2026-08-27 執行**）`form:billing_inquiry_guest`／
  `form:maintenance_request` 的 endpoint 已隨 legacy `billing_api` 刪除
  ⇒ 兩張表單 `is_active` 但**完成後必然失敗**。

  **裁定的 L1 deterministic remediation ＝ 停用表單，不是猜一個 replacement endpoint**：

  ```text
  missing endpoint + active form → is_active = 0（＋對應 rollback 還原原值）
  ❌ 不得自動映射到名稱相近的 endpoint
  ❌ 不得自動重建 legacy endpoint
  ❌ 不得讓 Skill 猜應該接哪支 API
  ```

  理由：以上三者都已跨入**產品語義**。若日後要恢復功能，
  另開產品決策決定 replacement endpoint。

  **執行結果（2026-08-27）**：兩張表單 `is_active` 已改為 false；
  rollback 寫入 `database/migrations/rollback/fix_config_disable_broken_forms_rollback.sql`；
  `make audit-config` 由 2 筆 L1 → **0 筆**。
  ⚠️ 射程：這是**斷未來的地雷**，不是修正在流血的傷口——
  實查該兩張表單的 trigger intent 在 `intents` 表**皆不存在**（正對照：intents 共 54 筆），
  且 form_sessions／form_submissions 各 0 筆、無知識以 form_id 直指、無 next_form_id 串接。
  _Requirements: 2.1_

## 5. Skill：knowledge governance reviewer（**不寫 DB**）

- [x] 5.1 **🧠主** Skill 讀 knowledge／persona／config，產出
  **proposed patch ＋ reason ＋ evidence**，並標明屬 L1／L2／L3。
  _Requirements: 4.1, 4.3_

- [x] 5.2 **🧠主** Skill **SHALL NOT** 直接寫 DB：變更一律走 migration／admin action，
  且先過掃描器的機械檢查。
  ⚠️ L3 提案必須明寫「這是產品語義決定」——替某筆知識加面向標籤看起來像資料清理，
  實際是在回答「**這個 query 應該由誰擁有**」，而那正是 `routing-authority-model`
  BLOCKED 的題。
  → 實作 `.claude/skills/config-governance-review/SKILL.md`（user_invocable）。
    邊界寫在檔頭第一段：**只提案、絕不寫 DB**；變更路徑固定為
    「提案 → 人裁 → migration／admin action → `make audit-config` 機械複驗」。
    第 0 步強制先跑 `make audit-config`——**結構還壞著時談語義，結論不可信**；
    四類語義矛盾（S1 category/responsibility 脫節／S2 跨角色進場／
    S3 宣告與 delegates 不一致／S4 同義知識分屬不同面向）；
    提案格式含**必填的「反對意見」欄**（說不出自己可能錯在哪＝還沒查夠）
    與上限 10 條（超過代表沒分優先序，人會整份略過）。
  _Requirements: 4.1, 4.2, 4.3_

## 6. 併入既有稽核體系（**待決定**）

- [~] 6.1 **🧠主**（**業主 2026-08-26 裁定 DEFERRED**：只有第一次全庫結果，
  不足以證明低誤報率；先累積治理掃描實績再談）決定 `make audit-config` 與 `make audit` 的關係：
  併入（部署前必跑）或並列（獨立節奏）。
  ⚠️ 併入前要先確定誤報率夠低——`check_invariants.sh` 的維護準則第 5 條：
  **FAIL 才擋部署，WARN 是雷達**；稽核疲勞會讓人習慣性跳過。
  _Requirements: 5.2, 5.3_

## 排序與門檻（**業主 2026-08-26 核准**）

```text
APPROVED：2 → 3 → 4 → 5，中間不再逐格詢問
DEFERRED：6（併入 make audit，需先有低誤報率實績）
```

## 新增治理不變量（C9／C10 事件推導出來的）

> **治理規則本身也必須有 provenance 與 executable coverage。**

否則會出現兩種都很危險的情況：

```text
規則引用不存在的資料欄位      → 永遠不可能正確（C9：立在 request 參數上）
契約檔宣告規則但 scanner 沒實作 → 看起來受治理，實際沒人在驗
```

⚠️ 這條由 **Task 2.2**（契約檔 ↔ 掃描器一致性）封住，**不另開研究線**。

## 與主線的關係（**業主 2026-08-27 裁定：治理線優先**）

```text
先做治理線 Task 2 → 3 → 4 → 5，完成後才回 conversational-routing-execution 主線。
```

⚠️ 這是**業主指定的排程**，不是技術依賴——兩條線在技術上互不阻塞
（前一版紀錄寫「並行但不互擋」，那描述的是依賴關係，仍然成立；
排程由本裁定決定）。

主線在此期間**不推進**；其既有阻塞與本裁定無關，各自獨立：

```text
P2.5   需業主授權（真 brain 對線上資料跑完整對話流程＋付費）
P2.4   preview 上仍不可取證（jgb2 preview 版本落後，合約端點 500）——
       已改在 production 唯讀取證，六項全過
6.3    production-facing gate 仍 CLOSED（人工放行）
```

治理線本身**沒有任何外部阻塞**，未完成項目一律屬「尚未開工」。
