/**
 * API 配置文件
 * 統一管理所有 API 端點，支援開發和生產環境
 */

/**
 * 獲取 API Base URL
 * - 開發環境: 使用 localhost
 * - 生產環境: 使用相對路徑（通過 Nginx proxy）
 */
const getBaseURL = () => {
  // 生產環境：使用相對路徑
  if (import.meta.env.PROD) {
    return '';  // 空字符串 = 相對路徑，通過 Nginx proxy
  }

  // 開發環境：使用空字符串，讓 Vite proxy 處理
  // Vite proxy 會將 /rag-api/* 路由到 rag-orchestrator:8100/api/*
  return '';
};

// API Base URL
export const API_BASE_URL = getBaseURL();

/**
 * 所有 API 端點定義
 */
export const API_ENDPOINTS = {
  // ==================== RAG Orchestrator API ====================

  // Chat 相關
  chat: `${API_BASE_URL}/rag-api/v1/chat`,
  chatStream: `${API_BASE_URL}/rag-api/v1/chat/stream`,

  // Intent 相關
  intents: `${API_BASE_URL}/rag-api/v1/intents`,
  intentById: (id) => `${API_BASE_URL}/rag-api/v1/intents/${id}`,

  // Vendor 相關（RAG API）
  vendorChat: (vendorId) => `${API_BASE_URL}/rag-api/v1/vendors/${vendorId}/chat`,
  vendorSOPs: (vendorId) => `${API_BASE_URL}/rag-api/v1/vendors/${vendorId}/sops`,

  // Knowledge Candidates 相關
  knowledgeCandidatesPending: `${API_BASE_URL}/rag-api/v1/knowledge-candidates/pending`,
  knowledgeCandidatesStats: `${API_BASE_URL}/rag-api/v1/knowledge-candidates/stats`,
  knowledgeCandidateById: (id) => `${API_BASE_URL}/rag-api/v1/knowledge-candidates/${id}`,
  knowledgeCandidateEdit: (id) => `${API_BASE_URL}/rag-api/v1/knowledge-candidates/${id}/edit`,
  knowledgeCandidateReview: (id) => `${API_BASE_URL}/rag-api/v1/knowledge-candidates/${id}/review`,

  // Loop Knowledge 相關（迴圈生成知識審核，包含 SOP）
  loopKnowledgePending: `${API_BASE_URL}/rag-api/v1/loop-knowledge/pending`,
  loopKnowledgeStats: `${API_BASE_URL}/rag-api/v1/loop-knowledge/stats`,
  loopKnowledgeById: (id) => `${API_BASE_URL}/rag-api/v1/loop-knowledge/${id}`,
  loopKnowledgeReview: (id) => `${API_BASE_URL}/rag-api/v1/loop-knowledge/${id}/review`,

  // SOP Categories 相關
  sopCategories: `${API_BASE_URL}/rag-api/v1/sop-categories`,

  // Vendors 相關（RAG API）
  ragVendors: `${API_BASE_URL}/rag-api/v1/vendors`,
  ragVendorById: (id) => `${API_BASE_URL}/rag-api/v1/vendors/${id}`,

  // SOP Groups 相關
  sopGroups: `${API_BASE_URL}/rag-api/v1/sop-groups`,

  // Unclear Questions 相關
  unclearQuestions: `${API_BASE_URL}/rag-api/v1/unclear-questions`,
  unclearQuestionById: (id) => `${API_BASE_URL}/rag-api/v1/unclear-questions/${id}`,

  // Platform SOP 相關
  platformSOPCategories: `${API_BASE_URL}/rag-api/v1/platform/sop/categories`,
  platformSOPGroups: `${API_BASE_URL}/rag-api/v1/platform/sop/groups`,
  platformSOPTemplates: `${API_BASE_URL}/rag-api/v1/platform/sop/templates`,

  // Loop 相關
  loopStart: `${API_BASE_URL}/rag-api/v1/loops/start`,
  loopList: `${API_BASE_URL}/rag-api/v1/loops/`,
  loopById: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}`,
  loopStatus: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/status`,
  loopIterations: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/iterations`,
  loopIterationResults: (loopId, iteration) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/iterations/${iteration}/backtest-results`,
  loopExecuteIteration: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/execute-iteration`,
  loopValidate: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/validate`,
  loopCompleteBatch: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/complete-batch`,
  loopStartNextBatch: `${API_BASE_URL}/rag-api/v1/loops/start-next-batch`,
  loopPause: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/pause`,
  loopResume: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/resume`,
  loopCancel: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/cancel`,

  // System Health 相關
  pipelineHealth: `${API_BASE_URL}/rag-api/v1/system/pipeline-health`,
  pipelineE2ETest: `${API_BASE_URL}/rag-api/v1/system/pipeline-e2e-test`,

  // ==================== Knowledge Admin API ====================

  // Vendors 相關
  vendors: '/api/vendors',
  vendorById: (id) => `/api/vendors/${id}`,

  // Test Scenarios 相關
  testScenarios: '/api/test-scenarios',
  testScenarioById: (id) => `/api/test-scenarios/${id}`,

  // Knowledge Base 相關
  knowledge: '/api/knowledge',
  knowledgeById: (id) => `/api/knowledge/${id}`,
};

/**
 * 構建完整 URL（用於特殊情況）
 * @param {string} endpoint - API 端點
 * @returns {string} 完整 URL
 */
export const buildURL = (endpoint) => {
  if (endpoint.startsWith('http')) {
    return endpoint;  // 已經是完整 URL
  }
  return `${API_BASE_URL}${endpoint}`;
};

/**
 * 獲取 WebSocket URL（用於 streaming）
 * @param {string} endpoint - WebSocket 端點
 * @returns {string} WebSocket URL
 */
export const getWebSocketURL = (endpoint) => {
  if (import.meta.env.PROD) {
    // 生產環境：使用當前域名的 ws/wss 協議
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${endpoint}`;
  }

  // 開發環境：使用 localhost
  return `ws://localhost:8100${endpoint}`;
};

// 導出默認配置
export default {
  API_BASE_URL,
  API_ENDPOINTS,
  buildURL,
  getWebSocketURL,
};
