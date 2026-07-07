"""
業者參數解析服務
處理模板變數替換，將 {{variable}} 替換為業者專屬參數值
"""
import os
import re
import json
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Set
from decimal import Decimal
from .db_utils import get_db_config


class VendorParameterResolver:
    """業者參數解析器"""

    def __init__(self):
        """初始化參數解析器"""
        # 參數快取（避免重複查詢）
        self._cache: Dict[int, Dict[str, any]] = {}

    def _get_db_connection(self):
        """建立資料庫連接（使用共用配置）"""
        db_config = get_db_config()
        return psycopg2.connect(**db_config)

    def get_vendor_parameters(
        self,
        vendor_id: int,
        use_cache: bool = True
    ) -> Dict[str, Dict]:
        """
        獲取業者的所有參數

        Args:
            vendor_id: 業者 ID
            use_cache: 是否使用快取

        Returns:
            參數字典，格式：
            {
                "payment_day": {
                    "value": "1",
                    "data_type": "number",
                    "unit": "號",
                    "display_name": "繳費日期"
                }
            }
        """
        # 檢查快取
        if use_cache and vendor_id in self._cache:
            return self._cache[vendor_id]

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 參數分工定案（使用者裁決 2026-07-06）：通用資料（電話/LINE/營業時間等
            # vendor 級單值）＝vendor_configs；案場級/清單級（管理費/電費/包裹）＝lookup
            # 由錨點消費。預設讀 configs；VENDOR_PARAMS_FROM_LOOKUP=true 保留切換能力。
            import os as _os
            if _os.getenv("VENDOR_PARAMS_FROM_LOOKUP", "false").lower() == "true":
                cursor.execute("""
                    SELECT
                        lookup_key   AS param_key,
                        lookup_value AS param_value,
                        metadata->>'data_type'    AS data_type,
                        metadata->>'unit'         AS unit,
                        metadata->>'display_name' AS display_name,
                        NULL         AS description
                    FROM lookup_tables
                    WHERE vendor_id = %s AND is_active = true
                      AND category IN ('payment', 'contract', 'service', 'contact')
                """, (vendor_id,))
            else:
                cursor.execute("""
                    SELECT
                        param_key,
                        param_value,
                        data_type,
                        unit,
                        display_name,
                        description
                    FROM vendor_configs
                    WHERE vendor_id = %s AND is_active = true
                """, (vendor_id,))

            rows = cursor.fetchall()
            cursor.close()

            # 轉換為字典格式
            params = {}
            for row in rows:
                params[row['param_key']] = {
                    'value': row['param_value'],
                    'data_type': row['data_type'],
                    'unit': row['unit'],
                    'display_name': row['display_name'],
                    'description': row['description']
                }

            # 存入快取
            self._cache[vendor_id] = params

            return params

        finally:
            conn.close()

    def extract_template_variables(self, text: str) -> Set[str]:
        """
        從文本中提取模板變數

        Args:
            text: 包含模板變數的文本

        Returns:
            變數名稱集合

        Example:
            "繳費日為 {{payment_day}} 號" -> {"payment_day"}
        """
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, text)
        return set(matches)

    def _format_value(
        self,
        value: str,
        data_type: str,
        unit: Optional[str] = None
    ) -> str:
        """
        格式化參數值

        Args:
            value: 原始值
            data_type: 資料型別（string, number, date, boolean, json）
            unit: 單位

        Returns:
            格式化後的值
        """
        # 數字類型：添加單位
        if data_type == 'number':
            try:
                # 嘗試轉換為數字（去除多餘的小數點）
                num = Decimal(value)
                # 如果是整數，不顯示小數點
                if num % 1 == 0:
                    formatted = str(int(num))
                else:
                    formatted = str(num)

                # 添加單位
                if unit:
                    return f"{formatted} {unit}"
                return formatted
            except:
                # 轉換失敗，返回原值
                return value + (f" {unit}" if unit else "")

        # 布林類型：轉換為中文
        elif data_type == 'boolean':
            if value.lower() in ['true', '1', 'yes', '是']:
                return '是'
            else:
                return '否'

        # JSON 類型：格式化為易讀格式
        elif data_type == 'json':
            try:
                obj = json.loads(value)
                # 如果是陣列，轉換為列表
                if isinstance(obj, list):
                    return '、'.join(str(item) for item in obj)
                # 如果是物件，保持 JSON 格式
                return json.dumps(obj, ensure_ascii=False, indent=2)
            except:
                return value

        # 日期類型：格式化（如果需要）
        elif data_type == 'date':
            # 這裡可以添加日期格式化邏輯
            return value

        # 字串類型：直接返回
        else:
            return value

    def resolve_template(
        self,
        text: str,
        vendor_id: int,
        raise_on_missing: bool = False
    ) -> str:
        """
        解析模板，替換變數為實際值

        Args:
            text: 包含模板變數的文本
            vendor_id: 業者 ID
            raise_on_missing: 遇到缺失變數是否拋出異常

        Returns:
            替換後的文本

        Example:
            輸入："繳費日為 {{payment_day}} 號，逾期費 {{late_fee}} 元"
            輸出："繳費日為 1 號，逾期費 200 元"
        """
        result, _ = self.resolve_template_with_tracking(text, vendor_id, raise_on_missing)
        return result

    def resolve_template_with_tracking(
        self,
        text: str,
        vendor_id: int,
        raise_on_missing: bool = False
    ) -> tuple[str, list[str]]:
        """
        解析模板並追蹤實際被替換的參數

        Args:
            text: 包含模板變數的文本
            vendor_id: 業者 ID
            raise_on_missing: 遇到缺失變數是否拋出異常

        Returns:
            (替換後的文本, 實際被使用的參數 key 列表)

        Example:
            輸入："繳費日為 {{payment_day}} 號"
            輸出：("繳費日為 1 號", ["payment_day"])
        """
        # 提取所有變數
        variables = self.extract_template_variables(text)

        if not variables:
            return text, []

        # 獲取業者參數
        params = self.get_vendor_parameters(vendor_id)

        # 替換變數
        result = text
        missing_vars = []
        used_params = []  # 追蹤實際被使用的參數

        for var_name in variables:
            if var_name not in params:
                missing_vars.append(var_name)
                if raise_on_missing:
                    raise ValueError(f"Missing parameter: {var_name} for vendor {vendor_id}")
                # 保留原變數
                continue

            param = params[var_name]
            formatted_value = self._format_value(
                param['value'],
                param['data_type'],
                param['unit']
            )

            # 替換 {{var_name}} 為實際值
            result = result.replace(f"{{{{{var_name}}}}}", formatted_value)
            used_params.append(var_name)  # 記錄被使用的參數

        if missing_vars and not raise_on_missing:
            print(f"⚠️  Warning: Missing parameters for vendor {vendor_id}: {missing_vars}")

        return result, used_params

    def resolve_multiple_templates(
        self,
        texts: List[str],
        vendor_id: int
    ) -> List[str]:
        """
        批次解析多個模板

        Args:
            texts: 模板文本列表
            vendor_id: 業者 ID

        Returns:
            替換後的文本列表
        """
        return [self.resolve_template(text, vendor_id) for text in texts]

    def get_vendor_info(self, vendor_id: int) -> Optional[Dict]:
        """
        獲取業者基本資訊

        Args:
            vendor_id: 業者 ID

        Returns:
            業者資訊字典
        """
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    id,
                    code,
                    name,
                    short_name,
                    contact_phone,
                    contact_email,
                    is_active,
                    subscription_plan,
                    business_types
                FROM vendors
                WHERE id = %s
            """, (vendor_id,))

            row = cursor.fetchone()
            cursor.close()

            return dict(row) if row else None

        finally:
            conn.close()

    def clear_cache(self, vendor_id: Optional[int] = None):
        """
        清除參數快取

        Args:
            vendor_id: 業者 ID（None 表示清除全部快取）
        """
        if vendor_id is None:
            self._cache.clear()
        elif vendor_id in self._cache:
            del self._cache[vendor_id]

    def validate_template(self, text: str, vendor_id: int) -> Dict:
        """
        驗證模板是否可以正確解析

        Args:
            text: 模板文本
            vendor_id: 業者 ID

        Returns:
            驗證結果
            {
                "valid": bool,
                "variables": List[str],
                "missing_variables": List[str],
                "resolved_text": str
            }
        """
        variables = self.extract_template_variables(text)
        params = self.get_vendor_parameters(vendor_id)

        missing_vars = [var for var in variables if var not in params]

        return {
            "valid": len(missing_vars) == 0,
            "variables": list(variables),
            "missing_variables": missing_vars,
            "resolved_text": self.resolve_template(text, vendor_id) if not missing_vars else None
        }


# 使用範例
if __name__ == "__main__":
    resolver = VendorParameterResolver()

    # 測試業者 A
    print("📋 測試業者 A 參數")
    print("=" * 60)

    # 獲取所有參數
    params_a = resolver.get_vendor_parameters(vendor_id=1)
    print(f"業者 A 參數數量: {len(params_a)}")
    for key, param in params_a.items():
        print(f"  {key}: {param['value']} ({param['data_type']})")

    # 測試模板解析
    template = "您的租金繳費日為每月 {{payment_day}}，逾期費用為 {{late_fee}}。"
    resolved = resolver.resolve_template(template, vendor_id=1)
    print(f"\n原始模板: {template}")
    print(f"解析結果: {resolved}")

    # 測試業者 B
    print("\n" + "=" * 60)
    print("📋 測試業者 B 參數")
    print("=" * 60)

    resolved_b = resolver.resolve_template(template, vendor_id=2)
    print(f"原始模板: {template}")
    print(f"解析結果: {resolved_b}")

    # 測試變數提取
    print("\n" + "=" * 60)
    print("📋 測試變數提取")
    print("=" * 60)

    complex_template = """
    繳費日: {{payment_day}}
    繳費方式: {{payment_method}}
    客服專線: {{service_hotline}}
    """
    variables = resolver.extract_template_variables(complex_template)
    print(f"模板變數: {variables}")

    # 測試模板驗證
    print("\n" + "=" * 60)
    print("📋 測試模板驗證")
    print("=" * 60)

    validation = resolver.validate_template(complex_template, vendor_id=1)
    print(f"驗證結果: {validation}")
