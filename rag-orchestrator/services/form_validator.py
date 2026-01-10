"""
表單欄位驗證器（Form Validator）
負責驗證用戶輸入的資料格式和合法性

支援的驗證類型：
1. 正則表達式驗證（pattern）
2. 長度驗證（min_length, max_length）
3. 自訂驗證函數（台灣身分證、電話號碼等）
"""
import re
from typing import Tuple, Optional


class FormValidator:
    """表單欄位驗證器"""

    def __init__(self):
        # 預定義的驗證器（匹配資料庫 validation_type）
        self.validators = {
            'phone': self._validate_phone,
            'taiwan_id': self._validate_taiwan_id,
            'taiwan_name': self._validate_taiwan_name,
            'address': self._validate_address,
            'email': self._validate_email
        }

    def validate_field(
        self,
        field_config: dict,
        user_input: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        驗證欄位資料

        Args:
            field_config: 欄位配置（包含驗證規則）
            user_input: 用戶輸入

        Returns:
            (is_valid, extracted_value, error_message)
            - is_valid: 是否通過驗證
            - extracted_value: 提取的值（若驗證通過）
            - error_message: 錯誤訊息（若驗證失敗）
        """
        field_type = field_config.get('field_type', 'text')
        field_label = field_config.get('field_label', '此欄位')
        validation_type = field_config.get('validation_type')

        # 1. 提取可能的值（去除多餘文字）
        extracted = self._extract_value(user_input, validation_type or field_type)

        # 2. 檢查必填欄位
        if field_config.get('required', False) and not extracted.strip():
            error_message = f"{field_label}為必填項目，請提供有效的資料。"
            return (False, None, error_message)

        # 3. 長度驗證
        max_length = field_config.get('max_length')
        min_length = field_config.get('min_length')

        if min_length and len(extracted) < min_length:
            error_message = f"{field_label}至少需要 {min_length} 個字元"
            return (False, None, error_message)

        if max_length and len(extracted) > max_length:
            error_message = f"{field_label}不能超過 {max_length} 個字元"
            return (False, None, error_message)

        # 4. 使用自訂驗證器（基於 validation_type）
        if validation_type and validation_type in self.validators:
            is_valid, error_msg = self.validators[validation_type](extracted)
            if not is_valid:
                return (False, None, error_msg)

        # 驗證通過
        return (True, extracted, None)

    def _extract_value(self, user_input: str, field_type: str) -> str:
        """
        從用戶輸入中提取值（去除多餘文字）

        例如：
        - "我的電話是0912345678" → "0912345678"
        - "身分證號碼：A123456789" → "A123456789"
        """
        cleaned = user_input.strip()

        # 根據欄位類型使用不同的提取策略
        if field_type == 'phone':
            # 提取電話號碼（支援台灣手機和市話格式）
            match = re.search(r'09\d{8}|0\d{1,2}-\d{6,8}', cleaned)
            if match:
                return match.group(0)

        elif field_type == 'taiwan_id':
            # 提取台灣身分證號碼
            match = re.search(r'[A-Z][12]\d{8}', cleaned.upper())
            if match:
                return match.group(0).upper()

        elif field_type == 'email':
            # 提取 Email
            match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', cleaned)
            if match:
                return match.group(0)

        # 如果沒有特殊提取規則，返回清理後的原文
        return cleaned

    def _validate_phone(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        驗證台灣電話號碼

        支援格式：
        - 手機：09xxxxxxxx（10碼）
        - 市話：0x-xxxxxxxx 或 0xx-xxxxxxx
        """
        patterns = [
            r'^09\d{8}$',           # 手機
            r'^0\d{1}-\d{7,8}$',    # 市話（1碼區碼）
            r'^0\d{2}-\d{6,8}$'     # 市話（2碼區碼）
        ]

        for pattern in patterns:
            if re.match(pattern, value):
                return (True, None)

        return (False, "請輸入正確的台灣電話號碼格式（如：0912345678 或 02-12345678）")

    def _validate_taiwan_id(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        驗證台灣身分證號碼（含檢查碼驗證）

        格式：
        - 第1碼：英文字母（A-Z）
        - 第2碼：性別（1=男, 2=女）
        - 第3-10碼：數字
        - 第10碼：檢查碼
        """
        # 格式檢查
        if not re.match(r'^[A-Z][12]\d{8}$', value):
            return (False, "請輸入正確的身分證字號格式（如：A123456789）")

        # 檢查碼驗證
        # 英文字母對應數字表
        letter_values = {
            'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17,
            'I': 34, 'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'O': 35, 'P': 23,
            'Q': 24, 'R': 25, 'S': 26, 'T': 27, 'U': 28, 'V': 29, 'W': 32, 'X': 30,
            'Y': 31, 'Z': 33
        }

        # 轉換第一個字母為數字
        first_letter = value[0]
        letter_num = letter_values[first_letter]

        # 計算檢查碼
        digits = [letter_num // 10, letter_num % 10] + [int(d) for d in value[1:]]
        weights = [1, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1]

        total = sum(d * w for d, w in zip(digits, weights))

        if total % 10 != 0:
            return (False, "身分證字號檢查碼錯誤，請確認後重新輸入")

        return (True, None)

    def _validate_email(self, value: str) -> Tuple[bool, Optional[str]]:
        """驗證 Email 格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, value):
            return (True, None)
        return (False, "請輸入正確的 Email 格式（如：example@domain.com）")

    def _validate_taiwan_name(self, value: str) -> Tuple[bool, Optional[str]]:
        """驗證台灣姓名（中文或英文）"""
        # 允許中文姓名（2-10個中文字）或英文姓名（2-50個英文字母加空格）
        chinese_pattern = r'^[\u4e00-\u9fa5]{2,10}$'
        english_pattern = r'^[a-zA-Z\s]{2,50}$'

        if re.match(chinese_pattern, value) or re.match(english_pattern, value):
            return (True, None)
        return (False, "請輸入正確的姓名（中文2-10字或英文2-50字）")

    def _validate_address(self, value: str) -> Tuple[bool, Optional[str]]:
        """驗證地址（基本長度檢查）"""
        # 台灣地址通常至少5個字元（如：台北市）
        if len(value) >= 5:
            return (True, None)
        return (False, "請輸入完整的地址（至少5個字元）")


def mask_sensitive_data(field_name: str, value: str) -> str:
    """
    遮罩敏感資料用於顯示

    Args:
        field_name: 欄位名稱
        value: 原始值

    Returns:
        遮罩後的值
    """
    sensitive_fields = {
        'id_number': lambda v: f"{v[:3]}{'*' * 6}{v[-2:]}" if len(v) >= 10 else v,
        'phone': lambda v: f"{v[:4]}****{v[-3:]}" if len(v) >= 8 else v,
        'email': lambda v: v.split('@')[0][:3] + '***@' + v.split('@')[1] if '@' in v else v
    }

    if field_name in sensitive_fields:
        return sensitive_fields[field_name](value)

    return value
