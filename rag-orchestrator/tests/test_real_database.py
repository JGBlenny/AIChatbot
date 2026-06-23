"""
實際資料庫測試腳本
測試 VendorSOPRetriever 和 FormManager 的擴展功能

⚠️ STALE（spec testing-traceability 元件 8 / 任務 1.5）：
本檔針對 pre-v2 的 `services.vendor_sop_retriever.VendorSOPRetriever` 撰寫，
該模組已移除、API（retrieve_sop_by_intent / get_all_categories / retrieve_sop_by_*）
不存在於現行 `VendorSOPRetrieverV2`（僅 retrieve_sop_by_query）。
此處修正匯入使收集（collection）零錯誤，並以 module-level skip 隔離，
待依現行 V2 API 重寫後再移除 skip（非破壞性，保留歷史）。
"""
import sys
import os
import asyncio

import pytest

# 添加路徑（conftest.py 已統一處理，保留以相容直接執行）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 修正 stale import：原 services.vendor_sop_retriever 已移除，改指向 V2 並保留舊名別名，
# 使本檔在收集階段不致 ImportError。
from services.vendor_sop_retriever_v2 import VendorSOPRetrieverV2 as VendorSOPRetriever
from services.form_manager import FormManager, FormState
import asyncpg

# 隔離：本檔測試 pre-v2 已移除 API，標示 integration 並整檔略過（不假綠燈、不報收集錯）。
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="stale: 針對 pre-v2 VendorSOPRetriever（已移除）；待依 V2 API 重寫"
    ),
]


async def test_vendor_sop_retriever_extensions():
    """測試 VendorSOPRetriever 的 next_action 欄位擴展"""
    print("\n" + "=" * 80)
    print("🧪 測試 1: VendorSOPRetriever next_action 欄位擴展")
    print("=" * 80)

    retriever = VendorSOPRetriever()

    # 測試 1.1: retrieve_sop_by_intent
    print("\n--- 1.1 測試 retrieve_sop_by_intent ---")
    try:
        # 假設 vendor_id=1, intent_id=1 存在
        sop_items = retriever.retrieve_sop_by_intent(
            vendor_id=1,
            intent_id=1,
            top_k=3
        )

        if sop_items:
            print(f"✅ 成功檢索 {len(sop_items)} 個 SOP 項目")
            for idx, item in enumerate(sop_items, 1):
                print(f"\n項目 {idx}:")
                print(f"  ID: {item.get('id')}")
                print(f"  名稱: {item.get('item_name')[:50]}")
                print(f"  觸發模式: {item.get('trigger_mode', 'N/A')}")
                print(f"  後續動作: {item.get('next_action', 'N/A')}")
                print(f"  表單 ID: {item.get('next_form_id', 'N/A')}")
                print(f"  觸發關鍵詞: {item.get('trigger_keywords', [])}")

                # 檢查欄位是否存在
                has_all_fields = all([
                    'trigger_mode' in item,
                    'next_action' in item,
                    'next_form_id' in item,
                    'next_api_config' in item,
                    'trigger_keywords' in item
                ])

                if has_all_fields:
                    print(f"  ✅ 所有 next_action 欄位都已包含")
                else:
                    print(f"  ❌ 缺少某些 next_action 欄位")
        else:
            print("⚠️  未找到 SOP 項目（可能該意圖沒有關聯的 SOP）")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

    # 測試 1.2: retrieve_sop_by_category
    print("\n--- 1.2 測試 retrieve_sop_by_category ---")
    try:
        # 先獲取所有分類
        categories = retriever.get_all_categories(vendor_id=1)

        if categories:
            first_category = categories[0]
            print(f"測試分類: {first_category['category_name']}")

            sop_items = retriever.retrieve_sop_by_category(
                vendor_id=1,
                category_name=first_category['category_name']
            )

            if sop_items:
                print(f"✅ 成功檢索 {len(sop_items)} 個 SOP 項目")

                # 檢查第一個項目
                first_item = sop_items[0]
                print(f"\n第一個項目:")
                print(f"  觸發模式: {first_item.get('trigger_mode', 'N/A')}")
                print(f"  後續動作: {first_item.get('next_action', 'N/A')}")

                has_fields = 'trigger_mode' in first_item and 'next_action' in first_item
                print(f"  {'✅' if has_fields else '❌'} next_action 欄位存在")
            else:
                print("⚠️  該分類下沒有 SOP 項目")
        else:
            print("⚠️  未找到任何分類")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

    # 測試 1.3: retrieve_sop_by_group
    print("\n--- 1.3 測試 retrieve_sop_by_group ---")
    try:
        # 先獲取所有群組
        groups = retriever.get_all_groups(vendor_id=1)

        if groups:
            first_group = groups[0]
            print(f"測試群組: {first_group['group_name'][:50]}")

            sop_items = retriever.retrieve_sop_by_group(
                vendor_id=1,
                group_id=first_group['id']
            )

            if sop_items:
                print(f"✅ 成功檢索 {len(sop_items)} 個 SOP 項目")

                # 檢查第一個項目
                first_item = sop_items[0]
                print(f"\n第一個項目:")
                print(f"  ID: {first_item.get('id')}")
                print(f"  名稱: {first_item.get('item_name')[:40]}")
                print(f"  觸發模式: {first_item.get('trigger_mode', 'N/A')}")
                print(f"  後續動作: {first_item.get('next_action', 'N/A')}")
                print(f"  立即詢問: {first_item.get('immediate_prompt', 'N/A')[:50] if first_item.get('immediate_prompt') else 'N/A'}")

                has_fields = all([
                    'trigger_mode' in first_item,
                    'next_action' in first_item,
                    'immediate_prompt' in first_item,
                    'followup_prompt' in first_item
                ])
                print(f"  {'✅' if has_fields else '❌'} 所有擴展欄位存在")
            else:
                print("⚠️  該群組下沒有 SOP 項目")
        else:
            print("⚠️  未找到任何群組")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_form_manager_new_states():
    """測試 FormManager 的新狀態（PAUSED/CONFIRMING）"""
    print("\n" + "=" * 80)
    print("🧪 測試 2: FormManager PAUSED/CONFIRMING 狀態")
    print("=" * 80)

    # 建立資料庫連接池
    db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        min_size=1,
        max_size=2
    )

    try:
        form_manager = FormManager(db_pool=db_pool)

        # 測試 2.1: 創建測試會話
        print("\n--- 2.1 創建測試表單會話 ---")

        test_session_id = f"test_paused_{int(asyncio.get_event_loop().time())}"

        # 假設有一個表單 ID（需要存在於資料庫）
        # 這裡我們先檢查是否有可用的表單
        form_schema = await form_manager.get_form_schema("maintenance_request", vendor_id=1)

        if not form_schema:
            print("⚠️  找不到測試表單 'maintenance_request'，跳過測試")
            await db_pool.close()
            return

        print(f"✅ 找到測試表單: {form_schema.get('form_name')}")

        # 創建會話
        await form_manager.create_form_session(
            session_id=test_session_id,
            user_id="test_user",
            vendor_id=1,
            form_id="maintenance_request"
        )

        print(f"✅ 創建測試會話: {test_session_id}")

        # 測試 2.2: 測試 pause_form
        print("\n--- 2.2 測試 pause_form ---")

        pause_result = await form_manager.pause_form(
            session_id=test_session_id,
            reason="測試 SOP form_then_api 場景",
            metadata={
                "sop_id": 123,
                "api_config": {"endpoint": "/api/test"}
            }
        )

        print(f"暫停結果: {pause_result.get('form_paused')}")
        print(f"狀態: {pause_result.get('state')}")
        print(f"可恢復: {pause_result.get('can_resume')}")

        if pause_result.get('state') == FormState.PAUSED:
            print("✅ 表單成功暫停為 PAUSED 狀態")
        else:
            print("❌ 表單暫停失敗")

        # 測試 2.3: 檢查會話狀態
        print("\n--- 2.3 檢查暫停後的會話狀態 ---")

        session_state = await form_manager.get_session_state(test_session_id)

        if session_state:
            print(f"當前狀態: {session_state.get('state')}")
            print(f"元數據: {session_state.get('metadata')}")

            if session_state.get('state') == FormState.PAUSED:
                print("✅ 會話狀態正確儲存為 PAUSED")
            else:
                print(f"❌ 會話狀態不正確: {session_state.get('state')}")
        else:
            print("❌ 無法獲取會話狀態")

        # 測試 2.4: 測試 resume_form_filling (從 PAUSED 恢復)
        print("\n--- 2.4 測試從 PAUSED 狀態恢復 ---")

        resume_result = await form_manager.resume_form_filling(
            session_id=test_session_id,
            vendor_id=1
        )

        print(f"恢復結果: {resume_result.get('form_resumed')}")
        print(f"恢復來源: {resume_result.get('resumed_from')}")

        if resume_result.get('form_resumed') and resume_result.get('resumed_from') == FormState.PAUSED:
            print("✅ 成功從 PAUSED 狀態恢復")
        else:
            print("❌ 恢復失敗")

        # 測試 2.5: 再次檢查狀態
        print("\n--- 2.5 檢查恢復後的狀態 ---")

        session_state = await form_manager.get_session_state(test_session_id)

        if session_state:
            print(f"當前狀態: {session_state.get('state')}")

            if session_state.get('state') == FormState.COLLECTING:
                print("✅ 狀態已正確恢復為 COLLECTING")
            else:
                print(f"❌ 狀態不正確: {session_state.get('state')}")

        # 清理測試數據
        print("\n--- 清理測試數據 ---")
        await form_manager.cancel_form(test_session_id)
        print(f"✅ 已清理測試會話: {test_session_id}")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db_pool.close()


async def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("🚀 開始實際資料庫測試")
    print("=" * 80)

    # 測試 1: VendorSOPRetriever 擴展
    await test_vendor_sop_retriever_extensions()

    # 測試 2: FormManager 新狀態
    await test_form_manager_new_states()

    print("\n" + "=" * 80)
    print("✅ 所有測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
