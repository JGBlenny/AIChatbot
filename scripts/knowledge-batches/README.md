# 知識批次（prod 部署重放依賴）

runbook §2/§3 引用的知識匯入批次（均經人工閘門審核後定稿）。原開發位置在 `.kiro/specs/<spec>/`
（開發史，不進版控），**定稿副本收於此處供部署重放**——修改批次請兩處同步或以此處為準。

用法：`python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/<batch>.json [--dry-run]`
（冪等；需本機 postgres 5432 與 embedding-api 5001。）`tune_routing.py` 為 §3 進場路由微調工具。
