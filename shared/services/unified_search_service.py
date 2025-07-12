#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一搜索服务 - 基于原项目HuaweiSearchAgent的搜索功能迁移
专注于搜索服务：本地知识库搜索和在线搜索
不包含代码生成和代码检查功能，确保职责分明
完全移除对huawei_rag的依赖，基于deepsearcher实现
"""

import logging
import time
import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("✅ 环境变量加载成功")
except ImportError:
    logging.warning("⚠️ python-dotenv未安装，环境变量可能未加载")

# 导入DeepSearcher组件
try:
    from deepsearcher.configuration import config, init_config
    # 确保环境变量已加载后再初始化
    init_config(config)
    from deepsearcher.configuration import llm, embedding_model, vector_db
    from deepsearcher.agent.chain_of_rag import ChainOfRAG
    from deepsearcher.agent.deep_search import DeepSearch
    from deepsearcher.agent.chain_of_search import ChainOfSearchOnly
    from deepsearcher.vector_db.base import RetrievalResult
    DEEPSEARCHER_AVAILABLE = True
    logging.info("✅ DeepSearcher组件初始化成功")
except ImportError as e:
    logging.warning(f"DeepSearcher模块导入失败: {e}")
    DEEPSEARCHER_AVAILABLE = False
    llm = embedding_model = vector_db = None
    ChainOfRAG = DeepSearch = ChainOfSearchOnly = RetrievalResult = None
except Exception as e:
    logging.warning(f"DeepSearcher组件初始化失败: {e}")
    DEEPSEARCHER_AVAILABLE = False
    llm = embedding_model = vector_db = None
    ChainOfRAG = DeepSearch = ChainOfSearchOnly = RetrievalResult = None

# 导入在线搜索组件
try:
    import requests
    from firecrawl import FirecrawlApp
    ONLINE_SEARCH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"在线搜索组件导入失败: {e}")
    ONLINE_SEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

class SearchMode(Enum):
    """搜索模式枚举 - 仅搜索相关模式"""
    LOCAL_ONLY = "local_only"           # 仅本地搜索
    ONLINE_ONLY = "online_only"         # 仅在线搜索
    HYBRID = "hybrid"                   # 混合搜索
    ADAPTIVE = "adaptive"               # 自适应搜索
    CHAIN_OF_SEARCH = "chain_of_search" # 链式搜索

class QueryType(Enum):
    """查询类型枚举 - 与原项目保持一致"""
    FACTUAL = "factual"           # 事实性查询
    PROCEDURAL = "procedural"     # 过程性查询  
    CONCEPTUAL = "conceptual"     # 概念性查询
    TROUBLESHOOTING = "troubleshooting"  # 故障排除
    CODE_EXAMPLE = "code_example" # 代码示例
    GENERAL = "general"           # 通用查询

@dataclass
class SearchContext:
    """搜索上下文 - 与原项目保持一致"""
    session_id: str
    query_history: List[str]
    search_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    domain_focus: str = "huawei"

@dataclass
class SearchResult:
    """搜索结果数据结构 - 与原项目保持一致"""
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    search_mode: SearchMode
    query_type: QueryType
    confidence_score: float
    processing_time: float
    token_usage: int
    metadata: Dict[str, Any]


class UnifiedSearchService:
    """
    统一搜索服务 - 基于原项目HuaweiSearchAgent的搜索功能迁移
    专注于搜索服务：本地知识库搜索和在线搜索
    不包含代码生成和代码检查功能，确保职责分明
    完全移除对huawei_rag的依赖，基于deepsearcher实现
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.initialized = False
        
        # 搜索配置 - 与原项目保持一致
        self.collection_name = self.config.get("collection_name", "huawei_docs")
        self.default_search_mode = SearchMode(self.config.get("default_search_mode", "online_only"))
        self.max_context_length = self.config.get("max_context_length", 10)
        
        # 核心组件 - 基于deepsearcher
        self.chain_of_rag = None
        self.deep_search = None
        self.chain_of_search = None
        self.online_searcher = None
        
        # 搜索上下文管理
        self.active_contexts: Dict[str, SearchContext] = {}
        
        # 统计信息 - 仅搜索相关
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "mode_usage": {mode.value: 0 for mode in SearchMode}
        }
    
    async def initialize(self) -> bool:
        """初始化统一搜索服务 - 基于deepsearcher"""
        try:
            logger.info("开始初始化统一搜索服务...")
            
            # 初始化DeepSearcher配置
            if DEEPSEARCHER_AVAILABLE:
                try:
                    init_config(config)
                    logger.info("✅ DeepSearcher配置初始化成功")
                    
                    # 初始化DeepSearcher组件
                    await self._initialize_deepsearcher_components()
                except Exception as e:
                    logger.warning(f"DeepSearcher配置初始化失败: {e}")
            
            # 初始化在线搜索组件
            await self._initialize_online_components()
            
            self.initialized = True
            logger.info("✅ 统一搜索服务初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 统一搜索服务初始化失败: {e}")
            return False
    
    async def _initialize_deepsearcher_components(self):
        """初始化DeepSearcher组件"""
        try:
            if not DEEPSEARCHER_AVAILABLE or not llm or not embedding_model or not vector_db:
                logger.warning("DeepSearcher组件不完整，跳过初始化")
                return
            
            # 初始化ChainOfRAG（用于本地搜索）
            self.chain_of_rag = ChainOfRAG(
                llm=llm,
                embedding_model=embedding_model,
                vector_db=vector_db,
                collection_name=self.collection_name
            )
            logger.info("✅ ChainOfRAG初始化成功")
            
            # 初始化DeepSearch（用于深度搜索）
            self.deep_search = DeepSearch(
                llm=llm,
                embedding_model=embedding_model,
                vector_db=vector_db,
                collection_name=self.collection_name
            )
            logger.info("✅ DeepSearch初始化成功")
            
            # 初始化ChainOfSearchOnly（用于链式搜索）
            self.chain_of_search = ChainOfSearchOnly(
                llm=llm,
                embedding_model=embedding_model,
                vector_db=vector_db,
                collection_name=self.collection_name
            )
            logger.info("✅ ChainOfSearchOnly初始化成功")
            
        except Exception as e:
            logger.warning(f"DeepSearcher组件初始化失败: {e}")
    
    async def _initialize_online_components(self):
        """初始化在线搜索组件"""
        try:
            if ONLINE_SEARCH_AVAILABLE:
                self.online_searcher = EnhancedOnlineSearcher()
                logger.info("✅ 在线搜索器初始化成功")
            else:
                logger.warning("在线搜索组件不可用")
        except Exception as e:
            logger.warning(f"在线搜索组件初始化失败: {e}")
    
    def _classify_query_type(self, query: str) -> QueryType:
        """分类查询类型 - 与原项目逻辑保持一致"""
        if not llm:
            return QueryType.GENERAL
        
        try:
            classification_prompt = f"""
请分析以下查询的类型，从以下选项中选择最合适的一个：
1. factual - 事实性查询（寻找具体信息、数据、定义）
2. procedural - 过程性查询（如何做某事的步骤）
3. conceptual - 概念性查询（理解概念、原理、架构）
4. troubleshooting - 故障排除（解决问题、错误修复）
5. code_example - 代码示例（需要代码演示、API使用）
6. general - 通用查询（其他类型）

查询: "{query}"

请只回答类型名称，不要解释。
"""
            
            response = llm.chat([{"role": "user", "content": classification_prompt}])
            query_type_str = llm.remove_think(response.content).strip().lower()
            
            # 映射到枚举
            type_mapping = {
                "factual": QueryType.FACTUAL,
                "procedural": QueryType.PROCEDURAL,
                "conceptual": QueryType.CONCEPTUAL,
                "troubleshooting": QueryType.TROUBLESHOOTING,
                "code_example": QueryType.CODE_EXAMPLE,
                "general": QueryType.GENERAL
            }
            
            return type_mapping.get(query_type_str, QueryType.GENERAL)
            
        except Exception as e:
            logger.warning(f"查询类型分类失败: {e}")
            return QueryType.GENERAL
    
    def _select_search_mode(self, query: str, query_type: QueryType, context: SearchContext = None) -> SearchMode:
        """智能选择搜索模式 - 专注于搜索策略"""
        if self.default_search_mode != SearchMode.ADAPTIVE:
            return self.default_search_mode
        
        # 基于查询类型的启发式规则
        if query_type == QueryType.TROUBLESHOOTING:
            return SearchMode.ONLINE_ONLY
        elif query_type == QueryType.FACTUAL:
            return SearchMode.HYBRID
        elif query_type in [QueryType.PROCEDURAL, QueryType.CONCEPTUAL]:
            return SearchMode.CHAIN_OF_SEARCH
        else:
            return SearchMode.HYBRID
    
    async def search(self, 
                    query: str,
                    search_mode: str = "adaptive",
                    session_id: str = None,
                    top_k: int = 5,
                    **kwargs) -> Dict[str, Any]:
        """
        执行搜索 - 与原项目接口保持一致
        """
        if not self.initialized:
            raise RuntimeError("搜索服务未初始化")
        
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        try:
            # 转换搜索模式
            mode = SearchMode(search_mode.lower())
            self.stats["mode_usage"][mode.value] += 1
            
            # 分类查询类型
            query_type = self._classify_query_type(query)
            
            # 获取或创建搜索上下文
            context = self._get_or_create_context(session_id, query) if session_id else None
            
            # 自适应模式需要选择具体搜索模式
            if mode == SearchMode.ADAPTIVE:
                mode = self._select_search_mode(query, query_type, context)
            
            # 执行搜索
            answer, sources, token_usage = await self._execute_search(query, mode, query_type, top_k, **kwargs)
            
            # 计算置信度
            confidence_score = self._calculate_confidence(answer, sources, mode)
            
            processing_time = time.time() - start_time
            
            self.stats["successful_queries"] += 1
            self._update_average_response_time(processing_time)
            
            # 更新搜索上下文
            if context:
                self._update_context(context, query, answer, sources)
            
            # 返回结果
            return {
                "query": query,
                "answer": answer,
                "sources": sources,
                "search_mode": mode.value,
                "query_type": query_type.value,
                "confidence_score": confidence_score,
                "processing_time": processing_time,
                "token_usage": token_usage,
                "metadata": {
                    "session_id": session_id,
                    "top_k": top_k
                },
                "success": True
            }
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            logger.error(f"搜索执行失败: {e}")
            return {
                "query": query,
                "answer": f"搜索失败: {str(e)}",
                "sources": [],
                "search_mode": search_mode,
                "success": False,
                "error": str(e)
            }
    
    async def _execute_search(self, 
                             query: str, 
                             search_mode: SearchMode, 
                             query_type: QueryType,
                             top_k: int,
                             **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """执行具体的搜索 - 基于deepsearcher组件"""
        if search_mode == SearchMode.LOCAL_ONLY:
            return await self._local_search(query, top_k, **kwargs)
        elif search_mode == SearchMode.ONLINE_ONLY:
            return await self._online_search(query, top_k, **kwargs)
        elif search_mode == SearchMode.HYBRID:
            return await self._hybrid_search(query, top_k, **kwargs)
        elif search_mode == SearchMode.CHAIN_OF_SEARCH:
            return await self._chain_of_search(query, top_k, **kwargs)
        else:
            # 默认使用混合搜索
            return await self._hybrid_search(query, top_k, **kwargs)
    
    async def _local_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """本地搜索 - 基于deepsearcher的ChainOfRAG"""
        if not self.chain_of_rag:
            return "本地搜索服务不可用", [], 0
        
        try:
            # 使用ChainOfRAG进行本地搜索 - 修复方法调用
            answer, retrieved_results, token_usage = await asyncio.to_thread(
                self.chain_of_rag.query,
                query,
                top_k=top_k
            )
            
            if not answer:
                return "未找到相关文档", [], 0
            
            # 格式化来源
            sources = []
            for result in retrieved_results[:top_k]:
                if hasattr(result, 'metadata') and hasattr(result, 'text') and hasattr(result, 'score'):
                    # RetrievalResult对象
                    formatted_source = {
                        "title": result.metadata.get("title", result.metadata.get("file_name", "未知标题")),
                        "content": result.text[:500],
                        "url": result.metadata.get("url", result.metadata.get("file_path", "")),
                        "score": result.score,
                        "source": "本地知识库"
                    }
                elif isinstance(result, dict):
                    formatted_source = {
                        "title": result.get("title", result.get("metadata", {}).get("title", "未知标题")),
                        "content": result.get("content", result.get("text", ""))[:500],
                        "url": result.get("url", result.get("metadata", {}).get("url", "")),
                        "score": result.get("score", result.get("similarity", 0.0)),
                        "source": "本地知识库"
                    }
                else:
                    formatted_source = {
                        "title": "搜索结果",
                        "content": str(result)[:500],
                        "url": "",
                        "score": 1.0,
                        "source": "本地知识库"
                    }
                sources.append(formatted_source)
            
            return answer, sources, token_usage
                
        except Exception as e:
            logger.error(f"本地搜索执行失败: {e}")
            return f"本地搜索失败: {str(e)}", [], 0
    
    async def _fallback_online_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """回退在线搜索 - 在没有真实在线搜索的情况下使用"""
        try:
            # 使用LLM生成模拟的在线搜索结果
            if not llm:
                return "在线搜索服务不可用，请配置 FIRECRAWL_API_KEY", [], 0
            
            # 使用LLM生成关于该查询的回答
            prompt = f"""
作为一个专业的华为技术专家，请回答以下问题。
如果涉及代码示例，请提供简洁实用的示例。
如果涉及配置或步骤，请提供清晰的指导。

问题：{query}

请基于你的专业知识回答，特别关注华为鸿蒙系统、ArkTS、ArkUI等相关技术。
"""
            
            response = llm.chat([{"role": "user", "content": prompt}])
            answer = llm.remove_think(response.content) if hasattr(llm, 'remove_think') else response.content
            
            # 创建模拟的来源
            sources = [
                {
                    "title": f"关于 '{query}' 的专业解答",
                    "content": answer[:500],
                    "url": "https://developer.huawei.com/consumer/cn/arkts/",
                    "score": 1.0,
                    "source": "AI生成内容"
                }
            ]
            
            return answer, sources, getattr(response, 'total_tokens', 0)
            
        except Exception as e:
            logger.error(f"回退在线搜索失败: {e}")
            return f"在线搜索失败: {str(e)}", [], 0
    
    async def _online_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """在线搜索 - 基于增强的在线搜索器"""
        if not self.online_searcher:
            # 如果在线搜索器不可用，返回模拟结果
            return await self._fallback_online_search(query, top_k, **kwargs)
        
        try:
            # 使用在线搜索器
            results = await asyncio.to_thread(
                self.online_searcher.search,
                query=f"{query} 华为 鸿蒙 ArkTS",
                num_results=top_k
            )
            
            if not results:
                return "未找到相关在线资源", [], 0
            
            # 格式化结果
            sources = []
            context_parts = []
            
            for result in results[:top_k]:
                source = {
                    "title": result.get("title", "未知标题"),
                    "content": result.get("snippet", result.get("content", ""))[:1000],
                    "url": result.get("url", ""),
                    "score": 1.0,
                    "source": "在线搜索"
                }
                sources.append(source)
                context_parts.append(f"标题: {source['title']}\n内容: {source['content']}")
            
            # 使用LLM生成综合答案
            if llm:
                context = "\n\n".join(context_parts)
                prompt = f"""
基于以下在线搜索结果，回答用户问题：

用户问题：{query}

搜索结果：
{context}

请提供准确、详细的回答，重点关注华为技术栈的特点和最佳实践。
"""
                response = llm.chat([{"role": "user", "content": prompt}])
                answer = llm.remove_think(response.content) if hasattr(llm, 'remove_think') else response.content
                token_usage = len(prompt.split()) + len(answer.split())
            else:
                answer = "在线搜索找到相关资源，但LLM服务不可用，无法生成综合答案。"
                token_usage = 0
            
            return answer, sources, token_usage
                
        except Exception as e:
            logger.error(f"在线搜索执行失败: {e}")
            return f"在线搜索失败: {str(e)}", [], 0
    
    async def _hybrid_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """混合搜索 - 并行执行本地和在线搜索"""
        # 并行执行本地和在线搜索
        local_task = asyncio.create_task(self._local_search(query, top_k//2, **kwargs))
        online_task = asyncio.create_task(self._online_search(query, top_k//2, **kwargs))
        
        local_answer, local_sources, local_tokens = await local_task
        online_answer, online_sources, online_tokens = await online_task
        
        # 合并结果
        all_sources = local_sources + online_sources
        total_tokens = local_tokens + online_tokens
        
        # 生成综合答案
        if llm:
            prompt = f"""
基于以下本地和在线搜索结果，为用户问题提供综合答案：

用户问题：{query}

本地搜索结果：
{local_answer}

在线搜索结果：
{online_answer}

请综合两个搜索结果，提供准确、完整的答案。
"""
            response = llm.chat([{"role": "user", "content": prompt}])
            answer = llm.remove_think(response.content) if hasattr(llm, 'remove_think') else response.content
            total_tokens += len(prompt.split()) + len(answer.split())
        else:
            answer = f"本地搜索：{local_answer}\n\n在线搜索：{online_answer}"
        
        return answer, all_sources, total_tokens
    
    async def _chain_of_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """链式搜索 - 基于deepsearcher的ChainOfSearchOnly"""
        if self.chain_of_search:
            try:
                # 使用ChainOfSearchOnly进行链式搜索 - 修复方法调用
                answer, retrieved_results, token_usage = await asyncio.to_thread(
                    self.chain_of_search.query,
                    query,
                    top_k=top_k
                )
                
                # 格式化来源
                sources = []
                for result in retrieved_results[:top_k]:
                    if hasattr(result, 'metadata') and hasattr(result, 'text') and hasattr(result, 'score'):
                        formatted_source = {
                            "title": result.metadata.get("title", result.metadata.get("file_name", "链式搜索结果")),
                            "content": result.text[:500],
                            "url": result.metadata.get("url", result.metadata.get("file_path", "")),
                            "score": result.score,
                            "source": "链式搜索"
                        }
                        sources.append(formatted_source)
                
                return answer, sources, token_usage
                
            except Exception as e:
                logger.warning(f"链式搜索失败，回退到混合搜索: {e}")
        
        # 回退到混合搜索
        return await self._hybrid_search(query, top_k, **kwargs)
    
    def _get_or_create_context(self, session_id: str = None, query: str = "") -> Optional[SearchContext]:
        """获取或创建搜索上下文 - 与原项目逻辑保持一致"""
        if not session_id:
            return None
        
        if session_id not in self.active_contexts:
            self.active_contexts[session_id] = SearchContext(
                session_id=session_id,
                query_history=[],
                search_history=[],
                user_preferences={},
                domain_focus="huawei"
            )
        
        return self.active_contexts[session_id]
    
    def _update_context(self, context: SearchContext, query: str, answer: str, sources: List[Dict[str, Any]]):
        """更新搜索上下文 - 与原项目逻辑保持一致"""
        context.query_history.append(query)
        context.search_history.append({
            "query": query,
            "answer": answer,
            "sources": sources,
            "timestamp": time.time()
        })
        
        # 保持历史记录在合理范围内
        if len(context.query_history) > self.max_context_length:
            context.query_history = context.query_history[-self.max_context_length:]
        if len(context.search_history) > self.max_context_length:
            context.search_history = context.search_history[-self.max_context_length:]
    
    def _calculate_confidence(self, answer: str, sources: List[Dict[str, Any]], search_mode: SearchMode) -> float:
        """计算置信度 - 与原项目逻辑保持一致"""
        base_confidence = 0.5
        
        # 基于答案长度调整
        if len(answer) > 100:
            base_confidence += 0.2
        
        # 基于来源数量调整
        source_bonus = min(len(sources) * 0.1, 0.3)
        base_confidence += source_bonus
        
        # 基于搜索模式调整
        mode_bonus = {
            SearchMode.HYBRID: 0.2,
            SearchMode.CHAIN_OF_SEARCH: 0.15,
            SearchMode.LOCAL_ONLY: 0.1,
            SearchMode.ONLINE_ONLY: 0.1
        }
        base_confidence += mode_bonus.get(search_mode, 0)
        
        return min(base_confidence, 1.0)
    
    def _update_average_response_time(self, processing_time: float):
        """更新平均响应时间"""
        total_queries = self.stats["successful_queries"]
        if total_queries == 1:
            self.stats["average_response_time"] = processing_time
        else:
            current_avg = self.stats["average_response_time"]
            self.stats["average_response_time"] = (
                (current_avg * (total_queries - 1) + processing_time) / total_queries
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            **self.stats,
            "initialized": self.initialized,
            "components_available": {
                "chain_of_rag": self.chain_of_rag is not None,
                "deep_search": self.deep_search is not None,
                "chain_of_search": self.chain_of_search is not None,
                "online_searcher": self.online_searcher is not None,
                "deepsearcher": DEEPSEARCHER_AVAILABLE,
                "online_search": ONLINE_SEARCH_AVAILABLE
            },
            "success_rate": (
                self.stats["successful_queries"] / max(self.stats["total_queries"], 1)
            ) * 100
        }
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.initialized and (
            self.chain_of_rag is not None or 
            self.online_searcher is not None
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy" if self.is_available() else "unhealthy",
            "initialized": self.initialized,
            "stats": self.get_stats(),
            "timestamp": time.time()
        }


# 增强的在线搜索器实现
class EnhancedOnlineSearcher:
    """增强的在线搜索器 - 基于firecrawl和其他搜索引擎"""
    
    def __init__(self):
        self.firecrawl_app = None
        self._initialize_firecrawl()
    
    def _initialize_firecrawl(self):
        """初始化FireCrawl"""
        try:
            if ONLINE_SEARCH_AVAILABLE:
                firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
                if firecrawl_api_key:
                    self.firecrawl_app = FirecrawlApp(api_key=firecrawl_api_key)
                    logger.info("✅ FireCrawl初始化成功")
                else:
                    logger.warning("FIRECRAWL_API_KEY未配置")
        except Exception as e:
            logger.warning(f"FireCrawl初始化失败: {e}")
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """执行在线搜索"""
        results = []
        
        # 尝试使用FireCrawl搜索
        if self.firecrawl_app:
            results.extend(self._firecrawl_search(query, num_results))
        
        # 如果结果不足，可以添加其他搜索源
        if len(results) < num_results:
            # 这里可以添加其他搜索引擎的实现
            pass
        
        return results[:num_results]
    
    def _firecrawl_search(self, query: str, num_results: int) -> List[Dict]:
        """使用FireCrawl进行搜索"""
        try:
            search_response = self.firecrawl_app.search(
                query=query,
                limit=num_results
            )
            
            results = []
            if hasattr(search_response, 'data'):
                search_data = search_response.data
            elif isinstance(search_response, dict) and 'data' in search_response:
                search_data = search_response['data']
            else:
                return []
            
            for item in search_data[:num_results]:
                if hasattr(item, '__dict__'):
                    item_dict = item.__dict__
                elif isinstance(item, dict):
                    item_dict = item
                else:
                    continue
                
                result = {
                    "title": item_dict.get("title", "未知标题"),
                    "snippet": item_dict.get("description", item_dict.get("content", "")),
                    "url": item_dict.get("url", ""),
                    "source": "firecrawl"
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"FireCrawl搜索失败: {e}")
            return [] 