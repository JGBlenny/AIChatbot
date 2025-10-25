#!/usr/bin/env python3
"""最終語氣測試 - 使用更通用的問題"""
import requests
import json
import time

API_BASE = "http://localhost:8100/api/v1"

def test_tone(vendor_id, vendor_name, business_type, question):
    """測試語氣"""
    print(f"\n{'='*70}")
    print(f"業者: {vendor_name} (ID: {vendor_id})")
    print(f"業態: {business_type}")
    print(f"問題: {question}")
    print(f"{'='*70}\n")

    url = f"{API_BASE}/chat/stream"
    payload = {
        "question": question,
        "vendor_id": vendor_id,
        "user_role": "customer",
        "user_id": f"test_{vendor_id}_{int(time.time())}"
    }

    try:
        response = requests.post(url, json=payload, headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }, stream=True, timeout=15)

        answer = ""
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if line.startswith('event:'):
                event = line.split(':', 1)[1].strip()
            elif line.startswith('data:') and event == 'answer_chunk':
                try:
                    data = json.loads(line.split(':', 1)[1].strip())
                    answer += data.get('chunk', '')
                except:
                    pass

        print(f"回答:\n{answer}\n")

        # 語氣檢查
        if business_type == 'full_service':
            keywords = ['我們會', '公司將', '我們負責', '我們處理', '我們安排', '我們協助']
            found = [kw for kw in keywords if kw in answer]
            if found:
                print(f"✅ 包租型語氣: {', '.join(found)}")
            else:
                print(f"⚠️  未找到包租型關鍵詞")

        elif business_type == 'property_management':
            keywords = ['請您', '建議', '可協助', '協助您聯繫', '居中協調', '建議您聯繫']
            found = [kw for kw in keywords if kw in answer]
            if found:
                print(f"✅ 代管型語氣: {', '.join(found)}")
            else:
                print(f"⚠️  未找到代管型關鍵詞")

    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("語氣調整功能最終測試")
    print("="*70)

    # 測試包租型
    test_tone(1, "甲山林", "full_service", "租金什麼時候要繳？")
    time.sleep(2)

    # 測試代管型
    test_tone(4, "永慶", "property_management", "租金什麼時候要繳？")

    print("\n" + "="*70)
    print("測試完成")
    print("="*70 + "\n")
