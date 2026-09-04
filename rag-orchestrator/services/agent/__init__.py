"""Agent 執行層（spec agentic-mcp-orchestration）。

⛔ 本套件的 `__init__` 刻意保持空白（不 re-export 任何子模組）——
檢索層（`vendor_knowledge_retriever_v2`）要 import `agent.identity`，
若這裡把工具／門面等重量模組拉進來，會在檢索路徑上製造循環匯入。
"""
