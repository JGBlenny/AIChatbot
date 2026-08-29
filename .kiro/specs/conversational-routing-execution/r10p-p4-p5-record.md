# R10-P4 registry seal ＋ P5 census 執行紀錄（2026-08-29）

## 一、產出與 digests

```text
r10p/registry.json       REGISTRY_DIGEST   3e5bcdc6a8265fbf…
r10p/p4-projection.json  PROJECTION_DIGEST 0635b469db39fc28…
r10p/p5-census.json      CENSUS_DIGEST     ee8e398deff686f6…
R10P_STAGE = P4_REGISTRY_SEALED → **P5_CENSUS_DONE**
```

## 二、業主凍結的五類投影規則

```text
CONFIRMED_RESPONSIBILITY  建立一筆 reviewed_active；confirmed members 全數掛入
MERGE_WITH_OTHER          ⛔ 不建 record；member rows 轉掛 target
SPLIT_REQUIRED            ⛔ 不建 source record；source row 掛到**每一個** split target；
                          membership_origin=SPLIT_REQUIRED；⛔ 貢獻 0 個新 identity
HISTORICAL_ONLY           status=reviewed_historical；⛔ 不計 active census、⛔ 不進 scoring
INSUFFICIENT_EVIDENCE     ⛔ 不建 record；row 記 unresolved
                          ⚠️ ⛔ 不得為了湊滿 54/54 而把 UNKNOWN truth 逼成假 authority
```

## 三、3511 的裁定：多重 membership，⛔ 不做 status=rejected

```text
row 3511 → R(move_in) ／ R(move_out) ／ R(early_termination) ／ R(renew)
理由：SPLIT_REQUIRED 否定的是「3511 作為 singleton responsibility」，
      ⛔ 不是否定 row 3511 本身。做成 rejected 會在 registry 永久留下一個
      **從未成立過的 fake responsibility identity**，只為記錄 proposal 被拆掉。
      那段歷史屬於 P3 provenance，⛔ 不得污染 P4 authoritative registry。
⚠️ 這同時驗證 C2 必須允許的關係：**一個 retrieval row 可以提名 1..N responsibilities**。
```

## 四、前提修正：row disposition 完整 ≠ responsibility assignment 完整

```text
舊說法（我先前的）  「54-row population 的每一列都必須在 registry 找得到歸屬」
業主修正           「每一列都必須在 P4 projection 找得到 **disposition**；
                    ⛔ 不要求每一列都有 confirmed responsibility membership」
窮盡分割（四類之一）
  A member of one reviewed responsibility          36
  B member of multiple reviewed responsibilities    1（3511）
  C historical-only member                          1（3498）
  D unresolved / no authoritative membership yet   16
                                            合計   54 ✅
```

## 五、P5 census —— 兩個 denominator 分開報

```text
ROW COVERAGE
  FROZEN_ROWS                     54
  ROWS_WITH_CONFIRMED_MEMBERSHIP  36
  ROWS_WITH_MULTI_MEMBERSHIP       1
  ROWS_HISTORICAL_ONLY             1
  ROWS_UNRESOLVED                 16

RESPONSIBILITY CENSUS
  ACTIVE_REVIEWED_RESPONSIBILITIES  **30**
  HISTORICAL_RESPONSIBILITIES         1

貢獻 0 個 active responsibility 的：3511（SPLIT）／3498（HISTORICAL）／
                                   16 個未解列／5 筆 MERGE（併入 target）

LEVEL_A_V2
  9 列 → **9 個相異 responsibility**（無共用、無多重 membership）
  ⚠️ A05 的 denominator 若維持 9，理由現在是**機器可追溯的 responsibility census**，
     ⛔ 不再是「看起來沒有 aliases」。
```

## 六、claim ceiling

```text
可宣稱  在機械凍結的 54-row governance population 內：row disposition 完整（54/54），
        已建立 30 個 active reviewed responsibility ＋ 1 個 historical。
⛔ 不可  「全 KB responsibility taxonomy 已完成」——54 是治理母體，不是全站語義宇宙
⛔ 不可  「54 列都有 responsibility 歸屬」——16 列是 D 類未解，這是**誠實的未知**
⛔ 不可  「30 就是最終責任數」——16 列未解，任一列日後可能新增或併入責任
```

## 七、新增不變量 20（P4 投影完整性）

```text
scripts/audit/checks/p4_projection_integrity.py（--self-test 九項全綠）
① registry／projection bytes == 凍結 digest（佔位一律 FAIL）
② row disposition 是 54 的窮盡分割，且**與 registry 實況逐列交叉核對**
③ SPLIT：⛔ 無自己的 record／恰好映到 frozen split_across／每個 target 皆 reviewed_active／
   來源列出現在**每一個** target 的 members／membership_origin 必須標 SPLIT_REQUIRED
④ MERGE：⛔ 無自己的 record；其列必須在 target 的 members 內
⑤ INSUFFICIENT_EVIDENCE 的列 ⛔ 不得出現在任何責任的 members（防為湊滿而製造 authority）
⑥ HISTORICAL ⛔ 不計入 active census
⑦ canonical_responsibility 與 PENDING_OWNER_STATEMENT 一致——⛔ 機器不得代填
正對照：漏掛 split target／偽造第五責任／掛到 split 之外／未解列被塞入／
        disposition 少一列／historical 標成 active／機器代填 canonical／bytes 被改
```

## 八、⚠️ 待業主處理

```text
canonical_responsibility 有 **23／31 筆為 PENDING_OWNER_STATEMENT**
（schema 明文：⛔ 不得由機器自動產生後直接生效，故一律留 null）
responsibility_id 目前是**機械序號** R-01…R-31（依 sealing group 最小 row id 排序），
⛔ 不承載語義、⛔ 不綁定任何單一 row——正式命名待業主。
```
