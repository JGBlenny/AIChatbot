# r6 plan-verifier（增量：agent.turn／design 1.4／tasks 2.6）— 2026-09-04

REVISE
[P1] `agent.turn` 以 scope=read 進共用 registry，`specs_for` 無門面專屬排除 ⇒ (a) 模型工具清單含它可自呼遞迴 (b) 影子 `readonly_view=True` 仍看得到且它會寫 `form_sessions` ⇒ 影子污染線上 session — 處置：`ToolSpec.facade_only`，`specs_for(for_model)` 排除；2.6／4.1 加驗收（design 1.4.1）。
[P1] Origin「缺 Origin 拒」與「`/mcp` 僅 server-to-server」互相抵銷（Claude Code 不送 Origin）⇒ agent.turn 路徑封死 — 處置：三態（缺 ⇒ 放行；白名單 ⇒ 放行；非白名單 ⇒ 403），缺 Origin 只記錄不告警（design 1.4.1、tasks 1.7）。
P2：身分契約文件無擁有者（→ 1.7 交付 `docs/api/mcp-facade.md`）；tasks 表頭版本過期（→ 1.4.1）；決策 15 排序（→ 已調）；roadmap `agent-tenant-audience` 未標 M4（→ 已標）；一呼叫一列 vs 多次 LLM（→ 元件 4 明寫彙總）。
r5 八條：1–4、7、8 已處置；5 行為已處置文件補擁有者；6 Origin 反成 P1 已改。
