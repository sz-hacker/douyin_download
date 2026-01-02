#!/usr/bin/env python3
"""Enhanced Douyin Video Downloader"""

import asyncio
import os
import sys
import re
import logging
import requests
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from typing import List, Dict, Optional

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 创建日志记录器
logger = logging.getLogger(__name__)

class EnhancedDouyinDownloader:
    def __init__(self, downloads_dir: str = None):
        if downloads_dir is None:
            self.downloads_dir = "output/downloads"
        else:
            self.downloads_dir = downloads_dir
        os.makedirs(self.downloads_dir, exist_ok=True)

    def _create_video_item(self, url: str, index: int, vtype: str, title: str = None, desc: str = None) -> Dict:
        return {
            "index": index,
            "type": vtype,
            "src": url,
            "title": title or f"Video {index}",
            "description": desc or f"Source: {vtype}"
        }

    async def analyze_douyin_page(self, url: str, timeout: int = 60000) -> List[Dict]:
        """
        分析抖音页面，提取视频链接
        
        Args:
            url: 抖音视频链接
            timeout: 页面加载超时时间（毫秒），默认 60 秒
            
        Returns:
            视频信息列表
        """
        logger.info(f"开始分析页面: {url}")
        logger.info(f"超时设置: {timeout}ms ({timeout/1000:.1f}秒)")
        
        async with async_playwright() as p:
            logger.info("正在初始化 Playwright...")
            logger.debug("启动 Chromium 浏览器...")
            start_time = asyncio.get_event_loop().time()
            browser = await p.chromium.launch(headless=True, args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-web-security', 
                '--disable-features=VizDisplayCompositor',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-gpu',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-ipc-flooding-protection'
            ])
            browser_start_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"浏览器启动成功，耗时: {browser_start_time:.2f}秒")
            
            logger.debug("创建浏览器上下文...")
            context = await browser.new_context(
                user_agent=USER_AGENT, 
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            logger.debug(f"浏览器上下文创建成功，User-Agent: {USER_AGENT[:50]}...")
            
            logger.debug("创建新页面...")
            page = await context.new_page()
            logger.debug("页面创建成功")
            
            # 设置页面超时
            logger.debug(f"设置页面超时: {timeout}ms")
            page.set_default_timeout(timeout)
            page.set_default_navigation_timeout(timeout)
            logger.debug("页面超时设置完成")
            
            video_urls, first_douyinvod_url, printed_nav = set(), None, set()
            network_errors = []
            
            async def handle_response(response):
                try:
                    url = response.url
                    status = response.status
                    content_type = response.headers.get('content-type', '')
                    
                    # 记录所有响应（调试用）
                    if status >= 400:
                        logger.debug(f"HTTP {status} 响应: {url[:100]}... (Content-Type: {content_type})")
                    
                    # 检查是否是视频文件
                    if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.flv', '.webm', '.mov', '.avi']):
                        if not any(skip in url.lower() for skip in ['icon', 'logo', 'bg', 'background', 'thumb', 'preview']):
                            if url not in video_urls:
                                video_urls.add(url)
                                logger.info(f"✓ 发现视频 URL (状态码: {status}): {url[:100]}...")
                            else:
                                logger.debug(f"视频 URL 已存在，跳过: {url[:100]}...")
                except Exception as e:
                    logger.warning(f"处理响应时出错: {str(e)}", exc_info=True)
            
            async def handle_navigation(request):
                nonlocal first_douyinvod_url
                try:
                    request_url = request.url
                    method = request.method
                    
                    # 记录所有导航请求（调试用）
                    if 'douyin' in request_url.lower():
                        logger.debug(f"导航请求: {method} {request_url[:100]}...")
                    
                    if 'douyinvod.com' in request_url and 'video' in request_url.lower():
                        if first_douyinvod_url is None:
                            first_douyinvod_url = request_url
                            logger.info(f"✓ 捕获到第一个视频 URL (导航拦截): {request_url}")
                        if request_url not in printed_nav:
                            printed_nav.add(request_url)
                            logger.debug(f"导航到视频 URL: {request_url[:100]}...")
                except Exception as e:
                    logger.warning(f"处理导航请求时出错: {str(e)}", exc_info=True)
            
            async def handle_request_failed(request):
                """处理请求失败"""
                try:
                    error_info = {
                        'url': request.url,
                        'method': request.method,
                        'failure': request.failure
                    }
                    network_errors.append(error_info)
                    logger.warning(f"✗ 请求失败: {request.method} {request.url[:100]}... - {request.failure}")
                    logger.debug(f"   完整 URL: {request.url}")
                except Exception as e:
                    logger.warning(f"处理请求失败事件时出错: {str(e)}", exc_info=True)
            
            logger.info("注册页面事件监听器...")
            page.on("response", handle_response)
            page.on("request", handle_navigation)
            page.on("requestfailed", handle_request_failed)
            logger.debug("事件监听器注册完成")
            
            try:
                    logger.info(f"正在导航到页面: {url}")
                    navigation_start = asyncio.get_event_loop().time()
                    # 增加超时时间，并改用 load 策略（更宽松）
                    await page.goto(url, wait_until="load", timeout=timeout)
                    navigation_time = asyncio.get_event_loop().time() - navigation_start
                    final_url = page.url
                    logger.info(f"页面加载完成，耗时: {navigation_time:.2f}秒")
                    logger.info(f"最终 URL: {final_url}")
                    
                    # 检查页面标题和内容
                    try:
                        title = await page.title()
                        logger.info(f"页面标题: {title}")
                    except Exception as e:
                        logger.debug(f"获取页面标题失败: {str(e)}")
                    
                    # 检查页面内容
                    try:
                        body_text_length = await page.evaluate("document.body ? document.body.innerText.length : 0")
                        logger.debug(f"页面内容长度: {body_text_length} 字符")
                    except Exception as e:
                        logger.debug(f"获取页面内容长度失败: {str(e)}")
                    
                    logger.debug("等待页面稳定 (5秒)...")
                    await asyncio.sleep(5)
                    logger.debug("页面稳定等待完成")
                    
                    # 尝试滚动页面和点击视频元素
                    logger.debug("开始交互页面（滚动和点击视频元素）...")
                    try:
                        video_elements_count = len(await page.query_selector_all("video"))
                        logger.debug(f"页面中找到 {video_elements_count} 个 video 元素")
                        
                        logger.debug("向下滚动页面...")
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                        logger.debug("向上滚动页面...")
                        await page.evaluate("window.scrollTo(0, 0)")
                        await asyncio.sleep(2)
                        
                        clicked_count = 0
                        for i, video in enumerate(await page.query_selector_all("video"), 1):
                            try:
                                logger.debug(f"尝试点击第 {i} 个视频元素...")
                                await video.click()
                                clicked_count += 1
                                await asyncio.sleep(1)
                            except Exception as e:
                                logger.debug(f"点击第 {i} 个视频元素失败: {str(e)}")
                        logger.debug(f"成功点击 {clicked_count} 个视频元素")
                    except Exception as e:
                        logger.warning(f"页面交互过程中出错: {str(e)}")
                    
                    logger.debug("等待视频加载 (3秒)...")
                    await asyncio.sleep(3)
                    logger.debug("等待完成")
                    
                    logger.info("开始执行页面脚本，提取视频信息...")
                    script_start = asyncio.get_event_loop().time()
                    video_data = await page.evaluate("""
                        () => {
                            const videos = [], skipWords = ['icon', 'logo', 'bg'];
                            const windowObjs = ['__INITIAL_STATE__', '__NUXT__', '__NEXT_DATA__', 'window._SSR_HYDRATED_DATA'];
                            for (const objName of windowObjs) {
                                try {
                                    const obj = window[objName];
                                    if (obj) {
                                        const matches = JSON.stringify(obj).match(/https?:\\/\\/[^"\\s]+\\/([^"\\s]*\\.mp4[^"\\s]*)/g);
                                        if (matches) matches.forEach(url => {
                                            if (!skipWords.some(w => url.includes(w))) {
                                                videos.push({url, source: objName, type: 'window_object'});
                                            }
                                        });
                                    }
                                } catch (e) {}
                            }
                            document.querySelectorAll('script').forEach(script => {
                                const content = script.textContent || '';
                                if (content.includes('play_addr') || content.includes('video_id') || content.includes('douyin')) {
                                    const urlMatches = content.match(/https?:\\/\\/[^"\\s]+\\/([^"\\s]*\\.mp4[^"\\s]*)/g);
                                    if (urlMatches) urlMatches.forEach(url => {
                                        if (!skipWords.some(w => url.includes(w))) {
                                            videos.push({url, source: 'script_content', type: 'script_extraction'});
                                        }
                                    });
                                    try {
                                        const jsonMatches = content.match(/\\{[^{}]*"play_addr"[^{}]*\\}/g);
                                        if (jsonMatches) jsonMatches.forEach(match => {
                                            try {
                                                const data = JSON.parse(match);
                                                if (data.play_addr?.url_list) {
                                                    data.play_addr.url_list.forEach(url => {
                                                        videos.push({
                                                            url, source: 'json_data', type: 'api_extraction',
                                                            title: data.desc || 'Douyin Video'
                                                        });
                                                    });
                                                }
                                            } catch (e) {}
                                        });
                                    } catch (e) {}
                                }
                            });
                            document.querySelectorAll('video').forEach(video => {
                                const src = video.src || video.currentSrc;
                                if (src?.includes('.mp4')) videos.push({url: src, source: 'video_element', type: 'html_element'});
                            });
                            return videos;
                        }
                    """)
                    script_time = asyncio.get_event_loop().time() - script_start
                    video_count = len(video_data) if video_data else 0
                    logger.info(f"页面脚本执行完成，耗时: {script_time:.2f}秒，从页面提取到 {video_count} 个视频 URL")
                    
                    if video_data:
                        logger.debug("提取到的视频来源统计:")
                        sources = {}
                        for item in video_data:
                            source = item.get('source', 'unknown')
                            sources[source] = sources.get(source, 0) + 1
                        for source, count in sources.items():
                            logger.debug(f"  - {source}: {count} 个")
                    
                    # 汇总所有找到的视频
                    logger.info("开始汇总所有找到的视频...")
                    if first_douyinvod_url:
                        logger.info(f"✓ 使用导航过程中捕获的第一个视频 URL: {first_douyinvod_url[:100]}...")
                        return [self._create_video_item(first_douyinvod_url, 1, "first_captured", "First Captured Video", 
                                                       "First douyinvod.com video URL captured during navigation")]
                    
                    videos, all_urls = [], set()
                    
                    # 添加网络拦截到的视频
                    logger.info(f"处理网络拦截到的视频 URL ({len(video_urls)} 个)...")
                    for i, url in enumerate(video_urls, 1):
                        if url not in all_urls:
                            all_urls.add(url)
                            videos.append(self._create_video_item(url, len(videos) + 1, "network_intercept", 
                                                                 f"Network Video {len(videos) + 1}", "Captured from network requests"))
                            logger.debug(f"  添加视频 {i}: {url[:100]}...")
                    logger.info(f"从网络拦截添加了 {len([v for v in videos if v['type'] == 'network_intercept'])} 个视频")
                    
                    # 添加从页面提取的视频
                    if video_data:
                        logger.info(f"处理页面提取到的视频 URL ({len(video_data)} 个)...")
                        added_count = 0
                        for item in video_data:
                            url = item['url']
                            if url not in all_urls:
                                all_urls.add(url)
                                videos.append(self._create_video_item(url, len(videos) + 1, item['type'], 
                                                                     item.get('title', f"Extracted Video {len(videos) + 1}"), 
                                                                     f"Source: {item['source']}"))
                                added_count += 1
                                logger.debug(f"  添加视频 (来源: {item.get('source', 'unknown')}): {url[:100]}...")
                        logger.info(f"从页面提取添加了 {added_count} 个视频")
                    
                    if not videos:
                        logger.warning("未找到任何视频，可能的原因：")
                        logger.warning(f"  1. 网络拦截到的视频 URL 数量: {len(video_urls)}")
                        logger.warning(f"  2. 页面提取到的视频 URL 数量: {len(video_data) if video_data else 0}")
                        logger.warning(f"  3. 导航捕获的视频 URL: {first_douyinvod_url or '无'}")
                        if network_errors:
                            logger.warning(f"  4. 网络请求失败数量: {len(network_errors)}")
                            for i, error in enumerate(network_errors[:5], 1):  # 只显示前5个错误
                                logger.warning(f"     错误 {i}: {error.get('method')} {error.get('url')} - {error.get('failure')}")
                        
                        # 尝试保存页面截图用于调试（仅在 Docker 环境中）
                        try:
                            screenshot_path = "/app/output/debug_screenshot.png"
                            await page.screenshot(path=screenshot_path, full_page=True)
                            logger.info(f"已保存页面截图到: {screenshot_path} (用于调试)")
                        except Exception as screenshot_error:
                            logger.debug(f"保存截图失败: {str(screenshot_error)}")
                    
                    logger.info(f"分析完成，共找到 {len(videos)} 个视频")
                    return videos
                    
            except asyncio.TimeoutError as e:
                logger.error(f"页面加载超时 ({timeout/1000:.1f}秒): {str(e)}")
                logger.error(f"  目标 URL: {url}")
                logger.error("  可能的原因：")
                logger.error("    1. 网络连接不稳定或速度慢")
                logger.error("    2. 抖音服务器响应慢")
                logger.error("    3. 需要更长的超时时间")
                logger.error("    4. 链接可能已失效或需要登录")
                if first_douyinvod_url:
                    logger.info(f"但在超时前捕获到视频 URL，返回: {first_douyinvod_url}")
                    return [self._create_video_item(first_douyinvod_url, 1, "first_captured", "First Captured Video",
                                                   "First douyinvod.com video URL captured during navigation (timeout occurred)")]
                return []
            except Exception as e:
                logger.error(f"分析页面时发生错误: {str(e)}", exc_info=True)
                logger.error(f"  错误类型: {type(e).__name__}")
                logger.error(f"  目标 URL: {url}")
                if first_douyinvod_url:
                    logger.info(f"但在错误发生前捕获到视频 URL，返回: {first_douyinvod_url}")
                    return [self._create_video_item(first_douyinvod_url, 1, "first_captured", "First Captured Video",
                                                   "First douyinvod.com video URL captured during navigation (error occurred)")]
                return []
            finally:
                try:
                    await browser.close()
                    logger.debug("浏览器已关闭")
                except Exception as e:
                    logger.warning(f"关闭浏览器时出错: {str(e)}")





