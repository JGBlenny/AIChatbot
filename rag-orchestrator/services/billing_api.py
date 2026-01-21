"""
帳單 API 服務

處理帳單相關的 API 調用：
- 查詢帳單狀態
- 驗證租客身份
- 重新發送帳單

注意：這是示例實作，實際環境中需要連接真實的帳單系統 API
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class BillingAPIService:
    """帳單 API 服務"""

    def __init__(self):
        """初始化 API 配置"""
        self.api_base_url = os.getenv('BILLING_API_BASE_URL', 'http://localhost:8000')
        self.api_key = os.getenv('BILLING_API_KEY', '')
        self.api_timeout = float(os.getenv('BILLING_API_TIMEOUT', '10.0'))

        # 是否使用模擬數據（開發/測試環境）
        self.use_mock = os.getenv('USE_MOCK_BILLING_API', 'true').lower() == 'true'

        logger.info(
            f"🔧 BillingAPIService 初始化 "
            f"(base_url={self.api_base_url}, use_mock={self.use_mock})"
        )

    async def get_invoice_status(
        self,
        user_id: str,
        month: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查詢帳單狀態

        Args:
            user_id: 租客 ID
            month: 查詢月份（格式：YYYY-MM），None 表示查詢最近一期

        Returns:
            {
                'success': True,
                'invoice_id': '帳單編號',
                'month': '帳單月份',
                'amount': 金額,
                'status': '狀態',
                'sent_date': '發送日期',
                'due_date': '到期日',
                'message': '格式化訊息'
            }
        """
        if self.use_mock:
            return self._mock_get_invoice_status(user_id, month)

        try:
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/billing/invoice",
                    params={'user_id': user_id, 'month': month},
                    headers={'X-API-Key': self.api_key}
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"❌ 帳單查詢 API 失敗: {e}")
            return {
                'success': False,
                'error': f"帳單查詢失敗: {str(e)}",
                'message': '⚠️ 目前無法查詢帳單，請稍後再試或聯繫客服。'
            }

    async def verify_tenant_identity(
        self,
        tenant_id: str,
        id_last_4: str
    ) -> Dict[str, Any]:
        """
        驗證租客身份

        Args:
            tenant_id: 租客編號
            id_last_4: 身分證後 4 碼

        Returns:
            {
                'verified': True/False,
                'message': '驗證訊息'
            }
        """
        if self.use_mock:
            return self._mock_verify_tenant_identity(tenant_id, id_last_4)

        try:
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/billing/verify",
                    json={'tenant_id': tenant_id, 'id_last_4': id_last_4},
                    headers={'X-API-Key': self.api_key}
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"❌ 身份驗證 API 失敗: {e}")
            return {
                'verified': False,
                'message': '⚠️ 目前無法驗證身份，請稍後再試或聯繫客服。'
            }

    async def resend_invoice(
        self,
        user_id: str,
        invoice_id: str
    ) -> Dict[str, Any]:
        """
        重新發送帳單

        Args:
            user_id: 租客 ID
            invoice_id: 帳單編號

        Returns:
            {
                'success': True/False,
                'message': '操作結果訊息'
            }
        """
        if self.use_mock:
            return self._mock_resend_invoice(user_id, invoice_id)

        try:
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/billing/resend",
                    json={'user_id': user_id, 'invoice_id': invoice_id},
                    headers={'X-API-Key': self.api_key}
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"❌ 重新發送帳單 API 失敗: {e}")
            return {
                'success': False,
                'message': '⚠️ 目前無法重新發送帳單，請稍後再試或聯繫客服。'
            }

    # ==========================================
    # 模擬實作（開發/測試用）
    # ==========================================

    def _mock_get_invoice_status(
        self,
        user_id: str,
        month: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        模擬帳單查詢（用於開發測試）

        方式 2：只返回原始數據，由系統自動格式化
        """
        logger.info(f"🧪 [MOCK] 查詢帳單: user_id={user_id}, month={month}")

        # 模擬不同場景
        if user_id == 'test_no_data':
            # 場景 1: 無帳單資料
            return {
                'success': False,
                'error': 'no_invoice_found',
                'error_type': '查無帳單資料',
                'suggestion': '您查詢的期間目前尚無帳單記錄'
            }

        if user_id == 'test_not_sent':
            # 場景 2: 尚未到發送時間
            next_send_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            return {
                'success': False,
                'error': 'not_sent_yet',
                'error_type': '帳單尚未發送',
                'next_send_date': next_send_date
            }

        # 場景 3: 正常查詢到帳單（只返回原始數據）
        current_month = month or datetime.now().strftime('%Y-%m')
        sent_date = f"{current_month}-01"
        due_date = f"{current_month}-15"

        return {
            'success': True,
            'invoice_id': f'INV-{user_id}-{current_month}',
            'month': current_month,
            'amount': 15000,
            'status': 'sent',
            'sent_date': sent_date,
            'due_date': due_date,
            'email': f"{user_id}@example.com"
            # ⭐ 注意：沒有 'message' 欄位，讓系統自動格式化
        }

    def _mock_verify_tenant_identity(
        self,
        tenant_id: str,
        id_last_4: str
    ) -> Dict[str, Any]:
        """模擬身份驗證（用於開發測試）"""
        logger.info(f"🧪 [MOCK] 驗證身份: tenant_id={tenant_id}, id_last_4={id_last_4}")

        # 模擬驗證邏輯：測試用戶的後 4 碼為 "1234"
        if tenant_id.startswith('test_') and id_last_4 == '1234':
            return {
                'verified': True,
                'message': '✅ 身份驗證成功'
            }

        return {
            'verified': False,
            'message': '❌ 身份驗證失敗，請確認您的租客編號和身分證後 4 碼是否正確。'
        }

    def _mock_resend_invoice(
        self,
        user_id: str,
        invoice_id: str
    ) -> Dict[str, Any]:
        """模擬重新發送帳單（用於開發測試）"""
        logger.info(f"🧪 [MOCK] 重新發送帳單: user_id={user_id}, invoice_id={invoice_id}")

        return {
            'success': True,
            'message': (
                '✅ **帳單已重新發送**\n\n'
                f'帳單編號 {invoice_id} 已重新發送至您的註冊郵箱，請注意查收。\n\n'
                '如仍未收到，請檢查垃圾郵件夾或聯繫客服。'
            )
        }

    async def submit_maintenance_request(
        self,
        user_id: str,
        location: str,
        description: str,
        urgency: str,
        contact_time: Optional[str] = None
    ) -> str:
        """
        提交報修申請

        Args:
            user_id: 用戶 ID
            location: 報修地點
            description: 問題描述
            urgency: 緊急程度
            contact_time: 方便聯繫時間

        Returns:
            報修單號
        """
        if self.use_mock:
            return self._mock_submit_maintenance_request(
                user_id, location, description, urgency, contact_time
            )

        try:
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/maintenance/submit",
                    json={
                        'user_id': user_id,
                        'location': location,
                        'description': description,
                        'urgency': urgency,
                        'contact_time': contact_time
                    },
                    headers={'X-API-Key': self.api_key}
                )
                response.raise_for_status()
                return response.json().get('ticket_id', 'UNKNOWN')

        except httpx.HTTPError as e:
            logger.error(f"❌ 報修申請 API 失敗: {e}")
            return "ERROR"

    def _mock_submit_maintenance_request(
        self,
        user_id: str,
        location: str,
        description: str,
        urgency: str,
        contact_time: Optional[str] = None
    ) -> str:
        """模擬報修申請（用於開發測試）"""
        import random
        ticket_id = f"MNT-{random.randint(100000, 999999)}"
        logger.info(f"🧪 [MOCK] 報修申請: user={user_id}, location={location}, urgency={urgency}, ticket={ticket_id}")
        return ticket_id


# ==========================================
# 環境變數設置說明
# ==========================================
"""
在 .env 文件中配置以下變數：

# 帳單 API 配置
BILLING_API_BASE_URL=http://your-billing-api.com
BILLING_API_KEY=your_secret_api_key
BILLING_API_TIMEOUT=10.0

# 開發/測試模式（使用模擬數據）
USE_MOCK_BILLING_API=true

# 生產環境請設置為 false 並配置真實的 API endpoint
"""
