#!/usr/bin/env python3
"""清除指定業者的緩存"""

import sys
sys.path.insert(0, '/app/rag-orchestrator')

from services.cache_service import CacheService

def clear_cache(vendor_id: int):
    """清除指定業者的緩存"""
    cache = CacheService()

    print(f"🗑️ 清除業者 {vendor_id} 的緩存...")
    count = cache.invalidate_by_vendor_id(vendor_id)
    print(f"✅ 已清除 {count} 條緩存")

    # 顯示統計
    stats = cache.get_stats()
    print(f"\n📊 當前緩存統計:")
    if stats.get('enabled'):
        for cache_type, count in stats.get('cache_counts', {}).items():
            print(f"  • {cache_type}: {count}")
    else:
        print(f"  緩存未啟用: {stats.get('reason', 'Unknown')}")

if __name__ == "__main__":
    vendor_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    clear_cache(vendor_id)
