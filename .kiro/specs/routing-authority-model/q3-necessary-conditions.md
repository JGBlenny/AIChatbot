# Q3：必要條件 vs 伴隨症狀（counterfactual removal test）

> 2026-08-24｜語言 zh-TW｜discovery Q3
> ⚠️ **不問「哪個 hypothesis 最像答案」**。程序固定為：

```text
Observed failure → counterfactual removal test → NECESSARY / SUPPORTED / MANIFESTATION
```

**升格為 `NECESSARY` 的唯一條件**（業主 2026-08-24 定）：

> **拿掉該條件後，已有 production／v1／holdout 的**具體 counterexample**證明系統仍會失敗。**
> 沒有 counterexample 者，只能是 `SUPPORTED REQUIREMENT` 或 `POSSIBLE DESIGN PROPERTY`。

---

## N1 — routing authority 必須取得「不等價於 retrieval similarity ＋ category」的 applicability information

**裁定：`NECESSARY`**

反事實：**若 routing 仍只用與 answer retrieval 相同的 similarity／category 資訊，系統是否仍失敗？**

```text
counterexample 1  20260731 補掛 categories → rule query 被 Face 攔截（v1 根因，實測 3 筆 REGRESSION）
counterexample 2  前案 3.4 anchor 修法：兩側僅靠 0.003–0.005 分差維持，獨立 verifier REFUTED
counterexample 3  Q2 replay：適用 0.733–0.962 vs 不適用 0.651–0.945 **大幅重疊**；
                  最佳單一門檻上限 23/31，且要達零放行須 >0.945 → 適用者只剩 1/16
```

⚠️ 本條**不指定**用什麼取得該資訊（LLM／intent classifier／Face contract／KB gate 皆未指定），
只指定**資訊必須新增**。

## N2 — applicability evidence 必須與「能否否決該 entry source」的 authority 接上

**裁定：`NECESSARY`**

反事實：**只有正確 signal、但沒有相應 veto authority，是否仍失敗？**

```text
counterexample  v1 holdout #11／#30：gate **判對了 block**，
                但落點 Face 不在 rollout scope → gate_applies_to=False → routing 仍錯
```

這是**實測**而非推論的天然反例。⚠️ 本條**不要求**所有 Face 走同一個 gate，只要求：
**對欲治理的 entry source，某個 applicability judgment 必須真的有權改變 routing outcome。**

## N3 — authority contract 必須區分 entry source，不得假設所有 entry 皆由 query semantics 決定

**裁定：`SUPPORTED REQUIREMENT`（**不是** NECESSARY）**

⚠️ **我在此下修業主草案的強度，理由是它過不了業主自己定的門檻。**

```text
證據（Q1 五路矩陣）：trigger_facet_key ← 呼叫端斷言｜vision ← 圖片｜session ← 既有狀態
                    三者的 authority **根本不看 query**
→ 若 v2 採「先判 query intent 再決定可否進 Face」，它**天生無法治理**這三路
```

**但這是 coverage gap，不是 failure counterexample**：
目前**沒有任何實測**顯示這三路正在產生 misrouting。
依 Q3 的門檻，「機制管不到」≠「已證明會失敗」，故**只能是 SUPPORTED**。

⚠️ 其核心區分仍應保留並顯眼：

```text
共同 authority contract  ≠  共同 classifier
（可以統一「授權格式／責任」，但不能假裝五種 entry source 必須共享同一種 evidence）
```

**升格條件**：出現任一路（trigger／vision／session）的實測 misrouting counterexample。

---

## MANIFESTATION／NOT NECESSARY

| 現象 | 定性 | 理由 |
|---|---|---|
| **64% abstain** | v1 lexical candidate 的 failure manifestation | 不代表任何新版都須降低某個「abstain rate」 |
| **Level A allowlist 太窄** | v1 candidate 的 implementation limitation | 不代表新版一定要有更大的 allowlist（N2 要的是「有權否決」，不是「清單更長」）|
| **KB categories 與 answer 共居** | H1 的結構風險 ＋ confirmed exposure mechanism | **尚未證明「共居本身必須被消滅」**——它是 N1 被違反的一種途徑，不是唯一途徑 |
| **gate 44% false reject** | 該 classifier 在該 calibration 下的性質 | 不是 routing architecture 的必要條件；且 direct-answer 與 routing 的 loss function 不同 |
| **LLM nondeterminism** | implementation property | 除非後續證明 routing authority **必須** deterministic，否則不得升為 architectural requirement |

⚠️ **loss function 差異（Q2 導出，此處保留）**：

```text
direct-answer false reject → 一次誠實查無（產品已裁定接受）
routing false reject       → 本應取得 instance-specific capability，卻掉回一般知識回答
∴ 同一 classifier、同一 criterion，**direct-answer 的 calibration 不得原封搬到 routing**
```

---

## H1／H2／H3 的重新定位（**研究方向，非結論**）

不互斥排名，而是各問一句：

| | 問題 | 目前答案 |
|---|---|---|
| **H1** KB Hint overloading | 是 root cause，還是違反 N1／N2 的一種 manifestation？ | **傾向後者**（它是 N1 被違反的具體途徑之一）；但未排除它同時是 root cause |
| **H2** 缺 first-class query semantics | 是必要 representation，還是滿足 N1 的一種方法？ | **SUPPORTED, but narrowly**——Q2 證明額外語義資訊存在，**未**證明 intent taxonomy 是正確承載方式 |
| **H3** Face applicability contract 不完整 | 是 authority 的核心，還是滿足 N2 的一種方法？ | 目前只能說是**滿足 N2 的一種方法**；且 Q1 顯示它管不到 5 路中的 3 路 |

**待驗研究方向（尚不可當結論）**：

> H1／H2／H3 可能**不是三個互斥 root cause**，而是分別落在
> **data provenance／semantic evidence／authority enforcement** 三個不同維度。

---

## Q3 結論

```text
NECESSARY
  N1  routing 必須取得不等價於 similarity＋category 的 applicability information
  N2  該 evidence 必須接上能真正否決該 entry source 的 authority

SUPPORTED REQUIREMENT
  N3  authority contract 須區分 entry source（共同 contract ≠ 共同 classifier）
      ——目前為 coverage gap，缺 failure counterexample

MANIFESTATION / NOT NECESSARY
  64% abstain｜Level A allowlist 窄｜KB 共居｜gate 44% FR｜LLM nondeterminism

INSUFFICIENT EVIDENCE
  L2／L3／L4／L6 何者應為 v2 主責任層（Q3 未改變此判定）
```

⚠️ **本文件不產出 solution proposal**。N1／N2 是**架構契約的下限**，不是設計方案；
滿足它們的方式有多種，選擇哪一種尚未有證據支持。
