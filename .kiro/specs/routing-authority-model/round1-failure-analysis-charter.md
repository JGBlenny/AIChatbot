# Round 1 failure analysis：憲章（**凍結於分析開始之前**）

> 2026-08-24｜語言 zh-TW｜對象：Experiment A 的 17 筆 false reject（`2b22835`）
> ⚠️ **目的不是修 member，而是回答「Round 1 到底反證了哪一層」。**

## 尚不得寫成結論的那句話

「85% 行為重合 → evaluator 主導」**言過其實**。目前正確表述：

> **shared evaluator dominance 是 strongly supported hypothesis；
> 尚未排除 shared decision semantics、source specification 不足，
> 或 prompt／output contract 本身共同誘發保守判定。**

## 四個假說（互斥度不必完美）

| | 假說 | 最有力證據形態 | 若成立則反證的是 |
|---|---|---|---|
| **F1** | evaluator／calibration dominance | source 明確支持 applicable ＋ query 明確符合 ＋ **reasoning 仍以「不夠確定／寧可拒絕」為由 reject** | evaluator／calibration |
| **F2** | provenance source 資訊不足 | D1 demand model 是否足以分「某一筆操作問題 vs 通則操作問題」；D3 contract 是否描述「已發出帳單能否修改／某張刪不掉／某張重發」這些 boundary | **member source specification**（非 evaluator）|
| **F3** | shared decision contract 把兩個 provenance 壓平 | 不同 source 都被迫轉譯成同一個 applicable／not 判準 → **provenance 差異在 decision interface 前就被消掉** | 目前的 evaluation abstraction **不能保留 provenance-specific information** |
| **F4** | ground-truth／axis tension | seed-based 產品 applicability = applicable，但 D1 的「instance-specific」**不足以推出**該 Face applicable（`instance-specific ≠ 自動屬於某個 fixed Face`）| **D1 需求模型少了一個 responsibility dimension**（非 label 錯）|

## 分析對象：**不只看 17 筆錯誤**

```text
17 false rejects  ＋  一小組 matched true accepts
```

⚠️ 只看錯誤必然「每一筆都能找到一個失敗理由」。有鑑別力的問法是：

> **同一 member 為什麼接受 A，卻拒絕語義結構非常接近的 B？**

優先找：`same Face ＋ same semantic operation ＋ similar wording structure ＋ 一筆 TP／一筆 FN`。

## Ablation 的法律地位（**寫死**）

cohort 已 **burned-for-member-improvement**。允許：改 prompt／移除 precision-first wording／
增補 source field／改 output rule／換 evaluator，並在這 29 pairs 上重跑作 **causal diagnosis**。

```text
✅ 可寫：diagnostic ablation supports F1／F2／F3／F4
❌ 不得寫：D1-member-2 PASS
❌ 不得以 ablation 結果更新 family disposition
```

新版 member 要重新證明，必須：**new member freeze → new unseen challenge cohort
→ new blind labels → A／B**。

## 停止條件（**不追求解釋到 100%**）

得到下列任一即停止：

```text
A. 足夠證據支持 evaluator／calibration 主導
B. 足夠證據支持 source information 不足
C. 足夠證據支持 shared abstraction 抹平 provenance
D. 多因並存、無法進一步分離 → INSUFFICIENT_EVIDENCE
```

**後續方向的預先綁定**（避免看到結果再選）：

```text
A 或 C → 下一輪**不再做**「文本 ＋ generic evaluator」形態
B      → 仍可留在 D1／D3 family，只換 information representation，**不換 family**
D      → **不得**靠直覺再造 member，先補可分離證據
```

## 為何現在不選 (c) 收掉 discovery

Round 1 足以淘汰「routing-owned／Face-owned semantic text ＋ 同一 generic evaluator」**這兩個 concrete member**，
並對該 **member shape** 給出強烈負面訊號；但**不足以**重排 D1／D3 family，更不足以收掉 discovery。
現在關案會停在「知道兩個 member 死了，但不知道應避免什麼」的位置。
