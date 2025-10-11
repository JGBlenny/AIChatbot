"""
測試答案合成的動態覆蓋功能

驗證即使配置中啟用了答案合成，也可以通過參數動態禁用
"""
import sys
import os

# 添加父目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.llm_answer_optimizer import LLMAnswerOptimizer


def test_synthesis_override():
    """測試答案合成覆蓋功能"""

    print("="*60)
    print("測試答案合成動態覆蓋功能")
    print("="*60)

    # 準備測試資料
    question = "退租時押金要怎麼退還？需要什麼流程？"  # 複合問題

    search_results = [
        {
            'id': 1,
            'title': '押金退還時間',
            'content': '押金通常會在退租後的 7-14 個工作天內退還',
            'category': '押金問題',
            'similarity': 0.65  # 低於閾值 0.7
        },
        {
            'id': 2,
            'title': '退租流程說明',
            'content': '1. 提前 30 天通知\n2. 約定檢查時間\n3. 房屋狀況檢查',
            'category': '退租流程',
            'similarity': 0.62
        },
        {
            'id': 3,
            'title': '退租注意事項',
            'content': '需繳清所有費用，歸還鑰匙，清空個人物品',
            'category': '退租流程',
            'similarity': 0.60
        }
    ]

    intent_info = {
        'intent_name': '退租流程',
        'intent_type': 'knowledge',
        'keywords': ['退租', '押金', '流程']
    }

    # 測試 1：配置啟用 + 沒有覆蓋（應該觸發合成）
    print("\n【測試 1】配置啟用 + 沒有覆蓋")
    print("-" * 60)
    optimizer1 = LLMAnswerOptimizer(config={
        "enable_synthesis": True,  # 配置啟用
        "synthesis_threshold": 0.7,
        "synthesis_min_results": 2
    })

    should_trigger = optimizer1._should_synthesize(question, search_results, enable_synthesis_override=None)
    print(f"預期：應該觸發合成 (True)")
    print(f"實際：{should_trigger}")
    print(f"結果：{'✅ PASS' if should_trigger else '❌ FAIL'}")

    # 測試 2：配置啟用 + 覆蓋為 False（不應該觸發合成）
    print("\n【測試 2】配置啟用 + 覆蓋為 False（回測模式）")
    print("-" * 60)
    optimizer2 = LLMAnswerOptimizer(config={
        "enable_synthesis": True,  # 配置啟用
        "synthesis_threshold": 0.7
    })

    should_trigger = optimizer2._should_synthesize(question, search_results, enable_synthesis_override=False)
    print(f"預期：不應該觸發合成 (False)")
    print(f"實際：{should_trigger}")
    print(f"結果：{'✅ PASS' if not should_trigger else '❌ FAIL'}")

    # 測試 3：配置停用 + 覆蓋為 True（應該觸發合成）
    print("\n【測試 3】配置停用 + 覆蓋為 True（強制啟用）")
    print("-" * 60)
    optimizer3 = LLMAnswerOptimizer(config={
        "enable_synthesis": False,  # 配置停用
        "synthesis_threshold": 0.7
    })

    should_trigger = optimizer3._should_synthesize(question, search_results, enable_synthesis_override=True)
    print(f"預期：應該觸發合成 (True)")
    print(f"實際：{should_trigger}")
    print(f"結果：{'✅ PASS' if should_trigger else '❌ FAIL'}")

    # 測試 4：配置停用 + 沒有覆蓋（不應該觸發合成）
    print("\n【測試 4】配置停用 + 沒有覆蓋")
    print("-" * 60)
    optimizer4 = LLMAnswerOptimizer(config={
        "enable_synthesis": False,  # 配置停用
        "synthesis_threshold": 0.7
    })

    should_trigger = optimizer4._should_synthesize(question, search_results, enable_synthesis_override=None)
    print(f"預期：不應該觸發合成 (False)")
    print(f"實際：{should_trigger}")
    print(f"結果：{'✅ PASS' if not should_trigger else '❌ FAIL'}")

    print("\n" + "="*60)
    print("✅ 所有測試完成！")
    print("="*60)

    print("\n💡 使用場景說明：")
    print("  - 生產環境：不傳 enable_synthesis_override（使用配置）")
    print("  - 回測框架：傳入 enable_synthesis_override=False（強制禁用）")
    print("  - 灰度測試：傳入 enable_synthesis_override=True（強制啟用）")


if __name__ == "__main__":
    test_synthesis_override()
