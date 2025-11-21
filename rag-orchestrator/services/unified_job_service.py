"""
統一 Job 管理服務 - 基類

用途：為所有異步作業（匯入、匯出、轉換等）提供統一的 CRUD 介面
特點：
- 統一狀態管理（pending → processing → completed/failed）
- 統一進度追蹤
- 統一錯誤處理
- 彈性配置（JSONB）

使用方式：
    class KnowledgeImportService(UnifiedJobService):
        async def process_import_job(self, job_id, ...):
            await self.update_status(job_id, 'processing')
            # ... 處理邏輯
            await self.update_status(job_id, 'completed', result={...})

實作日期：2025-11-21
相關文件：docs/planning/UNIFIED_JOB_SYSTEM_DESIGN.md
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from asyncpg.pool import Pool
import asyncpg


class UnifiedJobService:
    """統一 Job 管理服務（基類）"""

    def __init__(self, db_pool: Optional[Pool] = None):
        """
        初始化統一 Job 服務

        Args:
            db_pool: 資料庫連接池
        """
        self.db_pool = db_pool

    # ==================== Job 生命週期管理 ====================

    async def create_job(
        self,
        job_type: str,
        vendor_id: Optional[int],
        user_id: str,
        job_config: Dict,
        file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        expires_days: int = 7
    ) -> str:
        """
        創建新作業

        Args:
            job_type: 作業類型（knowledge_import, knowledge_export, document_convert 等）
            vendor_id: 業者 ID（None 表示通用知識）
            user_id: 使用者 ID
            job_config: 作業配置（JSONB，類型特定參數）
            file_path: 檔案路徑（可選）
            file_name: 檔案名稱（可選）
            file_size_bytes: 檔案大小（可選）
            expires_days: 檔案過期天數（預設 7 天）

        Returns:
            str: Job ID
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        job_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=expires_days) if file_path else None

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO unified_jobs (
                    job_id, job_type, vendor_id, user_id,
                    status, job_config,
                    file_path, file_name, file_size_bytes, expires_at,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
                uuid.UUID(job_id),
                job_type,
                vendor_id,
                user_id,
                'pending',
                json.dumps(job_config),
                file_path,
                file_name,
                file_size_bytes,
                expires_at
            )

        print(f"✅ 作業已創建")
        print(f"   Job ID: {job_id}")
        print(f"   類型: {job_type}")
        print(f"   業者 ID: {vendor_id or '通用知識'}")

        return job_id

    async def update_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[Dict] = None,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict] = None,
        **record_updates
    ):
        """
        更新作業狀態

        Args:
            job_id: 作業 ID
            status: 新狀態（pending, processing, completed, failed, cancelled）
            progress: 進度資訊（可選）
            result: 結果資訊（可選）
            error_message: 錯誤訊息（可選）
            error_details: 詳細錯誤資訊（可選）
            **record_updates: 其他欄位更新（如 total_records, processed_records 等）
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        # 建構更新 SQL
        update_parts = ["status = $2", "updated_at = CURRENT_TIMESTAMP"]
        params = [uuid.UUID(job_id), status]
        param_index = 3

        if progress is not None:
            update_parts.append(f"progress = ${param_index}")
            params.append(json.dumps(progress))
            param_index += 1

        if result is not None:
            update_parts.append(f"job_result = ${param_index}")
            params.append(json.dumps(result))
            param_index += 1

        if error_message is not None:
            update_parts.append(f"error_message = ${param_index}")
            params.append(error_message)
            param_index += 1

        if error_details is not None:
            update_parts.append(f"error_details = ${param_index}")
            params.append(json.dumps(error_details))
            param_index += 1

        # 處理其他欄位更新
        for key, value in record_updates.items():
            update_parts.append(f"{key} = ${param_index}")
            params.append(value)
            param_index += 1

        sql = f"""
            UPDATE unified_jobs
            SET {', '.join(update_parts)}
            WHERE job_id = $1
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def get_job(self, job_id: str) -> Optional[Dict]:
        """
        獲取作業詳情

        Args:
            job_id: 作業 ID

        Returns:
            Optional[Dict]: 作業資訊，不存在則返回 None
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    job_id, job_type, vendor_id, user_id,
                    status, progress, job_config, job_result,
                    error_message, error_details,
                    total_records, processed_records, success_records, failed_records, skipped_records,
                    file_path, file_name, file_size_bytes,
                    created_at, updated_at, started_at, completed_at,
                    processing_time_seconds, expires_at
                FROM unified_jobs
                WHERE job_id = $1
            """, uuid.UUID(job_id))

            if not row:
                return None

            # 解析 JSON 欄位
            return {
                'job_id': str(row['job_id']),
                'job_type': row['job_type'],
                'vendor_id': row['vendor_id'],
                'user_id': row['user_id'],
                'status': row['status'],
                'progress': json.loads(row['progress']) if row['progress'] else None,
                'config': json.loads(row['job_config']) if row['job_config'] else None,
                'result': json.loads(row['job_result']) if row['job_result'] else None,
                'error_message': row['error_message'],
                'error_details': json.loads(row['error_details']) if row['error_details'] else None,
                'total_records': row['total_records'],
                'processed_records': row['processed_records'],
                'success_records': row['success_records'],
                'failed_records': row['failed_records'],
                'skipped_records': row['skipped_records'],
                'file_path': row['file_path'],
                'file_name': row['file_name'],
                'file_size_bytes': row['file_size_bytes'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                'processing_time_seconds': row['processing_time_seconds'],
                'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None
            }

    async def list_jobs(
        self,
        job_type: Optional[str] = None,
        vendor_id: Optional[int] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict:
        """
        列出作業（支援多維度過濾）

        Args:
            job_type: 作業類型（可選）
            vendor_id: 業者 ID（可選）
            user_id: 使用者 ID（可選）
            status: 狀態（可選）
            limit: 返回數量限制
            offset: 偏移量

        Returns:
            Dict: {jobs: List[Dict], total: int, limit: int, offset: int}
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        # 建構 WHERE 條件
        where_parts = []
        params = []
        param_index = 1

        if job_type is not None:
            where_parts.append(f"job_type = ${param_index}")
            params.append(job_type)
            param_index += 1

        if vendor_id is not None:
            where_parts.append(f"vendor_id = ${param_index}")
            params.append(vendor_id)
            param_index += 1

        if user_id is not None:
            where_parts.append(f"user_id = ${param_index}")
            params.append(user_id)
            param_index += 1

        if status is not None:
            where_parts.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # 添加 limit 和 offset
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            # 查詢列表
            rows = await conn.fetch(f"""
                SELECT
                    job_id, job_type, vendor_id, status,
                    total_records, processed_records, success_records,
                    file_name, file_size_bytes,
                    created_at, completed_at, processing_time_seconds
                FROM unified_jobs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_index} OFFSET ${param_index + 1}
            """, *params)

            # 查詢總數
            total = await conn.fetchval(f"""
                SELECT COUNT(*) FROM unified_jobs {where_clause}
            """, *params[:-2])  # 排除 limit 和 offset

            jobs = [
                {
                    'job_id': str(row['job_id']),
                    'job_type': row['job_type'],
                    'vendor_id': row['vendor_id'],
                    'status': row['status'],
                    'total_records': row['total_records'],
                    'processed_records': row['processed_records'],
                    'success_records': row['success_records'],
                    'file_name': row['file_name'],
                    'file_size_bytes': row['file_size_bytes'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                    'processing_time_seconds': row['processing_time_seconds']
                }
                for row in rows
            ]

            return {
                'jobs': jobs,
                'total': total,
                'limit': limit,
                'offset': offset
            }

    async def delete_job(self, job_id: str, delete_file: bool = True):
        """
        刪除作業（含檔案）

        Args:
            job_id: 作業 ID
            delete_file: 是否刪除關聯的檔案（預設 True）
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        async with self.db_pool.acquire() as conn:
            # 取得檔案路徑
            job = await self.get_job(job_id)
            if not job:
                raise Exception(f"作業不存在: {job_id}")

            # 刪除實體檔案
            if delete_file and job.get('file_path'):
                import os
                file_path = job['file_path']
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"✅ 已刪除檔案: {file_path}")
                    except Exception as e:
                        print(f"⚠️ 無法刪除檔案: {e}")

            # 刪除資料庫記錄
            await conn.execute("""
                DELETE FROM unified_jobs WHERE job_id = $1
            """, uuid.UUID(job_id))

            print(f"✅ 作業已刪除 (job_id: {job_id})")

    async def cancel_job(self, job_id: str, reason: str = "使用者取消"):
        """
        取消作業

        Args:
            job_id: 作業 ID
            reason: 取消原因
        """
        await self.update_status(
            job_id,
            status='cancelled',
            error_message=reason
        )
        print(f"⚠️ 作業已取消 (job_id: {job_id}): {reason}")

    # ==================== 統計與監控 ====================

    async def get_statistics(
        self,
        job_type: Optional[str] = None,
        vendor_id: Optional[int] = None,
        days: int = 30
    ) -> Dict:
        """
        獲取統計資訊

        Args:
            job_type: 作業類型（可選，None 表示所有類型）
            vendor_id: 業者 ID（可選）
            days: 統計天數

        Returns:
            Dict: 統計資訊
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        # 建構 WHERE 條件
        where_parts = [f"created_at > CURRENT_TIMESTAMP - INTERVAL '{days} days'"]
        params = []
        param_index = 1

        if job_type is not None:
            where_parts.append(f"job_type = ${param_index}")
            params.append(job_type)
            param_index += 1

        if vendor_id is not None:
            where_parts.append(f"vendor_id = ${param_index}")
            params.append(vendor_id)
            param_index += 1

        where_clause = ' AND '.join(where_parts)

        async with self.db_pool.acquire() as conn:
            # 基礎統計
            stats = await conn.fetchrow(f"""
                SELECT
                    COUNT(*) as total_jobs,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_jobs,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_jobs,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing_jobs,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_jobs,
                    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_jobs,
                    COALESCE(SUM(total_records), 0) as total_records_sum,
                    COALESCE(SUM(success_records), 0) as success_records_sum,
                    COALESCE(SUM(failed_records), 0) as failed_records_sum,
                    COALESCE(AVG(processing_time_seconds), 0) as avg_processing_time
                FROM unified_jobs
                WHERE {where_clause}
            """, *params)

            # 按類型統計（如果沒有指定 job_type）
            by_type = None
            if job_type is None:
                type_stats = await conn.fetch(f"""
                    SELECT
                        job_type,
                        COUNT(*) as count,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed,
                        AVG(processing_time_seconds) as avg_time
                    FROM unified_jobs
                    WHERE {where_clause}
                    GROUP BY job_type
                    ORDER BY count DESC
                """, *params)

                by_type = [
                    {
                        'type': row['job_type'],
                        'count': row['count'],
                        'completed': row['completed'],
                        'avg_time_seconds': round(float(row['avg_time']), 2) if row['avg_time'] else 0
                    }
                    for row in type_stats
                ]

            # 計算成功率
            total = stats['total_jobs'] or 0
            completed = stats['completed_jobs'] or 0
            success_rate = (completed / total * 100) if total > 0 else 0

            return {
                'total_jobs': total,
                'completed_jobs': completed,
                'failed_jobs': stats['failed_jobs'],
                'processing_jobs': stats['processing_jobs'],
                'pending_jobs': stats['pending_jobs'],
                'cancelled_jobs': stats['cancelled_jobs'],
                'total_records_processed': stats['total_records_sum'],
                'success_records': stats['success_records_sum'],
                'failed_records': stats['failed_records_sum'],
                'avg_processing_time_seconds': round(float(stats['avg_processing_time']), 2),
                'success_rate': round(success_rate, 2),
                'by_type': by_type,
                'days': days
            }

    # ==================== 清理與維護 ====================

    async def cleanup_expired_jobs(self, dry_run: bool = True) -> Dict:
        """
        清理過期的作業檔案

        Args:
            dry_run: 是否為模擬運行（不實際刪除）

        Returns:
            Dict: 清理統計
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        async with self.db_pool.acquire() as conn:
            # 查詢過期的 jobs
            expired_jobs = await conn.fetch("""
                SELECT job_id, file_path
                FROM unified_jobs
                WHERE expires_at IS NOT NULL
                  AND expires_at < CURRENT_TIMESTAMP
                  AND status = 'completed'
            """)

            deleted_count = 0
            deleted_size = 0

            for job in expired_jobs:
                job_id = str(job['job_id'])
                file_path = job['file_path']

                if not dry_run:
                    try:
                        await self.delete_job(job_id, delete_file=True)
                        deleted_count += 1
                    except Exception as e:
                        print(f"⚠️ 清理失敗 (job_id: {job_id}): {e}")
                else:
                    deleted_count += 1
                    print(f"🔍 [模擬] 將刪除: {job_id} ({file_path})")

            return {
                'deleted_count': deleted_count,
                'dry_run': dry_run,
                'message': f"{'[模擬運行] ' if dry_run else ''}已清理 {deleted_count} 個過期作業"
            }
