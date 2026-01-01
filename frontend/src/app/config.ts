/**
 * API 配置
 */
// 获取环境变量中的 API URL，支持 Docker 环境
const getApiBaseUrl = (): string => {
  // @ts-ignore - Vite 环境变量
  const envUrl = import.meta.env?.VITE_API_BASE_URL;
  if (envUrl) {
    return envUrl;
  }
  // 默认使用 localhost:5174（本地开发环境）
  // Docker 环境可以通过 VITE_API_BASE_URL 环境变量设置为 http://localhost:9528
  return 'http://localhost:5174';
};

export const API_CONFIG = {
  // 后端 API 基础 URL
  // 支持环境变量，默认使用 localhost（开发环境）
  // 生产环境可以通过 VITE_API_BASE_URL 环境变量配置
  BASE_URL: getApiBaseUrl(),
} as const;

/**
 * API 端点
 */
export const API_ENDPOINTS = {
  // 下载视频
  DOWNLOAD: `${API_CONFIG.BASE_URL}/download`,
  // 健康检查
  HEALTH: `${API_CONFIG.BASE_URL}/health`,
} as const;

