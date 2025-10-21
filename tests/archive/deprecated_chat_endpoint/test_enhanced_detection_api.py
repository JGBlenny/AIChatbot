#!/usr/bin/env python3
"""
測試增強版重複問題檢測（透過 HTTP API）

測試目標：
1. 精確匹配
2. 組合策略：語義相似度 ≥ 0.80 OR 編輯距離 ≤ 2
3. 拼音檢測：語義 0.60-0.80 + 拼音相似度 ≥ 0.80
"""
import asyncio
import httpx
import json


async def clean_test_data():
    """清理測試數據"""
    print("🧹 清理測試數據...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 直接使用 psql 清理
        import subprocess
        subprocess.run([
            "docker", "exec", "aichatbot-db", "psql",
            "-U", "aichatbot", "-d", "aichatbot_admin",
            "-c", "DELETE FROM unclear_questions WHERE question LIKE '%租金%' OR question LIKE '%住金%'"
        ], capture_output=True)
    print("✅ 測試數據已清理")


async def ask_question(question: str):
    """
    向 RAG API 發送問題，會自動記錄未釐清問題
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8100/api/v1/chat",
            json={
                "question": question,
                "vendor_id": 1,  # 使用測試業者
                "user_role": "customer",
                "user_id": "test_user"
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"❌ API 錯誤: {response.status_code} - {response.text}")
            return None


async def get_unclear_questions():
    """取得未釐清問題列表"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "http://localhost:8100/api/v1/unclear-questions?status=pending&limit=20"
        )
        if response.status_code == 200:
            data = response.json()
            # API 返回格式可能是 {"questions": [...]} 或直接是列表
            if isinstance(data, dict) and 'questions' in data:
                return data['questions']
            elif isinstance(data, list):
                return data
            else:
                return []
        else:
            print(f"❌ API 錯誤: {response.status_code}")
            return []


async def test_detection():
    """測試檢測功能"""
    print("=" * 80)
    print("測試增強版重複問題檢測（透過 API）")
    print("=" * 80)

    # 清理舊數據
    await clean_test_data()

    # 測試案例
    test_cases = [
        ("每月租金幾號要繳", "原始問題", True),
        ("每月租金幾號要繳", "精確匹配", False),  # 應該合併
        ("每月租金幾號較腳", "組合策略-輕微同音錯誤", False),  # 應該合併
        ("每月住金幾號要繳", "組合策略-單字錯誤", False),  # 應該合併
        ("美越租金幾號較腳", "拼音檢測-嚴重同音錯誤", False),  # 應該合併（拼音）
        ("租金每個月幾號繳納", "語義改寫", False),  # 應該合併（語義）
    ]

    print("\n執行測試案例...")
    print("=" * 80)

    for idx, (question, description, is_first) in enumerate(test_cases, 1):
        print(f"\n測試案例 {idx}: {description}")
        print(f"問題: {question}")

        result = await ask_question(question)

        if result:
            print(f"意圖: {result.get('intent', 'N/A')}")
            print(f"信心度: {result.get('confidence', 0):.2f}")

        # 等待一下讓系統處理
        await asyncio.sleep(0.5)

    # 查詢最終結果
    print("\n" + "=" * 80)
    print("最終結果統計")
    print("=" * 80)

    questions = await get_unclear_questions()

    # 篩選租金相關問題
    rental_questions = [q for q in questions if '租金' in q['question'] or '住金' in q['question']]

    print(f"\n找到 {len(rental_questions)} 個租金相關的未釐清問題:")
    for q in rental_questions:
        print(f"\nID: {q['id']}")
        print(f"問題: {q['question']}")
        print(f"頻率: {q['frequency']}")
        print(f"首次提問: {q['first_asked_at']}")
        print(f"最後提問: {q['last_asked_at']}")

    # 評估結果
    print("\n" + "=" * 80)
    print("檢測效果評估")
    print("=" * 80)

    if len(rental_questions) == 1:
        print("✅ 完美！所有 6 個問題都被正確合併為 1 個")
        print(f"   合併後頻率: {rental_questions[0]['frequency']}")
        if rental_questions[0]['frequency'] == 6:
            print("✅ 頻率計數正確！")
        else:
            print(f"⚠️  頻率計數不符，期望 6，實際 {rental_questions[0]['frequency']}")
    elif len(rental_questions) <= 3:
        print(f"⚠️  部分成功：6 個問題合併為 {len(rental_questions)} 個")
        print("   某些檢測策略可能需要調整")
        total_freq = sum(q['frequency'] for q in rental_questions)
        print(f"   總頻率: {total_freq}/6")
    else:
        print(f"❌ 檢測效果不佳：6 個問題只合併為 {len(rental_questions)} 個")
        print("   需要檢查各層檢測邏輯")


if __name__ == "__main__":
    asyncio.run(test_detection())
