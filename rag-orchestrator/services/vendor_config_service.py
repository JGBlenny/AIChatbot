"""
業者配置服務
查詢並提供業者參數設定（層級2）
"""
import asyncpg
from typing import Dict, List, Optional, Any
from asyncpg.pool import Pool


class VendorConfigService:
    """業者配置服務 - 提供業者參數查詢"""

    def __init__(self, db_pool: Pool):
        """
        初始化服務

        Args:
            db_pool: 資料庫連接池
        """
        self.db_pool = db_pool
        self._cache: Dict[int, Dict[str, Any]] = {}  # vendor_id -> configs

    async def get_vendor_configs(self, vendor_id: int, category: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取業者配置參數

        Args:
            vendor_id: 業者 ID
            category: 配置類別（如 'payment', 'cashflow'），None 表示全部

        Returns:
            配置字典 {param_key: param_value}
        """
        cache_key = f"{vendor_id}:{category or 'all'}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        async with self.db_pool.acquire() as conn:
            if category:
                rows = await conn.fetch("""
                    SELECT param_key, param_value, data_type, display_name, unit
                    FROM vendor_configs
                    WHERE vendor_id = $1
                      AND category = $2
                      AND is_active = true
                    ORDER BY param_key
                """, vendor_id, category)
            else:
                rows = await conn.fetch("""
                    SELECT param_key, param_value, data_type, display_name, unit, category
                    FROM vendor_configs
                    WHERE vendor_id = $1
                      AND is_active = true
                    ORDER BY category, param_key
                """, vendor_id)

        configs = {}
        for row in rows:
            key = row['param_key']
            value = self._parse_value(row['param_value'], row['data_type'])
            configs[key] = {
                'value': value,
                'display_name': row['display_name'],
                'unit': row.get('unit', ''),
                'category': row.get('category', category)
            }

        self._cache[cache_key] = configs
        return configs

    def _parse_value(self, value: str, data_type: str) -> Any:
        """
        根據資料型別解析值

        Args:
            value: 字串值
            data_type: 資料型別（number, boolean, string, json）

        Returns:
            解析後的值
        """
        if data_type == 'number':
            try:
                if '.' in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value
        elif data_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 't')
        elif data_type == 'json':
            import json
            try:
                return json.loads(value)
            except:
                return value
        else:  # string
            return value

    async def get_payment_params(self, vendor_id: int) -> Dict[str, Any]:
        """
        獲取繳費相關參數

        Returns:
            {
                'payment_day': {'value': 1, 'display_name': '繳費日期', 'unit': '號'},
                'payment_methods': {'value': '銀行轉帳\n超商繳費\n信用卡', ...},
                ...
            }
        """
        return await self.get_vendor_configs(vendor_id, 'payment')

    async def get_cashflow_params(self, vendor_id: int) -> Dict[str, Any]:
        """獲取金流相關參數"""
        return await self.get_vendor_configs(vendor_id, 'cashflow')

    async def get_contract_params(self, vendor_id: int) -> Dict[str, Any]:
        """獲取合約相關參數"""
        return await self.get_vendor_configs(vendor_id, 'contract')

    def is_param_question(self, question: str, intent_type: str = None) -> Optional[str]:
        """
        判斷是否為參數型問題

        Args:
            question: 用戶問題
            intent_type: 意圖類型

        Returns:
            參數類別（'payment', 'cashflow', 'contract', 'service', 'contact'）或 None
        """
        # 繳費相關參數問題
        payment_keywords = [
            '繳費日期', '繳費時間', '幾號', '何時繳', '收租日', '扣款日',
            '繳費方式', '如何繳費', '怎麼繳', '付款方式',
            '寬限期', '逾期', '滯納金', '手續費'
        ]

        # 金流相關參數問題
        cashflow_keywords = [
            '金流', '收租方式', '代收', '誰收租', '租金誰收',
            '帳戶', '匯款帳號', '轉帳對象'
        ]

        # 合約相關參數問題
        contract_keywords = [
            '租期', '合約期限', '最短租期', '違約金',
            '押金', '保證金', '簽約費'
        ]

        # 服務相關參數問題
        service_keywords = [
            '客服專線', '客服電話', '聯絡電話', '電話', '專線',
            '服務時間', '營業時間', '上班時間',
            '報修', '維修', '回應時間'
        ]

        # 聯絡資訊相關參數問題
        contact_keywords = [
            'line', '官方帳號', '加line',
            '公司地址', '辦公室', '地址'
        ]

        question_lower = question.lower()

        if any(kw in question_lower for kw in payment_keywords):
            return 'payment'
        elif any(kw in question_lower for kw in cashflow_keywords):
            return 'cashflow'
        elif any(kw in question_lower for kw in contract_keywords):
            return 'contract'
        elif any(kw in question_lower for kw in service_keywords):
            return 'service'
        elif any(kw in question_lower for kw in contact_keywords):
            return 'contact'

        return None

    async def create_param_answer(
        self,
        vendor_id: int,
        question: str,
        param_category: str
    ) -> Optional[Dict[str, Any]]:
        """
        根據參數創建直接答案

        Args:
            vendor_id: 業者 ID
            question: 用戶問題
            param_category: 參數類別

        Returns:
            答案字典或 None
        """
        if param_category == 'payment':
            params = await self.get_payment_params(vendor_id)

            # 繳費日期問題
            if any(kw in question for kw in ['繳費日期', '幾號', '何時繳', '收租日']):
                if 'payment_day' in params:
                    day = params['payment_day']['value']
                    unit = params['payment_day'].get('unit', '號')
                    return {
                        'answer': f"租金繳費日期為每月{day}{unit}，請租客準時於每月{day}{unit}前完成繳費。",
                        'source': 'vendor_config',
                        'config_used': {
                            'payment_day': day
                        },
                        'confidence': 1.0  # 參數型答案信心度為 100%
                    }

            # 繳費方式問題
            if any(kw in question for kw in ['繳費方式', '如何繳費', '怎麼繳', '付款方式']):
                if 'payment_methods' in params:
                    methods = params['payment_methods']['value']
                    # 將換行符轉換為中文逗號分隔
                    methods_list = [m.strip() for m in methods.split('\n') if m.strip()]
                    methods_text = '、'.join(methods_list)
                    return {
                        'answer': f"本公司提供以下繳費方式：{methods_text}。",
                        'source': 'vendor_config',
                        'config_used': {
                            'payment_methods': methods_text
                        },
                        'confidence': 1.0
                    }

        elif param_category == 'cashflow':
            params = await self.get_cashflow_params(vendor_id)
            # TODO: 實作金流相關答案生成
            pass

        elif param_category == 'service':
            params = await self.get_vendor_configs(vendor_id, 'service')

            # 客服專線問題
            if any(kw in question for kw in ['客服專線', '客服電話', '聯絡電話', '電話', '專線']):
                if 'service_hotline' in params:
                    hotline = params['service_hotline']['value']
                    answer_parts = [f"我們的客服專線是 {hotline}"]

                    # 如果有服務時間，一併提供
                    if 'service_hours' in params:
                        hours = params['service_hours']['value']
                        answer_parts.append(f"服務時間為{hours}")

                    answer = "，".join(answer_parts) + "。"

                    return {
                        'answer': answer,
                        'source': 'vendor_config',
                        'config_used': {
                            'service_hotline': hotline,
                            'service_hours': params.get('service_hours', {}).get('value', '')
                        },
                        'confidence': 1.0
                    }

            # 服務時間問題
            if any(kw in question for kw in ['服務時間', '營業時間', '上班時間']):
                if 'service_hours' in params:
                    hours = params['service_hours']['value']
                    return {
                        'answer': f"我們的服務時間為{hours}。",
                        'source': 'vendor_config',
                        'config_used': {
                            'service_hours': hours
                        },
                        'confidence': 1.0
                    }

            # 報修回應時間問題
            if any(kw in question for kw in ['報修', '維修', '回應時間']):
                if 'repair_response_time' in params:
                    response_time = params['repair_response_time']['value']
                    unit = params['repair_response_time'].get('unit', '')
                    return {
                        'answer': f"我們承諾在收到報修通知後{response_time}{unit}內回應處理。",
                        'source': 'vendor_config',
                        'config_used': {
                            'repair_response_time': response_time
                        },
                        'confidence': 1.0
                    }

        elif param_category == 'contact':
            params = await self.get_vendor_configs(vendor_id, 'contact')

            # LINE 官方帳號問題
            if any(kw in question.lower() for kw in ['line', '官方帳號', '加line']):
                if 'line_id' in params:
                    line_id = params['line_id']['value']
                    return {
                        'answer': f"我們的 LINE 官方帳號是 {line_id}，歡迎加入以獲得即時服務。",
                        'source': 'vendor_config',
                        'config_used': {
                            'line_id': line_id
                        },
                        'confidence': 1.0
                    }

            # 公司地址問題
            if any(kw in question for kw in ['公司地址', '辦公室', '地址']):
                if 'office_address' in params:
                    address = params['office_address']['value']
                    return {
                        'answer': f"我們的公司地址是：{address}。",
                        'source': 'vendor_config',
                        'config_used': {
                            'office_address': address
                        },
                        'confidence': 1.0
                    }

        return None

    async def get_vendor_context(self, vendor_id: int) -> Dict[str, Any]:
        """
        獲取業者完整上下文（用於 LLM 注入）

        Returns:
            {
                'vendor_id': 1,
                'payment': {'payment_day': 1, 'payment_methods': '...'},
                'cashflow': {...},
                'contract': {...}
            }
        """
        all_configs = await self.get_vendor_configs(vendor_id)

        # 按類別組織
        context = {
            'vendor_id': vendor_id,
            'payment': {},
            'cashflow': {},
            'contract': {},
            'other': {}
        }

        for key, config in all_configs.items():
            category = config.get('category', 'other')
            if category in context:
                context[category][key] = config['value']
            else:
                context['other'][key] = config['value']

        return context

    def clear_cache(self):
        """清除快取"""
        self._cache.clear()
