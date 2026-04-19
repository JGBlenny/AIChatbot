# Implementation Plan

- [ ] 1. Foundation — SOP/KB 分工分類邏輯
- [x] 1.1 實作 SOP/KB 分工分類函式與準則資料
  - 建立 `scripts/kb_coverage/boundary_classifier.py`：包含決策樹函式 `classify_knowledge_type(topic) -> "sop" | "kb"`
  - 在同一檔案中定義 `BOUNDARY_EXAMPLES` 常數：至少 5 組對照範例（押金、報修、管理費、合約、繳費）
  - 同時產出 `boundary_definition.md` 作為人可讀的準則文件
  - 完成後：`classify_knowledge_type()` 可被 generate_checklist.py import 使用，5 組範例通過 assert 驗證
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. 三面向知識清單盤點
- [x] 2.1 清單生成框架與資料結構
  - 建立 ChecklistItem 資料結構（id, dimension, category, sub_topic, question, target_user, business_types, suggest_api）
  - 實作 JSON 輸出框架：三份檔案，含 `"status": "draft"` 欄位
  - 業者專屬知識產出通用欄位範本（is_template=true 的結構定義）
  - 完成後：腳本可執行並產出三份格式正確的 JSON 骨架
  - _Requirements: 2.1, 2.3, 2.5_
  - _Boundary: generate_checklist.py_

- [x] 2.2 LLM 輔助子題展開
  - 一般知識（11 大類）由 LLM 輔助展開子題，每大類 5-15 個子題，使用 boundary_classifier 確認屬於 KB
  - 產業知識（8 大類）子題展開，涉及業者特定數據的子題標註 suggest_api（用途描述）
  - 每個子題標註 target_user 與 business_types
  - 完成後：三份 JSON 各有 ≥20 個子題，每個子題包含完整的 ChecklistItem 欄位
  - _Requirements: 2.2, 2.4, 2.5, 2.6_
  - _Boundary: generate_checklist.py_

- [ ] 3. 缺口分析
- [x] 3.1 實作 analyze_gaps.py
  - **前置條件**：清單 JSON 須經人工審閱後將 status 改為 `"approved"`，腳本檢查此欄位，非 approved 則拒絕執行
  - 為每個清單子題生成 embedding，與現有 KB 做 cosine similarity（閾值 0.80 視為已覆蓋）
  - 與 vendor_sop_items.item_name 做語義比對（閾值 0.85）偵測 SOP 重疊
  - 品質檢查：answer 長度 < 50 字、僅含「請洽管理師」、含行話 → 標記品質不佳
  - 發現操作流程但 SOP 未涵蓋的主題 → 寫入 sop_gap_report.json
  - 彙整 suggest_api 子題清單到 gap_report.json 的 suggest_api_topics 欄位
  - 產出 gap_report.json 與 sop_gap_report.json
  - 完成後：gap_report.json 包含三面向覆蓋率統計 + suggest_api_topics 清單
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - _Boundary: analyze_gaps.py_

- [x] 3.2 實作 apply_deactivations.py
  - 讀取 gap_report.json 的 deactivated_kb 清單
  - 預設 --dry-run 模式顯示影響範圍（筆數、KB ID、question_summary、停用原因）
  - 需明確加 --execute 旗標才執行 `UPDATE knowledge_base SET is_active = false`
  - 完成後：dry-run 正確顯示待停用清單；--execute 正確停用並輸出摘要
  - _Requirements: 3.3, 3.6_
  - _Boundary: apply_deactivations.py_

- [ ] 4. KnowledgeGenerator 擴充
- [x] 4.1 擴充 category 指派、scope 設定與 template 支援
  - 從 gap metadata 讀取 dimension（general/industry），寫入回傳 dict 的 category 欄位
  - scope 從 metadata 讀取（global/vendor），寫入回傳 dict
  - 在生成 prompt 中加入 category context，讓 LLM 區分一般知識 vs 產業知識
  - 當 scope=vendor 時設定 is_template=true，掃描 answer 中的 `{{...}}` 佔位符組裝 template_vars
  - 在 `_save_to_database()` 中將 category、scope、is_template、template_vars 存入 loop_generated_knowledge
  - 完成後：生成的 KB 包含正確的 category/scope；scope=vendor 的 KB 包含 is_template 和 template_vars
  - _Requirements: 4.2, 4.6_
  - _Boundary: KnowledgeGenerator_

- [ ] 5. 審核同步擴充
- [x] 5.1 擴充 loop_knowledge.py 同步邏輯
  - 同步 INSERT 語句新增欄位：category, scope, is_template, template_vars
  - 從 loop_generated_knowledge 讀取這些欄位值寫入 knowledge_base
  - source_type 固定填入 'ai_generated'，generation_metadata 記錄 loop_id 與 iteration
  - 完成後：審核通過的 KB 同步到 knowledge_base 後，category/scope/is_template/template_vars 正確填入
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  - _Boundary: loop_knowledge.py_

- [ ] 6. 批量生成腳本
- [x] 6.1 實作 generate_kb_batch.py
  - 讀取 gap_report.json 的 kb_gaps 清單
  - 為每筆缺口建立 gap 結構（符合 KnowledgeGenerator 輸入格式），設定 category/scope metadata
  - 生成前檢查 loop_generated_knowledge 是否已有相同 question 的 pending 項目（冪等性）
  - 呼叫 KnowledgeGenerator.generate_knowledge() 批量生成，使用 tenacity 重試處理 API 限流
  - 完成後：gap_report 中的 kb_gaps 全數生成為 loop_generated_knowledge（status=pending），含正確的 category/scope
  - _Depends: 3.1, 3.2, 4.1_
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - _Boundary: generate_kb_batch.py_

- [ ] 7. 回測驗證
- [ ] 7.1 實作 run_coverage_backtest.py
  - 呼叫 AsyncBacktestFramework 執行回測（不修改框架本身）
  - 回測完成後用 source_ids join knowledge_base（scope, category）做面向分組統計
  - 面向判定：scope=global + category=general → 一般知識；scope=global + category=industry → 產業知識；scope=vendor → 業者專屬知識
  - 失敗分類：無命中 → missing_kb、有 KB 但 confidence < 0.60 → poor_quality、有 SOP 無 KB → should_be_sop、超時 → system_error
  - LLM 品質判定：沿用 detailed 模式 1-5 分，報告層轉換三級制（平均 ≥ 4.0=yes、≥ 2.5=partial、其他=no）
  - 額外統計 suggest_api 子題中的 fail 數量，供後續評估是否新增 api_endpoints
  - 產出回測報告 JSON（overall + by_dimension + failure_analysis + comparison + suggest_api_fail_count）
  - 完成後：回測報告包含三面向分別的 pass_rate 且數值加總等於整體
  - _Depends: 5.1_
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  - _Boundary: run_coverage_backtest.py_

- [ ] 8. 端到端驗證
- [ ] 8.1 端到端流程驗證
  - 執行完整流程：generate_checklist → 人工確認清單（status=approved）→ analyze_gaps → apply_deactivations --dry-run → generate_kb_batch → 批量審核 → run_coverage_backtest
  - 驗證回測 pass_rate 相比基準值有改善
  - 驗證 sop_gap_report.json 產出且格式正確
  - 驗證 suggest_api_topics 清單正確彙整
  - 完成後：端到端流程無錯誤完成，回測報告顯示覆蓋率提升
  - _Depends: 6.1, 7.1_
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

## Implementation Notes
- loop_generated_knowledge 表目前缺少 category、is_template、template_vars 欄位，需在 task 6.1 執行前建立 migration（ALTER TABLE ADD COLUMN）

---

## Phase 2：知識生成修正（2026-04-19 Review 後新增）

### 背景
Loop 190（工單主題 41 筆）生成方法失敗：把工單標題直接丟 GPT 生成 Q&A，跳過了理解實際對話流程的步驟。大多數工單主題是排查型問題（用戶問具體案例，需查 API），不該做成靜態知識。客服 QA Excel 12 個分頁中只用了 3 個。

### 資料來源
- 客服 QA Excel：`/Users/lenny/jgb/5.3.4_客服_ QA, FB, 來電 (1).xlsx`
- 工單 Excel：`/Users/lenny/jgb/export_1776587150.xlsx`（僅作參考，不作為知識來源）

- [ ] 9. 清理舊知識
- [x] 9.1 Reject loop 187 + 190 全部
  - loop 187（239 筆）+ loop 190（41 筆）全部 status 改為 rejected
  - 這些知識不合格，Phase 2 會重新釐清並產生符合的知識
  - 完成後：loop 187 + 190 無任何 pending 項目

- [ ] 10. 客服 QA Excel 完整分析
- [x] 10.1 分析 A.客戶回饋分頁（實際 679 rows）
  - 產出 `customer_feedback_analysis.json`，含分類統計、處置判斷、api_interpretation_knowledge
  - _Boundary: scripts/kb_coverage/_

- [x] 10.2 分析其他未利用分頁
  - 產出 `other_sheets_analysis.json`
  - 結論：C-1 要匯入（45 筆標準回覆）、C-3 部分價值（3-4 筆）、QA-old 不需處理、B 不需處理

- [ ] 11. 靜態知識生成
- [x] 11.1 整理靜態知識主題清單
  - 從 A.客戶回饋識別反覆出現的主題，同時參考 C-1.QA回覆的標準回覆作為知識內容來源
  - 補充 C-3.直客常見QA 中租客視角的知識
  - 列出每筆知識的主題、內容來源、預計寫法
  - **產出清單交由人工 review，確認方向後才進入 11.2**
  - _Depends: 10.1, 10.2_

- [x] 11.2 生成靜態知識
  - loop_id=192, id 3468-3501, 34 筆已審核通過並同步到 knowledge_base（kb id 3327-3360）
  - business_types=system_provider, category 按主題分類（合約操作/帳務管理/金流收款/帳號與驗證/IOT設備/系統設定/租賃契約與法規）
  - 修正 knowledge_generation.py 同步路徑：補上 business_types/target_user/category/scope 等欄位
  - _Depends: 11.1 review 通過_

- [ ] 12. API 狀態解讀知識
- [x] 12.1 整理 API 狀態解讀知識清單
  - 列出 10.1 標記為 `api_query` 的所有問題類型（8 個 A1-A8）
  - 比對現有 api_endpoints 表和 api_call_handler.py 中的 api_registry，找出 API 缺口（2 個：電表/IOT、通知發送紀錄）
  - 盤點每個 API 回傳狀態的解讀方式（22 條解讀知識 IK-01~IK-22）
  - 產出 `scripts/kb_coverage/api_interpretation_checklist.json`
  - **產出清單交由人工 review，確認後才進入 12.2**
  - _Depends: 10.1_

- [ ] 12.2 JGB API 整合（持續性任務）

  ### 相關檔案
  | 檔案 | 用途 |
  |---|---|
  | `scripts/kb_coverage/api_interpretation_checklist.json` | API 規格需求 + 解讀邏輯（給 JGB 團隊看） |
  | `scripts/kb_coverage/api_interpretation_entries.json` | 知識條目 + 表單定義（寫入 DB 的來源） |
  | `scripts/kb_coverage/insert_api_knowledge.py` | 知識 + 表單寫入 DB 腳本 |
  | `rag-orchestrator/services/jgb_system_api.py` | JGB API client（mock / real 切換） |
  | `rag-orchestrator/services/jgb_response_formatter.py` | JGB 回應格式化（獨立於 api_call_handler） |
  | `knowledge-admin/frontend/src/views/ChatTestView.vue` | B2B 測試介面（有 role_id/user_id 欄位） |
  | `jgb2/docs/api/client-guide.md` | JGB API 慣例（認證/格式/限流） |

  ### 已建立的知識 & 表單
  | form_id | kb_id | 場景 | 測試狀態 |
  |---|---|---|---|
  | jgb_bill_query (31) | 3361 | 帳單狀態查詢 | 已通過 |
  | jgb_invoice_query (32) | 3362 | 發票狀態查詢 | 待測 |
  | jgb_contract_query (33) | 3363 | 合約狀態查詢 | 待測 |
  | jgb_checkin_query (34) | 3364 | 點交資格查詢 | 待測 |
  | jgb_repair_query (35) | 3365 | 修繕進度查詢 | 待測 |
  | jgb_payment_query (36) | 3366 | 繳費紀錄查詢 | 待測 |
  | jgb_tenant_query (37) | 3367 | 租客資訊查詢 | 待測 |

  ### 已知問題 & 待改善
  - 回應只列出資料，缺少狀態解讀建議（如「逾期→建議盡快繳費」）
  - 回傳所有資料，未依用戶輸入的關鍵字過濾
  - 跨 API 交叉判斷尚未實作（如「發票沒開」需查帳單+合約）
  - 表單只收 ID/標題，用戶可能只知道月份或物件名稱
  - business_types 必須包含 full_service + property_management（否則被過濾）
  - 表單觸發需要 session_id（前端 chat-test 已有，JGB 嵌入端待確認）

  ### JGB 團隊待確認
  - 帳單 bit_status 完整清單（目前假設 2/16/64）
  - 合約 bit_status 完整清單（目前假設 8/1024）
  - API 認證方式（假設 X-API-Key）
  - 回傳是否帶 status_label
  - 資料權限範圍（role_id + user_id 的查詢邊界）
  - API 開發排程

  ### 變更紀錄
  - 2026-04-19: 建立 mock（對齊 client-guide）、7 表單+知識、formatter、chat-test B2B 欄位、帳單查詢端到端測試通過
