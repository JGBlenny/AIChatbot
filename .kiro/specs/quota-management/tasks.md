# 實作任務：quota-management

> 2026-07-06｜R1–R5｜design 6 元件｜鐵律：TDD；fail-open；chat.py 零侵入；opt-in 零回歸；內部流量不計不攔

- [x] 1. migration `add_vendor_quotas.sql`（冪等）＋quota 檢查器併入 usage_metering（QuotaState 狀態機、60s 快取、blocked 直查、count 排除 internal/blocked、fail-open、計量關閉停用）＋攔截文案/警示附註 helper（受眾分流）——unit 先紅後綠（狀態矩陣/文案分流/快取/fail-open/body 改寫含 Content-Length）
  - 需求：1.1, 1.2, 1.4, 1.5, 2.1–2.5, 3.1–3.3, 4.2, 4.3, 5.1, 5.2, 5.3
- [x] 2. middleware 擴充：進場 blocked 短路（JSONResponse 200 answer 形狀＋blocked 事件 status='blocked' 不計額度）＋出場 warn 且 pm 非串流 body 改寫——integration 活體（低額度三段 ok/warn/blocked、租客文案無商業字眼、加值即恢復、內部不受限）
  - 需求：3.1–3.3, 4.1–4.6, 2.2
- [x] 3. admin CRUD（GET/PUT/DELETE /api/usage/quotas，含 used/pct/state 供進度條）＋UsageStatsView 額度管理卡（三色進度條/inline 編輯/未管制入口）＋build
  - 需求：1.1, 1.3, 1.4, 3.4
- [x] 4. 稽核不變量 6（幽靈攔截 FAIL＋寬限燒錢 WARN）＋runbook＋收案（既有測試全綠、真打三段驗收、audit 綠）
  - 需求：5.1, 5.4, 5.5
