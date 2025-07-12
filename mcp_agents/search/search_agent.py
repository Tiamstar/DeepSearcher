#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Agent - MCP协议搜索Agent
专注于搜索功能：本地知识库搜索和在线搜索
不包含代码生成和代码检查功能，确保职责分明
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from mcp_agents.base import MCPAgent, MCPMessage
from shared.services.unified_search_service import (
    UnifiedSearchService, SearchMode, QueryType, SearchContext, SearchResult
)

# 导入DeepSearcher组件
try:
    from deepsearcher.configuration import config, init_config, llm, embedding_model, vector_db
    from deepsearcher.agent.chain_of_rag import ChainOfRAG
    from deepsearcher.agent.deep_search import DeepSearch
    from deepsearcher.agent.chain_of_search import ChainOfSearchOnly
    DEEPSEARCHER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"DeepSearcher模块导入失败: {e}")
    DEEPSEARCHER_AVAILABLE = False
    llm = embedding_model = vector_db = None
    ChainOfRAG = DeepSearch = ChainOfSearchOnly = None


class SearchAgent(MCPAgent):
    """
    搜索Agent - MCP协议版本
    专注于搜索功能：本地知识库搜索和基于firecrawl的在线搜索
    职责明确，不包含代码生成和代码检查功能
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("search")
        self.config = config or {}
        
        # 核心组件
        self.unified_search_service = None
        
        # 搜索配置
        self.collection_name = self.config.get("collection_name", "huawei_docs")
        self.default_search_mode = SearchMode(self.config.get("default_search_mode", "online_only"))
        self.max_context_length = self.config.get("max_context_length", 10)
        
        # 搜索上下文管理
        self.active_contexts: Dict[str, SearchContext] = {}
        
        # 统计信息
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "mode_usage": {mode.value: 0 for mode in SearchMode}
        }
        
        # 声明MCP能力 - 仅搜索相关
        self._declare_capabilities()
    
    def _declare_capabilities(self):
        """声明MCP能力 - 仅包含搜索功能"""
        # 搜索能力
        self.declare_capability("search.adaptive", {
            "description": "智能自适应搜索，自动选择最佳搜索模式",
            "parameters": ["query", "top_k", "session_id"]
        })
        
        self.declare_capability("search.local", {
            "description": "本地知识库搜索",
            "parameters": ["query", "top_k", "collection_name"]
        })
        
        self.declare_capability("search.online", {
            "description": "在线搜索（基于firecrawl）",
            "parameters": ["query", "top_k", "search_engine"]
        })
        
        self.declare_capability("search.hybrid", {
            "description": "混合搜索（本地+在线）",
            "parameters": ["query", "top_k", "session_id"]
        })
        
        self.declare_capability("search.chain_of_search", {
            "description": "链式搜索，深度挖掘信息",
            "parameters": ["query", "top_k", "session_id"]
        })
        
        # 上下文管理
        self.declare_capability("context.create", {
            "description": "创建搜索上下文",
            "parameters": ["session_id", "domain_focus"]
        })
        
        self.declare_capability("context.clear", {
            "description": "清除搜索上下文",
            "parameters": ["session_id"]
        })
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化搜索Agent"""
        try:
            self.logger.info("开始初始化搜索Agent...")
            
            # 初始化DeepSearcher配置
            if DEEPSEARCHER_AVAILABLE:
                try:
                    init_config(config)
                    self.logger.info("✅ DeepSearcher配置初始化成功")
                except Exception as e:
                    self.logger.warning(f"DeepSearcher配置初始化失败: {e}")
            
            # 初始化统一搜索服务
            self.unified_search_service = UnifiedSearchService(self.config)
            await self.unified_search_service.initialize()
            
            self.logger.info("✅ 搜索Agent初始化完成")
            
            return {
                "agent_id": self.agent_id,
                "capabilities": self.capabilities,
                "search_modes": [mode.value for mode in SearchMode],
                "query_types": [qtype.value for qtype in QueryType],
                "collection_name": self.collection_name,
                "components": {
                    "unified_search_service": self.unified_search_service is not None,
                    "deepsearcher_available": DEEPSEARCHER_AVAILABLE
                },
                "initialized_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"搜索Agent初始化失败: {str(e)}")
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理MCP请求"""
        try:
            method = message.method
            params = message.params or {}
            
            self.stats["total_queries"] += 1
            start_time = time.time()
            
            # 路由到具体的处理方法 - 仅搜索相关
            if method == "search.adaptive":
                result = await self._handle_adaptive_search(params)
            elif method == "search.local":
                result = await self._handle_local_search(params)
            elif method == "search.online":
                result = await self._handle_online_search(params)
            elif method == "search.hybrid":
                result = await self._handle_hybrid_search(params)
            elif method == "search.chain_of_search":
                result = await self._handle_chain_of_search(params)
            elif method == "context.create":
                result = await self._handle_context_create(params)
            elif method == "context.clear":
                result = await self._handle_context_clear(params)
            else:
                return self.protocol.handle_method_not_found(message.id, method)
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self.stats["successful_queries"] += 1
            self._update_average_response_time(processing_time)
            
            return self.protocol.create_response(message.id, result)
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            self.logger.error(f"处理搜索请求失败: {str(e)}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _handle_adaptive_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理自适应搜索"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        session_id = params.get("session_id")
        
        if not query:
            raise ValueError("查询不能为空")
        
        # 使用统一搜索服务
        result = await self.unified_search_service.search(
            query=query,
            search_mode="adaptive",
            session_id=session_id,
            top_k=top_k
        )
        
        # 更新搜索上下文
        if session_id:
            self._update_search_context(session_id, query, result)
        
        # 更新模式使用统计
        mode = result.get("search_mode", "adaptive")
        if mode in self.stats["mode_usage"]:
            self.stats["mode_usage"][mode] += 1
        
        return result
    
    async def _handle_local_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理本地搜索"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        collection_name = params.get("collection_name", self.collection_name)
        
        if not query:
            raise ValueError("查询不能为空")
        
        # 使用统一搜索服务
        result = await self.unified_search_service.search(
            query=query,
            search_mode="local_only",
            top_k=top_k
        )
        
        self.stats["mode_usage"]["local_only"] += 1
        return result
    
    async def _handle_online_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理在线搜索"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        search_engine = params.get("search_engine", "firecrawl")
        
        if not query:
            raise ValueError("查询不能为空")
        
        # 使用统一搜索服务
        result = await self.unified_search_service.search(
            query=query,
            search_mode="online_only",
            top_k=top_k
        )
        
        self.stats["mode_usage"]["online_only"] += 1
        return result
    
    async def _handle_hybrid_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理混合搜索"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        session_id = params.get("session_id")
        
        if not query:
            raise ValueError("查询不能为空")
        
        # 使用统一搜索服务
        result = await self.unified_search_service.search(
            query=query,
            search_mode="hybrid",
            session_id=session_id,
            top_k=top_k
        )
        
        # 更新搜索上下文
        if session_id:
            self._update_search_context(session_id, query, result)
        
        self.stats["mode_usage"]["hybrid"] += 1
        return result
    
    async def _handle_chain_of_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理链式搜索"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        session_id = params.get("session_id")
        
        if not query:
            raise ValueError("查询不能为空")
        
        # 使用统一搜索服务
        result = await self.unified_search_service.search(
            query=query,
            search_mode="chain_of_search",
            session_id=session_id,
            top_k=top_k
        )
        
        # 更新搜索上下文
        if session_id:
            self._update_search_context(session_id, query, result)
        
        self.stats["mode_usage"]["chain_of_search"] += 1
        return result
    
    async def _handle_context_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建搜索上下文"""
        session_id = params.get("session_id")
        domain_focus = params.get("domain_focus", "huawei")
        
        if not session_id:
            raise ValueError("会话ID不能为空")
        
        # 创建新的搜索上下文
        context = SearchContext(
            session_id=session_id,
            query_history=[],
            search_history=[],
            user_preferences={},
            domain_focus=domain_focus
        )
        
        self.active_contexts[session_id] = context
        
        return {
            "session_id": session_id,
            "domain_focus": domain_focus,
            "created_at": datetime.now().isoformat(),
            "status": "created"
        }
    
    async def _handle_context_clear(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """清除搜索上下文"""
        session_id = params.get("session_id")
        
        if not session_id:
            raise ValueError("会话ID不能为空")
        
        # 清除指定的搜索上下文
        if session_id in self.active_contexts:
            del self.active_contexts[session_id]
            status = "cleared"
        else:
            status = "not_found"
        
        return {
            "session_id": session_id,
            "status": status,
            "cleared_at": datetime.now().isoformat()
        }
    
    def _update_search_context(self, session_id: str, query: str, result: Dict[str, Any]):
        """更新搜索上下文"""
        if session_id not in self.active_contexts:
            self.active_contexts[session_id] = SearchContext(
                session_id=session_id,
                query_history=[],
                search_history=[],
                user_preferences={},
                domain_focus="huawei"
            )
        
        context = self.active_contexts[session_id]
        context.query_history.append(query)
        context.search_history.append({
            "query": query,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持历史记录在合理范围内
        if len(context.query_history) > self.max_context_length:
            context.query_history = context.query_history[-self.max_context_length:]
        if len(context.search_history) > self.max_context_length:
            context.search_history = context.search_history[-self.max_context_length:]
    
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
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取Agent提供的工具 - 仅搜索相关"""
        return [
            {
                "name": "adaptive_search",
                "description": "智能自适应搜索，自动选择最佳搜索策略",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "top_k": {"type": "integer", "default": 5, "description": "返回结果数量"},
                        "session_id": {"type": "string", "description": "会话ID（可选）"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "local_search",
                "description": "本地华为知识库搜索",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "top_k": {"type": "integer", "default": 5, "description": "返回结果数量"},
                        "collection_name": {"type": "string", "description": "知识库名称"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "online_search",
                "description": "基于firecrawl的在线搜索",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "top_k": {"type": "integer", "default": 5, "description": "返回结果数量"},
                        "search_engine": {"type": "string", "default": "firecrawl", "description": "搜索引擎"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "hybrid_search",
                "description": "混合搜索（本地+在线）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "top_k": {"type": "integer", "default": 5, "description": "返回结果数量"},
                        "session_id": {"type": "string", "description": "会话ID（可选）"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "chain_of_search",
                "description": "链式深度搜索",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "top_k": {"type": "integer", "default": 5, "description": "返回结果数量"},
                        "session_id": {"type": "string", "description": "会话ID（可选）"}
                    },
                    "required": ["query"]
                }
            }
        ]
    
    async def get_resources(self) -> List[Dict[str, Any]]:
        """获取Agent提供的资源"""
        return [
            {
                "uri": "search://huawei-docs",
                "name": "华为技术文档库",
                "description": "华为官方技术文档和开发指南",
                "mimeType": "application/json"
            },
            {
                "uri": "search://online-resources",
                "name": "在线技术资源",
                "description": "实时的在线技术资源和社区内容",
                "mimeType": "application/json"
            }
        ]
    
    async def get_prompts(self) -> List[Dict[str, Any]]:
        """获取Agent支持的提示词"""
        return [
            {
                "name": "technical_search",
                "description": "技术问题搜索提示词",
                "arguments": [
                    {"name": "query", "description": "技术问题", "required": True},
                    {"name": "context", "description": "上下文信息", "required": False}
                ]
            },
            {
                "name": "huawei_docs_search",
                "description": "华为文档搜索提示词",
                "arguments": [
                    {"name": "query", "description": "搜索查询", "required": True},
                    {"name": "domain", "description": "技术领域", "required": False}
                ]
            }
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "active_contexts": len(self.active_contexts),
            "success_rate": (
                self.stats["successful_queries"] / max(self.stats["total_queries"], 1)
            ) * 100,
            "components_status": {
                "unified_search_service": self.unified_search_service.is_available() if self.unified_search_service else False,
            }
        }

async def create_search_agent(config: Optional[Dict[str, Any]] = None) -> SearchAgent:
    """创建搜索Agent实例"""
    agent = SearchAgent(config)
    await agent.start()
    return agent

def main():
    """主函数"""
    async def run_agent():
        agent = await create_search_agent()
        await agent.run_stdio()
    
    asyncio.run(run_agent())

if __name__ == "__main__":
    main()