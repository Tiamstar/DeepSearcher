#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享接口定义
用于MCP系统中各组件间的通信和数据交换
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import time


# 搜索相关枚举
class SearchMode(Enum):
    """搜索模式"""
    LOCAL_ONLY = "local_only"           # 仅使用本地RAG搜索
    ONLINE_ONLY = "online_only"         # 仅使用在线搜索
    HYBRID = "hybrid"                   # 混合搜索（本地+在线）
    CHAIN_OF_SEARCH = "chain_of_search" # 链式搜索


class QueryType(Enum):
    """查询类型枚举"""
    FACTUAL = "factual"           # 事实性查询
    PROCEDURAL = "procedural"     # 过程性查询  
    CONCEPTUAL = "conceptual"     # 概念性查询
    TROUBLESHOOTING = "troubleshooting"  # 故障排除
    CODE_EXAMPLE = "code_example" # 代码示例
    GENERAL = "general"           # 通用查询


# 搜索相关数据结构
@dataclass
class SearchContext:
    """搜索上下文"""
    session_id: str
    query_history: List[str] = field(default_factory=list)
    search_history: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    domain_focus: str = "huawei"


@dataclass
class SearchResult:
    """搜索结果"""
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    search_mode: SearchMode
    query_type: QueryType
    confidence_score: float
    processing_time: float
    token_usage: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeReviewRequest:
    """代码检查请求"""
    original_query: str
    code: str
    language: str
    review_type: str = "comprehensive"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CodeReviewResult:
    """代码检查结果"""
    request_id: str
    original_query: str
    code: str
    language: str
    checker: str
    score: int
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    report: str
    execution_time: float
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CodeGenerationResult:
    """代码生成结果"""
    request_id: str
    original_query: str
    search_answer: str
    initial_code: str
    code_review: str
    final_code: str
    generation_metadata: Dict[str, Any] = field(default_factory=dict)
    code_review_result: Optional[CodeReviewResult] = None
    execution_time: float = 0.0


# 接口定义
class CodeReviewInterface(ABC):
    """代码检查接口"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查检查器是否可用"""
        pass
    
    @abstractmethod
    async def review_code(self, request: CodeReviewRequest) -> CodeReviewResult:
        """检查代码"""
        pass


class SearchInterface(ABC):
    """搜索接口"""
    
    @abstractmethod
    async def search(self, 
                     query: str, 
                     search_mode: SearchMode = SearchMode.HYBRID,
                     session_id: str = None,
                     top_k: int = 5,
                     **kwargs) -> SearchResult:
        """执行搜索"""
        pass
    
    @abstractmethod
    async def generate_code(self, 
                           query: str, 
                           session_id: str = None,
                           **kwargs) -> CodeGenerationResult:
        """生成代码"""
        pass
    
    @abstractmethod
    async def review_code_standalone(self, 
                                   query: str, 
                                   code: str,
                                   language: str = "unknown",
                                   review_type: str = "comprehensive") -> CodeReviewResult:
        """独立代码检查"""
        pass


class CodeGeneratorInterface(ABC):
    """代码生成接口"""
    
    @abstractmethod
    async def generate_code(self, query: str, language: str, **kwargs) -> CodeGenerationResult:
        """生成代码"""
        pass 