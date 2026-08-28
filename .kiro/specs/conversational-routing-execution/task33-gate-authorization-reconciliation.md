# 裁定 002 步驟 2：instance-reference gate 的 holdout 對帳

- 日期：2026-08-28｜依據：裁定 002 ②（authority 歸屬 ≠ 授權開 gate）
- 方法：容器內直接讀 `current_manifest()` 與 `assert_gate_enablable()`，**不看文件轉述**

## 對帳結果（實測）

```text
ruleset digest      = 80b2f570b10c2e20
active protocol     = 4690a258f502d98d
holdout             = status='failed'
                      ruleset ='80b2f570b10c2e20'   ← **與當前規則集相同**
                      protocol='4690a258f502d98d'   ← **與現行量尺相同**
gate_requested      = False
enablable           = False → "holdout 狀態為 'failed'——僅 'passed' 得啟用"
```

⇒ **現行 implementation 就是當初被 holdout REFUTED 的那一版。**
不是「換過規則集但沒重驗」，也不是「換過量尺」——三個 digest 全對得上。

## 當初被反證的理由（不是分數不夠，是結構性反證）

`current_manifest()` 的 docstring 記載，2026-08-24 裁決 `REFUTED`：

```text
50 筆未見語料，gate ON 與 OFF 的 routing **逐筆完全相同** → routing effect = 0/50
block 11 筆，實際抑制 Hint = **0 筆**
abstain 32/50 = 64%
```

⚠️ 依據刻意不是「準確率低於某條事後訂的門檻」——該門檻從未凍結，事後訂即違反 Req.3.5。

## 因此 3.4 的 blocker 精確化為

```text
不是「routing divergence 尚未歸因」（3.3 已歸因完畢）
而是：**deterministic eligibility authority 的現行 implementation 已被 holdout 反證，
      且尚未產生新的、通過驗證的替代品。**
```

裁定 002 ② 的分支判定結果 → 落在**第一支**：

```text
同一 implementation 已被 holdout REFUTED
  → ⛔ 不得直接 enable
  → 先修改 deterministic classifier
  → 再用**新的、未看過的** matching holdout 驗證
```

## 下一步的形狀（尚未開始，需業主決定範圍）

```text
1 修改 deterministic classifier（instance_evidence 的 POSITIVE/COUNTER patterns）
  ⚠️ 目標**不是**提高準確率數字，而是修掉「block 11 筆卻抑制 0 筆」這個
     結構性失效——判了 block 卻對 routing 毫無作用，等於 gate 不存在。
2 規則集一改，digest 就變 ⇒ 舊 holdout 自動失效（機制已內建，不需人記得）
3 以**未看過**的 matching holdout 驗新版；PASS 才寫回 manifest
4 gate authorized → 才 enable → 才跑 deterministic 3.4
```

⚠️ `SHALL NOT` 因為想讓 gate 可啟用而把 `holdout.status` 改回 `not_run` 或改成 `passed`
（該禁令已寫在 `current_manifest()` 的 docstring 內）。
`failed` 與 `not_run` 在「拒絕啟用」上等價，但語義不同：
前者代表**已驗且未通過**，後者代表**尚未驗**——改寫會抹掉那次反證。
