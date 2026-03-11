# AIChatbot API Endpoints - Complete Inventory

**Document Created:** 2026-02-17  
**System:** RAG Orchestrator (FastAPI)  
**Database:** PostgreSQL (asyncpg)  
**Host:** localhost:8100

---

## Table of Contents
1. [All API Endpoints](#all-api-endpoints)
2. [Lookup API Details](#lookup-api-details)
3. [API Endpoints Table Structure](#api-endpoints-table-structure)
4. [Form Integration & Action Types](#form-integration--action-types)
5. [Test Scripts & Examples](#test-scripts--examples)
6. [Sample Curl Commands](#sample-curl-commands)

---

## All API Endpoints

### Core Chat Endpoints (Prefix: `/api/v1`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/message` | Send chat message |
| GET | `/api/v1/conversations` | List conversations |
| GET | `/api/v1/conversations/{conversation_id}` | Get conversation details |
| POST | `/api/v1/conversations/{conversation_id}/feedback` | Submit feedback |
| GET | `/api/v1/test` | Test endpoint |
| POST | `/api/v1/reload` | Reload configuration |

### Intents Management (Prefix: `/api/v1`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/intents` | List all intents |
| GET | `/api/v1/intents/stats` | Intent statistics |
| GET | `/api/v1/intents/{intent_id}` | Get intent details |
| POST | `/api/v1/intents` | Create intent |
| PUT | `/api/v1/intents/{intent_id}` | Update intent |
| DELETE | `/api/v1/intents/{intent_id}` | Delete intent |
| PATCH | `/api/v1/intents/{intent_id}/toggle` | Toggle intent status |
| POST | `/api/v1/intents/reload` | Reload all intents |
| POST | `/api/v1/intents/regenerate-embeddings` | Regenerate intent embeddings |

### Knowledge Base Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/classify` | Classify knowledge (intent prediction) |
| POST | `/classify/batch` | Batch classify knowledge |
| POST | `/mark-reclassify` | Mark for reclassification |
| GET | `/stats` | Knowledge statistics |
| POST | `/reload` | Reload knowledge base |
| GET | `/health` | Knowledge system health check |

### Knowledge Import/Export (Prefix: `/api/v1`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/upload` | Upload knowledge file |
| GET | `/api/v1/jobs/{job_id}` | Get job status |
| GET | `/api/v1/jobs` | List all import jobs |
| POST | `/api/v1/preview` | Preview import file |
| POST | `/api/v1/jobs/{job_id}/confirm` | Confirm import |
| DELETE | `/api/v1/jobs/{job_id}` | Delete job |
| GET | `/api/v1/statistics` | Import statistics |

**Export Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/export` | Start export job |
| GET | `/jobs/{job_id}` | Get export job status |
| GET | `/jobs/{job_id}/download` | Download exported file |
| GET | `/jobs` | List export jobs |
| DELETE | `/jobs/{job_id}` | Delete export job |
| GET | `/statistics` | Export statistics |
| GET | `/preview` | Preview export data |

### Forms Management (Prefix: `/api/v1`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/forms` | List all forms |
| GET | `/api/v1/forms/{form_id}` | Get form details |
| POST | `/api/v1/forms` | Create form |
| PUT | `/api/v1/forms/{form_id}` | Update form |
| DELETE | `/api/v1/forms/{form_id}` | Delete form |
| GET | `/api/v1/forms/{form_id}/related-knowledge` | Get related knowledge |
| GET | `/api/v1/form-submissions` | List submissions |
| PATCH | `/api/v1/form-submissions/{submission_id}` | Update submission |

### API Endpoints Management (Prefix: `/api/v1`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/api-endpoints` | List all API endpoints |
| GET | `/api/v1/api-endpoints/{endpoint_id}` | Get endpoint details |
| POST | `/api/v1/api-endpoints` | Create endpoint |
| PUT | `/api/v1/api-endpoints/{endpoint_id}` | Update endpoint |
| DELETE | `/api/v1/api-endpoints/{endpoint_id}` | Delete endpoint |

### Lookup API (No Prefix)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/lookup` | Universal lookup query |
| GET | `/api/lookup/categories` | List lookup categories |
| GET | `/api/lookup/stats` | Lookup statistics |

### Vendors Management
| Method | Path | Description |
|--------|------|-------------|
| GET | `/vendors` | List vendors |
| POST | `/vendors` | Create vendor |
| GET | `/vendors/by-code/{vendor_code}` | Get vendor by code |
| GET | `/vendors/{vendor_id}` | Get vendor details |
| PUT | `/vendors/{vendor_id}` | Update vendor |
| DELETE | `/vendors/{vendor_id}` | Delete vendor |
| GET | `/vendors/{vendor_id}/configs` | Get vendor configs |
| PUT | `/vendors/{vendor_id}/configs` | Update vendor configs |
| GET | `/vendors/{vendor_id}/stats` | Get vendor statistics |
| GET | `/vendors/{vendor_id}/sop/categories` | List SOP categories |
| GET | `/vendors/{vendor_id}/sop/items` | List SOP items |
| PUT | `/vendors/{vendor_id}/sop/items/{item_id}` | Update SOP item |
| POST | `/vendors/{vendor_id}/sop/categories` | Create SOP category |
| POST | `/vendors/{vendor_id}/sop/items` | Create SOP item |
| DELETE | `/vendors/{vendor_id}/sop/items/{item_id}` | Delete SOP item |

### Platform SOP Management
| Method | Path | Description |
|--------|------|-------------|
| GET | `/categories` | List SOP categories |
| POST | `/categories` | Create SOP category |
| PUT | `/categories/{category_id}` | Update SOP category |
| DELETE | `/categories/{category_id}` | Delete SOP category |
| GET | `/groups` | List SOP groups |
| POST | `/groups` | Create SOP group |
| PUT | `/groups/{group_id}` | Update SOP group |
| DELETE | `/groups/{group_id}` | Delete SOP group |
| GET | `/templates` | List SOP templates |
| POST | `/templates` | Create SOP template |
| PUT | `/templates/{template_id}` | Update SOP template |
| DELETE | `/templates/{template_id}` | Delete SOP template |
| GET | `/statistics/usage` | Usage statistics |
| GET | `/templates/{template_id}/usage` | Template usage info |
| POST | `/import-excel` | Import from Excel |

### Unclear Questions Management
| Method | Path | Description |
|--------|------|-------------|
| GET | `/unclear-questions` | List unclear questions |
| GET | `/unclear-questions/{question_id}` | Get question details |
| PUT | `/unclear-questions/{question_id}` | Update question |
| DELETE | `/unclear-questions/{question_id}` | Delete question |
| GET | `/unclear-questions-stats` | Statistics |
| GET | `/unclear-questions-search` | Search questions |
| POST | `/unclear-questions-batch-update` | Batch update |

### Suggested Intents Management (Prefix: `/api/v1`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/suggested-intents` | List suggestions |
| GET | `/api/v1/suggested-intents/stats` | Statistics |
| GET | `/api/v1/suggested-intents/{suggestion_id}` | Get suggestion |
| POST | `/api/v1/suggested-intents/{suggestion_id}/approve` | Approve |
| POST | `/api/v1/suggested-intents/{suggestion_id}/reject` | Reject |
| POST | `/api/v1/suggested-intents/merge` | Merge suggestions |

### Knowledge Generation (Prefix: `/api/v1`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/test-scenarios/{scenario_id}/check-knowledge` | Check knowledge coverage |
| POST | `/api/v1/test-scenarios/{scenario_id}/generate-knowledge` | Generate knowledge |
| GET | `/api/v1/knowledge-candidates/stats` | Candidate statistics |
| GET | `/api/v1/knowledge-candidates` | List candidates |
| GET | `/api/v1/knowledge-candidates/pending` | List pending |
| GET | `/api/v1/knowledge-candidates/{candidate_id}` | Get candidate |
| PUT | `/api/v1/knowledge-candidates/{candidate_id}/edit` | Edit candidate |
| POST | `/api/v1/knowledge-candidates/{candidate_id}/review` | Review candidate |

### Document Converter
| Method | Path | Description |
|--------|------|-------------|
| POST | `/document-converter/upload` | Upload document |
| POST | `/document-converter/{job_id}/parse` | Parse document |
| POST | `/document-converter/{job_id}/convert` | Convert to Q&A |
| GET | `/document-converter/{job_id}` | Get job status |
| PUT | `/document-converter/{job_id}/qa-list` | Update Q&A list |
| POST | `/document-converter/{job_id}/estimate-cost` | Estimate AI cost |
| DELETE | `/document-converter/{job_id}` | Delete job |
| POST | `/document-converter/{job_id}/export-csv` | Export as CSV |

### Cache Management
| Method | Path | Description |
|--------|------|-------------|
| POST | `/cache/invalidate` | Invalidate cache |
| DELETE | `/cache/clear` | Clear all cache |
| GET | `/cache/stats` | Cache statistics |
| GET | `/cache/health` | Cache health check |

### Videos Management
| Method | Path | Description |
|--------|------|-------------|
| POST | `/videos/upload` | Upload video |
| DELETE | `/videos/{knowledge_id}` | Delete video |
| GET | `/videos/{knowledge_id}/info` | Get video info |
| GET | `/videos/health` | Health check |

### Business Types
| Method | Path | Description |
|--------|------|-------------|
| GET | `/business-types-config` | Get config |
| GET | `/business-types-config/{type_value}` | Get by type |
| GET | `/business-categories` | List categories |

### Lookup Table System (Prefix: `/api`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/lookup` | Query lookup data |
| GET | `/api/lookup/all` | Query all records in a category |
| GET | `/api/lookup/manage` | Management endpoint with full details |
| POST | `/api/lookup` | Create new lookup record |
| PUT | `/api/lookup/{id}` | Update lookup record |
| DELETE | `/api/lookup/{id}` | Delete single record |
| DELETE | `/api/lookup/batch` | Batch delete by vendor_id |
| POST | `/api/lookup/import` | Import business format Excel |
| GET | `/api/lookup/export` | Export to Excel |
| GET | `/api/lookup/template` | Download Excel template |
| GET | `/api/lookup/categories` | List all categories |
| GET | `/api/lookup/stats` | Get statistics |

### System Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/stats` | System statistics |

---

## Lookup API Details

### Endpoint: `/api/lookup`

**Type:** GET  
**Prefix:** None (direct `/api/lookup`)

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `category` | string | Yes | - | Lookup category ID (e.g., `billing_interval`) |
| `key` | string | Yes | - | Search key (e.g., address, license plate) |
| `vendor_id` | integer | Yes | - | Vendor ID |
| `fuzzy` | boolean | No | true | Enable fuzzy matching |
| `threshold` | float | No | 0.75 | Fuzzy match threshold (0.0-1.0) |

### Request Examples

```bash
# Exact match - precise address
curl "http://localhost:8100/api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號二樓&vendor_id=1"

# Fuzzy match - partial address (lower threshold)
curl "http://localhost:8100/api/lookup?category=billing_interval&key=新北市板橋區&vendor_id=1&fuzzy=true&threshold=0.5"

# List categories
curl "http://localhost:8100/api/lookup/categories?vendor_id=1"

# Get statistics
curl "http://localhost:8100/api/lookup/stats?vendor_id=1&category=billing_interval"
```

### Response Format

#### Success Response (Exact Match)
```json
{
  "success": true,
  "match_type": "exact",
  "category": "billing_interval",
  "key": "新北市板橋區忠孝路48巷4弄8號二樓",
  "value": "單月",
  "note": "您的電費帳單將於每【單月】寄送。",
  "fuzzy_warning": "",
  "metadata": {
    "note": "您的電費帳單將於每【單月】寄送。",
    "electric_number": "05120026123"
  }
}
```

#### Success Response (Fuzzy Match)
```json
{
  "success": true,
  "match_type": "fuzzy",
  "match_score": 0.85,
  "category": "billing_interval",
  "key": "新北市板橋區",
  "matched_key": "新北市板橋區忠孝路48巷4弄8號二樓",
  "value": "單月",
  "note": "您的電費帳單將於每【單月】寄送。",
  "fuzzy_warning": "⚠️ **注意**：您輸入的地址與資料庫記錄不完全相同（相似度 85%）\n📍 您輸入：新北市板橋區\n📍 實際匹配：**新北市板橋區忠孝路48巷4弄8號二樓**\n\n如果這不是您要查詢的地址，請提供完整正確的地址。",
  "metadata": {}
}
```

#### Ambiguous Match Response
```json
{
  "success": false,
  "error": "ambiguous_match",
  "category": "billing_interval",
  "key": "新北市三重區重陽路3段158號",
  "suggestions": [
    {
      "key": "新北市三重區重陽路3段158號一樓",
      "score": 0.98,
      "value": "單月"
    },
    {
      "key": "新北市三重區重陽路3段158號二樓",
      "score": 0.98,
      "value": "雙月"
    }
  ],
  "message": "您輸入的地址不夠完整，找到多個可能的匹配。請提供完整的地址（包含樓層等詳細資訊）。"
}
```

#### No Match Response
```json
{
  "success": false,
  "error": "no_match",
  "category": "billing_interval",
  "key": "未知地址",
  "suggestions": [
    {
      "key": "新北市三重區重陽路3段158號",
      "score": 0.45
    }
  ],
  "message": "未找到完全匹配的記錄，以下是相似選項"
}
```

#### No Data Response
```json
{
  "success": false,
  "error": "no_data",
  "category": "unknown_category",
  "message": "類別 [unknown_category] 暫無數據"
}
```

### Related Endpoints

**List Categories:**
```
GET /api/lookup/categories?vendor_id=1
```

**Get Statistics:**
```
GET /api/lookup/stats?vendor_id=1
GET /api/lookup/stats?vendor_id=1&category=billing_interval
```

### Additional Lookup Endpoints

#### Import/Export Operations

**Import Business Format Excel:**
```bash
POST /api/lookup/import?vendor_id=2
Content-Type: multipart/form-data

# Upload file with 14 sheets
curl -X POST "http://localhost:8100/api/lookup/import?vendor_id=2" \
  -F "file=@Vendor2_知識資料.xlsx"
```

**Response:**
```json
{
  "success": true,
  "message": "成功匯入 86 筆記錄",
  "total_records": 86,
  "categories": {
    "billing_interval": 5,
    "billing_method": 5,
    "parking_fee": 12
  }
}
```

**Export to Excel:**
```bash
GET /api/lookup/export?vendor_id=2

# Downloads file: Lookup_資料_vendor2_{timestamp}.xlsx
```

**Download Template:**
```bash
GET /api/lookup/template

# Downloads: Lookup匯入範本.xlsx
```

#### CRUD Operations

**Create Record:**
```bash
POST /api/lookup
Content-Type: application/json

{
  "category": "billing_interval",
  "lookup_key": "台北市大安區信義路三段125號",
  "lookup_value": "單月",
  "vendor_id": 2,
  "metadata": {"electric_number": "01190293109"},
  "note": "您的電費帳單將於每【單月】寄送。"
}
```

**Update Record:**
```bash
PUT /api/lookup/123
Content-Type: application/json

{
  "lookup_value": "雙月",
  "note": "您的電費帳單將於每【雙月】寄送。"
}
```

**Delete Record:**
```bash
DELETE /api/lookup/123
```

**Batch Delete:**
```bash
DELETE /api/lookup/batch?vendor_id=2
```

**Response:**
```json
{
  "success": true,
  "message": "成功刪除 86 筆記錄",
  "deleted_count": 86
}
```

#### Composite Key Query

For scenarios requiring two-level queries (e.g., address + parking number):

**Query Specific Item:**
```bash
GET /api/lookup?category=parking_fee&key=台北市大安區信義路三段123號&key2=B1-001&vendor_id=2
```

**Query All Items (key2="全部"):**
```bash
GET /api/lookup?category=parking_fee&key=台北市大安區信義路三段123號&key2=全部&vendor_id=2
```

**Response:**
```json
{
  "success": true,
  "match_type": "multiple",
  "category": "parking_fee",
  "key": "台北市大安區信義路三段123號",
  "results": [
    {"key2": "B1-001", "value": "3000", "note": "停車位 B1-001 的月租費用為 3000 元。"},
    {"key2": "B1-002", "value": "3500", "note": "停車位 B1-002 的月租費用為 3500 元。"}
  ],
  "count": 2
}
```

---

## Related Documentation

- **Lookup System Guide**: [docs/guides/features/LOOKUP_IMPORT_EXPORT_GUIDE.md](./guides/features/LOOKUP_IMPORT_EXPORT_GUIDE.md)
- **Frontend Component**: `knowledge-admin/frontend/src/components/VendorLookupManager.vue`
- **Backend Router**: `rag-orchestrator/routers/lookup.py`

---

## API Endpoints Table Structure

### Database Location
- **File:** `/Users/lenny/jgb/AIChatbot/database/migrations/create_api_endpoints_table.sql`
- **Table:** `api_endpoints`
- **Database:** PostgreSQL (aichatbot_admin)

### Table Schema

```sql
CREATE TABLE api_endpoints (
  id SERIAL PRIMARY KEY,
  endpoint_id VARCHAR(100) UNIQUE NOT NULL,
  endpoint_name VARCHAR(200) NOT NULL,
  endpoint_icon VARCHAR(10) DEFAULT '🔌',
  description TEXT,
  
  -- Dynamic Configuration Fields
  implementation_type VARCHAR(20) DEFAULT 'dynamic',  -- 'dynamic' or 'custom'
  api_url TEXT,                                        -- API URL with variable support
  http_method VARCHAR(10) DEFAULT 'GET',              -- GET, POST, PUT, DELETE
  request_headers JSONB DEFAULT '{}',                 -- Request headers as JSON
  request_body_template JSONB,                        -- Request body template for POST/PUT
  request_timeout INTEGER DEFAULT 30,                 -- Timeout in seconds
  param_mappings JSONB DEFAULT '[]',                  -- Parameter mapping configuration
  response_format_type VARCHAR(50) DEFAULT 'template',-- 'template', 'raw', 'custom'
  response_template TEXT,                             -- Response formatting template
  custom_handler_name VARCHAR(100),                   -- Custom handler function name
  retry_times INTEGER DEFAULT 0,                      -- Retry attempts
  cache_ttl INTEGER DEFAULT 0,                        -- Cache TTL in seconds
  
  -- Availability
  available_in_knowledge BOOLEAN DEFAULT TRUE,
  available_in_form BOOLEAN DEFAULT TRUE,
  
  -- Parameters Definition
  default_params JSONB DEFAULT '[]',
  
  -- Status
  is_active BOOLEAN DEFAULT TRUE,
  display_order INTEGER DEFAULT 0,
  vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Seed Data

**File:** `/Users/lenny/jgb/AIChatbot/database/migrations/add_lookup_api_endpoint.sql`

Initial endpoints inserted:
1. `lookup_billing_interval` - 電費寄送區間查詢 (dynamic)
2. `lookup_generic` - 通用 Lookup 查詢 (dynamic)
3. `billing_inquiry` - 帳單查詢 (custom)
4. `verify_tenant_identity` - 租客身份驗證 (custom)
5. `resend_invoice` - 重新發送帳單 (custom)
6. `maintenance_request` - 報修申請 (custom)

---

## Form Integration & Action Types

### Knowledge Base `action_type` Values

**Location:** `knowledge_base.action_type` column

Supported action types:
- `none` - No action
- `api_call` - Execute API call
- `form_then_api` - Fill form then call API
- `show_knowledge` - Show knowledge content

### Form Configuration

**Table:** `form_schemas`

```json
{
  "form_id": "billing_inquiry_form",
  "form_name": "帳單查詢表單",
  "on_complete_action": "api_call|show_knowledge|form_then_api",
  "api_config": {
    "endpoint": "lookup_billing_interval",
    "params": {
      "category": "billing_interval",
      "key": "address"
    }
  }
}
```

### API Config Structure

```python
api_config = {
    "endpoint": "lookup_billing_interval",  # Required: endpoint_id
    "params": {                              # Optional: parameter mapping
        "category": "billing_interval",
        "key": "address",
        "vendor_id": "session.vendor_id"
    },
    "response_template": "✅ 查詢成功...",  # Optional: custom response format
    "on_error": "show_suggestions"           # Optional: error handling strategy
}
```

### How Form Then API Works

1. **Form Submission** → Form data collected into `form_data`
2. **Parameter Resolution** → Variables like `{form.address}` replaced with actual form values
3. **API Execution** → Universal API Handler executes the configured API
4. **Response Processing** → Response formatted using `response_template`
5. **Result Display** → Formatted response shown to user

---

## Test Scripts & Examples

### Available Test Files

1. **Form Services Test:**
   - File: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/tests/test_form_services.py`
   - Tests form validation, state management

2. **SOP Orchestrator Tests:**
   - File: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/tests/test_sop_orchestrator.py`
   - Tests form_then_api and api_call action types

3. **Intent Manager Tests:**
   - File: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/tests/test_intent_manager.py`
   - Tests intent classification

4. **Data Import Script:**
   - File: `/Users/lenny/jgb/AIChatbot/scripts/data_import/import_billing_intervals.py`
   - Imports lookup table data

5. **Lookup Table Seeds:**
   - File: `/Users/lenny/jgb/AIChatbot/database/seeds/insert_lookup_tables_vendor1.sql`
   - 247 test records for vendor 1

### Key Service Files

**API Call Handler:**
- Location: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/api_call_handler.py`
- Executes API calls from knowledge or forms
- Supports both dynamic and custom handlers

**Universal API Handler:**
- Location: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/universal_api_handler.py`
- Implements dynamic API calling with config
- Handles parameter mapping and response formatting

**Form Manager:**
- Location: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/form_manager.py`
- Manages form lifecycle
- State transitions: COLLECTING → DIGRESSION → PAUSED → COMPLETED

---

## Sample Curl Commands

### Lookup API Examples

**1. Exact Match Query:**
```bash
curl -X GET \
  "http://localhost:8100/api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號二樓&vendor_id=1" \
  -H "Content-Type: application/json"
```

**2. Fuzzy Match with Lower Threshold:**
```bash
curl -X GET \
  "http://localhost:8100/api/lookup?category=billing_interval&key=新北市&vendor_id=1&fuzzy=true&threshold=0.5" \
  -H "Content-Type: application/json"
```

**3. List Available Categories:**
```bash
curl -X GET \
  "http://localhost:8100/api/lookup/categories?vendor_id=1" \
  -H "Content-Type: application/json"
```

**4. Get Statistics:**
```bash
curl -X GET \
  "http://localhost:8100/api/lookup/stats?vendor_id=1" \
  -H "Content-Type: application/json"
```

### API Endpoints Management

**1. List All API Endpoints:**
```bash
curl -X GET \
  "http://localhost:8100/api/v1/api-endpoints?scope=form&vendor_id=1" \
  -H "Content-Type: application/json"
```

**2. Get Specific Endpoint:**
```bash
curl -X GET \
  "http://localhost:8100/api/v1/api-endpoints/lookup_billing_interval" \
  -H "Content-Type: application/json"
```

**3. Create New Endpoint:**
```bash
curl -X POST \
  "http://localhost:8100/api/v1/api-endpoints" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint_id": "custom_lookup",
    "endpoint_name": "自訂查詢",
    "implementation_type": "dynamic",
    "api_url": "http://localhost:8100/api/lookup",
    "http_method": "GET",
    "param_mappings": [
      {
        "param_name": "category",
        "source": "static",
        "static_value": "custom_category"
      }
    ],
    "response_format_type": "template",
    "response_template": "查詢結果：{value}",
    "is_active": true
  }'
```

**4. Update Endpoint:**
```bash
curl -X PUT \
  "http://localhost:8100/api/v1/api-endpoints/lookup_billing_interval" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint_name": "更新的名稱",
    "is_active": true
  }'
```

**5. Delete Endpoint:**
```bash
curl -X DELETE \
  "http://localhost:8100/api/v1/api-endpoints/custom_lookup" \
  -H "Content-Type: application/json"
```

### Form Management

**1. Create Form with API Config:**
```bash
curl -X POST \
  "http://localhost:8100/api/v1/forms" \
  -H "Content-Type: application/json" \
  -d '{
    "form_id": "address_lookup",
    "form_name": "地址查詢",
    "fields": [
      {
        "field_name": "address",
        "field_label": "請輸入地址",
        "field_type": "text",
        "required": true
      }
    ],
    "on_complete_action": "api_call",
    "api_config": {
      "endpoint": "lookup_billing_interval"
    }
  }'
```

**2. Get Form:**
```bash
curl -X GET \
  "http://localhost:8100/api/v1/forms/address_lookup" \
  -H "Content-Type: application/json"
```

### Chat with Form/API

**1. Send Chat Message (may trigger form):**
```bash
curl -X POST \
  "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "vendor_id": 1,
    "message": "我要查詢帳單",
    "session_id": "session456"
  }'
```

### System Health & Stats

**1. Health Check:**
```bash
curl -X GET \
  "http://localhost:8100/api/v1/health" \
  -H "Content-Type: application/json"
```

**2. System Statistics:**
```bash
curl -X GET \
  "http://localhost:8100/api/v1/stats" \
  -H "Content-Type: application/json"
```

---

## Key Files Reference

| Component | File Path | Purpose |
|-----------|-----------|---------|
| Lookup Router | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/lookup.py` | Lookup API endpoints |
| API Endpoints Router | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/api_endpoints.py` | CRUD for API endpoints |
| Forms Router | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/forms.py` | Form management |
| API Call Handler | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/api_call_handler.py` | Execute API calls |
| Universal API Handler | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/universal_api_handler.py` | Dynamic API execution |
| Form Manager | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/form_manager.py` | Form lifecycle |
| Main App | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/app.py` | App setup & routing |
| API Endpoints Migration | `/Users/lenny/jgb/AIChatbot/database/migrations/create_api_endpoints_table.sql` | Table schema |
| Lookup Tables Migration | `/Users/lenny/jgb/AIChatbot/database/migrations/create_lookup_tables.sql` | Lookup data schema |
| Seed Data V1 | `/Users/lenny/jgb/AIChatbot/database/seeds/insert_lookup_tables_vendor1.sql` | Test data (247 records) |
| Seed Data V2 | `/Users/lenny/jgb/AIChatbot/database/seeds/insert_lookup_tables_vendor2.sql` | Test data for vendor 2 |

---

## Port Information

- **RAG Orchestrator:** `http://localhost:8100`
- **API Documentation:** `http://localhost:8100/docs` (Swagger UI)
- **ReDoc:** `http://localhost:8100/redoc`
- **Database:** PostgreSQL on standard postgres port (5432)

---

## Environment Variables

Key environment variables for API configuration:

```bash
# Database
DB_HOST=postgres
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# LLM Provider Configuration
LLM_PROVIDER=openai  # or anthropic, etc.
OPENAI_API_KEY=xxx
MODEL_NAME=gpt-4o-mini

# Feature Flags
ENABLE_ANSWER_SYNTHESIS=true
SYNTHESIS_THRESHOLD=0.7
SYNTHESIS_MIN_RESULTS=2
SYNTHESIS_MAX_RESULTS=3

# Server
UVICORN_RELOAD=false  # disable in production
```

---

## Quick Testing Checklist

- [ ] Test `/api/lookup` with exact address
- [ ] Test `/api/lookup` with partial address (fuzzy)
- [ ] Test `/api/lookup/categories`
- [ ] Test `/api/lookup/stats`
- [ ] List API endpoints: `/api/v1/api-endpoints`
- [ ] Create test form with API config
- [ ] Submit form and verify API call
- [ ] Check `/api/v1/health` status
- [ ] Verify database connectivity

