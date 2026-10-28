# 站內幫手上線後待處理問題（2026-10-15 起）

> 來源：正式機 2026-10-15 上線後實測＋`usage_events.decision_snapshot` 回合紀錄＋本機重現。本檔只列未處理的問題；已修好的（目錄完整 id、追問接回原流程、「客服」字眼、修繕入口缺欄追問、零列已審時不給 `kb.search`）與當時的量測紀錄見 `git show 720f0bf7:.kiro/specs/agentic-mcp-orchestration/issues-after-golive-20261015.md`。排序與擋不擋上線看 `HANDOFF-20261018.md` 待辦表。

## A. 我方（AIChatbot）

| 優先 | # | 問題 | 證據 | 影響 | 建議修法 |
|---|---|---|---|---|---|
| P2 | A4 | **列清單題被誤判成統計**：「列出我的合約」3 輪 1～2 次走 `jgb2.stats.*` ⇒「目前還不支援」；「幫我查一張修繕單的進度」第一句 1／3 同樣 | 正式機 2026-10-15 三輪卡片實測；之後未重測 | 能答的題回不支援 | 統計工具說明限定「統計／加總／N 個月內」語意；一般列清單走 `jgb2.query.*` |
| P3 | A5 | 驗證關 `POLARITY_MISMATCH` 退回後轉人 | 正式機 3 次 | 少量知識題 | 待查（未重現） |
| P3 | A6 | 接真 JGB 時修繕照片欄位格式不符：我方送物件陣列 `broken_photos`（`grep -n "broken_photos" rag-orchestrator/services/jgb_system_api.py`），既有 `POST /repairs` 收網址陣列 ⇒ 400 | jgb2 `RepairApiController@store` 驗證規則 | 正式機 `IMAGE_URL_ALLOWLIST` 未設、JGB 未接照片網域，目前不會觸發 | 待 JGB #22 定案；定案前接真 JGB 不送 `broken_photos` |
| P3 | A7 | 速度：每次模型呼叫約 2.3 秒、送約 13,500 token；`kb.search`（舊知識庫）中位 1.3 秒、p90 4.6 秒 | 正式機 2026-10-15 142 回合統計 | 正常查資料 5.6 秒 | 量 `kb.search` 去留與輸入縮減 |
| — | A8 | 文件：接口 A、接測清單仍是舊說法（統計新路徑、急迫程度問法），與 `jgb-api-spec-for-jgb-20261015.md` 不一致 | 2026-10-15 對碼 | 交給 JGB 會混淆 | 由維運指南那一窗改寫 |
| P3 | A10 | 知識缺「合約到期前通知」：正本無此主題（只有電錶服務到期 `jgb/G/power-meter-service-expiry`）。jgb2 有 `ContractNotifyExpiring`（Kernel 07:20，說明「30 日內將到期」）＋`ContractNotifyMoveout`（到期前 5 日點退）＋`ContractStatusUpdater` 內 `contract_notify_expiring`；`contract_expiring_by_days` 只發給房東／管理者（通知中心＋botbonnie） | jgb2 原始碼 | 問到期通知答不出 | 發送時點的比對式與說明不一致，逐支讀清後照知識線流程起草正本細目 |

## B. 等 JGB

1. 照 `jgb-api-spec-for-jgb-20261015.md` 開／改 API（統計擴充既有端點、建物件／合約／手動帳單新端點、照片上傳、四支讀取補成員過濾、`GET /estates/{id}` 放寬）與回答 §6 的 11 題（7 題擋上線）。
2. 修 `emergency_status` 對外 mapping（網頁 2＝緊急，API 標反）；給「改帳單到期日」正式路徑（`PATCH /agent/v1/bills/{id}` 在 master／preview 查無）。

## C. 業主決定／動作

1. jgb2 開場卡片改成互動句（實測 3 輪：帳單狀態 3／3、合約到期 3／3、修繕進度、報修）——在工單分支 `ticket_13290307734` 改，push 前給業主看。
2. 工具參數塞身分鍵：以程式現況「剝除」為準改接測清單，或改程式成「拒絕」。
3. 是否允許在 www 測試團隊真建一張修繕單。
4. 規格、指南、計畫、本檔等文件 commit。
