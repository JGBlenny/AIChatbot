"""
知識完善迴圈 - 審核面殘留模組

執行機制（回測、迴圈協調、知識生成）已於 2026-09 移除（原打的
POST /api/v1/message 已隨舊 REST 對話鏈刪除，迴圈自此無法執行）。
本目錄現僅保留審核面所需模組：

- embedding_client.py：`routers/loop_knowledge.py` 審核端點的去重比對用 embedding client
- create_missing_indexes.sql：既有索引腳本，與審核查詢效能相關
"""
