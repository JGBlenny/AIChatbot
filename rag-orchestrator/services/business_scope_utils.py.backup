"""
業務範圍工具函數
提供業務範圍與受眾（audience）的映射邏輯，用於知識檢索時的過濾

Version 2.0: 從數據庫 audience_config 表動態讀取映射關係
"""
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from .db_utils import get_db_config

# ========================================
# 緩存機制
# ========================================

# 緩存：避免每次都查數據庫
_AUDIENCE_CACHE: Optional[Dict[str, List[str]]] = None
_CACHE_TIMESTAMP: Optional[float] = None
_CACHE_TTL = 300  # 緩存有效期：5分鐘

# Fallback：如果數據庫查詢失敗，使用硬編碼的預設映射
FALLBACK_AUDIENCE_MAPPING: Dict[str, Dict[str, any]] = {
    'external': {
        'allowed_audiences': [
            '租客', '房東', 'tenant', 'general',
            '租客|管理師', '房東|租客', '房東|租客|管理師',
        ],
        'description': 'B2C 包租代管服務（租客、房東）'
    },
    'internal': {
        'allowed_audiences': [
            '管理師', '系統管理員', 'general',
            '租客|管理師', '房東|租客|管理師', '房東/管理師',
        ],
        'description': 'B2B 系統商內部管理'
    }
}


# ========================================
# 數據庫讀取函數
# ========================================

def _load_audience_mapping_from_db() -> Dict[str, List[str]]:
    """
    從數據庫 audience_config 表載入映射關係

    Returns:
        映射字典：
        {
            'external': ['租客', '房東', ...],
            'internal': ['管理師', '系統管理員', ...],
        }
    """
    try:
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 查詢所有啟用的 audience
        cursor.execute("""
            SELECT
                audience_value,
                business_scope
            FROM audience_config
            WHERE is_active = TRUE
            ORDER BY display_order
        """)

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # 建立映射
        mapping = {
            'external': [],
            'internal': []
        }

        for row in rows:
            audience_value = row['audience_value']
            business_scope = row['business_scope']

            # 根據 business_scope 分配
            if business_scope == 'external':
                mapping['external'].append(audience_value)
            elif business_scope == 'internal':
                mapping['internal'].append(audience_value)
            elif business_scope == 'both':
                # 'both' 表示兩邊都可見
                mapping['external'].append(audience_value)
                mapping['internal'].append(audience_value)

        return mapping

    except Exception as e:
        print(f"⚠️  Failed to load audience mapping from database: {e}")
        print("   Falling back to hardcoded mapping")
        return None


def _get_audience_mapping() -> Dict[str, List[str]]:
    """
    獲取 audience 映射（帶緩存）

    Returns:
        映射字典
    """
    global _AUDIENCE_CACHE, _CACHE_TIMESTAMP

    import time
    current_time = time.time()

    # 檢查緩存是否有效
    if _AUDIENCE_CACHE is not None and _CACHE_TIMESTAMP is not None:
        if current_time - _CACHE_TIMESTAMP < _CACHE_TTL:
            return _AUDIENCE_CACHE

    # 從數據庫載入
    mapping = _load_audience_mapping_from_db()

    if mapping:
        # 成功載入，更新緩存
        _AUDIENCE_CACHE = mapping
        _CACHE_TIMESTAMP = current_time
        return mapping
    else:
        # 載入失敗，使用 fallback
        return {
            'external': FALLBACK_AUDIENCE_MAPPING['external']['allowed_audiences'],
            'internal': FALLBACK_AUDIENCE_MAPPING['internal']['allowed_audiences']
        }


def clear_audience_cache():
    """
    清除 audience 映射緩存
    當 audience_config 表有更新時，可以呼叫此函數強制重新載入
    """
    global _AUDIENCE_CACHE, _CACHE_TIMESTAMP
    _AUDIENCE_CACHE = None
    _CACHE_TIMESTAMP = None


def get_allowed_audiences_for_scope(business_scope_name: str) -> List[str]:
    """
    根據業務範圍名稱獲取允許的受眾列表（從數據庫動態讀取）

    Args:
        business_scope_name: 業務範圍名稱 (external/internal)

    Returns:
        允許的受眾列表

    Examples:
        >>> get_allowed_audiences_for_scope('external')
        ['租客', '房東', 'tenant', 'general', ...]

        >>> get_allowed_audiences_for_scope('internal')
        ['管理師', '系統管理員', 'general', ...]
    """
    mapping = _get_audience_mapping()
    return mapping.get(business_scope_name, mapping.get('external', []))


def is_audience_allowed_for_scope(
    audience: str,
    business_scope_name: str
) -> bool:
    """
    判斷受眾是否屬於業務範圍

    Args:
        audience: 受眾名稱（如 '租客', '管理師'）
        business_scope_name: 業務範圍名稱 (external/internal)

    Returns:
        是否允許

    Examples:
        >>> is_audience_allowed_for_scope('租客', 'external')
        True

        >>> is_audience_allowed_for_scope('管理師', 'external')
        False

        >>> is_audience_allowed_for_scope('管理師', 'internal')
        True

        >>> is_audience_allowed_for_scope(None, 'external')
        True  # NULL audience 視為通用
    """
    if not audience:
        return True  # NULL audience 視為通用，允許所有業務範圍

    allowed = get_allowed_audiences_for_scope(business_scope_name)
    return audience in allowed


def get_scope_description(business_scope_name: str) -> str:
    """
    獲取業務範圍的描述

    Args:
        business_scope_name: 業務範圍名稱

    Returns:
        業務範圍描述
    """
    descriptions = {
        'external': 'B2C 包租代管服務（租客、房東）',
        'internal': 'B2B 系統商內部管理',
        'both': '通用（所有業務範圍）'
    }
    return descriptions.get(business_scope_name, f"未知業務範圍: {business_scope_name}")


def get_all_business_scopes() -> List[str]:
    """
    獲取所有支援的業務範圍名稱

    Returns:
        業務範圍名稱列表
    """
    return list(BUSINESS_SCOPE_AUDIENCE_MAPPING.keys())


# 使用範例和測試
if __name__ == "__main__":
    print("=" * 60)
    print("業務範圍工具測試")
    print("=" * 60)

    # 測試 external (B2C)
    print("\n✅ External (B2C) 允許的受眾:")
    external_audiences = get_allowed_audiences_for_scope('external')
    for aud in external_audiences:
        print(f"   - {aud}")

    # 測試 internal (B2B)
    print("\n✅ Internal (B2B) 允許的受眾:")
    internal_audiences = get_allowed_audiences_for_scope('internal')
    for aud in internal_audiences:
        print(f"   - {aud}")

    # 測試權限判斷
    print("\n" + "=" * 60)
    print("權限判斷測試")
    print("=" * 60)

    test_cases = [
        ('租客', 'external', True),
        ('租客', 'internal', False),
        ('管理師', 'external', False),
        ('管理師', 'internal', True),
        ('general', 'external', True),
        ('general', 'internal', True),
        (None, 'external', True),
        (None, 'internal', True),
    ]

    for audience, scope, expected in test_cases:
        result = is_audience_allowed_for_scope(audience, scope)
        status = "✅" if result == expected else "❌"
        print(f"{status} audience='{audience}', scope='{scope}' -> {result} (期望: {expected})")
