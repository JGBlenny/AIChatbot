#!/usr/bin/env python3
import requests
import sys

question = sys.argv[1] if len(sys.argv) > 1 else "馬桶堵住了"

response = requests.post(
    "http://localhost:8100/api/v1/message",
    json={
        "vendor_id": 2,
        "message": question,
        "session_id": "test_single",
        "user_id": "test"
    }
)

if response.status_code != 200:
    print(f"錯誤: HTTP {response.status_code}")
    print(response.text)
    sys.exit(1)

data = response.json()
print(f"問題: {question}")
print(f"找到: {data.get('source_count', 0)} 個 SOP\n")

sources = data.get("sources")
if sources:
    for src in sources:
        print(f"  - [ID {src.get('id')}] {src.get('question_summary')}")
else:
    print(f"  回答: {data.get('answer', '')[:100]}...")
