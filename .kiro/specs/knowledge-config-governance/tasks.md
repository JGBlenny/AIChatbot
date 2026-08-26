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

- [ ] 2.1 **⚡F** 把 1.3 的兩次錯誤變成測試（「修一類 bug ＝ 加一條不變量」）：
  · 合法變體不得被判違規：role-routed config（無 topic_scope／無 endpoint）→ 0 findings；
  · dynamic 端點（`api_endpoints` 有、Python registry 無）→ 0 findings；
  · 真違規必須被抓到：endpoint 兩邊都沒有 → 1 finding。
  以**注入的假資料**驗規則，不依賴當下 DB 內容（否則資料一變測試就漂）。
  _Requirements: 5.1_

- [ ] 2.2 **⚡F** 契約檔與掃描器的一致性測試：`config_contracts.yaml` 列出的每條 rule id
  必須在掃描器中有對應實作（或明確標 `not_implemented`），反之亦然。
  **防的是**：契約寫了一條漂亮的規則，但沒有人在跑它。
  _Requirements: 1.1_

## 3. `fix-config`（L1 決定性修正）

- [ ] 3.1 **🧠主** `make fix-config --dry-run`：輸出**將要執行**的變更，不寫入。
  _Requirements: 3.1_

- [ ] 3.2 **🧠主** 每一筆寫入產生對應 rollback SQL（沿用 `seed_*_rollback.sql` 慣例）。
  _Requirements: 3.2_

- [ ] 3.3 **🧠主 🔍V** autofix 範圍**只限 L1**，且逐條列出「可修」與「不可修」的理由；
  L2 需先寫得出明確規則才可自動化，寫不出來就降 L3。
  _Requirements: 3.3, 2.2_

## 4. 現存 L1 findings 的處置（**需業主裁定：這是資料變更**）

- [~] 4.1 `form:billing_inquiry_guest`／`form:maintenance_request` 的 endpoint
  （`billing_inquiry`／`maintenance_request`）已隨 legacy `billing_api` 刪除
  ⇒ 兩張表單 `is_active` 但**完成後必然失敗**。
  掃描器已抓到；**處置需業主裁定**（停用表單 vs 重新接端點），
  且執行位置是承載 production 等價資料的 DB。
  → 停用 SQL 已寫在 `conversational-routing-execution/transport-migration-inventory.md` §10。
  _Requirements: 2.1_

## 5. Skill：knowledge governance reviewer（**不寫 DB**）

- [ ] 5.1 **🧠主** Skill 讀 knowledge／persona／config，產出
  **proposed patch ＋ reason ＋ evidence**，並標明屬 L1／L2／L3。
  _Requirements: 4.1, 4.3_

- [ ] 5.2 **🧠主** Skill **SHALL NOT** 直接寫 DB：變更一律走 migration／admin action，
  且先過掃描器的機械檢查。
  ⚠️ L3 提案必須明寫「這是產品語義決定」——替某筆知識加面向標籤看起來像資料清理，
  實際是在回答「**這個 query 應該由誰擁有**」，而那正是 `routing-authority-model`
  BLOCKED 的題。
  _Requirements: 4.2, 4.3_

## 6. 併入既有稽核體系（**待決定**）

- [ ] 6.1 **🧠主** 決定 `make audit-config` 與 `make audit` 的關係：
  併入（部署前必跑）或並列（獨立節奏）。
  ⚠️ 併入前要先確定誤報率夠低——`check_invariants.sh` 的維護準則第 5 條：
  **FAIL 才擋部署，WARN 是雷達**；稽核疲勞會讓人習慣性跳過。
  _Requirements: 5.2, 5.3_

## 排序與門檻

```text
不需授權、不碰資料：2.1 → 2.2 → 3.1 → 3.2 → 3.3 → 5.1 → 5.2
需業主裁定（資料變更）：4.1
需先有低誤報率的實績：6.1
```

⚠️ 本線與 `conversational-routing-execution` 的 P2 rollout **並行但不互擋**；
P2 停在業主對「production 等價資料庫」的 A／B 裁定。
