# R6（derived design constraint）：first-class responsibility authority

> 2026-08-24｜語言 zh-TW
> **Provenance：`63351cd`（R-e discovery，結局 C）。本條由該輪 discovery 導出，
> 並非 requirements 初始階段即已知。**

## ⚠️ 為何是獨立檔，而不是寫進 `requirements.md`

`spec.json` 的 `approvals.requirements.frozen` 明載：

```text
「requirements 已凍結；EARS 展開不得變更其強度標記」
```

故本條**不**寫入 R1–R5，也**不**改寫其任何字句或強度標記，
依業主指示建立為 **derived design constraint**。歷史 requirements 保持原樣。

---

## R6

> **對需要 facet-specific applicability 的 routing path：
> 若既有 architecture 中沒有可用、且不可由既有 runtime bindings 機械導出的
> authoritative responsibility mapping，
> 則下一個 admissible design MUST 提供一個 first-class、machine-enforced
> responsibility authority；
> 其缺席 MUST NOT 由 similarity／category、Face self-declaration，
> 或未經背書的 classifier 補位。**

### 射程限定（**不得擴寫**）

```text
✅ 成立範圍：**audited architecture**
   —— `re-mapping-discovery-frozen.md` 所凍結、且已完成的 responsibility binding surface
❌ 不得擴寫為：「整個 production 世界不存在 R-e」
```

⚠️ `MUST` 保留，但**始終帶著 audited architecture 的限定**。

### 支撐證據鏈（逐段可查）

```text
R1（已凍結）      不得僅以 similarity＋category 作為 applicability authority
inventory 1f077f6 runtime-binding 的 applicability facts **存在**（N1／N2／N3）
semantic review   那些 facts **不含** facet discrimination（R-e ❌，三者皆 prerequisite）
                  b4b2b90
R-e discovery     facts → Face 的 authoritative 箭頭在 audited surface 內
63351cd           **不存在**，且**不可機械導出**
→ 結論            R1 的下限目前**無法**由既有元件滿足
```

### 三個反例把新 authority 的邊界切乾淨（皆來自 `63351cd`）

```text
B1  Face → builder 的方向**不能**反過來冒充 facts → Face；
    且反轉命令式 builder 會把 `_DIAG_KEYWORDS` 這類**已被反證的 lexical authority 偷渡回來**
B2  similarity ＋ category → Face 這條舊路徑**徹底封死**：
    它確實是一條 facts → Face 箭頭，但不是 R1 所要求的新增 applicability information
B3  **selection mechanism 已經存在**（per-query、面向專屬的 LLM 選擇器），
    runtime 只 enforce「選到的 key 合法」
    → 缺的是 **selection correctness 的 authoritative basis**，不是選擇器本身
    → **再新增一個 intent／LLM selector 不能自動補上這個洞**
```

## B5 的法律地位：**implementation precedent，不是 solution evidence**

```text
✅ 可證明：本系統已有「Face 宣告某條件 ＋ 程式 consumer 強制執行」這種模式
           （身分參數保底：缺必要 session key → **禁打 API**）
           → declaration alone ❌ ／ declaration ＋ enforcement ✅ **做得到**
❌ 不可證明：responsibility authority **應該** Face-owned
```

⚠️ 保留為後續 R4／R2 的 feasibility precedent，**不外推**。
