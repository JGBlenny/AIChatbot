#!/usr/bin/env python3
"""寫入 API 解讀知識（form_schemas + knowledge_base）"""

import json
import os
import psycopg2
import psycopg2.extras


def main():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    with open("/app/scripts/kb_coverage/api_interpretation_entries.json") as f:
        data = json.load(f)

    # 1. form_schemas
    print("=== form_schemas ===")
    for fs in data["form_schemas"]:
        cur.execute(
            """
            INSERT INTO form_schemas
                (form_id, form_name, description, fields,
                 default_intro, on_complete_action, api_config, skip_review, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)
            ON CONFLICT (form_id) DO UPDATE SET
                form_name = EXCLUDED.form_name,
                description = EXCLUDED.description,
                fields = EXCLUDED.fields,
                default_intro = EXCLUDED.default_intro,
                on_complete_action = EXCLUDED.on_complete_action,
                api_config = EXCLUDED.api_config,
                skip_review = EXCLUDED.skip_review
            RETURNING id, form_id
            """,
            (
                fs["form_id"],
                fs["form_name"],
                fs["description"],
                json.dumps(fs["fields"], ensure_ascii=False),
                fs["default_intro"],
                fs["on_complete_action"],
                json.dumps(fs["api_config"], ensure_ascii=False),
                fs["skip_review"],
            ),
        )
        r = cur.fetchone()
        print(f"  id={r['id']} form_id={r['form_id']}")

    # 2. knowledge_base
    print("\n=== knowledge_base ===")
    for kb in data["knowledge_entries"]:
        cur.execute(
            """
            INSERT INTO knowledge_base
                (question_summary, answer, action_type, form_id,
                 trigger_mode, trigger_form_condition,
                 api_config, scope, business_types, source_type, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
            RETURNING id, question_summary
            """,
            (
                kb["question_summary"],
                kb["answer"],
                kb["action_type"],
                kb["form_id"],
                kb["trigger_mode"],
                kb["trigger_form_condition"],
                json.dumps(kb.get("api_config"), ensure_ascii=False)
                if kb.get("api_config")
                else None,
                kb["scope"],
                kb["business_types"],
                kb["source_type"],
            ),
        )
        r = cur.fetchone()
        print(f"  id={r['id']} q={r['question_summary']}")

    conn.commit()
    print("\nDone!")
    conn.close()


if __name__ == "__main__":
    main()
