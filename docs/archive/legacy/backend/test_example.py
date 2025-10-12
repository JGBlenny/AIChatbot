"""
測試範例腳本
使用前請先啟動後端：uvicorn app.main:app --reload
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_import_line_conversation():
    """測試匯入 LINE 對話"""
    print("\n=== 測試 1: 匯入 LINE 對話 ===")

    # 準備測試資料
    data = {
        "messages": [
            {
                "timestamp": "2024/01/15 14:30",
                "sender": "客戶",
                "message": "你好，請問如何使用這個功能？"
            },
            {
                "timestamp": "2024/01/15 14:31",
                "sender": "客服",
                "message": "您好！使用方式很簡單："
            },
            {
                "timestamp": "2024/01/15 14:31",
                "sender": "客服",
                "message": "1. 打開應用程式\n2. 點選右上角設定\n3. 選擇您要的功能"
            },
            {
                "timestamp": "2024/01/15 14:32",
                "sender": "客戶",
                "message": "好的，我找到了！謝謝"
            },
            {
                "timestamp": "2024/01/15 14:33",
                "sender": "客服",
                "message": "不客氣，還有其他問題嗎？"
            },
            {
                "timestamp": "2024/01/15 14:33",
                "sender": "客戶",
                "message": "沒有了，謝謝"
            }
        ],
        "conversation_id": "test-line-001"
    }

    response = requests.post(
        f"{BASE_URL}/api/conversations/import/line",
        json=data
    )

    if response.status_code == 201:
        conversation = response.json()
        print(f"✅ 匯入成功")
        print(f"對話 ID: {conversation['id']}")
        print(f"來源: {conversation['source']}")
        print(f"狀態: {conversation['status']}")
        return conversation['id']
    else:
        print(f"❌ 匯入失敗: {response.json()}")
        return None


def test_process_conversation(conv_id):
    """測試 AI 處理對話"""
    print(f"\n=== 測試 2: AI 處理對話 {conv_id} ===")

    response = requests.post(
        f"{BASE_URL}/api/processing/{conv_id}/process-all"
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 處理成功")
        print(f"品質分數: {result.get('quality_score', 'N/A')}")
        print(f"主要分類: {result.get('primary_category', 'N/A')}")
        print(f"次要分類: {result.get('secondary_categories', [])}")
        print(f"標籤: {result.get('tags', [])}")
        print(f"情感: {result.get('sentiment', 'N/A')}")
        print(f"信心度: {result.get('confidence_score', 'N/A')}")

        # 顯示清理後的 Q&A
        if result.get('processed_content'):
            cleaned = result['processed_content'].get('cleaned', {})
            print(f"\n清理後內容:")
            print(f"Q: {cleaned.get('question', 'N/A')}")
            print(f"A: {cleaned.get('answer', 'N/A')}")
        return True
    else:
        print(f"❌ 處理失敗: {response.json()}")
        return False


def test_list_conversations():
    """測試查詢對話列表"""
    print("\n=== 測試 3: 查詢對話列表 ===")

    response = requests.get(
        f"{BASE_URL}/api/conversations/",
        params={"page": 1, "page_size": 5}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 查詢成功")
        print(f"總數: {data['total']}")
        print(f"當前頁: {data['page']}")
        print(f"每頁數量: {data['page_size']}")
        print(f"\n前 {len(data['items'])} 筆對話:")
        for item in data['items']:
            print(f"  - ID: {item['id']}")
            print(f"    分類: {item.get('primary_category', '未分類')}")
            print(f"    狀態: {item['status']}")
            print(f"    建立時間: {item['created_at']}")
        return True
    else:
        print(f"❌ 查詢失敗: {response.json()}")
        return False


def test_approve_conversation(conv_id):
    """測試批准對話"""
    print(f"\n=== 測試 4: 批准對話 {conv_id} ===")

    response = requests.post(
        f"{BASE_URL}/api/processing/{conv_id}/approve",
        params={
            "reviewed_by": "admin",
            "review_notes": "測試批准"
        }
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 批准成功")
        print(f"狀態: {result['status']}")
        print(f"審核人: {result.get('reviewed_by', 'N/A')}")
        print(f"審核備註: {result.get('review_notes', 'N/A')}")
        return True
    else:
        print(f"❌ 批准失敗: {response.json()}")
        return False


def test_stats():
    """測試統計資訊"""
    print("\n=== 測試 5: 統計資訊 ===")

    response = requests.get(f"{BASE_URL}/api/conversations/stats/summary")

    if response.status_code == 200:
        stats = response.json()
        print(f"✅ 查詢成功")
        print(f"總對話數: {stats['total']}")
        print(f"平均品質分數: {stats.get('avg_quality_score', 'N/A')}")
        print(f"最近7天匯入: {stats['recent_imports']}")
        print(f"\n按狀態統計:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")
        print(f"\n按分類統計:")
        for category, count in stats['by_category'].items():
            print(f"  {category}: {count}")
        return True
    else:
        print(f"❌ 查詢失敗: {response.json()}")
        return False


def main():
    """執行所有測試"""
    print("=" * 50)
    print("AIChatbot 後端 API 測試")
    print("=" * 50)

    # 檢查後端是否運行
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ 後端未運行，請先啟動：uvicorn app.main:app --reload")
            return
        print("✅ 後端運行中\n")
    except requests.ConnectionError:
        print("❌ 無法連接後端，請先啟動：uvicorn app.main:app --reload")
        return

    # 執行測試
    conv_id = test_import_line_conversation()

    if conv_id:
        test_process_conversation(conv_id)
        test_approve_conversation(conv_id)

    test_list_conversations()
    test_stats()

    print("\n" + "=" * 50)
    print("測試完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
