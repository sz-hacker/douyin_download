import React, { useState } from 'react';
import { Download, Terminal, Loader, CircleCheck, CircleAlert, Copy, ExternalLink } from 'lucide-react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Progress } from './ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'sonner';
import {
  downloadVideo,
  getVideoProxyUrl,
  getVideoDownloadUrl,
  processNoVocals,
  extractText,
  getFileDownloadUrl,
  downloadFile,
} from '../services/api';

interface VideoTask {
  id: string;
  url: string;
  platform: 'douyin' | 'unknown';
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'error';
  progress: number;
  progressMessage?: string; // 进度消息
  videoUrl?: string;
  videoUrls?: string[]; // 视频链接数组
  extractedText?: string;
  audioRemoved?: boolean;
  noVocalsFileUrl?: string; // 无背景音版本文件路径
  extractedTextFileUrl?: string; // 提取的文字文件路径
  extractTextTaskId?: string; // 提取文字的任务ID
  error?: string;
}

export function VideoDownloader() {
  /*
  拉布拉多喜结良缘，两个月以后生宝宝 http://xhslink.com/o/1p1co22wyeB 
复制后打开【小红书】查看笔记！
  */
  const [url, setUrl] = useState('9.20 复制打开抖音，看看【明慧.女性智慧的作品】为什么要努力学习# 重点班# 亲子教育 # 成长 ... https://v.douyin.com/e1VBWD6BHyo/ 12/30 Njp:/ v@F.UY ');
  const [tasks, setTasks] = useState<VideoTask[]>([]);
  const [activeTab, setActiveTab] = useState('download');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 检测URL平台
  const detectPlatform = (url: string): 'douyin' | 'unknown' => {
    if (url.includes('douyin') || url.includes('tiktok')) return 'douyin';
    return 'unknown';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!url.trim()) {
      toast.error('请输入视频URL');
      return;
    }

    const platform = detectPlatform(url);
    
    if (platform === 'unknown') {
      toast.warning('平台识别失败', {
        description: '请输入抖音的分享链接'
      });
      return;
    }

    setIsSubmitting(true);

    // 生成更友好的任务ID：时间戳 + 随机数
    const generateTaskId = () => {
      const timestamp = Date.now();
      const random = Math.random().toString(36).substring(2, 8);
      return `${timestamp}-${random}`;
    };

    const newTask: VideoTask = {
      id: generateTaskId(),
      url,
      platform,
      status: 'pending',
      progress: 0
    };

    setTasks(prev => [newTask, ...prev]);
    setUrl('');
    
    toast.success('任务已添加', {
      description: '检测到抖音视频'
    });

    // 调用后端API
    try {
      setTasks(prev => prev.map(task => 
        task.id === newTask.id 
          ? { ...task, status: 'downloading', progress: 10 }
          : task
      ));

      const data = await downloadVideo(url);
      
      setTasks(prev => prev.map(task => 
        task.id === newTask.id 
          ? { 
              ...task, 
              status: 'completed', 
              progress: 100,
              videoUrl: data.downloaded_file,
              videoUrls: data.videos || [], // 保存视频链接数组
              extractedText: data.message,
              audioRemoved: data.success
            }
          : task
      ));

      toast.success('任务完成', {
        description: data.message || '视频已下载并处理完成'
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '处理失败';
      setTasks(prev => prev.map(task => 
        task.id === newTask.id 
          ? { ...task, status: 'error', error: errorMessage }
          : task
      ));
      
      toast.error('处理失败', {
        description: errorMessage
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('已复制到剪贴板');
  };

  const getStatusText = (status: VideoTask['status']) => {
    const statusMap = {
      pending: '等待中',
      downloading: '下载中',
      processing: '处理中',
      completed: '已完成',
      error: '失败'
    };
    return statusMap[status];
  };

  return (
    <div className="min-h-screen bg-black text-green-400 p-4 md:p-8">
      {/* 终端风格头部 */}
      <div className="max-w-6xl mx-auto">

        {/* 输入区域 */}
        <Card className="bg-gray-950 border-green-500/30 p-6 mb-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-mono text-green-300 mb-2 block">
                {'>'} INPUT_URL:
              </label>
              <div className="flex gap-2">
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="粘贴抖音分享链接..."
                  className="bg-black border-green-500/50 text-green-400 placeholder:text-green-900 font-mono focus:border-green-500 focus:ring-green-500/20"
                />
                <Button 
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-green-600 hover:bg-green-700 text-black font-mono px-8 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <Loader className="w-4 h-4 mr-2 animate-spin" />
                      处理中...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      执行
                    </>
                  )}
                </Button>
              </div>
            </div>
            <div className="text-xs font-mono text-green-300/50">
              支持平台: 抖音 (Douyin)
            </div>
          </form>
        </Card>

        {/* 任务列表 */}
        <div className="space-y-4">
          {tasks.map((task) => (
            <Card 
              key={task.id} 
              className="bg-gray-950 border-green-500/30 p-6 hover:border-green-500/50 transition-all"
            >
              <div className="space-y-4">
                {/* 任务头部 */}
                <div>
                  <div className="flex items-center gap-2">
                    {task.status === 'completed' && (
                      <CircleCheck className="w-5 h-5 text-green-500" />
                    )}
                    {task.status === 'error' && (
                      <CircleAlert className="w-5 h-5 text-red-500" />
                    )}
                    {(task.status === 'downloading' || task.status === 'processing') && (
                      <Loader className="w-5 h-5 animate-spin text-green-500" />
                    )}
                  </div>
                  {/* 视频播放器 - 任务完成时显示第一个视频 */}
                  {task.status === 'completed' && task.videoUrls && task.videoUrls.length > 0 && (() => {
                    const videoUrl = task.videoUrls[0];
                    const fullVideoUrl = getVideoProxyUrl(videoUrl);
                    
                    return (
                      <div className="mt-4">
                        <div className="text-xs font-mono text-green-300 mb-2">
                          {'>'} 视频预览:
                        </div>
                        <div className="bg-black border border-green-500/30 rounded overflow-hidden">
                          <video 
                            src={fullVideoUrl}
                            controls
                            className="w-full max-w-2xl"
                            style={{ maxHeight: '400px' }}
                            crossOrigin="anonymous"
                            onError={(e) => {
                              console.error('视频加载失败:', fullVideoUrl, e);
                              toast.error('视频加载失败', {
                                description: '请检查视频URL是否正确或网络连接是否正常'
                              });
                            }}
                            onLoadStart={() => {
                              console.log('开始加载视频:', fullVideoUrl);
                            }}
                            onCanPlay={() => {
                              console.log('视频可以播放:', fullVideoUrl);
                            }}
                          >
                            您的浏览器不支持视频播放
                          </video>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* 进度条 */}
                {task.status !== 'completed' && task.status !== 'error' && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-green-300">
                        {task.progressMessage || getStatusText(task.status)}
                      </span>
                      <span className="text-green-500">{task.progress}%</span>
                    </div>
                    <Progress 
                      value={task.progress} 
                      className="bg-green-950 h-2"
                    />
                  </div>
                )}

                {/* 完成状态的选项卡 */}
                {task.status === 'completed' && (
                  <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsContent value="download" className="mt-4 space-y-2">
                      <div className="bg-black border border-green-500/30 p-4 rounded space-y-3">
                        {/* 视频链接列表 */}
                        {task.videoUrls && task.videoUrls.length > 0 ? (
                          <div className="space-y-2">
                            <div className="text-sm font-mono text-green-300 mb-2">
                              找到 {task.videoUrls.length} 个视频链接:
                            </div>
                            {task.videoUrls.map((videoUrl, index) => (
                              <div 
                                key={index}
                                className="bg-gray-950 border border-green-500/20 p-3 rounded flex items-center justify-between gap-2"
                              >
                                <div className="flex-1 min-w-0">
                                  <div className="text-xs font-mono text-green-400/70 mb-1">
                                    视频 {index + 1}
                                  </div>
                                  <div className="text-xs font-mono text-green-300 truncate" title={videoUrl}>
                                    {videoUrl}
                                  </div>
                                </div>
                                <div className="flex gap-2 flex-shrink-0">
                                  <Button 
                                    size="sm" 
                                    variant="ghost"
                                    className="text-green-500 hover:text-green-400 hover:bg-green-950"
                                    onClick={() => {
                                      copyText(videoUrl);
                                      toast.success('链接已复制');
                                    }}
                                    title="复制链接"
                                  >
                                    <Copy className="w-3 h-3" />
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    variant="ghost"
                                    className="text-green-500 hover:text-green-400 hover:bg-green-950"
                                    onClick={() => window.open(videoUrl, '_blank')}
                                    title="在新标签页打开"
                                  >
                                    <ExternalLink className="w-3 h-3" />
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    className="bg-green-600 hover:bg-green-700 text-black font-mono"
                                    onClick={() => {
                                      try {
                                        const downloadUrl = getVideoDownloadUrl(videoUrl, `video_${index + 1}.mp4`);
                                        downloadFile(downloadUrl, `video_${index + 1}.mp4`);
                                        toast.success('开始下载视频', {
                                          description: '视频正在下载中...'
                                        });
                                      } catch (error) {
                                        console.error('下载失败:', error);
                                        toast.error('下载失败', {
                                          description: '请检查网络连接或稍后重试'
                                        });
                                      }
                                    }}
                                    title="下载视频"
                                  >
                                    <Download className="w-3 h-3" />
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-sm font-mono text-green-300/50">
                            未找到视频链接
                          </div>
                        )}
                        
                        {/* 兼容旧版本：单个视频URL */}
                        {task.videoUrl && !task.videoUrls && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-mono text-green-300">原始视频</span>
                            <Button 
                              size="sm" 
                              className="bg-green-600 hover:bg-green-700 text-black font-mono"
                              onClick={() => toast.success('下载功能演示')}
                            >
                              <Download className="w-3 h-3 mr-1" />
                              下载
                            </Button>
                          </div>
                        )}
                        
                        {task.audioRemoved && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-mono text-green-300">无背景音版本</span>
                            <Button 
                              size="sm" 
                              className="bg-green-600 hover:bg-green-700 text-black font-mono"
                              onClick={async () => {
                                try {
                                  // 获取第一个视频URL
                                  const videoUrl = task.videoUrls && task.videoUrls.length > 0 
                                    ? task.videoUrls[0] 
                                    : task.videoUrl;
                                  
                                  if (!videoUrl) {
                                    toast.error('无法获取视频URL');
                                    return;
                                  }
                                  
                                  // 如果已经有处理好的文件，直接下载
                                  if (task.noVocalsFileUrl) {
                                    const downloadUrl = getFileDownloadUrl(task.noVocalsFileUrl);
                                    const filename = task.noVocalsFileUrl.split('/').pop() || 'no_vocals.mp4';
                                    downloadFile(downloadUrl, filename);
                                    toast.success('开始下载无背景音版本');
                                    return;
                                  }
                                  
                                  // 否则，先处理视频
                                  const processingToast = toast.info('正在处理视频，去除背景声...', {
                                    description: '这可能需要几分钟时间，请耐心等待',
                                    duration: Infinity  // 不自动关闭
                                  });
                                  
                                  try {
                                    const data = await processNoVocals(videoUrl);
                                    
                                    // 关闭处理中的提示
                                    toast.dismiss(processingToast);
                                    
                                    // 更新任务状态，保存文件路径
                                    setTasks(prev => prev.map(t => 
                                      t.id === task.id 
                                        ? { ...t, noVocalsFileUrl: data.file_path }
                                        : t
                                    ));
                                    
                                    // 下载文件
                                    const downloadUrl = getFileDownloadUrl(data.file_path);
                                    downloadFile(downloadUrl, data.filename || 'no_vocals.mp4');
                                    
                                    toast.success('无背景音版本生成成功', {
                                      description: '文件正在下载中...'
                                    });
                                  } catch (error) {
                                    // 关闭处理中的提示
                                    toast.dismiss(processingToast);
                                    throw error;
                                  }
                                } catch (error) {
                                  console.error('处理失败:', error);
                                  const errorMessage = error instanceof Error ? error.message : '处理失败';
                                  toast.error('处理失败', {
                                    description: errorMessage
                                  });
                                }
                              }}
                            >
                              <Download className="w-3 h-3 mr-1" />
                              下载
                            </Button>
                          </div>
                        )}
                        
                        {/* 提取视频文字 */}
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-mono text-green-300">提取视频文字</span>
                          <Button 
                            size="sm" 
                            className="bg-green-600 hover:bg-green-700 text-black font-mono"
                            onClick={async () => {
                              try {
                                // 获取第一个视频URL
                                const videoUrl = task.videoUrls && task.videoUrls.length > 0 
                                  ? task.videoUrls[0] 
                                  : task.videoUrl;
                                
                                if (!videoUrl) {
                                  toast.error('无法获取视频URL');
                                  return;
                                }
                                
                                // 如果已经有提取好的文件，直接下载
                                if (task.extractedTextFileUrl) {
                                  const downloadUrl = getFileDownloadUrl(task.extractedTextFileUrl);
                                  const filename = task.extractedTextFileUrl.split('/').pop() || 'extracted_text.txt';
                                  downloadFile(downloadUrl, filename);
                                  toast.success('开始下载文字文件');
                                  return;
                                }
                                
                                // 否则，先处理视频
                                // 生成任务ID
                                const extractTaskId = `extract_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
                                
                                // 显示处理中的提示（不改变UI状态）
                                const processingToast = toast.info('正在提取视频文字...', {
                                  description: '这可能需要几分钟时间，请耐心等待',
                                  duration: Infinity  // 不自动关闭
                                });
                                
                                try {
                                  // 启动处理
                                  const data = await extractText(videoUrl, extractTaskId);
                                  
                                  // 关闭处理中的提示
                                  toast.dismiss(processingToast);
                                  
                                  // 更新任务状态，保存文件路径（不改变status和progress）
                                  setTasks(prev => prev.map(t => 
                                    t.id === task.id 
                                      ? { 
                                          ...t, 
                                          extractedTextFileUrl: data.file_path
                                        }
                                      : t
                                  ));
                                  
                                  // 下载文件
                                  const downloadUrl = getFileDownloadUrl(data.file_path);
                                  downloadFile(downloadUrl, data.filename || 'extracted_text.txt');
                                  
                                  toast.success('文字提取成功', {
                                    description: '文件正在下载中...'
                                  });
                                } catch (error) {
                                  // 关闭处理中的提示
                                  toast.dismiss(processingToast);
                                  throw error;
                                }
                              } catch (error) {
                                console.error('提取失败:', error);
                                const errorMessage = error instanceof Error ? error.message : '提取失败';
                                toast.error('提取失败', {
                                  description: errorMessage
                                });
                              }
                            }}
                          >
                            <Download className="w-3 h-3 mr-1" />
                            下载
                          </Button>
                        </div>
                      </div>
                    </TabsContent>

                    <TabsContent value="text" className="mt-4">
                      <div className="bg-black border border-green-500/30 p-4 rounded space-y-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-mono text-green-300">提取的文字内容</span>
                          <Button 
                            size="sm" 
                            variant="ghost"
                            className="text-green-500 hover:text-green-400 hover:bg-green-950"
                            onClick={() => task.extractedText && copyText(task.extractedText)}
                          >
                            <Copy className="w-3 h-3 mr-1" />
                            复制
                          </Button>
                        </div>
                        <div className="bg-gray-950 p-3 rounded text-xs font-mono text-green-400 max-h-48 overflow-y-auto whitespace-pre-wrap">
                          {task.extractedText}
                        </div>
                      </div>
                    </TabsContent>

                    <TabsContent value="audio" className="mt-4">
                      <div className="bg-black border border-green-500/30 p-4 rounded space-y-3">
                        <div className="flex items-center gap-2 text-green-500">
                          <CircleCheck className="w-4 h-4" />
                          <span className="text-sm font-mono">背景音乐已消除</span>
                        </div>
                        <div className="text-xs font-mono text-green-300/70">
                          {'>'} Audio processing completed<br />
                          {'>'} Background music removed<br />
                          {'>'} Voice track preserved
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>
                )}

                {/* 错误状态 */}
                {task.status === 'error' && (
                  <div className="bg-red-950/30 border border-red-500/30 p-3 rounded">
                    <div className="text-sm font-mono text-red-400">
                      ERROR: {task.error || '处理失败'}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>

        {/* 空状态 */}
        {tasks.length === 0 && (
          <Card className="bg-gray-950 border-green-500/30 p-12 text-center">
            <Terminal className="w-12 h-12 mx-auto mb-4 text-green-500/50" />
            <p className="font-mono text-green-400/50">
              {'>'} NO_TASKS_FOUND
            </p>
            <p className="font-mono text-xs text-green-300/30 mt-2">
              输入视频URL开始下载任务
            </p>
          </Card>
        )}

        {/* 底部说明 */}
        <div className="mt-8 border border-green-500/20 bg-black/30 p-4 rounded">
          <div className="flex items-start gap-2">
            <CircleAlert className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div className="text-xs font-mono text-green-300/70 space-y-1">
              <p>注意事项:</p>
              <ul className="list-disc list-inside space-y-1 text-green-300/50">
                <li>实际视频下载需要遵守平台服务条款和版权法</li>
                <li>请勿下载或传播未经授权的内容</li>
                <li>建议仅用于个人学习和合法用途</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}