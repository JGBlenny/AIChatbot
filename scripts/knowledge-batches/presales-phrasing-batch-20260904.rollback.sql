-- rollback for presales-phrasing-batch-20260904.json（只刪本批 import_script 建立的列）
DELETE FROM knowledge_base WHERE created_by='import_script' AND question_summary IN (
  '可不可以線上簽約 線上簽 電子簽約 合約線上簽名 不用紙本',
  '費用怎麼算 一年多少錢 收費方式 月費 年費 要花多少',
  '公司管一百多間 幾百間 物件跟合約很多 團隊分工 大量物件怎麼管',
  '租客不繳租金怎麼辦 逾期 催繳 提醒 遲繳 拖欠',
  '舊系統資料可以匯進來嗎 批次匯入 搬資料 房東租客合約帳單 哪些能匯 合約能不能匯',
  '帳單格式能不能自己設定 帳單版面 收據樣式 自訂帳單 客製帳單 品項 抬頭'
);
-- 之後重建 semantic-model（排序表面含新列）
