#!/usr/bin/env python3
"""Enhanced Douyin Video Downloader"""

import asyncio
import os
import sys
import re
import logging
import requests
import random
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

    def _normalize_url(self, url: str) -> str:
        """规范化URL，去除查询参数以便去重"""
        try:
            parsed = urlparse(url)
            # 只保留scheme, netloc, path，去除query和fragment
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return normalized
        except:
            return url
    
    def _is_valid_video_url(self, url: str) -> bool:
        """检查是否是有效的视频URL"""
        if not url or not isinstance(url, str):
            return False
        url_lower = url.lower()
        # 排除不需要的URL
        skip_words = ['icon', 'logo', 'bg', 'background', 'thumb', 'preview', 'avatar', 'cover', 'uuu_265', 
                     'douyin_pc_client', 'client', 'download', 'install', 'setup']
        has_skip_word = any(skip in url_lower for skip in skip_words)
        if has_skip_word:
            return False
        
        # 优先检查是否是douyinvod.com的视频URL（这是真实的视频URL）
        is_douyin_vod = 'douyinvod.com' in url_lower and 'video' in url_lower
        if is_douyin_vod:
            return True
        
        # 排除特效视频、客户端下载链接和其他非真实视频
        exclude_domains = ['douyinstatic.com', 'byteeffecttos.com', 'effectcdn', 'bytednsdoc.com', 
                          'eden-cn', 'ild_jw']
        if any(domain in url_lower for domain in exclude_domains):
            return False
        
        # 检查是否是视频文件扩展名
        has_video_ext = any(ext in url_lower for ext in ['.mp4', '.m3u8', '.flv', '.webm', '.mov', '.avi'])
        return has_video_ext
    
    def _is_douyinvod_url(self, url: str) -> bool:
        """检查是否是douyinvod.com的真实视频URL"""
        if not url or not isinstance(url, str):
            return False
        url_lower = url.lower()
        return 'douyinvod.com' in url_lower and 'video' in url_lower

    def _get_stealth_js(self) -> str:
        """生成反检测 JavaScript 代码"""
        return """
        (function() {
            // 隐藏 webdriver 特征
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 删除 webdriver 相关属性
            delete navigator.__proto__.webdriver;
            
            // 伪造 Chrome 对象
            if (!window.chrome) {
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
            }
            
            // 伪造权限
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 伪造插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 伪造语言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            
            // 伪造 platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // 伪造硬件并发数
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // 伪造设备内存
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // 隐藏自动化特征 - 覆盖所有可能的检测点
            const props = ['webdriver', '__webdriver_script_fn', '__driver_evaluate', '__webdriver_evaluate', '__selenium_evaluate', '__fxdriver_evaluate', '__driver_unwrapped', '__webdriver_unwrapped', '__selenium_unwrapped', '__fxdriver_unwrapped', '__webdriver_script_func', '__webdriver_script_fn', '__webdriver_script_function'];
            props.forEach(prop => {
                try {
                    delete navigator[prop];
                    delete window[prop];
                } catch(e) {}
            });
            
            // 伪造 WebGL 渲染器
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.call(this, parameter);
            };
            
            // 覆盖 toString 方法，防止检测
            const originalToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === navigator.webdriver || this === window.chrome) {
                    return 'function() { [native code] }';
                }
                return originalToString.call(this);
            };
        })();
        """

    async def analyze_douyin_page(self, url: str) -> List[Dict]:
        logger.info(f"Analyzing URL: {url}")
        async with async_playwright() as p:
            # 增强反检测的启动参数
            logger.info("Launching browser...")
            browser = await p.chromium.launch(
                headless=True, 
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',  # 关键：禁用自动化控制特征
                    '--disable-features=IsolateOrigins,site-per-process',  # 禁用某些特征
                    '--disable-web-security', 
                    '--disable-features=VizDisplayCompositor',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-infobars',
                    '--disable-notifications',
                    '--lang=zh-CN',  # 设置语言
                    '--window-size=1920,1080',  # 设置窗口大小
                    '--start-maximized',  # 最大化窗口
                    '--disable-background-timer-throttling',  # 禁用后台节流
                    '--disable-backgrounding-occluded-windows',  # 禁用后台窗口
                    '--disable-renderer-backgrounding',  # 禁用渲染器后台
                    '--disable-features=TranslateUI',  # 禁用翻译UI
                    '--disable-ipc-flooding-protection',  # 禁用IPC洪水保护
                ]
            )
            logger.info("Browser launched successfully")
            
            # 创建更真实的浏览器上下文
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',  # 设置语言环境
                timezone_id='Asia/Shanghai',  # 设置时区
                permissions=['geolocation', 'notifications'],  # 模拟权限
                color_scheme='light',
                # 添加更多真实的 HTTP 头
                extra_http_headers={
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            page = await context.new_page()
            
            # 在页面加载前注入反检测脚本
            await page.add_init_script(self._get_stealth_js())
            
            logger.info("Page created, setting up event handlers...")
            
            video_urls, first_douyinvod_url, printed_nav = set(), None, set()
            normalized_urls = set()  # 用于去重的规范化URL集合
            total_requests = 0  # 统计总请求数
            total_responses = 0  # 统计总响应数
            douyin_requests = []  # 记录包含 douyin 的请求（用于调试）
            
            async def handle_response(response):
                nonlocal total_responses
                total_responses += 1
                url = response.url
                url_lower = url.lower()
                
                # 记录包含 douyin 的响应（用于调试）
                if 'douyin' in url_lower and total_responses <= 20:  # 只记录前20个，避免日志过多
                    logger.debug(f"Response #{total_responses}: {url[:120]}...")
                
                if self._is_valid_video_url(url):
                    video_urls.add(url)
                    normalized = self._normalize_url(url)
                    normalized_urls.add(normalized)
                    # 如果是 douyinvod.com 的视频，记录日志
                    if self._is_douyinvod_url(url):
                        logger.info(f"Captured douyinvod.com video from response: {url[:100]}...")
            
            async def handle_navigation(request):
                nonlocal first_douyinvod_url, total_requests
                total_requests += 1
                url = request.url
                url_lower = url.lower()
                
                # 记录包含 douyin 的请求（用于调试）
                if 'douyin' in url_lower and total_requests <= 20:  # 只记录前20个
                    douyin_requests.append(url)
                    logger.debug(f"Request #{total_requests}: {url[:120]}...")
                
                # 只捕获 douyinvod.com 的视频URL作为 first_douyinvod_url
                if 'douyinvod.com' in url_lower and 'video' in url_lower:
                    if first_douyinvod_url is None:
                        first_douyinvod_url = url
                        logger.info(f"First video URL captured from request: {url[:120]}...")
                    if url not in printed_nav:
                        printed_nav.add(url)
                        logger.debug(f"Navigation to: {url}")
                # 其他有效的视频URL也记录，但不作为 first_douyinvod_url
                elif self._is_valid_video_url(url):
                    if url not in printed_nav:
                        printed_nav.add(url)
                        logger.debug(f"Other video URL from request: {url[:120]}...")

            page.on("response", handle_response)
            page.on("request", handle_navigation)
            logger.info("Event handlers registered, starting page navigation...")
            
            try:
                # 添加随机延迟，模拟人类行为
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # 在 Docker 环境中，networkidle 可能永远无法满足，使用 load 更可靠
                # 增加超时时间到 60 秒，适应 Docker 环境的网络延迟
                # 如果 load 失败，尝试 domcontentloaded 作为备用
                logger.info(f"Navigating to URL: {url}")
                try:
                    await page.goto(url, wait_until="load", timeout=60000)
                    logger.info(f"Page loaded successfully, Final URL: {page.url}")
                    logger.info(f"Total requests so far: {total_requests}, Total responses so far: {total_responses}")
                except Exception as load_error:
                    logger.warning(f"Load timeout, trying domcontentloaded: {load_error}")
                    # 备用策略：使用 domcontentloaded，这个条件更容易满足
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    logger.info(f"Page domcontentloaded, Final URL: {page.url}")
                    logger.info(f"Total requests so far: {total_requests}, Total responses so far: {total_responses}")
                
                # 等待一段时间让 JavaScript 执行（Docker 环境需要更长时间）
                await asyncio.sleep(random.uniform(2, 3))
                
                # 检查页面标题和内容
                try:
                    page_title = await page.title()
                    logger.info(f"Page title: '{page_title}'")
                    if not page_title or page_title.strip() == '':
                        logger.warning("Page title is empty, page might not be fully loaded or blocked")
                        # 尝试等待更长时间
                        logger.info("Waiting additional time for page to load...")
                        await asyncio.sleep(random.uniform(3, 5))
                        page_title = await page.title()
                        logger.info(f"Page title after additional wait: '{page_title}'")
                except Exception as e:
                    logger.warning(f"Failed to get page title: {e}")
                
                # 检查页面是否有视频元素
                try:
                    video_count = await page.evaluate("document.querySelectorAll('video').length")
                    logger.info(f"Found {video_count} video elements on page")
                    if video_count == 0:
                        logger.warning("No video elements found on page, might be blocked or not loaded")
                        # 尝试等待并重新检查
                        logger.info("Waiting and rechecking video elements...")
                        await asyncio.sleep(random.uniform(3, 5))
                        video_count = await page.evaluate("document.querySelectorAll('video').length")
                        logger.info(f"Found {video_count} video elements after additional wait")
                except Exception as e:
                    logger.warning(f"Failed to count video elements: {e}")
                
                # 检查页面内容，看是否有反爬虫检测
                try:
                    page_text = await page.evaluate("document.body.innerText")
                    if page_text:
                        text_preview = page_text[:200] if len(page_text) > 200 else page_text
                        logger.debug(f"Page content preview: {text_preview}...")
                        # 检查是否有反爬虫提示
                        anti_crawl_keywords = ['验证', '验证码', '安全验证', '人机验证', '访问异常', 'blocked', 'captcha']
                        if any(keyword in page_text for keyword in anti_crawl_keywords):
                            logger.warning("Possible anti-crawl detection detected in page content")
                except Exception as e:
                    logger.debug(f"Failed to get page content: {e}")
                
                # 检查是否有 douyin 相关的请求
                if douyin_requests:
                    logger.info(f"Found {len(douyin_requests)} douyin-related requests")
                    # 检查是否有 douyinvod.com 的请求
                    douyinvod_requests = [req for req in douyin_requests if 'douyinvod.com' in req.lower()]
                    if douyinvod_requests:
                        logger.info(f"Found {len(douyinvod_requests)} douyinvod.com requests: {[req[:100] + '...' if len(req) > 100 else req for req in douyinvod_requests[:3]]}")
                    else:
                        logger.warning(f"No douyinvod.com requests found in {len(douyin_requests)} douyin requests")
                        # 记录一些请求用于调试
                        logger.debug(f"Sample douyin requests: {[req[:150] + '...' if len(req) > 150 else req for req in douyin_requests[:5]]}")
                else:
                    logger.warning("No douyin-related requests captured yet")
                    logger.debug(f"Total requests captured: {total_requests}, Total responses: {total_responses}")
                
                # 等待页面加载完成，给足够时间让视频URL被捕获
                # Docker 环境可能需要更长时间，增加等待次数和间隔
                max_wait_attempts = 12  # Docker 环境需要更多等待
                wait_interval = 5  # 增加等待间隔
                
                logger.info(f"Starting wait loop (max {max_wait_attempts} attempts, {wait_interval}s each)...")
                for attempt in range(max_wait_attempts):
                    # 添加随机延迟，模拟人类行为
                    await asyncio.sleep(wait_interval + random.uniform(-0.5, 0.5))
                    elapsed_time = (attempt + 1) * wait_interval
                    
                    # 检查是否已经捕获到 douyinvod.com 的视频
                    if first_douyinvod_url:
                        logger.info(f"Douyinvod.com video URL captured after {elapsed_time}s")
                        break
                    
                    # 检查响应中是否有 douyinvod.com 的视频
                    douyinvod_in_responses = [url for url in video_urls if self._is_douyinvod_url(url)]
                    if douyinvod_in_responses:
                        logger.info(f"Found {len(douyinvod_in_responses)} douyinvod.com video(s) in responses after {elapsed_time}s")
                        break
                    
                    # 检查是否有新的 douyinvod.com 请求
                    current_douyinvod_requests = [req for req in douyin_requests if 'douyinvod.com' in req.lower() and 'video' in req.lower()]
                    
                    # 记录当前状态（用于调试）
                    logger.info(f"Wait attempt {attempt + 1}/{max_wait_attempts}: "
                              f"Total requests: {total_requests}, Total responses: {total_responses}, "
                              f"Video URLs found: {len(video_urls)}, "
                              f"Douyinvod.com videos: {len([u for u in video_urls if self._is_douyinvod_url(u)])}, "
                              f"Douyinvod.com requests: {len(current_douyinvod_requests)}")
                    
                    # 如果还没有任何视频URL，记录一些请求信息（用于调试）
                    if len(video_urls) == 0:
                        if attempt == 2 and douyin_requests:
                            logger.warning(f"No video URLs found yet. Sample douyin requests: {[req[:100] + '...' if len(req) > 100 else req for req in douyin_requests[:3]]}")
                        if current_douyinvod_requests and not first_douyinvod_url:
                            logger.warning(f"Found {len(current_douyinvod_requests)} douyinvod.com requests but no video URL captured yet. "
                                         f"Sample: {[req[:120] + '...' if len(req) > 120 else req for req in current_douyinvod_requests[:2]]}")
                
                # 如果还没有捕获到 first_douyinvod_url，尝试滚动和点击视频
                if not first_douyinvod_url:
                    logger.info("No douyinvod.com video captured yet, trying to interact with page")
                    try:
                        # 先检查页面是否可滚动
                        scroll_height = await page.evaluate("document.body.scrollHeight")
                        viewport_height = await page.evaluate("window.innerHeight")
                        logger.info(f"Page scroll info: scrollHeight={scroll_height}, viewportHeight={viewport_height}")
                        
                        # 模拟人类滚动行为（随机速度）
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(random.uniform(1.5, 2.5))
                        await page.evaluate("window.scrollTo(0, 0)")
                        await asyncio.sleep(random.uniform(1.5, 2.5))
                        
                        video_elements = await page.query_selector_all("video")
                        logger.info(f"Found {len(video_elements)} video elements on page after scroll")
                        
                        if video_elements:
                            for idx, video in enumerate(video_elements):
                                try:
                                    logger.info(f"Clicking video element {idx + 1}/{len(video_elements)}")
                                    await video.click()
                                    await asyncio.sleep(random.uniform(4, 6))  # 随机延迟，模拟人类行为
                                    
                                    # 检查点击后是否有新的请求
                                    new_requests_before = total_requests
                                    await asyncio.sleep(random.uniform(2, 4))
                                    new_requests_after = total_requests
                                    if new_requests_after > new_requests_before:
                                        logger.info(f"New requests after video click: {new_requests_after - new_requests_before}")
                                    
                                    # 再次检查是否捕获到视频URL
                                    if first_douyinvod_url:
                                        logger.info("Video URL captured after clicking video element")
                                        break
                                except Exception as e:
                                    logger.debug(f"Error clicking video element {idx + 1}: {e}")
                        else:
                            logger.warning("No video elements found to click")
                    except Exception as e:
                        logger.warning(f"Error interacting with page: {e}")
                    
                    # 等待交互后的网络请求
                    logger.info("Waiting after page interaction for video URLs to load...")
                    await asyncio.sleep(random.uniform(7, 9))  # 随机延迟
                    
                    # 如果还没有捕获到，尝试从页面 JavaScript 中提取视频 URL（备用方案）
                    if not first_douyinvod_url:
                        logger.info("Trying to extract video URL from page JavaScript as fallback...")
                        try:
                            # 尝试从页面 JavaScript 中提取视频 URL（更全面的提取逻辑）
                            js_video_url = await page.evaluate("""
                                () => {
                                    // 方法1: 尝试从 window 对象中提取
                                    const windowObjs = ['__INITIAL_STATE__', '__NUXT__', '__NEXT_DATA__', '_SSR_HYDRATED_DATA'];
                                    for (const objName of windowObjs) {
                                        try {
                                            const obj = window[objName];
                                            if (obj) {
                                                const jsonStr = JSON.stringify(obj);
                                                // 匹配 douyinvod.com 的视频 URL
                                                const matches = jsonStr.match(/https?:\\/\\/[^"\\s]*douyinvod\\.com[^"\\s]*video[^"\\s]*/g);
                                                if (matches && matches.length > 0) {
                                                    return matches[0];
                                                }
                                            }
                                        } catch (e) {}
                                    }
                                    
                                    // 方法2: 尝试从所有 script 标签中提取
                                    const scripts = document.querySelectorAll('script');
                                    for (const script of scripts) {
                                        const content = script.textContent || script.innerHTML;
                                        if (content && content.includes('douyinvod.com') && content.includes('video')) {
                                            const matches = content.match(/https?:\\/\\/[^"\\s]*douyinvod\\.com[^"\\s]*video[^"\\s]*/g);
                                            if (matches && matches.length > 0) {
                                                return matches[0];
                                            }
                                        }
                                    }
                                    
                                    // 方法3: 尝试从 video 元素的 src 或 currentSrc 属性获取
                                    const videos = document.querySelectorAll('video');
                                    for (const video of videos) {
                                        const src = video.src || video.currentSrc || video.getAttribute('src');
                                        if (src && src.includes('douyinvod.com')) {
                                            return src;
                                        }
                                    }
                                    
                                    // 方法4: 尝试从 performance API 中获取
                                    try {
                                        const resources = performance.getEntriesByType('resource');
                                        for (const resource of resources) {
                                            if (resource.name && resource.name.includes('douyinvod.com') && resource.name.includes('video')) {
                                                return resource.name;
                                            }
                                        }
                                    } catch (e) {}
                                    
                                    return null;
                                }
                            """)
                            
                            if js_video_url and self._is_douyinvod_url(js_video_url):
                                first_douyinvod_url = js_video_url
                                logger.info(f"Extracted douyinvod.com video URL from JavaScript: {js_video_url[:120]}...")
                        except Exception as e:
                            logger.debug(f"Failed to extract video URL from JavaScript: {e}")
                    
                    # 再次检查状态
                    logger.info(f"After interaction: Total requests: {total_requests}, Total responses: {total_responses}, "
                              f"Video URLs: {len(video_urls)}, "
                              f"Douyinvod.com videos: {len([u for u in video_urls if self._is_douyinvod_url(u)])}")
                
                # 最终检查
                logger.info(f"Final statistics: Total requests: {total_requests}, Total responses: {total_responses}, "
                          f"Video URLs captured: {len(video_urls)}")
                
                if first_douyinvod_url:
                    logger.info(f"Douyinvod.com video URL captured after page interaction")
                else:
                    # 检查是否有 douyinvod.com 的视频在 video_urls 中
                    douyinvod_in_responses = [url for url in video_urls if self._is_douyinvod_url(url)]
                    if douyinvod_in_responses:
                        logger.info(f"Found {len(douyinvod_in_responses)} douyinvod.com video(s) in responses")
                    else:
                        # 记录一些无效的 URL 用于调试（只记录前3个，避免日志过长）
                        invalid_urls = [url for url in list(video_urls)[:3] if not self._is_douyinvod_url(url)]
                        if invalid_urls:
                            logger.warning(f"No douyinvod.com video found. Sample invalid URLs: {[url[:80] + '...' if len(url) > 80 else url for url in invalid_urls]}")
                        else:
                            logger.warning(f"No douyinvod.com video found, found {len(video_urls)} total video URLs")
                            # 如果没有任何视频URL，记录一些请求信息
                            if len(video_urls) == 0:
                                logger.warning(f"No video URLs captured at all. This might indicate:")
                                logger.warning(f"  1. Page didn't load properly")
                                logger.warning(f"  2. Network requests were blocked")
                                logger.warning(f"  3. Video URL format changed")
                                if douyin_requests:
                                    logger.warning(f"Sample douyin requests captured: {len(douyin_requests)}")
                                    logger.warning(f"First few: {douyin_requests[:3]}")
                                else:
                                    logger.warning(f"No douyin-related requests captured at all")
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

                # 优先使用 first_douyinvod_url，如果存在则只返回它
                if first_douyinvod_url:
                    logger.info(f"Using first captured douyinvod.com video URL")
                    return [self._create_video_item(first_douyinvod_url, 1, "first_captured", "First Captured Video",
                                                   "First douyinvod.com video URL captured during navigation")]

                # 收集所有视频URL，使用规范化URL去重
                videos, all_urls = [], set()
                douyinvod_videos = []  # 专门存储 douyinvod.com 的视频
                invalid_urls = []  # 记录被过滤的无效 URL（用于调试）
                
                # 首先处理网络拦截的视频URL
                for url in video_urls:
                    # 检查是否是有效的视频 URL
                    if not self._is_valid_video_url(url):
                        # 记录被过滤的无效 URL（只记录前3个，避免日志过长）
                        if len(invalid_urls) < 3:
                            invalid_urls.append(url)
                        continue
                    
                    normalized = self._normalize_url(url)
                    if normalized not in all_urls:
                        all_urls.add(normalized)
                        video_item = self._create_video_item(url, len(videos) + 1, "network_intercept",
                                                             f"Network Video {len(videos) + 1}", "Captured from network requests")
                        videos.append(video_item)
                        # 如果是 douyinvod.com 的视频，单独记录
                        if self._is_douyinvod_url(url):
                            douyinvod_videos.append(video_item)
                            logger.info(f"Found douyinvod.com video from network: {url[:100]}...")
                        else:
                            logger.debug(f"Found other video from network: {url[:80]}...")

                # 然后处理从页面提取的视频URL
                if video_data:
                    logger.debug(f"Processing {len(video_data)} extracted video items from page")
                    for item in video_data:
                        url = item.get('url', '')
                        if not url:
                            continue
                        # 检查是否是有效的视频 URL
                        if not self._is_valid_video_url(url):
                            # 记录被过滤的无效 URL（只记录前3个）
                            if len(invalid_urls) < 3:
                                invalid_urls.append(url)
                            continue
                        normalized = self._normalize_url(url)
                        if normalized not in all_urls:
                            all_urls.add(normalized)
                            video_item = self._create_video_item(url, len(videos) + 1, item.get('type', 'unknown'),
                                                                 item.get('title', f"Extracted Video {len(videos) + 1}"),
                                                                 f"Source: {item.get('source', 'unknown')}")
                            videos.append(video_item)
                            # 如果是 douyinvod.com 的视频，单独记录
                            if self._is_douyinvod_url(url):
                                douyinvod_videos.append(video_item)
                                logger.info(f"Found douyinvod.com video from page: {url[:100]}...")
                            else:
                                logger.debug(f"Found other video from page: {url[:80]}...")
                
                # 如果有被过滤的无效 URL，记录日志（用于调试）
                if invalid_urls:
                    logger.debug(f"Filtered {len(invalid_urls)} invalid video URLs (sample): {[url[:80] + '...' if len(url) > 80 else url for url in invalid_urls]}")

                # 优先返回 douyinvod.com 的视频
                if douyinvod_videos:
                    logger.info(f"Found {len(douyinvod_videos)} douyinvod.com video(s) out of {len(videos)} total, returning the first douyinvod.com video")
                    return [douyinvod_videos[0]]
                
                # 如果没有 douyinvod.com 的视频，返回第一个有效视频
                if videos:
                    logger.warning(f"Found {len(videos)} videos but no douyinvod.com video, returning the first one: {videos[0]['src'][:80]}...")
                    return [videos[0]]
                
                logger.info(f"Found {len(videos)} videos")
                return videos
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                # 即使出错，也尝试返回已捕获的视频URL
                if first_douyinvod_url:
                    logger.info("Returning first captured douyinvod.com video URL despite error")
                    return [self._create_video_item(first_douyinvod_url, 1, "first_captured", "First Captured Video",
                                                   "First douyinvod.com video URL captured during navigation")]
                # 如果有网络拦截的视频URL，优先选择 douyinvod.com 的
                douyinvod_urls = [url for url in video_urls if self._is_douyinvod_url(url)]
                if douyinvod_urls:
                    first_url = douyinvod_urls[0]
                    logger.info(f"Returning first douyinvod.com video URL from network intercept: {first_url[:80]}...")
                    return [self._create_video_item(first_url, 1, "network_intercept", "Network Video",
                                                   "Captured from network requests")]
                # 如果没有 douyinvod.com 的视频，返回第一个
                if video_urls:
                    first_url = next(iter(video_urls))
                    logger.warning(f"Returning first network intercepted video URL (not douyinvod.com): {first_url[:80]}...")
                    return [self._create_video_item(first_url, 1, "network_intercept", "Network Video",
                                                   "Captured from network requests")]
                return []
            finally:
                await browser.close()





