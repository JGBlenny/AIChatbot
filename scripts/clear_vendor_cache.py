"""
清除業者參數快取
"""
import redis
import os

# 連接到 Redis
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6381))

try:
    r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

    # 測試連接
    r.ping()
    print(f"✅ 成功連接到 Redis: {redis_host}:{redis_port}")

    # 找出所有業者參數相關的快取鍵
    vendor_keys = r.keys('vendor_params:*')

    if vendor_keys:
        print(f"\n找到 {len(vendor_keys)} 個業者參數快取鍵:")
        for key in vendor_keys:
            print(f"  - {key}")

        # 刪除所有快取
        deleted = r.delete(*vendor_keys)
        print(f"\n✅ 已刪除 {deleted} 個快取鍵")
    else:
        print("\n沒有找到業者參數快取鍵")

    # 也清除所有快取（可選）
    # r.flushall()
    # print("\n✅ 已清除所有 Redis 快取")

except redis.ConnectionError as e:
    print(f"❌ 無法連接到 Redis: {e}")
except Exception as e:
    print(f"❌ 錯誤: {e}")
