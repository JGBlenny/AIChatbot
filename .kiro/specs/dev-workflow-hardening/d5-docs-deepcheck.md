# D5 docs 第二批：判不出 63 份逐份核對結果（2026-10-18，三位唯讀 scout）

> 業主選「先處理確定的 21 份，判不出的再核對」後派出；結果交業主，業主選「AUTO 處理，完成後派 verifier」。證據為 scout 回報的可 grep 符號＋路徑（行號只作定位，執行者改前須重新對碼）。
> 計數：依程式更正 35、刪除 3、紀錄（有日期，留）16、現行正確 7、仍判不出 2。另 4 份 README 由第二批 executor 逐份核對（見下表「四份 README」）。

## 四份 README（第二批 executor 核對後判定）

| 檔 | 判定 | 改了什麼 | 證據指令 |
|---|---|---|---|
| docs/guides/README.md | 依程式更正 | 各子目錄檔數更正、補列 `how-to-add-a-query-capability.md`、刪除檔連結改指封存 | `ls docs/guides/development` |
| docs/features/README.md | 依程式更正 | 文件總數改為本目錄 7 份＋`sop/` 5 份、刪除檔連結改指封存或移除 | `ls docs/features docs/features/sop` |
| docs/features/sop/README.md | 依程式更正（含 `agent.turn` 正對照命中） | vendors 的 `/sop/*` 路由數 10 → 13；`platform_sop` 15 支 | `grep -c '@router' rag-orchestrator/routers/platform_sop.py` |
| docs/deployment/README.md | 依程式更正 | 移除不存在的 `archive/deployment-logs/` 與版本子目錄、註明 `DEPLOY_FROM_FA4D9A6_TO_LATEST.md` 已遺失、補列 `records/` | `ls docs/deployment docs/deployment/records` |

## 刪除（描述的功能整個不存在）

| 檔 | 證據 |
|---|---|
| docs/testing/BATCH_TEST_STANDARDS.md | `batch_test_runner.sh`、`run_all_batches.sh` 全 repo 不存在；`notes LIKE 'Batch N:%'` 0 命中 |
| docs/features/knowledge-form-auto-quick-ref.md | `trigger_form_condition` 欄位已由 `rag-orchestrator/database/migrations/drop_knowledge_trigger_dead_columns.sql` 刪除；`.py` 內 0 命中；knowledge-admin 無此表單 |
| docs/guides/development/FRONTEND_USAGE_GUIDE.md | `/suggested-intents`、`/business-scope` 路由不在 `knowledge-admin/frontend/src/router.js`；`IntentSuggestionEngine`／`suggested_intents` 無符號；`POST /api/v1/chat` 無路由 |

## 依程式更正（每檔要改的點）

**docs/api**
- `loop_knowledge_api.md`：路徑改為 `/api/v1/loops` prefix＋`/loop-knowledge/...`（`routers/loop_knowledge.py`）；SOP 同步段 embedding 改為非同步 `generate_sop_embeddings_async`；「單一項目超時 30 秒」無程式依據 ⇒ 刪。
- `README.md`：「39 支端點」與實際（knowledge-admin/backend 路由裝飾器約 66 個）不符 ⇒ 改為不寫死數字或附查證指令；「只重疊 2 支」⇒ 至少 4 支（GET/POST `/api/knowledge`、PUT/DELETE `/api/knowledge/{id}`）；「15 face」⇒ 16。
- `repair-api-contract.md`：「`NotImplementedError` 占位」已不成立（`services/jgb_system_api.py` 註明 2026-08-25 改真端點 status-overview）；`emergency_status` 段已修正（`services/jgb/repairs.py`、`services/jgb/transport.py` 為 1＝非緊急／2＝緊急）。
- `KNOWLEDGE_ADMIN_API.md`：檔頭稱 `PUT`／`DELETE /api/knowledge/{id}`、`POST /api/login` 已不存在 ⇒ 前兩者存在於 `knowledge-admin/backend/app.py`；登入為 `/api/auth/login`（`routes_auth.py`）；`GET /api/knowledge` 參數改為 search／category／business_types／universal_only／limit／offset；POST body 欄位為 `question_summary`（`KnowledgeUpdate`）。
- `API_REFERENCE_KNOWLEDGE_ADMIN.md`：`/api/backtest/run|status|results` ⇒ 實為 `/api/backtest/runs...`；`/api/knowledge/{id}/intents` 無路由；`GET /api/v1/vendors` 屬 rag-orchestrator，knowledge-admin 為 `/api/vendors`；檔頭「`/api/auth/login` 查無實作」錯；`business_scope`／`vendor_ids`／`sort_by`／`order` 參數不存在。

**docs/architecture**
- `DATABASE_SCHEMA.md`：knowledge_base DDL 缺程式在用欄位（`target_user`、`business_types`、`action_type`、`api_config`、`form_id`、`trigger_mode`）；註明這些表的 CREATE 不在 repo migrations、權威 schema 需查 DB；「核心表 16 個」與自述 63 張矛盾 ⇒ 擇一並註明來源。
- `facet-architecture.md`：「共 15 個」⇒ 16（contracts 漏「合約基本資料」，見 `services/jgb/contracts.py` 的 `FACE_BUILDERS`）。

**docs/design**
- `PERMISSION_SYSTEM_DESIGN.md`：`require_permission` 程式中無定義；預設 6 角色在非 docs 檔找不到（只有 `create_admin.py` 的 super_admin）⇒ 標明為未實作的設計段。
- `PERMISSION_UI_DESIGN.md`：`PermissionManagementView`、`RoleBadge.vue`、`PermissionGuard.vue` 不存在；現有 `RoleManagementView.vue`、`RoleFormModal.vue`、`AdminManagementView.vue`、`PermissionSelector.vue`、`directives/permission.js`、`composables/usePermission.js`。

**docs/deployment**
- `DEPLOY_CHECKLIST.md`：「後端 Python 只需重啟」錯——`docker-compose.prod.yml` 的 rag-orchestrator 無原始碼掛載；knowledge-admin-api 只掛 `app.py`、`create_admin.py`、`scripts`，`routes_*.py` 改了需 `up -d --build`。
- `DEPLOY_GUIDE.md`：`docs/deployment/2026-01-10/`、`docs/deployment/版本號/` 不存在；方案 A「restart rag-orchestrator」與自身步驟表矛盾 ⇒ 改 `up -d --build`。

**docs/testing**
- `api-integration-testing-guide.md`：「系統應該觸發 API 調用」屬已刪的 `api_call_handler.py`（2026-09-11，DSP-046）⇒ 標退役；`action_type`／`api_config` 欄位仍在可保留。

**docs/knowledge**
- `outline-architecture-proposal.md`：`KNOWN_TARGET_USERS` 為 4 值（`tools/contracts/visibility.py`、`services/vendor_knowledge_retriever_v2.py`）；「pm 68 條翻成 approved」與現況（1,753 條皆 proposed）不符；標題「尚未實作」與 `canon/jgb/A–I.md` 已存在不一致。
- `jgb-domain-map.md`：§0 P0-1 講法數字為合併前快照 ⇒ 更新為現況（皆 proposed）或標快照日期。
- `agent-readable-knowledge.md`：`verifier.py:_verify_citation` ⇒ 實為 `_verify_ref`／`_ref_failures`；`_split_sentences` 在 `services/agent/provenance_units.py`。

**docs/frontend**
- `batch_review_requirements.md`：「重複警告」「duplication_warning」「similar_knowledge」「全選所有頁」未實作（frontend 0 命中）⇒ 標未實作；已實作者見 `components/review/LoopKnowledgeReviewTab.vue`、`routers/loop_knowledge.py` batch-review；補快照日期標示。

**docs 根目錄**
- `LLM_PROVIDER_MIXED_CONFIG_GUIDE.md`：`_provider_cache` 為惰性建立（`services/llm_provider.py`），非預先建三實例。
- `KB_EMBEDDING_OPTIMIZATION.md`：`scripts/knowledge_extraction/import_excel_to_kb.py`、`import_extracted_to_db.py` 不存在；「所有新增編輯會自動用新策略」不成立（`knowledge-admin/backend/app.py` 仍附加關鍵字、用 `answer[:200]` 退路）；現行單一實作為 `services/retrieval_representation.py` 的 `scoring_surface()`。
- `backtest/assistant-report-workflow.md`：jgb2 路徑 `/Users/lenny/...` 不存在 ⇒ 改為「jgb2 checkout（本機路徑依環境）」不寫死。

**docs/features**
- `PERMISSION_SYSTEM_README.md`：`require_permission`、`has_permission` 不存在（`auth_utils.py` 只有 `get_user_permissions`）。
- `AUTH_SYSTEM_README.md`：`JWT_EXPIRATION_HOURS`／`JWT_ALGORITHM` 實為常數 `ACCESS_TOKEN_EXPIRE_HOURS`、`ALGORITHM`；`ResetPasswordModal.vue`、`ADMIN_MANAGEMENT_PLAN.md`、`AUTH_IMPLEMENTATION_SUMMARY.md` 不存在；`/:vendorCode/chat` 無此路由。
- `knowledge-form-auto-option.md`（紀錄，需加標示）：`trigger_form_condition` 已刪 ⇒ 檔頭加「歷史設計案，欄位已刪」標示。

**docs/guides**
- `reference/SOP_QUICK_REFERENCE.md`：`scripts/add_pet_policy_sop.sql`、`scripts/sop_templates.sql` 實在 `database/seeds/`；`backtest_framework.py`、`docs/SOP_COMPLETE_GUIDE.md` 不存在；「意圖關聯」已棄用。
- `development/FRONTEND_DEV_MODE.md`：dev compose 無前端服務、prod 為 nginx＋dist、無 profiles；vite proxy 只有 `/rag-api`、`/api`；掛載檔為 `nginx.conf.template`。
- `development/MARKDOWN_TO_PDF_GUIDE.md`：寫死的 `/Users/lenny/...` 路徑 ⇒ 改相對路徑。
- `api/api-path-conventions.md`：`/rag-api/v1/chat|chat/stream|knowledge/classify|reload|stats|vendors/:id/chat` 無路由；`/rag-api/v1/vendors/:id/sops` ⇒ `/api/v1/vendors/{vendor_id}/sop/items`；`knowledge-export/excel` ⇒ `POST /export`；`/api/test-scenarios` ⇒ `/api/test/scenarios`；`/api/backtest/*` 列表與 `/api/knowledge/:id/intents` 不存在；nginx 片段檔名為 `knowledge-admin/frontend/nginx.conf.template`。
- `deployment/AWS_S3_VIDEO_SETUP.md`：格式另允許 `video/x-msvideo`（`routers/videos.py`）；`localhost:3000` 無映射。
- `features/PERMISSION_SYSTEM_QUICK_GUIDE.md`：權限名 `knowledge:update`／`approve`、`intent:review` 不存在（遷移有 `knowledge:edit`、`knowledge:review`、`intent:suggest`）；vendor 5、role 4（非 4、5）；後端無權限強制、只在前端。
- `getting-started/PERMISSION_QUICK_START.md`：`require_permission` 不存在。
- `deployment/AUTH_DEPLOYMENT_GUIDE.md`：`/:vendorCode/chat`、`VendorChatDemo` 不存在；公開路由只有 `/:vendorCode/form-submissions`。
- `migration/TEST_SCENARIOS_MIGRATION_GUIDE.md`：`database/init/` ⇒ `database/init-legacy/`；`migrate_excel_to_db.py`、`docs/BACKTEST_OPTIMIZATION_GUIDE.md` 不存在；collections 端點與 `test_collections` 不存在；「16 個端點」「100% 完成」不成立。
- `development/SIMPLIFICATION_IMPLEMENTATION_GUIDE.md`：`40-simplify-test-scenarios-for-llm-eval.sql` 不存在；「進行中」⇒ 已實作（`expected_answer`／`min_quality_score` 在 `routes_test_scenarios.py`）。
- `features/CACHE_SYSTEM_GUIDE.md`：快取鍵為 `rag:question:{vendor_id}:{target_user}:{config_version}:{hash}`（`services/cache_service.py`）；參數為 `target_user` 非 `user_role`；「include_debug_info 跳過快取」已隨舊鏈刪除。
- `development/KNOWLEDGE_EXTRACTION_GUIDE.md`：`scripts/knowledge_extraction/*`、`scripts/import_knowledge_batch.py` 不存在；`localhost:8200` 無映射。
- `reference/PRIORITY_QUICK_REFERENCE.md`：`PRIORITY_BOOST=0.15` 無讀者；priority 只用於 `ORDER BY kb.priority DESC`（`services/vendor_knowledge_retriever_v2.py`）；關鍵字加成在 `base_retriever.py` 的 `_apply_keyword_boost`。
- `features/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md`：`GET /api/v1/knowledge-export/export` ⇒ `POST`；「分數 ≥6/10」⇒ 只看 LLM 布林 `is_acceptable`（`knowledge_import_service.py`）。

## 紀錄（有日期，留）16 份、現行正確 7 份

紀錄：api 的 account／iot／billing／estate／g1-g4／jgb-contracts-api-spec 六份合約快照；design 的 API_CONFIGURATION_GUIDE、CORE_API_FUNCTIONS_REFERENCE、FORM_FILLING_DIALOG_DESIGN 三份殘段；frontend 的 loop_management_requirements、backtest_view_analysis；API_ENDPOINTS_COMPLETE_INVENTORY、SMART_RETRIEVAL_QUICK_REF 兩份殘段；features 的 SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE；guides 的 PGVECTOR_SETUP 殘段。（knowledge-form-auto-option 歸紀錄但需加標示，列於更正。）
現行正確：architecture 的 COMPLETE_CONVERSATION_ARCHITECTURE（§3 行號已漂，以符號為準）、BOUNDARY；user-guides/README、docs/README、docs/INDEX、chat-architecture-overview；guides 的 how-to-add-a-query-capability。

## 仍判不出（外部事實）

- docs/api/jgb_external_api_spec.md：需 jgb2 `routes/api.php` 與 controller 核對。
- docs/knowledge/jgb-product-facts.md：需在 jgb2 checkout 釘住 commit `b2ee2ac382ce` 逐條核對。
→ 列入 D4 待裁表。
