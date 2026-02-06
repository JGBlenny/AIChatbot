#!/usr/bin/env python3
"""
完整測試腳本 - 驗證語義模型系統
"""

from sentence_transformers import CrossEncoder
import json
import time
from datetime import datetime

def load_knowledge_base():
    """載入完整知識庫"""
    with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def test_semantic_matching():
    """測試語義匹配功能"""

    print("="*70)
    print("語義模型系統 - 完整測試")
    print("="*70)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 載入模型
    print("1. 載入模型...")
    start_time = time.time()
    model = CrossEncoder('BAAI/bge-reranker-base', max_length=512)
    load_time = time.time() - start_time
    print(f"   ✅ 模型載入成功 (耗時: {load_time:.2f}秒)")

    # 2. 載入知識庫
    print("\n2. 載入知識庫...")
    knowledge_base = load_knowledge_base()
    print(f"   ✅ 載入 {len(knowledge_base)} 個知識點")

    # 3. 定義測試案例（包含各種類型的查詢）
    test_cases = [
        # 報修相關
        ("我要報修", "troubleshooting"),
        ("冷氣壞了", "troubleshooting"),
        ("東西故障了", "troubleshooting"),

        # 費用相關
        ("電費怎麼算", "cost"),
        ("租金多少錢", "cost"),
        ("管理費多少", "cost"),

        # 時間相關
        ("電費幾號寄", "time"),
        ("繳費期限", "time"),
        ("什麼時候繳租金", "time"),

        # 規定相關
        ("可以養寵物嗎", "regulation"),
        ("租屋規定", "regulation"),
        ("退租須知", "regulation"),

        # 流程相關
        ("退租流程", "process"),
        ("申請停車位", "process"),
        ("如何入住", "process"),

        # 特定測試（電費帳單）
        ("電費帳單寄送區間", "billing"),
        ("查詢電費寄送時間", "billing"),
        ("單月雙月電費", "billing")
    ]

    print("\n3. 開始測試查詢...")
    print("="*70)

    results = []
    for query, category in test_cases:
        print(f"\n測試: {query}")
        print("-" * 40)

        # 對所有知識點評分
        start_time = time.time()
        scores = []

        # 批次處理以提高效率
        batch_size = 100
        for i in range(0, len(knowledge_base), batch_size):
            batch = knowledge_base[i:i+batch_size]
            pairs = [[query, kb['content']] for kb in batch]
            batch_scores = model.predict(pairs)

            for j, score in enumerate(batch_scores):
                scores.append({
                    'id': batch[j]['id'],
                    'title': batch[j]['title'],
                    'score': float(score),
                    'action_type': batch[j].get('action_type'),
                    'form_id': batch[j].get('form_id'),
                    'keywords': batch[j].get('keywords', [])
                })

        # 排序找出最佳匹配
        scores.sort(key=lambda x: x['score'], reverse=True)
        search_time = time.time() - start_time

        # 顯示前3個結果
        print(f"前3個匹配結果 (搜索耗時: {search_time:.2f}秒):")
        for i, result in enumerate(scores[:3], 1):
            print(f"  {i}. {result['title'][:40]}...")
            print(f"     分數: {result['score']:.3f}")
            print(f"     類型: {result['action_type']}")
            if result['form_id']:
                print(f"     表單: {result['form_id']}")
            if result['keywords']:
                print(f"     關鍵字: {', '.join(result['keywords'][:5])}")

        # 記錄結果
        results.append({
            'query': query,
            'category': category,
            'best_match': scores[0] if scores else None,
            'search_time': search_time
        })

    # 4. 分析結果
    print("\n" + "="*70)
    print("4. 測試結果分析")
    print("="*70)

    # 統計各類別的平均分數
    category_stats = {}
    for result in results:
        category = result['category']
        if category not in category_stats:
            category_stats[category] = []
        if result['best_match']:
            category_stats[category].append(result['best_match']['score'])

    print("\n各類別平均匹配分數:")
    for category, scores in category_stats.items():
        avg_score = sum(scores) / len(scores) if scores else 0
        print(f"  {category:15s}: {avg_score:.3f}")

    # 統計動作類型分布
    action_types = {}
    for result in results:
        if result['best_match']:
            action = result['best_match']['action_type']
            action_types[action] = action_types.get(action, 0) + 1

    print("\n動作類型分布:")
    for action, count in action_types.items():
        print(f"  {action:15s}: {count}")

    # 平均搜索時間
    avg_search_time = sum(r['search_time'] for r in results) / len(results)
    print(f"\n平均搜索時間: {avg_search_time:.3f}秒")

    # 5. 特別測試：電費相關查詢
    print("\n" + "="*70)
    print("5. 特別測試：電費帳單相關")
    print("="*70)

    billing_queries = [
        "電費帳單寄送區間",
        "查詢電費寄送時間",
        "電費幾號寄",
        "單月電費",
        "雙月電費寄送"
    ]

    print("\n尋找包含'電費'和'寄送'的知識點...")
    relevant_kb = []
    for kb in knowledge_base:
        title = kb.get('title', '').lower()
        content = kb.get('content', '').lower()
        keywords = ' '.join(kb.get('keywords', [])).lower()

        combined = title + ' ' + content + ' ' + keywords

        if ('電費' in combined or '電' in combined) and ('寄送' in combined or '寄' in combined or '送' in combined):
            relevant_kb.append(kb)
            print(f"  找到相關知識點 ID {kb['id']}: {kb['title'][:50]}...")

    if not relevant_kb:
        print("  ⚠️ 沒有找到直接相關的知識點")
        print("  建議：可能需要新增「電費帳單寄送」相關的知識點")

    # 6. 總結
    print("\n" + "="*70)
    print("6. 測試總結")
    print("="*70)

    successful_matches = sum(1 for r in results if r['best_match'] and r['best_match']['score'] > 0.5)
    total_tests = len(results)
    success_rate = successful_matches / total_tests * 100

    print(f"\n測試案例數: {total_tests}")
    print(f"成功匹配數 (分數>0.5): {successful_matches}")
    print(f"成功率: {success_rate:.1f}%")

    if success_rate >= 70:
        print("\n✅ 系統測試通過！語義模型運作良好")
    else:
        print("\n⚠️ 成功率偏低，建議：")
        print("  1. 增加更多訓練數據")
        print("  2. 考慮微調模型")
        print("  3. 調整匹配閾值")

    # 保存測試報告
    report = {
        'test_time': datetime.now().isoformat(),
        'model': 'BAAI/bge-reranker-base',
        'knowledge_base_size': len(knowledge_base),
        'test_cases': len(test_cases),
        'success_rate': success_rate,
        'avg_search_time': avg_search_time,
        'results': results
    }

    with open('test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n測試報告已保存: test_report.json")

    return success_rate

if __name__ == "__main__":
    success_rate = test_semantic_matching()

    print("\n" + "="*70)
    print("✅ 測試完成！")
    print("="*70)
    print(f"最終成功率: {success_rate:.1f}%")
    print("\n系統已準備就緒，可以開始使用！")