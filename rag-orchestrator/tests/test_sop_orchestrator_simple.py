"""
SOP Orchestrator 簡化實際環境測試
驗證核心組件集成和基本流程
"""
import sys
import os
import asyncio

# 添加路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.sop_orchestrator import SOPOrchestrator
from services.form_manager import FormManager
from services.sop_trigger_handler import SOPTriggerHandler
from services.sop_next_action_handler import SOPNextActionHandler
import asyncpg


async def test_component_initialization(db_pool):
    """測試所有組件的初始化"""
    print("\n" + "=" * 80)
    print("🧪 測試 1: 組件初始化")
    print("=" * 80)

    try:
        form_manager = FormManager(db_pool=db_pool)
        orchestrator = SOPOrchestrator(form_manager=form_manager)

        print("✅ FormManager 初始化成功")
        print("✅ SOPOrchestrator 初始化成功")

        # 檢查組件
        assert orchestrator.trigger_handler is not None, "trigger_handler 未初始化"
        assert orchestrator.next_action_handler is not None, "next_action_handler 未初始化"
        assert orchestrator.keyword_matcher is not None, "keyword_matcher 未初始化"
        assert orchestrator.sop_retriever is not None, "sop_retriever 未初始化"

        print("✅ TriggerHandler 已初始化")
        print("✅ NextActionHandler 已初始化")
        print("✅ KeywordMatcher 已初始化")
        print("✅ SOPRetriever 已初始化")

        # 驗證類型
        assert isinstance(orchestrator.trigger_handler, SOPTriggerHandler)
        assert isinstance(orchestrator.next_action_handler, SOPNextActionHandler)

        print("✅ 所有組件類型正確")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_trigger_handler_context(db_pool):
    """測試 Trigger Handler 的 Context 操作"""
    print("\n" + "=" * 80)
    print("🧪 測試 2: Trigger Handler Context 操作")
    print("=" * 80)

    try:
        form_manager = FormManager(db_pool=db_pool)
        orchestrator = SOPOrchestrator(form_manager=form_manager)
        trigger_handler = orchestrator.trigger_handler

        session_id = "test_context_ops"

        # 測試 2.1: 通過 handle_trigger 儲存 context (manual 模式)
        print("\n--- 2.1 觸發 manual 模式（會儲存 context） ---")
        result = await trigger_handler.handle_trigger(
            sop_item={
                'id': 9999,
                'item_name': '測試 SOP',
                'content': '測試內容',
                'trigger_mode': 'manual',
                'next_action': 'form_fill',
                'next_form_id': 'test_form',
                'trigger_keywords': ['觸發', '確認'],
                'followup_prompt': '準備好了嗎？'
            },
            user_message="測試訊息",
            session_id=session_id,
            vendor_id=1
        )

        if result.get('context_saved'):
            print("✅ Context 儲存成功")
        else:
            print("❌ Context 未儲存")

        # 測試 2.2: 檢索 context
        print("\n--- 2.2 檢索 context ---")
        context = trigger_handler.get_context(session_id)
        if context:
            print(f"✅ Context 檢索成功")
            print(f"   SOP ID: {context.get('sop_id')}")
            print(f"   Trigger Mode: {context.get('trigger_mode')}")
            print(f"   Next Action: {context.get('next_action')}")
        else:
            print("❌ Context 檢索失敗")

        # 測試 2.3: 刪除 context
        print("\n--- 2.3 刪除 context ---")
        deleted = trigger_handler.delete_context(session_id)
        if deleted:
            print("✅ Context 刪除成功")
        else:
            print("⚠️  Context 可能不存在或已刪除")

        # 測試 2.4: 驗證刪除
        print("\n--- 2.4 驗證刪除 ---")
        context_after = trigger_handler.get_context(session_id)
        if context_after is None:
            print("✅ Context 已被正確刪除")
        else:
            print("❌ Context 未被刪除")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_trigger_handler(db_pool):
    """測試 Trigger Handler 的觸發邏輯"""
    print("\n" + "=" * 80)
    print("🧪 測試 3: Trigger Handler")
    print("=" * 80)

    try:
        form_manager = FormManager(db_pool=db_pool)
        orchestrator = SOPOrchestrator(form_manager=form_manager)
        trigger_handler = orchestrator.trigger_handler

        # 測試 3.1: none 模式
        print("\n--- 3.1 測試 none 模式 ---")
        result_none = await trigger_handler.handle_trigger(
            sop_item={
                'id': 1,
                'item_name': 'None 模式測試',
                'content': '這是純資訊',
                'trigger_mode': 'none',
                'next_action': 'none'
            },
            user_message="測試訊息",
            session_id="test_none"
        )

        print(f"action: {result_none.get('action')}")
        print(f"should_trigger: {result_none.get('should_trigger')}")
        print(f"context_saved: {result_none.get('context_saved')}")

        if result_none.get('action') == 'provide_info' and not result_none.get('should_trigger'):
            print("✅ none 模式處理正確")
        else:
            print("❌ none 模式處理異常")

        # 測試 3.2: manual 模式
        print("\n--- 3.2 測試 manual 模式 ---")
        result_manual = await trigger_handler.handle_trigger(
            sop_item={
                'id': 2,
                'item_name': 'Manual 模式測試',
                'content': '請先排查',
                'trigger_mode': 'manual',
                'next_action': 'form_fill',
                'next_form_id': 'test_form',
                'trigger_keywords': ['還是不行', '試過了'],
                'followup_prompt': '如果還是不行，可以填表單'
            },
            user_message="測試訊息",
            session_id="test_manual",
            vendor_id=1
        )

        print(f"action: {result_manual.get('action')}")
        print(f"context_saved: {result_manual.get('context_saved')}")

        if result_manual.get('action') == 'provide_info_and_wait' and result_manual.get('context_saved'):
            print("✅ manual 模式處理正確（已儲存 context）")
        else:
            print("❌ manual 模式處理異常")

        # 測試 3.3: immediate 模式
        print("\n--- 3.3 測試 immediate 模式 ---")
        result_immediate = await trigger_handler.handle_trigger(
            sop_item={
                'id': 3,
                'item_name': 'Immediate 模式測試',
                'content': '立即詢問',
                'trigger_mode': 'immediate',
                'next_action': 'api_call',
                'next_api_config': {'endpoint': '/test'},
                'trigger_keywords': ['是', '要'],
                'immediate_prompt': '請問要執行嗎？'
            },
            user_message="測試訊息",
            session_id="test_immediate",
            vendor_id=1
        )

        print(f"action: {result_immediate.get('action')}")
        print(f"context_saved: {result_immediate.get('context_saved')}")

        if result_immediate.get('action') == 'ask_immediate_confirmation':
            print("✅ immediate 模式處理正確")
        else:
            print("❌ immediate 模式處理異常")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_next_action_handler(db_pool):
    """測試 Next Action Handler 的動作處理"""
    print("\n" + "=" * 80)
    print("🧪 測試 4: Next Action Handler")
    print("=" * 80)

    try:
        form_manager = FormManager(db_pool=db_pool)
        orchestrator = SOPOrchestrator(form_manager=form_manager)
        action_handler = orchestrator.next_action_handler

        # 測試 4.1: form_fill 動作
        print("\n--- 4.1 測試 form_fill 動作 ---")
        result_form = await action_handler.execute_action(
            next_action="form_fill",
            session_id="test_form_action",
            vendor_id=1,
            form_id="maintenance_request",
            api_config=None
        )

        print(f"success: {result_form.get('success')}")
        print(f"action_type: {result_form.get('action_type')}")
        print(f"form_id: {result_form.get('form_id')}")

        if result_form.get('success') and result_form.get('action_type') == 'form_fill':
            print("✅ form_fill 動作處理正確")
        else:
            print("❌ form_fill 動作處理異常")

        # 測試 4.2: api_call 動作（模擬）
        print("\n--- 4.2 測試 api_call 動作 ---")
        result_api = await action_handler.execute_action(
            next_action="api_call",
            session_id="test_api_action",
            vendor_id=1,
            form_id=None,
            api_config={
                'endpoint': '/api/test',
                'method': 'POST',
                'params': ['param1', 'param2']
            }
        )

        print(f"success: {result_api.get('success')}")
        print(f"action_type: {result_api.get('action_type')}")

        if result_api.get('action_type') == 'api_call':
            print("✅ api_call 動作處理正確（模擬）")
        else:
            print("❌ api_call 動作處理異常")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_context_ttl(db_pool):
    """測試 Context 的 TTL 過期（使用內存存儲）"""
    print("\n" + "=" * 80)
    print("🧪 測試 5: Context TTL 過期")
    print("=" * 80)

    print("⚠️  注意：此測試使用內存存儲（未安裝 Redis）")
    print("   內存存儲不支持 TTL，Context 不會自動過期")
    print("   如需測試真實 TTL 功能，請安裝並配置 Redis")

    try:
        form_manager = FormManager(db_pool=db_pool)
        orchestrator = SOPOrchestrator(form_manager=form_manager)
        trigger_handler = orchestrator.trigger_handler

        session_id = "test_ttl"

        # 通過 handle_trigger 儲存 context
        print("\n--- 儲存 context (manual 模式) ---")
        result = await trigger_handler.handle_trigger(
            sop_item={
                'id': 888,
                'item_name': 'TTL 測試',
                'content': '測試 TTL',
                'trigger_mode': 'manual',
                'next_action': 'form_fill',
                'next_form_id': 'test_form',
                'trigger_keywords': ['測試'],
                'followup_prompt': '測試提示'
            },
            user_message="測試訊息",
            session_id=session_id,
            vendor_id=1
        )

        if result.get('context_saved'):
            print("✅ Context 已儲存")
        else:
            print("❌ Context 未儲存")

        # 立即檢查
        context1 = trigger_handler.get_context(session_id)
        if context1:
            print("✅ Context 存在（立即檢查）")
        else:
            print("❌ Context 不存在（不應該）")

        # 手動刪除 context（模擬過期）
        print("\n--- 手動刪除 context （模擬過期） ---")
        trigger_handler.delete_context(session_id)

        # 再次檢查
        context2 = trigger_handler.get_context(session_id)
        if context2 is None:
            print("✅ Context 已刪除（模擬過期成功）")
        else:
            print(f"❌ Context 仍存在: {context2}")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("🚀 開始 SOP Orchestrator 簡化實際環境測試")
    print("=" * 80)

    # 建立資料庫連接池
    db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        min_size=1,
        max_size=5
    )

    try:
        # 測試 1: 組件初始化
        await test_component_initialization(db_pool)

        # 測試 2: Trigger Handler Context 操作
        await test_trigger_handler_context(db_pool)

        # 測試 3: Trigger Handler 觸發邏輯
        await test_trigger_handler(db_pool)

        # 測試 4: Next Action Handler
        await test_next_action_handler(db_pool)

        # 測試 5: Context TTL
        await test_context_ttl(db_pool)

        print("\n" + "=" * 80)
        print("✅ 所有測試完成！")
        print("=" * 80)

    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
