# b2b／b2c 資源池邏輯盤查

> 2026-09-01｜唯讀｜三個來源交叉：**契約文件 → 程式實作 → 實際流量**

## 1. 契約怎麼定義（`docs/jgb2-chat-integration.md` §1）

```text
身分            請求形狀                                   回答資源池
業者用戶 b2b    mode=b2b + target_user=property_manager    只走 JGB 系統知識（不走 SOP）
租客     b2c    mode=b2c + target_user=tenant              該業者 SOP ＋ 租客知識，比分擇優
潛在客戶        mode=b2b + target_user=prospect            售前顧問知識
```

文件 :82 明文：「`b2b`＝業者側資源池；`b2c`＝租客側。**帶錯即受眾錯位**——
租客帶成 b2b 會吃到業者知識庫」⇒ **租客走 b2c 是契約規定，不是我的假設。**

## 2. 程式怎麼實作（`services/vendor_knowledge_retriever_v2.py:63-81`）

```text
is_b2b_mode = (target_user in ['property_manager','system_admin']) or (mode == 'b2b')

b2b   business_types && {system_provider}              ← 嚴格，**無 IS NULL 放行**
      target_user IS NULL OR target_user && {該角色}
b2c   business_types IS NULL OR business_types && 該業者業態
      target_user IS NULL OR target_user && {該角色, all_users}
```

⚠️ 現有 4 個 active 業者的業態都是 `property_management` / `full_service`，
**沒有任何業者帶 `system_provider`** ⇒ b2c 情境永遠看不到 system_provider 的列。

⛔ 前案已裁：`docs/retrieval-recall-audit-20260822.md:82`
「b2b 的 `business_types && {system_provider}` 嚴格過濾是**刻意的隔離機制，勿改**」。
⇒ 本盤查**不提議動過濾器**，只指出資料歸池的問題。

## 3. 實際流量（`usage_events`，非內部）

```text
b2b / property_manager   1,321      ← 現役主力
b2b / (null)               258
b2c / tenant                21      ← **幾乎沒有流量**
b2b / prospect               6
(null) / 各種               ~44
```

⚠️ **租客通道實際上幾乎沒被使用**（21 筆，跨 2026-07-11～08-22）。
這改變優先序：b2c 側的缺口目前影響的是一條幾乎沒有人走的路。

## 4. 三者一致嗎——**一致**

契約說租客走 b2c、程式照 mode 分池、流量也確實有 b2c/tenant 事件。
⇒ 我用 `mode=b2c` 測租客題**沒有測錯情境**（不是 harness artifact）。

## 5. 所以那 80 筆的正確定性

```text
⛔ 不是    過濾器有 bug（過濾器是刻意的，前案已裁勿改）
⛔ 不是    檢索排序爛（語義相似度 0.80–0.88，換池後名次都是 1）
✅ 是      **受眾宣告與資源池歸屬不一致**：
           target_user 寫著含 tenant，business_types 卻只有 system_provider
           ⇒ 在契約定義的租客通道（b2c）裡結構上不可達
方向性     反方向（宣告給 property_manager 卻 b2b 看不到）＝ **0 筆** ⇒ 單向
最硬的證據 3441-3447、3517、3521 共 9 筆 target_user **只寫 tenant**
```

⚠️ 但契約的 b2c 池是「該業者 SOP ＋ 租客知識」——
也可能設計本意是：**JGB 平台操作知識由業者 SOP 承接，不進租客知識池**。
⇒ 這 80 筆是「錯置」還是「本來就該由 SOP 承接」，是**產品裁決**，⛔ 不是我能判的。

## 6. ⚠️ 我這次量測的兩個限制（必須揭露）

```text
① 我只量了 knowledge_base，**沒有量 SOP**。
   契約說 b2c 是「SOP ＋ 租客知識，比分擇優」⇒ 租客實際可能從 SOP 得到答案。
② 我用 vendor_id=1 測，而 **vendor 1 的 active SOP ＝ 0 筆**
   （SOP 現況：vendor 2 有 250 筆、vendor 3 有 4 筆、vendor 1／4 為 0）
⇒ 我的 b2c 結果對 **vendor 1 的租客成立**，⛔ **不得外推到 vendor 2 的租客**。
```

## 7. 給裁決用的三條路

```text
A 補業態標記   給那 80 筆的 business_types 補上業者業態 ⇒ 租客搜得到
              代價：改資料、可逆；⚠️ 但可能牴觸「平台知識由 SOP 承接」的設計本意
B 維持現狀     認定 JGB 平台操作知識就該只在 b2b；租客端由業者 SOP 負責
              代價：vendor 1／4 的租客沒有 SOP 也沒有這些知識 ⇒ 那條路是空的
C 先不動       b2c 流量僅 21 筆，優先序低；等 b2c 真的要上線再處理
              代價：缺口留著；但這是目前唯一不需要產品裁決就能選的
```
