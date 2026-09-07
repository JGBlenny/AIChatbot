# line-bot 側情境增補（2026-09-08 業主轉貼）→ AIChatbot 觸點與處置

> 來源：line-bot-platform `chatai-repair-capture-spec.md`（線③ A–L → A–Q，驗收 12→17）、`chatai-digest-followup-spec.md`（線⑤ A–H → A–K，驗收 9→12）。兩份「既有契約沒有動」。③④⑤ 線依業主 2026-09-07 裁示**先不併 demo**；本檔只記觸點，⛔ 不改優先序。貼文於 Q 末句「這跟『描述不…」與 J「請以…」截斷，⚠️ 待補全文。

## 觸到 demo 現行工作的（4 格）

| 格 | line-bot 期望 | AIChatbot 觸點 | 處置 |
|---|---|---|---|
| **O** 只改急迫性；**值域已確認：急迫送 2、非緊急送 1** | 與 B 同：只重確認被改的那一項 | **jgb2 三處用法對碼證實 2＝緊急、1＝非緊急（DB 真值）**——line-bot 與 AIChatbot 都對；⚠️ jgb2 `Repair.php` 常數註解與 External API 列舉標籤反了（C1′ 請 JGB 修，⛔ 別照那張標籤改回來） | C1 結案、C1′ 送 JGB |
| **Q** 分類樹涵蓋不到 ⇒ 退回大類讓選、描述留空、照樣開得成單；⛔ 不為填滿分類編葉節點 | 開單 payload 允許 `category=大類節點`＋`description=""` | 寫入工具 W4 `jgb2.action.repair_create` 的 payload 契約與替身 `create_repair`／`repair_categories` 必須接受父節點分類與空描述；正本 A 粗目「看不出損壞描述留空」同一紀律 | 併入 Plan W4 驗收（加一案） |
| **N** 這戶已有未結同類單 ⇒ line-bot 進場前先 `GET /repairs`；若確認摘要能顯示「另有未結單」願多帶一欄 | 確認卡（W2 程式 render）可選欄位 `open_repairs_hint` | demo 不做；W2 卡 formatter 留可選欄位位置（不實作） | 後面要改（③ 併入時） |
| **I** 電錶追問：「餘額還能用幾天」是推算 ⇒ 硬性標明推算 | pm 正本 F／系統脈絡「數字出處」細目已有「推算要標明」規則（`number-data-provenance-rule`）；替身 meters fixture 已有 B10 餘額 | R-讀 S8#1 實跑看是否標明；未標明 ⇒ 正本電錶細目補一句定義（⛔ 不寫例子） | 本輪 R-讀 檢 |

## 純 ③④⑤ 線（demo 不碰，記下不忘）

| 格 | 要點 | AIChatbot 落點（併入時） |
|---|---|---|
| M 同名多戶 | line-bot 自己收斂成一戶再進場 ⇒ `estate_id` 永遠單一值、物件槽進場即填妥 | 契約 B1 `facet_context.estate_id: str`（非 list）；③ 進場不問物件 |
| P 一組照片兩個問題 | line-bot 不拆；面向短期做不到 ⇒ 他們上傳前提示「一次報一個問題」 | ③ 辨識回多問題時回「一次一個」訊號；不自行拆單 |
| J 點開時資料已變（清單快取 5 分鐘） | 面向查到的現況與 `facet_context` 衝突 ⇒ 以現況為準（原文截斷）；⛔ 不沿用快照數字 | ⑤ 面向：`facet_context` 只當進場提示，事實一律由 `jgb2.query.*` 現查——與現行 agent 設計一致（工具事實 > 帶入值） |
| K 同一戶問別類別 | 答得出來先答、答不出指路回清單；⛔ 不觸發 `scope_exit` | ⑤ `scope_exit` 只在「別戶」觸發；同戶跨類別走面向切換（design「中途切換」） |

## 查證
- C1 兩源：`rg -n "2=緊急|EMERGENCY_NON_STATUS|suggested_emergency" rag-orchestrator/services/image_recognition_service.py`；jgb2 `rg -n "EMERGENCY_NON_STATUS" app/Models/Repair.php`（待 JGB）。
- 推算標明規則：`rg -n "number-data-provenance-rule|推算" rag-orchestrator/canon/property_manager.md`。
