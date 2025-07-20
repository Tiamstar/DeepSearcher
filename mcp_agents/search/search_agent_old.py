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
        
        # 鸿蒙专用搜索
        self.declare_capability("search.harmonyos_context", {
            "description": "鸿蒙开发上下文搜索，支持错误修复模式",
            "parameters": ["query", "search_mode", "error_context", "focus_keywords", "fix_instructions"]
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
            elif method == "search.harmonyos_context":
                result = await self._handle_harmonyos_search(params)
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
    
    # ==================== 鸿蒙专用搜索方法 ====================
    
    async def _handle_harmonyos_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理鸿蒙上下文搜索"""
        try:
            query = params.get("query", "")
            search_mode = params.get("search_mode", "normal")
            error_context = params.get("error_context", {})
            focus_keywords = params.get("focus_keywords", [])
            fix_instructions = params.get("fix_instructions", [])
            
            if not query:
                raise ValueError("搜索查询不能为空")
            
            self.logger.info(f"开始鸿蒙搜索: {query} (模式: {search_mode})")
            
            # 构建鸿蒙专用搜索查询
            enhanced_query = self._build_harmonyos_query(query, search_mode, error_context, focus_keywords, fix_instructions)
            
            # 执行搜索
            if DEEPSEARCHER_AVAILABLE and llm:
                search_result = await self._execute_harmonyos_search(enhanced_query, search_mode)
                
                # 后处理搜索结果
                processed_result = self._process_harmonyos_result(search_result, error_context, fix_instructions)
                
                self.logger.info(f"鸿蒙搜索完成: {len(processed_result.get('sources', []))} 个来源")
                
                return processed_result
            else:
                # 如果DeepSearcher不可用，返回基础的搜索结果
                return await self._fallback_harmonyos_search(enhanced_query, search_mode, error_context)
                
        except Exception as e:
            self.logger.error(f"鸿蒙搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "search_context": "",
                "sources": []
            }
    
    def _build_harmonyos_query(self, query: str, search_mode: str, error_context: Dict, focus_keywords: List, fix_instructions: List) -> str:
        """构建鸿蒙专用搜索查询"""
        enhanced_parts = [query]
        
        # 添加鸿蒙关键词
        harmonyos_keywords = ["鸿蒙", "HarmonyOS", "ArkTS", "ArkUI"]
        enhanced_parts.extend(harmonyos_keywords)
        
        # 添加焦点关键词
        if focus_keywords:
            enhanced_parts.extend(focus_keywords)
        
        # 错误修复模式下的特殊处理
        if search_mode == "error_fixing" and error_context:
            enhanced_parts.append("错误解决")
            enhanced_parts.append("故障排除")
            
            # 从错误上下文中提取关键词
            if error_context.get("error_categories"):
                for category in error_context["error_categories"]:
                    if category == "import_error":
                        enhanced_parts.extend(["模块导入", "依赖管理", "包配置"])
                    elif category == "syntax_error":
                        enhanced_parts.extend(["语法错误", "代码规范", "ArkTS语法"])
                    elif category == "type_error":
                        enhanced_parts.extend(["类型错误", "接口定义", "类型检查"])
                    elif category == "decorator_error":
                        enhanced_parts.extend(["装饰器", "@Component", "@Entry"])
        
        return " ".join(enhanced_parts)
    
    async def _execute_harmonyos_search(self, enhanced_query: str, search_mode: str) -> Dict[str, Any]:
        """执行鸿蒙搜索"""
        try:
            # 使用统一搜索服务
            if self.unified_search_service and self.unified_search_service.is_available():
                # 使用统一搜索服务
                context = SearchContext(
                    session_id=f"harmonyos_{int(time.time())}",
                    query_history=[enhanced_query],
                    search_history=[],
                    user_preferences={"domain": "harmonyos"},
                    domain_focus="harmonyos"
                )
                
                result = await self.unified_search_service.search(
                    query=enhanced_query,
                    mode=SearchMode.HYBRID,
                    query_type=QueryType.CODE_EXAMPLE,
                    context=context,
                    top_k=5
                )
                
                return {
                    "success": True,
                    "answer": result.answer,
                    "sources": result.sources,
                    "search_query": enhanced_query,
                    "search_mode": search_mode
                }
            
            # 如果统一搜索服务不可用，使用ChainOfRAG
            elif DEEPSEARCHER_AVAILABLE:
                chain_rag = ChainOfRAG(llm, embedding_model, vector_db)
                
                # 直接调用查询方法
                response = chain_rag.query(enhanced_query)
                
                return {
                    "success": True,
                    "answer": response.get("answer", ""),
                    "sources": response.get("sources", []),
                    "search_query": enhanced_query,
                    "search_mode": search_mode
                }
            else:
                raise Exception("搜索服务不可用")
            
        except Exception as e:
            self.logger.error(f"执行鸿蒙搜索失败: {e}")
            raise
    
    async def _fallback_harmonyos_search(self, enhanced_query: str, search_mode: str, error_context: Dict) -> Dict[str, Any]:
        """备用搜索方法（当DeepSearcher不可用时）"""
        # 基于错误上下文和关键词生成基础回答
        if search_mode == "error_fixing":
            basic_answer = self._generate_basic_error_answer(error_context)
        else:
            basic_answer = self._generate_basic_harmonyos_answer(enhanced_query)
        
        return {
            "success": True,
            "answer": basic_answer,
            "sources": [],
            "search_context": basic_answer,
            "search_query": enhanced_query,
            "search_mode": search_mode,
            "fallback_mode": True
        }
    
    def _process_harmonyos_result(self, search_result: Dict, error_context: Dict, fix_instructions: List) -> Dict[str, Any]:
        """后处理鸿蒙搜索结果"""
        answer = search_result.get("answer", "")
        sources = search_result.get("sources", [])
        
        # 构建搜索上下文
        search_context = f"""鸿蒙开发上下文信息：

{answer}

相关资源：
"""
        
        for i, source in enumerate(sources[:3], 1):
            search_context += f"{i}. {source.get('title', 'Unknown')}\n"
        
        if fix_instructions:
            search_context += f"\n修复指导：\n"
            for instruction in fix_instructions:
                search_context += f"- {instruction}\n"
        
        return {
            "success": True,
            "answer": answer,
            "search_context": search_context,
            "sources": sources,
            "search_query": search_result.get("search_query", ""),
            "search_mode": search_result.get("search_mode", "normal"),
            "error_context": error_context,
            "fix_instructions": fix_instructions
        }
    
    def _generate_basic_error_answer(self, error_context: Dict) -> str:
        """生成基础错误解答"""
        error_categories = error_context.get("error_categories", {})
        
        if "import_error" in error_categories:
            return """鸿蒙模块导入问题解决方案：

1. 检查模块路径是否正确
2. 确认依赖是否已安装在oh_modules中
3. 验证import语句语法
4. 检查模块是否支持当前API版本

常见导入格式：
- import { Component } from '@ohos.component'
- import router from '@ohos.router'
"""
        
        elif "syntax_error" in error_categories:
            return """ArkTS语法错误解决方案：

1. 检查装饰器使用：@Entry、@Component、@State等
2. 确认struct定义和build()方法格式
3. 验证大括号和分号使用
4. 检查变量类型定义

基础格式：
@Entry
@Component
struct PageName {
  build() {
    // 组件内容
  }
}
"""
        
        else:
            return """鸿蒙开发常见问题解决指南：

1. 确保使用正确的ArkTS语法
2. 检查组件装饰器配置
3. 验证模块导入和依赖
4. 确认API版本兼容性
5. 使用官方组件和API

建议参考鸿蒙官方文档和示例代码。
"""
    
    def _generate_basic_harmonyos_answer(self, query: str) -> str:
        """生成基础鸿蒙回答"""
        return f"""基于查询"{query}"的鸿蒙开发指导：

鸿蒙应用开发要点：
1. 使用ArkTS语言进行开发
2. 遵循鸿蒙组件化架构
3. 正确使用@Entry、@Component等装饰器
4. 采用声明式UI开发模式
5. 使用Column、Row、Text等基础组件

推荐开发流程：
1. 创建页面结构(.ets文件)
2. 定义组件状态和属性
3. 实现build()方法构建UI
4. 添加事件处理逻辑
5. 进行测试和调试

建议查阅鸿蒙官方开发文档获取详细信息。
"""

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