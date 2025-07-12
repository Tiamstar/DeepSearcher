#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为RAG知识库系统

一个完整的华为开发者文档RAG (Retrieval-Augmented Generation) 系统，
包含内容爬取、向量化存储、本地搜索和增强版在线搜索功能。
"""

from .core.pipeline import HuaweiRAGPipeline
from .core.crawler import HuaweiContentCrawler
from .core.adapter import HuaweiDeepSearcherAdapter
from .core.online_search import EnhancedOnlineSearchEngine

__version__ = "2.0.0"
__author__ = "LFF"

# 主要的便捷类
class HuaweiRAG:
    """华为RAG系统的简化接口"""
    
    def __init__(self, config_file: str = None):
        """
        初始化华为RAG系统
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认配置
        """
        self.pipeline = HuaweiRAGPipeline(config_file=config_file)
        self.online_engine = None
    
    def crawl_and_load(self, force_recrawl: bool = False):
        """
        爬取华为文档并加载到向量数据库
        
        Args:
            force_recrawl: 是否强制重新爬取
        """
        return self.pipeline.run_full_pipeline(force_recrawl=force_recrawl)
    
    def search(self, query: str, top_k: int = 5):
        """
        搜索华为文档 (本地搜索)
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        return self.pipeline.search(query, top_k=top_k)
    
    def online_search(self, query: str, top_k: int = 5):
        """
        增强版在线搜索华为文档 - 使用FireCrawl智能搜索
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            
        Returns:
            (答案, 信息源列表)
        """
        if not self.online_engine:
            # 确保DeepSearcher配置已设置
            self.pipeline.setup_deepsearcher()
            self.online_engine = EnhancedOnlineSearchEngine(max_search_results=top_k)
        
        return self.online_engine.search_and_answer(query)
    
    def hybrid_search(self, 
                     query: str, 
                     use_local: bool = True, 
                     use_online: bool = True,
                     top_k: int = 5):
        """
        混合搜索：结合本地数据库和增强版在线搜索
        
        Args:
            query: 搜索查询
            use_local: 是否使用本地搜索
            use_online: 是否使用在线搜索
            top_k: 本地搜索返回结果数量
            
        Returns:
            包含综合答案和来源信息的字典
        """
        if self.online_engine is None:
            # 延迟初始化，确保配置已设置
            self.pipeline.setup_deepsearcher()
            self.online_engine = EnhancedOnlineSearchEngine()
        
        return self.online_engine.hybrid_search_and_answer(
            user_query=query,
            use_local=use_local,
            use_online=use_online
        )
    
    def get_status(self):
        """获取系统状态"""
        return self.pipeline.get_status()

__all__ = [
    'HuaweiRAG',
    'HuaweiRAGPipeline', 
    'HuaweiContentCrawler',
    'HuaweiDeepSearcherAdapter',
    'EnhancedOnlineSearchEngine'
] 