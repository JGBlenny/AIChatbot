# 任務 1.5：negative control 有效性稽核（逐 test ID）

> 2026-08-23｜語言 zh-TW｜_Requirements: 6.5_
> 對象：1.1（6）＋1.2（12）＋1.3（6）＋1.4（6）＝ **30 個 test ID**
> ⚠️ 先前口頭說「26 個」是加錯，實際母體為 **30**——分母錯會讓覆蓋率看起來比實際好。
> ⚠️ **逐 test ID 判失敗原因，不看 failed 總數**（業主裁示）。

## 判準

```text
A. EXPECTED SEMANTIC RED / PROVEN GREEN
   契約真的因它要攔的錯誤而失敗（或：以突變證明它會因該錯誤而失敗）
   → negative control 成立

B. SCAFFOLD RED
   ModuleNotFoundError／symbol 尚不存在
   → 只能證明 pre-implementation scaffold，尚不能證明 semantic effectiveness

C. UNEXPECTED RED/GREEN
   assertion／fixture／seam／contract 本身有問題 → 先修契約，不得進 Task 2
```

⚠️ **綠色不會自動等於有效**。一條恆綠的斷言與一條有效的斷言在報表上長得一樣。
故本稽核對每一條綠都問：**「什麼樣的錯誤會讓它變紅？」**——
答不出來就不是 A。實作方式是**突變測試**：故意把被守護的東西弄壞，看它有沒有咬。

## 方法論邊界：實作了量尺，沒有實作 candidate

為了讓 1.2 的 12 條能被語義判真，本輪實作了 `rag-orchestrator/scripts/routing/protocol_v1.py`。

```text
量尺（measurement infrastructure）  ← 本輪實作；protocol v1 凍結在前，量尺照著實作
candidate（InstanceEvidence／gate／seam 整合）  ← **未動**，仍待 1.6 erratum 後才開始
```

⚠️ 因此 **1.1 六條與 1.4 的兩條成員資格斷言必然維持 B**——
它們守的是 candidate 模組（`services.instance_reference_gate`），
而該模組正是 1.6 裁定之前**不得**開始的東西。
**這不是稽核的缺口，是順序紀律的必然結果**，於下方逐條標明。

## 突變清單（13 個，**全數被殺，0 survived**）

| ID | 突變內容 | 被哪些 test ID 殺掉 |
|---|---|---|
| M1 | 量尺：任何 `dialog` 都算 pass（**前案判定式的形狀**）| wrong_facet×5、dialog_without_facet、bilateral_rejects、bilateral_requires_both |
| M2 | 量尺：`UNDECIDED` 當成 pass | undecided_unscored |
| M3 | 量尺：bilateral 只看 RULE 側（單邊假綠）| bilateral_rejects |
| M4 | 量尺：`dialog` 但無 facet 也算 pass | dialog_without_facet、bilateral_requires_both |
| M5 | 1.3：省事修法——整列 categories 全封掉 | instance_still_enters、flag_off_unchanged |
| M6 | 1.3：竄改凍結的 v2 案例 | cases_come_from_frozen_v2 |
| M7 | 1.3：把 multi-category 換成非 Face 分類 | case_shape_is_genuinely_multi_face、cases_come_from_frozen_v2 |
| M8 | 1.4：隔離判定式恆回「無漂移」（瞎的量尺）| isolation_catches_overbroad |
| M9 | 1.4：隔離判定式恆回「有漂移」（沒有鑑別力）| flag_on_does_not_change_outside、isolation_not_flag_correct |
| M10 | 量尺：恆判 fail（恆紅）| correct_facet_is_the_only_pass、bilateral_requires_both |
| M11 | 量尺：恆判 pass（恆綠）| wrong_facet×5、dialog_without_facet、single_shot_is_failure、bilateral×2 |
| M12 | 量尺：`PROTOCOL_DIGEST` 改掉（未釘在 v1）| 全 12 條 |
| M13 | 1.4：待裁定 Face 名單與母體不符 | pending_faces_recorded_not_asserted |

⚠️ **M10／M11 成對**：只證明「恆綠會被抓」不夠——恆紅的量尺同樣測不出東西，
且會把正確實作一起擋掉。**兩個方向都要有人守**。
⚠️ **M8／M9 成對**：同理施加於隔離判定式自身。

## 逐 test ID 判定

### 1.1 `test_instance_gate_enable_invariant_req.py`（6）── 全 **B**

| test ID | 判定 | 失敗原因 |
|---|---|---|
| test_reject_when_holdout_not_run | **B** | `ModuleNotFoundError: services.instance_reference_gate` |
| test_reject_when_holdout_failed | **B** | 同上 |
| test_reject_when_passed_on_a_different_ruleset | **B** | 同上 |
| test_reject_when_passed_under_a_different_protocol | **B** | 同上 |
| test_allow_only_when_all_three_match | **B** | 同上 |
| test_rejection_is_not_downgraded_to_warning | **B** | 同上 |

> **升格條件**：candidate 模組存在後重跑，並以突變（例如把 `status=="failed"` 誤放行、
> 把三重 digest 比對改成 `result is not None`）證明各條會咬。**排在 1.6 裁定之後。**

### 1.2 `test_protocol_facet_verdict_req.py`（12）── 全 **A**

12/12 通過，且每一條**至少被一個突變殺掉**：

| test ID | 判定 | 殺它的突變 |
|---|---|---|
| test_wrong_facet_is_not_success[帳單異常] | **A** | M1、M11、M12 |
| test_wrong_facet_is_not_success[發票] | **A** | M1、M11、M12 |
| test_wrong_facet_is_not_success[滯納金] | **A** | M1、M11、M12 |
| test_wrong_facet_is_not_success[繳費金流排障] | **A** | M1、M11、M12 |
| test_wrong_facet_is_not_success[狀態判斷] | **A** | M1、M11、M12 |
| test_correct_facet_is_the_only_pass | **A** | M10、M12 |
| test_dialog_without_facet_is_never_pass | **A** | M1、M4、M11、M12 |
| test_single_shot_on_instance_is_failure | **A** | M11、M12 |
| test_bilateral_pass_rejects_run_where_instances_landed_in_wrong_facet | **A** | M1、M3、M11、M12 |
| test_bilateral_pass_requires_both_sides | **A** | M1、M4、M10、M11、M12 |
| test_expected_facet_comes_from_the_frozen_protocol | **A** | M12 |
| test_undecided_cases_are_unscored_not_pass | **A** | M2、M12 |

**業主指定的五項結案條件，逐項成立**：

```text
錯 facet            → 因 wrong facet 而 FAIL      ✓（M1／M11 反證）
single on instance  → 因 wrong route 而 FAIL      ✓（M11 反證）
UNDECIDED           → unscored（非 pass）          ✓（M2 反證）
正確 facet          → PASS                        ✓（M10 反證：恆紅會被抓）
bilateral 假綠      → 被拒絕                       ✓（M3 反證：單邊會被抓）
```

### 1.3 `test_multi_category_gate_scope_req.py`（6）── 全 **A**

| test ID | 現況 | 判定 | 依據 |
|---|---|---|---|
| rule_stays_single[diagnosis_first] | 🔴 | **A** | semantic red：實際進了 `bill_diagnosis` |
| rule_stays_single[anomaly_first] | 🔴 | **A** | semantic red：實際進了 `billing_anomaly` |
| instance_still_enters_bill_diagnosis | 🟢 | **A** | M5 殺得掉（省事修法會讓它紅）|
| flag_off_leaves_behaviour_unchanged | 🟢 | **A** | M5 殺得掉 |
| case_shape_is_genuinely_multi_face | 🟢 | **A** | M7 殺得掉 |
| cases_come_from_frozen_protocol_v2 | 🟢 | **A** | M6／M7 殺得掉 |

⚠️ 兩條紅**不是**實作缺失，是契約逼出 `open_conflict_for_task_4_1`：
Level A 白名單只涵蓋一個 Face，而 rule 側收斂成 `single` 需要 `billing_anomaly` 也被抑制。
**1.6 裁定前必然紅**，不得為求綠燈調斷言。

### 1.4 `test_level_a_scope_isolation_req.py`（6）── **A×4、B×2**

| test ID | 現況 | 判定 | 依據 |
|---|---|---|---|
| membership_is_not_bool_required_slots | 🔴 | **B** | `ModuleNotFoundError`（candidate 模組）|
| faces_without_required_slots_are_never_members | 🔴 | **B** | 同上 |
| flag_on_does_not_change_faces_outside_level_a | 🟢 | **A** | M9 殺得掉 |
| isolation_check_catches_an_overbroad_gate | 🟢 | **A** | M8 殺得掉 |
| isolation_check_does_not_flag_a_correctly_scoped_gate | 🟢 | **A** | M9 殺得掉 |
| pending_faces_recorded_not_asserted | 🟢 | **A** | M13 殺得掉 |

## 結論

```text
A（semantic effectiveness proven）  22 / 30   ← 1.2 十二 ＋ 1.3 六 ＋ 1.4 四
B（scaffold，待 candidate 模組）      8 / 30   ← 1.1 六 ＋ 1.4 成員資格二
C（契約本身有問題）                   0 / 30
```

**C ＝ 0**：沒有任何一條出現非預期的紅或綠，故**無契約需先修**。

**尚不能宣稱**：candidate 的 semantic effectiveness（8 條 B 守的東西還不存在）。
**可以宣稱**：量尺（protocol v1 scorer）與作用域判定式**確實會咬到它們聲稱要咬的錯誤**，
且**不會把正確實作誤判為越界**。

**下一步 SHALL 為 1.6 design erratum**，而非 Task 2。

---

## 附記（2026-08-23，erratum 01 裁定後）

erratum 01 改判 membership 為「C 語義契約 × D rollout scope 兩層」，
任務 1.4 因此**新增 2 條契約**（兩層不得被摺疊、Level A Face 兩層皆成立），
兩條皆為 **B（scaffold）**——它們守的同樣是 1.6 後才能實作的 candidate 模組。

```text
母體 30 → 32

A semantic effectiveness proven   22 / 32
B scaffold（待 candidate 模組）     10 / 32
C contract defect                  0 / 32
```

⚠️ **分母變動必須明記**：本輪 A 的絕對數未變（22），
但若只更新分子而不更新分母，覆蓋率會被讀成上升。
