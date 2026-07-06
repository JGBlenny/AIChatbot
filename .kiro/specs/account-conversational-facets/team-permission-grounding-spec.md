# 團隊權限面向 grounded 需求（交付 jgb2 端）

> 目的：讓 AI 客服能決定性回答「我的某成員為什麼看不到某張帳單/某份合約/某個物件」這類**角色權限確認**問題。
> 交付日期：2026-07-04　原則：AI 不重建 jgb2 權限邏輯（易錯且會隨你們改動漂移）——由 jgb2 給「權威判定」，AI 只轉述。
>
> **重要：角色為團隊自訂**——下文「會計」僅為舉例。團隊可自定義任意角色（`role_characters` 每個 character 不論範本或自訂都帶同一組能力旗標）。因此本需求**一律以能力旗標判定、不依賴角色名**；角色名只用於回話顯示（「你給他的『XXX』角色是只看自己經手的」）。AI 不需認得任何特定角色，對範本角色與完全自訂角色是同一套邏輯。
>
> **狀態：✅ 全數上線並收案（2026-07-04）**。JGB 已交付 T1（`GET /roles/{role_id}/members?keyword=`）＋viewer 圈定（bills/contracts 帶 `viewer_user_id`＋單筆過濾）＋permissions（32 旗標含成對 `show_owner_*`）；AIChatbot 已接完整版三跳（commit 73535d5，unit/integration/e2e 對 preview 真成員實測全綠）。以下保留為設計依據。

## 一、AI 要給業者的答案長怎樣（目標）

業者：「我的會計看不到 A 棟這張帳單，為什麼？」
AI（grounded）：
> 「你的會計角色是**只看自己經手的**（`show_owner_bill`），不是全團隊（`show_bill`）——所以他只看得到**被指派為經理人**的合約底下的帳單。這張帳單的合約沒指派給他，因此看不到。解法：把該合約指派他為經理人，或改用開全團隊可見的角色。」

要能這樣答，AI 需要兩件事：**(1) 這張帳單他到底看不看得到（權威事實）** ＋ **(2) 為什麼（角色旗標解釋）**。

## 二、AI 的決定性判定流程（三步）

```
輸入：業者說的「成員識別」（email/名字）＋「資源」（帳單編號/合約/物件）
步驟 1：成員識別 → member_user_id
步驟 2：查「該成員看不看得到這個資源」→ 權威 yes/no
步驟 3：查該成員角色的可見範圍旗標 → 解釋原因
輸出：看不到 + 原因（角色設計 or 未指派）+ 解法
```

## 三、每步需要什麼——對照你們現有能力

| 步驟 | 需要的資料 | 現況 |
|---|---|---|
| 1. 成員 → user_id | `email/名字 → 團隊成員 user_id` | ❌ **唯一真缺的一塊**（`roles/{id}/members` 現為 404） |
| 2. 看不看得到（權威） | 帶 `viewer_user_id=該成員` 查該資源在不在結果內 | ✅ **已有**（bills/contracts/estates 支援 viewer 圈定，docs/external-api-permission.md）——只要能帶單一資源 id 過濾即可 |
| 3. 原因（角色旗標） | 該成員角色的能力旗標（show_bill / show_owner_bill / show_contract / show_owner_contract / show_estate / show_owner_estate…） | ✅ **已有**（`roles/{role_id}/members/{user_id}/permissions` 回 27 旗標） |

**結論：你們只需補「步驟 1」一支，步驟 2、3 都現成。**

## 四、需要 JGB 提供的（明確清單）

### 🔴 必要（缺這個整個面向做不了）

**T1. 團隊成員查詢：email/名字 → 成員 user_id**

建議端點（照你們命名慣例）：
```
GET /api/external/v1/roles/{role_id}/members?keyword=<email 或 名字>
```
回應（一或多筆——同名多位會計要能列出讓業者選）：
```json
{ "success": true, "data": [
  { "member_user_id": 12345, "character_name": "會計", "character_id": 5,
    "match_field": "email" }   // 不需回 email/phone 明文，遮罩或省略即可
] }
```
- 授權：沿三層（key＋role 白名單＋`roles:read`），只回**該 role_id 底下的成員**（同 G-A1 防枚舉精神）。
- 個資：不必回成員 email/phone 明文；AI 只需要 `member_user_id`＋角色名做後續查詢與追問。

### 🟡 待你們確認（決定 AI 能答到多細）

**T2. 步驟 2 的「單一資源可見性」查法**——請確認下列任一可行：
- (a) `GET /bills?role_id=&viewer_user_id=&bill_id=<Y>` 帶 viewer 圈定＋單筆過濾：回得到＝看得到、回空＝看不到。**（最理想，複用現有 viewer 機制）**
- (b) 或 bills/contracts 回應本身帶**資源指派欄位**（該合約/物件的 `agent_user_ids` 經理人清單），AI 自行比對 member_user_id 是否在內。

有 (a) 或 (b) 其一，步驟 2 就成立；兩者皆無，AI 只能答「角色設計層」（步驟 3）不能答「這張**具體**歸誰」。

## 五、明文排除／邊界（同前）

- 不回成員 email/phone 明文（AI 用不到，只需 user_id＋角色名）。
- viewer_user_id 只用於「圈定可見範圍」，不外洩該成員其他個資。
- 驗證碼、密碼相關一律不開（沿既有紅線）。

## 六、AI 端承諾

- 存在性驅動：T1 未上線前，團隊權限面向維持現況（category 知識樹，答「去成員列表變更角色」），不阻斷。
- T1 上線 → AI 自動啟用「確認角色權限」grounded 分支：先追問是哪位成員（同名多位則列候選）→ 查旗標 → 解釋 + 解法。
- 全程只轉述 jgb2 的權威判定與旗標，不自行推斷權限規則。

## 七、一句話總結給 JGB

> 「確認角色權限」只缺**一支成員查詢 API（email/名字→user_id）**；權限旗標端點與 viewer 圈定你們都已上線。補了 T1，AI 就能決定性回答「你的會計為什麼看不到某帳單」。T2 請確認單一資源可見性怎麼查，決定 AI 答到「角色層」還是「這張具體資源層」。
