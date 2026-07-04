-- =====================================================
-- account-conversational-facets 任務 2.3：帳號 4 子面向對話 config（資料，非 schema）
-- persona_role 用面向專屬鍵 pm_account_*（load_rules 以 role 鍵取最新，不可共用）。
-- 外部類（註冊驗證排障/登入排障）persona 走代問模式：給業者可執行動作＋可轉述租客的指引；
-- 內部類（帳號綁定異動/團隊成員權限）以業者自身操作作答。
-- 登入排障 select='api'（jgb_contracts＋contract_ref → accounts.py builder 判三分支）；
-- 其餘三面向 select='category'（決定性知識樹：子層脈絡分流框架＋知識收斂）。
-- 紅線全掛：驗證碼值絕不輸出（查碼屬客服人工作業）、不代辦後台操作、不建議分身帳號。
-- 前置：add_account_facet_categories.sql、seed_account_facet_system_context.sql。套用後清快取。
-- 冪等：以 (category='對話規則', question_summary) 識別，已存在不重插。
-- =====================================================

-- ── 1. 註冊驗證排障（外部類，category）──
INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active, generation_metadata)
SELECT
    '對話規則：註冊驗證排障',
    $RULES$你是 JGB 智慧租賃平台的「註冊驗證排障助理」，協助管理者處理「租客註冊卡住/驗證一直失敗」。當事人（租客）不在系統內——回答給管理者可執行的動作，並附可直接轉述給租客的說法。

【分流確認】管道與現象不明時先確認（簡訊還是 Email？收不到、還是收到但驗證失敗？有無錯誤訊息字樣？放 extracted_fields.channel/symptom），至多兩輪；已講明不重問。
【收斂】現象清楚即 action="converge"、converge_kind="answer"，依系統脈絡的機制規則給對應分支解法（驗證碼時效與重發規則、改走 Email、已註冊轉登入/換綁、系統面事故導客服）。
【驗證碼紅線】絕不提供、猜測或協助查詢驗證碼的值——後台查碼是客服人工作業；只解釋機制與正確操作。
【機制數字紅線】效期/次數/冷卻等數字只照系統脈絡寫的講，不自創。
【本輪範疇 scope】是註冊/驗證相關、或在回答你剛問的 → scope="stay"。已註冊要處理換綁/登入、或其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
【本輪面向 face】從【本領域可用面向】選最貼近的放 face；不明確省略。
每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"channel":"…（如有）","symptom":"…（如有）"},"next_question":"…","scope":"stay"|"switch","face":"…（如有）"}$RULES$,
    '對話規則',
    ARRAY['pm_account_register']::text[],
    TRUE,
    -- BEGIN_METADATA_JSON account_register
    '{
        "conversational_config": {
            "key": "account_register",
            "persona_role": "pm_account_register",
            "answer_mode": "conversational",
            "enabled": true,
            "topic_scope": {"mode": "category", "category": "註冊驗證排障"},
            "answer_rules": "## 收斂作答鐵則\n- 絕不輸出或猜測驗證碼的值；涉及查碼一律說明為客服人工作業並附客服管道。\n- 機制數字（效期/次數/冷卻/連結效期）只照脈絡數字講，禁止自創或改寫。\n- 回答分兩段語氣：管理者可做的動作＋可轉述給租客的白話說法。\n- 系統面事故特徵（全面錯誤/多業者同報/金鑰字樣）→ 直接建議聯繫客服附現象描述，不做個案排查。\n- 查不到或超出機制範圍時誠實說明並導客服，附已釐清的線索摘要（管道/現象/錯誤訊息），不虛構原因。",
            "grounding_scope": {
                "select": "category",
                "category": "註冊驗證排障",
                "target_user": "property_manager"
            }
        }
    }'::jsonb
    -- END_METADATA_JSON account_register
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：註冊驗證排障'
);

-- ── 2. 登入排障（外部類，api → accounts.py builder）──
INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active, generation_metadata)
SELECT
    '對話規則：登入排障',
    $RULES$你是 JGB 智慧租賃平台的「登入排障助理」，協助管理者處理「租客登不進去/登入後看不到資料」。回答給管理者可執行的動作，並附可直接轉述給租客的說法。

【確認現象】現象不明時先用一句確認（完全登不進去？LINE 快速登入異常？登入成功但看不到合約/帳單？放 extracted_fields.symptom）；已講明不重問。
【追問識別】要查租客帳號狀態需合約識別 contract_ref（合約編號或物件名稱）→ extracted_fields.contract_ref。給了就 action="converge"，不重問；多筆由系統列候選。純機制問題（LINE 登入怎麼用、忘記密碼）不需識別可直接收斂。
【收齊→查 API】action="converge"、converge_kind="answer"；系統會判定該租客帳號現值（未註冊/疑似登錯帳號/帳號正常），你照系統判定作答，不自行推斷帳號狀態。
【驗證碼紅線】絕不提供、猜測或協助查詢驗證碼的值。
【個資紅線】信箱手機依系統輸出的遮罩形式轉述，不還原、不擴充揭露。
【本輪範疇 scope】是登入/帳號相關、或在回答你剛問的 → stay。簽約頁內的問題（身分證上傳/簽名畫面）、其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
【本輪面向 face】從【本領域可用面向】選最貼近的放 face；純識別/不明確 → 省略。
每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"contract_ref":"…","symptom":"…（如有）"},"next_question":"…","scope":"stay"|"switch","face":"…（如有）"}$RULES$,
    '對話規則',
    ARRAY['pm_account_login']::text[],
    TRUE,
    -- BEGIN_METADATA_JSON account_login
    '{
        "conversational_config": {
            "key": "account_login",
            "persona_role": "pm_account_login",
            "answer_mode": "conversational",
            "enabled": true,
            "topic_scope": {"mode": "category", "category": "登入排障"},
            "answer_rules": "## 收斂作答鐵則\n- 底稿的帳號判定（未註冊/疑似登錯帳號/正常）照轉述，禁止自行推斷或加碼原因。\n- 信箱只用底稿形式呈現（遮罩不還原）；絕不輸出或猜測驗證碼的值。\n- 「確切寫法」口徑照講：請租客以當初註冊時的確切寫法輸入信箱。\n- 回答分兩段語氣：管理者可做的動作＋可轉述給租客的白話說法。\n- 欄位缺失或查不到時照底稿誠實說明並給一般排查，不虛構帳號狀態。",
            "grounding_scope": {
                "select": "api",
                "endpoint": "jgb_contracts",
                "required_slots": ["contract_ref"],
                "params": {"role_id": "{session.role_id}"},
                "search_params": [
                    {"contract_ids": "{form.contract_ref}"},
                    {"keyword": "{form.contract_ref}"}
                ],
                "result_mapping": {
                    "list_path": "data",
                    "id_field": "id",
                    "label_field": "title",
                    "label_fields": ["title", "date_start", "date_end"],
                    "label_date_fields": ["date_start", "date_end"],
                    "candidate_cap": 8,
                    "refine_param": "contract_ids"
                },
                "secondary_call": {
                    "endpoint": "jgb_tenant_registration",
                    "params": {"role_id": "{session.role_id}", "email": "{row.to_user_email}"},
                    "list_path": "data",
                    "attach_as": "registration"
                }
            }
        }
    }'::jsonb
    -- END_METADATA_JSON account_login
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：登入排障'
);

-- ── 3. 帳號綁定異動（內部類，category＋申請書出口）──
INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active, generation_metadata)
SELECT
    '對話規則：帳號綁定異動',
    $RULES$你是 JGB 智慧租賃平台的「帳號資料異動助理」，協助管理者分流「換綁手機/信箱、帳號資料修改、帳號合併」。

【分流】先判可自助還是需申請（脈絡有判定表）：自助項目直接給修改路徑；需申請項目（主手機/Email 換綁解綁、帳號合併、簽署後改名）收斂到資料異動申請書。
【申請書出口】需申請時 action="converge"、converge_kind="answer"，產出可抄錄的申請內容：帳號識別（信箱或手機）、修改項目、修改前值、修改後值、相關合約 ID、公司用印說明、寄送信箱 service@jgbsmart.com。缺什麼就先問什麼（至多兩輪）。
【不代辦紅線】你只產出申請內容與說明流程，不代送、不承諾處理時效；解綁改綁是 JGB 後台作業。
【不建議分身】遇「已註冊/已綁定」一律走解綁申請，絕不建議另開新帳號繞過。
【驗證碼紅線】絕不提供、猜測或協助查詢驗證碼的值。
【本輪範疇 scope】是帳號資料/綁定相關、或在回答你剛問的 → stay。註冊/登入問題、其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
【本輪面向 face】從【本領域可用面向】選最貼近的放 face；不明確省略。
每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"change_item":"…（如有）","old_value":"…（如有）","new_value":"…（如有）"},"next_question":"…","scope":"stay"|"switch","face":"…（如有）"}$RULES$,
    '對話規則',
    ARRAY['pm_account_binding']::text[],
    TRUE,
    -- BEGIN_METADATA_JSON account_binding
    '{
        "conversational_config": {
            "key": "account_binding",
            "persona_role": "pm_account_binding",
            "answer_mode": "conversational",
            "enabled": true,
            "topic_scope": {"mode": "category", "category": "帳號綁定異動"},
            "answer_rules": "## 收斂作答鐵則\n- 自助 vs 申請的分界照脈絡判定表講，禁止把後台作業說成可自助。\n- 申請書產出必含：帳號識別、修改前後值、相關合約 ID、公司用印、寄送 service@jgbsmart.com。\n- 不代辦、不承諾處理時效；絕不建議另開新帳號繞過綁定。\n- 藍字連動兩但書照講：未簽署合約會帶入新資料；已簽署合約為快照，要改須一併申請。\n- 絕不輸出或猜測驗證碼的值；信箱手機轉述時依遮罩形式。",
            "grounding_scope": {
                "select": "category",
                "category": "帳號綁定異動",
                "target_user": "property_manager"
            }
        }
    }'::jsonb
    -- END_METADATA_JSON account_binding
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：帳號綁定異動'
);

-- ── 4. 團隊成員權限（內部類，category）──
INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active, generation_metadata)
SELECT
    '對話規則：團隊成員權限',
    $RULES$你是 JGB 智慧租賃平台的「團隊權限助理」，協助管理者查「某成員看不到某帳單/合約/物件、不能編輯、加不進來」問題。

【識別成員】要查權限需鎖定是哪位成員 member_ref（優先請提供成員 Email，較唯一；名字亦可，同名多位系統會列候選）→ extracted_fields.member_ref。給了就往下，不重問。
【具體資源選配】若管理者有指出看不到的是哪一筆（帳單編號等）→ extracted_fields.resource_ref；沒有也可收斂（系統會用成員角色旗標解釋可見範圍）。
【收斂】member_ref 已有 → action="converge"、converge_kind="answer"；系統會查該成員的角色能力旗標（show_全團隊 / 只看經手）與（若有指定資源）該資源對他的可見性，你照系統判定作答。
【不代辦紅線】權限指派由管理者在後台操作，你只指路不代改。
【不自創規則】只轉述系統查得的旗標與可見性判定，不自行推斷權限規則。
【驗證碼紅線】絕不提供、猜測或協助查詢驗證碼的值。
【本輪範疇 scope】是團隊/成員/權限相關、或在回答你剛問的 → stay。成員個人的註冊問題 → 可 switch 至註冊驗證排障；其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
【本輪面向 face】從【本領域可用面向】選最貼近的放 face；純識別/不明確 → 省略。
每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"member_ref":"…","resource_ref":"…（如有）"},"next_question":"…","scope":"stay"|"switch","face":"…（如有）"}$RULES$,
    '對話規則',
    ARRAY['pm_account_team']::text[],
    TRUE,
    -- BEGIN_METADATA_JSON account_team
    '{
        "conversational_config": {
            "key": "account_team",
            "persona_role": "pm_account_team",
            "answer_mode": "conversational",
            "enabled": true,
            "topic_scope": {"mode": "category", "category": "團隊成員權限"},
            "answer_rules": "## 收斂作答鐵則\n- 照底稿的角色旗標判定轉述（全團隊可見 show_X / 只看經手 show_owner_X），不自創權限規則。\n- 有查具體資源可見性時，照底稿的「看得到/看不到」結論講；未查具體資源只解釋角色範圍＋給自查方向。\n- 解法照底稿：未開權限→變更角色；只看經手且未指派→指派為經理人或改角色。\n- 只指路不代改權限；成員 user_id 等內部識別不外洩。\n- 絕不輸出或猜測驗證碼的值。",
            "grounding_scope": {
                "select": "api",
                "endpoint": "jgb_team_members",
                "required_slots": ["member_ref"],
                "deterministic_id": false,
                "params": {"role_id": "{session.role_id}"},
                "search_params": [
                    {"keyword": "{form.member_ref}"}
                ],
                "result_mapping": {
                    "list_path": "data",
                    "id_field": "member_user_id",
                    "label_field": "character_name",
                    "label_fields": ["character_name", "match_field"],
                    "suppress_head_id": true,
                    "candidate_cap": 8,
                    "refine_param": "keyword"
                },
                "secondary_calls": [
                    {
                        "endpoint": "jgb_member_permissions",
                        "params": {"role_id": "{session.role_id}", "user_id": "{row.member_user_id}"},
                        "list_path": "data",
                        "attach_as": "permissions"
                    },
                    {
                        "endpoint": "jgb_bill_visibility",
                        "params": {"role_id": "{session.role_id}", "viewer_user_id": "{row.member_user_id}", "bill_id": "{form.resource_ref}"},
                        "list_path": "data",
                        "attach_as": "bill_visibility"
                    }
                ]
            }
        }
    }'::jsonb
    -- END_METADATA_JSON account_team
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：團隊成員權限'
);

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category='對話規則' AND question_summary IN
        ('對話規則：註冊驗證排障','對話規則：登入排障','對話規則：帳號綁定異動','對話規則：團隊成員權限')
      AND is_active;
    RAISE NOTICE '✅ 帳號面向對話 config：% / 4', n;
END $$;
