/**
 * AI 回答文字格式化工具
 *
 * 條件式處理：
 * - 如果文字已經有格式（換行、Markdown），保持原樣
 * - 如果是一整段沒有換行的文字，自動在句號後添加段落
 */

/**
 * 格式化 AI 回答文字
 * @param {string} text - AI 回答原始文字
 * @returns {string} - 格式化後的文字
 */
export function formatAIResponse(text) {
  if (!text || typeof text !== 'string') {
    return text;
  }

  // 檢查是否已經有格式（包含換行符或 Markdown 標記）
  const hasFormatting = (
    text.includes('\n') ||           // 已有換行
    text.includes('##') ||            // Markdown 標題
    text.includes('- ') ||            // Markdown 列表
    text.includes('* ') ||            // Markdown 列表（星號）
    text.includes('1. ') ||           // Markdown 數字列表
    text.match(/^>\s/m)               // Markdown 引用
  );

  // 如果已經有格式，保持原樣
  if (hasFormatting) {
    return text;
  }

  // 如果是一整段沒有換行的文字，自動分段
  // 在中文句號、問號、驚嘆號後添加雙換行（段落分隔）
  return text
    .replace(/([。！？])\s*/g, '$1\n\n')  // 句子結尾後添加段落
    .replace(/\n{3,}/g, '\n\n')          // 移除過多空行（最多保留雙換行）
    .trim();                              // 移除首尾空白
}

/**
 * 檢查文字是否需要格式化
 * @param {string} text - 文字內容
 * @returns {boolean} - true 表示需要格式化
 */
export function needsFormatting(text) {
  if (!text || typeof text !== 'string') {
    return false;
  }

  return !(
    text.includes('\n') ||
    text.includes('##') ||
    text.includes('- ') ||
    text.includes('* ') ||
    text.includes('1. ')
  );
}
