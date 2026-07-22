-- 反悔:20260722_routing_keyword_hygiene.sql——keywords/categories 還原至調校前原值,錨點下架
-- (原值快照自 dev 2026-07-22 調校前實查)

UPDATE knowledge_base SET keywords = '{合約,簽約邀請,發送邀請,不能發送,邀請}', updated_at = now()
WHERE id = 3368 AND question_summary = '合約簽約邀請 發送邀請 為什麼不能發送';
UPDATE knowledge_base SET keywords = '{合約,提前解約,解約,提前終止,可以解約}', updated_at = now()
WHERE id = 3370 AND question_summary = '合約提前解約 可以解約嗎 提前終止';
UPDATE knowledge_base SET keywords = '{合約,續約,可以續約,延長}', updated_at = now()
WHERE id = 3371 AND question_summary = '合約續約 可以續約嗎 延長合約';
UPDATE knowledge_base SET keywords = '{合約,合約狀態,狀態查詢}', updated_at = now()
WHERE id = 3372 AND question_summary = '合約狀態查詢 目前狀態';
UPDATE knowledge_base SET keywords = '{合約狀態,合約階段,狀態總覽,合約流程,"12 種狀態",合約}', updated_at = now()
WHERE id = 3373 AND question_summary = '合約狀態 12 階段總覽';
UPDATE knowledge_base SET keywords = '{物件狀態,已出租,刊登中,租約中,洽談中,物件}', updated_at = now()
WHERE id = 3428 AND question_summary = '物件狀態 定義條件';
UPDATE knowledge_base SET keywords = '{註冊,建立帳號,新帳號,開戶,註冊流程,第一次使用,怎麼開始}', updated_at = now()
WHERE id = 3435 AND question_summary = '註冊帳號 建立流程';
UPDATE knowledge_base SET keywords = '{門鎖故障,設備離線,門鎖離線,電表,"IoT 問題",無法連線,設備異常,門鎖,電表離線}', updated_at = now()
WHERE id = 3461 AND question_summary = 'IoT 設備無法連線 排查';
UPDATE knowledge_base SET keywords = '{租客管理,新增租客,編輯租客,租客名單,租客列表,管理租客}', updated_at = now()
WHERE id = 3475 AND question_summary = '租客名單 新增編輯管理';
UPDATE knowledge_base SET keywords = '{帳單發不出,帳單無法發送,帳單發送失敗,帳單寄不出,金額不能為空,帳單問題}', updated_at = now()
WHERE id = 3495 AND question_summary = '帳單為什麼發不出去';
UPDATE knowledge_base SET keywords = '{免註冊租客,免註冊續約,續約簽名,不用簽名,未綁定續約,租客類型}', updated_at = now()
WHERE id = 3529 AND question_summary = '免註冊租客續約 不需電子簽名';
UPDATE knowledge_base SET keywords = '{合約,生效,還沒生效}', updated_at = now()
WHERE id = 3814 AND question_summary = '合約怎麼還沒生效 生效了沒';
UPDATE knowledge_base SET keywords = '{合約,卡住,沒動靜}', updated_at = now()
WHERE id = 3815 AND question_summary = '合約卡在哪 卡住了 簽了沒動靜';
UPDATE knowledge_base SET keywords = '{點退,30天}', updated_at = now()
WHERE id = 3848 AND question_summary = '點退時間窗 到期前30天起';
UPDATE knowledge_base SET keywords = '{繳了,沒進來}', updated_at = now()
WHERE id = 3931 AND question_summary = '租客說繳了 錢還沒進來';
UPDATE knowledge_base SET keywords = '{無法註冊,註冊失敗}', updated_at = now()
WHERE id = 3975 AND question_summary = '租客一直沒辦法註冊 卡住了';
UPDATE knowledge_base SET keywords = '{儲值教學,租客儲值,怎麼儲值}', categories = '{}', updated_at = now()
WHERE id = 4053 AND question_summary = '租客儲值教學 操作步驟';
UPDATE knowledge_base SET keywords = '{刪除物件,合約,IoT}', updated_at = now()
WHERE id = 4144 AND question_summary = '物件刪除 條件 歷史合約會消失嗎';
UPDATE knowledge_base SET keywords = '{招租店舖,對外首頁,分享}', updated_at = now()
WHERE id = 4146 AND question_summary = '招租店舖 房東對外首頁 入口 分享';
UPDATE knowledge_base SET keywords = '{點交,點退,押金}', updated_at = now()
WHERE id = 4149 AND question_summary = '點交 點退 押金狀態 物件快速篩選';
UPDATE knowledge_base SET keywords = '{退房,換租客,點退,重開物件}', updated_at = now()
WHERE id = 4216 AND question_summary = '退房後換新租客 點退押金 物件要重開嗎';

-- 錨點下架(不實體刪除,保留稽核軌跡)
UPDATE knowledge_base SET is_active = FALSE, updated_at = now()
WHERE question_summary IN ('註冊名字跟證件不符 要怎麼改資料','想改合約租期 租金要調整',
                           '合約狀態怪怪的 不太對勁','租客儲值了電還是沒有來 沒復電');
