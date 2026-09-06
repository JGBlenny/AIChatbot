# 步 7：import

⛔ **需業主授權（D1）**——本步 ⛔ 不得在無業主明確授權下執行。

**輸入**：已核可正本、`diff-report.json`。
**輸出**：`export_batch` → `import_facet_knowledge` 的執行結果＋rollback SQL。
**形態**：腳本；DB 寫入／migration 執行由業主親跑。

⚠️ **尚未實作**（任務 7.1／7.2）：`tools/canon/export_batch.py` 目前不存在；
`import_facet_knowledge.py` 的擴充（讀正本匯出批次寫入）尚未完成。本步驟現況是設計，不是可執行的腳本。
**出口條件**：業主核可＋D1 放行後方可執行；執行前給七步指令＋每步預期輸出＋rollback 路徑。
