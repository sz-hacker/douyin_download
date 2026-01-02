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

    async def analyze_douyin_page(self, url: str) -> List[Dict]:
        logger.info(f"Analyzing URL: {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                '--disable-web-security', '--disable-features=VizDisplayCompositor'
            ])
            context = await browser.new_context(user_agent=USER_AGENT, viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            video_urls, first_douyinvod_url, printed_nav = set(), None, set()
            
            async def handle_response(response):
                url = response.url
                if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.flv', '.webm', '.mov', '.avi']):
                    if not any(skip in url.lower() for skip in ['icon', 'logo', 'bg', 'background', 'thumb', 'preview']):
                        video_urls.add(url)
            
            async def handle_navigation(request):
                nonlocal first_douyinvod_url
                if 'douyinvod.com' in request.url and 'video' in request.url.lower():
                    if first_douyinvod_url is None:
                        first_douyinvod_url = request.url
                        logger.debug(f"First video URL captured: {request.url}")
                    if request.url not in printed_nav:
                        printed_nav.add(request.url)
                        logger.debug(f"Navigation to: {request.url}")

            page.on("response", handle_response)
            page.on("request", handle_navigation)
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=10000)
                logger.debug(f"Final URL: {page.url}")
                await asyncio.sleep(5)

                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(2)
                    for video in await page.query_selector_all("video"):
                        try:
                            await video.click()
                            await asyncio.sleep(1)
                        except:
                            pass
                except:
                    pass

                await asyncio.sleep(3)
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

                if first_douyinvod_url:
                    logger.info("Using first captured video URL")
                    return [self._create_video_item(first_douyinvod_url, 1, "first_captured", "First Captured Video",
                                                   "First douyinvod.com video URL captured during navigation")]

                videos, all_urls = [], set()
                for url in video_urls:
                    if url not in all_urls:
                        all_urls.add(url)
                        videos.append(self._create_video_item(url, len(videos) + 1, "network_intercept",
                                                             f"Network Video {len(videos) + 1}", "Captured from network requests"))

                if video_data:
                    for item in video_data:
                        url = item['url']
                        if url not in all_urls:
                            all_urls.add(url)
                            videos.append(self._create_video_item(url, len(videos) + 1, item['type'],
                                                                 item.get('title', f"Extracted Video {len(videos) + 1}"),
                                                                 f"Source: {item['source']}"))

                logger.info(f"Found {len(videos)} videos")
                return videos
            except Exception as e:
                logger.error(f"Error: {e}")
                if first_douyinvod_url:
                    return [self._create_video_item(first_douyinvod_url, 1, "first_captured", "First Captured Video",
                                                   "First douyinvod.com video URL captured during navigation")]
                return []
            finally:
                await browser.close()





