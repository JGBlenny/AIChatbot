#!/usr/bin/env python3
"""
測試結果深入分析腳本
基於實際 API 響應格式進行分析
"""

import json
import sys
from collections import defaultdict
from typing import Dict, List

def load_results(filename: str) -> Dict:
    """載入測試結果"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_dialogue_logic(results: List[Dict]):
    """深入分析對話邏輯"""

    print("=" * 80)
    print("📊 對話邏輯深入分析")
    print("=" * 80)

    # 1. Intent Type 分析
    intent_types = defaultdict(int)
    intent_names = defaultdict(int)
    sources_analysis = {
        "knowledge_base": 0,
        "vendor_sop": 0,
        "platform_sop": 0,
        "no_source": 0
    }

    # 2. 檢索效果分析
    confidence_distribution = {
        "high (>= 0.8)": 0,
        "medium (0.6-0.8)": 0,
        "low (< 0.6)": 0
    }

    # 3. 多語意問題分析
    multi_intent_questions = []
    ambiguous_questions = []

    # 4. 回答質量分析
    answer_lengths = []

    # 5. 特殊情況統計
    form_triggered = 0
    has_video = 0
    has_quick_replies = 0

    for result in results:
        if result["status"] != "success":
            continue

        raw = result.get("raw_response", {})

        # Intent Type
        intent_type = raw.get("intent_type", "unknown")
        intent_types[intent_type] += 1

        # Intent Name
        intent_name = raw.get("intent_name", "unknown")
        intent_names[intent_name] += 1

        # Sources
        sources = raw.get("sources", [])
        if not sources:
            sources_analysis["no_source"] += 1
        else:
            source_scope = sources[0].get("scope", "unknown")
            if source_scope in sources_analysis:
                sources_analysis[source_scope] += 1

        # Confidence
        confidence = raw.get("confidence", 0)
        if confidence >= 0.8:
            confidence_distribution["high (>= 0.8)"] += 1
        elif confidence >= 0.6:
            confidence_distribution["medium (0.6-0.8)"] += 1
        else:
            confidence_distribution["low (< 0.6)"] += 1

        # Multi-intent
        all_intents = raw.get("all_intents") or []
        if len(all_intents) > 1:
            multi_intent_questions.append({
                "question": result["question"],
                "intents": all_intents
            })

        # Answer length
        answer = raw.get("answer", "")
        answer_lengths.append(len(answer))

        # Special cases
        if raw.get("form_triggered"):
            form_triggered += 1
        if raw.get("video_url"):
            has_video += 1
        if raw.get("quick_replies"):
            has_quick_replies += 1

    total = len([r for r in results if r["status"] == "success"])

    # === 輸出分析結果 ===

    print(f"\n1️⃣  Intent Type 分布 (對話類型)")
    print("-" * 80)
    for intent_type, count in sorted(intent_types.items(), key=lambda x: -x[1]):
        print(f"  {intent_type:25s}: {count:3d} ({count/total*100:5.1f}%)")

    print(f"\n2️⃣  Intent Name TOP 15 (意圖分類)")
    print("-" * 80)
    for intent_name, count in sorted(intent_names.items(), key=lambda x: -x[1])[:15]:
        print(f"  {intent_name:30s}: {count:3d}")

    print(f"\n3️⃣  資料來源分析")
    print("-" * 80)
    for source_type, count in sorted(sources_analysis.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {source_type:20s}: {count:3d} ({count/total*100:5.1f}%)")

    print(f"\n4️⃣  信心度分布")
    print("-" * 80)
    for level, count in confidence_distribution.items():
        print(f"  {level:20s}: {count:3d} ({count/total*100:5.1f}%)")

    print(f"\n5️⃣  回答長度統計")
    print("-" * 80)
    if answer_lengths:
        avg_length = sum(answer_lengths) / len(answer_lengths)
        min_length = min(answer_lengths)
        max_length = max(answer_lengths)
        print(f"  平均長度: {avg_length:.1f} 字元")
        print(f"  最短回答: {min_length} 字元")
        print(f"  最長回答: {max_length} 字元")

    print(f"\n6️⃣  特殊功能使用")
    print("-" * 80)
    print(f"  表單觸發: {form_triggered:3d} ({form_triggered/total*100:5.1f}%)")
    print(f"  包含影片: {has_video:3d} ({has_video/total*100:5.1f}%)")
    print(f"  快速回覆: {has_quick_replies:3d} ({has_quick_replies/total*100:5.1f}%)")

    if multi_intent_questions:
        print(f"\n7️⃣  多意圖問題 ({len(multi_intent_questions)} 個)")
        print("-" * 80)
        for item in multi_intent_questions[:10]:
            intents_str = ", ".join(item["intents"])
            print(f"  Q: {item['question'][:40]}")
            print(f"     意圖: {intents_str}\n")


def analyze_by_category(results: List[Dict]):
    """按類別分析"""
    print("\n" + "=" * 80)
    print("📚 按測試類別分析")
    print("=" * 80)

    categories = defaultdict(lambda: {
        "total": 0,
        "success": 0,
        "intents": defaultdict(int),
        "avg_confidence": []
    })

    for result in results:
        cat = result["category"].split("-")[0]
        categories[cat]["total"] += 1

        if result["status"] == "success":
            categories[cat]["success"] += 1
            raw = result.get("raw_response", {})
            intent_name = raw.get("intent_name", "unknown")
            categories[cat]["intents"][intent_name] += 1
            categories[cat]["avg_confidence"].append(raw.get("confidence", 0))

    print(f"\n{'類別':15s} | {'成功率':8s} | {'平均信心度':10s} | {'主要意圖':30s}")
    print("-" * 80)

    for cat in sorted(categories.keys()):
        stats = categories[cat]
        success_rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        avg_conf = sum(stats["avg_confidence"]) / len(stats["avg_confidence"]) if stats["avg_confidence"] else 0
        top_intent = max(stats["intents"].items(), key=lambda x: x[1])[0] if stats["intents"] else "N/A"

        print(f"{cat:15s} | {success_rate:7.1f}% | {avg_conf:10.3f} | {top_intent:30s}")


def find_problem_cases(results: List[Dict]):
    """找出潛在問題案例"""
    print("\n" + "=" * 80)
    print("⚠️  潛在問題案例分析")
    print("=" * 80)

    # 1. 低信心度回答
    low_confidence = []
    # 2. 無來源回答
    no_source = []
    # 3. 回答過短
    short_answers = []
    # 4. 意圖不明確
    unclear_intent = []

    for result in results:
        if result["status"] != "success":
            continue

        raw = result.get("raw_response", {})
        confidence = raw.get("confidence", 0)
        sources = raw.get("sources", [])
        answer = raw.get("answer", "")
        intent_name = raw.get("intent_name", "")

        if confidence < 0.7:
            low_confidence.append({
                "question": result["question"],
                "confidence": confidence,
                "intent": intent_name
            })

        if not sources:
            no_source.append({
                "question": result["question"],
                "answer": answer[:100]
            })

        if len(answer) < 20:
            short_answers.append({
                "question": result["question"],
                "answer": answer,
                "length": len(answer)
            })

        if "unclear" in intent_name.lower() or not intent_name:
            unclear_intent.append({
                "question": result["question"],
                "intent": intent_name
            })

    if low_confidence:
        print(f"\n1️⃣  低信心度回答 ({len(low_confidence)} 個，信心度 < 0.7)")
        print("-" * 80)
        for item in low_confidence[:10]:
            print(f"  Q: {item['question'][:50]}")
            print(f"     信心度: {item['confidence']:.3f} | 意圖: {item['intent']}\n")

    if no_source:
        print(f"\n2️⃣  無來源回答 ({len(no_source)} 個，可能是 LLM 生成)")
        print("-" * 80)
        for item in no_source[:10]:
            print(f"  Q: {item['question'][:50]}")
            print(f"     A: {item['answer'][:80]}...\n")

    if short_answers:
        print(f"\n3️⃣  回答過短 ({len(short_answers)} 個，< 20字元)")
        print("-" * 80)
        for item in short_answers[:10]:
            print(f"  Q: {item['question'][:50]}")
            print(f"     A: {item['answer']} ({item['length']}字元)\n")

    if unclear_intent:
        print(f"\n4️⃣  意圖不明確 ({len(unclear_intent)} 個)")
        print("-" * 80)
        for item in unclear_intent[:10]:
            print(f"  Q: {item['question'][:50]}")
            print(f"     意圖: {item['intent']}\n")


def generate_recommendations(results: List[Dict]):
    """生成改進建議"""
    print("\n" + "=" * 80)
    print("💡 改進建議")
    print("=" * 80)

    # 統計數據
    total_success = len([r for r in results if r["status"] == "success"])

    intents = defaultdict(int)
    sources = defaultdict(int)
    confidences = []

    for result in results:
        if result["status"] != "success":
            continue
        raw = result.get("raw_response", {})
        intents[raw.get("intent_type", "unknown")] += 1
        source_list = raw.get("sources", [])
        if source_list:
            sources[source_list[0].get("scope", "unknown")] += 1
        confidences.append(raw.get("confidence", 0))

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    print("\n【整體評估】")
    print(f"  • 成功率: {total_success}/{len(results)} ({total_success/len(results)*100:.1f}%)")
    print(f"  • 平均信心度: {avg_confidence:.3f}")

    print("\n【核心建議】")

    # 建議 1: 檢查所有 action_type 為 None 的情況
    print("\n1. ⚠️  緊急：action_type 欄位缺失")
    print("   問題: 所有響應的 action_type 都是 None")
    print("   影響: 無法正確判斷對話流程類型（知識查詢/SOP/表單/API）")
    print("   建議:")
    print("   - 檢查 chat router 是否正確設置 action_type")
    print("   - 確認 VendorChatResponse 模型包含 action_type 欄位")
    print("   - 參考: rag-orchestrator/routers/chat.py")

    # 建議 2: sources 來源分析
    vendor_sop_count = sources.get("vendor_sop", 0)
    knowledge_base_count = sources.get("knowledge_base", 0)
    no_source_count = sources.get("no_source", 0)

    print(f"\n2. 📊 資料來源分布")
    print(f"   vendor_sop: {vendor_sop_count}/{total_success} ({vendor_sop_count/total_success*100:.1f}%)")
    print(f"   knowledge_base: {knowledge_base_count}/{total_success} ({knowledge_base_count/total_success*100:.1f}%)")
    print(f"   no_source: {no_source_count}/{total_success} ({no_source_count/total_success*100:.1f}%)")
    if vendor_sop_count > knowledge_base_count * 2:
        print("   ⚠️  vendor_sop 使用率過高，可能需要檢查")

    # 建議 3: 信心度分析
    low_confidence_count = len([c for c in confidences if c < 0.7])
    print(f"\n3. 🎯 信心度評估")
    print(f"   低信心度 (<0.7): {low_confidence_count}/{total_success} ({low_confidence_count/total_success*100:.1f}%)")
    if low_confidence_count > total_success * 0.2:
        print("   ⚠️  低信心度比例偏高，建議:")
        print("   - 優化檢索算法參數")
        print("   - 增加訓練數據")
        print("   - 調整相似度閾值")

    print("\n【詳細優化方向】")
    print("\n4. 多語意支援")
    print("   - 粵語混合: aircon唔夠凍 → 需要更好的語言識別")
    print("   - 英文簡稱: AC, deposit → 需要同義詞擴展")
    print("   - 模糊問題: \"多少錢\", \"這個可以嗎\" → 需要上下文理解")

    print("\n5. 對話流程優化")
    print("   - 確保 SOP 觸發邏輯正確（trigger_mode: manual/immediate）")
    print("   - 確保表單填寫流程完整（form_triggered, form_id）")
    print("   - 確保 API 調用流程正確（帳單、繳費記錄查詢）")

    print("\n6. 錯誤處理改進")
    print("   - 對於無意義輸入（\"......\", \"123456\"）的處理")
    print("   - 對於過短/過長問題的引導")
    print("   - 對於不相關問題的友善回應")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 analyze_test_results.py <result_file.json>")
        sys.exit(1)

    filename = sys.argv[1]
    data = load_results(filename)
    results = data.get("results", [])

    print(f"\n載入測試結果: {filename}")
    print(f"總測試數: {len(results)}")
    print(f"時間戳: {data.get('timestamp')}")

    # 執行各種分析
    analyze_dialogue_logic(results)
    analyze_by_category(results)
    find_problem_cases(results)
    generate_recommendations(results)

    print("\n" + "=" * 80)
    print("✅ 分析完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
