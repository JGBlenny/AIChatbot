# 物件（Estate）領域 J/G 契約（交付 jgb2 端）

> 交付日期：2026-07-04　來源：estate-conversational-facets research.md（jgb2 真碼盤查，file:line 齊）
> 消費端一律**存在性驅動**：欄位/參數出現即自動啟用，缺失走降級——**不需與 AIChatbot 同步上版**。
> 批次上傳範圍外（使用者裁定 2026-07-04 不處理，J-E1 已撤）。
> **必要新開 API：無**——`GET /external/v1/estates`＋`/estates/{id}` 現有欄位（title/status/display_address/rent/contract_required_fields）已齊物件現況診斷全部主場景。

## 🟡 G-E1：estates API 硬過濾 is_open=1——非刊登物件完全查不到（選配升級）

| 項目 | 內容 |
|---|---|
| 現況 | index 與 show 基底查詢皆 `where('active',1)->where('is_open',1)`（EstateApiController.php:53-54、121-124）——**只回刊登中物件** |
| 對 AI 客服的限制 | 業者問「這個物件為什麼查不到/是不是被下架了/為什麼不能建約」時，**非刊登物件恰是最需要診斷的對象**，但 API 看不到——AIChatbot 只能以「刊登清單中找不到」弱信號反推（口徑紅線：不斷言已刪除），無法正面回答「它現在是未刊登還是已下架」 |
| 建議（擇一） | ① index 加選配參數（如 `include_unpublished=1`，僅對 key 白名單內的 role 生效）；② 或 show 單筆放寬 is_open 過濾（白名單內單筆查詢無枚舉風險）；③ 或回應加 `is_open` 欄位（現查得到者恆 true，僅為語義完備） |
| 消費端承諾 | 存在性驅動：參數/欄位出現即自動升級為正面判定；未升級前弱信號口徑照常上線，**不阻塞** |

## 🔵 觀察級（無需行動，供產品面評估）

1. **完整地址露出**：external estates 回應含 `address`/`full_address`（真實完整地址）與經緯度（formatEstate :228-229）。AIChatbot 消費端已自律不出口（回答只用 display_address 對外遮蔽版）；對外 API 若另有第三方訂閱者，建議產品面評估是否符合最小揭露。
2. **keyword 只搜 title**（:191-194）：AIChatbot 已用 client 端過濾（title＋display_address token 比對）解決，無需改；物件數極大（>200 筆）的團隊由我方翻頁處理。

## 消費端承諾

- 全部唯讀：AIChatbot 對物件只消費 GET（estates index/show）；建立/編輯/刊登/刪除/批次**不代操作**，只判定與指路。發 key 建議僅授 estates:read。
- 個資紅線：address/full_address/經緯度不進 AI 回答；識別與呈現只用 title/display_address/serial_id。
- status 位元由我方程式決定性轉譯（1/2/4/8；真資料已驗證互斥）；未知值不臆測。
- 「查不到」口徑紅線：不斷言已刪除，導後台物件總表確認。

## 優先序建議

G-E1（診斷體驗升級，隨排程）＞ 觀察級（隨緣）。
