#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SearchAgent - 华为文档智能搜索代理
整合本地RAG搜索和在线搜索，提供智能搜索代理服务
现在增加了华为操作系统代码生成功能
"""

import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json
from abc import ABC, abstractmethod

# 导入现有模块
from .adapter import HuaweiDeepSearcherAdapter
from .online_search import EnhancedOnlineSearchEngine
from .pipeline import HuaweiRAGPipeline

# 导入DeepSearcher组件
try:
    from deepsearcher.configuration import config, init_config
    # 初始化DeepSearcher配置
    try:
        init_config(config)
        from deepsearcher.configuration import llm, embedding_model, vector_db
        from deepsearcher.agent.chain_of_rag import ChainOfRAG
        from deepsearcher.agent.deep_search import DeepSearch
        from deepsearcher.agent.chain_of_search import ChainOfSearchOnly
        from deepsearcher.vector_db.base import RetrievalResult
        logging.info("✅ DeepSearcher组件初始化成功")
    except Exception as init_error:
        logging.warning(f"DeepSearcher组件初始化失败: {init_error}")
        llm = embedding_model = vector_db = None
        ChainOfRAG = DeepSearch = ChainOfSearchOnly = RetrievalResult = None
except ImportError as e:
    logging.warning(f"DeepSearcher模块导入失败: {e}")
    llm = embedding_model = vector_db = None
    ChainOfRAG = DeepSearch = ChainOfSearchOnly = RetrievalResult = None

logger = logging.getLogger(__name__)

class SearchMode(Enum):
    """搜索模式枚举"""
    LOCAL_ONLY = "local_only"           # 仅本地搜索
    ONLINE_ONLY = "online_only"         # 仅在线搜索
    HYBRID = "hybrid"                   # 混合搜索
    ADAPTIVE = "adaptive"               # 自适应搜索
    CHAIN_OF_SEARCH = "chain_of_search" # 链式搜索
    CODE_GENERATION = "code_generation" # 代码生成模式

class QueryType(Enum):
    """查询类型枚举"""
    FACTUAL = "factual"           # 事实性查询
    PROCEDURAL = "procedural"     # 过程性查询  
    CONCEPTUAL = "conceptual"     # 概念性查询
    TROUBLESHOOTING = "troubleshooting"  # 故障排除
    CODE_EXAMPLE = "code_example" # 代码示例
    GENERAL = "general"           # 通用查询

@dataclass
class SearchContext:
    """搜索上下文"""
    session_id: str
    query_history: List[str]
    search_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    domain_focus: str = "huawei"
    
@dataclass
class SearchResult:
    """搜索结果数据结构"""
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    search_mode: SearchMode
    query_type: QueryType
    confidence_score: float
    processing_time: float
    token_usage: int
    metadata: Dict[str, Any]

@dataclass
class CodeGenerationResult:
    """代码生成结果数据结构"""
    original_query: str
    search_answer: str
    initial_code: str
    code_review: str
    final_code: str
    generation_metadata: Dict[str, Any]
    code_review_result: Optional['CodeReviewResult'] = None  # 使用前向引用

@dataclass
class CodeReviewRequest:
    """代码检查请求数据结构"""
    original_query: str
    code: str
    language: str = "unknown"
    review_type: str = "comprehensive"  # comprehensive, syntax, security, performance
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class CodeReviewResult:
    """代码检查结果数据结构"""
    request_id: str
    original_query: str
    code: str
    review_report: str
    issues_found: List[Dict[str, Any]]
    suggestions: List[str]
    score: float  # 0-100的代码质量评分
    review_metadata: Dict[str, Any]
    processing_time: float
    
    def __post_init__(self):
        if self.review_metadata is None:
            self.review_metadata = {}

class CodeReviewInterface(ABC):
    """代码检查接口抽象类"""
    
    @abstractmethod
    async def review_code(self, request: CodeReviewRequest) -> CodeReviewResult:
        """
        执行代码检查
        
        Args:
            request: 代码检查请求
            
        Returns:
            代码检查结果
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查代码检查服务是否可用"""
        pass

class LLMCodeReviewService(CodeReviewInterface):
    """基于LLM的代码检查服务（当前实现）"""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.review_count = 0
        
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.llm is not None
    
    async def review_code(self, request: CodeReviewRequest) -> CodeReviewResult:
        """
        使用LLM进行代码检查
        
        Args:
            request: 代码检查请求
            
        Returns:
            代码检查结果
        """
        start_time = time.time()
        request_id = f"review_{int(time.time())}_{self.review_count}"
        self.review_count += 1
        
        try:
            if not self.is_available():
                raise ValueError("LLM代码检查服务不可用")
            
            # 构建检查提示词
            review_prompt = self._build_review_prompt(request)
            
            # 调用LLM进行检查
            response = self.llm.chat([{"role": "user", "content": review_prompt}])
            review_content = self.llm.remove_think(response.content)
            
            # 解析检查结果
            review_result = self._parse_review_result(
                request_id, request, review_content, response.total_tokens
            )
            
            review_result.processing_time = time.time() - start_time
            
            logger.info(f"✅ 代码检查完成: {request_id}")
            return review_result
            
        except Exception as e:
            logger.error(f"❌ 代码检查失败: {e}")
            # 返回错误结果
            return CodeReviewResult(
                request_id=request_id,
                original_query=request.original_query,
                code=request.code,
                review_report=f"代码检查失败: {str(e)}",
                issues_found=[{"type": "error", "message": str(e)}],
                suggestions=[],
                score=0.0,
                review_metadata={"error": str(e), "token_usage": 0},
                processing_time=time.time() - start_time
            )
    
    def _build_review_prompt(self, request: CodeReviewRequest) -> str:
        """构建代码检查提示词"""
        base_prompt = f"""
作为高级代码审查专家，请对以下华为操作系统相关代码进行全面评价：

原始需求：{request.original_query}
代码语言：{request.language}
检查类型：{request.review_type}

待评价代码：
```
{request.code}
```

请从以下几个方面进行评价并给出结构化的评价报告：

1. 代码正确性：语法是否正确，逻辑是否合理
2. 华为规范性：是否符合华为开发规范和最佳实践
3. 功能完整性：是否满足用户需求
4. 代码质量：可读性、可维护性、性能等
5. 安全性：是否存在安全隐患
6. 改进建议：具体的优化建议

请按以下格式返回评价结果：

## 总体评价
[总体评价内容]

## 发现的问题
[列出具体问题，每个问题包含类型、位置、描述]

## 改进建议
[具体的改进建议列表]

## 质量评分
[给出0-100的质量评分及理由]

## 详细分析
[详细的技术分析]
"""
        
        # 根据检查类型调整提示词
        if request.review_type == "syntax":
            base_prompt += "\n特别关注：语法错误和基本逻辑问题"
        elif request.review_type == "security":
            base_prompt += "\n特别关注：安全漏洞和潜在风险"
        elif request.review_type == "performance":
            base_prompt += "\n特别关注：性能优化和效率问题"
        
        return base_prompt
    
    def _parse_review_result(self, request_id: str, request: CodeReviewRequest, 
                           review_content: str, token_usage: int) -> CodeReviewResult:
        """解析LLM返回的检查结果"""
        
        # 提取各个部分
        sections = review_content.split('## ')
        
        review_report = review_content
        issues_found = []
        suggestions = []
        score = 70.0  # 默认评分
        
        try:
            for section in sections:
                if section.startswith('发现的问题'):
                    issues_text = section.replace('发现的问题\n', '').strip()
                    # 简单解析问题列表
                    for line in issues_text.split('\n'):
                        if line.strip() and ('问题' in line or '错误' in line or '警告' in line):
                            issues_found.append({
                                "type": "issue",
                                "message": line.strip(),
                                "severity": "medium"
                            })
                
                elif section.startswith('改进建议'):
                    suggestions_text = section.replace('改进建议\n', '').strip()
                    for line in suggestions_text.split('\n'):
                        if line.strip() and line.strip().startswith(('-', '*', '•')):
                            suggestions.append(line.strip())
                
                elif section.startswith('质量评分'):
                    score_text = section.replace('质量评分\n', '').strip()
                    # 尝试提取数字评分
                    import re
                    score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                    if score_match:
                        score = float(score_match.group(1))
                        if score > 100:
                            score = score / 10  # 如果是1000制，转换为100制
        
        except Exception as e:
            logger.warning(f"解析检查结果时出错: {e}")
        
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            review_report=review_report,
            issues_found=issues_found,
            suggestions=suggestions,
            score=score,
            review_metadata={
                "token_usage": token_usage,
                "review_type": request.review_type,
                "language": request.language
            },
            processing_time=0.0  # 将在外部设置
        )

class HuaweiSearchAgent:
    """
    华为文档智能搜索代理
    
    整合本地RAG搜索、在线搜索和智能代理功能，
    提供统一的智能搜索服务接口
    现在支持华为操作系统代码生成功能
    """
    
    def __init__(self, 
                 config_file: str = None,
                 collection_name: str = "huawei_docs",
                 default_search_mode: SearchMode = SearchMode.ADAPTIVE,
                 max_context_length: int = 10,
                 code_review_service: CodeReviewInterface = None):
        """
        初始化华为搜索代理
        
        Args:
            config_file: 配置文件路径
            collection_name: 向量数据库集合名称
            default_search_mode: 默认搜索模式
            max_context_length: 最大上下文长度
            code_review_service: 自定义代码检查服务（可选）
        """
        self.config_file = config_file
        self.collection_name = collection_name
        self.default_search_mode = default_search_mode
        self.max_context_length = max_context_length
        
        # 初始化组件
        self._initialize_components(config_file)
        
        # 初始化代码检查服务
        if code_review_service:
            self.code_review_service = code_review_service
            logger.info("✅ 使用自定义代码检查服务")
        else:
            # 使用新的统一代码检查器替代LLM服务
            try:
                from huawei_rag.services import UnifiedCodeChecker, create_simple_config
                self.code_review_service = UnifiedCodeChecker(config=create_simple_config())
                logger.info("✅ 使用统一代码检查服务 (ESLint + Cppcheck)")
            except ImportError as e:
                logger.warning(f"统一代码检查服务导入失败: {e}")
                # 回退到LLM服务
                self.code_review_service = LLMCodeReviewService(llm_client=llm)
                logger.info("✅ 回退到LLM代码检查服务")
        
        # 搜索上下文管理
        self.active_contexts: Dict[str, SearchContext] = {}
        
        # 统计信息
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "mode_usage": {mode.value: 0 for mode in SearchMode},
            "code_generation_count": 0,
            "code_review_count": 0  # 新增代码检查统计
        }
        
        logger.info("✅ 华为搜索代理初始化完成")
    
    def _initialize_components(self, config_file: str = None):
        """初始化各个搜索组件"""
        try:
            # 尝试独立初始化本地适配器，不依赖全局DeepSearcher配置
            self.local_adapter = HuaweiDeepSearcherAdapter(
                collection_name=self.collection_name
            )
            logger.info("✅ 本地搜索适配器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 本地搜索适配器初始化失败: {e}")
            # 如果全局DeepSearcher配置失败，尝试手动初始化配置
            try:
                logger.info("🔄 尝试手动初始化DeepSearcher配置...")
                from deepsearcher.configuration import init_config, config
                init_config(config)
                
                # 重试初始化本地适配器
                self.local_adapter = HuaweiDeepSearcherAdapter(
                    collection_name=self.collection_name
                )
                logger.info("✅ 手动配置后本地搜索适配器初始化成功")
            except Exception as retry_error:
                logger.error(f"❌ 手动初始化也失败: {retry_error}")
                self.local_adapter = None
        
        try:
            # 初始化在线搜索引擎
            self.online_engine = EnhancedOnlineSearchEngine()
            logger.info("✅ 在线搜索引擎初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 在线搜索引擎初始化失败: {e}")
        
        try:
            # 初始化RAG流水线
            self.rag_pipeline = HuaweiRAGPipeline(config_file=config_file)
            logger.info("✅ RAG流水线初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ RAG流水线初始化失败: {e}")
    
    def _classify_query_type(self, query: str) -> QueryType:
        """
        使用LLM分类查询类型
        
        Args:
            query: 用户查询
            
        Returns:
            查询类型
        """
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
        """
        智能选择搜索模式
        
        Args:
            query: 用户查询
            query_type: 查询类型
            context: 搜索上下文
            
        Returns:
            推荐的搜索模式
        """
        if self.default_search_mode != SearchMode.ADAPTIVE:
            return self.default_search_mode
        
        # 检查是否为代码生成请求
        code_keywords = ["生成代码", "代码示例", "写代码", "实现代码", "代码实现", "编程示例"]
        if any(keyword in query for keyword in code_keywords):
            return SearchMode.CODE_GENERATION
        
        # 基于查询类型的启发式规则
        if query_type == QueryType.CODE_EXAMPLE:
            # 代码示例可能需要代码生成
            return SearchMode.CODE_GENERATION
        elif query_type == QueryType.TROUBLESHOOTING:
            # 故障排除优先在线搜索（获取最新解决方案）
            return SearchMode.ONLINE_ONLY
        elif query_type == QueryType.FACTUAL:
            # 事实性查询使用混合搜索
            return SearchMode.HYBRID
        elif query_type in [QueryType.PROCEDURAL, QueryType.CONCEPTUAL]:
            # 过程性和概念性查询使用链式搜索
            return SearchMode.CHAIN_OF_SEARCH
        else:
            # 默认使用混合搜索
            return SearchMode.HYBRID
    
    async def search(self, 
                    query: str,
                    search_mode: SearchMode = None,
                    session_id: str = None,
                    top_k: int = 5,
                    **kwargs) -> SearchResult:
        """
        执行智能搜索
        
        Args:
            query: 搜索查询
            search_mode: 搜索模式（如果为None则自动选择）
            session_id: 会话ID
            top_k: 返回结果数量
            **kwargs: 其他参数
            
        Returns:
            搜索结果
        """
        start_time = time.time()
        
        try:
            # 更新统计
            self.stats["total_queries"] += 1
            
            # 获取或创建搜索上下文
            context = self._get_or_create_context(session_id, query)
            
            # 分类查询类型
            query_type = self._classify_query_type(query)
            logger.info(f"🏷️ 查询类型: {query_type.value}")
            
            # 选择搜索模式
            if search_mode is None:
                search_mode = self._select_search_mode(query, query_type, context)
            
            logger.info(f"🎯 选择搜索模式: {search_mode.value}")
            self.stats["mode_usage"][search_mode.value] += 1
            
            # 执行搜索
            answer, sources, token_usage = await self._execute_search(
                query, search_mode, query_type, top_k, **kwargs
            )
            
            # 计算置信度
            confidence_score = self._calculate_confidence(answer, sources, search_mode)
            
            # 更新上下文
            self._update_context(context, query, answer, sources)
            
            # 创建搜索结果
            processing_time = time.time() - start_time
            result = SearchResult(
                query=query,
                answer=answer,
                sources=sources,
                search_mode=search_mode,
                query_type=query_type,
                confidence_score=confidence_score,
                processing_time=processing_time,
                token_usage=token_usage,
                metadata={
                    "session_id": session_id,
                    "context_length": len(context.query_history) if context else 0
                }
            )
            
            # 更新统计
            self.stats["successful_queries"] += 1
            self.stats["average_response_time"] = (
                (self.stats["average_response_time"] * (self.stats["successful_queries"] - 1) + processing_time) 
                / self.stats["successful_queries"]
            )
            
            logger.info(f"✅ 搜索完成，耗时 {processing_time:.2f}s，置信度 {confidence_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            processing_time = time.time() - start_time
            
            # 返回错误结果
            return SearchResult(
                query=query,
                answer=f"搜索过程中发生错误: {str(e)}",
                sources=[],
                search_mode=search_mode or SearchMode.ADAPTIVE,
                query_type=QueryType.GENERAL,
                confidence_score=0.0,
                processing_time=processing_time,
                token_usage=0,
                metadata={"error": str(e)}
            )
    
    async def _execute_search(self, 
                             query: str, 
                             search_mode: SearchMode, 
                             query_type: QueryType,
                             top_k: int,
                             **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """
        执行具体的搜索逻辑
        
        Args:
            query: 搜索查询
            search_mode: 搜索模式
            query_type: 查询类型
            top_k: 返回结果数量
            **kwargs: 其他参数
            
        Returns:
            (答案, 信息源列表, token使用量)
        """
        if search_mode == SearchMode.LOCAL_ONLY:
            return await self._local_search(query, top_k, **kwargs)
        elif search_mode == SearchMode.ONLINE_ONLY:
            return await self._online_search(query, top_k, **kwargs)
        elif search_mode == SearchMode.HYBRID:
            return await self._hybrid_search(query, top_k, **kwargs)
        elif search_mode == SearchMode.CHAIN_OF_SEARCH:
            return await self._chain_of_search(query, top_k, **kwargs)
        elif search_mode == SearchMode.CODE_GENERATION:
            return await self._code_generation_search(query, top_k, **kwargs)
        else:
            # 默认使用混合搜索
            return await self._hybrid_search(query, top_k, **kwargs)
    
    async def _local_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """本地搜索"""
        if not self.local_adapter:
            return "本地搜索服务不可用：适配器未初始化。请确保向量数据库和嵌入模型已正确配置。", [], 0
        
        try:
            results = self.local_adapter.search_huawei_docs(
                query=query,
                top_k=top_k,
                **kwargs
            )
            
            # 生成答案
            if results and llm:
                context = "\n".join([r.get('content', '') for r in results[:3]])
                answer_prompt = f"""
基于以下华为文档内容，回答用户问题：

问题: {query}

文档内容:
{context}

请提供准确、详细的答案：
"""
                response = llm.chat([{"role": "user", "content": answer_prompt}])
                answer = llm.remove_think(response.content)
                token_usage = response.total_tokens
            else:
                if results:
                    # 有结果但LLM不可用，返回搜索结果摘要
                    answer = f"找到 {len(results)} 个相关文档：\n"
                    for i, r in enumerate(results[:3], 1):
                        answer += f"{i}. {r.get('title', '未知标题')}\n   {r.get('content', '')[:100]}...\n"
                else:
                    answer = "未找到相关文档"
                token_usage = 0
            
            sources = [
                {
                    "title": r.get('title', '未知标题'),
                    "url": r.get('url', ''),
                    "content": r.get('content', '')[:200] + "...",
                    "score": r.get('score', 0),
                    "source_type": "local"
                }
                for r in results
            ]
            
            return answer, sources, token_usage
            
        except Exception as e:
            logger.error(f"本地搜索失败: {e}")
            return f"本地搜索失败: {str(e)}", [], 0
    
    async def _online_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """在线搜索"""
        if not self.online_engine:
            return "在线搜索服务不可用", [], 0
        
        try:
            answer, documents = self.online_engine.search_and_answer(query)
            
            sources = [
                {
                    "title": doc.get('title', '未知标题'),
                    "url": doc.get('url', ''),
                    "content": doc.get('content', '')[:200] + "...",
                    "score": doc.get('relevance_score', 0),
                    "source_type": "online"
                }
                for doc in documents[:top_k]
            ]
            
            # 估算token使用量（在线搜索中已使用）
            token_usage = len(answer) // 4  # 粗略估算
            
            return answer, sources, token_usage
            
        except Exception as e:
            logger.error(f"在线搜索失败: {e}")
            return f"在线搜索失败: {str(e)}", [], 0
    
    async def _hybrid_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """混合搜索"""
        # 并行执行本地和在线搜索
        local_task = self._local_search(query, top_k // 2, **kwargs)
        online_task = self._online_search(query, top_k // 2, **kwargs)
        
        local_result, online_result = await asyncio.gather(local_task, online_task, return_exceptions=True)
        
        # 处理异常结果
        if isinstance(local_result, Exception):
            local_answer, local_sources, local_tokens = f"本地搜索异常: {local_result}", [], 0
        else:
            local_answer, local_sources, local_tokens = local_result
        
        if isinstance(online_result, Exception):
            online_answer, online_sources, online_tokens = f"在线搜索异常: {online_result}", [], 0
        else:
            online_answer, online_sources, online_tokens = online_result
        
        # 合并结果
        all_sources = local_sources + online_sources
        
        # 生成综合答案
        if llm and (local_sources or online_sources):
            synthesis_prompt = f"""
请基于本地搜索和在线搜索的结果，为用户问题提供综合答案：

用户问题: {query}

本地搜索答案:
{local_answer}

在线搜索答案:
{online_answer}

请提供一个综合、准确的最终答案：
"""
            response = llm.chat([{"role": "user", "content": synthesis_prompt}])
            final_answer = llm.remove_think(response.content)
            total_tokens = local_tokens + online_tokens + response.total_tokens
        else:
            final_answer = f"本地搜索: {local_answer}\n\n在线搜索: {online_answer}"
            total_tokens = local_tokens + online_tokens
        
        return final_answer, all_sources, total_tokens
    
    async def _chain_of_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """链式搜索"""
        if not ChainOfRAG or not llm or not embedding_model or not vector_db:
            # 降级到混合搜索
            return await self._hybrid_search(query, top_k, **kwargs)
        
        try:
            # 使用ChainOfRAG进行多步推理搜索
            chain_rag = ChainOfRAG(
                llm=llm,
                embedding_model=embedding_model,
                vector_db=vector_db,
                max_iter=3,
                early_stopping=True
            )
            
            answer, retrieved_results, token_usage = chain_rag.query(query, top_k=top_k)
            
            sources = [
                {
                    "title": result.metadata.get('title', '未知标题'),
                    "url": result.metadata.get('url', ''),
                    "content": result.text[:200] + "...",
                    "score": result.score,
                    "source_type": "chain_search"
                }
                for result in retrieved_results[:top_k]
            ]
            
            return answer, sources, token_usage
            
        except Exception as e:
            logger.error(f"链式搜索失败: {e}")
            # 降级到混合搜索
            return await self._hybrid_search(query, top_k, **kwargs)
    
    async def _code_generation_search(self, query: str, top_k: int, **kwargs) -> Tuple[str, List[Dict[str, Any]], int]:
        """
        代码生成搜索：先搜索文档，然后生成华为操作系统相关代码
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            **kwargs: 其他参数
            
        Returns:
            (最终答案包含代码, 信息源列表, token使用量)
        """
        if not llm:
            return "代码生成服务不可用：LLM未初始化", [], 0
        
        try:
            logger.info(f"🔨 开始代码生成流程: {query}")
            
            # 步骤1：先执行文档搜索获取相关信息
            logger.info("📚 步骤1：搜索相关文档...")
            search_answer, sources, search_tokens = await self._hybrid_search(query, top_k, **kwargs)
            
            # 步骤2：基于搜索结果生成华为操作系统相关代码
            logger.info("💻 步骤2：生成华为操作系统代码...")
            initial_code, code_gen_tokens = await self._generate_huawei_code(query, search_answer, sources)
            
            # 步骤3：使用新的代码检查服务进行评价
            logger.info("🔍 步骤3：进行代码检查...")
            code_review_result = await self._review_code_with_service(query, initial_code)
            
            # 步骤4：基于评价结果生成最终优化代码
            logger.info("✨ 步骤4：生成最终优化代码...")
            final_code, final_tokens = await self._generate_final_code(
                query, initial_code, code_review_result.review_report
            )
            
            # 更新统计
            self.stats["code_generation_count"] += 1
            
            # 组织最终答案，包含初始代码信息
            final_answer = self._format_code_generation_result(
                query, search_answer, initial_code, code_review_result.review_report, final_code,
                code_review_result
            )
            
            # 计算总token使用量
            total_tokens = (search_tokens + code_gen_tokens + 
                          code_review_result.review_metadata.get('token_usage', 0) + final_tokens)
            
            # 添加代码生成标记到sources
            for source in sources:
                source["code_generated"] = True
                source["initial_code_generated"] = True
                source["code_reviewed"] = True
                source["final_code_generated"] = True
            
            # 保存代码生成的详细信息到元数据
            if sources:
                sources[0]["code_generation_details"] = {
                    "initial_code": initial_code,
                    "code_review_result": code_review_result,  # 保存完整的检查结果对象
                    "review_result": {
                        "request_id": code_review_result.request_id,
                        "score": code_review_result.score,
                        "issues_count": len(code_review_result.issues_found),
                        "suggestions_count": len(code_review_result.suggestions)
                    }
                }
            
            logger.info("✅ 代码生成流程完成")
            return final_answer, sources, total_tokens
            
        except Exception as e:
            logger.error(f"❌ 代码生成失败: {e}")
            return f"代码生成失败: {str(e)}", [], 0
    
    async def _generate_huawei_code(self, query: str, search_context: str, sources: List[Dict]) -> Tuple[str, int]:
        """
        基于搜索结果生成华为操作系统相关代码
        
        Args:
            query: 原始查询
            search_context: 搜索得到的上下文信息
            sources: 信息源列表
            
        Returns:
            (生成的代码, token使用量)
        """
        try:
            # 构建代码生成提示词
            code_prompt = f"""
作为华为操作系统开发专家，请基于以下文档信息，为用户需求生成相应的华为操作系统相关代码。

用户需求: {query}

参考文档信息:
{search_context}

请生成符合以下要求的代码：
1. 代码必须与华为操作系统（如HarmonyOS、鸿蒙系统）相关
2. 使用华为官方推荐的开发语言和框架（如ArkTS、ArkUI等）
3. 遵循华为开发规范和最佳实践
4. 代码应该是完整的、可运行的示例
5. 包含适当的注释说明

请生成代码，并简要说明代码的功能和使用方法：
"""
            
            response = llm.chat([{"role": "user", "content": code_prompt}])
            code = llm.remove_think(response.content)
            
            return code, response.total_tokens
            
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            return f"代码生成失败: {str(e)}", 0
    
    async def _review_code_with_service(self, query: str, code: str) -> CodeReviewResult:
        """
        使用代码检查服务进行代码评价
        
        Args:
            query: 原始查询
            code: 待评价的代码
            
        Returns:
            代码检查结果
        """
        try:
            # 尝试检测代码语言
            language = self._detect_code_language(code)
            
            # 创建检查请求（使用 shared.interfaces 中的类）
            from shared.interfaces import CodeReviewRequest as SharedCodeReviewRequest
            request = SharedCodeReviewRequest(
                original_query=query,
                code=code,
                language=language,
                review_type="comprehensive"
            )
            
            # 执行检查（返回 shared.interfaces.CodeReviewResult）
            shared_result = await self.code_review_service.review_code(request)
            
            # 将 shared.interfaces.CodeReviewResult 转换为 huawei_rag 中的 CodeReviewResult
            huawei_result = CodeReviewResult(
                request_id=shared_result.request_id,
                original_query=shared_result.original_query,
                code=shared_result.code,
                review_report=shared_result.report,  # 转换属性名：report -> review_report
                issues_found=shared_result.issues,   # 转换属性名：issues -> issues_found
                suggestions=shared_result.suggestions,
                score=float(shared_result.score),
                review_metadata=shared_result.metadata or {},  # 转换属性名：metadata -> review_metadata
                processing_time=shared_result.execution_time   # 转换属性名：execution_time -> processing_time
            )
            
            return huawei_result
            
        except Exception as e:
            logger.error(f"代码检查服务调用失败: {e}")
            # 如果服务失败，回退到原始方法
            logger.info("回退到原始代码检查方法")
            review_text, token_usage = await self._review_code(query, code)
            
            # 构造兼容的结果
            return CodeReviewResult(
                request_id=f"fallback_{int(time.time())}",
                original_query=query,
                code=code,
                review_report=review_text,
                issues_found=[],
                suggestions=[],
                score=70.0,
                review_metadata={"token_usage": token_usage, "fallback": True},
                processing_time=0.0
            )
    
    def _detect_code_language(self, code: str) -> str:
        """
        优化的代码语言检测 - 增强ArkTS识别能力
        
        Args:
            code: 代码字符串
            
        Returns:
            检测到的语言
        """
        code_lower = code.lower()
        code_lines = code.split('\n')
        
        # ArkTS 特征检测（优先级最高）
        arkts_decorators = ['@entry', '@component', '@state', '@prop', '@link', '@provide', 
                           '@consume', '@objectlink', '@observed', '@watch', '@builder', 
                           '@extend', '@styles', '@preview']
        arkts_keywords = ['struct', 'build()', 'abouttoappear', 'abouttodisappear', 
                         'onpageshow', 'onpagehide', 'onbackpress']
        arkts_ui_components = ['column', 'row', 'stack', 'flex', 'text', 'button', 
                              'image', 'list', 'listitem', 'grid', 'griditem', 'scroll']
        
        # 检查 ArkTS 装饰器
        if any(decorator in code_lower for decorator in arkts_decorators):
            return "arkts"
        
        # 检查 ArkTS 关键字
        if any(keyword in code_lower for keyword in arkts_keywords):
            return "arkts"
        
        # 检查 ArkTS UI 组件
        if any(component in code_lower for component in arkts_ui_components):
            # 进一步检查是否是 ArkTS 语法
            if 'struct' in code_lower or any(decorator in code_lower for decorator in arkts_decorators[:3]):
                return "arkts"
        
        # 检查文件扩展名相关的语法模式
        if '.ets' in code_lower or 'export struct' in code_lower:
            return "arkts"
        
        # 检查 ArkTS 特有的语法模式
        for line in code_lines:
            line_lower = line.lower().strip()
            # ArkTS 组件定义模式
            if line_lower.startswith('struct ') and '{' in line:
                return "arkts"
            # ArkTS build 方法模式
            if line_lower.startswith('build()') or 'build() {' in line_lower:
                return "arkts"
            # ArkTS 状态变量模式
            if line_lower.startswith('@state') or line_lower.startswith('@prop'):
                return "arkts"
        
        # TypeScript 检测
        typescript_indicators = ['interface ', 'type ', 'enum ', 'namespace ', 'declare ', 
                               'import type', 'export type', 'as const', 'readonly ', 
                               'keyof ', 'typeof ', 'extends ', 'implements ']
        typescript_generics = ['<T>', '<T,', '<T extends', '<K,', '<V>', 'Array<', 'Promise<']
        
        if any(indicator in code_lower for indicator in typescript_indicators):
            return "typescript"
        
        if any(generic in code for generic in typescript_generics):
            return "typescript"
        
        # 检查 TypeScript 类型注解
        if ':' in code and any(pattern in code for pattern in [': string', ': number', ': boolean', 
                                                              ': object', ': any', ': void', 
                                                              ': Array<', ': Promise<']):
            return "typescript"
        
        # JavaScript 检测
        javascript_indicators = ['function ', 'var ', 'let ', 'const ', 'import ', 'export ', 
                               'class ', 'extends ', 'super(', 'this.', 'prototype.', 
                               'async ', 'await ', '=>', 'require(', 'module.exports']
        
        if any(indicator in code_lower for indicator in javascript_indicators):
            # 进一步区分 JavaScript 和 TypeScript
            if ':' in code and any(type_hint in code for type_hint in [': string', ': number', ': boolean']):
                return "typescript"
            return "javascript"
        
        # Java 检测
        java_indicators = ['public class', 'private class', 'protected class', 'public static void main',
                          'package ', 'import java.', 'System.out.', 'public void ', 'private void ',
                          'protected void ', 'public int ', 'private int ', 'String[]', 'ArrayList<']
        
        if any(indicator in code_lower for indicator in java_indicators):
            return "java"
        
        # Python 检测
        python_indicators = ['def ', 'class ', 'import ', 'from ', 'if __name__', 'print(', 
                           'self.', 'elif ', 'with ', 'as ', 'lambda ', 'yield ', 'async def']
        
        if any(indicator in code_lower for indicator in python_indicators):
            return "python"
        
        # C/C++ 检测
        cpp_indicators = ['#include', 'int main', 'std::', 'using namespace', 'cout <<', 
                         'cin >>', 'endl', 'printf(', 'scanf(', 'malloc(', 'free(']
        
        if any(indicator in code_lower for indicator in cpp_indicators):
            return "cpp"
        
        # Vue 检测
        vue_indicators = ['<template>', '<script>', '<style>', 'export default', 'Vue.', 
                         'v-if', 'v-for', 'v-model', '@click', ':class', ':style']
        
        if any(indicator in code_lower for indicator in vue_indicators):
            return "vue"
        
        # HTML 检测
        html_indicators = ['<!doctype', '<html', '<head>', '<body>', '<div', '<span', 
                          '<p>', '<a href', '<img src', '<script src']
        
        if any(indicator in code_lower for indicator in html_indicators):
            return "html"
        
        # CSS 检测
        css_indicators = ['{', '}', ':', ';', 'px', 'em', 'rem', '%', 'color:', 'background:', 
                         'margin:', 'padding:', 'display:', 'position:', 'font-']
        
        if code.count('{') > 2 and code.count('}') > 2 and ':' in code and ';' in code:
            if any(indicator in code_lower for indicator in css_indicators):
                return "css"
        
        # JSON 检测
        if code.strip().startswith('{') and code.strip().endswith('}'):
            try:
                import json
                json.loads(code)
                return "json"
            except:
                pass
        
        # 默认返回 unknown
        return "unknown"
    
    async def _review_code(self, query: str, code: str) -> Tuple[str, int]:
        """
        对生成的代码进行评价和检查
        
        Args:
            query: 原始查询
            code: 待评价的代码
            
        Returns:
            (评价结果, token使用量)
        """
        try:
            review_prompt = f"""
作为高级代码审查专家，请对以下华为操作系统相关代码进行全面评价：

原始需求：{query}

待评价代码：
{code}

请从以下几个方面进行评价：
1. 代码正确性：语法是否正确，逻辑是否合理
2. 华为规范性：是否符合华为开发规范和最佳实践
3. 功能完整性：是否满足用户需求
4. 代码质量：可读性、可维护性、性能等
5. 安全性：是否存在安全隐患
6. 改进建议：具体的优化建议

请提供详细的评价报告：
"""
            
            response = llm.chat([{"role": "user", "content": review_prompt}])
            review = llm.remove_think(response.content)
            
            return review, response.total_tokens
            
        except Exception as e:
            logger.error(f"代码评价失败: {e}")
            return f"代码评价失败: {str(e)}", 0
    
    async def _generate_final_code(self, query: str, initial_code: str, review: str) -> Tuple[str, int]:
        """
        基于评价结果生成最终优化的代码
        
        Args:
            query: 原始查询
            initial_code: 初始代码
            review: 代码评价
            
        Returns:
            (最终优化代码, token使用量)
        """
        try:
            final_prompt = f"""
基于代码评价结果，请生成最终优化的华为操作系统代码：

原始需求：{query}

初始代码：
{initial_code}

代码评价：
{review}

请根据评价中的建议，生成最终优化的代码：
1. 修复所有指出的问题
2. 应用所有改进建议
3. 确保代码的正确性和完整性
4. 保持代码的清晰性和可维护性
5. 添加必要的注释和文档

请提供最终的完整代码：
"""
            
            response = llm.chat([{"role": "user", "content": final_prompt}])
            final_code = llm.remove_think(response.content)
            
            return final_code, response.total_tokens
            
        except Exception as e:
            logger.error(f"最终代码生成失败: {e}")
            return f"最终代码生成失败: {str(e)}", 0
    
    def _format_code_generation_result(self, query: str, search_answer: str, 
                                     initial_code: str, review: str, final_code: str,
                                     code_review_result: CodeReviewResult = None) -> str:
        """
        格式化代码生成结果
        
        Args:
            query: 原始查询
            search_answer: 搜索答案
            initial_code: 初始代码
            review: 代码评价
            final_code: 最终代码
            code_review_result: 代码检查结果（新增）
            
        Returns:
            格式化的最终答案（包含详细的代码检查信息）
        """
        result = f"""## 华为代码生成结果

### 用户需求
{query}

### 最终生成代码
```
{final_code}
```

### 🔍 代码检查详情"""
        
        if code_review_result:
            # 基本检查信息
            result += f"""
**检查器服务**: {code_review_result.review_metadata.get('service', '未知')}
**检查语言**: {code_review_result.review_metadata.get('language', '未知')}
**代码质量评分**: {code_review_result.score}/100
**处理时间**: {code_review_result.processing_time:.2f}秒
**检查ID**: {code_review_result.request_id}"""

            # 显示使用的具体检查器
            if code_review_result.review_metadata.get('unified_service'):
                selected_checker = code_review_result.review_metadata.get('selected_checker', '未知')
                result += f"""
**使用的检查器**: {selected_checker.upper()}
**统一检查服务**: ✅ 已启用"""
                
                # 如果使用了ESLint，显示ESLint特定信息
                if selected_checker == 'eslint':
                    result += f"""
**ESLint版本**: 已集成
**支持语言**: JavaScript, TypeScript, ArkTS"""
                
                # 如果使用了CppCheck，显示CppCheck特定信息
                elif selected_checker == 'cppcheck':
                    result += f"""
**CppCheck版本**: 已集成
**支持语言**: C, C++"""
            else:
                result += f"""
**检查方式**: LLM模拟检查（回退模式）"""

            result += f"""

#### 📋 发现的问题 ({len(code_review_result.issues_found)} 个)"""
            
            if code_review_result.issues_found:
                for i, issue in enumerate(code_review_result.issues_found, 1):
                    issue_type = issue.get('type', 'unknown')
                    severity = issue.get('severity', 'info')
                    message = issue.get('message', '未知问题')
                    line = issue.get('line', 0)
                    column = issue.get('column', 0)
                    rule = issue.get('rule', issue.get('rule_id', 'unknown'))
                    category = issue.get('category', 'general')
                    
                    # 根据严重程度选择图标
                    severity_icon = {
                        'error': '❌',
                        'warning': '⚠️', 
                        'info': 'ℹ️'
                    }.get(severity.lower(), '📝')
                    
                    result += f"""
{i}. {severity_icon} **[{severity.upper()}]** {message}"""
                    
                    if line > 0:
                        result += f"""
   📍 **位置**: 第 {line} 行""" + (f"，第 {column} 列" if column > 0 else "")
                    
                    result += f"""
   🔍 **规则**: `{rule}`
   📂 **分类**: {category}"""
                    
                    # 如果有修复建议
                    fix_suggestion = issue.get('fix_suggestion', '')
                    if fix_suggestion:
                        result += f"""
   💡 **修复建议**: {fix_suggestion}"""
            else:
                result += f"""
✅ **未发现问题，代码质量良好！**"""
            
            result += f"""

#### 💡 改进建议 ({len(code_review_result.suggestions)} 条)"""
            
            if code_review_result.suggestions:
                for i, suggestion in enumerate(code_review_result.suggestions, 1):
                    result += f"""
{i}. 💡 {suggestion}"""
            else:
                result += f"""
✅ **代码已经很好，暂无改进建议**"""
            
            # 显示技术细节
            result += f"""

#### 🔧 检查技术细节"""
            
            # 显示检查器元数据
            if code_review_result.review_metadata:
                result += f"""
- **Token使用量**: {code_review_result.review_metadata.get('token_usage', 'N/A')}
- **检查文件数**: {code_review_result.review_metadata.get('files_checked', 'N/A')}
- **总处理时间**: {code_review_result.review_metadata.get('total_processing_time', code_review_result.processing_time):.2f}秒"""
                
                # 如果是统一服务，显示更多细节
                if code_review_result.review_metadata.get('unified_service'):
                    result += f"""
- **检查器可用性**: ✅ 真实工具检查
- **回退状态**: 否"""
                else:
                    result += f"""
- **检查器可用性**: ⚠️ 使用LLM回退检查
- **回退原因**: 真实检查器不可用"""

            result += f"""

#### 📄 完整检查报告
```
{code_review_result.review_report}
```"""
        else:
            result += f"""
⚠️ **代码检查结果不可用**
- 可能原因：检查器初始化失败或服务不可用
- 建议：检查ESLint和CppCheck工具是否正确安装"""
        
        result += f"""

### 📝 初始代码（供调试参考）
```
{initial_code}
```

### 🎯 开发说明
- **代码来源**: 基于华为官方文档生成，遵循华为开发规范
- **质量保证**: 已通过专业静态分析工具检查和优化
- **使用建议**: 请根据具体环境和需求进行适当调整
- **问题排查**: 如有问题，请参考上述检查详情进行调试

### 📊 生成统计"""
        
        if code_review_result:
            result += f"""
- **代码质量评分**: {code_review_result.score}/100
- **发现问题数**: {len(code_review_result.issues_found)}
- **改进建议数**: {len(code_review_result.suggestions)}
- **检查器类型**: {code_review_result.review_metadata.get('selected_checker', '未知').upper()}"""
        
        result += f"""

---
*🚀 由华为代码生成系统自动生成 | 🔍 检查器: {code_review_result.review_metadata.get('selected_checker', '未知').upper() if code_review_result else '未知'} | ⏱️ 处理时间: {f'{code_review_result.processing_time:.2f}s' if code_review_result else 'N/A'}*"""
        
        return result.strip()
    
    def _get_or_create_context(self, session_id: str = None, query: str = "") -> Optional[SearchContext]:
        """获取或创建搜索上下文"""
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
        
        context = self.active_contexts[session_id]
        context.query_history.append(query)
        
        # 限制上下文长度
        if len(context.query_history) > self.max_context_length:
            context.query_history = context.query_history[-self.max_context_length:]
            context.search_history = context.search_history[-self.max_context_length:]
        
        return context
    
    def _update_context(self, context: SearchContext, query: str, answer: str, sources: List[Dict[str, Any]]):
        """更新搜索上下文"""
        if context:
            context.search_history.append({
                "query": query,
                "answer": answer,
                "sources_count": len(sources),
                "timestamp": time.time()
            })
    
    def _calculate_confidence(self, answer: str, sources: List[Dict[str, Any]], search_mode: SearchMode) -> float:
        """计算搜索结果的置信度"""
        confidence = 0.5  # 基础置信度
        
        # 基于信息源数量
        if sources:
            source_bonus = min(len(sources) * 0.1, 0.3)
            confidence += source_bonus
        
        # 基于搜索模式
        mode_bonus = {
            SearchMode.HYBRID: 0.2,
            SearchMode.CHAIN_OF_SEARCH: 0.15,
            SearchMode.LOCAL_ONLY: 0.1,
            SearchMode.ONLINE_ONLY: 0.1,
            SearchMode.ADAPTIVE: 0.05
        }
        confidence += mode_bonus.get(search_mode, 0)
        
        # 基于答案长度（合理范围内）
        if 100 <= len(answer) <= 2000:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        return self.stats.copy()
    
    def clear_context(self, session_id: str = None):
        """清除搜索上下文"""
        if session_id:
            self.active_contexts.pop(session_id, None)
        else:
            self.active_contexts.clear()
    
    def search_sync(self, query: str, **kwargs) -> SearchResult:
        """同步版本的搜索方法（兼容旧版本API）"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self.search(query, **kwargs))
            return result
        finally:
            loop.close()
    
    async def generate_code(self, 
                           query: str, 
                           session_id: str = None,
                           **kwargs) -> CodeGenerationResult:
        """
        专门的代码生成方法
        
        Args:
            query: 代码生成请求
            session_id: 会话ID
            **kwargs: 其他参数
            
        Returns:
            代码生成结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔨 开始代码生成: {query}")
            
            # 强制使用代码生成模式
            result = await self.search(
                query=query,
                search_mode=SearchMode.CODE_GENERATION,
                session_id=session_id,
                **kwargs
            )
            
            # 从sources中提取详细的代码生成信息
            initial_code = ""
            code_review_details = {}
            full_code_review_result = None  # 新增：完整的检查结果
            
            if result.sources and len(result.sources) > 0:
                source = result.sources[0]
                if "code_generation_details" in source:
                    details = source["code_generation_details"]
                    initial_code = details.get("initial_code", "")
                    code_review_details = details.get("review_result", {})
                    full_code_review_result = details.get("code_review_result")  # 提取完整结果
            
            # 解析结果以提取各个部分
            answer_sections = result.answer.split('## ')
            
            original_query = query
            search_answer = ""
            code_review = ""
            final_code = ""
            
            for section in answer_sections:
                if section.startswith('相关文档信息'):
                    search_answer = section.replace('相关文档信息\n', '').strip()
                elif section.startswith('最终生成代码'):
                    final_code = section.replace('最终生成代码\n', '').strip()
                elif section.startswith('代码评价摘要'):
                    code_review = section.replace('代码评价摘要\n', '').strip()
            
            # 组装元数据
            generation_metadata = {
                "processing_time": result.processing_time,
                "token_usage": result.token_usage,
                "sources_count": len(result.sources),
                "confidence_score": result.confidence_score,
                "code_review_details": code_review_details
            }
            
            code_result = CodeGenerationResult(
                original_query=original_query,
                search_answer=search_answer,
                initial_code=initial_code,  # 现在包含真实的初始代码
                code_review=code_review,
                final_code=final_code,
                generation_metadata=generation_metadata,
                code_review_result=full_code_review_result
            )
            
            logger.info("✅ 代码生成完成")
            return code_result
            
        except Exception as e:
            logger.error(f"❌ 代码生成失败: {e}")
            # 返回错误结果
            return CodeGenerationResult(
                original_query=query,
                search_answer="",
                initial_code="",
                code_review="",
                final_code=f"代码生成失败: {str(e)}",
                generation_metadata={"error": str(e)},
                code_review_result=None
            )
    
    def generate_code_sync(self, query: str, **kwargs) -> CodeGenerationResult:
        """同步版本的代码生成方法"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self.generate_code(query, **kwargs))
            return result
        finally:
            loop.close()
    
    async def review_code_standalone(self, 
                                   query: str, 
                                   code: str,
                                   language: str = "unknown",
                                   review_type: str = "comprehensive") -> CodeReviewResult:
        """
        独立的代码检查方法
        
        Args:
            query: 原始需求描述
            code: 待检查的代码
            language: 代码语言
            review_type: 检查类型 (comprehensive, syntax, security, performance)
            
        Returns:
            代码检查结果
        """
        try:
            logger.info(f"🔍 开始代码检查: {query[:50]}...")
            
            # 创建检查请求
            request = CodeReviewRequest(
                original_query=query,
                code=code,
                language=language,
                review_type=review_type
            )
            
            # 执行检查
            result = await self.code_review_service.review_code(request)
            
            # 更新统计
            self.stats["code_review_count"] += 1
            
            logger.info(f"✅ 代码检查完成: {result.request_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 代码检查失败: {e}")
            raise 