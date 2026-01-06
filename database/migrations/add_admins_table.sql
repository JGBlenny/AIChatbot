-- 建立管理員帳號表
-- 用途：支持管理後台登入認證
-- 執行時機：部署登入功能時

-- 建立 admins 表
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hash
    email VARCHAR(100),
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引以提升查詢效能
CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);
CREATE INDEX IF NOT EXISTS idx_admins_active ON admins(is_active);

-- 添加註解
COMMENT ON TABLE admins IS '管理員帳號表 - 用於管理後台登入認證';
COMMENT ON COLUMN admins.username IS '登入帳號（唯一）';
COMMENT ON COLUMN admins.password_hash IS 'bcrypt 加密的密碼雜湊';
COMMENT ON COLUMN admins.email IS '管理員 Email';
COMMENT ON COLUMN admins.full_name IS '管理員姓名';
COMMENT ON COLUMN admins.is_active IS '帳號是否啟用';
COMMENT ON COLUMN admins.last_login_at IS '最後登入時間';

-- 建立觸發器：自動更新 updated_at
CREATE TRIGGER update_admins_updated_at
    BEFORE UPDATE ON admins
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入預設管理員帳號
-- 帳號: admin
-- 密碼: admin123
-- bcrypt hash 使用 12 rounds (bcrypt 4.0.1)
INSERT INTO admins (username, password_hash, email, full_name)
VALUES (
    'admin',
    '$2b$12$JUPKTOD66WsBfuJpvTf2oeaOUJwzmW03CIgXx2n4aPWqjopaKaYPi',
    'admin@aichatbot.com',
    '系統管理員'
) ON CONFLICT (username) DO NOTHING;

-- 驗證資料
SELECT id, username, email, full_name, is_active, created_at FROM admins;
