"""
執行完整的知識匯入測試
測試完整流程：上傳 → 輪詢狀態 → 驗證結果
"""
import requests
import time
import json
from pathlib import Path

# API 設定
BASE_URL = "http://localhost:8100/api/v1/knowledge-import"
TEST_FILE = Path(__file__).parent.parent / "fixtures" / "test_knowledge_data.xlsx"

def upload_file():
    """上傳測試檔案"""
    print(f"\n{'='*60}")
    print("📤 步驟 1: 上傳測試檔案")
    print(f"{'='*60}")

    with open(TEST_FILE, 'rb') as f:
        files = {'file': ('test_knowledge_data.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'vendor_id': '',  # 留空表示通用知識
            'import_mode': 'append',
            'enable_deduplication': 'true'
        }

        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        response.raise_for_status()

        result = response.json()
        print(f"✅ 上傳成功")
        print(f"   Job ID: {result['job_id']}")
        print(f"   狀態: {result['status']}")
        print(f"   訊息: {result['message']}")

        return result['job_id']

def poll_status(job_id, max_attempts=60):
    """輪詢任務狀態"""
    print(f"\n{'='*60}")
    print(f"⏳ 步驟 2: 監控處理進度")
    print(f"{'='*60}")

    for attempt in range(max_attempts):
        time.sleep(2)  # 每2秒輪詢一次

        response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        response.raise_for_status()

        result = response.json()
        status = result['status']
        progress = result.get('progress', {})

        if progress:
            stage = progress.get('stage', '處理中')
            current = progress.get('current', 0)
            total = progress.get('total', 100)
            print(f"   [{attempt+1:2d}/60] {status.upper()}: {stage} ({current}/{total}%)")

        if status == 'completed':
            print(f"\n✅ 處理完成")
            return result
        elif status == 'failed':
            print(f"\n❌ 處理失敗: {result.get('error')}")
            return result

    print(f"\n⚠️  超時：任務未在預期時間內完成")
    return None

def verify_results(result):
    """驗證匯入結果"""
    print(f"\n{'='*60}")
    print(f"📊 步驟 3: 驗證匯入結果")
    print(f"{'='*60}")

    if not result:
        print("❌ 無法取得結果")
        return

    import_result = result.get('result', {})

    print(f"\n【匯入統計】")
    print(f"  匯入知識: {import_result.get('imported', 0)} 條")
    print(f"  跳過: {import_result.get('skipped', 0)} 條")
    print(f"  錯誤: {import_result.get('errors', 0)} 條")
    print(f"  總計: {import_result.get('total', 0)} 條")
    print(f"  測試情境建議: {import_result.get('test_scenarios_created', 0)} 個")
    print(f"  模式: {import_result.get('mode', 'unknown')}")

    print(f"\n【預期 vs 實際】")
    print(f"  預期匯入: ~7 條（10條 - 1完全重複 - 2語意相似）")
    print(f"  實際匯入: {import_result.get('imported', 0)} 條")

    print(f"\n  預期測試情境: ~7 個（B2C 且未重複）")
    print(f"  實際測試情境: {import_result.get('test_scenarios_created', 0)} 個")

def check_review_queue():
    """檢查審核佇列"""
    print(f"\n{'='*60}")
    print(f"📋 步驟 4: 檢查審核佇列")
    print(f"{'='*60}")

    try:
        # 直接查詢資料庫
        import subprocess
        cmd = '''docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin -c "
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE ai_model = 'knowledge_import') as from_import
            FROM ai_generated_knowledge_candidates
            WHERE status = 'pending_review';
        "'''

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)

        # 查看最新3條的意圖推薦
        cmd2 = '''docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin -c "
            SELECT
                LEFT(question, 50) as question,
                generation_reasoning
            FROM ai_generated_knowledge_candidates
            WHERE ai_model = 'knowledge_import'
            ORDER BY created_at DESC
            LIMIT 3;
        "'''

        print("\n【最新3條知識的意圖推薦】")
        result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        print(result2.stdout)

    except Exception as e:
        print(f"⚠️  無法查詢資料庫: {e}")

def main():
    """執行完整測試"""
    print(f"\n{'#'*60}")
    print(f"# 知識匯入完整測試")
    print(f"# 測試檔案: {TEST_FILE}")
    print(f"{'#'*60}")

    try:
        # 1. 上傳檔案
        job_id = upload_file()

        # 2. 監控進度
        result = poll_status(job_id)

        # 3. 驗證結果
        verify_results(result)

        # 4. 檢查審核佇列
        check_review_queue()

        print(f"\n{'='*60}")
        print(f"✅ 測試完成")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
