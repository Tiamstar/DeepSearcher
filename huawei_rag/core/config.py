#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为RAG系统配置管理
"""

import os
from typing import Dict, List, Any
from pathlib import Path

class CrawlerConfig:
    """爬虫配置类 - 重构后的精简版本"""
    
    # 文件路径配置
    LINKS_FILE = "huawei_docs_tree.json"
    OUTPUT_FILE = "huawei_docs_content.json"
    DATA_DIR = Path("data")
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    
    # 爬取控制
    MAX_CONCURRENT = 3
    DELAY_SECONDS = 3
    REQUEST_TIMEOUT = 30000
    
    # 页面等待配置
    WAIT_FOR_SELECTOR_TIMEOUT = 5000
    WAIT_FOR_CONTENT_TIMEOUT = 3000
    
    # 内容选择器
    CONTENT_SELECTORS = [
        '.doc-content', '.content', '.main-content', '.article-content',
        '#main-content', '.documentation', '.doc-body', 'main',
        '.markdown-body', '.content-wrapper', '.page-content'
    ]
    
    # 代码选择器
    CODE_SELECTORS = [
        'pre code', 'pre', '.highlight code', '.code-block',
        '.language-java', '.language-javascript', '.language-python',
        '.language-xml', '.language-json', '.language-kotlin',
        'code[class*="language-"]', '.hljs', '.codehilite'
    ]
    
    # 文本元素
    TEXT_ELEMENTS = [
        'p', 'div', 'span', 'li', 'td', 'th', 
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    ]
    
    # 过滤配置
    MIN_TEXT_LENGTH = 10
    MIN_CODE_LENGTH = 5
    MIN_CONTENT_LENGTH = 100
    
    # 浏览器配置
    BROWSER_ARGS = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled'
    ]
    
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    VIEWPORT = {'width': 1920, 'height': 1080}
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    
    # 增量保存配置
    ENABLE_INCREMENTAL_SAVE = True
    INCREMENTAL_SAVE_INTERVAL = 10
    ENABLE_RESUME_CRAWLING = True
    
    # 过滤配置
    FILTER_CONFIG = {
        'skip_empty_content': True,
        'min_content_length': MIN_CONTENT_LENGTH,
        'skip_error_pages': True,
    }
    
    # 输出配置
    OUTPUT_CONFIG = {
        'save_statistics': True,
        'save_by_category': False,  # 简化，默认不分类保存
        'save_code_separately': False,
    }
    
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.RAW_DATA_DIR.mkdir(exist_ok=True)
        cls.PROCESSED_DATA_DIR.mkdir(exist_ok=True)


class RAGConfig:
    """RAG系统配置"""
    
    # DeepSearcher配置
    DEFAULT_LLM_PROVIDER = "DeepSeek"
    DEFAULT_LLM_MODEL = "deepseek-reasoner"
    DEFAULT_EMBEDDING_PROVIDER = "SiliconflowEmbedding"
    DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
    DEFAULT_VECTOR_DB_PROVIDER = "Milvus"
    DEFAULT_VECTOR_DB_CONFIG = {"uri": "./milvus.db", "token": ""}
    
    # 文档处理配置
    DEFAULT_CHUNK_SIZE = 1500
    DEFAULT_CHUNK_OVERLAP = 100
    DEFAULT_COLLECTION_NAME = "huawei_docs"
    
    # 搜索配置
    DEFAULT_SEARCH_TOP_K = 5
    DEFAULT_SEARCH_THRESHOLD = 0.7


# 页面类型特殊配置（简化版）
PAGE_TYPE_CONFIGS = {
    'api_docs': {
        'selectors': ['.api-content', '.method-details'],
        'code_selectors': ['.api-example', '.code-sample'],
        'wait_time': 4000
    },
    'tutorial': {
        'selectors': ['.tutorial-content', '.guide-content'],
        'code_selectors': ['.tutorial-code', '.example-code'],
        'wait_time': 3000
    }
} 