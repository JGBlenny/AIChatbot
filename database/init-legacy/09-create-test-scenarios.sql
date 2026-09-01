-- ========================================
-- 測試題庫與回測系統資料表
-- ========================================

-- ========================================
-- 1. 測試集合表（Test Collections）
-- ========================================
CREATE TABLE IF NOT EXISTS test_collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,

    -- 集合屬性
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,

    -- 統計資訊
    total_scenarios INTEGER DEFAULT 0,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

-- 預設測試集合
INSERT INTO test_collections (name, display_name, description, is_default) VALUES
    ('smoke', 'Smoke 測試', '快速煙霧測試，包含核心功能測試案例', false),
    ('full', 'Full 測試', '完整測試套件，涵蓋所有功能領域', true),
    ('regression', 'Regression 測試', '回歸測試，確保更新不破壞現有功能', false),
    ('edge_cases', 'Edge Cases', '邊界情況與異常測試', false);

-- ========================================
-- 2. 測試情境表（Test Scenarios）
-- ========================================
CREATE TABLE IF NOT EXISTS test_scenarios (
    id SERIAL PRIMARY KEY,

    -- 所屬集合（可以屬於多個集合）
    collection_id INTEGER REFERENCES test_collections(id) ON DELETE CASCADE,

    -- 測試內容
    test_question TEXT NOT NULL,
    expected_category VARCHAR(100),  -- 預期意圖分類
    expected_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL,  -- 關聯意圖表
    expected_keywords TEXT[],  -- 預期包含的關鍵字

    -- 測試屬性
    difficulty VARCHAR(20) DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard')),
    tags TEXT[],  -- 標籤：['帳務', '退租', '維修'] 等
    priority INTEGER DEFAULT 50 CHECK (priority BETWEEN 1 AND 100),  -- 優先級 1-100

    -- 預期結果
    expected_min_confidence FLOAT DEFAULT 0.6,  -- 預期最低信心度
    expected_source_count INTEGER,  -- 預期知識來源數量
    expected_answer TEXT,  -- 標準答案（可選）用於 LLM 語義對比
    min_quality_score DECIMAL(2,1) DEFAULT 3.0 CHECK (min_quality_score >= 1.0 AND min_quality_score <= 5.0),  -- 最低質量要求

    -- 狀態管理
    status VARCHAR(20) DEFAULT 'pending_review' CHECK (status IN ('pending_review', 'approved', 'rejected', 'draft')),
    is_active BOOLEAN DEFAULT true,

    -- 來源追蹤
    source VARCHAR(50) DEFAULT 'manual' CHECK (source IN ('manual', 'user_question', 'auto_generated', 'imported')),
    source_question_id INTEGER,  -- 如果來自 unclear_questions，記錄來源 ID

    -- 備註與說明
    notes TEXT,
    test_purpose TEXT,  -- 測試目的

    -- 關聯知識
    related_knowledge_ids INTEGER[],  -- 相關知識 ID 列表

    -- 統計資訊
    total_runs INTEGER DEFAULT 0,  -- 執行次數
    pass_count INTEGER DEFAULT 0,  -- 通過次數
    fail_count INTEGER DEFAULT 0,  -- 失敗次數
    avg_score FLOAT,  -- 平均分數
    last_run_at TIMESTAMP,
    last_result VARCHAR(20),  -- 'passed', 'failed', 'error'

    -- 審核資訊
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

-- ========================================
-- 3. 回測執行記錄表（Backtest Runs）
-- ========================================
CREATE TABLE IF NOT EXISTS backtest_runs (
    id SERIAL PRIMARY KEY,

    -- 執行配置
    collection_id INTEGER REFERENCES test_collections(id) ON DELETE SET NULL,
    quality_mode VARCHAR(20) DEFAULT 'basic' CHECK (quality_mode IN ('basic', 'hybrid', 'detailed')),
    test_type VARCHAR(20) DEFAULT 'smoke' CHECK (test_type IN ('smoke', 'full', 'custom')),

    -- 執行範圍
    total_scenarios INTEGER,
    executed_scenarios INTEGER DEFAULT 0,

    -- 執行狀態
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- 環境資訊
    rag_api_url VARCHAR(255),
    vendor_id INTEGER,

    -- 執行結果統計
    passed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    pass_rate FLOAT,
    avg_score FLOAT,
    avg_confidence FLOAT,

    -- 品質評估統計（如果啟用）
    avg_relevance FLOAT,
    avg_completeness FLOAT,
    avg_accuracy FLOAT,
    avg_intent_match FLOAT,
    avg_quality_overall FLOAT,
    ndcg_score FLOAT,  -- NDCG@3 排序品質

    -- 執行時間
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- 結果輸出
    output_file_path TEXT,
    summary_file_path TEXT,

    -- 備註
    notes TEXT,
    error_message TEXT,

    -- 執行者
    executed_by VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 4. 回測結果詳細表（Backtest Results）
-- ========================================
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,

    -- 關聯回測執行
    run_id INTEGER REFERENCES backtest_runs(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES test_scenarios(id) ON DELETE CASCADE,

    -- 測試資訊
    test_question TEXT NOT NULL,
    expected_category VARCHAR(100),

    -- 系統回應
    actual_intent VARCHAR(100),
    all_intents TEXT[],  -- 所有相關意圖
    system_answer TEXT,
    confidence FLOAT,

    -- 評分
    score FLOAT,  -- 基礎評分
    overall_score FLOAT,  -- 混合評分（如果使用 hybrid/detailed）
    passed BOOLEAN,

    -- 基礎評估詳情
    category_match BOOLEAN,
    keyword_coverage FLOAT,

    -- LLM 品質評估（如果啟用）
    relevance INTEGER,  -- 1-5
    completeness INTEGER,  -- 1-5
    accuracy INTEGER,  -- 1-5
    intent_match INTEGER,  -- 1-5
    quality_overall INTEGER,  -- 1-5
    quality_reasoning TEXT,

    -- 知識來源
    source_ids TEXT,  -- 逗號分隔的 ID
    source_count INTEGER,
    knowledge_sources TEXT,  -- 來源摘要

    -- 優化建議
    optimization_tips TEXT,

    -- 回測時間
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 元數據
    evaluation JSONB,  -- 完整評估數據
    response_metadata JSONB  -- 完整回應數據
);

-- ========================================
-- 5. 測試情境與集合的多對多關聯表
-- ========================================
CREATE TABLE IF NOT EXISTS test_scenario_collections (
    scenario_id INTEGER REFERENCES test_scenarios(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES test_collections(id) ON DELETE CASCADE,

    -- 在該集合中的順序
    display_order INTEGER DEFAULT 0,

    -- 是否在該集合中啟用
    is_enabled BOOLEAN DEFAULT true,

    -- 時間戳記
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by VARCHAR(100),

    PRIMARY KEY (scenario_id, collection_id)
);

-- ========================================
-- 索引優化
-- ========================================

-- test_collections 索引
CREATE INDEX IF NOT EXISTS idx_test_collections_active ON test_collections(is_active);
CREATE INDEX IF NOT EXISTS idx_test_collections_default ON test_collections(is_default);

-- test_scenarios 索引
CREATE INDEX IF NOT EXISTS idx_test_scenarios_collection ON test_scenarios(collection_id);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_status ON test_scenarios(status);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_active ON test_scenarios(is_active);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_difficulty ON test_scenarios(difficulty);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_intent ON test_scenarios(expected_intent_id);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_tags ON test_scenarios USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_priority ON test_scenarios(priority DESC);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_last_result ON test_scenarios(last_result);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_source ON test_scenarios(source);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_source_question ON test_scenarios(source_question_id);

-- backtest_runs 索引
CREATE INDEX IF NOT EXISTS idx_backtest_runs_status ON backtest_runs(status);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_collection ON backtest_runs(collection_id);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_started ON backtest_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_quality_mode ON backtest_runs(quality_mode);

-- backtest_results 索引
CREATE INDEX IF NOT EXISTS idx_backtest_results_run ON backtest_results(run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_results_scenario ON backtest_results(scenario_id);
CREATE INDEX IF NOT EXISTS idx_backtest_results_passed ON backtest_results(passed);
CREATE INDEX IF NOT EXISTS idx_backtest_results_tested_at ON backtest_results(tested_at DESC);

-- test_scenario_collections 索引
CREATE INDEX IF NOT EXISTS idx_scenario_collections_scenario ON test_scenario_collections(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_collections_collection ON test_scenario_collections(collection_id);
CREATE INDEX IF NOT EXISTS idx_scenario_collections_enabled ON test_scenario_collections(is_enabled);

-- ========================================
-- 觸發器：自動更新統計資訊
-- ========================================

-- 更新 test_collections 的 total_scenarios
CREATE OR REPLACE FUNCTION update_collection_scenario_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE test_collections
    SET total_scenarios = (
        SELECT COUNT(DISTINCT scenario_id)
        FROM test_scenario_collections
        WHERE collection_id = COALESCE(NEW.collection_id, OLD.collection_id)
        AND is_enabled = true
    )
    WHERE id = COALESCE(NEW.collection_id, OLD.collection_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_collection_count_insert
    AFTER INSERT ON test_scenario_collections
    FOR EACH ROW
    EXECUTE FUNCTION update_collection_scenario_count();

CREATE TRIGGER trigger_update_collection_count_update
    AFTER UPDATE ON test_scenario_collections
    FOR EACH ROW
    EXECUTE FUNCTION update_collection_scenario_count();

CREATE TRIGGER trigger_update_collection_count_delete
    AFTER DELETE ON test_scenario_collections
    FOR EACH ROW
    EXECUTE FUNCTION update_collection_scenario_count();

-- 更新 test_scenarios 的 updated_at
CREATE TRIGGER update_test_scenarios_updated_at
    BEFORE UPDATE ON test_scenarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_collections_updated_at
    BEFORE UPDATE ON test_collections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 更新測試情境統計（從回測結果）
CREATE OR REPLACE FUNCTION update_scenario_statistics()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE test_scenarios
    SET
        total_runs = total_runs + 1,
        pass_count = pass_count + CASE WHEN NEW.passed THEN 1 ELSE 0 END,
        fail_count = fail_count + CASE WHEN NOT NEW.passed THEN 1 ELSE 0 END,
        avg_score = (
            SELECT AVG(score)
            FROM backtest_results
            WHERE scenario_id = NEW.scenario_id
        ),
        last_run_at = NEW.tested_at,
        last_result = CASE WHEN NEW.passed THEN 'passed' ELSE 'failed' END
    WHERE id = NEW.scenario_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_scenario_stats
    AFTER INSERT ON backtest_results
    FOR EACH ROW
    EXECUTE FUNCTION update_scenario_statistics();

-- ========================================
-- 輔助函數：從用戶問題創建測試情境
-- ========================================

-- 從 unclear_questions 創建測試情境（待審核）
CREATE OR REPLACE FUNCTION create_test_scenario_from_unclear_question(
    p_unclear_question_id INTEGER,
    p_expected_category VARCHAR(100) DEFAULT NULL,
    p_difficulty VARCHAR(20) DEFAULT 'medium',
    p_created_by VARCHAR(100) DEFAULT 'system'
) RETURNS INTEGER AS $$
DECLARE
    v_scenario_id INTEGER;
    v_question TEXT;
    v_intent_type VARCHAR(50);
BEGIN
    -- 獲取 unclear_question 詳情
    SELECT question, intent_type
    INTO v_question, v_intent_type
    FROM unclear_questions
    WHERE id = p_unclear_question_id;

    IF v_question IS NULL THEN
        RAISE EXCEPTION 'Unclear question not found: %', p_unclear_question_id;
    END IF;

    -- 創建測試情境（待審核狀態）
    INSERT INTO test_scenarios (
        test_question,
        expected_category,
        difficulty,
        status,
        source,
        source_question_id,
        created_by,
        notes
    ) VALUES (
        v_question,
        COALESCE(p_expected_category, v_intent_type),
        p_difficulty,
        'pending_review',  -- 待審核
        'user_question',  -- 來源：用戶問題
        p_unclear_question_id,
        p_created_by,
        FORMAT('從用戶問題 #%s 創建，問題被問 %s 次',
            p_unclear_question_id,
            (SELECT frequency FROM unclear_questions WHERE id = p_unclear_question_id))
    )
    RETURNING id INTO v_scenario_id;

    -- 更新 unclear_questions 的處理狀態
    UPDATE unclear_questions
    SET
        status = 'in_progress',
        resolution_note = FORMAT('已創建測試情境 #%s，待審核', v_scenario_id),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_unclear_question_id;

    RETURN v_scenario_id;
END;
$$ LANGUAGE plpgsql;

-- 審核測試情境（批准或拒絕）
CREATE OR REPLACE FUNCTION review_test_scenario(
    p_scenario_id INTEGER,
    p_action VARCHAR(20),  -- 'approve' or 'reject'
    p_reviewer VARCHAR(100),
    p_notes TEXT DEFAULT NULL,
    p_add_to_collection VARCHAR(100) DEFAULT NULL  -- 可選：批准時加入指定集合
) RETURNS BOOLEAN AS $$
DECLARE
    v_collection_id INTEGER;
    v_new_status VARCHAR(20);
BEGIN
    -- 驗證動作
    IF p_action NOT IN ('approve', 'reject') THEN
        RAISE EXCEPTION 'Invalid action: %. Must be approve or reject', p_action;
    END IF;

    -- 設定新狀態
    v_new_status := CASE
        WHEN p_action = 'approve' THEN 'approved'
        WHEN p_action = 'reject' THEN 'rejected'
    END;

    -- 更新測試情境
    UPDATE test_scenarios
    SET
        status = v_new_status,
        reviewed_by = p_reviewer,
        reviewed_at = CURRENT_TIMESTAMP,
        review_notes = p_notes,
        is_active = CASE WHEN p_action = 'approve' THEN true ELSE false END
    WHERE id = p_scenario_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Test scenario not found: %', p_scenario_id;
    END IF;

    -- 如果批准且指定了集合，加入該集合
    IF p_action = 'approve' AND p_add_to_collection IS NOT NULL THEN
        SELECT id INTO v_collection_id
        FROM test_collections
        WHERE name = p_add_to_collection;

        IF v_collection_id IS NOT NULL THEN
            INSERT INTO test_scenario_collections (scenario_id, collection_id, added_by)
            VALUES (p_scenario_id, v_collection_id, p_reviewer)
            ON CONFLICT (scenario_id, collection_id) DO NOTHING;
        END IF;
    END IF;

    -- 如果來源是用戶問題，更新 unclear_questions 狀態
    UPDATE unclear_questions
    SET
        status = CASE
            WHEN p_action = 'approve' THEN 'resolved'
            WHEN p_action = 'reject' THEN 'ignored'
        END,
        resolved_at = CURRENT_TIMESTAMP,
        resolution_note = FORMAT('測試情境 #%s %s',
            p_scenario_id,
            CASE WHEN p_action = 'approve' THEN '已批准' ELSE '已拒絕' END),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = (SELECT source_question_id FROM test_scenarios WHERE id = p_scenario_id)
      AND status != 'resolved';

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- 視圖：方便查詢
-- ========================================

-- 測試集合摘要視圖
CREATE OR REPLACE VIEW v_test_collection_summary AS
SELECT
    tc.id,
    tc.name,
    tc.display_name,
    tc.description,
    tc.is_active,
    tc.is_default,
    COUNT(DISTINCT tsc.scenario_id) as scenario_count,
    COUNT(DISTINCT CASE WHEN ts.is_active THEN tsc.scenario_id END) as active_scenario_count,
    tc.created_at,
    tc.updated_at
FROM test_collections tc
LEFT JOIN test_scenario_collections tsc ON tc.id = tsc.collection_id
LEFT JOIN test_scenarios ts ON tsc.scenario_id = ts.id
GROUP BY tc.id;

-- 測試情境詳情視圖
CREATE OR REPLACE VIEW v_test_scenario_details AS
SELECT
    ts.id,
    ts.test_question,
    ts.expected_category,
    i.name as expected_intent_name,
    ts.difficulty,
    ts.tags,
    ts.priority,
    ts.status,
    ts.is_active,
    ts.source,
    ts.total_runs,
    ts.pass_count,
    ts.fail_count,
    CASE
        WHEN ts.total_runs > 0 THEN ROUND((ts.pass_count::numeric / ts.total_runs::numeric * 100), 2)
        ELSE NULL
    END as pass_rate,
    ts.avg_score,
    ts.last_run_at,
    ts.last_result,
    ARRAY_AGG(DISTINCT tc.name) FILTER (WHERE tc.name IS NOT NULL) as collections,
    ts.created_at,
    ts.created_by
FROM test_scenarios ts
LEFT JOIN intents i ON ts.expected_intent_id = i.id
LEFT JOIN test_scenario_collections tsc ON ts.id = tsc.scenario_id
LEFT JOIN test_collections tc ON tsc.collection_id = tc.id
GROUP BY ts.id, i.name;

-- 回測執行摘要視圖
CREATE OR REPLACE VIEW v_backtest_run_summary AS
SELECT
    br.id,
    tc.display_name as collection_name,
    br.quality_mode,
    br.test_type,
    br.status,
    br.total_scenarios,
    br.executed_scenarios,
    br.passed_count,
    br.failed_count,
    br.pass_rate,
    br.avg_score,
    br.avg_confidence,
    br.avg_quality_overall,
    br.started_at,
    br.completed_at,
    br.duration_seconds,
    br.executed_by
FROM backtest_runs br
LEFT JOIN test_collections tc ON br.collection_id = tc.id
ORDER BY br.started_at DESC;

-- 待審核測試情境視圖
CREATE OR REPLACE VIEW v_pending_test_scenarios AS
SELECT
    ts.id,
    ts.test_question,
    ts.expected_category,
    ts.difficulty,
    ts.status,
    ts.source,
    ts.source_question_id,
    CASE
        WHEN ts.source_question_id IS NOT NULL THEN (
            SELECT uq.frequency
            FROM unclear_questions uq
            WHERE uq.id = ts.source_question_id
        )
        ELSE NULL
    END as question_frequency,
    CASE
        WHEN ts.source_question_id IS NOT NULL THEN (
            SELECT uq.first_asked_at
            FROM unclear_questions uq
            WHERE uq.id = ts.source_question_id
        )
        ELSE NULL
    END as first_asked_at,
    ts.notes,
    ts.created_at,
    ts.created_by
FROM test_scenarios ts
WHERE ts.status = 'pending_review'
ORDER BY ts.created_at DESC;

-- 用戶問題轉測試情境候選視圖
CREATE OR REPLACE VIEW v_unclear_question_candidates AS
SELECT
    uq.id as unclear_question_id,
    uq.question,
    uq.intent_type,
    uq.frequency,
    uq.first_asked_at,
    uq.last_asked_at,
    uq.status as unclear_status,
    ts.id as existing_scenario_id,
    ts.status as scenario_status,
    CASE
        WHEN ts.id IS NULL THEN true
        ELSE false
    END as can_create_scenario,
    uq.similarity_score,
    uq.retrieved_docs
FROM unclear_questions uq
LEFT JOIN test_scenarios ts ON ts.source_question_id = uq.id
WHERE uq.status IN ('pending', 'in_progress')
  AND uq.frequency >= 2  -- 至少被問過2次
ORDER BY uq.frequency DESC, uq.last_asked_at DESC;

-- ========================================
-- 註解說明
-- ========================================

COMMENT ON TABLE test_collections IS '測試集合：組織和管理不同測試套件（smoke、full、regression等）';
COMMENT ON TABLE test_scenarios IS '測試情境：儲存所有測試問題及預期結果';
COMMENT ON TABLE backtest_runs IS '回測執行記錄：追蹤每次回測的執行狀態和結果';
COMMENT ON TABLE backtest_results IS '回測結果詳細：儲存每個測試案例的執行結果';
COMMENT ON TABLE test_scenario_collections IS '測試情境與集合關聯：支援一個測試屬於多個集合';

COMMENT ON COLUMN test_scenarios.priority IS '優先級 1-100，數字越大優先級越高';
COMMENT ON COLUMN test_scenarios.expected_min_confidence IS '預期最低信心度，用於判斷測試是否通過';
COMMENT ON COLUMN backtest_runs.quality_mode IS '品質評估模式：basic（快速）、hybrid（混合）、detailed（深度）';
COMMENT ON COLUMN backtest_runs.ndcg_score IS 'NDCG@3 排序品質評分，衡量檢索結果排序的優劣';
COMMENT ON COLUMN test_scenarios.status IS '狀態：pending_review（待審核）、approved（已批准）、rejected（已拒絕）、draft（草稿）';
COMMENT ON COLUMN test_scenarios.source IS '來源：manual（手動）、user_question（用戶問題）、auto_generated（自動生成）、imported（匯入）';
COMMENT ON COLUMN test_scenarios.source_question_id IS '如果來自 unclear_questions，記錄來源問題 ID';

COMMENT ON FUNCTION create_test_scenario_from_unclear_question IS '從 unclear_questions 表創建測試情境（待審核狀態）';
COMMENT ON FUNCTION review_test_scenario IS '審核測試情境（批准或拒絕），可選擇加入指定集合';

COMMENT ON VIEW v_pending_test_scenarios IS '待審核測試情境列表，包含來源資訊';
COMMENT ON VIEW v_unclear_question_candidates IS '用戶問題轉測試情境候選列表（頻率>=2且未創建）';

-- ========================================
-- 初始化成功訊息
-- ========================================
DO $$
BEGIN
    RAISE NOTICE '✅ 測試題庫與回測系統資料表建立完成';
    RAISE NOTICE '   📦 Tables:';
    RAISE NOTICE '      - test_collections: 測試集合管理';
    RAISE NOTICE '      - test_scenarios: 測試情境儲存';
    RAISE NOTICE '      - backtest_runs: 回測執行記錄';
    RAISE NOTICE '      - backtest_results: 回測結果詳細';
    RAISE NOTICE '      - test_scenario_collections: 多對多關聯';
    RAISE NOTICE '   📊 Views:';
    RAISE NOTICE '      - v_test_collection_summary: 集合摘要';
    RAISE NOTICE '      - v_test_scenario_details: 情境詳情';
    RAISE NOTICE '      - v_backtest_run_summary: 執行摘要';
    RAISE NOTICE '      - v_pending_test_scenarios: 待審核情境';
    RAISE NOTICE '      - v_unclear_question_candidates: 用戶問題候選';
    RAISE NOTICE '   ⚙️  Functions:';
    RAISE NOTICE '      - create_test_scenario_from_unclear_question(): 從用戶問題創建測試情境';
    RAISE NOTICE '      - review_test_scenario(): 審核測試情境（批准/拒絕）';
    RAISE NOTICE '   🎯 預設集合: smoke, full, regression, edge_cases';
    RAISE NOTICE '   📝 狀態流程: pending_review → approved/rejected';
    RAISE NOTICE '   📥 來源追蹤: manual, user_question, auto_generated, imported';
END $$;

-- ========================================
-- 擴展 test_scenarios 表：AI 知識生成追蹤
-- ========================================

ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS has_knowledge BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS linked_knowledge_ids INTEGER[],
ADD COLUMN IF NOT EXISTS knowledge_generation_requested BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS knowledge_generation_requested_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS question_embedding vector(1536);

COMMENT ON COLUMN test_scenarios.has_knowledge IS '是否已有對應的知識庫內容';
COMMENT ON COLUMN test_scenarios.linked_knowledge_ids IS '關聯的知識 ID 陣列';
COMMENT ON COLUMN test_scenarios.knowledge_generation_requested IS '是否已請求 AI 生成知識';
COMMENT ON COLUMN test_scenarios.knowledge_generation_requested_at IS 'AI 生成請求時間';
COMMENT ON COLUMN test_scenarios.question_embedding IS '問題的向量表示（用於相似度搜尋）';

-- 為 question_embedding 建立索引
-- ⚠️ 2026-09-01：原為 IVFFlat `lists=100`。實測該參數在小資料量下**靜默漏召回**
--    （knowledge_base 992 筆向量 ⇒ 每 list 約 10 筆、probes 預設 1 且全 repo 從未設定
--     ⇒ top-20 候選池召回率 31%、top-1 與精確掃描不同 46%，且**不會報錯**）。
--    改用 HNSW：⛔ 沒有 lists／probes 可以配錯，召回率不隨資料量崩塌。
--    證據 .kiro/specs/conversational-routing-execution/ivfflat-index-defect.md
CREATE INDEX IF NOT EXISTS idx_test_scenarios_embedding
ON test_scenarios
USING hnsw (question_embedding vector_cosine_ops);

-- ========================================
-- 擴展 knowledge_base 表：標註知識來源
-- ========================================

ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS source_test_scenario_id INTEGER,
ADD COLUMN IF NOT EXISTS generation_metadata JSONB,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

COMMENT ON COLUMN knowledge_base.source_type IS '知識來源類型: manual (人工), ai_generated (AI生成), imported (匯入), ai_assisted (AI輔助)';
COMMENT ON COLUMN knowledge_base.source_test_scenario_id IS '來源測試情境 ID（如果由測試情境生成）';
COMMENT ON COLUMN knowledge_base.generation_metadata IS 'AI 生成的詳細資訊: {model, prompt, confidence, reviewed_by, edited}';
COMMENT ON COLUMN knowledge_base.is_active IS '知識是否啟用';

-- ========================================
-- 為 knowledge_base 添加外鍵約束
-- ========================================

-- 添加 source_test_scenario_id 外鍵約束
ALTER TABLE knowledge_base
ADD CONSTRAINT IF NOT EXISTS fk_knowledge_source_test_scenario
FOREIGN KEY (source_test_scenario_id)
REFERENCES test_scenarios(id)
ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_kb_source_test_scenario ON knowledge_base(source_test_scenario_id);
CREATE INDEX IF NOT EXISTS idx_kb_source_type ON knowledge_base(source_type);
CREATE INDEX IF NOT EXISTS idx_kb_is_active ON knowledge_base(is_active);
