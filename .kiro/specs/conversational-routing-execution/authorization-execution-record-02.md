# Execution record #02 —— P1f **successor candidate 凍結**

日期：2026-08-29｜前一份 `#01`（SHA `f898612`）已標記 **REFUTED_BY_A03**

```text
implementation SHA        8fb196f46a01f5122f6147c872d884acc98cf534
Level-A population digest 57413ee8a4068f73bc4e0c2c0512967e（未變）
face requirement digest   bde00b206c9c8b7d4b1328e7440d754f（未變）
gate                      **still OFF**（INSTANCE_REFERENCE_GATE 未設）
LEVEL_A_INSTANCE_GATE_SCOPE  {bill_diagnosis}（未變）
```

## 狀態分解（⛔ 不得再籠統寫「P1f 完成」）

```text
production transport   **CONFIRMED**
consumer wiring        **CONFIRMED**
policy semantics       **CONFIRMED**
end-to-end authorization  ⏸ **尚未取得**（見下方 blocker）
```

## 完整因果套件（⛔ 不以「全層 1596/0」代替；逐檔重跑）

```text
production-shape contract        test_p1g_transport_contract_req        10/10 ✅
authority-transfer death controls
  ＋ mutations ＋ gate-OFF 等價
  ＋ non-Level-A 等價             test_p1f_authority_transfer_req        23/23 ✅
tri-state 六格 matrix             test_applicability_decision_matrix_req 21/21 ✅
契約三態與不降級                   test_instance_applicability_contract_req 20/20 ✅
Face requirement population       test_face_requirement_population_req    5/5  ✅
                                                                       ────────
                                                                        79/79
不變量 1–11 全綠（含 10 的窄豁免、11 的常數間接解析與植入缺漏正對照）
```

### production-shape 正對照（**真實 retriever path**，本地 DB，⛔ 非 fixture）

```text
3503 → instance ✅   3402 → general ✅   3406 → general ✅
4640 → instance ✅   4657 → instance ✅  3519 → general ✅
且 production row **不含** generation_metadata
```

## ⚠️ 主線 blocker 已經**換人**

```text
舊 blocker：AUTHORITY_INPUT_TRANSPORT_MISSING   → 已修（fa9d74d）
新 blocker：**RETRIEVAL_SEMANTIC_MISALIGNMENT** → A03-SEMANTIC = FAIL，**仍然成立**
```

⚠️ ⛔ **不得**因為 transport 修好了，就把 A03 整體視為「舊 implementation 造成的失敗」。
Layer A 發生在 applicability consumer **之前** ⇒ 就算今天 production row 已正確帶著宣告，
`G2 15%`、`I2-explicit 30%` 這些結果**不會自動消失**。

### 這替本條線的病灶再加一層

```text
nomination ≠ authority
select=api ≠ capability equivalence
有資料流   ≠ 流到正確語義槽位
fixture 有資料 ≠ production 有資料
**authority input 有值 ≠ authority input 指的是正確 intent**
```

```text
錯的 interpretation → 正確讀取該 row truth → 正確執行 authority
                   → 對使用者**仍然是錯的 routing**
```

## 正式狀態

```text
P1f successor transport fix   ✅ implemented ＋ **successor freeze（本記錄）**
A03-AUTHORITY                 INCONCLUSIVE（⛔ 不得以 A03 重考）
A03-SEMANTIC                  **FAIL ／ CONFIRMED upstream defect**
gate authorization            ⏸ **BLOCKED_BY_RETRIEVAL_SEMANTIC_FAILURE**
3.4／gate enable／scope expansion／release   ⏸ 全部 PAUSED
```

## ⛔ 下一刀**不是** A04

```text
已有合法、burned、**事前凍結 oracle** 的 A03 證據證明至少六個 semantic unit 未達 80%
⇒ 缺陷已成立，⛔ 不需要新 holdout 再證明一次「它有問題」
若現在急著找新 corpus：
  已知 upstream semantic retrieval FAIL → 不修 → 換一批 unseen corpus 再驗 end-to-end
  ⇒ 即使 P1f conditional behavior 100%，**仍無法解除** gate authorization 的 blocker
```

⇒ 下一刀＝**retrieval semantic failure analysis**，
✅ 合法使用 A03 **burned** corpus（用途已是 failure analysis，⛔ 不再形成 validation claim）。
