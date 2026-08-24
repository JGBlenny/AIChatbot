# Carrier comparison ruler（**凍結於比較之前**）

> 2026-08-24｜語言 zh-TW
> 前置：`responsibility-authority-contract.md`（**APPROVED／FROZEN**，`3e573a0`＋本輪凍結）
> 業主裁定：Contract 凍結後才凍結本量尺；**本檔只定判準，不做比較、不選 carrier。**

## 這把量尺存在的理由

Contract 凍結後，A／B／C **MUST 吃同一套**：

```text
input semantics（含 candidate proposal 的 non-evidentiary 隔離）
evidence roles（PREREQUISITE／RESPONSIBILITY_SUPPORT／EXCLUSION／OBSERVATION，且 role 為關係性）
composition／conflict algebra（C-1～C-5 ＋ 決定性評估順序）
三值語義（applicable ≠ must enter ≠ unique；not_applicable 需正向反證；unknown 不得 collapse）
```

> **因此上述四項 MUST NOT 成為比較軸。**
> 它們若還能被 carrier 改動，比的就不是 carrier，而是三種判決哲學。

---

## 五條比較軸（**唯一合法的比較內容**）

### X-1｜Authority origin：這個 authority **真正**從哪裡來？

```text
MUST 指名：誰產生這份 responsibility binding、誰擁有它、它憑什麼具 authority
MUST 區分：**宣告** vs **強制**（G1 對 class constant、inventory N6 對 grounding_scope 的同一判準）
```

**當場失敗條件（standing）**：

```text
若答案仍是「Face RULES 寫了這樣」／「後台某欄位填了」而無獨立強制端
→ **該 carrier 直接失敗**（G-d ＋ G-e）
```

### X-2｜Enrollment：新 Face 如何取得 binding？

```text
MUST 回答：新增一個 Face 時，binding 從何而來、由誰核可、何時生效
MUST 相容 M-4：尚未取得 binding 的 Face → verdict = unknown（不得因存在於 DB 就 applicable）
MUST NOT 依賴「新增 Face 時記得寫對」（RE5／R4 已 CONFIRMED 的制度失敗形態）
```

### X-3｜Machine-enforcement：怎麼被強制？

```text
MUST 指出 enforcement point 與**違反時的可觀察後果**
MUST 滿足 G-b 的 counterfactual requirement：拿掉該 authority 應觀察到**不同的 routing outcome**
❌ 只讀 verdict／寫 log 而 entry 照舊 = 形式滿足、實質違反（R2 §2.2）
```

### X-4｜Unknown fidelity：`unknown` 沿路如何保真？

```text
MUST 說明 unknown（含 conflict 標記）從 authority 傳到 final routing 的路徑上，
**在哪些點可能被折成 applicable／not_applicable**，以及靠什麼防止
❌ 任何「為了好接線所以把 unknown 當 reject」的設計 = 第四次 precision-first collapse
```

### X-5｜Correctness under Face addition：新增 Face 後 correctness 如何持續成立？

```text
MUST 回答：加入第 N+1 個 Face 之後
  - 既有 Face 的 verdict 會不會被動改變？若會，靠什麼偵測？
  - G-a（同一組 instance proof 下能區別候選 Face）是否仍成立？
  - 是否需要重新驗證全部既有 binding？（若需要 → 對 open-Face 是實務上的封閉要求）
MUST 相容 G-c：不得要求先封閉全世界 Face taxonomy
```

---

## 明確**不是**比較軸（列出以免被偷渡）

```text
✗ 哪個 carrier 比較漂亮／比較符合直覺
✗ 哪個比較好實作／改動比較小／比較快上線
✗ 哪個比較像我們原本的 D1／D3 分類
✗ 任何 Contract 已凍結的語義（見開頭四項）
```

⚠️ 實作成本**不是**本輪判準。它是 carrier 通過 X-1～X-5 **之後**才談的事。

---

## 每個 carrier 的判定格式

```text
carrier            A ／ B ／ C
X-1 authority origin        PASS ／ FAIL ／ INSUFFICIENT_EVIDENCE ＋ 證據
X-2 enrollment              同上
X-3 machine-enforcement     同上
X-4 unknown fidelity        同上
X-5 correctness under addition  同上
standing failure            是否觸發「authority 來自 Face RULES」的當場失敗
disposition        ADMISSIBLE ／ REJECTED ／ INSUFFICIENT_EVIDENCE
```

⚠️ `INSUFFICIENT_EVIDENCE` **不得**預設倒向 PASS 或 FAIL。

## 事前綁定的結局（**不看到結果再選**）

```text
結局 1  恰一個 carrier ADMISSIBLE
        → 進入該 carrier 的設計；D1／D3 的歸屬由其 authority provenance 決定
        （routing-owned→D1 ／ Face-owned but independently enforced→D3 ／
          neutral／capability-owned→D1／D3 分類可能失去重要性）

結局 2  多於一個 ADMISSIBLE
        → **不由我選**。以 X-1～X-5 的證據呈報，由業主裁定；
          若差異涉及產品取捨（如 unknown 的 recovery 代價），
          即觸發尚未裁定的 `unresolved.routing_false_reject_cost`

結局 3  **三個皆非 ADMISSIBLE**
        → 這是**允許且有價值**的結果：說明 R6 所要求的 authority
          在既有承載方式下都無法成立，需要重新界定承載形態
        ⚠️ **不得**為了避免結局 3 而放寬 X-1～X-5
```

## 輸出限制

```text
只輸出：三個 carrier × 五軸的判定 ＋ 證據 ＋ disposition ＋ 結局

❌ 不設計 schema、不寫 migration、不提實作計畫
❌ 不開 D1／D3／D4 member；D2 仍 deferred
❌ 不改已凍結的 Contract 語義（發現需要改 → 停下來提出，不得邊比邊改）
❌ 不改 family disposition
❌ 不動 production；不產測資；ruler 0.058928 仍凍結未用
```

⚠️ **最後一條特別重要**：若比較過程中發現 Contract 的某條語義擋住了所有 carrier，
**正確做法是停下來提報**，而不是回頭鬆綁 Contract——那會讓凍結失去意義。
