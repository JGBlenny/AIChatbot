# A03 retrieval semantic failure —— 分類學（2026-08-29）

- 語料：A03 **burned** corpus（用途已是 failure analysis，⛔ 不再形成任何 validation claim）
- 母體：10 個 semantic evaluation units 的 **SEMANTICALLY_JUDGEABLE** 查詢，共 **126**
- ⛔ 本檔**只做分類與歸因候選**，未修改任何設定、未動 KB、未調門檻

## primary buckets（**互斥**，⛔ 不重複計數）

```text
                              n    %
P0 CORRECT_TOP1              67  53.2%
P1 EXPECTED_OUTSIDE_TOP10    46  36.5%   ← **最大宗**
P2 WRONG_TOP1_LEVEL_A         4   3.2%
P3 WRONG_TOP1_NON_LEVEL_A     9   7.1%
```

| unit | n | P0 | P1 | P2 | P3 |
|---|---:|---:|---:|---:|---:|
| G1 | 19 | 8 | 6 | 0 | 5 |
| G2 | 20 | **3** | **16** | 0 | 1 |
| G3 | 18 | 5 | 9 | 3 | 1 |
| I1-explicit | 10 | **10** | 0 | 0 | 0 |
| I2-explicit | 10 | 3 | 5 | 0 | 2 |
| I3-explicit | 10 | 7 | 2 | 1 | 0 |
| I4-explicit | 10 | 8 | 2 | 0 | 0 |
| I5-explicit | 9 | 8 | 1 | 0 | 0 |
| I6-explicit | 10 | 5 | 5 | 0 | 0 |
| I7-explicit | 10 | **10** | 0 | 0 | 0 |

## 正交 tags（僅 wrong-top1，n=59）

```text
T_PAIR_COMPETITION   **5/59（8.5%）**
T_SAME_CATEGORY      10/59
T_EXPECTED_RANK      {2:5, 3:5, 4:1, 6:1, 7:1}｜**expected 未進 top10：46**
T_MARGIN             n=13  min 0.0005 ／ median 0.0815 ／ max 0.2464
```

## ⚠️ 第一個結論：**pair-competition 假說被資料反證**

```text
T_PAIR_COMPETITION 只占 wrong-top1 的 **8.5%**
且真正落在「expected rank2 ＋ winner 是配對成員 ＋ margin 很小」的案例是少數
⇒ ⛔ **不得**把「mechanism ↔ lookup pair 可分辨性」升成主要機制
（我先前的懷疑方向是錯的，這裡照實更正）
```

## ⚠️ 第二個結論：主導失敗是 **candidate generation／recall**，不是 ranking

```text
P1 再拆（互斥）：
  P1a **零召回**（top-k 完全空）        **17**
  P1b 有候選但 expected 不在 top10      29

且「有候選」時候選數極少（要 top_k=10，實得）：
  1 筆 ×9｜2 筆 ×10｜3 筆 ×3｜4 筆 ×2｜5 筆 ×3｜6 筆 ×1｜8 筆 ×1
⇒ **多數查詢在 production 門檻下只留下 1–2 個候選**
```

⚠️ 這是**在 production 門檻（`DecisionConfig.kb_threshold`）下**的實況，
⛔ 不是我把門檻調高造成的 artifact。

### 零召回集中在 G2（11/17）

```text
下載收據需要什麼權限嗎 ／ 怎麼一次下載多張收據 ／ 房客說要正式收據我該給他什麼
收據是 PDF 檔嗎還是只能截圖 ／ 收據檔案要怎麼寄給房客 ／ 收據能不能直接用email寄出
繳費證明可以補印嗎 ／ 請問繳費證明跟收據是同一份東西嗎要怎麼拿 …
```

## ⚠️ 兩個**尚未分離**的機制候選（⛔ 我不預選）

```text
【M-A】retrieval 召不回**本來就涵蓋該 intent** 的 row
      ⇒ 屬 retrieval／candidate generation 缺陷
【M-B】KB **本來就沒有**涵蓋該 intent
      ⇒ 屬知識覆蓋缺口；作者依任務描述自然發散，寫出 3406 那一列並未回答的問題
        （「email 寄送」「批次下載」「下載權限」「補印」皆非 3406 的內容）
```

⚠️ ⛔ **不得**在未分離前宣稱「retrieval 壞了」——那會把知識覆蓋問題誤記成檢索缺陷，
並導致錯誤的修法（調門檻／改 embedding）去補一個**知識本來就沒有**的答案。

## 各 unit 的形狀差異也支持「不是單一原因」

```text
I1-explicit／I7-explicit  **10/10 全對**  ⇒ 檢索在這兩個語義上完全正常
G2                        3/20，且 11 筆零召回 ⇒ 極端案例
G1／G3                    P3（被非-Level-A KB 超車）較多 ⇒ 與 G2 形態不同
```

⇒ ⛔ 不得用單一結論概括十個 unit。

## 下一步的可行分岔（⛔ 待裁，未執行）

```text
【甲】先分離 M-A／M-B：逐一檢視零召回與 P1b 的問句，判定「KB 是否本來就涵蓋」
     ⚠️ 這是**知識覆蓋判定**，屬產品語義，⛔ 不是我單方能裁
【乙】量測 production 門檻對候選數的影響（純觀測，⛔ 不調參）
【丙】先不動 retrieval，改為檢視 A03 corpus 的 stratum 定義是否比 KB 實際涵蓋更寬
     ⚠️ 若是，那 Layer A 的 80% 門檻在這些 unit 上量的其實是**知識覆蓋**而非檢索對位
```

## 狀態

```text
P1f successor             FROZEN／locally confirmed（SHA 8fb196f）
A03-SEMANTIC              FAIL（**仍成立**）
retrieval root cause      **NOT YET ESTABLISHED**
pair-competition 假說      **REFUTED**（8.5%）
主導失敗型態               candidate generation／recall（P1 = 36.5%，其中零召回 17）
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
