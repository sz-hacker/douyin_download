/**
 * API 服务
 * 封装所有后端接口调用
 */

import { API_CONFIG } from '../config';

/**
 * 下载视频分析响应
 */
export interface DownloadResponse {
  success: boolean;
  message: string;
  videos?: string[];
  downloaded_file?: string;
  no_vocals_file?: string;
}

/**
 * 处理无背景音版本响应
 */
export interface NoVocalsResponse {
  success: boolean;
  message: string;
  file_path: string;
  filename: string;
}

/**
 * 提取文字响应
 */
export interface ExtractTextResponse {
  success: boolean;
  message: string;
  file_path: string;
  filename: string;
  task_id?: string;
}

/**
 * 任务进度响应
 */
export interface TaskProgressResponse {
  status: 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
  result?: {
    success: boolean;
    file_path: string;
    filename: string;
  };
}

/**
 * 下载视频（分析页面获取视频列表）
 */
export async function downloadVideo(url: string): Promise<DownloadResponse> {
  const response = await fetch(`${API_CONFIG.BASE_URL}/download`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '请求失败');
  }

  return response.json();
}

/**
 * 获取视频代理URL（用于播放）
 */
export function getVideoProxyUrl(videoUrl: string): string {
  const isDouyinVideo = videoUrl.includes('douyinvod.com') || videoUrl.includes('douyin.com');
  if (isDouyinVideo) {
    return `${API_CONFIG.BASE_URL}/proxy/video?video_url=${encodeURIComponent(videoUrl)}`;
  }
  return videoUrl.startsWith('http') ? videoUrl : `${API_CONFIG.BASE_URL}${videoUrl.startsWith('/') ? '' : '/'}${videoUrl}`;
}

/**
 * 下载视频文件
 */
export function getVideoDownloadUrl(videoUrl: string, filename?: string): string {
  const params = new URLSearchParams({
    video_url: videoUrl,
  });
  if (filename) {
    params.append('filename', filename);
  }
  return `${API_CONFIG.BASE_URL}/download/video?${params.toString()}`;
}

/**
 * 处理视频，生成无背景音版本
 */
export async function processNoVocals(videoUrl: string): Promise<NoVocalsResponse> {
  const response = await fetch(
    `${API_CONFIG.BASE_URL}/process/no-vocals?video_url=${encodeURIComponent(videoUrl)}`,
    {
      method: 'POST',
    }
  );

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '处理失败');
  }

  return response.json();
}

/**
 * 提取视频文字
 */
export async function extractText(videoUrl: string, taskId?: string): Promise<ExtractTextResponse> {
  const params = new URLSearchParams({
    video_url: videoUrl,
  });
  if (taskId) {
    params.append('task_id', taskId);
  }

  const response = await fetch(
    `${API_CONFIG.BASE_URL}/process/extract-text?${params.toString()}`,
    {
      method: 'POST',
    }
  );

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '处理失败');
  }

  return response.json();
}

/**
 * 获取任务进度
 */
export async function getTaskProgress(taskId: string): Promise<TaskProgressResponse> {
  const response = await fetch(`${API_CONFIG.BASE_URL}/task/progress/${taskId}`);

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '获取进度失败');
  }

  return response.json();
}

/**
 * 下载文件（包括无背景音版本和文字文件）
 */
export function getFileDownloadUrl(filePath: string): string {
  // filePath 可能是 /output/downloads/filename 或完整的URL
  if (filePath.startsWith('http')) {
    return filePath;
  }
  return `${API_CONFIG.BASE_URL}${filePath.startsWith('/') ? '' : '/'}${filePath}`;
}

/**
 * 触发文件下载
 */
export function downloadFile(url: string, filename: string): void {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

