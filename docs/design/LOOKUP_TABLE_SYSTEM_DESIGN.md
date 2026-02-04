# 📊 Lookup Table System 設計文檔

**文檔版本**: v1.0
**創建日期**: 2026-02-04
**作者**: AI Chatbot Development Team
**狀態**: 📝 規劃中

---

## 📋 目錄

1. [系統概述](#系統概述)
2. [業務場景](#業務場景)
3. [架構設計](#架構設計)
4. [數據庫設計](#數據庫設計)
5. [API 設計](#api設計)
6. [對話流程設計](#對話流程設計)
7. [實現步驟](#實現步驟)
8. [測試計劃](#測試計劃)
9. [部署計劃](#部署計劃)
10. [FAQ](#faq)

---

## 🎯 系統概述

### 問題背景

用戶提供了一個 Excel 文件（`data/全案場電錶.xlsx`），包含 309 筆電錶資料：
- **物件地址**: 各案場的地址
- **寄送區間**: 單月 或 雙月
- **電號**: 電錶號碼

用戶希望在聊天系統中實現：
```
用戶: 電費怎麼繳？
系統: 請提供您的地址
用戶: 新北市板橋區忠孝路48巷4弄8號二樓
系統: 您的電費帳單於【雙月】寄送
```

### 設計目標

1. ✅ **通用性**: 不僅限於電費查詢，可擴展到任何「鍵值對」查詢場景
2. ✅ **易維護**: 透過數據庫配置，無需修改代碼
3. ✅ **智能匹配**: 支持模糊匹配，提升用戶體驗
4. ✅ **高性能**: 使用索引優化查詢速度
5. ✅ **可擴展**: 支持多個業者、多個查詢類別

---

## 💼 業務場景

### 場景 1: 電費寄送區間查詢

**觸發條件**: 用戶詢問「電費怎麼繳」、「帳單什麼時候寄」等

**處理流程**:
1. 匹配知識庫（`action_type='form_then_api'`）
2. 彈出表單收集地址
3. 調用 Lookup API 查詢寄送區間
4. 返回格式化結果

**數據來源**: `data/全案場電錶.xlsx`

### 場景 2: 其他可擴展場景

| 場景 | 查詢鍵 | 查詢值 | 類別 ID |
|-----|--------|--------|---------|
| 電費寄送區間 | 地址 | 單月/雙月 | `billing_interval` |
| 物業管理員查詢 | 社區名稱 | 管理員姓名、電話 | `property_manager` |
| 停車位查詢 | 車牌號碼 | 停車位編號 | `parking_slot` |
| 垃圾收集時間 | 地址 | 收集時間 | `garbage_schedule` |
| 公設預約狀態 | 設施名稱 + 日期 | 可用/已預約 | `facility_booking` |

---

## 🏗️ 架構設計

### 整體架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                         用戶對話                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   知識庫系統 (Knowledge Base)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ vendor_knowledge_base                                 │   │
│  │ - question: "電費怎麼繳"                               │   │
│  │ - action_type: "form_then_api"                       │   │
│  │ - form_schema_id: 201 (地址收集表單)                  │   │
│  │ - api_config: {...}                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   表單系統 (Form System)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ form_schemas (id=201)                                │   │
│  │ - form_name: "地址收集表單"                            │   │
│  │ - fields: [{"name": "address", ...}]                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    【表單收集完成】
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              API 調用處理器 (API Call Handler)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ APICallHandler                                       │   │
│  │   ↓                                                  │   │
│  │ UniversalAPICallHandler                             │   │
│  │   - 解析 api_config                                  │   │
│  │   - 動態參數替換                                      │   │
│  │   - 執行 HTTP 請求                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Lookup API Service                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ GET /api/lookup?category=billing_interval&key=地址    │   │
│  │                                                      │   │
│  │ 功能:                                                 │   │
│  │ 1. 精確匹配                                           │   │
│  │ 2. 模糊匹配 (difflib.get_close_matches)              │   │
│  │ 3. 返回結果或建議                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   數據存儲 (Database)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ lookup_tables                                        │   │
│  │ ┌─────────────┬──────────────┬───────┬────────────┐  │   │
│  │ │ category    │ lookup_key   │ value │ metadata   │  │   │
│  │ ├─────────────┼──────────────┼───────┼────────────┤  │   │
│  │ │ billing_... │ 新北市板橋... │ 雙月   │ {...}      │  │   │
│  │ │ billing_... │ 台北市大安... │ 單月   │ {...}      │  │   │
│  │ └─────────────┴──────────────┴───────┴────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ api_endpoints                                        │   │
│  │ - endpoint_id: "lookup_billing_interval"            │   │
│  │ - api_url: "http://localhost:8100/api/lookup"      │   │
│  │ - implementation_type: "dynamic"                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 核心組件

#### 1. Lookup API Service
- **路徑**: `/rag-orchestrator/routers/lookup.py` (新建)
- **功能**: 處理查詢請求，支持精確和模糊匹配
- **依賴**: asyncpg, difflib

#### 2. UniversalAPICallHandler
- **路徑**: `/rag-orchestrator/services/universal_api_handler.py` (已存在)
- **功能**: 動態調用 API，無需為每個 API 寫函數
- **支持**: 內部 API 和外部 API

#### 3. Lookup Tables
- **表名**: `lookup_tables`
- **用途**: 存儲所有鍵值對數據
- **特點**: 支持多租戶、多類別

---

## 🗄️ 數據庫設計

### 1. lookup_tables 表

```sql
CREATE TABLE lookup_tables (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    category VARCHAR(100) NOT NULL,           -- 類別 ID (如 billing_interval)
    category_name VARCHAR(200),               -- 類別顯示名稱 (如 "電費寄送區間")
    lookup_key TEXT NOT NULL,                 -- 查詢鍵 (如地址)
    lookup_value TEXT NOT NULL,               -- 查詢值 (如 "雙月")
    metadata JSONB DEFAULT '{}',              -- 額外數據 (如電號、備註)
    is_active BOOLEAN DEFAULT true,           -- 是否啟用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 索引優化
    CONSTRAINT unique_vendor_category_key
        UNIQUE(vendor_id, category, lookup_key)
);

-- 建立索引
CREATE INDEX idx_lookup_category ON lookup_tables(vendor_id, category, is_active);
CREATE INDEX idx_lookup_key_gin ON lookup_tables USING gin(lookup_key gin_trgm_ops);
```

**關鍵設計點**:
- `category`: 使用字符串 ID 而非數字，提高可讀性
- `metadata`: JSONB 格式，靈活存儲額外信息
- GIN 索引: 支持模糊查詢（需要 pg_trgm 擴展）
- 唯一約束: 防止重複數據

### 2. api_endpoints 配置

```sql
INSERT INTO api_endpoints (
    endpoint_id,
    endpoint_name,
    implementation_type,
    api_url,
    http_method,
    param_mappings,
    response_format_type,
    response_template,
    is_active
) VALUES (
    'lookup_billing_interval',
    '電費寄送區間查詢',
    'dynamic',
    'http://localhost:8100/api/lookup',
    'GET',
    '[
        {
            "param_name": "category",
            "source": "static",
            "static_value": "billing_interval",
            "required": true
        },
        {
            "param_name": "key",
            "source": "form",
            "source_key": "address",
            "required": true
        },
        {
            "param_name": "vendor_id",
            "source": "session",
            "source_key": "vendor_id",
            "required": true
        }
    ]'::jsonb,
    'template',
    '✅ 查詢成功

📬 **寄送區間**: {value}
💡 您的電費帳單將於每【{value}】寄送。

{metadata.note}',
    true
);
```

### 3. form_schemas 配置

```sql
INSERT INTO form_schemas (
    vendor_id,
    form_name,
    form_description,
    fields,
    submit_behavior,
    is_active
) VALUES (
    1,  -- vendor_id
    '地址收集表單',
    '請提供您的地址以查詢電費寄送資訊',
    '[
        {
            "name": "address",
            "label": "地址",
            "type": "text",
            "required": true,
            "placeholder": "例如：新北市板橋區忠孝路48巷4弄8號二樓",
            "validation": {
                "minLength": 5,
                "pattern": "^.{5,}$"
            },
            "help_text": "請輸入完整地址，包含縣市、區、路名、門牌號"
        }
    ]'::jsonb,
    'api_call',
    true
);
```

### 4. vendor_knowledge_base 配置

```sql
INSERT INTO vendor_knowledge_base (
    vendor_id,
    question,
    answer,
    action_type,
    form_schema_id,
    api_config,
    trigger_mode,
    category,
    tags
) VALUES (
    1,
    '電費怎麼繳',
    '為了查詢您的電費寄送資訊，我需要知道您的地址。',
    'form_then_api',
    201,  -- 地址收集表單 ID
    '{
        "endpoint": "lookup_billing_interval",
        "combine_with_knowledge": true
    }'::jsonb,
    'manual',
    'billing',
    ARRAY['電費', '帳單', '繳費', '寄送區間']
);
```

---

## 🔌 API 設計

### Lookup API Endpoint

#### 請求

```http
GET /api/lookup?category={category}&key={key}&vendor_id={vendor_id}
```

**參數**:
| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `category` | string | ✅ | 查詢類別 ID (如 `billing_interval`) |
| `key` | string | ✅ | 查詢鍵 (如地址) |
| `vendor_id` | integer | ✅ | 業者 ID |
| `fuzzy` | boolean | ❌ | 是否啟用模糊匹配（默認 true） |
| `threshold` | float | ❌ | 模糊匹配閾值 0-1（默認 0.6） |

#### 響應

**成功 - 精確匹配**:
```json
{
    "success": true,
    "match_type": "exact",
    "category": "billing_interval",
    "key": "新北市板橋區忠孝路48巷4弄8號二樓",
    "value": "雙月",
    "metadata": {
        "electric_number": "12345678",
        "note": "每逢雙月 5 號寄送"
    }
}
```

**成功 - 模糊匹配**:
```json
{
    "success": true,
    "match_type": "fuzzy",
    "match_score": 0.85,
    "category": "billing_interval",
    "key": "新北市板橋區忠孝路48巷4弄8號2樓",
    "matched_key": "新北市板橋區忠孝路48巷4弄8號二樓",
    "value": "雙月",
    "metadata": {
        "electric_number": "12345678"
    }
}
```

**失敗 - 未找到**:
```json
{
    "success": false,
    "error": "no_match",
    "category": "billing_interval",
    "key": "台北市信義區信義路五段7號",
    "suggestions": [
        {
            "key": "台北市信義區信義路五段1號",
            "score": 0.75
        },
        {
            "key": "台北市信義區信義路四段7號",
            "score": 0.70
        }
    ],
    "message": "未找到完全匹配的地址，以下是相似地址"
}
```

**錯誤 - 參數錯誤**:
```json
{
    "success": false,
    "error": "invalid_params",
    "message": "缺少必要參數: category"
}
```

---

## 🗣️ 對話流程設計

### 完整對話流程

```
階段 1: 用戶提問
────────────────────────────────────────────────
用戶: 電費怎麼繳？

系統處理:
  1. RAG 檢索匹配知識庫
  2. 找到 action_type='form_then_api' 的知識
  3. 判斷需要收集表單

系統回應:
  為了查詢您的電費寄送資訊，我需要知道您的地址。

  📋 請填寫以下資訊：

  1️⃣ 地址: _____________
     (例如：新北市板橋區忠孝路48巷4弄8號二樓)


階段 2: 用戶填寫表單
────────────────────────────────────────────────
用戶: 新北市板橋區忠孝路48巷4弄8號二樓

系統處理:
  1. 驗證表單輸入
  2. 表單完成 ✅
  3. 觸發 API 調用
     - APICallHandler.execute_api_call()
     - UniversalAPICallHandler.execute_api_call()
  4. 調用內部 Lookup API
     GET /api/lookup?category=billing_interval&key=新北市...
  5. 數據庫查詢 (精確匹配成功)
  6. 格式化響應

系統回應:
  ✅ 查詢成功

  📬 **寄送區間**: 雙月
  💡 您的電費帳單將於每【雙月】寄送。

  每逢雙月 5 號寄送

  ---

  為了查詢您的電費寄送資訊，我需要知道您的地址。


階段 3: 後續互動（可選）
────────────────────────────────────────────────
用戶: 如果沒收到怎麼辦？

系統處理:
  1. RAG 檢索相關知識
  2. 返回未收到帳單的處理方式
```

### 模糊匹配場景

```
用戶: 新北市板橋區忠孝路48巷4弄8號2樓  (輸入 "2樓" 而非 "二樓")

系統處理:
  1. 精確匹配失敗
  2. 啟用模糊匹配
  3. 找到相似度 0.95 的地址
  4. 返回匹配結果

系統回應:
  ✅ 查詢成功（模糊匹配）

  📬 **寄送區間**: 雙月
  💡 您的電費帳單將於每【雙月】寄送。

  🔍 匹配地址: 新北市板橋區忠孝路48巷4弄8號二樓
  (與您輸入的地址相似度: 95%)
```

### 未匹配場景

```
用戶: 台北市信義區信義路五段999號

系統處理:
  1. 精確匹配失敗
  2. 模糊匹配無符合閾值結果
  3. 返回建議

系統回應:
  ⚠️ 未找到完全匹配的地址

  以下是相似地址，請確認是否為以下地址：

  1. 台北市信義區信義路五段1號 (相似度: 75%)
  2. 台北市信義區信義路四段999號 (相似度: 70%)

  請重新輸入完整地址，或聯繫客服協助查詢。
```

---

## 🛠️ 實現步驟

### Phase 1: 數據庫準備 (預計 1 小時)

#### 1.1 創建 lookup_tables 表

**文件**: `database/migrations/create_lookup_tables.sql`

```sql
-- 啟用 pg_trgm 擴展（支持模糊查詢）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 創建表
CREATE TABLE IF NOT EXISTS lookup_tables (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    category_name VARCHAR(200),
    lookup_key TEXT NOT NULL,
    lookup_value TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_vendor_category_key
        UNIQUE(vendor_id, category, lookup_key)
);

-- 建立索引
CREATE INDEX idx_lookup_category
    ON lookup_tables(vendor_id, category, is_active);

CREATE INDEX idx_lookup_key_gin
    ON lookup_tables USING gin(lookup_key gin_trgm_ops);

-- 添加註釋
COMMENT ON TABLE lookup_tables IS 'Lookup Table System - 通用鍵值對查詢表';
COMMENT ON COLUMN lookup_tables.category IS '類別 ID (如 billing_interval)';
COMMENT ON COLUMN lookup_tables.lookup_key IS '查詢鍵 (如地址)';
COMMENT ON COLUMN lookup_tables.lookup_value IS '查詢值 (如單月/雙月)';
```

#### 1.2 配置 api_endpoints

**文件**: `database/migrations/add_lookup_api_endpoint.sql`

```sql
INSERT INTO api_endpoints (
    endpoint_id,
    endpoint_name,
    implementation_type,
    api_url,
    http_method,
    param_mappings,
    response_format_type,
    response_template,
    is_active
) VALUES (
    'lookup_billing_interval',
    '電費寄送區間查詢',
    'dynamic',
    'http://localhost:8100/api/lookup',
    'GET',
    '[
        {
            "param_name": "category",
            "source": "static",
            "static_value": "billing_interval",
            "required": true
        },
        {
            "param_name": "key",
            "source": "form",
            "source_key": "address",
            "required": true
        },
        {
            "param_name": "vendor_id",
            "source": "session",
            "source_key": "vendor_id",
            "required": true
        }
    ]'::jsonb,
    'template',
    '✅ 查詢成功

📬 **寄送區間**: {value}
💡 您的電費帳單將於每【{value}】寄送。',
    true
) ON CONFLICT (endpoint_id) DO UPDATE SET
    endpoint_name = EXCLUDED.endpoint_name,
    api_url = EXCLUDED.api_url,
    param_mappings = EXCLUDED.param_mappings,
    response_template = EXCLUDED.response_template,
    updated_at = CURRENT_TIMESTAMP;
```

### Phase 2: 數據導入 (預計 30 分鐘)

#### 2.1 Excel 數據轉換腳本

**文件**: `scripts/data_import/import_billing_intervals.py`

```python
#!/usr/bin/env python3
"""
從 Excel 導入電費寄送區間數據到 lookup_tables
"""

import pandas as pd
import asyncpg
import asyncio
import os

async def import_data():
    # 讀取 Excel (相對於項目根目錄)
    excel_file = 'data/全案場電錶.xlsx'
    df = pd.read_excel(excel_file)

    print(f"📊 讀取 Excel 文件: {excel_file}")
    print(f"📊 共 {len(df)} 筆記錄")

    # 連接數據庫
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='aichatbot_admin',
        user='aichatbot',
        password='aichatbot_password'
    )

    try:
        # 清空舊數據（可選）
        await conn.execute("""
            DELETE FROM lookup_tables
            WHERE category = 'billing_interval'
        """)
        print("🗑️  清空舊數據")

        # 插入數據
        inserted = 0
        skipped = 0

        for idx, row in df.iterrows():
            address = str(row['物件地址']).strip()
            interval = str(row['寄送區間:單月/雙月']).strip()
            electric_number = str(row.get('電號', '')).strip()

            # 驗證數據
            if not address or address == 'nan':
                skipped += 1
                continue

            if interval not in ['單月', '雙月']:
                print(f"⚠️  行 {idx+2}: 寄送區間無效 [{interval}]")
                skipped += 1
                continue

            # 準備 metadata
            metadata = {}
            if electric_number and electric_number != 'nan':
                metadata['electric_number'] = electric_number

            # 插入數據庫
            try:
                await conn.execute("""
                    INSERT INTO lookup_tables (
                        vendor_id, category, category_name,
                        lookup_key, lookup_value, metadata, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (vendor_id, category, lookup_key)
                    DO UPDATE SET
                        lookup_value = EXCLUDED.lookup_value,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    1,  # vendor_id
                    'billing_interval',
                    '電費寄送區間',
                    address,
                    interval,
                    metadata,
                    True
                )
                inserted += 1

                if (inserted % 50) == 0:
                    print(f"⏳ 已插入 {inserted} 筆...")

            except Exception as e:
                print(f"❌ 行 {idx+2} 插入失敗: {e}")
                skipped += 1

        print(f"\n✅ 導入完成!")
        print(f"   - 成功插入: {inserted} 筆")
        print(f"   - 跳過: {skipped} 筆")

        # 驗證數據
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM lookup_tables
            WHERE category = 'billing_interval'
        """)
        print(f"   - 數據庫現有記錄: {count} 筆")

    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(import_data())
```

### Phase 3: 後端實現 (預計 2 小時)

#### 3.1 創建 Lookup API

**文件**: `rag-orchestrator/routers/lookup.py`

```python
"""
Lookup API - 通用查詢服務

支持:
- 精確匹配
- 模糊匹配 (基於 difflib)
- 多租戶隔離
- 高性能查詢
"""

from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, Dict, Any, List, Tuple
import logging
from difflib import get_close_matches

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["lookup"])


@router.get("/lookup")
async def lookup(
    request: Request,
    category: str = Query(..., description="查詢類別 ID"),
    key: str = Query(..., description="查詢鍵"),
    vendor_id: int = Query(..., description="業者 ID"),
    fuzzy: bool = Query(True, description="是否啟用模糊匹配"),
    threshold: float = Query(0.6, ge=0.0, le=1.0, description="模糊匹配閾值")
) -> Dict[str, Any]:
    """
    通用 Lookup 查詢服務

    參數:
        - category: 查詢類別 (如 billing_interval)
        - key: 查詢鍵 (如地址)
        - vendor_id: 業者 ID
        - fuzzy: 是否啟用模糊匹配 (默認 true)
        - threshold: 模糊匹配閾值 0-1 (默認 0.6)

    返回:
        - success: 是否成功
        - match_type: 匹配類型 (exact/fuzzy/none)
        - value: 查詢結果
        - metadata: 額外數據
    """

    logger.info(f"🔍 Lookup 查詢: category={category}, key={key[:50]}..., vendor_id={vendor_id}")

    db_pool = request.app.state.db_pool

    try:
        # 1. 精確匹配
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT lookup_value, metadata
                FROM lookup_tables
                WHERE vendor_id = $1
                  AND category = $2
                  AND lookup_key = $3
                  AND is_active = true
            """, vendor_id, category, key)

            if row:
                logger.info(f"✅ 精確匹配成功")
                return {
                    "success": True,
                    "match_type": "exact",
                    "category": category,
                    "key": key,
                    "value": row['lookup_value'],
                    "metadata": row['metadata'] or {}
                }

        # 2. 模糊匹配
        if fuzzy:
            logger.info(f"🔍 嘗試模糊匹配 (threshold={threshold})...")

            async with db_pool.acquire() as conn:
                # 獲取所有該類別的 keys
                rows = await conn.fetch("""
                    SELECT lookup_key, lookup_value, metadata
                    FROM lookup_tables
                    WHERE vendor_id = $1
                      AND category = $2
                      AND is_active = true
                """, vendor_id, category)

                if not rows:
                    logger.warning(f"⚠️  類別 [{category}] 無數據")
                    return {
                        "success": False,
                        "error": "no_data",
                        "message": f"類別 [{category}] 暫無數據"
                    }

                # 使用 difflib 進行模糊匹配
                all_keys = [row['lookup_key'] for row in rows]
                matches = get_close_matches(key, all_keys, n=3, cutoff=threshold)

                if matches:
                    # 返回最佳匹配
                    best_match = matches[0]

                    # 計算相似度分數
                    from difflib import SequenceMatcher
                    score = SequenceMatcher(None, key, best_match).ratio()

                    # 找到對應的值
                    matched_row = next(r for r in rows if r['lookup_key'] == best_match)

                    logger.info(f"✅ 模糊匹配成功: {best_match} (score={score:.2f})")

                    return {
                        "success": True,
                        "match_type": "fuzzy",
                        "match_score": round(score, 2),
                        "category": category,
                        "key": key,
                        "matched_key": best_match,
                        "value": matched_row['lookup_value'],
                        "metadata": matched_row['metadata'] or {}
                    }
                else:
                    # 返回建議
                    suggestions = get_close_matches(
                        key, all_keys, n=5, cutoff=max(0.3, threshold - 0.2)
                    )

                    logger.info(f"⚠️  未找到匹配，返回 {len(suggestions)} 個建議")

                    return {
                        "success": False,
                        "error": "no_match",
                        "category": category,
                        "key": key,
                        "suggestions": [
                            {
                                "key": s,
                                "score": round(
                                    SequenceMatcher(None, key, s).ratio(), 2
                                )
                            }
                            for s in suggestions
                        ],
                        "message": "未找到完全匹配的記錄，以下是相似選項"
                    }

        # 3. 無匹配
        logger.warning(f"❌ 未找到匹配記錄")
        return {
            "success": False,
            "error": "no_match",
            "category": category,
            "key": key,
            "message": "未找到匹配的記錄"
        }

    except Exception as e:
        logger.error(f"❌ Lookup 查詢失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@router.get("/lookup/categories")
async def list_categories(
    request: Request,
    vendor_id: int = Query(..., description="業者 ID")
) -> Dict[str, Any]:
    """
    列出所有可用的查詢類別
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT
                category,
                category_name,
                COUNT(*) as record_count
            FROM lookup_tables
            WHERE vendor_id = $1
              AND is_active = true
            GROUP BY category, category_name
            ORDER BY category
        """, vendor_id)

        categories = [
            {
                "category": row['category'],
                "category_name": row['category_name'],
                "record_count": row['record_count']
            }
            for row in rows
        ]

        return {
            "success": True,
            "vendor_id": vendor_id,
            "categories": categories,
            "total": len(categories)
        }
```

#### 3.2 註冊 Router

**文件**: `rag-orchestrator/main.py` (修改)

```python
# ... 現有導入 ...

from routers.lookup import router as lookup_router  # 新增

# ... 現有代碼 ...

# 註冊路由
app.include_router(lookup_router)  # 新增

# ... 現有代碼 ...
```

### Phase 4: 表單與知識庫配置 (預計 30 分鐘)

#### 4.1 創建地址收集表單

**文件**: `database/test_data/insert_address_form.sql`

```sql
-- 插入地址收集表單
INSERT INTO form_schemas (
    vendor_id,
    form_name,
    form_description,
    fields,
    submit_behavior,
    is_active
) VALUES (
    1,
    '地址收集表單',
    '請提供您的地址以查詢相關資訊',
    '[
        {
            "name": "address",
            "label": "地址",
            "type": "text",
            "required": true,
            "placeholder": "例如：新北市板橋區忠孝路48巷4弄8號二樓",
            "validation": {
                "minLength": 5,
                "maxLength": 200,
                "pattern": "^.{5,}$"
            },
            "help_text": "請輸入完整地址，包含縣市、區、路名、門牌號"
        }
    ]'::jsonb,
    'api_call',
    true
)
ON CONFLICT (vendor_id, form_name) DO UPDATE SET
    fields = EXCLUDED.fields,
    form_description = EXCLUDED.form_description,
    updated_at = CURRENT_TIMESTAMP
RETURNING id;
```

#### 4.2 創建知識庫項目

**文件**: `database/test_data/insert_billing_knowledge.sql`

```sql
-- 獲取表單 ID
DO $$
DECLARE
    form_id INTEGER;
BEGIN
    SELECT id INTO form_id
    FROM form_schemas
    WHERE vendor_id = 1 AND form_name = '地址收集表單';

    -- 插入知識庫
    INSERT INTO vendor_knowledge_base (
        vendor_id,
        question,
        answer,
        action_type,
        form_schema_id,
        api_config,
        trigger_mode,
        category,
        tags
    ) VALUES (
        1,
        '電費怎麼繳',
        '為了查詢您的電費寄送資訊，我需要知道您的地址。',
        'form_then_api',
        form_id,
        '{
            "endpoint": "lookup_billing_interval",
            "combine_with_knowledge": true
        }'::jsonb,
        'manual',
        'billing',
        ARRAY['電費', '帳單', '繳費', '寄送區間', '電費帳單']
    )
    ON CONFLICT (vendor_id, question) DO UPDATE SET
        action_type = EXCLUDED.action_type,
        form_schema_id = EXCLUDED.form_schema_id,
        api_config = EXCLUDED.api_config,
        trigger_mode = EXCLUDED.trigger_mode,
        updated_at = CURRENT_TIMESTAMP;

    RAISE NOTICE '✅ 知識庫項目已創建/更新';
END $$;
```

### Phase 5: 測試 (預計 1 小時)

#### 5.1 單元測試 - Lookup API

**文件**: `tests/test_lookup_api.sh`

```bash
#!/bin/bash

echo "🧪 測試 Lookup API"
echo "===================="

BASE_URL="http://localhost:8100"

# 測試 1: 精確匹配
echo -e "\n📝 測試 1: 精確匹配"
curl -s -X GET "$BASE_URL/api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號二樓&vendor_id=1" \
    | python3 -m json.tool

# 測試 2: 模糊匹配
echo -e "\n📝 測試 2: 模糊匹配 (2樓 -> 二樓)"
curl -s -X GET "$BASE_URL/api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號2樓&vendor_id=1" \
    | python3 -m json.tool

# 測試 3: 無匹配
echo -e "\n📝 測試 3: 無匹配 (返回建議)"
curl -s -X GET "$BASE_URL/api/lookup?category=billing_interval&key=不存在的地址&vendor_id=1" \
    | python3 -m json.tool

# 測試 4: 列出類別
echo -e "\n📝 測試 4: 列出所有類別"
curl -s -X GET "$BASE_URL/api/lookup/categories?vendor_id=1" \
    | python3 -m json.tool
```

#### 5.2 集成測試 - 完整對話流程

**文件**: `tests/test_billing_chat_flow.sh`

```bash
#!/bin/bash

echo "🧪 測試完整對話流程 - 電費查詢"
echo "========================================"

BASE_URL="http://localhost:8100"
SESSION_ID="test_billing_$(date +%s)"

# 第 1 輪: 提問
echo -e "\n📝 第 1 輪: 用戶提問「電費怎麼繳」"
response1=$(curl -s -X POST "$BASE_URL/api/v1/message" \
    -H "Content-Type: application/json" \
    -d "{
        \"message\": \"電費怎麼繳\",
        \"vendor_id\": 1,
        \"user_role\": \"customer\",
        \"user_id\": \"test_user\",
        \"session_id\": \"$SESSION_ID\"
    }")

echo "$response1" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 回應:', data.get('answer', '')[:100])
print('📋 表單觸發:', data.get('form_triggered'))
print('📋 表單 ID:', data.get('form_id'))
"

# 第 2 輪: 提供地址
echo -e "\n📝 第 2 輪: 提供地址"
response2=$(curl -s -X POST "$BASE_URL/api/v1/message" \
    -H "Content-Type: application/json" \
    -d "{
        \"message\": \"新北市板橋區忠孝路48巷4弄8號二樓\",
        \"vendor_id\": 1,
        \"user_role\": \"customer\",
        \"user_id\": \"test_user\",
        \"session_id\": \"$SESSION_ID\"
    }")

echo "$response2" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 最終回應:')
print(data.get('answer', ''))
print('\n📊 API 調用結果:', 'success' if '寄送區間' in data.get('answer', '') else 'failed')
"

echo -e "\n✅ 測試完成!"
```

### Phase 6: 部署 (預計 30 分鐘)

#### 6.1 部署檢查清單

```bash
#!/bin/bash

echo "🚀 Lookup Table System 部署檢查清單"
echo "========================================"

# 1. 數據庫遷移
echo "1️⃣ 執行數據庫遷移..."
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/create_lookup_tables.sql
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_lookup_api_endpoint.sql

# 2. 導入數據
echo "2️⃣ 導入電費數據..."
python3 scripts/data_import/import_billing_intervals.py

# 3. 創建表單和知識庫
echo "3️⃣ 創建表單和知識庫..."
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin < database/test_data/insert_address_form.sql
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin < database/test_data/insert_billing_knowledge.sql

# 4. 重啟服務
echo "4️⃣ 重啟 RAG Orchestrator..."
docker-compose restart rag-orchestrator

# 5. 等待服務啟動
echo "5️⃣ 等待服務啟動..."
sleep 5

# 6. 驗證部署
echo "6️⃣ 驗證部署..."
bash tests/test_lookup_api.sh

echo "✅ 部署完成!"
```

---

## 🧪 測試計劃

### 測試矩陣

| 測試類型 | 測試場景 | 預期結果 | 優先級 |
|---------|---------|---------|-------|
| **單元測試** | Lookup API - 精確匹配 | 返回正確的寄送區間 | P0 |
| **單元測試** | Lookup API - 模糊匹配 | 返回最接近的地址 | P0 |
| **單元測試** | Lookup API - 無匹配 | 返回建議列表 | P1 |
| **單元測試** | Lookup API - 參數驗證 | 返回錯誤訊息 | P1 |
| **集成測試** | 完整對話流程 | 表單 → API → 結果 | P0 |
| **集成測試** | 模糊匹配對話 | 顯示匹配度 | P1 |
| **集成測試** | 未匹配對話 | 顯示建議 | P1 |
| **性能測試** | 100 次並發查詢 | < 500ms 響應 | P2 |
| **壓力測試** | 1000 次並發查詢 | 無錯誤 | P2 |

### 測試數據

```sql
-- 測試數據準備
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata) VALUES
(1, 'billing_interval', '電費寄送區間', '新北市板橋區忠孝路48巷4弄8號二樓', '雙月', '{"electric_number": "12345678"}'::jsonb),
(1, 'billing_interval', '電費寄送區間', '台北市大安區信義路四段1號', '單月', '{"electric_number": "87654321"}'::jsonb),
(1, 'billing_interval', '電費寄送區間', '台北市信義區信義路五段7號', '雙月', '{}'::jsonb);
```

---

## 🚀 部署計劃

### 部署環境

- **開發環境**: localhost (已配置)
- **測試環境**: 待配置
- **生產環境**: 待配置

### 部署步驟

1. **數據庫遷移** → 2 分鐘
2. **數據導入** → 5 分鐘
3. **配置檢查** → 3 分鐘
4. **服務重啟** → 2 分鐘
5. **冒煙測試** → 5 分鐘
6. **監控檢查** → 3 分鐘

**總計**: 約 20 分鐘

### 回滾計劃

如果部署失敗：

```sql
-- 快速回滾
BEGIN;
DELETE FROM vendor_knowledge_base WHERE question = '電費怎麼繳';
DELETE FROM form_schemas WHERE form_name = '地址收集表單';
DELETE FROM api_endpoints WHERE endpoint_id = 'lookup_billing_interval';
DROP TABLE IF EXISTS lookup_tables;
COMMIT;
```

---

## ❓ FAQ

### Q1: 為什麼不用 Redis 存儲？

**A**: lookup_tables 需要支持模糊匹配和復雜查詢，PostgreSQL 的 GIN 索引更適合。Redis 可用於緩存熱點數據。

### Q2: 模糊匹配性能如何？

**A**:
- 精確匹配: < 10ms (使用索引)
- 模糊匹配: < 100ms (內存中使用 difflib)
- 如果數據量超過 10,000 筆，考慮使用 PostgreSQL 的 `similarity()` 函數

### Q3: 如何新增其他查詢類別？

**A**:
1. 插入新數據到 `lookup_tables`（使用新的 `category`）
2. 配置新的 `api_endpoints`（指定 static category 參數）
3. 創建對應的表單和知識庫項目

### Q4: 支持多語言嗎？

**A**: 當前僅支持繁體中文。如需多語言，可在 `metadata` 中存儲翻譯：

```json
{
    "value_zh_TW": "雙月",
    "value_en_US": "Bi-monthly",
    "value_ja_JP": "隔月"
}
```

### Q5: 如何處理數據更新？

**A**:
- **單筆更新**: 直接 UPDATE lookup_tables
- **批量更新**: 重新執行 import 腳本（使用 UPSERT）
- **增量更新**: 提供管理後台（待開發）

---

## 📚 相關文檔

- [Knowledge Action System Design](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [API Configuration Guide](./API_CONFIGURATION_GUIDE.md)
- [Universal API Handler 實現](../../rag-orchestrator/services/universal_api_handler.py)
- [SOP 系統指南](../guides/SOP_GUIDE.md)

---

## 📝 變更歷史

| 版本 | 日期 | 作者 | 變更內容 |
|-----|------|------|---------|
| v1.0 | 2026-02-04 | AI Team | 初始版本 |

---

**文檔狀態**: 📝 規劃完成，待實現

**下一步**: 開始 Phase 1 - 數據庫準備
