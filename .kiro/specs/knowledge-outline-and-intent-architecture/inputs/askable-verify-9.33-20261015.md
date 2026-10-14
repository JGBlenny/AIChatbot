# Plan 9.33 S1＋S1b 驗證紀錄（2026-10-15）

> 計畫：`inputs/plan-9.33-coverage-askable-list-20261007.md` §8、§9.9～§9.13a。清單：`inputs/askable-list-9.33-20261015.json`（2,096 件）。本檔不含客服原話。

## 1. 清單組成
- 列舉 1,642 件（六批）−完整性列錯 21＋完整性新增 358 ⇒ 1,979 件（`existing` sha256 `000fcbc3270a63b2024fddabcd18cfc89dbff6172226e417bf13e1d4aa12afc6`）。
- S1b-1／2／3（片段版）新增 25＋52＋45＝122，剔跨批重複 5 ⇒ 淨增 117；S1b-4～7 依業主「A 停 S1b」不跑。
- 最終 2,096 件；機械檢查（形狀、值域、id 唯一、57／57 粗目、182 頁＋`bills.sheet` 業主排除、引文逐字命中釘住匯出或幫助中心、客戶名詞表 0）：0 錯。

## 2. 更正（純形狀／引文抄錯，事實不變）

- `A-registration#1`（S1）basis[0].quote：代理抄錯一字（改使用→改用）；原檔 app/Http/Controllers/AuthController.php 該行逐字為後者，事實不變
- `C-community-force-binding#7`（S1）presales：計畫 §2.2：售前不適用的 3 個粗目一律 presales=false；C-community-force-binding 屬不適用
- `D-entrust-contract#b1`（S1b-3）basis.quote：引文 121 字超過上限 120，截去結尾分號；截後仍逐字命中原檔，事實不變

## 3. S1b 編號對照（`#b<n>` → `#b<批>-<n>`）

- S1b-1 `E-bill-list#b1` → `E-bill-list#b1-1`
- S1b-1 `E-bill-list#b2` → `E-bill-list#b1-2`
- S1b-1 `E-bill-list#b3` → `E-bill-list#b1-3`
- S1b-1 `E-bill-list#b4` → `E-bill-list#b1-4`
- S1b-1 `E-bill-create-edit#b1` → `E-bill-create-edit#b1-1`
- S1b-1 `E-bill-create-edit#b2` → `E-bill-create-edit#b1-2`
- S1b-1 `E-bill-create-edit#b3` → `E-bill-create-edit#b1-3`
- S1b-1 `E-bill-create-edit#b4` → `E-bill-create-edit#b1-4`
- S1b-1 `C-community-list#b1` → `C-community-list#b1-1`
- S1b-1 `C-community-list#b2` → `C-community-list#b1-2`
- S1b-1 `C-community-list#b3` → `C-community-list#b1-3`
- S1b-1 `D-contract-list#b1` → `D-contract-list#b1-1`
- S1b-1 `D-move-out#b1` → `D-move-out#b1-1`
- S1b-1 `D-entrust-contract#b1` → `D-entrust-contract#b1-1`
- S1b-1 `D-entrust-contract#b2` → `D-entrust-contract#b1-2`
- S1b-1 `A-notification-settings#b1` → `A-notification-settings#b1-1`
- S1b-1 `A-notification-settings#b2` → `A-notification-settings#b1-2`
- S1b-1 `I-subscription-payment#b1` → `I-subscription-payment#b1-1`
- S1b-1 `D-contract-edit-general#b1` → `D-contract-edit-general#b1-1`
- S1b-1 `G-power-meter#b1` → `G-power-meter#b1-1`
- S1b-1 `G-power-meter#b2` → `G-power-meter#b1-2`
- S1b-1 `G-power-meter#b3` → `G-power-meter#b1-3`
- S1b-1 `E-balance-invoice#b1` → `E-balance-invoice#b1-1`
- S1b-1 `E-payment-onboarding#b1` → `E-payment-onboarding#b1-1`
- S1b-1 `B-biglandlord-sheet#b1` → `B-biglandlord-sheet#b1-1`
- S1b-2 `A-login#b1` → `A-login#b2-1`
- S1b-2 `A-signer-info#b1` → `A-signer-info#b2-1`
- S1b-2 `B-advanced-settings#b1` → `B-advanced-settings#b2-1`
- S1b-2 `B-advanced-settings#b2` → `B-advanced-settings#b2-2`
- S1b-2 `C-community-estates#b1` → `C-community-estates#b2-1`
- S1b-2 `C-community-estates#b2` → `C-community-estates#b2-2`
- S1b-2 `C-community-estates#b3` → `C-community-estates#b2-3`
- S1b-2 `C-community-estates#b4` → `C-community-estates#b2-4`
- S1b-2 `C-community-estates#b5` → `C-community-estates#b2-5`
- S1b-2 `C-community-estates#b6` → `C-community-estates#b2-6`
- S1b-2 `C-community-estates#b7` → `C-community-estates#b2-7`
- S1b-2 `C-community-estates#b8` → `C-community-estates#b2-8`
- S1b-2 `C-estate-dashboard#b1` → `C-estate-dashboard#b2-1`
- S1b-2 `C-estate-dashboard#b2` → `C-estate-dashboard#b2-2`
- S1b-2 `C-estate-dashboard#b3` → `C-estate-dashboard#b2-3`
- S1b-2 `C-estate-edit#b1` → `C-estate-edit#b2-1`
- S1b-2 `C-estate-edit#b2` → `C-estate-edit#b2-2`
- S1b-2 `C-estate-edit#b3` → `C-estate-edit#b2-3`
- S1b-2 `C-estate-list#b1` → `C-estate-list#b2-1`
- S1b-2 `C-estate-list#b2` → `C-estate-list#b2-2`
- S1b-2 `C-rent-listing#b1` → `C-rent-listing#b2-1`
- S1b-2 `C-rent-listing#b2` → `C-rent-listing#b2-2`
- S1b-2 `D-contract-edit-general#b1` → `D-contract-edit-general#b2-1`
- S1b-2 `D-contract-edit-general#b2` → `D-contract-edit-general#b2-2`
- S1b-2 `D-contract-edit-general#b3` → `D-contract-edit-general#b2-3`
- S1b-2 `D-contract-edit-general#b4` → `D-contract-edit-general#b2-4`
- S1b-2 `D-contract-edit-general#b5` → `D-contract-edit-general#b2-5`
- S1b-2 `D-contract-edit-social-housing#b1` → `D-contract-edit-social-housing#b2-1`
- S1b-2 `D-contract-list#b1` → 剔除（跨批重複，保留 S1b-1 版）
- S1b-2 `D-contract-list#b2` → `D-contract-list#b2-2`
- S1b-2 `D-contract-sign-view#b1` → `D-contract-sign-view#b2-1`
- S1b-2 `D-contract-sign-view#b2` → `D-contract-sign-view#b2-2`
- S1b-2 `D-entrust-contract#b1` → `D-entrust-contract#b2-1`
- S1b-2 `D-entrust-contract#b2` → `D-entrust-contract#b2-2`
- S1b-2 `D-entrust-contract#b3` → `D-entrust-contract#b2-3`
- S1b-2 `D-move-in#b1` → `D-move-in#b2-1`
- S1b-2 `D-move-in#b2` → `D-move-in#b2-2`
- S1b-2 `D-move-out#b1` → 剔除（跨批重複，保留 S1b-1 版）
- S1b-2 `D-renew#b1` → `D-renew#b2-1`
- S1b-2 `D-renew#b2` → `D-renew#b2-2`
- S1b-2 `E-balance-invoice#b1` → 剔除（跨批重複，保留 S1b-1 版）
- S1b-2 `E-balance-invoice#b2` → `E-balance-invoice#b2-2`
- S1b-2 `E-balance-invoice#b3` → `E-balance-invoice#b2-3`
- S1b-2 `E-bill-list#b1` → `E-bill-list#b2-1`
- S1b-2 `E-bill-list#b2` → `E-bill-list#b2-2`
- S1b-2 `E-bill-list#b3` → `E-bill-list#b2-3`
- S1b-2 `E-bill-stats#b1` → `E-bill-stats#b2-1`
- S1b-2 `G-device-page#b1` → `G-device-page#b2-1`
- S1b-2 `G-power-meter#b1` → `G-power-meter#b2-1`
- S1b-2 `G-power-meter#b2` → `G-power-meter#b2-2`
- S1b-2 `G-power-meter#b3` → 剔除（跨批重複，保留 S1b-1 版）
- S1b-2 `I-subscription-payment#b1` → 剔除（跨批重複，保留 S1b-1 版）
- S1b-3 `A-registration#b1` → `A-registration#b3-1`
- S1b-3 `A-registration#b2` → `A-registration#b3-2`
- S1b-3 `A-account-recovery#b1` → `A-account-recovery#b3-1`
- S1b-3 `A-signer-info#b1` → `A-signer-info#b3-1`
- S1b-3 `A-signer-info#b2` → `A-signer-info#b3-2`
- S1b-3 `A-member-home#b1` → `A-member-home#b3-1`
- S1b-3 `A-member-home#b2` → `A-member-home#b3-2`
- S1b-3 `B-biglandlord-list#b1` → `B-biglandlord-list#b3-1`
- S1b-3 `B-biglandlord-list#b2` → `B-biglandlord-list#b3-2`
- S1b-3 `B-biglandlord-report#b1` → `B-biglandlord-report#b3-1`
- S1b-3 `B-biglandlord-report#b2` → `B-biglandlord-report#b3-2`
- S1b-3 `C-community-estates#b1` → `C-community-estates#b3-1`
- S1b-3 `C-community-estates#b2` → `C-community-estates#b3-2`
- S1b-3 `C-community-estates#b3` → `C-community-estates#b3-3`
- S1b-3 `C-community-estates#b4` → `C-community-estates#b3-4`
- S1b-3 `C-community-list#b1` → `C-community-list#b3-1`
- S1b-3 `D-entrust-contract#b1` → `D-entrust-contract#b3-1`
- S1b-3 `E-balance-invoice#b1` → `E-balance-invoice#b3-1`
- S1b-3 `E-bill-list#b1` → `E-bill-list#b3-1`
- S1b-3 `E-virtual-account#b1` → `E-virtual-account#b3-1`
- S1b-3 `E-bill-list#b2` → `E-bill-list#b3-2`
- S1b-3 `E-bill-list#b3` → `E-bill-list#b3-3`
- S1b-3 `E-bill-list#b4` → `E-bill-list#b3-4`
- S1b-3 `E-bill-list#b5` → `E-bill-list#b3-5`
- S1b-3 `E-bill-list#b6` → `E-bill-list#b3-6`
- S1b-3 `E-bill-list#b7` → `E-bill-list#b3-7`
- S1b-3 `E-bill-list#b8` → `E-bill-list#b3-8`
- S1b-3 `E-bill-list#b9` → `E-bill-list#b3-9`
- S1b-3 `E-bill-list#b10` → `E-bill-list#b3-10`
- S1b-3 `E-bill-list#b11` → `E-bill-list#b3-11`
- S1b-3 `E-bill-list#b12` → `E-bill-list#b3-12`
- S1b-3 `E-bill-list#b13` → `E-bill-list#b3-13`
- S1b-3 `E-bill-list#b14` → `E-bill-list#b3-14`
- S1b-3 `E-bill-list#b15` → `E-bill-list#b3-15`
- S1b-3 `E-bill-list#b16` → `E-bill-list#b3-16`
- S1b-3 `G-power-meter#b1` → `G-power-meter#b3-1`
- S1b-3 `E-bill-create-edit#b1` → `E-bill-create-edit#b3-1`
- S1b-3 `E-bill-create-edit#b2` → `E-bill-create-edit#b3-2`
- S1b-3 `E-bill-create-edit#b3` → `E-bill-create-edit#b3-3`
- S1b-3 `E-bill-create-edit#b4` → `E-bill-create-edit#b3-4`
- S1b-3 `E-bill-create-edit#b5` → `E-bill-create-edit#b3-5`
- S1b-3 `E-bill-create-edit#b6` → `E-bill-create-edit#b3-6`
- S1b-3 `E-bill-create-edit#b7` → `E-bill-create-edit#b3-7`
- S1b-3 `E-social-housing-report#b1` → `E-social-housing-report#b3-1`
- S1b-3 `E-social-housing-report#b2` → `E-social-housing-report#b3-2`

## 4. 完整性
- 種入（種子 20261004）補回 4／10，**未達** ≥8／10（§9.4 業主核可放寬）；收尾盲判同 4 件，0 分歧。
- 外部對照 64 格：收尾盲判 36／26／2，與主 session 分歧 12 格經業主逐項裁定（2026-10-15「照建議：9 條採盲判，第 5 條維持對到」）⇒ **對到 39／漏列 23／不屬 2**；E5／E16「漏列 ≤3」**未達**，業主 2026-10-15 核可 §9.13 時明示同意「E5／E16 未達、清單完整性未經證實」。
- 漏列 23 格（19 條事實）全數列入 S2 凍結補內容清單：

  - `p914-balance-invoice-refund`（1 格）
  - `p914-bill-archive-states`（1 格）
  - `p914-cash-account-delete`（1 格）
  - `p914-contract-additional-tenants`（3 格）
  - `p914-contract-cable-tv-fee`（1 格）
  - `p914-contract-date-start`（1 格）
  - `p914-contract-lease-scope`（1 格）
  - `p914-credit-installment`（1 格）
  - `p914-doorlock-tenant-password`（1 格）
  - `p914-duplicate-remittance`（1 格）
  - `p914-early-termination-bills`（2 格）
  - `p914-help-tenant-register`（1 格）
  - `p914-invoice-per-bill`（1 格）
  - `p914-lessee-records`（1 格）
  - `p914-newebpay-atm-expiry`（1 格）
  - `p914-real-price-registration`（2 格）
  - `p914-receipt-email`（1 格）
  - `p914-refund-bill-account`（1 格）
  - `p914-web-not-app`（1 格）

## 5. 讀取稽核與防洩漏
- 列舉、完整性、S1b 各批讀取稽核命中逐筆判定見 scratch `hit-review.md`（收尾 verifier 重核）。
- 盲判讀取稽核：`blind_audit.py` 0 命中（自測 3／3）。

## 6. E7 staging 檢查
2026-10-15 主 session staging 後實跑（計畫 §9.13a 列名清單）：

```
staged:
   .kiro/specs/knowledge-outline-and-intent-architecture/acceptance-9.33-20261007.md ✅
   .kiro/specs/knowledge-outline-and-intent-architecture/inputs/askable-list-9.33-20261015.json ✅
   .kiro/specs/knowledge-outline-and-intent-architecture/inputs/askable-verify-9.33-20261015.md ✅
   .kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.33-coverage-askable-list-20261007.md ✅
   .kiro/specs/knowledge-outline-and-intent-architecture/verification/20261015-p933-s1-closeout.json ✅
正對照 .kiro/specs/knowledge-outline-and-intent-architecture/design.md 不在清單（不得 staged）✅
E7: PASS
```



## 7. make audit（2026-10-15）

`make audit` OVERALL FAIL，失敗項逐條與本 commit 無關（業主 2026-10-15「先 commit，註明 audit 失敗來自他線 (Recommended)」）：
- 不變量 3：`services/agent/mcp_facade.py`、`services/agent/tools/jgb2.py`、`services/jgb/transport.py`、`services/jgb_system_api.py` 容器與本地不一致，`services/agent/tools/jgb2_stats.py` 本地有容器沒有——皆為站內幫手線（`.kiro/specs/agentic-mcp-orchestration/plan-assistant-11-items-20261014.md` S0／S1）未 commit、未部署的程式；業主先前指示長駐容器先不重建。
- 不變量 7：`rag-orchestrator/services/jgb/transport.py` 替身建立帳單直接寫 `final_total`——站內幫手 S0 引入，列入該線 S1 修正。
- 不變量 43（本線紀律）：✅ PASS。本 commit 只含本 spec 目錄 6 個列名產物（E7 檢查見 §6）。
