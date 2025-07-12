"""
FireCrawl高级配置 - 充分利用Firecrawl的强大功能
专门针对华为文档优化
"""

from firecrawl import FirecrawlApp, ScrapeOptions
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class AdvancedFirecrawlConfig:
    """FireCrawl高级配置类"""
    
    @staticmethod
    def get_huawei_optimized_scrape_options() -> ScrapeOptions:
        """
        获取针对华为网站优化的爬取选项
        
        Returns:
            优化的ScrapeOptions配置
        """
        return ScrapeOptions(
            formats=['markdown', 'html', 'links', 'screenshot'],  # 多格式输出
            only_main_content=True,  # 只提取主要内容
            wait_for=3000,  # 等待3秒确保内容加载完成
            timeout=45000,  # 45秒超时
            
            # 高级选项
            include_tags=['article', 'main', 'section', 'div.content', 'div.doc-content'],
            exclude_tags=['nav', 'footer', 'aside', 'header', '.sidebar', '.advertisement'],
            
            # 移除不需要的元素
            remove_tags=['script', 'style', 'noscript', 'iframe'],
            
            # 华为网站特定的CSS选择器
            include_selectors=[
                '.doc-content',
                '.article-content', 
                '.guide-content',
                '.api-doc',
                'main',
                '[role="main"]'
            ],
            
            exclude_selectors=[
                '.sidebar',
                '.navigation',
                '.breadcrumb',
                '.footer',
                '.header',
                '.advertisement',
                '.related-links'
            ]
        )
    
    @staticmethod
    def get_general_optimized_scrape_options() -> ScrapeOptions:
        """
        获取通用网站的优化爬取选项
        
        Returns:
            通用优化的ScrapeOptions配置
        """
        return ScrapeOptions(
            formats=['markdown', 'links'],  # 减少格式以提高速度
            only_main_content=True,
            wait_for=2000,
            timeout=30000,
            
            # 通用内容选择器
            include_tags=['article', 'main', 'section'],
            exclude_tags=['nav', 'footer', 'aside', 'header'],
            remove_tags=['script', 'style', 'noscript']
        )
    
    @staticmethod
    def get_crawl_options_for_huawei_docs() -> Dict[str, Any]:
        """
        获取华为文档站点的爬取选项
        
        Returns:
            爬取配置字典
        """
        return {
            'limit': 50,  # 最多爬取50个页面
            'max_depth': 3,  # 最大深度3层
            'allow_backward_links': False,  # 不允许向上爬取
            'scrape_options': ScrapeOptions(
                formats=['markdown', 'links'],
                only_main_content=True,
                wait_for=2000,
                timeout=35000,
                
                # 华为文档特定优化
                include_selectors=[
                    '.doc-content',
                    '.guide-content', 
                    '.api-reference',
                    'article',
                    'main'
                ],
                
                exclude_selectors=[
                    '.sidebar',
                    '.toc',
                    '.breadcrumb',
                    '.footer',
                    '.header'
                ]
            ),
            'poll_interval': 3  # 每3秒检查一次爬取状态
        }
    
    @staticmethod
    def get_search_options_for_huawei() -> Dict[str, Any]:
        """
        获取华为相关搜索的优化选项
        
        Returns:
            搜索配置字典
        """
        return {
            'limit': 10,
            'location': 'China',  # 中国地区优化
            'tbs': None,  # 不限制时间
            'timeout': 60000,  # 60秒超时
            'ignore_invalid_urls': True,  # 忽略无效URL
            'scrape_options': ScrapeOptions(
                formats=['markdown', 'links'],
                only_main_content=True,
                wait_for=2500,
                timeout=40000,
                
                # 针对搜索结果页面的优化
                include_tags=['article', 'main', 'section', '.content'],
                exclude_tags=['nav', 'footer', 'aside', '.sidebar'],
                
                # 华为相关内容的特殊处理
                include_selectors=[
                    '.doc-content',
                    '.developer-content',
                    '.guide-section',
                    'main',
                    '[role="main"]'
                ]
            )
        }
    
    @staticmethod
    def get_actions_for_dynamic_content() -> List[Dict[str, Any]]:
        """
        获取处理动态内容的动作序列
        适用于需要交互的华为开发者页面
        
        Returns:
            动作序列列表
        """
        return [
            {"type": "wait", "milliseconds": 3000},  # 等待页面加载
            {"type": "scroll", "direction": "down", "amount": 3},  # 向下滚动触发懒加载
            {"type": "wait", "milliseconds": 2000},  # 等待内容加载
            {"type": "click", "selector": ".expand-content", "optional": True},  # 展开内容（如果存在）
            {"type": "wait", "milliseconds": 1000},
            {"type": "scrape"}  # 执行爬取
        ]
    
    @staticmethod
    def get_extract_schema_for_huawei_api() -> Dict[str, Any]:
        """
        获取华为API文档的结构化提取模式
        
        Returns:
            提取模式配置
        """
        return {
            "api_name": "string",
            "description": "string", 
            "parameters": [
                {
                    "name": "string",
                    "type": "string",
                    "required": "boolean",
                    "description": "string"
                }
            ],
            "return_type": "string",
            "example_code": "string",
            "supported_platforms": ["string"],
            "minimum_version": "string"
        }
    
    @staticmethod
    def create_advanced_firecrawl_app(api_key: str) -> FirecrawlApp:
        """
        创建配置优化的FireCrawl应用实例
        
        Args:
            api_key: FireCrawl API密钥
            
        Returns:
            配置好的FirecrawlApp实例
        """
        try:
            app = FirecrawlApp(api_key=api_key)
            logger.info("✅ FireCrawl高级应用实例创建成功")
            return app
        except Exception as e:
            logger.error(f"❌ FireCrawl应用实例创建失败: {e}")
            raise

# 使用示例
class HuaweiDocumentCrawler:
    """华为文档专用爬虫"""
    
    def __init__(self, api_key: str):
        self.app = AdvancedFirecrawlConfig.create_advanced_firecrawl_app(api_key)
        self.config = AdvancedFirecrawlConfig()
    
    def scrape_huawei_doc_page(self, url: str):
        """爬取华为文档页面"""
        try:
            scrape_options = self.config.get_huawei_optimized_scrape_options()
            
            result = self.app.scrape_url(
                url=url,
                **scrape_options.model_dump()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 爬取华为文档页面失败: {e}")
            return None
    
    def crawl_huawei_doc_site(self, base_url: str):
        """爬取整个华为文档站点"""
        try:
            crawl_options = self.config.get_crawl_options_for_huawei_docs()
            
            result = self.app.crawl_url(
                url=base_url,
                **crawl_options
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 爬取华为文档站点失败: {e}")
            return None
    
    def search_huawei_content(self, query: str):
        """搜索华为相关内容"""
        try:
            search_options = self.config.get_search_options_for_huawei()
            
            # 优化搜索查询
            optimized_queries = [
                f"{query} site:developer.huawei.com",
                f"{query} site:developer.harmonyos.com",
                f"华为 {query}",
                f"HMS {query}"
            ]
            
            all_results = []
            for q in optimized_queries:
                try:
                    result = self.app.search(
                        query=q,
                        **search_options
                    )
                    if result and hasattr(result, 'data'):
                        all_results.extend(result.data)
                except Exception as e:
                    logger.warning(f"⚠️ 搜索查询失败 '{q}': {e}")
                    continue
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ 搜索华为内容失败: {e}")
            return []
    
    def scrape_with_actions(self, url: str):
        """使用动作序列爬取动态内容"""
        try:
            actions = self.config.get_actions_for_dynamic_content()
            scrape_options = self.config.get_huawei_optimized_scrape_options()
            
            result = self.app.scrape_url(
                url=url,
                actions=actions,
                **scrape_options.model_dump()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 动态内容爬取失败: {e}")
            return None 