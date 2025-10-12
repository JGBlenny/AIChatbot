"""
業務範圍工具函數
提供業務範圍與受眾（audience）的映射邏輯，用於知識檢索時的過濾
"""
from typing import List, Dict

# 業務範圍與受眾映射表
# 用於知識檢索時根據 vendor 的 business_scope_name 過濾允許的 audience
BUSINESS_SCOPE_AUDIENCE_MAPPING: Dict[str, Dict[str, any]] = {
    'external': {
        'allowed_audiences': [
            # B2C 租客、房東相關
            '租客',
            '房東',
            'tenant',
            'general',
            # 複合受眾（包含租客或房東）
            '租客|管理師',
            '房東|租客',
            '房東|租客|管理師',
        ],
        'description': 'B2C 包租代管服務（租客、房東）'
    },
    'internal': {
        'allowed_audiences': [
            # B2B 系統商內部管理
            '管理師',
            '系統管理員',
            'general',
            # 複合受眾（包含管理師）
            '租客|管理師',
            '房東|租客|管理師',
            '房東/管理師',
        ],
        'description': 'B2B 系統商內部管理'
    }
}


def get_allowed_audiences_for_scope(business_scope_name: str) -> List[str]:
    """
    根據業務範圍名稱獲取允許的受眾列表

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
    mapping = BUSINESS_SCOPE_AUDIENCE_MAPPING.get(
        business_scope_name,
        BUSINESS_SCOPE_AUDIENCE_MAPPING['external']  # 預設 B2C
    )
    return mapping['allowed_audiences']


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
    mapping = BUSINESS_SCOPE_AUDIENCE_MAPPING.get(business_scope_name)
    if mapping:
        return mapping['description']
    return f"未知業務範圍: {business_scope_name}"


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
