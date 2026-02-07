#!/bin/bash
# 在 EC2 上創建最小必要檔案讓服務能啟動的腳本

echo "Creating minimal data files for semantic model service..."

# 創建 data 目錄
mkdir -p data

# 創建最小的 knowledge_base.json
cat > data/knowledge_base.json << 'EOF'
[]
EOF

# 創建其他可選檔案
cat > data/training_data.json << 'EOF'
[]
EOF

cat > data/test_data.json << 'EOF'
[]
EOF

cat > data/sample_queries.json << 'EOF'
[]
EOF

cat > data/knowledge_analysis.json << 'EOF'
{
  "total_records": 0,
  "categories": {},
  "extraction_time": "$(date -Iseconds)"
}
EOF

echo "✅ Minimal data files created successfully"
echo "⚠️  Note: These are empty files just to allow service startup"
echo "📌 You should run 'python scripts/extract_knowledge.py' to generate real data"