#!/usr/bin/env python3
"""
測試知識庫是否正確根據業態類型（business_types）過濾知識
"""
import requests
import json
import time

API_BASE = "http://localhost:8100/api/v1"

def test_chat_with_business_type(vendor_id, vendor_name, business_type, question):
    """測試特定業者的聊天回應"""
    print(f"\n{'='*70}")
    print(f"測試業者: {vendor_name} (ID: {vendor_id})")
    print(f"業態: {business_type}")
    print(f"問題: {question}")
    print(f"{'='*70}\n")

    url = f"{API_BASE}/chat/stream"
    payload = {
        "question": question,
        "vendor_id": vendor_id,
        "user_role": "customer",
        "user_id": f"test_btype_{vendor_id}_{int(time.time())}"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            stream=True,
            timeout=15
        )

        answer = ""
        search_results = []

        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')

            if line.startswith('event:'):
                event = line.split(':', 1)[1].strip()
            elif line.startswith('data:'):
                try:
                    data = json.loads(line.split(':', 1)[1].strip())
                    if event == 'answer_chunk':
                        answer += data.get('chunk', '')
                    elif event == 'search_results':
                        search_results = data.get('results', [])
                except:
                    pass

        print(f"📊 檢索到的知識數量: {len(search_results)}")

        if search_results:
            print("\n🔍 檢索到的知識:")
            for idx, result in enumerate(search_results[:3], 1):
                kb_id = result.get('id', 'N/A')
                question_summary = result.get('question_summary', 'N/A')
                business_types = result.get('business_types', [])
                similarity = result.get('similarity', 0)

                print(f"  {idx}. [ID: {kb_id}] {question_summary[:50]}...")
                print(f"     業態: {business_types if business_types else '通用（所有業態）'}")
                print(f"     相似度: {similarity:.3f}")
        else:
            print("⚠️  沒有檢索到任何知識")

        print(f"\n💬 回答:\n{answer[:200]}{'...' if len(answer) > 200 else ''}\n")

        # 驗證業態過濾
        if search_results:
            for result in search_results:
                kb_business_types = result.get('business_types', [])
                if kb_business_types:  # 如果知識有指定業態
                    if business_type in kb_business_types:
                        print(f"✅ 正確：知識 {result['id']} 的業態 {kb_business_types} 包含 {business_type}")
                    else:
                        print(f"❌ 錯誤：知識 {result['id']} 的業態 {kb_business_types} 不應該被檢索（業者業態: {business_type}）")
                else:
                    print(f"ℹ️  通用知識 {result['id']}（適用所有業態）")

        return True

    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        return False


def check_vendor_info(vendor_id):
    """檢查業者的業態設定"""
    try:
        response = requests.get(f"{API_BASE}/vendors/{vendor_id}")
        if response.status_code == 200:
            vendor = response.json()
            print(f"\n📋 業者資訊: {vendor['name']}")
            print(f"   業態類型: {vendor.get('business_types', [])}")
            return vendor.get('business_types', [])
        else:
            print(f"⚠️  無法取得業者資訊: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 取得業者資訊失敗: {e}")
        return []


if __name__ == "__main__":
    print("\n" + "="*70)
    print("業態類型過濾測試")
    print("="*70)

    # 檢查測試業者的業態設定
    print("\n【步驟 1】檢查業者業態設定")
    vendor_1_types = check_vendor_info(1)
    vendor_4_types = check_vendor_info(4)

    # 測試相同問題在不同業態的回應
    print("\n【步驟 2】測試相同問題，不同業態的知識檢索")

    test_question = "租金什麼時候要繳？"

    # 測試包租型業者
    if vendor_1_types:
        test_chat_with_business_type(
            1,
            "甲山林",
            vendor_1_types[0],
            test_question
        )

    time.sleep(2)

    # 測試代管型業者
    if vendor_4_types:
        test_chat_with_business_type(
            4,
            "永慶",
            vendor_4_types[0],
            test_question
        )

    print("\n" + "="*70)
    print("測試完成")
    print("="*70)
    print("\n預期結果：")
    print("1. 每個業者應該只檢索到符合其業態的知識（或通用知識）")
    print("2. 包租型業者不應該檢索到只標記為代管型的知識")
    print("3. 代管型業者不應該檢索到只標記為包租型的知識")
    print("4. 標記為通用（NULL）的知識應該對所有業態可見")
    print()
