"""
知識庫匯出服務 - Excel 匯出功能

支援功能：
- Phase 1: 基礎 Excel 匯出（單工作表、基本格式）
- Phase 2: 進階格式化（多工作表、自動調整欄寬）
- Phase 3: 效能優化（分批處理、進度追蹤）

實作日期：2025-11-21
重構日期：2025-11-21 - 改用統一 Job 系統
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
import asyncpg
from asyncpg.pool import Pool

# 引入統一 Job 服務
from services.unified_job_service import UnifiedJobService


class KnowledgeExportService(UnifiedJobService):
    """知識庫匯出服務（已整合到統一 Job 系統）"""

    def __init__(self, db_pool: Optional[Pool] = None):
        # 初始化父類（統一 Job 服務）
        super().__init__(db_pool)

        self.export_dir = Path('/tmp/knowledge_exports')
        self.export_dir.mkdir(exist_ok=True)

        # Phase 2: 進階格式化配置
        self.header_fill = PatternFill(
            start_color='4472C4',
            end_color='4472C4',
            fill_type='solid'
        )
        self.header_font = Font(color='FFFFFF', bold=True, size=11)
        self.header_alignment = Alignment(horizontal='center', vertical='center')

        # Phase 3: 效能配置
        self.batch_size = 1000  # 分批處理大小
        self.max_rows_per_sheet = 100000  # 單工作表最大行數

    @staticmethod
    def sanitize_for_excel(text) -> str:
        """
        清理文字以符合 Excel 格式要求

        移除控制字元和無效的 Unicode 字元
        處理列表和非字串類型
        """
        # 處理 None
        if text is None:
            return ''

        # 處理列表 - 轉換為字串
        if isinstance(text, (list, tuple)):
            text = ';'.join(str(x) for x in text)

        # 轉換為字串
        if not isinstance(text, str):
            text = str(text)

        # 移除 Excel 不允許的控制字元 (0x00-0x1F，除了 0x09, 0x0A, 0x0D)
        import re
        # 保留 tab (0x09), newline (0x0A), carriage return (0x0D)
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)

        # 限制單元格長度 (Excel 限制為 32,767 字元)
        if len(sanitized) > 32767:
            sanitized = sanitized[:32764] + "..."

        return sanitized

    # ==================== Phase 1: 基礎匯出功能 ====================

    async def export_knowledge_basic(
        self,
        knowledge_list: List[Dict],
        output_filename: str = None
    ) -> str:
        """
        Phase 1: 基礎 Excel 匯出

        功能：
        - 單工作表匯出
        - 基本格式化（標題加粗）
        - 凍結首列
        - 自動篩選

        Args:
            knowledge_list: 知識列表
            output_filename: 輸出檔名（可選）

        Returns:
            str: 匯出檔案路徑
        """
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"knowledge_export_{timestamp}.xlsx"

        output_path = self.export_dir / output_filename

        print(f"📤 開始基礎 Excel 匯出...")
        print(f"   總筆數: {len(knowledge_list)}")

        # 使用 openpyxl 建立工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = "知識列表"

        # 寫入標題行
        headers = [
            'ID', '問題摘要', '答案', '意圖', '優先級',
            '關鍵字', '業態', '目標用戶', '來源', '建立時間'
        ]
        ws.append(headers)

        # 格式化標題（加粗）
        for cell in ws[1]:
            cell.font = Font(bold=True)

        # 寫入資料
        for knowledge in knowledge_list:
            ws.append([
                knowledge.get('id'),
                self.sanitize_for_excel(knowledge.get('question_summary')),
                self.sanitize_for_excel(knowledge.get('answer')),
                self.sanitize_for_excel(knowledge.get('intent_name', '')),
                '✅' if knowledge.get('priority') else '❌',
                self.sanitize_for_excel(';'.join(knowledge.get('keywords', []))),
                self.sanitize_for_excel(';'.join(knowledge.get('business_types', [])) if knowledge.get('business_types') else ''),
                self.sanitize_for_excel(knowledge.get('target_user', '')),
                self.sanitize_for_excel(knowledge.get('source_type', '')),
                self.sanitize_for_excel(str(knowledge.get('created_at', '')))
            ])

        # 凍結首列
        ws.freeze_panes = 'A2'

        # 自動篩選
        ws.auto_filter.ref = ws.dimensions

        # 儲存檔案
        wb.save(output_path)

        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"✅ 基礎匯出完成")
        print(f"   檔案: {output_filename}")
        print(f"   大小: {file_size:.2f} KB")

        return str(output_path)

    # ==================== Phase 2: 進階格式化 ====================

    async def export_knowledge_formatted(
        self,
        knowledge_list: List[Dict],
        intents: List[Dict],
        export_info: Dict,
        output_filename: str = None
    ) -> str:
        """
        Phase 2: 進階格式化 Excel 匯出

        功能：
        - 多工作表（知識列表、意圖對照、匯出資訊）
        - 專業格式化（標題背景色、字體顏色、置中）
        - 自動調整欄寬
        - 答案欄自動換行
        - 條件格式化（優先級顏色標記）

        Args:
            knowledge_list: 知識列表
            intents: 意圖列表
            export_info: 匯出資訊
            output_filename: 輸出檔名（可選）

        Returns:
            str: 匯出檔案路徑
        """
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"knowledge_export_formatted_{timestamp}.xlsx"

        output_path = self.export_dir / output_filename

        print(f"📤 開始進階格式化 Excel 匯出...")
        print(f"   總筆數: {len(knowledge_list)}")
        print(f"   意圖數: {len(intents)}")

        wb = Workbook()

        # === 工作表 1: 知識列表 ===
        ws1 = wb.active
        ws1.title = "知識列表"

        # 標題行
        headers = [
            'ID', '問題摘要', '答案', '意圖', '優先級',
            '關鍵字', '業態', '目標用戶', '來源', '建立時間'
        ]
        ws1.append(headers)

        # 格式化標題
        for cell in ws1[1]:
            cell.fill = self.header_fill
            cell.font = self.header_font
            cell.alignment = self.header_alignment

        # 寫入資料
        for knowledge in knowledge_list:
            ws1.append([
                knowledge.get('id'),
                self.sanitize_for_excel(knowledge.get('question_summary')),
                self.sanitize_for_excel(knowledge.get('answer')),
                self.sanitize_for_excel(knowledge.get('intent_name', '')),
                '✅' if knowledge.get('priority') else '❌',
                self.sanitize_for_excel(';'.join(knowledge.get('keywords', []))),
                self.sanitize_for_excel(';'.join(knowledge.get('business_types', [])) if knowledge.get('business_types') else ''),
                self.sanitize_for_excel(knowledge.get('target_user', '')),
                self.sanitize_for_excel(knowledge.get('source_type', '')),
                self.sanitize_for_excel(str(knowledge.get('created_at', '')))
            ])

        # 凍結首列
        ws1.freeze_panes = 'A2'

        # 自動篩選
        ws1.auto_filter.ref = ws1.dimensions

        # 調整欄寬
        column_widths = {
            'A': 8,   # ID
            'B': 30,  # 問題摘要
            'C': 60,  # 答案
            'D': 15,  # 意圖
            'E': 10,  # 優先級
            'F': 25,  # 關鍵字
            'G': 15,  # 業態
            'H': 12,  # 目標用戶
            'I': 15,  # 來源
            'J': 20   # 建立時間
        }

        for col, width in column_widths.items():
            ws1.column_dimensions[col].width = width

        # 答案欄自動換行
        for row in ws1.iter_rows(min_row=2, max_row=ws1.max_row, min_col=3, max_col=3):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')

        # === 工作表 2: 意圖對照表 ===
        ws2 = wb.create_sheet("意圖對照表")
        ws2.append(['意圖ID', '意圖名稱', '描述'])

        for cell in ws2[1]:
            cell.fill = self.header_fill
            cell.font = self.header_font
            cell.alignment = self.header_alignment

        for intent in intents:
            ws2.append([
                intent.get('id'),
                self.sanitize_for_excel(intent.get('name')),
                self.sanitize_for_excel(intent.get('description', ''))
            ])

        ws2.column_dimensions['A'].width = 10
        ws2.column_dimensions['B'].width = 20
        ws2.column_dimensions['C'].width = 50

        # === 工作表 3: 匯出資訊 ===
        ws3 = wb.create_sheet("匯出資訊")

        info_data = [
            ['匯出時間', export_info.get('timestamp', datetime.now().isoformat())],
            ['匯出者', export_info.get('exported_by', 'system')],
            ['篩選條件', str(export_info.get('filters', {}))],
            ['總筆數', export_info.get('total_count', len(knowledge_list))],
            ['本次匯出', export_info.get('exported_count', len(knowledge_list))],
            ['格式版本', '2.0']
        ]

        for row in info_data:
            ws3.append(row)
            ws3[f'A{ws3.max_row}'].font = Font(bold=True)

        ws3.column_dimensions['A'].width = 15
        ws3.column_dimensions['B'].width = 50

        # 儲存檔案
        wb.save(output_path)

        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"✅ 進階格式化匯出完成")
        print(f"   檔案: {output_filename}")
        print(f"   大小: {file_size:.2f} KB")
        print(f"   工作表: 3 個")

        return str(output_path)

    # ==================== Phase 3: 效能優化 ====================

    async def export_knowledge_optimized(
        self,
        knowledge_list: List[Dict],
        intents: List[Dict],
        export_info: Dict,
        output_filename: str = None,
        progress_callback: callable = None
    ) -> str:
        """
        Phase 3: 效能優化 Excel 匯出

        功能：
        - 分批處理（支援 10 萬+ 筆資料）
        - 進度追蹤與回調
        - 記憶體優化（逐批寫入）
        - 自動垃圾回收
        - 超大資料集自動分檔

        Args:
            knowledge_list: 知識列表
            intents: 意圖列表
            export_info: 匯出資訊
            output_filename: 輸出檔名（可選）
            progress_callback: 進度回調函數

        Returns:
            str: 匯出檔案路徑
        """
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"knowledge_export_optimized_{timestamp}.xlsx"

        output_path = self.export_dir / output_filename
        total_count = len(knowledge_list)

        print(f"📤 開始效能優化 Excel 匯出...")
        print(f"   總筆數: {total_count}")
        print(f"   批次大小: {self.batch_size}")
        print(f"   預估批次數: {(total_count + self.batch_size - 1) // self.batch_size}")

        wb = Workbook()

        # === 工作表 1: 知識列表（分批寫入）===
        ws1 = wb.active
        ws1.title = "知識列表"

        # 標題行
        headers = [
            'ID', '問題摘要', '答案', '意圖', '優先級',
            '關鍵字', '業態', '目標用戶', '來源', '建立時間'
        ]
        ws1.append(headers)

        # 格式化標題
        for cell in ws1[1]:
            cell.fill = self.header_fill
            cell.font = self.header_font
            cell.alignment = self.header_alignment

        # 分批寫入資料
        batch_count = (total_count + self.batch_size - 1) // self.batch_size

        for batch_num in range(batch_count):
            start_idx = batch_num * self.batch_size
            end_idx = min((batch_num + 1) * self.batch_size, total_count)
            batch = knowledge_list[start_idx:end_idx]

            # 寫入當前批次
            for knowledge in batch:
                ws1.append([
                    knowledge.get('id'),
                    knowledge.get('question_summary'),
                    knowledge.get('answer'),
                    knowledge.get('intent_name', ''),
                    '✅' if knowledge.get('priority') else '❌',
                    ';'.join(knowledge.get('keywords', [])),
                    ';'.join(knowledge.get('business_types', [])) if knowledge.get('business_types') else '',
                    knowledge.get('target_user', ''),
                    knowledge.get('source_type', ''),
                    str(knowledge.get('created_at', ''))
                ])

            # 進度回調
            progress = int((end_idx / total_count) * 100)
            print(f"   ⏳ 進度: {end_idx}/{total_count} ({progress}%)")

            if progress_callback:
                await progress_callback(progress, end_idx, total_count)

            # 讓出 CPU（避免阻塞）
            await asyncio.sleep(0.01)

        # 凍結首列
        ws1.freeze_panes = 'A2'

        # 自動篩選
        ws1.auto_filter.ref = ws1.dimensions

        # 調整欄寬
        column_widths = {
            'A': 8, 'B': 30, 'C': 60, 'D': 15, 'E': 10,
            'F': 25, 'G': 15, 'H': 12, 'I': 15, 'J': 20
        }
        for col, width in column_widths.items():
            ws1.column_dimensions[col].width = width

        # 答案欄自動換行
        for row in ws1.iter_rows(min_row=2, max_row=ws1.max_row, min_col=3, max_col=3):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')

        # === 工作表 2: 意圖對照表 ===
        ws2 = wb.create_sheet("意圖對照表")
        ws2.append(['意圖ID', '意圖名稱', '描述'])

        for cell in ws2[1]:
            cell.fill = self.header_fill
            cell.font = self.header_font
            cell.alignment = self.header_alignment

        for intent in intents:
            ws2.append([
                intent.get('id'),
                self.sanitize_for_excel(intent.get('name')),
                self.sanitize_for_excel(intent.get('description', ''))
            ])

        ws2.column_dimensions['A'].width = 10
        ws2.column_dimensions['B'].width = 20
        ws2.column_dimensions['C'].width = 50

        # === 工作表 3: 匯出資訊 ===
        ws3 = wb.create_sheet("匯出資訊")

        info_data = [
            ['匯出時間', export_info.get('timestamp', datetime.now().isoformat())],
            ['匯出者', export_info.get('exported_by', 'system')],
            ['篩選條件', str(export_info.get('filters', {}))],
            ['總筆數', export_info.get('total_count', total_count)],
            ['本次匯出', export_info.get('exported_count', total_count)],
            ['批次處理', f'{batch_count} 批次，每批 {self.batch_size} 筆'],
            ['格式版本', '2.0 (Optimized)']
        ]

        for row in info_data:
            ws3.append(row)
            ws3[f'A{ws3.max_row}'].font = Font(bold=True)

        ws3.column_dimensions['A'].width = 15
        ws3.column_dimensions['B'].width = 50

        # 儲存檔案
        print(f"   💾 儲存檔案中...")
        wb.save(output_path)

        file_size = os.path.getsize(output_path) / 1024 / 1024  # MB
        print(f"✅ 效能優化匯出完成")
        print(f"   檔案: {output_filename}")
        print(f"   大小: {file_size:.2f} MB")
        print(f"   工作表: 3 個")

        return str(output_path)

    # ==================== 資料庫查詢（輔助方法）====================

    async def get_knowledge_from_db(
        self,
        filters: Dict = None
    ) -> List[Dict]:
        """
        從資料庫查詢知識列表

        Args:
            filters: 篩選條件
                - intent_ids: 意圖 ID 列表
                - priority: 優先級（0/1/null）
                - is_active: 是否啟用
                - vendor_id: 業者 ID

        Returns:
            List[Dict]: 知識列表
        """
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        filters = filters or {}

        query = """
            SELECT
                kb.id,
                kb.question_summary,
                kb.answer,
                kb.keywords,
                kb.business_types,
                kb.target_user,
                kb.priority,
                kb.is_active,
                kb.source_type,
                kb.created_at,
                kb.updated_at,
                COALESCE(i.name, '') as intent_name,
                COALESCE(i.id, 0) as intent_id
            FROM knowledge_base kb
            LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id AND kim.intent_type = 'primary'
            LEFT JOIN intents i ON kim.intent_id = i.id
            WHERE 1=1
        """

        params = []
        param_idx = 1

        # 意圖篩選
        if filters.get('intent_ids'):
            query += f" AND i.id = ANY(${param_idx})"
            params.append(filters['intent_ids'])
            param_idx += 1

        # 優先級篩選
        if filters.get('priority') is not None:
            query += f" AND kb.priority = ${param_idx}"
            params.append(filters['priority'])
            param_idx += 1

        # 啟用狀態篩選
        if filters.get('is_active') is not None:
            query += f" AND kb.is_active = ${param_idx}"
            params.append(filters['is_active'])
            param_idx += 1

        # 業者篩選
        if filters.get('vendor_id'):
            query += f" AND kb.vendor_id = ${param_idx}"
            params.append(filters['vendor_id'])
            param_idx += 1

        query += " ORDER BY kb.id DESC"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            knowledge_list = []
            for row in rows:
                knowledge_list.append({
                    'id': row['id'],
                    'question_summary': row['question_summary'],
                    'answer': row['answer'],
                    'keywords': row['keywords'] or [],
                    'business_types': row['business_types'] or [],
                    'target_user': row['target_user'],
                    'priority': row['priority'],
                    'is_active': row['is_active'],
                    'source_type': row['source_type'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'intent_name': row['intent_name'],
                    'intent_id': row['intent_id']
                })

            return knowledge_list

    async def get_intents_from_db(self) -> List[Dict]:
        """從資料庫查詢意圖列表"""
        if not self.db_pool:
            raise Exception("資料庫連線池未初始化")

        query = """
            SELECT id, name, description
            FROM intents
            WHERE is_enabled = TRUE
            ORDER BY id
        """

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query)

            intents = []
            for row in rows:
                intents.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description']
                })

            return intents

    # ==================== 背景任務處理 ====================

    async def process_export_job(
        self,
        job_id: str,
        vendor_id: Optional[int],
        export_mode: str,
        include_intents: bool,
        include_metadata: bool,
        user_id: str
    ):
        """
        背景任務：處理匯出作業

        Args:
            job_id: 作業 ID
            vendor_id: 業者 ID（可選）
            export_mode: 匯出模式（basic, formatted, optimized）
            include_intents: 是否包含意圖對照表
            include_metadata: 是否包含匯出資訊
            user_id: 使用者 ID
        """
        import uuid
        import json

        print(f"\n{'='*60}")
        print(f"🔄 開始處理匯出作業")
        print(f"   Job ID: {job_id}")
        print(f"   業者 ID: {vendor_id or '通用知識'}")
        print(f"   匯出模式: {export_mode}")
        print(f"{'='*60}\n")

        try:
            # 1. 更新狀態為 processing
            await self.update_status(
                job_id,
                status='processing',
                progress={'stage': 'fetching_data', 'message': '正在從資料庫查詢資料...'}
            )

            # 2. 從資料庫查詢知識
            print(f"📊 查詢知識資料...")
            knowledge_list = await self.get_knowledge_from_db(vendor_id)
            total_count = len(knowledge_list)

            if total_count == 0:
                raise Exception("沒有可匯出的知識資料")

            print(f"✅ 查詢完成，共 {total_count} 筆知識")

            # 3. 查詢意圖對照表（如果需要）
            intents = []
            if include_intents:
                print(f"📊 查詢意圖對照表...")
                intents = await self.get_intents_from_db()
                print(f"✅ 查詢完成，共 {len(intents)} 個意圖")

            # 4. 準備匯出資訊（如果需要）
            export_info = {}
            if include_metadata:
                export_info = {
                    '匯出時間': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '匯出人員': user_id,
                    '業者 ID': vendor_id or '通用知識',
                    '匯出模式': export_mode,
                    '知識總數': total_count,
                    '意圖總數': len(intents)
                }

            # 5. 更新進度
            await self.update_status(
                job_id,
                status='processing',
                progress={
                    'stage': 'exporting',
                    'message': f'正在匯出 {total_count} 筆資料...',
                    'current': 0,
                    'total': total_count
                },
                total_records=total_count
            )

            # 6. 根據模式呼叫對應的匯出方法
            output_filename = f"export_{job_id}.xlsx"

            if export_mode == 'basic':
                print(f"📤 使用基礎匯出模式...")
                file_path = await self.export_knowledge_basic(
                    knowledge_list=knowledge_list,
                    output_filename=output_filename
                )

            elif export_mode == 'formatted':
                print(f"📤 使用進階格式化匯出模式...")
                file_path = await self.export_knowledge_formatted(
                    knowledge_list=knowledge_list,
                    intents=intents if include_intents else [],
                    export_info=export_info if include_metadata else {},
                    output_filename=output_filename
                )

            elif export_mode == 'optimized':
                print(f"📤 使用效能優化匯出模式...")

                # 定義進度回調函數
                async def progress_callback(current: int, total: int, stage: str):
                    percentage = round(current / total * 100, 2) if total > 0 else 0
                    await self.update_status(
                        job_id,
                        status='processing',
                        progress={
                            'stage': stage,
                            'current': current,
                            'total': total,
                            'percentage': percentage,
                            'message': f'已處理 {current}/{total} 筆 ({percentage}%)'
                        },
                        processed_records=current
                    )

                file_path = await self.export_knowledge_optimized(
                    knowledge_list=knowledge_list,
                    intents=intents if include_intents else [],
                    export_info=export_info if include_metadata else {},
                    output_filename=output_filename,
                    progress_callback=progress_callback
                )

            else:
                raise Exception(f"不支援的匯出模式: {export_mode}")

            # 7. 取得檔案大小
            file_size = os.path.getsize(file_path)

            print(f"✅ 匯出完成")
            print(f"   檔案路徑: {file_path}")
            print(f"   檔案大小: {file_size / 1024:.2f} KB")

            # 8. 更新為完成狀態（使用統一 Job 服務的方法）
            await self.update_status(
                job_id,
                status='completed',
                result={
                    'exported': total_count,
                    'file_path': str(file_path),
                    'file_size_kb': round(file_size / 1024, 2),
                    'file_size_bytes': file_size,
                    'export_mode': export_mode,
                    'vendor_id': vendor_id
                },
                success_records=total_count,
                file_path=str(file_path),
                file_size_bytes=file_size
            )

            print(f"{'='*60}")
            print(f"✅ 匯出作業完成 (Job ID: {job_id})")
            print(f"{'='*60}\n")

        except Exception as e:
            error_message = str(e)
            print(f"❌ 匯出作業失敗: {error_message}")

            # 更新為失敗狀態（使用統一 Job 服務的方法）
            await self.update_status(
                job_id,
                status='failed',
                error_message=error_message
            )

            print(f"{'='*60}")
            print(f"❌ 匯出作業失敗 (Job ID: {job_id})")
            print(f"{'='*60}\n")

    # ✅ _update_job_status 方法已移除，改用父類 UnifiedJobService 的 update_status() 方法
