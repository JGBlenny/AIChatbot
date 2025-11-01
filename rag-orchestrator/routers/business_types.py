"""
業態類型配置 API（只讀）
從配置文件讀取業態類型，不涉及資料庫操作
"""
from fastapi import APIRouter
from config.business_types import (
    BUSINESS_CATEGORIES,
    get_all_business_types,
    get_business_type,
    get_business_category
)

router = APIRouter()


@router.get("/business-types-config")
async def get_all_business_types_api(is_active: bool = True):
    """
    取得所有業態類型配置（從配置文件讀取）

    Args:
        is_active: 保留此參數以兼容前端，但配置文件中所有類型都是啟用的

    Returns:
        業態類型列表
    """
    try:
        business_types = get_all_business_types()

        # 格式化為前端期望的格式，添加 is_active 欄位
        formatted_types = []
        for bt in business_types:
            formatted_types.append({
                "type_value": bt["type_value"],
                "display_name": bt["display_name"],
                "description": bt["description"],
                "icon": bt["icon"],
                "color": bt["color"],
                "is_active": True  # 配置文件中的類型都是啟用的
            })

        return {
            "business_types": formatted_types,
            "total": len(formatted_types)
        }

    except Exception as e:
        return {
            "business_types": [],
            "total": 0,
            "error": str(e)
        }


@router.get("/business-types-config/{type_value}")
async def get_business_type_api(type_value: str):
    """
    取得特定業態類型配置（從配置文件讀取）

    Args:
        type_value: 業態類型值（如 'full_service'）

    Returns:
        業態類型詳情
    """
    business_type = get_business_type(type_value)

    if not business_type:
        return {
            "error": f"找不到業態類型: {type_value}",
            "type_value": type_value
        }

    return {
        **business_type,
        "is_active": True
    }


@router.get("/business-categories")
async def get_all_categories():
    """
    取得所有業務類別（B2C / B2B）及其下的業態類型

    Returns:
        完整的業態類別層級結構
    """
    return {
        "categories": BUSINESS_CATEGORIES,
        "total": len(BUSINESS_CATEGORIES)
    }
