"""
Test router registration to diagnose the issue
"""
from fastapi import FastAPI
from routers import knowledge_export

app = FastAPI()

print(f"Before registration:")
print(f"  Router prefix: {knowledge_export.router.prefix}")
print(f"  Router routes: {len(knowledge_export.router.routes)}")
print(f"  Route paths: {[r.path for r in knowledge_export.router.routes]}")

try:
    app.include_router(knowledge_export.router, tags=["knowledge_export"])
    print(f"\n✅ Router registered successfully")
    print(f"\nAfter registration:")
    print(f"  App routes: {len(app.routes)}")
    print(f"  App route paths: {[r.path for r in app.routes]}")
except Exception as e:
    print(f"\n❌ Registration failed: {e}")
    import traceback
    traceback.print_exc()
