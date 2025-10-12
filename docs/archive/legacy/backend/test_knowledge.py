"""
測試 Markdown 知識庫生成功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_generate_knowledge_base():
    """測試生成知識庫"""
    print("\n=== 測試：生成完整知識庫 ===")

    response = requests.post(
        f"{BASE_URL}/api/knowledge/generate",
        json={
            "categories": None,  # None = 所有分類
            "min_quality_score": 7,
            "only_approved": True
        }
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 生成成功")
        print(f"檔案數: {len(result['files_generated'])}")
        print(f"對話數: {result['total_conversations']}")
        print(f"檔案列表:")
        for file in result['files_generated']:
            print(f"  - {file}")
        return True
    else:
        print(f"❌ 生成失敗: {response.json()}")
        return False


def test_list_knowledge_files():
    """測試列出知識庫檔案"""
    print("\n=== 測試：查詢知識庫檔案列表 ===")

    response = requests.get(f"{BASE_URL}/api/knowledge/files")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 查詢成功")
        print(f"檔案總數: {result['total']}")
        print(f"\n檔案詳情:")
        for file in result['files']:
            print(f"\n  檔案: {file['filename']}")
            print(f"  分類: {file['category']}")
            print(f"  對話數: {file['conversations_count']}")
            print(f"  大小: {file['size_bytes']} bytes")
        return True
    else:
        print(f"❌ 查詢失敗: {response.json()}")
        return False


def test_get_knowledge_file(category):
    """測試獲取知識庫檔案內容"""
    print(f"\n=== 測試：讀取知識庫檔案 ({category}) ===")

    response = requests.get(f"{BASE_URL}/api/knowledge/files/{category}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 讀取成功")
        print(f"分類: {result['category']}")
        print(f"檔案: {result['filename']}")
        print(f"\n內容預覽（前 500 字元）:")
        print(result['content'][:500])
        print("...")
        return True
    else:
        print(f"❌ 讀取失敗: {response.json()}")
        return False


def test_knowledge_stats():
    """測試知識庫統計"""
    print("\n=== 測試：知識庫統計 ===")

    response = requests.get(f"{BASE_URL}/api/knowledge/stats")

    if response.status_code == 200:
        stats = response.json()
        print(f"✅ 查詢成功")
        print(f"\n統計資訊:")
        print(f"  檔案總數: {stats['total_files']}")
        print(f"  總大小: {stats['total_size_mb']} MB")
        print(f"  已匯出對話: {stats['conversations_exported']}")
        print(f"  已批准對話: {stats['conversations_approved']}")
        print(f"  匯出覆蓋率: {stats['export_coverage']}%")
        return True
    else:
        print(f"❌ 查詢失敗: {response.json()}")
        return False


def test_generate_category(category):
    """測試生成特定分類"""
    print(f"\n=== 測試：生成特定分類 ({category}) ===")

    response = requests.post(
        f"{BASE_URL}/api/knowledge/generate/{category}",
        params={"min_quality_score": 7}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 生成成功")
        print(f"對話數: {result['total_conversations']}")
        print(f"檔案: {result['files_generated']}")
        return True
    else:
        print(f"❌ 生成失敗: {response.json()}")
        return False


def main():
    """執行所有測試"""
    print("=" * 50)
    print("Markdown 知識庫生成功能測試")
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

    # 檢查是否有已批准的對話
    response = requests.get(f"{BASE_URL}/api/conversations/stats/summary")
    if response.status_code == 200:
        stats = response.json()
        approved_count = stats['by_status'].get('approved', 0)
        if approved_count == 0:
            print("⚠️  沒有已批准的對話")
            print("提示：請先匯入對話並完成 AI 處理和審核")
            print("\n建議步驟：")
            print("1. 匯入 LINE 對話：python test_example.py")
            print("2. 重新執行此腳本")
            return
        print(f"✅ 找到 {approved_count} 筆已批准的對話\n")

    # 執行測試
    test_generate_knowledge_base()
    test_list_knowledge_files()
    test_knowledge_stats()

    # 如果有檔案，測試讀取
    response = requests.get(f"{BASE_URL}/api/knowledge/files")
    if response.status_code == 200:
        files = response.json()['files']
        if files:
            # 讀取第一個檔案
            first_category = files[0]['category']
            test_get_knowledge_file(first_category)

    print("\n" + "=" * 50)
    print("測試完成！")
    print("=" * 50)
    print("\n查看生成的檔案：")
    print("  cd ../knowledge-base")
    print("  ls -la")


if __name__ == "__main__":
    main()
