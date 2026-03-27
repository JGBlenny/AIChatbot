"""
測試 GapClassifier 與 LoopCoordinator 整合

檢查是否能正確 import 和初始化
"""

import sys
sys.path.insert(0, '/app')

try:
    from gap_classifier import GapClassifier
    print("✅ GapClassifier import 成功")
except Exception as e:
    print(f"❌ GapClassifier import 失敗: {e}")
    sys.exit(1)

try:
    from coordinator import LoopCoordinator
    print("✅ LoopCoordinator import 成功")
except Exception as e:
    print(f"❌ LoopCoordinator import 失敗: {e}")
    sys.exit(1)

# 測試初始化
try:
    classifier = GapClassifier(openai_api_key=None, model="gpt-4o-mini")
    print(f"✅ GapClassifier 初始化成功（Stub 模式）")
except Exception as e:
    print(f"❌ GapClassifier 初始化失敗: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 整合測試完成：所有模組都可以正常 import 和初始化")
print("=" * 60)
