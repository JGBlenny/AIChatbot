# Spec 修訂稿 01｜量尺、埋點、不變量的架構性修正（呈業主核准後方可套用）

> # ⛔ 已作廢（2026-08-19）——**不是規格，僅供追溯**
> 修訂稿 01 經審查退回（01：4 項阻斷；02：8 項阻斷含 2 P1），內容已拆解併入
> `decisions/DECISIONS.md` D-01～D-23。**任何條文以三份正文為準，本檔不得引用。**

> 提出日期：2026-08-19｜提出人：實作方｜狀態：**待核准，未套用**
> 觸發：V0 關卡三隻反證代理盤查（見 gate-reports/V0-p0-gate-report.md 附錄），
> 得四項 P2。其中一項證實為**設計期缺陷**（通過設計審查而未被攔下），三項為實作未達標。
> 本稿只寫「改什麼、為什麼、代價」；核准前不動 requirements.md / design.md 一字。

## 0. 修訂總表

| # | 對象 | 性質 | 一句話 |
|---|---|---|---|
| M1 | R1.3＋名詞定義「路由類別」 | **改正設計錯誤** | 路由類別改以決策層自身 verdict 為準，不再從答案文字反推 |
| M2 | R1.3（新增子項） | 補漏 | 驗收比較單位＝(verdict, grounded) 複合鍵，單用類別視為缺陷 |
| M3 | R8.3 | 澄清並可稽核 | 「每輪」明確含面向內續輪與快取命中輪；覆蓋率入 audit 不變量 |
| M4 | R1.1／R1.2（新增子項 R1.8） | 補漏 | 完整性錨點須為本流程不可改寫的外部事實 |
| M5 | 流程鐵則（新增 R2.4） | 補漏 | 不變量須查可觀測事實或 AST，字面 grep 不得為唯一手段 |
| M6 | design C6 | 重寫 | EvalHarness 改讀決策快照；文字判定降級為舊檔專用且標 low confidence |
| M7 | design C1 | 補強 | verdict 與 grounded 為快照必要輸出 |
| M8 | design C8 | 推廣既有原則 | 決策快照與 append_turn 同走 dispatcher 統一出口 |
| M9 | design 新增 C9 | 新增 | 不變量體系的實作標準（可觀測性優先） |

---

## M1｜R1.3：路由類別以決策層 verdict 為準（改正設計錯誤）

### 缺陷事實

同一份 design.md 內兩套詞彙：

- `design.md:85`（C1 決策中樞）：`verdict: Literal["direct_answer", "enter_facet", "form", "fallback", "stay_facet", "exit_facet"]` —— **六值**
- `design.md:230`（C6 評測）：`routing_class: Literal["ANSWER","ASK_ID","FACET_EMPTY","FORM","FALLBACK"]` —— **五值**
- `design.md:234`：`def classify_routing(answer: str)` —— **從答案文字反推**

五類的出處是 `requirements.md:16` 對 E-5 的人工歸納（「直答⇄面向索編號⇄fallback⇄表單」），
於 `requirements.md:60`（R1.3）凍為需求。**決策層知道自己做了什麼，評測卻在外面猜。**

### 實測後果（反證代理，可重現）

1. 五類無法表達「同一類別但知識接地翻轉」：#09/#10 T10「我可以擁有多少個物件？」
   一輪帶 sources 答『上限 10 份』、一輪無 sources 答『**並沒有上限**』（與知識庫矛盾的幻覺），
   兩者皆記 `ANSWER`。逐輪比對實測**漏計 9/25＝36% 的路由不穩定輪**。
2. 五類無 `stay_facet`：面向內澄清與直答混為 ANSWER，V0 曾為此另立 `clarify_question` 旗標，
   屬繞道而非解決。
3. `FORM` 在全語料 1291 輪（含 13 個有記錄該欄位的新 run）**成立 0 次**；run1 五輪真實表單
   被判 ASK_ID。立案敘述「⇄表單」那一支，本尺實質量不到。
4. 文字判定與程式字面量之間無測試釘住：改一次 `conversational_engine.py` 的查無句，
   整批 FACET_EMPTY 會被靜默重判成 ANSWER，而 `classifier_version` 不變。

### 修訂內容

**名詞定義（requirements.md「路由類別」條）**

- 現行：一輪回應的行為歸類——直答知識（ANSWER）／面向索取識別（ASK_ID）／面向查無（FACET_EMPTY）／表單（FORM）／fallback（FALLBACK）。
- 修訂為：一輪回應的**決策層判定去向**，取值即 C1 `RoutingDecision.verdict`
  （`direct_answer`／`enter_facet`／`stay_facet`／`exit_facet`／`form`／`fallback`）。
  類別由決策層產出並落快照，**不得由答案文字反推**。
  舊五類名稱（ANSWER/ASK_ID/…）僅保留於 20260810 凍結語料舊檔的相容判讀，
  並須標記為 `legacy_text_classifier`，不得與 verdict 尺混用於同一統計。

**R1.3 改寫**

- 現行：THE 評測流程 SHALL 對每輪回應自動判定路由類別（ANSWER／ASK_ID／FACET_EMPTY／FORM／FALLBACK），且判定規則 SHALL 版本化以供跨輪比較。
- 修訂為：
  1. THE 評測流程 SHALL 以決策層落於 `usage_events.decision_snapshot` 的 `verdict`
     為路由類別的唯一來源；SHALL NOT 以回應文字反推類別作為正式量測。
  2. WHERE 舊檔（本 spec 立案前產生、無決策快照）需重判，THE 評測流程 MAY 使用文字判定，
     但 SHALL 標記 `legacy_text_classifier` 與其版本戳，且 SHALL NOT 與 verdict 尺混計。
  3. THE 評測流程 SHALL 對「決策層詞彙」與「評測所用詞彙」的一致性設自動檢查
     （枚舉值集合相同），不一致即失敗。

### 代價與影響

- **舊基線失效**：run2/run3 與 b1–b3／a1–a3 皆無完整 verdict 快照，V0 的等價數字須在
  M3、M8 完成後以新尺重測（含把搬移前的碼放回容器重跑 3 輪，約 1 小時）。
- **好處（順帶解消一項待決）**：業主原本待裁的「是否增設第六類 FACET_CLARIFY」自動消失
  —— 評測直接採用 C1 既有的 `stay_facet`，不需另行維護第二套詞彙。

---

## M2｜R1.3 新增子項：驗收比較單位＝(verdict, grounded) 複合鍵

**新增條文**：THE 評測流程 SHALL 對每輪同時記錄 `grounded`（本輪答案是否有知識來源支撐）；
路由穩定性與等價比較 SHALL 以 `(verdict, grounded)` 複合鍵為單位。
WHERE 兩輪 verdict 相同但 grounded 不同，SHALL 計為不一致（該情形代表知識命中退化為
無據生成，後果重於類別翻動）。

**依據**：上節後果 1 的實測——只用類別漏計 36%。以複合尺重算 V0：
多數決不一致 1/107 → **4/107**；輪內變異中位 before 5→13、after 9→13（前後同值，
等價結論反而更乾淨）；E-5 現況不穩定度 5–9/107 → **13/107**。

**連帶**：`e5-attribution-report.md` 的 E-5 目標上限提案（≤3/104）**作廢**，
須於新尺下重新提案並重新請業主核定。

---

## M3｜R8.3：「每輪」的可稽核定義

- 現行：THE 決策層 SHALL 對每輪記錄路由判定的關鍵訊號（校準信心、相對差距、進出面向事件），使任何路由不一致可事後歸因。
- 修訂為（原文保留，補三子項）：
  1. 「每輪」SHALL 含**面向內續輪**、**快取命中輪**與**短路路徑**（如 b2b 僅知識檢索）。
  2. THE 系統 SHALL 使「未落快照」成為可觀測狀態而非靜默缺席——無法產出完整快照的路徑
     SHALL 仍落一筆帶 `path` 標記的最小快照。
  3. 快照覆蓋率 SHALL 入 `make audit` 不變量：非內部事件中 `decision_snapshot IS NULL`
     比例 > 1% 即 FAIL。

**缺口事實**：現況覆蓋 176/321＝54.8%；扣除面向進場輪後其餘 230 輪僅 37%；
面向內續輪 **0%**——即 #07「一次黏著、五輪全毀」的現場零埋點。
`services/decision_layer.py` 檔頭「從此每輪記下」與實作不符，須同步更正。

---

## M4｜新增 R1.8：完整性錨點須為外部不可改寫事實

**新增條文**：THE 評測流程對凍結語料的完整性檢核 SHALL 以**本流程無法改寫的外部事實**
為錨點（如 S3 物件的 SHA-256）；SHALL NOT 僅比對由本流程自行產生並可一併更新的本機摘要。
WHERE 外部錨點暫不可達，THE 流程 SHALL 明示降級並標記該輪結論「完整性未經外部錨點驗證」。

**缺口事實**：現行 `verify_corpus_integrity` 只比對 `noise_manifest.json` 內由同一支程式
算出的樹雜湊——同時改語料與重算雜湊即可通過（自簽自證）。而
`docs/backtest/corpus-20260810/README.md:20` 明寫「開跑前必驗 SHA-256，不符即 abort」，
程式從未讀取 `tarball_sha256`、從未觸及 S3 —— **文件與實作不符，須擇一修正（本稿主張實作）**。
另：三個 run 目錄受 `.gitignore` 忽略，竄改不留版控痕跡，本條為唯一防線。

---

## M5｜新增 R2.4（流程鐵則）：不變量查事實不查字串

**新增條文**：WHEN 為「修掉一類 bug」新增系統不變量，THE 不變量 SHALL 檢查
**可觀測結果**（資料庫事實、執行期行為）或**語法結構**（AST）；
SHALL NOT 以原始碼字面 grep 作為唯一手段，除非該檢查對象本身即為文字（如文案外洩）。
THE 不變量 SHALL 附「規避測試」：以該類 bug 的合理變形寫法驗證確實 FAIL。

**缺口事實**：不變量 8 實測 8 種寫法只擋 1 種——`os.environ[...]`、`os.environ.get`、
`from os import getenv`、字串拼接、變數間接、**甚至多一個空格**皆可繞過；
常數檢查對 `_SOP_MIN = 0.6`、型別註記、dict 形式、內聯字面量 `if s > 0.6:` 全無感；
掃描範圍未含 `tools/`、`scripts/`、`knowledge-admin/`。
現況無實際洩漏（任務 1.3 的收斂是真的），失效的是「鎖得住」這句話。

---

## M6｜design C6 重寫：EvalHarness 改讀快照

```python
# scripts/backtest/decision_replay.py
class TurnResult(TypedDict):
    case_id: str; turn: int
    verdict: Literal["direct_answer","enter_facet","stay_facet","exit_facet","form","fallback"]
    grounded: bool | None            # 知識接地（正交維度，M2）
    source: Literal["snapshot","legacy_text"]   # 類別來源，混計即為缺陷
    classifier_version: str | None   # 僅 legacy_text 有值
    noise_tags: list[str]

def collect_verdicts(run_tag: str) -> dict[tuple[str,int], TurnResult]: ...
    # 重播後自 usage_events 依 session_id 取回快照對齊輪次（**不改請求 payload**，
    # 與凍結語料 payload 逐欄一致，可比性不變）
def classify_routing_legacy(answer: str, *, sources) -> tuple[str, str]: ...
    # 舊檔專用；回傳值一律標 source='legacy_text'
```

**設計決策**：
- 重播請求形狀不動（保持與 run2/run3 可比），對齊靠 `session_id`＋輪序，不靠回應欄位。
- verdict 與評測枚舉的一致性由自動檢查釘住（M1-3）。
- 表單路由自此由 verdict `form` 直接可見，不再依賴 `form_triggered` 欄位。

---

## M7｜design C1 補強

`RoutingDecision.snapshot` 的**必要欄位**明列：`verdict`、`grounded`、`rule_version`、
`config_hash`、`decision_case`、`path`。缺任一即視為不完整快照（M3-2 的最小快照除外，
但須帶 `path` 與 `incomplete: true`）。

---

## M8｜design C8 推廣既有原則

現行 C8（審查修訂 3）已定：`append_turn` 統一放 dispatcher 出口層、含快取命中路徑。
**本稿將同一原則推廣至決策快照**：快照於請求生命週期中由各階段**貢獻**片段，
於**唯一出口**組裝落地；任何未貢獻的路徑落最小快照（M3-2），不得靜默缺席。

**風險**：動 chat.py 回應出口層，風險高於任務 1.3 的搬移。緩解：沿用同一套等價驗證
（先埋後搬、決定性子決策嚴格等價＋凍結語料統計等價），並以 M3-3 的覆蓋率不變量收尾。

---

## M9｜design 新增 C9：不變量體系實作標準

| 檢查對象 | 允許手段 | 禁止 |
|---|---|---|
| 程式結構（讀值點、常數定義） | AST 走訪 | 字面 grep 為唯一手段 |
| 執行期事實（埋點覆蓋、資料一致） | DB 查詢／實跑探測 | 相信程式碼有呼叫 |
| 外部資產完整性 | 外部錨點（S3 sha256） | 本流程自簽摘要 |
| 文案外洩類 | grep 可（對象即文字） | — |

每條不變量 SHALL 附規避測試（M5）。

---

## 影響彙總與代價

| 項 | 工作量 | 風險 |
|---|---|---|
| M8 埋點搬統一出口（先做，M1 依賴它） | 1 天 | 中—動出口層，需等價驗證 |
| M1／M2／M6 量測改讀 verdict＋複合尺 | 0.5 天 | 低 |
| M3-3／M5／M9 不變量升級（AST＋覆蓋率＋規避測試） | 0.5 天 | 低 |
| M4 語料錨點接 S3 | 0.5 天 | 低 |
| V0 全套重測（含搬移前碼回放 3 輪＋搬移後 3 輪） | 0.5 天 | 低 |
| **合計** | **約 3 天** | — |

**P0 須重開**：V0 現有數字（1/107、基線 5/107、E-5 上限 ≤3/104）全部建於舊尺，
修訂套用後一律作廢重測。已完成且不受影響的部分：任務 1.3 的門檻收斂（實質正確）、
六 case 嚴格等價（38 萬格獨立對拍）、快取軌別閘門。

## 請業主裁決

1. 本修訂稿是否核准套用（核准後才改 requirements.md／design.md）。
2. M1 動到已核准需求 R1.3 與名詞定義——確認是否同意以「決策層 verdict」取代人工五類。
3. P0 重開、V0 重測，時程增加約 3 天——是否接受。
