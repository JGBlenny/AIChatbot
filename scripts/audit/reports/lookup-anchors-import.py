"""部署重放：lookup 案場級錨點（通用類已依 2026-07-06 分工定案改 configs 模板，不在此腳本）。"""

import json, urllib.request, psycopg2

ANCHORS = [
    ("管理費 金額 多少 包含項目 涵蓋什麼", "management_fee"),
    ("包裹代收 收件 包裹室位置 領取時間", "parcel_service"),
    ("停車費 車位費用 月租車位", "parking_fee"),
    ("社區設施 公共設施 健身房 交誼廳", "community_facilities"),
    ("押金資訊 押金多少 退還方式", "deposit_info"),
    ("租金資訊 租金金額 繳納方式", "rent_info"),
    ("電費 計費方式 每度電價 電錶", "utility_electricity"),
    ("水費 計費方式 水錶", "utility_water"),
    ("瓦斯費 計費方式 瓦斯錶", "utility_gas"),
]

def emb(text):
    req = urllib.request.Request("http://localhost:5001/api/v1/embeddings",
                                 data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        e = json.loads(r.read())["embedding"]
    assert len(e) == 1536
    return "[" + ",".join(f"{v:.8f}" for v in e) + "]"

conn = psycopg2.connect(host="localhost", user="aichatbot",
                        password="aichatbot_password", dbname="aichatbot_admin")
cur = conn.cursor()
n = 0
for q, cat in ANCHORS:
    cur.execute("SELECT id FROM knowledge_base WHERE question_summary=%s", (q,))
    if cur.fetchone():
        print(f"⏭️ 已存在：{q}")
        continue
    api_config = json.dumps({"endpoint": "lookup",
                             "static_params": {"key": "", "key2": "全部", "category": cat}},
                            ensure_ascii=False)
    cur.execute("""
        INSERT INTO knowledge_base (question_summary, answer, action_type, api_config,
            target_user, business_types, scope, priority, is_active, source_type, created_by, embedding)
        VALUES (%s, '', 'api_call', %s,
            ARRAY['tenant','landlord','all_users'], ARRAY['property_management','full_service'],
            'global', 0, TRUE, 'manual', 'lookup_anchor_20260706', %s::vector)
    """, (q, api_config, emb(q)))
    n += 1
    print(f"＋ {q} → {cat}")
conn.commit()
print(f"完成：{n} 筆錨點")
"""一次性：lookup 錨點自然問句變體（0.75 觸發門檻對策）。"""
import json, urllib.request, psycopg2

VARIANTS = {
    "management_fee": ["管理費多少錢 包含哪些項目", "為什麼要收管理費 費用怎麼算"],
    "parcel_service": ["管理員會代收包裹嗎", "包裹可以代收嗎 要去哪裡領包裹"],
    "parking_fee": ["有停車位嗎 停車費怎麼算", "機車汽車停車位費用"],
    "community_facilities": ["社區有哪些公共設施可以用", "有健身房或交誼廳嗎"],
    "deposit_info": ["押金要付多少 什麼時候退", "退租押金怎麼退還"],
    "rent_info": ["租金什麼時候繳 怎麼計算", "每月租金繳費資訊"],
    "utility_electricity": ["電費怎麼算 一度多少錢", "電費帳單計費方式"],
    "utility_water": ["水費怎麼算 怎麼收", "水費帳單計費方式"],
    "utility_gas": ["瓦斯費怎麼算 怎麼收", "瓦斯費計費收費方式"],
}

def emb(text):
    req = urllib.request.Request("http://localhost:5001/api/v1/embeddings",
                                 data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return "[" + ",".join(f"{v:.8f}" for v in json.loads(r.read())["embedding"]) + "]"

conn = psycopg2.connect(host="localhost", user="aichatbot",
                        password="aichatbot_password", dbname="aichatbot_admin")
cur = conn.cursor()
n = 0
for cat, qs in VARIANTS.items():
    api_config = json.dumps({"endpoint": "lookup",
                             "static_params": {"key": "", "key2": "全部", "category": cat}},
                            ensure_ascii=False)
    for q in qs:
        cur.execute("SELECT id FROM knowledge_base WHERE question_summary=%s", (q,))
        if cur.fetchone():
            continue
        cur.execute("""
            INSERT INTO knowledge_base (question_summary, answer, action_type, api_config,
                target_user, business_types, scope, priority, is_active, source_type, created_by, embedding)
            VALUES (%s, '', 'api_call', %s,
                ARRAY['tenant','landlord','all_users'], ARRAY['property_management','full_service'],
                'global', 0, TRUE, 'manual', 'lookup_anchor_20260706', %s::vector)
        """, (q, api_config, emb(q)))
        n += 1
conn.commit()
print(f"變體錨點：{n} 筆")
