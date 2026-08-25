# transport 遷移盤查清單（**inventory only**）

> 2026-08-25｜語言 zh-TW｜**本檔未執行任何 OpenAI 呼叫、未改任何程式、未碰 staging／production**
> 起因：業主質問「物件／合約／帳單／IoT／發票 各種情境都驗證過了嗎」——答案是**沒有**。
> 本檔把「還沒被證的」逐端點列出來，**不是**任務、**不是**已核准的範圍擴張。

## 0. 這份檔是什麼／不是什麼

```text
是    現況盤點＋逐端點稽核成本估算＋可複用的稽核協議（M2 recipe）
不是  scope 擴張——`conversational-routing-execution` 任務 4.6 的邊界（「其餘端點不動」）未被本檔改動
不是  遷移計畫的核准；每個端點要不要做、什麼時候做，由業主逐項裁定
❌    不得因為本檔存在，就把未列入 MIGRATED_ENDPOINTS 的端點當成「快要好了」
```

## 1. 事實基準（三條可複現的 grep）

```bash
# ① transport 保真的唯一事實
grep -n "MIGRATED_ENDPOINTS" rag-orchestrator/services/jgb/transport.py     # → bills / bill_detail / contracts
# ② 仍為方法級 mock 的短路點
grep -c "if self.use_mock" rag-orchestrator/services/jgb_system_api.py       # → 25
# ③ production 端點權威
sed -n '31,172p' /Users/lenny/jgb/project/jgb_1/jgb2/routes/api.php          # external/v1 路由群（checkout: master 5eaebb7f0a）
```

## 2. 分級

```text
A  已達 transport 保真（逐鍵對照過 jgb2 原始碼）             3 個端點
B  live facet 在用、但仍方法級 mock（**盤查主體**）           11 個註冊鍵 / 9 個真端點
C  registry 有、repo 內 seed 未見面向引用                      8 個註冊鍵
D  mock 存在但 production **無對應端點**（不可遷移，屬缺口）   1＋4 個
```

⚠️ B／C 的分界只用 repo 內 `seed_*facet*.sql`。面向設定是 **DB 資料驅動、後台可編**——
`repo 內未見引用` ≠ `production 沒有在用`。要定案 C 級，必須查 production `conversational_configs`。

## 3. A 級：已證（勿重做）

| 註冊鍵 | rag 方法 | 路徑 | jgb2 | 保真依據 |
|---|---|---|---|---|
| `jgb_bills` | `get_bills` | `GET /bills` | `BillApiController@index` | 33 欄逐鍵對 `formatBill`（任務 4.4） |
| `jgb_bill_detail` | `get_bill_detail` | `GET /bills/{bill_id}` | `BillApiController@show` | 同上＋三個 production 怪癖照抄（4.5） |
| `jgb_contracts` | `get_contracts` | `GET /contracts/status-overview` | `ContractApiController@index` | M2 逐鍵對 `formatContract`＋where 條件 |

## 4. B 級：盤查主體（live facet 在用，替身未經查證）

| 註冊鍵 | rag 方法 | 路徑 | jgb2 controller@method | 使用面向（seed） | 稽核成本 |
|---|---|---|---|---|---|
| `jgb_estate_status` | `get_estate_status` | `GET /estates` | `EstateApiController@index` | estate | ✅ **已稽核**（estates-source-audit.md） |
| `jgb_estates` | `get_estates` | `GET /estates` | 同上 | repair 表單（*註1*） | ✅ **已稽核**；與上共用端點、**語義不同勿混用** |
| `jgb_estate_detail` | `get_estate_detail` | `GET /estates/{id}` | `EstateApiController@show` | estate | ✅ **已稽核** |
| `jgb_meters` | `get_meters` | `GET /meters` | `MeterApiController@index` | iot | 中（208 行／1 format） |
| `jgb_invoices` | `get_invoices` | `GET /invoices` | `InvoiceApiController@index` | billing | 中（181 行／1 format） |
| `jgb_payment_logs` | `get_payment_logs` | `GET /payment-logs` | `PaymentLogApiController@index` | billing | 中（140 行／inline 投影） |
| `jgb_team_members` | `get_team_members` | `GET /roles/{role_id}/members` | `TeamMemberApiController@members` | account | 中（203 行） |
| `jgb_member_permissions` | `get_member_permissions` | `GET /roles/{id}/members/{uid}/permissions` | `TeamMemberApiController@permissions` | account・contract | 中（同檔） |
| `jgb_tenant_registration` | `get_tenant_registration` | `GET /tenants/registration-status` | `TenantApiController@registrationStatus` | account | 低（168 行） |
| `jgb_bill_visibility` | `get_bill_visibility` | `GET /bills` | `BillApiController@index` | account | **最低——見下** |
| `jgb_create_repair` | `create_repair` | `POST /repairs` | `RepairApiController@store` | repair | **高＋寫入語義**（485 行） |

*註1*：`jgb_estates` 在 repo 的 `seed_*facet*.sql` 內**只出現在註解裡**（`seed_estate_facet_configs.sql:5`
「修繕報修表單現役鍵勿用」）。它列為 B 級的依據是 `api_call_handler.py:78` 與
`jgb_response_formatter.py:188` 兩處程式註解，**不是**設定證據——實際表單設定在 DB，須查 production 定案。

**`jgb_bill_visibility` 原判「零稽核成本」——2026-08-25 查證後撤銷**：
`_bills_index` **根本沒實作 `viewer_user_id`**。production 的圈定走
`ExternalViewerScope` → `VisibleScope::resolve` → `Bill::queryThisUser`，依 roleType
（owner／agent／biglandlord／tenant）與 `show_*` 權限旗標過濾 `owner_role_id`／
`issue_target_role_id`／`estate_id`／`contract_id`——**前兩者不在 33 欄投影內**，
權限表也不在 fixture 射程。直接刪短路只會把「捏造的看不到」換成「捏造的看得到」。
已改為：替身對 `viewer_user_id` **一律 raise**（`UnsupportedMockParameterError`），
`get_bill_visibility` 在 mock 端回降級而非 `data: []`——secondary attach 只在 success 時掛，
面向因此自然走「未確認具體資源」措辭，不再無證據地宣稱某成員看不到某張帳單。
真正要做這格，得先有 viewer 權限模型的 fixture，成本屬**中高**，不是一行。

## 5. C 級：registry 有、repo seed 未見面向引用（先查 production 設定再排序）

```text
jgb_contract_checkin  GET /contracts/{id}/checkin-eligibility  ContractCheckinApiController@show
jgb_payments          GET /payments                            PaymentApiController@index
jgb_repairs           GET /repairs                             RepairApiController@index
jgb_tenant_summary    GET /tenants/{user_id}/summary           TenantApiController@summary
jgb_invoice_logs      GET /invoice-logs                        InvoiceLogApiController@index
jgb_subscription      GET /roles/{role_id}/subscription        SubscriptionApiController@show
jgb_iot_manufacturers GET /iot-manufacturers                   IotManufacturerApiController@index
jgb_repair_categories GET /repairs/categories                  RepairApiController@categories
```

⚠️ `jgb_repair_categories` **不經 registry**：`services/jgb/repair_prefill.py:116` 直接呼叫，
   屬 live path，排序上應比其餘 C 級高。

## 6. D 級：mock 存在，但 production **沒有這支端點**（遷移在此不可能）

```text
get_tenant_contracts   ✅ **2026-08-25 改判並修復**——G1「jgb2 沒有租客視角端點」是錯的：
                       `ContractApiController@index:63-65` 就是
                       `where('to_user_id', (int) user_id)`。已改走
                       `GET /contracts/status-overview` 帶 `user_id`，移除 NotImplementedError
                       與方法級 mock；替身補上 `user_id` 過濾（內部欄位 `to_user_id`，不投影）。
                       ⚠️ 修復前：呼叫端 `repair_prefill.py:303` 吞掉例外 → production 的
                       「物件自動帶入」**靜默失效**而 mock 測試全綠。
billing_api.py ×4      billing_inquiry／verify_tenant_identity／resend_invoice／maintenance_request
                       指向 BILLING_API_BASE_URL（預設 localhost:8000）的 /api/billing/*、
                       /api/maintenance/*；**jgb2 external/v1 路由表無任何對應**。
                       **2026-08-25 逐條查證（dev DB）**：
                         · repo：除 api_registry 四行外零引用；tests/ 零引用（無測試保護）
                         · knowledge_base／vendor_sop_items／intents／api_endpoints：0 命中
                         · form_schemas：**2 筆命中且 is_active=true**——
                           `billing_inquiry_guest`（含 verify_identity_first）與 `maintenance_request`，
                           vendor_id 為 NULL＝**全業者可選**（form_manager.py:152 的
                           `vendor_id = %s OR vendor_id IS NULL`）
                         · 但兩張表的 trigger_intents（帳單查詢／查詢帳單／報修／維修申請／設備故障）
                           **在 intents 表全部不存在** → `trigger_intents @> [intent]` 永不命中
                         · knowledge_base.form_id／next_form_id／form_sessions／form_submissions
                           對這兩個 form_id 皆 **0 列**（連歷史使用都沒有）
                       ⇒ dev 判定 **unreachable**；⚠️ **production DB 未查證**（見 §10）。
                       ⚠️ 若 production 真的可觸發，後果不是「壞掉」而是**編造**：
                          USE_MOCK_BILLING_API 沒有任何 compose 宣告 → 預設 true，
                          `_mock_submit_maintenance_request` 回**隨機**單號 `MNT-######`，
                          而表單模板照樣講「✅ 報修申請已送出，報修單號：…」。
```

## 6b. 已登記缺口（**不得讀成已證**）

```text
GAP-B1  GET /bills 的 `user_id` 替身**不過濾**（production：
        whereHas('belongContract', to_user_id = user_id AND active = 1)）。
        `get_bills` 的租客情境確實會帶這個參數 ⇒ 帳單替身在租客情境下回的是**全部** fixture。
        為何不現在修：帳單 fixture 掛在合約 700100／700200，合約 fixture 只有 678／600，
        兩個 fixture 宇宙不連通；忠實實作會讓所有租客情境變 0 筆，
        而接通必須改動 **C4a 已凍結**的 fixture 值（5.x 的 covered bytes 會失效）。
        現況已由 tests/unit/api/test_bills_viewer_scope_gap_req.py 具名鎖住並標為缺口。
        ⚠️ 這是 A 級端點內部的缺口——**「已達 transport 保真」指投影與 where 條件，
           不等於每個參數都已實作**。
GAP-B2  viewer 權限圈定（viewer_user_id）無 fixture 模型；替身改為拒答。
GAP-I1  GET /invoices 的 `user_id` 替身不過濾（production 走 invoices→bills→contracts
        三張表的 whereExists）。與 GAP-B1 同源：三個 fixture 宇宙不連通。
        現況由 tests/unit/api/test_invoices_mock_fidelity_req.py 具名鎖住。
GAP-P1  payment_logs 的 `response` 欄 production **不投影**（DB 有、API 不回），
        故 services/jgb/payments.py 的原因碼分析在線上無資料可用，只能退回 note。
        要驗證那段邏輯，得先讓 jgb2 把 response 加進投影。
```

## 7. 逐端點稽核協議（M2 recipe，六步；每個端點重跑一次）

```text
① 讀 production controller 的 index/show 全文，抄出**投影鍵集合**（format* 方法逐鍵）
② 抄出**恆定 where 條件**（M2 在 contracts 抓到漏 is_newest=1）
③ 抄出**參數解析語義**（M2 抓到 contract_ids 的 PHP intval 前綴語義）
④ 抄出**過度寬鬆處**：搜尋比對欄位、模糊比對範圍（M2 抓到 keyword production 只比 title）
⑤ 抄出**分頁與排序**邊界（orderBy、total_pages／has_more）
⑥ 寫下**未涵蓋清單**：認證/權限、user_id 篩選、延遲與錯誤碼、真實資料分佈
   —— 這四類 mock 結構上證不到，只能在 R 階段（staging/real API smoke）現形
產出＝一份 `mN-<endpoint>-source-audit.md` ＋ fixtures/transport 的具名鎖定測試
```

## 8. 建議順序（依「證據價值 ÷ 成本」）

```text
1  ✅ **已完成** D 級 get_tenant_contracts（改判 G1 不存在 → 真的接上端點）
2  ✅ **已完成** B 級 jgb_bill_visibility 的**止血**（拒答取代捏造）；
      真正的 viewer 權限 fixture 仍未做，成本改判中高
3  D 級 billing_api ×4              查證後刪除，減少 4 個假綠面
4  ✅ **已完成** B 級 estate 三鍵（estates-source-audit.md）——抓到 6 處偏差並修好：
      投影外欄位 estate_room_number／keyword 連地址一起比／role_id 被寫成 echo 而非篩選／
      缺 is_open=1 恆定 where（sentinel 分支因此測不到）／分頁排序寫死／
      contract_required_fields 回 production 產不出的空 fields。
      ⚠️ estates **仍未遷入 transport**（MIGRATED_ENDPOINTS 未變），本次只對齊方法級 mock
5  ✅ **已完成** B 級 invoices ＋ payment_logs（invoices-payment-logs-source-audit.md）
      invoices：參數被忽略／排序反了／分頁寫死（投影與三組枚舉本來就對）
      payment-logs：**回應信封整個不同**——production 是 {bill_id, payments, payment_logs,
      summary}，舊 mock 回 {mapping, data, pagination}，而消費端讀 data
      ⇒ 線上這個面向一律回「查無金流日誌」。另修 bill_id 必填與兩個 production 不讀的參數。
6  ✅ **已完成** B 級 meters（iot-account-source-audit.md）——adapter 註解宣稱
      「端點無 keyword」是錯的（:41-56 有）；替身只有一列，兩條衍生規則
      （meter_type 白名單、is_poweron **三態**）從未被走到；estate_id 被忽略。
7  ✅ **已完成** B 級 team_members ＋ permissions（同上稽核檔）——keyword 比對沒實作、
      擁有者與 null character 兩種形狀缺席、abilities 只回 6/32 鍵，
      且替身憑空回了 production 沒有的 `character_name`（production 是 `character` 物件），
      而 accounts.py 正是讀那個鍵 ⇒ 線上取不到值。已修 accounts.py 改讀 character.name。
8  B 級 create_repair               寫入語義，需先定「mock 寫入」的驗收語義，留最後
9  ✅ **已完成（且改判）** 原 C 級八鍵——查 DB 後**全部是 live**，C 級不存在。
      逐一盤查見 remaining-endpoints-source-audit.md：invoice-logs 三處問題最大
      （production 只回白名單化的 response_parsed，而消費端讀 response_data ⇒ 線上取不到）；
      payments／repairs 的篩選與排序全被忽略；categories／subscription／iot-manufacturers／
      tenant-summary／checkin-eligibility 四支本來就忠實，只補測試釘住。
```

## 9. 勿違

```text
❌ 用本檔把任何端點寫進 MIGRATED_ENDPOINTS——遷移必須連同 ①–⑥ 的稽核產出一起進
❌ 以「repo seed 沒引用」宣稱某端點沒人用（設定在 DB、後台可編）
❌ 把 estate 的兩個註冊鍵當同一語義（`jgb_estates` 是修繕報修表單現役鍵）
❌ 讓任何遷移失敗 fallback 到真網路（4.3 的三態原則不因新端點而放寬）
❌ 把本檔的「成本估算」當成工時承諾——行數只是原始碼閱讀量的 proxy
```

## 10. production 端證據缺口——**已關閉**（2026-08-25 業主裁定）

> 業主聲明：**本地與線上資料相同**。故 §6 的 dev DB 查證結果直接適用於 production：
> `billing_inquiry_guest`／`maintenance_request` 兩張表單雖 `is_active=true`，
> 但其 trigger_intents 在 `intents` 表不存在 → 線上同樣**觸發不了**，
> 且 form_sessions／form_submissions 零列。
> ⇒ `refactor(billing-api)` 那筆是**純清理**，部署前**不需要**先停用表單。

⚠️ 證據性質要標清楚：這是**業主對自家環境的裁定**，不是我實測 production 的輸出。
日後若 dev／prod 出現分歧（例如線上另外建過表單或意圖），本節結論即失效，須重跑下列唯讀查詢：

```sql
SELECT form_id, form_name, is_active, vendor_id, trigger_intents
FROM form_schemas
WHERE api_config::text ~ 'billing_inquiry|verify_tenant_identity|resend_invoice|maintenance_request|verify_identity_first';

SELECT name, is_enabled FROM intents
WHERE name IN ('帳單查詢','查詢帳單','報修','維修申請','設備故障');

SELECT form_id, count(*) FROM form_sessions
WHERE form_id IN ('billing_inquiry_guest','maintenance_request') GROUP BY 1;
```

### 建議的收尾（可選，不阻擋部署）

那兩張表單會變成「active 但指向已不存在的 endpoint」的孤兒列。現在觸發不到，
但只要日後有人建一個叫「報修」或「帳單查詢」的意圖，它們就會被選中並拿到
「不支援的 API endpoint」錯誤。要斷這條路，在**同一份資料**上停用即可：

```sql
UPDATE form_schemas SET is_active = false, updated_at = now()
WHERE form_id IN ('billing_inquiry_guest', 'maintenance_request');
```
