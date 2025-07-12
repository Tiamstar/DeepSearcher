#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为开发者文档内容爬虫 - 重构版
精简了原始爬虫的功能，保留核心的内容提取和边爬边存功能
"""

import asyncio
import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from playwright.async_api import async_playwright, Page, Browser

from .config import CrawlerConfig, PAGE_TYPE_CONFIGS

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class PageContent:
    """页面内容数据结构"""
    url: str
    title: str
    text_content: str = ""
    code_blocks: List[Dict[str, str]] = None
    metadata: Dict[str, Any] = None
    crawl_time: str = ""
    page_type: str = "unknown"
    content_length: int = 0
    
    def __post_init__(self):
        if self.code_blocks is None:
            self.code_blocks = []
        if self.metadata is None:
            self.metadata = {}
        if not self.crawl_time:
            self.crawl_time = datetime.now().isoformat()
        self.content_length = len(self.text_content)


class ContentExtractionResult:
    """内容提取结果"""
    def __init__(self, content: Optional[PageContent] = None, 
                 should_retry: bool = True, 
                 reason: str = ""):
        self.content = content
        self.should_retry = should_retry
        self.reason = reason
    
    @property
    def success(self) -> bool:
        return self.content is not None
    
    @classmethod
    def success_result(cls, content: PageContent):
        return cls(content=content, should_retry=False, reason="success")
    
    @classmethod
    def insufficient_content(cls, url: str, details: str = ""):
        return cls(content=None, should_retry=False, 
                  reason=f"内容不足，跳过: {details}")
    
    @classmethod
    def technical_error(cls, error: str):
        return cls(content=None, should_retry=True, reason=f"技术错误: {error}")


class HuaweiContentCrawler:
    """华为开发者文档内容爬虫 - 重构版"""
    
    def __init__(self, links_file: str = None, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.links_file = links_file or self.config.LINKS_FILE
        self.crawled_content: Dict[str, PageContent] = {}
        self.failed_urls: List[Dict] = []
        self.skipped_urls: List[Dict] = []
        
        # 边爬边存配置
        self.save_interval = self.config.INCREMENTAL_SAVE_INTERVAL
        self.enable_incremental_save = self.config.ENABLE_INCREMENTAL_SAVE
        self.crawled_count = 0
        self.last_save_count = 0
        self._save_lock = asyncio.Lock()
        
        # 确保目录存在
        self.config.ensure_directories()
    
    def load_links(self) -> List[Dict]:
        """从JSON文件加载链接"""
        try:
            with open(self.links_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            urls = []
            for url, info in data.items():
                urls.append({
                    'url': url,
                    'title': info.get('title', ''),
                    'level': info.get('level', 0)
                })
                self._extract_child_urls(info.get('children', []), urls)
            
            logger.info(f"从 {self.links_file} 加载了 {len(urls)} 个链接")
            return urls
            
        except Exception as e:
            logger.error(f"加载链接文件失败: {e}")
            return []
    
    def _extract_child_urls(self, children: List[Dict], urls: List[Dict]):
        """递归提取子页面URL"""
        for child in children:
            urls.append({
                'url': child.get('url', ''),
                'title': child.get('title', ''),
                'level': child.get('level', 0)
            })
            if child.get('children'):
                self._extract_child_urls(child['children'], urls)
    
    def _detect_page_type(self, url: str) -> str:
        """检测页面类型"""
        url_lower = url.lower()
        if 'api' in url_lower or 'reference' in url_lower:
            return 'api_docs'
        elif 'tutorial' in url_lower or 'guide' in url_lower:
            return 'tutorial'
        return 'unknown'
    
    def _get_page_config(self, page_type: str, url: str) -> Dict:
        """获取页面特定配置"""
        config = {
            'selectors': self.config.CONTENT_SELECTORS,
            'code_selectors': self.config.CODE_SELECTORS,
            'wait_time': self.config.WAIT_FOR_CONTENT_TIMEOUT
        }
        
        if page_type in PAGE_TYPE_CONFIGS:
            type_config = PAGE_TYPE_CONFIGS[page_type]
            config['selectors'] = type_config['selectors'] + config['selectors']
            config['code_selectors'] = type_config['code_selectors'] + config['code_selectors']
            config['wait_time'] = type_config['wait_time']
        
        return config
    
    async def setup_page(self, browser: Browser) -> Page:
        """设置页面"""
        context = await browser.new_context(
            user_agent=self.config.USER_AGENT,
            viewport=self.config.VIEWPORT
        )
        
        page = await context.new_page()
        return page
    
    async def extract_content(self, page: Page, url: str) -> ContentExtractionResult:
        """提取页面内容"""
        page_type = self._detect_page_type(url)
        page_config = self._get_page_config(page_type, url)
        
        try:
            response = await page.goto(
                url, 
                wait_until='domcontentloaded', 
                timeout=self.config.REQUEST_TIMEOUT
            )
            
            if not response or response.status != 200:
                if self.config.FILTER_CONFIG['skip_error_pages']:
                    return ContentExtractionResult.insufficient_content(
                        url, f"HTTP状态码: {response.status if response else 'None'}")
                else:
                    return ContentExtractionResult.technical_error(
                        f"HTTP错误，状态码: {response.status if response else 'None'}")
            
            await page.wait_for_load_state('networkidle', timeout=self.config.REQUEST_TIMEOUT)
            await page.wait_for_timeout(page_config['wait_time'])
            
            title = await page.title()
            
            # 提取页面内容 - 简化版
            content_data = await page.evaluate(f"""
                () => {{
                    const result = {{
                        text_content: '',
                        code_blocks: [],
                        metadata: {{}}
                    }};
                    
                    // 查找主要内容容器
                    const contentSelectors = {page_config['selectors']};
                    let contentContainer = document.body;
                    
                    for (const selector of contentSelectors) {{
                        const container = document.querySelector(selector);
                        if (container) {{
                            contentContainer = container;
                            break;
                        }}
                    }}
                    
                    // 提取文本内容
                    const textElements = {self.config.TEXT_ELEMENTS};
                    const textParts = [];
                    
                    textElements.forEach(tagName => {{
                        const elements = contentContainer.querySelectorAll(tagName);
                        elements.forEach(el => {{
                            const text = el.textContent.trim();
                            if (text && text.length > {self.config.MIN_TEXT_LENGTH}) {{
                                textParts.push(text);
                            }}
                        }});
                    }});
                    
                    result.text_content = textParts.join('\\n\\n');
                    
                    // 提取代码块
                    const codeSelectors = {page_config['code_selectors']};
                    let codeIndex = 0;
                    
                    codeSelectors.forEach(selector => {{
                        try {{
                            const codeElements = document.querySelectorAll(selector);
                            codeElements.forEach(codeEl => {{
                                const code = codeEl.textContent.trim();
                                if (code && code.length > {self.config.MIN_CODE_LENGTH}) {{
                                    let language = 'unknown';
                                    const classMatch = codeEl.className.match(/(?:language-|lang-)([\\w]+)/);
                                    if (classMatch) {{
                                        language = classMatch[1];
                                    }}
                                    
                                    result.code_blocks.push({{
                                        id: codeIndex++,
                                        language: language,
                                        code: code
                                    }});
                                }}
                            }});
                        }} catch(e) {{
                            console.log('Invalid selector:', selector);
                        }}
                    }});
                    
                    // 元数据
                    result.metadata['page_url'] = window.location.href;
                    result.metadata['page_title'] = document.title;
                    
                    return result;
                }}
            """)
            
            # 检查内容质量
            total_content_length = len(content_data['text_content'])
            has_meaningful_content = (
                total_content_length >= self.config.FILTER_CONFIG['min_content_length'] or
                len(content_data['code_blocks']) > 0
            )
            
            if self.config.FILTER_CONFIG['skip_empty_content'] and not has_meaningful_content:
                content_details = f"文本: {total_content_length} 字符, 代码: {len(content_data['code_blocks'])} 个"
                logger.debug(f"⏩ 页面内容不足，跳过: {url} ({content_details})")
                return ContentExtractionResult.insufficient_content(url, content_details)
            
            # 创建PageContent对象
            page_content = PageContent(
                url=url,
                title=title,
                text_content=content_data['text_content'],
                code_blocks=content_data['code_blocks'],
                metadata=content_data['metadata'],
                page_type=page_type
            )
            
            logger.info(f"✅ 成功提取: {url} (类型: {page_type}, 内容: {total_content_length} 字符)")
            return ContentExtractionResult.success_result(page_content)
            
        except Exception as e:
            logger.warning(f"⚠️ 页面访问异常 {url}: {e}")
            return ContentExtractionResult.technical_error(str(e))
    
    async def crawl_with_retry(self, page: Page, url_info: Dict) -> Optional[PageContent]:
        """带重试机制的爬取"""
        url = url_info['url']
        max_retries = self.config.MAX_RETRIES
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.extract_content(page, url)
                
                if result.success:
                    return result.content
                elif not result.should_retry:
                    self.skipped_urls.append({
                        'url': url,
                        'reason': result.reason,
                        'skip_type': 'insufficient_content'
                    })
                    return None
                else:
                    if attempt < max_retries:
                        logger.warning(f"🔄 第 {attempt + 1} 次技术错误，准备重试: {url}")
                        await asyncio.sleep(self.config.RETRY_DELAY)
                    else:
                        self.failed_urls.append({
                            'url': url,
                            'error': result.reason,
                            'attempts': attempt + 1,
                            'failure_type': 'technical_error'
                        })
                        return None
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"🔄 第 {attempt + 1} 次代码异常，准备重试 {url}: {e}")
                    await asyncio.sleep(self.config.RETRY_DELAY)
                else:
                    self.failed_urls.append({
                        'url': url,
                        'error': str(e),
                        'attempts': attempt + 1,
                        'failure_type': 'code_exception'
                    })
                    return None
        
        return None
    
    async def crawl_content(self, urls: List[Dict]) -> Dict[str, PageContent]:
        """批量爬取页面内容"""
        logger.info(f"开始爬取 {len(urls)} 个页面的内容")
        
        self.load_existing_content()
        
        # 过滤已爬取的URL
        urls_to_crawl = [url_info for url_info in urls 
                        if not self.should_skip_url(url_info['url'])]
        already_crawled = len(urls) - len(urls_to_crawl)
        
        if already_crawled > 0:
            logger.info(f"📂 发现 {already_crawled} 个已爬取的页面，跳过")
        
        if not urls_to_crawl:
            logger.info("✅ 所有页面都已爬取完成")
            return self.crawled_content
        
        logger.info(f"📋 需要爬取 {len(urls_to_crawl)} 个新页面")
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=self.config.BROWSER_ARGS
            )
            
            try:
                semaphore = asyncio.Semaphore(self.config.MAX_CONCURRENT)
                
                async def crawl_single_page(url_info: Dict):
                    async with semaphore:
                        if self.should_skip_url(url_info['url']):
                            return
                        
                        page = await self.setup_page(browser)
                        try:
                            content = await self.crawl_with_retry(page, url_info)
                            if content:
                                self.crawled_content[url_info['url']] = content
                                await self.incremental_save()
                            
                            await asyncio.sleep(self.config.DELAY_SECONDS)
                            
                        finally:
                            await page.close()
                
                # 并发爬取
                tasks = [crawl_single_page(url_info) for url_info in urls_to_crawl]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # 最终保存
                await self.incremental_save(force=True)
                
                logger.info(f"爬取完成: 成功 {len(self.crawled_content)} 个，"
                          f"失败 {len(self.failed_urls)} 个，跳过 {len(self.skipped_urls)} 个")
                
                return self.crawled_content
                
            finally:
                await browser.close()
    
    async def incremental_save(self, force: bool = False):
        """增量保存"""
        if not self.enable_incremental_save:
            return
            
        async with self._save_lock:
            current_count = len(self.crawled_content)
            
            if not force and (current_count - self.last_save_count) < self.save_interval:
                return
            
            try:
                # 保存到 processed 目录
                output_path = self.config.PROCESSED_DATA_DIR / self.config.OUTPUT_FILE
                temp_path = output_path.with_suffix('.tmp')
                
                serializable_content = {}
                for url, content in self.crawled_content.items():
                    serializable_content[url] = asdict(content)
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(serializable_content, f, ensure_ascii=False, indent=2)
                
                temp_path.replace(output_path)
                
                # 保存失败和跳过记录
                if self.failed_urls:
                    failed_path = output_path.with_name(f"{output_path.stem}_failed.json")
                    with open(failed_path, 'w', encoding='utf-8') as f:
                        json.dump(self.failed_urls, f, ensure_ascii=False, indent=2)
                
                if self.skipped_urls:
                    skipped_path = output_path.with_name(f"{output_path.stem}_skipped.json")
                    with open(skipped_path, 'w', encoding='utf-8') as f:
                        json.dump(self.skipped_urls, f, ensure_ascii=False, indent=2)
                
                logger.info(f"💾 增量保存: {current_count} 个页面已保存")
                self.last_save_count = current_count
                
            except Exception as e:
                logger.error(f"❌ 增量保存失败: {e}")
    
    def load_existing_content(self):
        """加载已存在的内容"""
        output_path = self.config.PROCESSED_DATA_DIR / self.config.OUTPUT_FILE
        
        if not output_path.exists():
            logger.info("📂 未找到现有内容文件，从头开始爬取")
            return
        
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            for url, data in existing_data.items():
                self.crawled_content[url] = PageContent(
                    url=data['url'],
                    title=data['title'],
                    text_content=data.get('text_content', ''),
                    code_blocks=data.get('code_blocks', []),
                    metadata=data.get('metadata', {}),
                    crawl_time=data.get('crawl_time', ''),
                    page_type=data.get('page_type', 'unknown'),
                    content_length=data.get('content_length', 0)
                )
            
            logger.info(f"📂 加载现有内容: {len(self.crawled_content)} 个页面已存在")
            self.last_save_count = len(self.crawled_content)
            
        except Exception as e:
            logger.error(f"❌ 加载现有内容失败: {e}")
    
    def should_skip_url(self, url: str) -> bool:
        """检查URL是否应该跳过"""
        if url in self.crawled_content:
            return True
        
        for skipped in self.skipped_urls:
            if skipped.get('url') == url:
                return True
        
        return False
    
    def save_content(self, filename: str = None):
        """保存爬取的内容"""
        if filename is None:
            filename = self.config.PROCESSED_DATA_DIR / self.config.OUTPUT_FILE
        
        try:
            serializable_content = {}
            for url, content in self.crawled_content.items():
                serializable_content[url] = asdict(content)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_content, f, ensure_ascii=False, indent=2)
            
            logger.info(f"内容已保存到: {filename}")
            
        except Exception as e:
            logger.error(f"保存内容失败: {e}")
    
    def generate_statistics(self) -> Dict:
        """生成爬取统计信息"""
        total_pages = len(self.crawled_content)
        total_text_length = sum(len(content.text_content) for content in self.crawled_content.values())
        total_code_blocks = sum(len(content.code_blocks) for content in self.crawled_content.values())
        
        return {
            'total_pages': total_pages,
            'total_text_length': total_text_length,
            'total_code_blocks': total_code_blocks,
            'failed_pages': len(self.failed_urls),
            'skipped_pages': len(self.skipped_urls),
            'crawl_time': datetime.now().isoformat()
        } 