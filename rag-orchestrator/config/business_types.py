"""
业态类型配置

结构说明：
- 业务类别（B2C / B2B）
  - 业态类型（包租型 / 代管型 / 系统商）

注意：此配置用于 LLM 答案优化器的语气调整
"""

from typing import Dict, List, TypedDict


class BusinessTypeConfig(TypedDict):
    """业态配置结构"""
    type_value: str
    display_name: str
    description: str
    color: str
    icon: str
    tone_prompt: str
    features: List[str]


class BusinessCategoryConfig(TypedDict):
    """业务类别配置结构"""
    code: str
    name: str
    description: str
    icon: str
    color: str
    types: List[BusinessTypeConfig]


# 业态类型配置
BUSINESS_CATEGORIES: Dict[str, BusinessCategoryConfig] = {
    'B2C': {
        'code': 'B2C',
        'name': 'B2C（面向个人客户）',
        'description': '面向个人房东和租客提供租赁相关服务',
        'icon': '👤',
        'color': 'blue',
        'types': [
            {
                'type_value': 'full_service',
                'display_name': '包租型',
                'description': '提供全方位租赁管理服务，直接负责租赁相关事务',
                'color': 'blue',
                'icon': '🏠',
                'tone_prompt': """业种特性：包租型业者 - 提供全方位服务，直接负责租赁管理

语气要求：
• 使用主动承诺语气：「我们会」、「公司将」
• 展现服务主导性：强调由公司直接处理
• 避免被动引导：不要用「请您联系」、「建议」等

范例转换：
❌ 「请您与房东联系处理维修事宜」
✅ 「我们会立即为您安排维修处理」

❌ 「建议您可以询问房东」
✅ 「我们会直接与房东确认并回复您」""",
                'features': [
                    '全权处理租赁事务',
                    '直接与租客签约',
                    '承担租金保证',
                    '负责维修保养'
                ]
            },
            {
                'type_value': 'property_management',
                'display_name': '代管型',
                'description': '提供物业代理管理服务，协助房东处理租赁事务',
                'color': 'green',
                'icon': '🔧',
                'tone_prompt': """业种特性：代管型业者 - 协助房东管理物业，扮演中介协调角色

语气要求：
• 使用协助引导语气：「我们可以协助」、「帮您转达」
• 展现协调角色：强调沟通和协助
• 适当引导：「我们会帮您询问房东」、「协助您联系」

范例转换：
❌ 「我们会立即为您处理」（过于主动）
✅ 「我们会协助您向房东反映，并帮您追踪处理进度」

❌ 「公司将直接安排」（过于直接）
✅ 「我们可以帮您联系房东安排」""",
                'features': [
                    '协助房东管理物业',
                    '代收代付租金',
                    '协调租赁事务',
                    '提供咨询建议'
                ]
            }
        ]
    },
    'B2B': {
        'code': 'B2B',
        'name': 'B2B（面向企业客户）',
        'description': '面向企业和系统商提供专业解决方案',
        'icon': '🏢',
        'color': 'purple',
        'types': [
            {
                'type_value': 'system_provider',
                'display_name': '系统商',
                'description': '提供租赁管理系统解决方案和技术服务',
                'color': 'purple',
                'icon': '💻',
                'tone_prompt': """业种特性：系统商 - 提供技术解决方案，面向专业客户

语气要求：
• 使用专业技术语气：「系统功能」、「API 接口」
• 展现技术专业性：强调系统能力和技术支持
• 提供明确规格：具体的功能说明和技术细节

范例转换：
❌ 「我们会帮您处理」（过于笼统）
✅ 「系统提供自动化处理功能，您可透过 API 进行整合」

❌ 「请联系我们」（不够专业）
✅ 「请参考技术文档或联系技术支持团队」""",
                'features': [
                    '提供系统解决方案',
                    'API 技术支持',
                    '客制化开发',
                    '系统整合服务'
                ]
            }
        ]
    }
}


def get_all_business_types() -> List[BusinessTypeConfig]:
    """
    取得所有业态类型（扁平化）

    Returns:
        业态类型列表
    """
    types = []
    for category in BUSINESS_CATEGORIES.values():
        for business_type in category['types']:
            types.append(business_type)
    return types


def get_business_type(type_value: str) -> BusinessTypeConfig | None:
    """
    根据 type_value 查找业态

    Args:
        type_value: 业态类型值（如 'full_service'）

    Returns:
        业态配置，若不存在返回 None
    """
    all_types = get_all_business_types()
    for business_type in all_types:
        if business_type['type_value'] == type_value:
            return business_type
    return None


def get_business_category(category_code: str) -> BusinessCategoryConfig | None:
    """
    根据类别代码查找类别

    Args:
        category_code: 类别代码（'B2C' 或 'B2B'）

    Returns:
        类别配置，若不存在返回 None
    """
    return BUSINESS_CATEGORIES.get(category_code)


def get_tone_prompt(type_value: str) -> str | None:
    """
    取得业态的语气 Prompt

    Args:
        type_value: 业态类型值

    Returns:
        语气 Prompt，若不存在返回 None
    """
    business_type = get_business_type(type_value)
    if business_type:
        return business_type.get('tone_prompt')
    return None


def get_all_tone_prompts() -> Dict[str, str]:
    """
    取得所有业态的语气 Prompt 字典

    Returns:
        {type_value: tone_prompt} 字典
    """
    result = {}
    for business_type in get_all_business_types():
        tone_prompt = business_type.get('tone_prompt')
        if tone_prompt:
            result[business_type['type_value']] = tone_prompt
    return result
