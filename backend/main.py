#!/usr/bin/env python3
"""
Video Downloader API Service
简单的API服务，通过API传递URL调用下载器
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn
import re
import logging
import requests
import uuid
import time
import sys
import os
import asyncio
from pathlib import Path
from urllib.parse import unquote, urlparse
from douyin_downloader import EnhancedDouyinDownloader, USER_AGENT
from remove_vocals import VocalRemover
from extract_video_text import VideoTextExtractor

# 任务进度存储（内存中，生产环境应使用Redis等）
task_progress: Dict[str, Dict] = {}

# 统一的输出目录配置
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR = OUTPUT_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)
TEMP_AUDIO_DIR = OUTPUT_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)
TEMP_TEXT_DIR = OUTPUT_DIR / "temp_text"
TEMP_TEXT_DIR.mkdir(exist_ok=True)

# 公共请求头
def get_video_headers() -> Dict[str, str]:
    """获取视频请求的公共请求头"""
    return {
        'User-Agent': USER_AGENT,
        'Referer': 'https://www.douyin.com/',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
    }

# 下载视频到本地
def download_video_to_local(video_url: str, output_path: Path, timeout: int = 60) -> None:
    """下载视频到本地文件"""
    headers = get_video_headers()
    response = requests.get(
        video_url,
        headers=headers,
        stream=True,
        timeout=timeout,
        allow_redirects=True
    )
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

# 配置日志
def setup_logging():
    """配置日志系统"""
    # 检查是否已经配置过
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return root_logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 配置根日志记录器
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    return root_logger

# 初始化日志系统
setup_logging()

# 创建当前模块的日志记录器
logger = logging.getLogger(__name__)

# 配置 asyncio 日志级别，减少连接关闭相关的错误日志
# 在 Windows 上，客户端提前关闭连接会导致 asyncio 产生错误日志
# 这些是正常现象，不应该显示为错误
asyncio_logger = logging.getLogger('asyncio')
asyncio_logger.setLevel(logging.CRITICAL)  # 只显示严重错误，忽略连接关闭错误

# 同时配置 uvicorn 的访问日志，减少不必要的日志
uvicorn_access_logger = logging.getLogger('uvicorn.access')
uvicorn_access_logger.setLevel(logging.WARNING)  # 减少访问日志输出

# 添加异常处理器，捕获 asyncio 回调中的连接错误
def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理器，过滤掉常见的连接关闭错误"""
    if issubclass(exc_type, (ConnectionResetError, BrokenPipeError, OSError)):
        # 检查是否是连接关闭相关的错误
        error_msg = str(exc_value)
        if any(keyword in error_msg.lower() for keyword in ['10054', 'connection', 'reset', 'broken pipe']):
            # 这些是正常的连接关闭，不记录
            return
    
    # 其他错误正常记录
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# 只在 Windows 上应用异常处理器
if sys.platform == 'win32':
    sys.excepthook = handle_exception

app = FastAPI(title="Video Downloader API", version="1.0.0")

# 添加 asyncio 事件循环异常处理器（用于抑制连接关闭错误）
def custom_exception_handler(loop, context):
    """自定义 asyncio 异常处理器，过滤连接关闭错误"""
    exception = context.get('exception')
    if exception:
        if isinstance(exception, (ConnectionResetError, BrokenPipeError, OSError)):
            error_msg = str(exception)
            if any(keyword in error_msg.lower() for keyword in ['10054', 'connection', 'reset', 'broken pipe', 'shutdown']):
                # 这些是正常的连接关闭，不记录
                return
    
    # 其他异常使用默认处理
    loop.default_exception_handler(context)

# 设置全局异常处理器
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # 如果循环已经在运行，使用 call_soon_threadsafe
        loop.call_soon_threadsafe(lambda: loop.set_exception_handler(custom_exception_handler))
    else:
        loop.set_exception_handler(custom_exception_handler)
except RuntimeError:
    # 如果没有事件循环，在启动时设置
    pass

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)


class DownloadRequest(BaseModel):
    url: str


class DownloadResponse(BaseModel):
    success: bool
    message: str
    videos: Optional[list] = None
    downloaded_file: Optional[str] = None
    no_vocals_file: Optional[str] = None  # 无背景音版本文件路径


@app.post("/download", response_model=DownloadResponse)
async def download_video(request: DownloadRequest):
    """
    下载视频
    接收URL参数，分析页面并下载视频
    """
    logger.info(f"收到下载请求，原始URL: {request.url}")
    try:
        # 使用正则匹配提取 HTTP/HTTPS 地址
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        matches = re.findall(url_pattern, request.url)
        
        if not matches:
            logger.warning(f"未找到有效的URL地址，原始输入: {request.url}")
            raise HTTPException(status_code=400, detail="未找到有效的URL地址")
        
        # 取第一个匹配的URL
        url = matches[0].strip()
        logger.debug(f"提取的URL: {url}")
        
        # 验证URL格式
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            logger.debug(f"URL添加协议前缀: {url}")
        
        logger.info(f"开始分析页面: {url}")
        # 创建下载器实例
        downloader = EnhancedDouyinDownloader()
        
        # 分析页面获取视频列表
        videos = await downloader.analyze_douyin_page(url)
        
        if not videos:
            logger.warning(f"页面分析完成，但未找到视频: {url}")
            return DownloadResponse(
                success=False,
                message="未找到视频",
                videos=[]
            )
        
        logger.info(f"页面分析完成，找到 {len(videos)} 个视频")
        
        # 提取视频链接数组
        video_urls = [video.get('src', '') for video in videos if video.get('src')]
        
        return DownloadResponse(
            success=True,
            message=f"成功找到 {len(video_urls)} 个视频",
            videos=video_urls
        )
    
    except HTTPException:
        # 重新抛出 HTTP 异常，不记录为错误
        raise
    except Exception as e:
        logger.error(f"处理请求时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "Video Downloader API",
        "version": "1.0.0",
        "endpoints": {
            "POST /download": "下载视频，需要传递url参数"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.get("/proxy/video")
async def proxy_video(video_url: str, request: Request):
    """
    代理视频流，用于绕过防盗链
    通过后端代理访问视频，添加必要的请求头
    """
    try:
        # URL解码
        video_url = unquote(video_url)
        
        logger.info(f"代理视频请求: {video_url}")
        
        # 设置请求头，模拟浏览器请求
        headers = get_video_headers()
        
        # 从请求中获取Range头（用于视频播放的断点续传）
        range_header = request.headers.get('Range')
        if range_header:
            headers['Range'] = range_header
            logger.debug(f"转发Range请求: {range_header}")
        
        # 发送请求获取视频流
        response = requests.get(
            video_url,
            headers=headers,
            stream=True,
            timeout=30,
            allow_redirects=True
        )

        response.raise_for_status()
        
        # 构建响应头
        response_headers = {
            'Accept-Ranges': 'bytes',
            'Content-Type': response.headers.get('Content-Type', 'video/mp4'),
        }
        
        # 如果有Content-Length，添加它
        if 'Content-Length' in response.headers:
            response_headers['Content-Length'] = response.headers['Content-Length']
        
        # 如果有Content-Range（Range请求的响应），添加它
        if 'Content-Range' in response.headers:
            response_headers['Content-Range'] = response.headers['Content-Range']
            # Range请求返回206状态码
            status_code = 206
        else:
            status_code = 200
        
        # 创建安全的流式生成器，捕获连接错误
        def safe_iter_content():
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                # 客户端提前关闭连接是正常情况，只记录调试信息
                logger.debug(f"客户端关闭连接: {str(e)}")
            except Exception as e:
                # 其他错误才记录为警告
                logger.warning(f"流式传输错误: {str(e)}")
        
        # 返回流式响应
        return StreamingResponse(
            safe_iter_content(),
            media_type=response.headers.get('Content-Type', 'video/mp4'),
            headers=response_headers,
            status_code=status_code
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"代理视频请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"代理视频失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理视频代理时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理视频代理时出错: {str(e)}")


@app.get("/download/video")
async def download_video_file(video_url: str, filename: Optional[str] = None):
    """
    下载视频文件
    通过后端代理下载视频，绕过防盗链，返回可下载的文件
    """
    try:
        # URL解码
        video_url = unquote(video_url)
        
        logger.info(f"下载视频请求: {video_url}")
        
        # 设置请求头，模拟浏览器请求
        headers = get_video_headers()
        
        # 发送请求获取视频流
        response = requests.get(
            video_url,
            headers=headers,
            stream=True,
            timeout=60,  # 下载可能需要更长时间
            allow_redirects=True
        )

        response.raise_for_status()
        
        # 如果没有提供文件名，从URL或Content-Disposition中提取
        if not filename:
            # 尝试从Content-Disposition头获取文件名
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^\s;]+)', content_disposition)
                if filename_match:
                    filename = filename_match.group(1).strip('\'"')
            
            # 如果还是没有，从URL路径提取
            if not filename:
                parsed_url = urlparse(video_url)
                path = parsed_url.path
                if path:
                    filename = path.split('/')[-1]
                    # 清理文件名
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # 如果还是没有，使用默认名称
            if not filename or '.' not in filename:
                filename = 'video.mp4'
        
        # 确保文件名安全
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        if not filename.endswith('.mp4') and not filename.endswith('.webm') and not filename.endswith('.mov'):
            filename += '.mp4'
        
        # 构建响应头，设置下载文件名
        response_headers = {
            'Content-Type': response.headers.get('Content-Type', 'video/mp4'),
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
        
        # 如果有Content-Length，添加它（用于显示下载进度）
        if 'Content-Length' in response.headers:
            response_headers['Content-Length'] = response.headers['Content-Length']
        
        logger.info(f"开始流式传输视频: {filename}, 大小: {response_headers.get('Content-Length', '未知')}")
        
        # 返回流式响应，浏览器会自动下载
        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type=response.headers.get('Content-Type', 'video/mp4'),
            headers=response_headers
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"下载视频请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载视频失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理视频下载时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理视频下载时出错: {str(e)}")


@app.post("/process/no-vocals")
async def process_no_vocals(video_url: str):
    """
    处理视频，生成无背景音版本
    下载视频，去除人声，返回处理后的文件路径
    """
    try:
        video_url = unquote(video_url)

        logger.info(f"处理无背景音版本请求: {video_url}")
        
        # 下载视频到临时目录
        temp_filename = f"temp_{int(time.time())}.mp4"
        temp_video_path = DOWNLOADS_DIR / temp_filename
        
        logger.info(f"开始下载视频到: {temp_video_path}")
        
        # 下载视频
        download_video_to_local(video_url, temp_video_path, timeout=60)
        
        logger.info(f"视频下载完成: {temp_video_path}")
        
        # 处理视频，生成无背景音版本
        logger.info("开始处理视频，去除人声...")
        remover = VocalRemover(method='demucs', temp_dir=str(TEMP_AUDIO_DIR))
        
        # 生成输出文件名
        output_filename = f"{temp_video_path.stem}_no_vocals{temp_video_path.suffix}"
        output_path = DOWNLOADS_DIR / output_filename
        
        # 处理视频
        success = remover.process_video(
            str(temp_video_path),
            str(output_path),
            keep_vocals=False  # 去除人声，保留背景音乐
        )
        
        if not success or not output_path.exists():
            # 清理临时文件
            if temp_video_path.exists():
                temp_video_path.unlink()
            raise HTTPException(status_code=500, detail="视频处理失败")
        
        logger.info(f"无背景音版本生成完成: {output_path}")
        
        # 清理临时原始视频文件
        if temp_video_path.exists():
            temp_video_path.unlink()
        
        # 返回文件路径（相对路径，前端可以通过静态文件服务访问）
        return {
            "success": True,
            "message": "无背景音版本生成成功",
            "file_path": f"/output/downloads/{output_filename}",
            "filename": output_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理无背景音版本时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/output/downloads/{filename}")
async def download_file(filename: str):
    """
    下载文件（包括无背景音版本）
    """
    try:
        file_path = DOWNLOADS_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查文件是否在downloads目录内（安全措施）
        if not str(file_path.resolve()).startswith(str(DOWNLOADS_DIR.resolve())):
            raise HTTPException(status_code=403, detail="访问被拒绝")
        
        def iterfile():
            try:
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                # 客户端提前关闭连接是正常情况，只记录调试信息
                logger.debug(f"客户端关闭连接: {str(e)}")
            except Exception as e:
                logger.warning(f"文件流式传输错误: {str(e)}")
        
        # 确定媒体类型
        if filename.endswith('.mp4'):
            media_type = 'video/mp4'
        elif filename.endswith('.mp3'):
            media_type = 'audio/mpeg'
        elif filename.endswith('.txt'):
            media_type = 'text/plain; charset=utf-8'
        elif filename.endswith('.srt'):
            media_type = 'text/plain; charset=utf-8'
        else:
            media_type = 'application/octet-stream'
        
        return StreamingResponse(
            iterfile(),
            media_type=media_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(file_path.stat().st_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@app.post("/process/extract-text")
async def process_extract_text(video_url: str, task_id: Optional[str] = None):
    """
    提取视频文字
    下载视频，提取文字（优先使用嵌入字幕，失败则使用ASR），返回提取的文字文件路径
    """
    try:
        video_url = unquote(video_url)
        
        # 生成或使用提供的任务ID
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # 初始化任务进度
        task_progress[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "开始处理...",
            "result": None
        }
        
        logger.info(f"提取视频文字请求: {video_url}, 任务ID: {task_id}")
        
        # 下载视频到临时目录
        temp_filename = f"temp_text_{int(time.time())}.mp4"
        temp_video_path = DOWNLOADS_DIR / temp_filename
        
        logger.info(f"开始下载视频到: {temp_video_path}")
        
        # 下载视频
        download_video_to_local(video_url, temp_video_path, timeout=60)
        
        logger.info(f"视频下载完成: {temp_video_path}")
        
        # 提取文字
        logger.info("开始提取视频文字...")
        extractor = VideoTextExtractor(temp_dir=str(TEMP_TEXT_DIR))
        
        if not extractor.check_dependencies():
            raise HTTPException(status_code=500, detail="依赖检查失败")
        
        # 优先尝试提取嵌入字幕
        text_file_path = None
        success = False
        
        # 尝试提取嵌入字幕
        try:
            logger.info("尝试提取嵌入字幕...")
            task_progress[task_id].update({
                "progress": 40,
                "message": "正在提取嵌入字幕..."
            })
            subtitle_output = DOWNLOADS_DIR / f"{temp_video_path.stem}_subtitle.txt"
            success = extractor.extract_embedded_subtitles(str(temp_video_path), str(subtitle_output))
            if success and subtitle_output.exists():
                text_file_path = subtitle_output
                logger.info(f"嵌入字幕提取成功: {text_file_path}")
                task_progress[task_id].update({
                    "progress": 100,
                    "message": "嵌入字幕提取成功"
                })
        except Exception as e:
            logger.warning(f"提取嵌入字幕失败: {str(e)}")
        
        # 如果嵌入字幕失败，尝试使用ASR（语音识别）
        if not success or not text_file_path:
            try:
                logger.info("尝试使用ASR提取文字...")
                task_progress[task_id].update({
                    "progress": 40,
                    "message": "正在使用语音识别提取文字（这可能需要几分钟）..."
                })
                asr_output = DOWNLOADS_DIR / f"{temp_video_path.stem}_asr.txt"
                success = extractor.extract_with_asr(str(temp_video_path), str(asr_output), method='whisper')
                if success and asr_output.exists():
                    text_file_path = asr_output
                    logger.info(f"ASR提取成功: {text_file_path}")
                    task_progress[task_id].update({
                        "progress": 100,
                        "message": "语音识别提取成功"
                    })
            except Exception as e:
                logger.warning(f"ASR提取失败: {str(e)}")
        
        # 如果还是失败，尝试OCR（优先使用PaddleOCR，对中文支持更好）
        if not success or not text_file_path:
            # 优先尝试 PaddleOCR（对中文支持更好）
            try:
                logger.info("尝试使用PaddleOCR提取文字...")
                task_progress[task_id].update({
                    "progress": 40,
                    "message": "正在使用OCR识别画面文字（这可能需要几分钟）..."
                })
                ocr_output = DOWNLOADS_DIR / f"{temp_video_path.stem}_ocr.txt"
                success = extractor.extract_with_ocr(
                    str(temp_video_path), 
                    str(ocr_output), 
                    method='paddleocr',
                    interval=0.5,  # 减小采样间隔，提高覆盖率
                    lang='ch'
                )
                if success and ocr_output.exists():
                    text_file_path = ocr_output
                    logger.info(f"PaddleOCR提取成功: {text_file_path}")
                    task_progress[task_id].update({
                        "progress": 100,
                        "message": "OCR识别成功"
                    })
            except Exception as e:
                logger.warning(f"PaddleOCR提取失败: {str(e)}")
                # 如果PaddleOCR失败，尝试EasyOCR
                try:
                    logger.info("尝试使用EasyOCR提取文字...")
                    task_progress[task_id].update({
                        "progress": 40,
                        "message": "正在使用EasyOCR识别画面文字..."
                    })
                    ocr_output = DOWNLOADS_DIR / f"{temp_video_path.stem}_ocr.txt"
                    success = extractor.extract_with_ocr(
                        str(temp_video_path), 
                        str(ocr_output), 
                        method='easyocr',
                        interval=0.5,
                        lang='ch_sim+en'
                    )
                    if success and ocr_output.exists():
                        text_file_path = ocr_output
                        logger.info(f"EasyOCR提取成功: {text_file_path}")
                        task_progress[task_id].update({
                            "progress": 100,
                            "message": "OCR识别成功"
                        })
                except Exception as e2:
                    logger.warning(f"EasyOCR提取失败: {str(e2)}")
        
        if not success or not text_file_path or not text_file_path.exists():
            # 清理临时文件
            if temp_video_path.exists():
                temp_video_path.unlink()
            # 更新任务进度：失败
            task_progress[task_id].update({
                "status": "error",
                "progress": 0,
                "message": "文字提取失败，请检查视频是否包含字幕或语音"
            })
            raise HTTPException(status_code=500, detail="文字提取失败，请检查视频是否包含字幕或语音")
        
        logger.info(f"文字提取完成: {text_file_path}")
        
        # 清理临时原始视频文件
        if temp_video_path.exists():
            temp_video_path.unlink()
        
        # 更新任务进度：完成
        task_progress[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "文字提取成功",
            "result": {
                "success": True,
                "file_path": f"/output/downloads/{text_file_path.name}",
                "filename": text_file_path.name
            }
        })
        
        # 返回文件路径（相对路径，前端可以通过静态文件服务访问）
        return {
            "success": True,
            "message": "文字提取成功",
            "file_path": f"/output/downloads/{text_file_path.name}",
            "filename": text_file_path.name,
            "task_id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取视频文字时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
    finally:
        # 如果任务失败，更新状态
        if task_id in task_progress and task_progress[task_id]["status"] != "completed":
            task_progress[task_id].update({
                "status": "error",
                "message": "处理失败"
            })


@app.get("/task/progress/{task_id}")
async def get_task_progress(task_id: str):
    """
    获取任务进度
    """
    if task_id not in task_progress:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task_progress[task_id]


if __name__ == "__main__":
    # 配置 uvicorn 日志，抑制连接关闭相关的错误
    import logging.config
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "asyncio": {
                "level": "CRITICAL",  # 只显示严重错误
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "WARNING",  # 减少访问日志
                "handlers": ["default"],
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"],
        },
    }
    
    # 在启动前设置 asyncio 异常处理器（用于抑制连接关闭错误）
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.set_exception_handler(custom_exception_handler)
    except (RuntimeError, Exception) as e:
        logger.debug(f"设置 asyncio 异常处理器失败: {e}")
    
    # 从环境变量读取端口，默认值：本地开发 5174，Docker 环境 9528
    port = int(os.getenv("PORT", "5174"))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_config=log_config
    )

