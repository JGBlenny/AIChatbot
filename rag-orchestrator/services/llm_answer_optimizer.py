"""
LLM 答案優化服務
使用 GPT 模型優化 RAG 檢索結果，生成更自然、更精準的答案
Phase 1 擴展：支援業者參數動態注入
Phase 3 擴展：條件式優化（快速路徑 + 模板格式化）
Phase 4 擴展：業態語氣配置從資料庫動態載入
"""
import os
import re
from typing import List, Dict, Optional
from openai import OpenAI
import time
import psycopg2
import psycopg2.extras
from .answer_formatter import AnswerFormatter
from .db_utils import get_db_config

# 業態語氣配置快取（避免頻繁查詢資料庫）
_TONE_CONFIG_CACHE: Optional[Dict[str, Dict]] = None
_TONE_CACHE_TIMESTAMP: Optional[float] = None
_TONE_CACHE_TTL = 300  # 5 分鐘快取


class LLMAnswerOptimizer:
    """LLM 答案優化器"""

    def __init__(self, config: Dict = None):
        """
        初始化 LLM 答案優化器

        Args:
            config: 配置字典
        """
        # 延遲初始化：只有在需要時才檢查 API key
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

        # 從環境變數讀取模型配置（用於降低測試成本）
        # 預設使用 gpt-3.5-turbo（速度快 2-3倍，成本低 70%）
        default_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

        # 從環境變數讀取配置
        synthesis_threshold = float(os.getenv("SYNTHESIS_THRESHOLD", "0.80"))
        fast_path_threshold = float(os.getenv("FAST_PATH_THRESHOLD", "0.75"))
        template_min_score = float(os.getenv("TEMPLATE_MIN_SCORE", "0.55"))
        template_max_score = float(os.getenv("TEMPLATE_MAX_SCORE", "0.75"))

        # 預設配置
        default_config = {
            "model": default_model,
            "temperature": float(os.getenv("LLM_ANSWER_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("LLM_ANSWER_MAX_TOKENS", "800")),
            "enable_optimization": True,
            "optimize_for_confidence": ["high", "medium"],  # 只優化高/中信心度
            "fallback_on_error": True,  # 錯誤時使用原始答案
            # Phase 2 擴展：答案合成功能
            "enable_synthesis": True,  # 是否啟用答案合成（已啟用，整合多個 SOP 項目）
            "synthesis_min_results": 2,  # 最少需要幾個結果才考慮合成
            "synthesis_max_results": 5,  # 最多合成幾個答案（調整為 5，支援更多 SOP 項目）
            "synthesis_threshold": synthesis_threshold,  # 從環境變數讀取（預設 0.80）
            # Phase 3 擴展：條件式優化
            "enable_fast_path": True,  # 是否啟用快速路徑
            "fast_path_threshold": fast_path_threshold,  # 從環境變數讀取（預設 0.75）
            "enable_template": True,  # 是否啟用模板格式化
            "template_min_score": template_min_score,  # 從環境變數讀取（預設 0.55）
            "template_max_score": template_max_score  # 從環境變數讀取（預設 0.75）
        }

        # 初始化答案格式化器
        self.formatter = AnswerFormatter()

        # 合併用戶配置與預設配置
        if config:
            self.config = {**default_config, **config}
        else:
            self.config = default_config

    @staticmethod
    def _load_tone_configs_from_db() -> Dict[str, str]:
        """
        從配置文件載入業態語氣配置

        Returns:
            Dict[business_type, tone_prompt]
        """
        try:
            from config.business_types import get_all_tone_prompts
            configs = get_all_tone_prompts()
            print(f"✅ 從配置文件載入 {len(configs)} 個業態語氣配置")
            return configs
        except Exception as e:
            print(f"⚠️ 載入業態語氣配置失敗: {e}")
            return {}

    @staticmethod
    def _get_tone_config(business_type: str) -> Optional[str]:
        """
        取得業態語氣配置（含快取機制）

        Args:
            business_type: 業態類型 (如: 'full_service', 'property_management')

        Returns:
            語氣 prompt 文字，或 None
        """
        global _TONE_CONFIG_CACHE, _TONE_CACHE_TIMESTAMP

        current_time = time.time()

        # 檢查快取是否有效
        if _TONE_CONFIG_CACHE is not None and _TONE_CACHE_TIMESTAMP is not None:
            if current_time - _TONE_CACHE_TIMESTAMP < _TONE_CACHE_TTL:
                return _TONE_CONFIG_CACHE.get(business_type)

        # 重新載入配置
        _TONE_CONFIG_CACHE = LLMAnswerOptimizer._load_tone_configs_from_db()
        _TONE_CACHE_TIMESTAMP = current_time

        return _TONE_CONFIG_CACHE.get(business_type)

    @staticmethod
    def clear_tone_cache():
        """清空業態語氣配置快取"""
        global _TONE_CONFIG_CACHE, _TONE_CACHE_TIMESTAMP
        _TONE_CONFIG_CACHE = None
        _TONE_CACHE_TIMESTAMP = None
        print("✅ 業態語氣配置快取已清空")

    def optimize_answer(
        self,
        question: str,
        search_results: List[Dict],
        confidence_level: str,
        intent_info: Dict,
        confidence_score: Optional[float] = None,
        vendor_params: Optional[Dict] = None,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None,
        enable_synthesis_override: Optional[bool] = None
    ) -> Dict:
        """
        優化答案（Phase 3 擴展：條件式優化）

        Args:
            question: 使用者問題
            search_results: RAG 檢索結果列表
            confidence_level: 信心度等級
            intent_info: 意圖資訊
            confidence_score: 信心度分數 (0-1)，用於條件式優化判斷
            vendor_params: 業者參數（Phase 1 擴展）
            vendor_name: 業者名稱（Phase 1 擴展）
            vendor_info: 完整業者資訊（包含 business_type, cashflow_model 等，Phase 1 SOP 擴展）
            enable_synthesis_override: 覆蓋答案合成配置（None=使用配置，True=強制啟用，False=強制禁用）

        Returns:
            優化結果字典，包含:
            - optimized_answer: 優化後的答案
            - original_answer: 原始答案
            - optimization_applied: 是否使用了優化
            - optimization_method: 優化方法 (fast_path/template/llm/none)
            - synthesis_applied: 是否使用了答案合成
            - tokens_used: 使用的 token 數
            - processing_time_ms: 處理時間
        """
        start_time = time.time()

        # 1. 檢查是否需要優化
        if not self._should_optimize(confidence_level, search_results):
            return self._create_fallback_response(search_results, start_time)

        # DEBUG: 記錄條件式優化參數
        print(f"🔧 條件式優化檢查: confidence_score={confidence_score}, confidence_level={confidence_level}")

        # 2. 優先檢查：多個高品質結果 → 答案合成（精煉版邏輯）
        synthesis_threshold = self.config.get("synthesis_threshold", 0.80)
        high_quality_results = [r for r in search_results if r.get('similarity', 0) > synthesis_threshold]
        force_synthesis = False

        if len(high_quality_results) >= 2 and self.config.get("enable_synthesis", True):
            # 檢測流程問題
            process_keywords = ["流程", "步驟", "如何", "怎麼", "程序", "過程"]
            is_process_question = any(kw in question for kw in process_keywords)

            # 檢測廣泛查詢（涵蓋多個主題的問題）
            broad_keywords = ["條款", "規定", "說明", "內容", "包括", "有哪些", "什麼", "包含"]
            is_broad_query = any(kw in question for kw in broad_keywords)

            # 檢查結果多樣性（不同主題數量）
            topics = set()
            for r in high_quality_results[:5]:  # 檢查前 5 個結果
                # 支援 SOP (item_name)、KB (question_summary)、和標準格式 (title)
                if 'item_name' in r:
                    topics.add(r['item_name'])
                elif 'question_summary' in r:
                    topics.add(r['question_summary'])
                elif 'title' in r:
                    topics.add(r['title'])
            has_diverse_topics = len(topics) >= 3  # 至少 3 個不同主題

            # 檢查是否有完美匹配（使用原始相似度，不含意圖加成）
            # 意圖加成只用於排序，不應影響完美匹配判斷
            max_similarity = max(
                r.get('original_similarity', r['similarity'])
                for r in high_quality_results
            )
            perfect_match_threshold = self.config.get("perfect_match_threshold", 0.95)
            has_perfect_match = max_similarity >= perfect_match_threshold

            # 強制合成的條件（優先級從高到低）：
            # 1. 流程問題（需要完整步驟）
            # 2. 廣泛查詢 + 主題多樣（涵蓋多個子主題）- 優先於完美匹配檢查
            # 3. 沒有完美匹配（需要組合多個答案）
            if is_process_question:
                force_synthesis = True
                print(f"🔄 檢測到 {len(high_quality_results)} 個高品質結果（流程問題），強制使用答案合成")
                print(f"   相似度範圍: {min(r['similarity'] for r in high_quality_results):.3f}-{max_similarity:.3f}")
            elif is_broad_query and has_diverse_topics:
                # 廣泛查詢優先於完美匹配（即使 SOP similarity=1.0 也要合成）
                force_synthesis = True
                print(f"🔄 檢測到 {len(high_quality_results)} 個高品質結果（廣泛查詢 + {len(topics)} 個不同主題），強制使用答案合成")
                print(f"   主題: {', '.join(list(topics)[:5])}")
                print(f"   相似度: {max_similarity:.3f} (忽略完美匹配，因為是廣泛查詢)")
            elif not has_perfect_match:
                force_synthesis = True
                print(f"🔄 檢測到 {len(high_quality_results)} 個高品質結果（無完美匹配: max={max_similarity:.3f} < {perfect_match_threshold}），強制使用答案合成")
            else:
                print(f"ℹ️  檢測到完美匹配（{max_similarity:.3f} >= {perfect_match_threshold}），使用單一答案優化")
                force_synthesis = False
        # 3. Phase 3 條件式優化：檢查是否可以使用快速路徑（單一結果或低品質多結果）
        elif confidence_score is not None and self.config.get("enable_fast_path", True):
            if self.formatter.should_use_fast_path(
                confidence_score,
                search_results,
                threshold=self.config.get("fast_path_threshold", 0.85)
            ):
                # 快速路徑：直接返回格式化答案，無需 LLM
                print(f"⚡ 快速路徑觸發 (信心度: {confidence_score:.3f})")
                result = self.formatter.format_simple_answer(search_results)
                answer = result["answer"]

                # ✅ Phase 1 擴展 + 方案 A：快速路徑進行參數注入和語氣調整
                if vendor_params and vendor_name:
                    print(f"   💉 快速路徑 - 注入業者參數 + 語氣調整 ({len(vendor_params)} 個)")
                    answer = self.inject_vendor_params(answer, vendor_params, vendor_name, vendor_info)

                processing_time = int((time.time() - start_time) * 1000)

                return {
                    "optimized_answer": answer,
                    "original_answer": search_results[0].get('content', ''),
                    "optimization_applied": True,
                    "optimization_method": "fast_path",
                    "synthesis_applied": False,
                    "tokens_used": 0,
                    "processing_time_ms": processing_time,
                    "model": "none"
                }

        # 4. Phase 3 條件式優化：檢查是否可以使用模板格式化（非高品質多結果時）
        elif confidence_score is not None and self.config.get("enable_template", True):
            if self.formatter.should_use_template(
                confidence_score,
                confidence_level,
                search_results
            ):
                # 模板格式化：使用預定義模板，無需 LLM
                print(f"📋 模板格式化觸發 (信心度: {confidence_score:.3f})")
                result = self.formatter.format_with_template(
                    question,
                    search_results,
                    intent_type=intent_info.get('intent_type')
                )
                answer = result["answer"]

                # ✅ Phase 1 擴展 + 方案 A：模板格式化進行參數注入和語氣調整
                if vendor_params and vendor_name:
                    print(f"   💉 模板格式化 - 注入業者參數 + 語氣調整 ({len(vendor_params)} 個)")
                    answer = self.inject_vendor_params(answer, vendor_params, vendor_name, vendor_info)

                processing_time = int((time.time() - start_time) * 1000)

                return {
                    "optimized_answer": answer,
                    "original_answer": search_results[0].get('content', ''),
                    "optimization_applied": True,
                    "optimization_method": "template",
                    "synthesis_applied": False,
                    "tokens_used": 0,
                    "processing_time_ms": processing_time,
                    "model": "none"
                }

        # 4. 準備原始答案（如果需要完整 LLM 優化）
        original_answer = self._create_original_answer(search_results)

        # 5. 判斷是否需要答案合成（Phase 2 擴展）
        # 支援動態覆蓋：如果有多個高品質結果，強制啟用合成；否則使用原有邏輯
        if force_synthesis:
            should_synthesize = True
            print(f"✅ 強制啟用答案合成（{len(high_quality_results)} 個高品質結果）")
        else:
            should_synthesize = self._should_synthesize(
                question,
                search_results,
                enable_synthesis_override
            )

        # 6. 執行完整 LLM 優化（Phase 1 擴展：加入業者參數注入；Phase 2 擴展：答案合成）
        try:
            if should_synthesize:
                # 使用答案合成模式
                conf_str = f"{confidence_score:.3f}" if confidence_score is not None else "N/A"
                print(f"🔄 答案合成模式 (信心度: {conf_str})")
                optimized_answer, tokens_used = self.synthesize_answer(
                    question=question,
                    search_results=search_results,
                    intent_info=intent_info,
                    vendor_params=vendor_params,
                    vendor_name=vendor_name,
                    vendor_info=vendor_info
                )
                synthesis_applied = True
            else:
                # 使用傳統優化模式
                conf_str = f"{confidence_score:.3f}" if confidence_score is not None else "N/A"
                print(f"🤖 完整 LLM 優化 (信心度: {conf_str})")
                optimized_answer, tokens_used = self._call_llm(
                    question=question,
                    search_results=search_results,
                    intent_info=intent_info,
                    vendor_params=vendor_params,
                    vendor_name=vendor_name,
                    vendor_info=vendor_info
                )
                synthesis_applied = False

            processing_time = int((time.time() - start_time) * 1000)

            return {
                "optimized_answer": optimized_answer,
                "original_answer": original_answer,
                "optimization_applied": True,
                "optimization_method": "synthesis" if synthesis_applied else "llm",
                "synthesis_applied": synthesis_applied,  # 新增：標記是否使用了合成
                "tokens_used": tokens_used,
                "processing_time_ms": processing_time,
                "model": self.config["model"]
            }

        except Exception as e:
            print(f"❌ LLM 優化失敗: {e}")

            if self.config["fallback_on_error"]:
                # 錯誤時使用原始答案
                processing_time = int((time.time() - start_time) * 1000)
                return {
                    "optimized_answer": original_answer,
                    "original_answer": original_answer,
                    "optimization_applied": False,
                    "synthesis_applied": False,
                    "tokens_used": 0,
                    "processing_time_ms": processing_time,
                    "error": str(e)
                }
            else:
                raise

    def _should_optimize(self, confidence_level: str, search_results: List[Dict]) -> bool:
        """判斷是否應該優化"""
        if not self.config["enable_optimization"]:
            return False

        if not search_results:
            return False

        if confidence_level not in self.config["optimize_for_confidence"]:
            return False

        return True

    def _should_synthesize(
        self,
        question: str,
        search_results: List[Dict],
        enable_synthesis_override: Optional[bool] = None
    ) -> bool:
        """
        判斷是否需要答案合成

        觸發條件（全部滿足）：
        1. 啟用合成功能
        2. 至少有指定數量的檢索結果
        3. 問題包含複合需求關鍵字（這類問題通常需要多方面資訊）
        4. 沒有單一高分答案（最高相似度 < 閾值）

        Args:
            question: 用戶問題
            search_results: 檢索結果列表
            enable_synthesis_override: 覆蓋配置（None=使用配置，True=強制啟用，False=強制禁用）

        Returns:
            是否應該合成答案
        """
        # 1. 功能開關（支援動態覆蓋）
        if enable_synthesis_override is not None:
            # 如果傳入覆蓋值，使用覆蓋值
            if not enable_synthesis_override:
                return False
        else:
            # 否則使用配置
            if not self.config.get("enable_synthesis", False):
                return False

        # 2. 結果數量
        min_results = self.config.get("synthesis_min_results", 2)
        if len(search_results) < min_results:
            return False

        # 3. 複合問題關鍵字（這類問題通常需要多方面資訊）
        complex_keywords = ["如何", "怎麼", "流程", "步驟", "需要", "什麼時候", "注意", "準備", "辦理"]
        has_complex_pattern = any(kw in question for kw in complex_keywords)

        # 4. 沒有單一高分答案（表示可能需要組合多個答案）
        threshold = self.config.get("synthesis_threshold", 0.7)
        max_similarity = max(r['similarity'] for r in search_results[:min_results])
        no_perfect_match = max_similarity < threshold

        # 記錄判斷結果（用於調試）
        if has_complex_pattern and no_perfect_match:
            print(f"🔄 答案合成觸發：問題類型={has_complex_pattern}, 最高相似度={max_similarity:.3f} < {threshold}")

        return has_complex_pattern and no_perfect_match

    def _get_result_title(self, result: Dict) -> str:
        """
        獲取檢索結果的標題（支援 KB 和 SOP 格式）

        Args:
            result: 檢索結果

        Returns:
            標題字串（KB 使用 question_summary，SOP 使用 item_name）
        """
        if 'question_summary' in result:
            return result['question_summary']
        elif 'item_name' in result:
            return result['item_name']
        else:
            return "（無標題）"

    def _create_original_answer(self, search_results: List[Dict]) -> str:
        """建立原始答案（未優化）"""
        if not search_results:
            return ""

        best_result = search_results[0]
        title = self._get_result_title(best_result)
        content = best_result.get('content', '')

        return f"{title}\n\n{content}"

    def _create_fallback_response(self, search_results: List[Dict], start_time: float) -> Dict:
        """建立備用回應（不優化）"""
        original_answer = self._create_original_answer(search_results)
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "optimized_answer": original_answer,
            "original_answer": original_answer,
            "optimization_applied": False,
            "tokens_used": 0,
            "processing_time_ms": processing_time
        }

    def _replace_params_deterministic(
        self,
        content: str,
        vendor_params: Dict,
        vendor_name: str
    ) -> str:
        """
        階段 1：確定性參數替換（不使用 LLM）

        使用正則表達式和字符串匹配，100% 可靠地替換參數值

        Args:
            content: 原始內容
            vendor_params: 業者參數字典
            vendor_name: 業者名稱

        Returns:
            參數替換後的內容
        """
        result = content
        replacements_made = []

        # 1. 替換明確的模板變數 {{xxx}}
        for key, value in vendor_params.items():
            pattern = f"{{{{{key}}}}}"
            if pattern in result:
                # 處理 dict 格式的業者參數（包含 display_name, value, unit）
                if isinstance(value, dict):
                    param_value = value.get('value', '')
                    unit = value.get('unit', '')
                    full_value = f"{param_value}{unit}" if unit else param_value
                else:
                    full_value = str(value)

                result = result.replace(pattern, full_value)
                replacements_made.append(f"{{{{{{{key}}}}}}} → {full_value}")

        # 2. 智能匹配常見模式並替換

        # 2a. 電話號碼模式（如 0800-123-456, 02-1234-5678）
        if 'service_hotline' in vendor_params:
            phone_patterns = [
                r'\d{4}-\d{3}-\d{3}',  # 0800-123-456
                r'\d{2}-\d{4}-\d{4}',  # 02-1234-5678
                r'\d{4}-\d{6}',        # 0800-123456
            ]
            for pattern in phone_patterns:
                matches = re.findall(pattern, result)
                for match in matches:
                    # 排除緊急專線等特定號碼
                    if '0911' not in match and '119' not in match:
                        hotline_value = vendor_params['service_hotline'].get('value', vendor_params['service_hotline']) if isinstance(vendor_params['service_hotline'], dict) else vendor_params['service_hotline']
                        result = result.replace(match, hotline_value)
                        replacements_made.append(f"{match} → {hotline_value} (電話)")
                        break  # 只替換第一個匹配

        # 2b. 工作天數模式（如 "3個工作天"）- 暫時停用
        # 原因：repair_response_time 的單位是「小時」，無法直接替換「天」
        # 如果需要替換天數，應該在資料庫中新增 repair_response_days 參數
        # if 'repair_response_days' in vendor_params:
        #     time_pattern = r'(\d+)\s*(個)?工作天'
        #     matches = re.finditer(time_pattern, result)
        #     for match in matches:
        #         old_value = match.group(1)
        #         if int(old_value) <= 7:
        #             full_match = match.group(0)
        #             new_text = f"{vendor_params['repair_response_days']}個工作天"
        #             result = result.replace(full_match, new_text, 1)
        #             replacements_made.append(f"{full_match} → {new_text} (時效)")

        # 2c. 小時數模式（如 "24小時"）- 針對 repair_response_time
        if 'repair_response_time' in vendor_params:
            hour_pattern = r'(\d+)\s*小時'
            # 只在提到"回應"或"處理"的上下文中替換
            if '回應' in result or '處理' in result:
                matches = list(re.finditer(hour_pattern, result))
                for match in matches:
                    old_value = match.group(1)
                    # 只替換合理範圍內的小時數
                    if 12 <= int(old_value) <= 72:
                        full_match = match.group(0)
                        # 檢查前後文，確保是維修相關
                        start = max(0, match.start() - 20)
                        end = min(len(result), match.end() + 20)
                        context = result[start:end]
                        if '緊急' not in context:  # 不替換緊急專線的24小時
                            response_time_value = vendor_params['repair_response_time'].get('value', vendor_params['repair_response_time']) if isinstance(vendor_params['repair_response_time'], dict) else vendor_params['repair_response_time']
                            new_text = f"{response_time_value} 小時"
                            result = result.replace(full_match, new_text, 1)
                            replacements_made.append(f"{full_match} → {new_text} (時效)")
                            break


        if replacements_made:
            print(f"      ✅ 確定性替換完成：{len(replacements_made)} 項")
            for r in replacements_made:
                print(f"         - {r}")
        else:
            print(f"      ℹ️  無需確定性替換")

        return result

    def inject_vendor_params(
        self,
        content: str,
        vendor_params: Dict,
        vendor_name: str,
        vendor_info: Optional[Dict] = None
    ) -> str:
        """
        使用兩階段方法進行參數注入和語氣調整（方案 C）

        階段 1: 確定性參數替換 - 使用正則和字符串匹配，100% 可靠
        階段 2: 語氣調整 - 使用 LLM 調整表達方式（不做參數替換）

        Args:
            content: 原始知識內容
            vendor_params: 業者參數字典
            vendor_name: 業者名稱
            vendor_info: 完整業者資訊（包含 business_type 等）

        Returns:
            調整後的內容
        """
        if not vendor_params:
            return content

        print(f"      🔍 兩階段參數注入 + 語氣調整 - 原始內容長度: {len(content)} 字元")
        print(f"      📋 業者參數: {list(vendor_params.keys())}")

        # === 階段 1：確定性參數替換（不用 LLM）===
        content = self._replace_params_deterministic(content, vendor_params, vendor_name)

        # === 階段 2：語氣調整（使用 LLM）===
        # 檢查是否需要語氣調整
        business_type = 'property_management'  # 預設值
        if vendor_info:
            business_type = vendor_info.get('business_type', 'property_management')
            print(f"      🏢 業種類型: {business_type}")

        # 根據業種類型調整語氣
        tone_prompt = self._get_tone_config(business_type)

        # 如果沒有語氣配置，直接返回（跳過階段 2）
        if not tone_prompt:
            print(f"      ℹ️  業態類型 '{business_type}' 無語氣配置，跳過 LLM 調整")
            return content

        # 有語氣配置，使用 LLM 調整
        system_prompt = f"""你是一個專業的語氣調整助理。

**重要原則**：
1. ❌ **禁止修改任何數值**（電話、日期、金額、時間等）
2. ❌ **禁止輸出模板變數格式**（如 {{{{service_hotline}}}}、@vendorA 等）
3. ✅ **只調整語氣和表達方式**（使內容更符合業態風格）
4. ✅ **保持內容結構和格式**（標題、列表、段落）

業者名稱：{vendor_name}
業種類型：{business_type}

【語氣調整規範】
{tone_prompt}

注意：
- 內容中的所有數值都已經是正確的業者參數，請勿修改
- 只調整用詞、語氣、表達方式
- 只輸出調整後的內容，不要加上任何說明"""

        user_prompt = f"""請根據業種語氣調整以下內容（請勿修改任何數值）：

{content}"""

        try:
            if not self.client:
                raise Exception("OpenAI client not initialized (missing API key)")

            # 方案 C: 語氣調整專用，temperature 0.3 足夠（不做參數替換）
            tone_adjustment_temp = float(os.getenv("LLM_TONE_ADJUSTMENT_TEMP", "0.3"))
            response = self.client.chat.completions.create(
                model=self.config["model"],
                temperature=tone_adjustment_temp,  # 預設 0.3
                max_tokens=self.config["max_tokens"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            adjusted_content = response.choices[0].message.content.strip()

            # 檢查內容是否有變化
            if adjusted_content != content:
                print(f"      ✅ 語氣調整完成 - 內容已調整")
                print(f"         原始: {content[:100]}...")
                print(f"         調整: {adjusted_content[:100]}...")
            else:
                print(f"      ℹ️  內容未變化（無需語氣調整）")

            return adjusted_content

        except Exception as e:
            print(f"      ⚠️  語氣調整失敗，使用原始內容: {e}")
            return content

    def synthesize_answer(
        self,
        question: str,
        search_results: List[Dict],
        intent_info: Dict,
        vendor_params: Optional[Dict] = None,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None
    ) -> tuple[str, int]:
        """
        合成多個答案為一個完整答案（Phase 2 擴展功能）

        當檢索到的多個答案各有側重時，使用 LLM 將它們合成為一個完整、結構化的答案。
        這可以提升答案的完整性，特別適用於複雜問題。

        Args:
            question: 用戶問題
            search_results: 多個檢索結果
            intent_info: 意圖資訊
            vendor_params: 業者參數（用於動態注入）
            vendor_name: 業者名稱
            vendor_info: 完整業者資訊（包含 business_type, cashflow_model 等）

        Returns:
            (合成後的答案, 使用的 tokens 數)
        """
        # 準備多個答案的上下文（先進行參數注入）
        max_results = self.config.get("synthesis_max_results", 3)
        answers_to_synthesize = []

        for i, result in enumerate(search_results[:max_results], 1):
            content = result['content']

            print(f"   📄 答案 {i} 原始內容（前100字）: {content[:100]}...")

            # 如果有業者參數，先進行智能參數注入和語氣調整
            if vendor_params and vendor_name:
                print(f"   💉 對答案 {i} 執行參數注入...")
                content = self.inject_vendor_params(content, vendor_params, vendor_name, vendor_info)
                print(f"   ✅ 答案 {i} 注入後內容（前100字）: {content[:100]}...")
            else:
                print(f"   ⚠️  跳過答案 {i} 的參數注入（vendor_params或vendor_name為空）")

            answers_to_synthesize.append({
                "index": i,
                "title": self._get_result_title(result),
                "content": content,
                "similarity": result['similarity']
            })

        # 格式化答案列表
        formatted_answers = "\n\n".join([
            f"【答案 {ans['index']}】\n"
            f"標題：{ans['title']}\n"
            f"相似度：{ans['similarity']:.2f}\n"
            f"內容：\n{ans['content']}"
            for ans in answers_to_synthesize
        ])

        # 建立合成 Prompt（加入業者參數）
        system_prompt = self._create_synthesis_system_prompt(intent_info, vendor_name, vendor_info, vendor_params)
        user_prompt = self._create_synthesis_user_prompt(question, formatted_answers, intent_info)

        # 檢查 API key
        if not self.client:
            raise Exception("OpenAI client not initialized (missing API key)")

        # 呼叫 OpenAI API 進行合成
        synthesis_temp = float(os.getenv("LLM_SYNTHESIS_TEMP", "0.5"))
        response = self.client.chat.completions.create(
            model=self.config["model"],
            temperature=synthesis_temp,  # 從環境變數讀取，稍低溫度以確保準確性和結構
            max_tokens=self.config["max_tokens"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        synthesized_answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        print(f"✨ 答案合成完成：使用了 {len(answers_to_synthesize)} 個來源，tokens: {tokens_used}")

        return synthesized_answer, tokens_used

    def _create_synthesis_system_prompt(
        self,
        intent_info: Dict,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None,
        vendor_params: Optional[Dict] = None
    ) -> str:
        """建立答案合成的系統提示詞"""
        intent_type = intent_info.get('intent_type', 'knowledge')

        # 調試：檢查 vendor_params
        print(f"   🔍 調試 - vendor_params 類型: {type(vendor_params)}, 是否為空: {not vendor_params}")
        if vendor_params:
            print(f"   🔍 調試 - vendor_params 數量: {len(vendor_params)}, 前3個 key: {list(vendor_params.keys())[:3]}")

        base_prompt = """你是一個專業的知識整合助理。你的任務是將多個相關但各有側重的答案，合成為一個完整、準確、結構化的回覆。

合成要求：
1. **完整性**：涵蓋所有重要資訊，不遺漏任何關鍵步驟或細節
2. **準確性**：資訊必須來自提供的答案，不要編造或推測
3. **結構化**：使用清晰的標題、列表、步驟編號，使答案易於閱讀
4. **去重**：如果多個答案提到相同資訊，只保留一次，避免重複
5. **優先級**：優先使用相似度較高的答案內容
6. **語氣**：保持專業、友善、易懂的繁體中文表達
7. **Markdown**：適當使用 Markdown 格式（## 標題、- 列表、**粗體**）"""

        rule_number = 8

        # 如果有業者參數，加入參數替換指令
        if vendor_params:
            print(f"   ✅ 加入業者參數替換指令到合成提示詞")
            base_prompt += f"\n{rule_number}. **業者參數替換（重要）**：\n"
            base_prompt += "   - ⚠️ **必須替換通用描述為具體值**：\n"
            base_prompt += "     * 「依業者規定」、「根據合約規定」→ 使用下方業者參數的具體值\n"
            base_prompt += "     * 「固定金額」、「具體天數」→ 使用下方業者參數的具體值\n"
            base_prompt += "     * 「請聯繫我們確認」→ 直接給出具體值，不要保留模糊說法\n\n"

            # 格式化業者參數列表
            base_prompt += "   - 📋 **可用的業者參數**：\n"
            params_added = 0
            for key, value in vendor_params.items():
                if isinstance(value, dict):
                    display_name = value.get('display_name', key)
                    param_value = value.get('value', '')
                    unit = value.get('unit', '')
                    full_value = f"{param_value}{unit}" if unit else param_value
                    base_prompt += f"     * **{display_name}**: {full_value}\n"
                    params_added += 1
            print(f"   📋 已加入 {params_added} 個業者參數到提示詞")

            base_prompt += "\n   - 📌 **替換示例（必須遵循）**：\n"
            base_prompt += "     * ❌ 錯誤：「寬限期依業者規定」\n"
            base_prompt += "     * ✅ 正確：「寬限期為3天」（使用業者參數）\n"
            base_prompt += "     * ❌ 錯誤：「逾期費用為固定金額」\n"
            base_prompt += "     * ✅ 正確：「逾期費用為300元」（使用業者參數）\n"

            rule_number += 1
        else:
            print(f"   ⚠️  未加入業者參數（vendor_params 為空）")

        # 如果有業者名稱，加入業者資訊
        if vendor_name:
            base_prompt += f"\n{rule_number}. **業者身份**：你代表 {vendor_name}，請使用該業者的資訊回答"
            rule_number += 1

        # 根據業種類型調整語氣（Phase 4 擴展：從資料庫載入 - 簡化版）
        if vendor_info:
            business_type = vendor_info.get('business_type', 'property_management')
            tone_prompt = self._get_tone_config(business_type)
            if tone_prompt:
                # 將完整的 tone prompt 加入（簡潔版本，用於答案合成）
                base_prompt += f"\n{rule_number}. **業種語氣**：{vendor_name} 的語氣調整規範如下：\n{tone_prompt}"
                rule_number += 1

        # 根據意圖類型調整提示
        if intent_type == "knowledge":
            base_prompt += f"\n{rule_number}. **知識類型**：這是知識查詢，請提供完整的說明、步驟和注意事項"
        elif intent_type == "data_query":
            base_prompt += f"\n{rule_number}. **資料查詢**：如需查詢具體資料，請說明如何查詢和所需資料"
        elif intent_type == "action":
            base_prompt += f"\n{rule_number}. **操作指引**：請提供具體、可執行的操作步驟"

        base_prompt += "\n\n重要：只輸出合成後的完整答案，不要加上「根據以上資訊」等元資訊。"

        # 調試：輸出prompt的前1500字元
        print(f"   📝 合成提示詞長度: {len(base_prompt)} 字元")
        print(f"   📝 合成提示詞（前1500字）: {base_prompt[:1500]}...")

        return base_prompt

    def _create_synthesis_user_prompt(self, question: str, formatted_answers: str, intent_info: Dict) -> str:
        """建立答案合成的使用者提示詞"""
        keywords = intent_info.get('keywords', [])
        keywords_str = "、".join(keywords) if keywords else "無"

        # 檢測是否為流程/步驟類問題
        process_keywords = ["流程", "步驟", "如何", "怎麼", "程序", "過程"]
        is_process_question = any(kw in question for kw in process_keywords)

        prompt = f"""使用者問題：{question}

意圖類型：{intent_info.get('intent_name', '未知')}
關鍵字：{keywords_str}

以下是多個相關答案，請將它們合成為一個完整的回覆：

{formatted_answers}

請綜合以上答案，生成一個完整、準確、結構化的回覆。確保："""

        if is_process_question:
            # 流程類問題：強調完整性和順序性
            prompt += """
- **完整流程**：這是流程相關問題，請包含所有檢索到的步驟，按時間順序整理（從開始到結束）
- **不要遺漏步驟**：即使某個步驟在問題中沒有直接提到，只要它是流程的一部分，就必須包含
- **時序邏輯**：請按照實際執行的先後順序組織答案（例如：申請→審核→批准→簽約）
- 使用清晰的編號或標題標示每個步驟
- 涵蓋所有重要資訊
- 避免重複
- 保持準確性
- **請直接回答，不要在答案中提及「答案1」、「答案2」等來源編號**"""
        else:
            # 一般問題：保持原有邏輯
            prompt += """
- **優先使用與問題主題最相關的答案**
- 如果某個答案與當前問題無關，請忽略它
- 只整合能回答當前問題的內容
- 涵蓋所有重要資訊
- 使用清晰的結構（標題、列表、步驟）
- 避免重複
- 保持準確性
- **請直接回答，不要在答案中提及「答案1」、「答案2」等來源編號**"""

        return prompt

    def _call_llm(
        self,
        question: str,
        search_results: List[Dict],
        intent_info: Dict,
        vendor_params: Optional[Dict] = None,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None
    ) -> tuple[str, int]:
        """
        呼叫 LLM 優化答案

        Args:
            question: 使用者問題
            search_results: 檢索結果
            intent_info: 意圖資訊
            vendor_params: 業者參數（用於動態注入）
            vendor_name: 業者名稱
            vendor_info: 完整業者資訊（包含 business_type, cashflow_model 等）

        Returns:
            (優化後的答案, 使用的 tokens 數)
        """
        # 1. 準備檢索結果上下文（先進行參數注入）
        context_parts = []
        for i, result in enumerate(search_results[:3], 1):  # 最多使用前 3 個結果
            content = result['content']

            # Phase 1 擴展 + 方案 A：如果有業者參數，先進行智能參數注入和語氣調整
            if vendor_params and vendor_name:
                content = self.inject_vendor_params(content, vendor_params, vendor_name, vendor_info)

            context_parts.append(
                f"【參考資料 {i}】\n"
                f"標題：{self._get_result_title(result)}\n"
                f"內容：{content}\n"
                f"相似度：{result['similarity']:.2f}"
            )

        context = "\n\n".join(context_parts)

        # 2. 建立優化 Prompt（加入業者參數）
        system_prompt = self._create_system_prompt(intent_info, vendor_name, vendor_info, vendor_params)
        user_prompt = self._create_user_prompt(question, context, intent_info)

        # 檢查 API key
        if not self.client:
            raise Exception("OpenAI client not initialized (missing API key)")

        # 3. 呼叫 OpenAI API
        response = self.client.chat.completions.create(
            model=self.config["model"],
            temperature=self.config["temperature"],
            max_tokens=self.config["max_tokens"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        optimized_answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return optimized_answer, tokens_used

    def _create_system_prompt(
        self,
        intent_info: Dict,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None,
        vendor_params: Optional[Dict] = None
    ) -> str:
        """建立系統提示詞"""
        intent_type = intent_info.get('intent_type', 'knowledge')

        base_prompt = """你是一個專業、友善的客服助理。

🎯 **核心任務**：用業者的實際參數值回答問題，參考資料僅作為回答架構參考。

回答要求：
1. 直接回答問題，不要重複問題內容
2. 使用繁體中文，語氣親切專業
3. **【重要】參數替換規則 - 業者參數絕對優先**：
   - ⚠️ 參考資料是通用範本，**所有數值都必須被業者參數覆蓋**
   - ⚠️ 即使參考資料說「內政部規定」、「通常」、「一般」，仍須使用業者參數
   - 你**必須替換**以下所有類型的數值：
     * 明確數值：「每月1號」→ payment_day=5 → 答「每月5號」
     * 時間描述：「一個月」→ termination_notice_days=60 → 答「60天（兩個月）」
     * 金額描述：「一個月租金」→ early_termination_fee=5000 → 答「5000元」
     * 日期範圍：「1日至5日」→ grace_period=3 → 答「3天寬限期」
     * 數字描述：「兩個月」→ deposit_months=2 → 答「2個月」
4. 如有步驟或流程，請清楚列出
5. 適當使用 Markdown 格式（標題、列表）使答案更易讀
6. 保持簡潔，避免冗長
7. 如果參考資料不足以回答，請誠實說明"""

        rule_number = 8

        # 如果有業者名稱，加入業者資訊
        if vendor_name:
            base_prompt += f"\n{rule_number}. 你代表 {vendor_name}，請使用該業者的資訊回答"
            rule_number += 1

        # 【新增】如果有業者參數，明確列出所有參數供 AI 參考
        if vendor_params:
            base_prompt += f"\n{rule_number}. **【關鍵】業者特定參數 - 絕對優先使用**：\n"
            base_prompt += "   - ⚠️ **參考資料中的所有數值都是範例**，包括明確數字、通用描述（如「一個月」、「一個月租金」、「1日至5日」）\n"
            base_prompt += "   - ✅ **必須用以下業者參數覆蓋**參考資料中的任何相關數值\n"
            base_prompt += "   - 📌 **替換示例（必須遵循）**：\n"
            base_prompt += "     * 參考資料：「每月1號」→ 使用 payment_day=5 → 答案：「每月5號」\n"
            base_prompt += "     * 參考資料：「提前一個月通知」→ 使用 termination_notice_days=60 → 答案：「提前60天（兩個月）通知」\n"
            base_prompt += "     * 參考資料：「違約金一個月租金」→ 使用 early_termination_fee=5000 → 答案：「違約金5000元」\n"
            base_prompt += "     * 參考資料：「1日至5日寬限期」→ 使用 grace_period=3 → 答案：「3天寬限期」\n"
            base_prompt += "     * ⚠️ 參考資料：「逾期費用為固定金額」→ 使用 late_fee=300元 → 答案：「逾期費用為300元」（**不可省略具體金額**）\n"
            base_prompt += "     * ⚠️ 參考資料：「寬限期根據合約規定」→ 使用 grace_period=3天 → 答案：「寬限期為3天」（**不可省略具體天數**）\n"
            base_prompt += "     * ⚠️ 問題「續約前多久通知」→ **只能**使用 renewal_notice_days（30天），**絕不**使用 termination_notice_days\n"
            base_prompt += "     * ⚠️ 問題「提前解約/終止」→ **只能**使用 termination_notice_days（60天），**絕不**使用 renewal_notice_days\n"
            base_prompt += "   - 🎯 以下是該業者的**真實參數值**，請務必使用：\n\n"

            # 將參數按類別組織，更易讀
            payment_params = {}
            service_params = {}
            contract_params = {}
            other_params = {}

            for key, value in vendor_params.items():
                if 'payment' in key or 'fee' in key or 'late' in key or 'grace' in key:
                    payment_params[key] = value
                elif 'service' in key or 'hotline' in key or 'hours' in key or 'repair' in key or 'line' in key or 'address' in key:
                    service_params[key] = value
                elif 'lease' in key or 'deposit' in key or 'termination' in key or 'notice' in key:
                    contract_params[key] = value
                else:
                    other_params[key] = value

            # 格式化參數顯示的輔助函數
            def format_param(key, value):
                """格式化參數顯示，優先使用中文 display_name"""
                # 特定參數的使用場景說明
                usage_hints = {
                    'renewal_notice_days': '← ⚠️ **只用於「續約」問題，不可用於解約**',
                    'termination_notice_days': '← ⚠️ **只用於「提前解約/終止」問題，不可用於續約**',
                    'late_fee': '← ⚠️ **必須補充具體金額到答案中**',
                    'grace_period': '← ⚠️ **必須補充具體天數到答案中**'
                }

                # 檢查 value 是否為 dict（包含 display_name, unit 等完整資訊）
                if isinstance(value, dict):
                    display_name = value.get('display_name', key)
                    param_value = value.get('value', '')
                    unit = value.get('unit', '')
                    full_value = f"{param_value}{unit}" if unit else param_value
                    hint = usage_hints.get(key, '← 必須使用此值')
                    return f"   - **{display_name}** ({key}): **{full_value}** {hint}\n"
                else:
                    # 向後兼容：如果是簡單字串值
                    hint = usage_hints.get(key, '← 必須使用此值')
                    return f"   - {key}: **{value}** {hint}\n"

            # 繳費相關參數
            if payment_params:
                base_prompt += "   【繳費相關】**（覆蓋參考資料中的所有相關數值）**\n"
                for key, value in payment_params.items():
                    base_prompt += format_param(key, value)

            # 服務相關參數
            if service_params:
                base_prompt += "   【客服聯絡】**（覆蓋參考資料中的所有相關數值）**\n"
                for key, value in service_params.items():
                    base_prompt += format_param(key, value)

            # 合約相關參數
            if contract_params:
                base_prompt += "   【合約條款】**（覆蓋參考資料中的所有相關數值）**\n"
                for key, value in contract_params.items():
                    base_prompt += format_param(key, value)

            # 其他參數
            if other_params:
                base_prompt += "   【其他資訊】**（覆蓋參考資料中的所有相關數值）**\n"
                for key, value in other_params.items():
                    base_prompt += format_param(key, value)

            base_prompt += "\n   ⚠️ **最後檢查清單**：\n"
            base_prompt += "   - [ ] 參考資料中的日期/數字是否已替換？（如「1號」→「5號」、「一個月」→「60天」）\n"
            base_prompt += "   - [ ] 參考資料中的金額是否已替換？（如「一個月租金」→「5000元」）\n"
            base_prompt += "   - [ ] 參考資料中的時間範圍是否已替換？（如「1日至5日」→「3天」）\n"
            base_prompt += "   - [ ] 所有通用描述是否都已用實際參數值覆蓋？\n"
            rule_number += 1

        # 根據業種類型調整語氣（Phase 4 擴展：從資料庫載入 - 簡化版）
        if vendor_info:
            business_type = vendor_info.get('business_type', 'property_management')
            tone_prompt = self._get_tone_config(business_type)
            if tone_prompt:
                # 將完整的 tone prompt 加入（簡潔版本，用於答案優化）
                base_prompt += f"\n{rule_number}. 【業種語氣】{vendor_name} 的語氣調整規範如下：\n{tone_prompt}"
                rule_number += 1

        # 根據意圖類型調整提示
        if intent_type == "knowledge":
            base_prompt += f"\n{rule_number}. 這是知識查詢問題，請提供清楚的說明和步驟"
        elif intent_type == "data_query":
            base_prompt += f"\n{rule_number}. 這是資料查詢問題，如需查詢具體資料，請說明如何查詢"
        elif intent_type == "action":
            base_prompt += f"\n{rule_number}. 這是操作執行問題，請說明具體操作步驟"

        return base_prompt

    def _create_user_prompt(self, question: str, context: str, intent_info: Dict) -> str:
        """建立使用者提示詞"""
        keywords = intent_info.get('keywords', [])
        keywords_str = "、".join(keywords) if keywords else "無"

        # 檢測是否為流程/步驟類問題
        process_keywords = ["流程", "步驟", "如何", "怎麼", "程序", "過程"]
        is_process_question = any(kw in question for kw in process_keywords)

        prompt = f"""使用者問題：{question}

意圖類型：{intent_info.get('intent_name', '未知')}
關鍵字：{keywords_str}

參考資料：
{context}

請根據以上參考資料，用自然、友善的語氣回答使用者的問題。

⚠️ 重要提醒："""

        if is_process_question:
            # 流程類問題：包含所有步驟
            prompt += """
1. **這是流程相關問題**：請包含所有參考資料中的步驟，按時間順序整理
2. 即使某個步驟在問題中沒有直接提到，只要它是完整流程的一部分，就應該包含
3. 請按照實際執行的先後順序組織答案（例如：申請→審核→批准→簽約）
4. 相似度分數僅供參考，請以流程的完整性為主
5. **請直接回答，不要在答案中提及「參考資料1」、「參考資料2」等來源編號**"""
        else:
            # 一般問題：保持原有邏輯
            prompt += """
1. **請仔細閱讀每個參考資料，選擇最能回答當前問題的那個**
2. 如果某個參考資料的標題/內容與問題不直接相關，請不要使用它
3. 優先使用與問題主題最匹配的參考資料
4. 相似度分數僅供參考，請以內容相關性為主
5. **請直接回答，不要在答案中提及「參考資料1」、「參考資料2」等來源編號**"""

        return prompt

    def get_optimization_stats(self, optimizations: List[Dict]) -> Dict:
        """
        計算優化統計資訊

        Args:
            optimizations: 優化結果列表

        Returns:
            統計資訊字典
        """
        if not optimizations:
            return {
                "total_optimizations": 0,
                "successful_optimizations": 0,
                "total_tokens_used": 0,
                "avg_tokens_per_optimization": 0,
                "avg_processing_time_ms": 0
            }

        total = len(optimizations)
        successful = sum(1 for o in optimizations if o.get('optimization_applied', False))
        total_tokens = sum(o.get('tokens_used', 0) for o in optimizations)
        total_time = sum(o.get('processing_time_ms', 0) for o in optimizations)

        return {
            "total_optimizations": total,
            "successful_optimizations": successful,
            "success_rate": round(successful / total, 3) if total > 0 else 0,
            "total_tokens_used": total_tokens,
            "avg_tokens_per_optimization": round(total_tokens / successful, 1) if successful > 0 else 0,
            "avg_processing_time_ms": round(total_time / total, 1) if total > 0 else 0
        }


# 使用範例
if __name__ == "__main__":
    import asyncio

    async def test_optimizer():
        """測試 LLM 答案優化器"""
        optimizer = LLMAnswerOptimizer()

        # 模擬檢索結果
        search_results = [
            {
                "id": 1,
                "title": "退租流程說明",
                "category": "合約問題",
                "content": """# 退租流程

## 步驟說明

1. **提前通知**：請於退租日前30天以書面方式通知房東
2. **繳清費用**：確認所有租金、水電費已繳清
3. **房屋檢查**：與房東約定時間進行房屋檢查
4. **押金退還**：確認房屋狀況良好後，7個工作天內退還押金

## 注意事項
- 需提前30天通知
- 需繳清所有費用
- 房屋需恢復原狀""",
                "similarity": 0.89
            }
        ]

        intent_info = {
            "intent_name": "退租流程",
            "intent_type": "knowledge",
            "keywords": ["退租", "辦理"]
        }

        # 測試優化
        print("🔄 開始優化答案...")
        result = optimizer.optimize_answer(
            question="請問如何辦理退租手續？",
            search_results=search_results,
            confidence_level="high",
            intent_info=intent_info
        )

        print(f"\n✅ 優化完成")
        print(f"使用優化：{result['optimization_applied']}")
        print(f"Token 使用：{result['tokens_used']}")
        print(f"處理時間：{result['processing_time_ms']}ms")
        print(f"\n{'='*60}")
        print("原始答案：")
        print(result['original_answer'][:200] + "...")
        print(f"\n{'='*60}")
        print("優化後答案：")
        print(result['optimized_answer'])
        print(f"{'='*60}")

    # 執行測試
    asyncio.run(test_optimizer())
