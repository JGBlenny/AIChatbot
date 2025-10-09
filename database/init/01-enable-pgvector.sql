-- 啟用 pgvector 擴充套件
CREATE EXTENSION IF NOT EXISTS vector;

-- 驗證安裝
SELECT * FROM pg_extension WHERE extname = 'vector';
