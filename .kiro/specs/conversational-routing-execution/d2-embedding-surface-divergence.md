# D2 divergence register —— embedding surface 的三個產生點（**其中兩個互相矛盾**）

發現時機：D1/D2/D3 第一階段接線時，機器掃描（不變量 12 檢查項 C）盤出。
⚠️ 這是**既有缺陷**，⛔ 不是本輪引入。

## 掃出的三個產生點

| 產生點 | surface 表達式 | 何時跑 |
|---|---|---|
| `knowledge-admin/backend/app.py` `create_knowledge`（POST） | `question_summary` | 新建知識 |
| `knowledge-admin/backend/app.py` `update_knowledge`（PUT） | `f"{question_summary}. 關鍵字: {keywords}"` | 編輯知識 |
| `services/knowledge_import_service.py` | `question_summary` | 批次匯入 |
| `scripts/regenerate_all_embeddings.py` | `question_summary` | 全量重生 |

## ⚠️ 已確認的矛盾（**同一支服務、同一張表**）

```text
新建 → embedding 只吃 question_summary
編輯 → embedding 吃 question_summary ＋ ". 關鍵字: …"
⇒ **一筆知識被編輯過，它的 embedding surface 就換了一種**，
  且沒有任何欄位記錄它現在是哪一種。
⇒ 全量重生（regenerate_all_embeddings）會把所有被編輯過的 row
  **靜默改回**只有 summary 的版本。
```

兩邊各自的註解都言之成理，且**互相對立**：
- create：「keywords 透過獨立的關鍵字搜尋機制處理」
- update：「✅ 方案 A：將 keywords 融入 embedding」

⇒ 這正是 D2 要根除的形態：**沒有單一 surface 契約，就會長出互相矛盾的實作。**

## 本輪的處置（⛔ 未修）

```text
✅ 登記在不變量 12 的 register，狀態 `divergent_pending`
✅ 新增未登記的 surface 產生點 ⇒ 稽核**紅燈**（防止再長第四種）
⛔ **未**統一——統一等於改變**全庫**既有 row 的 embedding 語義，
   遠超「Level-A 10 rows」的授權範圍
```

## 待業主裁定（⚠️ 不在本輪 scope，供排序用）

```text
Q1 keywords 要不要進 embedding？（現況是「看你有沒有編輯過」——無論答案為何，這都不對）
Q2 統一之後是否需要全量 re-embed？（成本與風險）
Q3 統一時機：在 Level-A 10 rows 驗證之後，還是同批？
```
⚠️ 現有實測證據（「加入 answer 降低 9.2%」）談的是 **answer**，
⛔ **不**構成對 Q1（keywords）的答案。
