# T3：3939／3940 provenance audit（2026-08-29）

```text
射程  純 git／spec／source archaeology
⛔ 不碰 A04、⛔ 不跑 retrieval、⛔ 不改任何 row、⛔ 不查真實客服語料
```

## Verdict：**H2 — VARIANTS_BY_DESIGN**（有正向證據，⛔ 非「查無理由」）

## 證據一：建立時的設計規則**明文寫著**

`.kiro/specs/billing-conversational-facets/billing-knowledge-review.md:77`

```text
## 三、錨點（12 筆，answer 空、**一種講法一筆**）
```

「**一種講法一筆**」就是建立時的規則本身——錨點的單位是**講法**，⛔ 不是責任。

## 證據二：批次檔的 schema **無法表達**責任區分

`.kiro/specs/billing-conversational-facets/billing-knowledge-batch.json` 的 `anchors`：

```json
{"facet": "滯納金", "question": "滯納金怎麼收這麼多",   "keywords": ["滯納金", "收這麼多"]}
{"facet": "滯納金", "question": "這筆延遲金是怎麼算的", "keywords": ["延遲金", "怎麼算"]}
```

```text
每筆只有 facet／question／keywords 三欄
⛔ 沒有 responsibility 欄、⛔ 沒有 sub-intent 欄、⛔ answer 一律空
⇒ **唯一的語義負載是 `facet`**；兩筆的 facet **相同**
```

## 證據三：同批、同秒級建立

```text
3934 06:21:56.63｜3935 06:21:57.04｜3936 06:21:57.37｜3939 06:21:58.32｜3940 06:21:58.88
（皆 2026-07-03，同一次 seed run）
建立 commit：a020884「帳務知識工程——補標/口徑修正/**錨點**＋路由回歸擴至 44 案」
```

## 證據四：**同一規則套用在全部 5 個 face**

```text
繳費金流排障 3 種講法｜帳單異常 3 種｜發票 2 種｜滯納金 2 種｜帳單設定引導 2 種
⇒ 「一 facet 多講法」是**全域一致的 authoring rule**，⛔ 不是滯納金的特例
```

## ⚠️ 這同時**修正**我在 T4 的一個推論

```text
T4 我寫：帳單異常的 3 個 anchor「產品 intent 明顯不同」
⇒ 那是**我的推論**，⛔ 不是設計。
設計原文說的是「一種講法一筆」——3934/3935/3936 同樣是**講法變體**。
⇒ 「多 anchor 共用一份 facts」不只是觀察到的行為，而是**明文的建立規則**。
```

## ⇒ 對 3939／3940 的裁定輸入

```text
✅ H2 成立：兩列是同一 facet 的 **entry variants**，⛔ 不是兩個 responsibility
⇒ 業主已凍的兩條路：CONSOLIDATE_ONE ／ 明示 alias-entry governance
⛔ **不得**寫兩份 semantic contract
```

## ⚠️ 但這暴露一個更上層的契約張力（需業主裁）

```text
`retrieval_representation` 是 **per-row** 契約
但本設計的責任單位是 **per-facet**（錨點只是該 facet 的不同講法）
⇒ 同 facet 的多個 anchor 若各寫一份 representation：
     內容必然近義 ⇒ 產生兩份高度重疊的 scoring document
     ⇒ 正是 3498 mutation 實證過的 **ranking competition**
   若共用同一份 representation：
     兩列的 scoring 文字**完全相同** ⇒ 排序由其他因素隨機決定
```

⚠️ 這不只影響 3939／3940——**全部 12 個錨點**（5 個 face）都是同一形狀。
⇒ 建議把它立成獨立議題：**responsibility 的契約單位應該是 row 還是 facet？**
⛔ 我沒有替它選邊；本輪只回報 provenance 事實。

## 現況

```text
3939／3940  applicability = instance（已宣告）
            retrieval_representation = **未寫**（⛔ 依業主裁示不硬寫兩份）
LEVEL_A_V2  仍 9 rows，未變
```
