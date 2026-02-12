#!/usr/bin/env python3
"""
測試聊天系統語氣調整功能
"""
import requests
import json
import time

API_BASE = "http://localhost:8100/api/v1"

def test_chat_tone(vendor_id, vendor_name, expected_business_type, question):
    """測試特定業者的語氣"""
    print(f"\n{'='*60}")
    print(f"測試業者: {vendor_name} (ID: {vendor_id})")
    print(f"預期業態: {expected_business_type}")
    print(f"測試問題: {question}")
    print(f"{'='*60}\n")

    url = f"{API_BASE}/chat/stream"
    payload = {
        "question": question,
        "vendor_id": vendor_id,
        "user_role": "customer",
        "user_id": f"test_tone_{vendor_id}_{int(time.time())}"
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

        answer_chunks = []
        metadata = {}

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')

            if line.startswith('event:'):
                current_event = line.split(':', 1)[1].strip()
            elif line.startswith('data:'):
                try:
                    data = json.loads(line.split(':', 1)[1].strip())

                    if current_event == 'answer_chunk':
                        answer_chunks.append(data.get('chunk', ''))
                    elif current_event == 'complete':
                        metadata = data
                except:
                    pass

        answer = ''.join(answer_chunks)

        print(f"📝 完整回答:\n{answer}\n")

        # 檢查語氣
        print(f"🔍 語氣檢查:")

        if expected_business_type == 'full_service':
            # 包租型 - 應該用主動承諾語氣
            keywords = ['我們會', '公司將', '我們負責', '我們處理', '我們安排', '我們協助']
            found_keywords = [kw for kw in keywords if kw in answer]

            if found_keywords:
                print(f"  ✅ 使用了包租型語氣關鍵詞: {', '.join(found_keywords)}")
            else:
                print(f"  ❌ 未找到包租型語氣關鍵詞")

            # 檢查不應該出現的代管型語氣
            avoid_keywords = ['請您聯繫房東', '建議您聯繫', '請與房東', '協助您聯繫房東']
            found_avoid = [kw for kw in avoid_keywords if kw in answer]
            if found_avoid:
                print(f"  ⚠️  出現了不應有的代管型語氣: {', '.join(found_avoid)}")

        elif expected_business_type == 'property_management':
            # 代管型 - 應該用協助引導語氣
            keywords = ['請您', '建議', '可協助', '協助您聯繫', '居中協調', '聯繫房東']
            found_keywords = [kw for kw in keywords if kw in answer]

            if found_keywords:
                print(f"  ✅ 使用了代管型語氣關鍵詞: {', '.join(found_keywords)}")
            else:
                print(f"  ❌ 未找到代管型語氣關鍵詞")

            # 檢查不應該出現的包租型語氣
            avoid_keywords = ['我們會處理', '公司負責', '我們負責']
            found_avoid = [kw for kw in avoid_keywords if kw in answer]
            if found_avoid:
                print(f"  ⚠️  出現了不應有的包租型語氣: {', '.join(found_avoid)}")

        print(f"\n💡 元數據: {json.dumps(metadata, ensure_ascii=False, indent=2)}")

        return True

    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("開始測試聊天系統語氣調整功能")
    print("="*60)

    # 測試 1: 包租型業者
    test_chat_tone(
        vendor_id=1,
        vendor_name="甲山林包租代管股份有限公司",
        expected_business_type="full_service",
        question="房間漏水了怎麼辦？"
    )

    time.sleep(2)

    # 測試 2: 代管型業者
    test_chat_tone(
        vendor_id=4,
        vendor_name="永慶包租代管股份有限公司",
        expected_business_type="property_management",
        question="房間漏水了怎麼辦？"
    )

    print("\n" + "="*60)
    print("測試完成")
    print("="*60 + "\n")
