-- Migration 41: 移除 Category 的 icon 欄位
-- 目的：簡化分類配置，移除不需要的圖示欄位
-- 日期：2025-10-25

-- 移除 icon 欄位
ALTER TABLE category_config DROP COLUMN IF EXISTS icon;

-- 移除相關註釋
COMMENT ON COLUMN category_config.icon IS NULL;
