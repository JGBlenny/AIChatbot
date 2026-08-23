# 需求規格：routing-disambiguation

> 建立 2026-08-23｜語言 zh-TW
> 前案：[conversational-routing-execution](../conversational-routing-execution/tasks.md)（3.3 診斷完成／3.4 修法 REFUTED）
> ⚠️ `.kiro/settings/rules/ears-format.md` 與 `templates/specs/requirements.md` 不存在，
> 本文件沿用前案已建立的 WHEN/THEN/SHALL 內建結構與數字 ID 編號。

## 本案要回答的問題

> **當同一語義主題同時包含教學／規則型與 instance-specific 問句時，
> routing 應在哪一層取得足夠訊號，把兩者可靠分開？**

⚠️ **不需重做「有沒有問題」的 discovery**——問題陳述已由前案 3.3／3.4 以實測證實：

| 已證實 | 出處 |
|---|---|
| 三筆 production `REGRESSION`（HARNESS_DRIFT 0／EXPECTATION_DRIFT 0）| 3.3 evidence packet，六案兩側逐節點比對 |
| 根因＝routing metadata overreach | `20260731_assistant_report_fixes.sql` §3 逐字點名 3402／3406／3519 |
| in-scope 的 anchor 修法**不足** | 3.4 獨立 verifier REFUTED（`ae2aedc` → revert `89ff489`）|
| 兩邊共用同一份 metadata、以現行機制拆不開 | 雙向 regression suite，integration 177 passed／4 known-red |

**反證細節**（本案不走 anchor 路線的直接理由）：

```text
instance：我這筆點退帳單怎麼會是這個數字   3519 0.905 vs 錨點 0.902  → 差 0.003，錯邊
rule    ：系統怎麼算點退帳單的金額         錨點 0.967 vs 3519 0.963  → 差 0.004，也錯邊
```

---

## Requirement 1：判別能力必須**雙邊同時**成立

**背景**：前案最重要的教訓是「三筆 regression 綠了」曾構成假綠——
被修復所要**保存**的另一半能力（T-1 的查實值）根本沒有進驗收集合。
本案的驗收從第一天就必須同時描述兩邊。

> ⚠️ **1.1–1.3 的適用範圍限於 Requirement 2.5 最終宣告之範圍**（例如僅帳單診斷域）。
> 未經 2.5 宣告為可推廣者，SHALL NOT 表述為 21 個面向的通則。

- 1.1 **在 Req.2.5 宣告之適用範圍內**，WHEN 使用者提出 **instance-specific** 問句
  （指涉自己的某一筆資料），THEN 系統 SHALL 進入該筆資料對應的診斷面向。
- 1.2 **在 Req.2.5 宣告之適用範圍內**，WHEN 使用者提出 **教學／規則／流程／操作** 問句
  （詢問通則而非某一筆），THEN 系統 SHALL 以單發直答回應，SHALL NOT 進入面向後反問識別欄位。
- 1.3 任何修法 SHALL 同時通過 1.1 與 1.2；**只通過其一者不構成修復**。
- 1.4 instance 側的驗收 SHALL 斷言到**具體面向**，SHALL NOT 僅斷言「進入了某個對話」——
  前案已兩度因只驗 `dialog` 而把**跑錯面向**算成成功。
- 1.5 ⚠️ 本需求描述的是**能力**，不指定實作層級；層級由 Requirement 2 選定。

---

## Requirement 2：判別訊號的**層級歸屬**必須以證據選定

**背景**：3.4 證明「在 KB metadata 層以相似度競爭分辨兩類問句」不可行。
本案的核心產出是**選定判別訊號應落在哪一層**，而非再調一次措辭。

- 2.1 系統設計 SHALL 逐一評估下列候選層。**每一層（含被否決者）SHALL 留下同等份量的證據**，
  各含六項：①可觀測的 signal 是什麼；②相對**現行判別機制**新增了什麼資訊；
  ③可行性；④代價；⑤否決／保留理由；⑥**可反證條件**。
  SHALL NOT 只詳寫勝出方案而以「代價較高」一句帶過其餘五層。

  | 候選層 | 說明 |
  |---|---|
  | lexical／structural instance signal | 「我的／這張／編號 N」等表層或句構訊號 |
  | routing-specific metadata／trigger representation | 把 Routing Hint 與 knowledge evidence 分離表示 |
  | intent stage | 在意圖分類階段就分流 |
  | applicability gate | 進場後把關（現有 `_preentry_routable` 的延伸）|
  | clarification | 先澄清再 routing |
  | KB responsibility 拆分 | 一筆 KB 只承載一種使用者意圖 |

- 2.2 ⚠️ 評估 SHALL NOT 預設答案為 instance-marker；
  「表層訊號最直覺」不構成選定理由。
- 2.3 選定的層級 SHALL 附**可反證的依據**——說明它為何能提供
  **現行判別機制或被它替代的方案拿不到**的訊號，而非僅「換個地方做同樣的相似度比較」。
  （六個候選層**不是線性 pipeline**，故不以「前一層」表述。）
- 2.4 IF 評估結論為「現有任一層皆無法可靠分辨」，
  THEN 該結論本身 SHALL 被記錄為有效產出，並說明所缺的是什麼訊號。
  ⚠️ **六層皆不足時 SHALL NOT 為了讓本 spec 看起來完成而強選一個 winner。**
- 2.5 選定方案 SHALL 說明其**適用範圍**：僅適用帳單診斷域，或可推廣至全部 21 個面向。
  該宣告即 Requirement 1 的作用域，SHALL 明確且可驗。
- 2.6 六個候選層 SHALL **各自產出一筆 disposition**：
  `SUPPORTED` ／ `REJECTED` ／ `INSUFFICIENT_EVIDENCE`。
  每筆 SHALL 指名**支持或否決它的 production evidence**，
  以及「**哪一個觀察結果若出現，會推翻本判定**」。
  SHALL NOT 只記錄最終選定方案。

  > 合法的結論形態包括六層全為 `REJECTED`／`INSUFFICIENT_EVIDENCE`——
  > **那比被迫挑一個 winner 更有價值**。

---

## Requirement 3：判別**不得依賴相似度排名邊際**

**背景**：3.4 的修法在兩側皆以 0.003～0.005 的分數差維持，
corpus 新增或 semantic-model 重建即可能翻面——這是機制脆弱，不是措辭不佳。

- 3.1 判別結果 SHALL NOT 由**兩個競爭候選之間的相似度差**單獨決定。
- 3.2 WHEN 依 **3.5 預先凍結的 corpus／model perturbation protocol** 新增知識或重建 semantic-model，
  THEN 判別穩健性 SHALL 滿足 3.3 預先定義的通過門檻。
  （不要求對**所有未知未來資料**做不可證明的保證——那無法驗收。）
- 3.3 方案 SHALL 提出**可量測的穩健性判準**，並說明其量測方式
  （例：擾動語料後判別翻面率、判別依據與分數的相關性）。
- 3.4 ⚠️ 「加一個更好的錨點使分數差擴大」SHALL NOT 視為滿足本需求——
  那只是把邊際從 0.003 變大，未消除「由邊際決定」這個性質。
- 3.5 **BEFORE** 任何候選方案依驗收結果進行實作或調整，
  穩健性量測 SHALL 凍結：**案例集合、擾動方式、分母、指標、通過門檻、corpus／model 版本**。
  **AFTER** 方案未通過，若需修改量尺，THEN SHALL 建立**新量測版本並保留舊版本結果**；
  SHALL NOT 事後修改原量尺使既有方案轉為通過。

  > ⚠️ 這是前案 `freeze_measurement.py` 紀律在本案真正需要出現的位置：
  > 量尺若能在看到結果後才定，就可以先做方案、再挑對自己有利的 perturbation——
  > 那是另一種 overfit，且比調測試集更難察覺。

---

## Requirement 4：面向歸屬**未定案項**必須判定

**背景**：前案標記兩筆問句實測進入「帳單異常」而非「條件診斷：帳單」，
其**產品上的正確歸屬尚未定案**，故被隔離於 `BILLING_INSTANCE_FACET_UNDECIDED`。

- 4.1 系統 SHALL 判定下列問句在產品上應進入哪一個面向：

  | 問句 | 實測進入 | 正確歸屬 |
  |---|---|---|
  | 我的收據在哪 | 帳單異常（3936）| 待判定 |
  | 我這筆點退的錢怎麼怪怪的 | 帳單異常（3934）| 待判定 |

- 4.2 判定 SHALL 來自**產品 owner 裁示**，或**既有產品規格／業務規則**。
  WHEN 判定完成，THEN 該問句始得列入 Requirement 1 的正向斷言集合；
  無上述依據者 SHALL 維持 undecided。
  ⚠️ **現行 route、embedding 分數、migration provenance 三者皆 SHALL NOT 單獨作為產品歸屬依據**——
  否則等於讓測試結果替產品做決策（前案 3.3 已據此建立 `provenance ≠ justification`，見 Req.7.3）。
- 4.3 ⚠️ 在判定完成之前，SHALL NOT 以「有進入某個面向」作為 instance 能力成立的證據。
- 4.4 IF 判定結論為「兩個面向皆可接受」，
  THEN 驗收斷言 SHALL 明確表達該可接受集合，而非放寬為「任一 dialog」。

---

## Requirement 5：既有能力**不得回退**

- 5.1 WHEN 方案上線，THEN `20260731` T-1 所建立的查實值能力 SHALL 維持——
  該需求本身是真的，**修復不得以犧牲它為代價**。
- 5.2 對 20260731 同批其餘七筆知識（3495／3496／3498／3499／4640／4656／4657），
  系統 SHALL 先**區分「現行行為」與「產品上應維持的行為」**：

  ① 逐筆判定其代表的 **intended behavior**（依據同 Req.4.2：產品裁示或既有規格／業務規則）；
  ② **僅有產品依據支持者**始得成為 non-regression assertion；
  ③ 驗收 SHALL 鎖**使用者可見的 expected route／facet**，
     SHALL NOT 要求既有 KB metadata 或 entry mechanism 原樣保留；
  ④ 七筆之 blast radius SHALL **全數實測記錄**（不論是否入 assertion）。

  > ⚠️ 「這七筆現在怎麼跑，以後就 SHALL 怎麼跑」**與 Req.7.3 直接衝突**——
  > 那是從另一扇門把「現況＝正確」放回來。且會鎖死 Req.2 的方案空間：
  > 若判別移至 intent stage 或 applicability gate，這些 KB 可能**不再以同樣機制進場，
  > 但產品能力仍正確**。故本需求鎖能力，不鎖機制。
- 5.3 WHEN 方案上線，THEN integration baseline SHALL NOT 出現新的失敗；
  現行雙向 suite 的**四筆 routing known-red SHALL 轉綠**。

  | known-red | 來源 |
  |---|---|
  | 點退帳單的金額是怎麼算的 | 前案 3.3 正式判定之 `REGRESSION` |
  | 點退做完後，帳單會自動出來嗎？ | 同上 |
  | 收據 PDF 在哪裡下載 | 同上 |
  | 系統怎麼算點退帳單的金額 | **後續 3.4 verifier（A2）新暴露的 rule-side known-red** |

  ⚠️ 前案 3.3 的正式定案為 **三筆** `REGRESSION`；第四筆是雙向 suite 上線後才暴露的。
  SHALL NOT 回寫成「3.3 判定四筆」。

---

## Requirement 6：量測與驗收紀律（沿用前案既有資產）

**背景**：前案已建立可信的量測環境，本案 SHALL 直接沿用，不重造。

- 6.1 驗證 SHALL 驅動 **production code path**（`_diagnosis_config_for_knowledge`），
  SHALL NOT 於測試內重演或重建 routing 語義。
- 6.2 語料 SHALL 使用 **frozen corpus**（`scripts/provision-test-db.sh --with-corpus`）。
  **權威來源為 `database/test-corpus.manifest` 的 digest／version，而非列數**；
  語料變動 SHALL 反映於 digest 並於報告中標明。
  （本案立案時之 snapshot 為 873 列／872 embedding、digest `918b69ce70fbb8f1660819c3774eb24b`
  ——**記錄用，非驗收條件**；經正式程序換 snapshot 時本需求不因列數變動而失真。）
- 6.3 測試環境的行為參數與服務位置 SHALL 與 production 一致
  （由 `test_env_parity_req.py` 守護）——前案曾因少一個 env 或多一個宿主視角 URL
  而使判定本身成為假證據。
- 6.4 測試 SHALL 連白名單內的測試資料庫；DB fail-closed 守門 SHALL 維持有效。
- 6.5 ⚠️ 新增任何守門或不變量時 SHALL 先做 **negative control**——
  證明它在「該失敗的情境」下真的會失敗，否則加進去的是假綠燈。

---

## Requirement 7：metadata 變更的審查等級

**背景**：本案的病灶正是一次未經同等審查的 metadata 變更（20260731 §3）。

- 7.1 WHEN 變更任何具 routing／action 意義的 metadata，
  THEN 該變更 SHALL 經與程式碼變更同等的審查與回歸驗證。
- 7.2 變更 SHALL 明確記錄其**新增或移除的 Face entry points**。
- 7.3 ⚠️ **provenance ≠ justification**：能證明「某變更為何造成今日行為」
  SHALL NOT 自動成為「該行為正確」的依據——前案 3.3 已據此把三筆判為 `REGRESSION`
  而非 `EXPECTATION_DRIFT`。

---

## Requirement 8：範圍邊界（明確不做）

| 項目 | 不做的依據 |
|---|---|
| 更多 anchor tuning | 3.4 已反證：脆弱性來自**機制**，不是措辭 |
| 對測試集調向量排名 | 雙向 regression suite 的存在即為使這條路不可行 |
| 在前案 spec 內偷塞全域 routing heuristic | 前案 Req.8 明文排除；本案若需動 routing，SHALL 於本案內明示並評估 |
| 調整全域 similarity threshold 或 `top_k` | 前案已證非現行分歧；動它們會改變所有面向的行為 |
| 重建或替換 retrieval pipeline | 病灶不在檢索找錯 KB——**KB 找對了，是它攜帶的 Routing Hint 過寬** |

---

## Requirement 9：結論分級

- 9.1 WHEN 僅通過現有 frozen corpus 與雙向 suite，
  THEN 結論 SHALL 僅聲稱「技術可行／regression-safe」。
- 9.2 「routing 品質確實提升」SHALL 僅在通過 production holdout 後聲稱。
  ⚠️ **holdout SHALL NOT 參與方案選定、threshold 設定或 regression suite 調整**——
  用 holdout 調完再說「holdout 通過」，名義上仍是 holdout，實際已污染。
- 9.3 任何關於**泛化效果**（例如「可推廣至全部面向」）的比較性結論
  SHALL 以 **≥30 個可判定案例**為基礎。
  **不受此限**：單一 bug 重現、deterministic contract 驗證、已知 case 的回歸。
- 9.4 IF 方案僅在帳單診斷域驗證，
  THEN 結論 SHALL 明確標示其適用範圍，SHALL NOT 表述為通用解。

---

## 需求優先序

```
Req.3.5  凍結穩健性量尺        ← **最先做**：量尺不得在看到結果後才定
   ↓
Req.2    六層評估＋逐層 disposition（含否決證據）  ← 核心產出，先於任何實作
   ↓
Req.4    面向歸屬判定（產品裁示）  ┐
Req.5.2  七筆 intended behavior 判定 ┘ ← 兩者共同決定 Req.1／5 的斷言集合
   ↓
Req.2.5  宣告適用範圍          ← 即 Req.1 的作用域
   ↓
Req.1    雙邊能力（驗收主軸）
   ↓
Req.3    穩健性驗證            ← 與 Req.1 同批驗，不得後補
   ↓
Req.5.3  四筆 known-red 轉綠 ＋ 5.2 blast radius 全數記錄
```

⚠️ **兩處順序不可對調**：
① **Req.3.5 必須在任何實作或調整之前**——否則可先做方案、再挑對自己有利的擾動定尺；
② **Req.4／5.2 的產品判定必須在斷言集合定案之前**——否則等於讓測試結果替產品做決策。

Req.6／Req.7／Req.8／Req.9 為橫向約束，適用於全程。

**命名約定**：`Req.N` 指本文件的需求編號；引用前案時一律加 spec 名
（例：`conversational-routing-execution` Req.8），兩者不得混用。
