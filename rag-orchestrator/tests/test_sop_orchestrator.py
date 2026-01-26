"""
SOP Orchestrator 實際環境測試
測試完整的 SOP 編排流程
"""
import sys
import os
import asyncio
import json

# 添加路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.sop_orchestrator import SOPOrchestrator
from services.form_manager import FormManager
import asyncpg


async def test_sop_orchestrator_none_mode(db_pool):
    """測試 none 模式（純資訊型 SOP）"""
    print("\n" + "=" * 80)
    print("🧪 測試 1: none 模式 - 純資訊型 SOP")
    print("=" * 80)

    form_manager = FormManager(db_pool=db_pool)
    orchestrator = SOPOrchestrator(form_manager=form_manager)

    # 模擬 SOP 項目（none 模式）
    sop_item = {
        'id': 1001,
        'item_name': '租金繳納資訊',
        'content': '租金每月 5 號前繳納，可使用轉帳或現金。',
        'trigger_mode': 'none',
        'next_action': 'none',
        'next_form_id': None,
        'next_api_config': None,
        'trigger_keywords': None,
        'immediate_prompt': None,
        'followup_prompt': None
    }

    user_message = "租金怎麼繳？"
    session_id = "test_none_mode"
    vendor_id = 1

    try:
        result = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message=user_message,
            session_id=session_id,
            vendor_id=vendor_id
        )

        print(f"\n使用者訊息: {user_message}")
        print(f"SOP 內容: {sop_item['content']}")
        print(f"\n處理結果:")
        print(f"  action: {result.get('action')}")
        print(f"  message: {result.get('message', '')[:100]}")
        print(f"  context_saved: {result.get('context_saved')}")
        print(f"  should_trigger: {result.get('should_trigger')}")

        if result.get('action') == 'provide_info':
            print("✅ none 模式測試通過：純資訊回應，無後續動作")
        else:
            print(f"❌ none 模式測試失敗：預期 action='provide_info'，實際 '{result.get('action')}'")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_sop_orchestrator_manual_mode(db_pool):
    """測試 manual 模式（排查型 SOP）"""
    print("\n" + "=" * 80)
    print("🧪 測試 2: manual 模式 - 排查型 SOP")
    print("=" * 80)

    form_manager = FormManager(db_pool=db_pool)
    orchestrator = SOPOrchestrator(form_manager=form_manager)

    # 模擬 SOP 項目（manual 模式 + form_fill）
    sop_item = {
        'id': 1002,
        'item_name': '冷氣故障排查',
        'content': '請先檢查：1) 遙控器電池 2) 電源開關 3) 濾網清潔。如果還是不行，請填寫報修表。',
        'trigger_mode': 'manual',
        'next_action': 'form_fill',
        'next_form_id': 'maintenance_request',
        'next_api_config': None,
        'trigger_keywords': ['還是不行', '試過了', '沒用'],
        'immediate_prompt': None,
        'followup_prompt': '如果以上方法都試過還是不行，我可以幫您填寫報修表。'
    }

    session_id = "test_manual_mode"
    vendor_id = 1

    try:
        # 第一次：提供排查資訊
        print("\n--- 第一輪：提供排查資訊 ---")
        user_message_1 = "冷氣壞了"

        result_1 = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message=user_message_1,
            session_id=session_id,
            vendor_id=vendor_id
        )

        print(f"使用者訊息: {user_message_1}")
        print(f"處理結果:")
        print(f"  action: {result_1.get('action')}")
        print(f"  context_saved: {result_1.get('context_saved')}")
        print(f"  ttl: {result_1.get('context_ttl')}")

        if result_1.get('action') == 'provide_info_and_wait':
            print("✅ 第一輪通過：提供排查資訊並等待")
        else:
            print(f"❌ 第一輪失敗：預期 action='provide_info_and_wait'")

        # 等待一下（模擬用戶操作）
        await asyncio.sleep(0.5)

        # 第二次：用戶回應觸發關鍵詞
        print("\n--- 第二輪：觸發關鍵詞 ---")
        user_message_2 = "試過了還是不行"

        result_2 = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message=user_message_2,
            session_id=session_id,
            vendor_id=vendor_id
        )

        print(f"使用者訊息: {user_message_2}")
        print(f"處理結果:")
        print(f"  action: {result_2.get('action')}")
        print(f"  should_trigger: {result_2.get('should_trigger')}")
        print(f"  matched_keyword: {result_2.get('matched_keyword')}")
        print(f"  next_action: {result_2.get('next_action')}")

        if result_2.get('should_trigger') and result_2.get('action') == 'trigger_form':
            print("✅ 第二輪通過：成功觸發表單填寫")
        else:
            print(f"❌ 第二輪失敗：未成功觸發")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_sop_orchestrator_immediate_mode(db_pool):
    """測試 immediate 模式（行動型 SOP）"""
    print("\n" + "=" * 80)
    print("🧪 測試 3: immediate 模式 - 行動型 SOP")
    print("=" * 80)

    form_manager = FormManager(db_pool=db_pool)
    orchestrator = SOPOrchestrator(form_manager=form_manager)

    # 模擬 SOP 項目（immediate 模式 + api_call）
    sop_item = {
        'id': 1003,
        'item_name': '預約看房',
        'content': '您好！我可以幫您預約看房時間。',
        'trigger_mode': 'immediate',
        'next_action': 'api_call',
        'next_form_id': None,
        'next_api_config': {
            'endpoint': '/api/schedule-viewing',
            'method': 'POST',
            'params': ['property_id', 'preferred_time']
        },
        'trigger_keywords': ['是', '要', '好', '可以'],
        'immediate_prompt': '請問您要預約看房嗎？',
        'followup_prompt': None
    }

    session_id = "test_immediate_mode"
    vendor_id = 1

    try:
        # 第一次：立即詢問
        print("\n--- 第一輪：立即詢問 ---")
        user_message_1 = "我想看房"

        result_1 = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message=user_message_1,
            session_id=session_id,
            vendor_id=vendor_id
        )

        print(f"使用者訊息: {user_message_1}")
        print(f"處理結果:")
        print(f"  action: {result_1.get('action')}")
        print(f"  message: {result_1.get('message', '')[:80]}")
        print(f"  context_saved: {result_1.get('context_saved')}")

        if result_1.get('action') == 'ask_immediate_confirmation':
            print("✅ 第一輪通過：立即詢問確認")
        else:
            print(f"❌ 第一輪失敗：預期 action='ask_immediate_confirmation'")

        # 第二次：用戶確認
        print("\n--- 第二輪：用戶確認 ---")
        user_message_2 = "要"

        result_2 = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message=user_message_2,
            session_id=session_id,
            vendor_id=vendor_id
        )

        print(f"使用者訊息: {user_message_2}")
        print(f"處理結果:")
        print(f"  action: {result_2.get('action')}")
        print(f"  should_trigger: {result_2.get('should_trigger')}")
        print(f"  api_config: {result_2.get('api_config')}")

        if result_2.get('should_trigger') and result_2.get('action') == 'trigger_api':
            print("✅ 第二輪通過：成功觸發 API 呼叫")
        else:
            print(f"❌ 第二輪失敗：未成功觸發 API")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_sop_orchestrator_form_then_api(db_pool):
    """測試 form_then_api 場景"""
    print("\n" + "=" * 80)
    print("🧪 測試 4: form_then_api - 表單後 API 呼叫")
    print("=" * 80)

    try:
        form_manager = FormManager(db_pool=db_pool)
        orchestrator = SOPOrchestrator(form_manager=form_manager)

        # 模擬 SOP 項目（manual 模式 + form_then_api）
        sop_item = {
            'id': 1004,
            'item_name': '線上報修流程',
            'content': '請先填寫報修表，系統會自動派工。',
            'trigger_mode': 'manual',
            'next_action': 'form_then_api',
            'next_form_id': 'maintenance_request',
            'next_api_config': {
                'endpoint': '/api/auto-dispatch',
                'method': 'POST',
                'params': ['maintenance_type', 'location']
            },
            'trigger_keywords': ['好', '要填'],
            'immediate_prompt': None,
            'followup_prompt': '請問您要填寫報修表嗎？'
        }

        session_id = f"test_form_then_api_{int(asyncio.get_event_loop().time())}"
        vendor_id = 1

        # 第一輪：提供資訊並詢問
        print("\n--- 第一輪：提供資訊 ---")
        user_message_1 = "需要報修"

        result_1 = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message=user_message_1,
            session_id=session_id,
            vendor_id=vendor_id
        )

        print(f"使用者訊息: {user_message_1}")
        print(f"處理結果:")
        print(f"  action: {result_1.get('action')}")
        print(f"  context_saved: {result_1.get('context_saved')}")

        # 第二輪：用戶確認填寫表單
        print("\n--- 第二輪：確認填寫表單 ---")
        user_message_2 = "好，要填"

        result_2 = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message=user_message_2,
            session_id=session_id,
            vendor_id=vendor_id
        )

        print(f"使用者訊息: {user_message_2}")
        print(f"處理結果:")
        print(f"  action: {result_2.get('action')}")
        print(f"  should_trigger: {result_2.get('should_trigger')}")
        print(f"  next_action: {result_2.get('next_action')}")
        print(f"  form_id: {result_2.get('form_id')}")
        print(f"  api_config: {result_2.get('api_config', {}).get('endpoint', 'N/A')}")

        if result_2.get('should_trigger') and result_2.get('action') == 'trigger_form_then_api':
            print("✅ form_then_api 測試通過：成功觸發表單填寫（後續會呼叫 API）")
            print(f"  表單 ID: {result_2.get('form_id')}")
            print(f"  API 端點: {result_2.get('api_config', {}).get('endpoint')}")
        else:
            print(f"❌ form_then_api 測試失敗")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_redis_context_expiry(db_pool):
    """測試 Redis Context 過期機制"""
    print("\n" + "=" * 80)
    print("🧪 測試 5: Redis Context TTL 過期")
    print("=" * 80)

    form_manager = FormManager(db_pool=db_pool)
    orchestrator = SOPOrchestrator(form_manager=form_manager)

    sop_item = {
        'id': 1005,
        'item_name': 'TTL 測試',
        'content': '測試 context 過期',
        'trigger_mode': 'manual',
        'next_action': 'form_fill',
        'next_form_id': 'test_form',
        'next_api_config': None,
        'trigger_keywords': ['觸發'],
        'immediate_prompt': None,
        'followup_prompt': '準備好了嗎？'
    }

    session_id = "test_ttl"
    vendor_id = 1

    try:
        # 第一次：儲存 context
        print("\n--- 儲存 context (TTL=3秒) ---")

        result_1 = await orchestrator.process_sop_response(
            sop_item=sop_item,
            user_message="測試訊息",
            session_id=session_id,
            vendor_id=vendor_id
        )

        # 手動設置短 TTL（用於測試）
        await orchestrator.context_manager.save_context(
            session_id=session_id,
            sop_id=sop_item['id'],
            trigger_mode='manual',
            next_action='form_fill',
            next_form_id='test_form',
            ttl=3  # 3 秒過期
        )

        print(f"Context 已儲存，TTL=3秒")

        # 立即檢查 context
        context = await orchestrator.context_manager.get_context(session_id)
        if context:
            print(f"✅ Context 存在: sop_id={context.get('sop_id')}")
        else:
            print("❌ Context 不存在（不應該發生）")

        # 等待 4 秒（超過 TTL）
        print("\n--- 等待 4 秒（超過 TTL） ---")
        await asyncio.sleep(4)

        # 再次檢查 context
        context = await orchestrator.context_manager.get_context(session_id)
        if context is None:
            print("✅ Context 已過期（符合預期）")
        else:
            print(f"❌ Context 仍存在（不應該）: {context}")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("🚀 開始 SOP Orchestrator 實際環境測試")
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
        # 測試 1: none 模式
        await test_sop_orchestrator_none_mode(db_pool)

        # 測試 2: manual 模式
        await test_sop_orchestrator_manual_mode(db_pool)

        # 測試 3: immediate 模式
        await test_sop_orchestrator_immediate_mode(db_pool)

        # 測試 4: form_then_api
        await test_sop_orchestrator_form_then_api(db_pool)

        # 測試 5: Redis TTL
        await test_redis_context_expiry(db_pool)

        print("\n" + "=" * 80)
        print("✅ 所有 SOP Orchestrator 測試完成！")
        print("=" * 80)

    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
