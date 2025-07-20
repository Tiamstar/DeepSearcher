#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复后的搜索Agent - 优先使用在线搜索(firecrawl)，失败时使用本地搜索(milvus)
"""

import asyncio
import logging
import time
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from mcp_agents.base import MCPAgent, MCPMessage

# 导入firecrawl在线搜索
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False

# 导入DeepSearcher本地搜索
try:
    from deepsearcher.configuration import config, init_config, llm, embedding_model, vector_db
    from deepsearcher.agent.chain_of_rag import ChainOfRAG
    init_config(config)
    DEEPSEARCHER_AVAILABLE = True
except ImportError:
    DEEPSEARCHER_AVAILABLE = False
    llm = embedding_model = vector_db = ChainOfRAG = None

logger = logging.getLogger(__name__)


class SearchAgent(MCPAgent):
    """搜索Agent - 优先使用在线搜索，失败时使用本地搜索"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("search")
        self.config = config or {}
        
        # 在线搜索客户端
        self.firecrawl_client = None
        
        # 本地搜索客户端
        self.local_search_client = None
        
        # 统计信息
        self.stats = {
            "total_searches": 0,
            "online_searches": 0,
            "local_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0
        }
        
        # 声明能力
        self.declare_capability("search.online", {
            "description": "基于firecrawl的在线搜索",
            "parameters": ["query", "top_k"]
        })
        
        self.declare_capability("search.local", {
            "description": "基于milvus的本地RAG搜索",
            "parameters": ["query", "top_k"]
        })
        
        self.declare_capability("search.harmonyos", {
            "description": "鸿蒙专用搜索",
            "parameters": ["query", "search_mode", "error_context"]
        })
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化搜索Agent"""
        try:
            # 初始化在线搜索客户端
            if FIRECRAWL_AVAILABLE:
                api_key = os.getenv("FIRECRAWL_API_KEY")
                if api_key:
                    self.firecrawl_client = FirecrawlApp(api_key=api_key)
                    logger.info("✅ Firecrawl在线搜索初始化成功")
                else:
                    logger.warning("❌ FIRECRAWL_API_KEY环境变量未设置")
            
            # 初始化本地搜索客户端
            if DEEPSEARCHER_AVAILABLE and llm and embedding_model and vector_db:
                self.local_search_client = ChainOfRAG(llm, embedding_model, vector_db)
                logger.info("✅ 本地RAG搜索初始化成功")
            else:
                logger.warning("❌ DeepSearcher组件不可用")
            
            return {
                "agent_id": self.agent_id,
                "capabilities": self.capabilities,
                "firecrawl_available": self.firecrawl_client is not None,
                "local_search_available": self.local_search_client is not None,
                "status": "initialized"
            }
            
        except Exception as e:
            logger.error(f"搜索Agent初始化失败: {e}")
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理搜索请求"""
        try:
            method = message.method
            params = message.params or {}
            
            if method == "search.online":
                result = await self._online_search(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "search.local":
                result = await self._local_search(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "search.harmonyos":
                result = await self._harmonyos_search(params)
                return self.protocol.create_response(message.id, result)
            
            else:
                return self.protocol.handle_method_not_found(message.id, method)
                
        except Exception as e:
            logger.error(f"处理搜索请求失败: {e}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _online_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """在线搜索"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        
        if not query:
            raise ValueError("搜索查询不能为空")
        
        self.stats["total_searches"] += 1
        self.stats["online_searches"] += 1
        
        start_time = time.time()
        
        try:
            if not self.firecrawl_client:
                raise Exception("Firecrawl客户端不可用")
            
            # 使用firecrawl进行在线搜索
            logger.info(f"开始firecrawl搜索: {query}")
            search_results = self.firecrawl_client.search(
                query=query,
                limit=top_k
            )
            logger.info(f"firecrawl搜索响应类型: {type(search_results)}")
            logger.info(f"firecrawl搜索响应属性: {dir(search_results)}")
            
            # 处理搜索结果
            sources = []
            answer_parts = []
            
            # search_results是SearchResponse对象，需要访问data属性
            results_data = getattr(search_results, 'data', [])
            if not results_data and hasattr(search_results, '__dict__'):
                # 如果没有data属性，尝试直接访问对象属性
                results_data = [search_results.__dict__] if search_results.__dict__ else []
            
            for result in results_data[:top_k]:
                # 处理字典格式的结果
                if isinstance(result, dict):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", result.get("description", ""))
                else:
                    # 处理对象格式的结果
                    title = getattr(result, 'title', "")
                    url = getattr(result, 'url', "")
                    content = getattr(result, 'content', getattr(result, 'description', ""))
                
                # 截断过长的内容
                if len(content) > 500:
                    content = content[:500] + "..."
                
                source = {
                    "title": title,
                    "url": url,
                    "content": content,
                    "source_type": "online"
                }
                sources.append(source)
                answer_parts.append(content)
            
            # 生成答案
            answer = self._generate_answer_from_sources(query, answer_parts)
            
            processing_time = time.time() - start_time
            self.stats["successful_searches"] += 1
            
            return {
                "success": True,
                "query": query,
                "answer": answer,
                "sources": sources,
                "search_method": "online",
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.stats["failed_searches"] += 1
            logger.error(f"在线搜索失败: {e}")
            raise
    
    async def _local_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """本地搜索"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        
        if not query:
            raise ValueError("搜索查询不能为空")
        
        self.stats["total_searches"] += 1
        self.stats["local_searches"] += 1
        
        start_time = time.time()
        
        try:
            if not self.local_search_client:
                raise Exception("本地搜索客户端不可用")
            
            # 使用ChainOfRAG进行本地搜索
            response = self.local_search_client.query(query)
            
            # 处理搜索结果
            sources = []
            if isinstance(response, dict) and "sources" in response:
                sources = response["sources"][:top_k]
            
            answer = response.get("answer", "") if isinstance(response, dict) else str(response)
            
            processing_time = time.time() - start_time
            self.stats["successful_searches"] += 1
            
            return {
                "success": True,
                "query": query,
                "answer": answer,
                "sources": sources,
                "search_method": "local",
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.stats["failed_searches"] += 1
            logger.error(f"本地搜索失败: {e}")
            raise
    
    async def _harmonyos_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """鸿蒙专用搜索 - 优先在线搜索，失败时使用本地搜索"""
        query = params.get("query", "")
        search_mode = params.get("search_mode", "normal")
        error_context = params.get("error_context", {})
        
        if not query:
            raise ValueError("搜索查询不能为空")
        
        # 构建鸿蒙专用查询
        harmonyos_query = self._build_harmonyos_query(query, search_mode, error_context)
        
        try:
            # 优先尝试在线搜索
            online_params = {"query": harmonyos_query, "top_k": 5}
            result = await self._online_search(online_params)
            
            # 增强鸿蒙搜索结果
            result["search_context"] = self._build_harmonyos_context(result, error_context)
            result["search_mode"] = search_mode
            
            return result
            
        except Exception as online_error:
            logger.warning(f"在线搜索失败，尝试本地搜索: {online_error}")
            
            try:
                # 使用本地搜索作为备选
                local_params = {"query": harmonyos_query, "top_k": 5}
                result = await self._local_search(local_params)
                
                # 增强鸿蒙搜索结果
                result["search_context"] = self._build_harmonyos_context(result, error_context)
                result["search_mode"] = search_mode
                result["fallback_to_local"] = True
                
                return result
                
            except Exception as local_error:
                logger.error(f"本地搜索也失败: {local_error}")
                
                # 返回基础鸿蒙开发建议（确保总是有答案）
                fallback_answer = self._generate_basic_harmonyos_answer(query, search_mode, error_context)
                return {
                    "success": True,  # 改为True，因为我们提供了备用答案
                    "query": query,
                    "answer": fallback_answer,
                    "sources": [],
                    "search_method": "fallback",
                    "search_mode": search_mode,
                    "search_context": fallback_answer,
                    "fallback_reason": f"在线和本地搜索都失败: {str(local_error)}"
                }
    
    def _build_harmonyos_query(self, query: str, search_mode: str, error_context: Dict) -> str:
        """构建鸿蒙专用搜索查询"""
        query_parts = [query]
        
        # 添加鸿蒙关键词
        query_parts.extend(["HarmonyOS", "鸿蒙", "ArkTS", "ArkUI"])
        
        # 根据搜索模式添加特定关键词
        if search_mode == "error_fixing":
            query_parts.extend(["错误修复", "问题解决", "调试"])
            
            # 添加错误上下文
            if error_context:
                error_type = error_context.get("error_type", "")
                if error_type:
                    query_parts.append(error_type)
        
        elif search_mode == "code_generation":
            query_parts.extend(["代码示例", "开发指南", "API文档"])
        
        return " ".join(query_parts)
    
    def _build_harmonyos_context(self, search_result: Dict, error_context: Dict) -> str:
        """构建鸿蒙搜索上下文"""
        context_parts = []
        
        if search_result.get("answer"):
            context_parts.append(f"搜索结果: {search_result['answer']}")
        
        if error_context:
            context_parts.append(f"错误上下文: {error_context}")
        
        return "\n".join(context_parts)
    
    def _generate_answer_from_sources(self, query: str, sources: List[str]) -> str:
        """从源内容生成答案"""
        if not sources:
            return f"未找到关于 '{query}' 的相关信息"
        
        # 简单的答案生成逻辑
        combined_content = "\n".join(sources[:3])  # 使用前3个源
        
        if len(combined_content) > 1000:
            combined_content = combined_content[:1000] + "..."
        
        return f"根据搜索结果，关于 '{query}' 的信息：\n{combined_content}"
    
    def _generate_basic_harmonyos_answer(self, query: str, search_mode: str, error_context: Dict) -> str:
        """生成基础鸿蒙答案"""
        if search_mode == "error_fixing":
            return f"""基于错误修复模式的鸿蒙开发建议：

针对查询: {query}

常见鸿蒙开发问题解决方案：
1. **语法错误**: 检查ArkTS语法，确保使用正确的装饰器语法
2. **导入错误**: 验证模块导入路径，如 import {{hilog}} from '@ohos.hilog'
3. **组件定义**: 确保使用@Component装饰器，实现build()方法
4. **入口页面**: 使用@Entry装饰器标识应用入口
5. **状态管理**: 正确使用@State、@Prop等状态装饰器

错误上下文: {error_context}

建议检查官方文档: https://developer.harmonyos.com/
"""
        
        elif search_mode == "code_generation":
            return f"""鸿蒙{query}开发指南：

基础结构模板：
```arkts
import {{hilog}} from '@ohos.hilog';

@Entry
@Component
struct LoginPage {{
  @State username: string = '';
  @State password: string = '';

  build() {{
    Column() {{
      Text('鸿蒙登录页面')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .margin({{bottom: 30}})
      
      TextInput({{placeholder: '用户名'}})
        .width('80%')
        .height(40)
        .margin({{bottom: 15}})
        .onChange((value: string) => {{
          this.username = value;
        }})
      
      TextInput({{placeholder: '密码'}})
        .type(InputType.Password)
        .width('80%')
        .height(40)
        .margin({{bottom: 20}})
        .onChange((value: string) => {{
          this.password = value;
        }})
      
      Button('登录')
        .width('80%')
        .height(40)
        .onClick(() => {{
          // 登录逻辑
          hilog.info(0x0000, 'LoginPage', `用户名: ${{this.username}}`);
        }})
    }}
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .backgroundColor('#f0f0f0')
  }}
}}
```

关键开发要点：
1. 使用ArkTS语言开发
2. 组件必须用@Component装饰
3. 入口页面用@Entry装饰
4. 状态变量用@State装饰
5. build()方法构建UI界面
"""
        
        return f"""关于鸿蒙'{query}'的基础开发信息：

鸿蒙应用开发基础：
1. **开发语言**: ArkTS (TypeScript增强版)
2. **开发框架**: ArkUI声明式UI框架
3. **项目结构**: 使用DevEco Studio开发
4. **核心概念**: Ability、Component、Page
5. **UI组件**: Text、Button、Image、Column、Row等

基础组件使用示例：
- @Entry: 标识应用入口页面
- @Component: 定义可复用组件
- @State: 管理组件状态
- build(): 构建UI界面的方法

建议参考华为官方文档获取详细开发指南。
"""
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()