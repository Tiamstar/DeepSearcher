#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为RAG增强版在线搜索模块
专注于使用FireCrawl的智能搜索功能，移除基础搜索引擎依赖
"""

import logging
import time
import os
import random
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from firecrawl import FirecrawlApp, ScrapeOptions

# 导入DeepSearcher的LLM配置
from deepsearcher.configuration import llm, embedding_model, vector_db

logger = logging.getLogger(__name__)

class EnhancedOnlineSearchEngine:
    """
    增强版在线搜索引擎
    专门使用FireCrawl的智能搜索功能，针对华为文档进行优化
    """
    
    def __init__(self, 
                 max_search_results: int = 10,
                 max_sub_queries: int = 5,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        """
        初始化增强版在线搜索引擎
        
        Args:
            max_search_results: 最大搜索结果数量
            max_sub_queries: 最大子查询数量
            chunk_size: 文档分块大小
            chunk_overlap: 文档分块重叠大小
        """
        self.max_search_results = max_search_results
        self.max_sub_queries = max_sub_queries
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # LLM相关组件初始化为None，在使用时动态获取
        self.llm = None
        self.embedding_model = None
        self.vector_db = None
        
        # 初始化FireCrawl
        try:
            api_key = os.getenv("FIRECRAWL_API_KEY")
            if not api_key:
                raise ValueError("FIRECRAWL_API_KEY未配置")
            
            self.firecrawl_app = FirecrawlApp(api_key=api_key)
            logger.info("✅ 增强版在线搜索引擎初始化成功")
        except Exception as e:
            logger.error(f"❌ FireCrawl初始化失败: {e}")
            self.firecrawl_app = None
    
    def _ensure_components_initialized(self):
        """确保组件已正确初始化"""
        if self.llm is None or self.embedding_model is None:
            # 重新获取全局组件
            from deepsearcher.configuration import llm as global_llm, embedding_model as global_embedding, vector_db as global_vector_db
            
            if global_llm is None:
                logger.warning("⚠️ LLM未初始化，需要先调用 init_config()")
                return False
            if global_embedding is None:
                logger.warning("⚠️ 嵌入模型未初始化，需要先调用 init_config()")
                return False
            
            self.llm = global_llm
            self.embedding_model = global_embedding
            self.vector_db = global_vector_db
            logger.info("✅ LLM组件已动态初始化")
        return True
    
    def search_and_answer(self, user_query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        智能搜索和回答 - 使用LLM进行问题分解和答案生成
        
        Args:
            user_query: 用户查询
            
        Returns:
            (答案, 信息源列表)
        """
        try:
            logger.info(f"🧠 开始增强版在线搜索: {user_query}")
            
            if not self.firecrawl_app:
                return "FireCrawl服务未配置，无法进行在线搜索。请配置FIRECRAWL_API_KEY。", []
            
            # 第一步：使用LLM分解用户问题
            sub_queries = self._decompose_query_with_llm(user_query)
            logger.info(f"🔍 问题分解完成，生成 {len(sub_queries)} 个子查询")
            
            # 第二步：对每个子查询使用FireCrawl搜索
            all_documents = []
            search_results_summary = {}
            
            for i, sub_query in enumerate(sub_queries, 1):
                logger.info(f"🔍 执行子查询 {i}/{len(sub_queries)}: {sub_query}")
                documents = self._search_with_firecrawl(sub_query, user_query)
                
                if documents:
                    all_documents.extend(documents)
                    search_results_summary[sub_query] = len(documents)
                    logger.info(f"✅ 子查询 {i} 获得 {len(documents)} 个文档")
                else:
                    logger.warning(f"⚠️ 子查询 {i} 未找到相关文档")
                
                # 添加延迟避免API频率限制
                if i < len(sub_queries):
                    time.sleep(random.uniform(1, 2))
            
            # 第三步：去重和排序文档
            unique_documents = self._deduplicate_and_rank_documents(all_documents, user_query)
            logger.info(f"📚 文档处理完成，最终获得 {len(unique_documents)} 个高质量文档")
            
            if not unique_documents:
                return "抱歉，没有找到相关的华为技术文档。建议尝试更具体的关键词或查看华为开发者官网。", []
            
            # 第四步：使用LLM基于搜索结果生成综合答案
            answer = self._generate_comprehensive_answer_with_llm(
                user_query, unique_documents, sub_queries, search_results_summary
            )
            
            # 第五步：准备信息源
            sources = self._prepare_sources_info(unique_documents)
            
            logger.info(f"🎉 增强版搜索完成，生成答案长度: {len(answer)} 字符，信息源: {len(sources)} 个")
            return answer, sources
            
        except Exception as e:
            logger.error(f"❌ 增强版在线搜索失败: {e}")
            return f"搜索过程中发生错误: {str(e)}", []
    
    def hybrid_search_and_answer(self, 
                                user_query: str, 
                                use_local: bool = True,
                                use_online: bool = True,
                                collection_name: str = None) -> Dict[str, Any]:
        """
        混合搜索：结合本地数据库和在线搜索
        
        Args:
            user_query: 用户查询
            use_local: 是否使用本地搜索
            use_online: 是否使用在线搜索
            collection_name: 本地搜索的集合名称
            
        Returns:
            包含综合答案和来源信息的字典
        """
        logger.info(f"🔀 开始混合搜索: {user_query}")
        
        local_results = []
        online_answer = ""
        online_sources = []
        
        # 本地搜索
        if use_local:
            try:
                from .adapter import HuaweiDeepSearcherAdapter
                adapter = HuaweiDeepSearcherAdapter()
                local_results = adapter.search_huawei_docs(user_query, top_k=5)
                logger.info(f"📚 本地搜索完成，找到 {len(local_results)} 个结果")
            except Exception as e:
                logger.warning(f"⚠️ 本地搜索失败: {e}")
        
        # 在线搜索
        if use_online:
            try:
                online_answer, online_sources = self.search_and_answer(user_query)
                logger.info(f"🌐 在线搜索完成，生成答案长度: {len(online_answer)} 字符")
            except Exception as e:
                logger.warning(f"⚠️ 在线搜索失败: {e}")
        
        # 生成混合答案
        if local_results or online_answer:
            final_answer = self._generate_hybrid_answer(
                user_query, local_results, online_answer, online_sources
            )
            
            # 准备来源信息
            sources = []
            
            # 添加本地来源
            for result in local_results:
                sources.append({
                    'type': 'local',
                    'title': result.get('title', '本地文档'),
                    'url': result.get('url', ''),
                    'relevance_score': result.get('score', 0)
                })
            
            # 添加在线来源
            for source in online_sources:
                source['type'] = 'online'
                sources.append(source)
            
            return {
                'final_answer': final_answer,
                'sources': sources,
                'local_results_count': len(local_results),
                'online_sources_count': len(online_sources)
            }
        else:
            return {
                'final_answer': "抱歉，没有找到相关信息。建议尝试更具体的关键词。",
                'sources': [],
                'local_results_count': 0,
                'online_sources_count': 0
            }
    
    def _decompose_query_with_llm(self, user_query: str) -> List[str]:
        """
        使用LLM将用户查询分解为多个子查询
        
        Args:
            user_query: 用户原始查询
            
        Returns:
            分解后的子查询列表
        """
        try:
            if not self._ensure_components_initialized():
                logger.warning("⚠️ LLM未初始化，使用默认查询分解策略")
                return self._fallback_query_decomposition(user_query)
            
            # 构建问题分解的提示词
            decomposition_prompt = f"""
作为华为技术文档搜索专家，请将用户的查询分解为多个具体的子查询，以便更全面地搜索相关信息。

用户查询：{user_query}

请遵循以下原则：
1. 分解为3-5个具体的子查询
2. 每个子查询应该聚焦于问题的一个特定方面
3. 优先考虑华为技术栈相关的查询
4. 包含不同层次的查询（概念、实现、示例、最佳实践等）
5. 确保查询适合在华为开发者文档中搜索

请直接输出子查询列表，每行一个，不要添加编号或其他格式：
"""
            
            # 调用LLM进行问题分解
            logger.info("🧠 正在使用LLM分解查询...")
            messages = [{"role": "user", "content": decomposition_prompt}]
            response = self.llm.chat(messages)
            
            # 解析LLM响应
            sub_queries = []
            for line in response.content.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith(('#', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    # 清理可能的编号前缀
                    cleaned_line = line
                    for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '*', '•']:
                        if cleaned_line.startswith(prefix):
                            cleaned_line = cleaned_line[len(prefix):].strip()
                    
                    if cleaned_line:
                        sub_queries.append(cleaned_line)
            
            # 限制子查询数量并添加原始查询
            sub_queries = sub_queries[:self.max_sub_queries-1]
            if user_query not in sub_queries:
                sub_queries.insert(0, user_query)  # 确保原始查询在第一位
            
            logger.info(f"✅ LLM分解查询成功，生成 {len(sub_queries)} 个子查询")
            return sub_queries
            
        except Exception as e:
            logger.warning(f"⚠️ LLM查询分解失败: {e}，使用备用策略")
            return self._fallback_query_decomposition(user_query)
    
    def _fallback_query_decomposition(self, user_query: str) -> List[str]:
        """
        备用查询分解策略（当LLM不可用时）
        
        Args:
            user_query: 用户原始查询
            
        Returns:
            分解后的子查询列表
        """
        # 基于关键词的简单分解策略
        base_queries = [user_query]
        
        # 添加华为相关的扩展查询
        huawei_terms = ["华为", "Huawei", "HMS", "HarmonyOS", "鸿蒙"]
        for term in huawei_terms:
            if term.lower() not in user_query.lower():
                base_queries.append(f"{user_query} {term}")
                break
        
        # 添加技术相关的扩展查询
        if "开发" not in user_query and "API" not in user_query:
            base_queries.append(f"{user_query} 开发指南")
        
        if "示例" not in user_query and "例子" not in user_query:
            base_queries.append(f"{user_query} 示例")
        
        return base_queries[:self.max_sub_queries]
    
    def _search_with_firecrawl(self, query: str, original_query: str) -> List[Document]:
        """
        使用FireCrawl进行搜索
        
        Args:
            query: 搜索查询
            original_query: 原始用户查询
            
        Returns:
            搜索到的文档列表
        """
        try:
            if not self.firecrawl_app:
                logger.warning("⚠️ FireCrawl未初始化")
                return []
            
            # 生成华为优化的搜索查询
            optimized_queries = self._generate_huawei_optimized_queries(query)
            
            documents = []
            for search_query in optimized_queries:
                try:
                    logger.info(f"🔥 FireCrawl搜索: {search_query}")
                    
                    # 使用FireCrawl的搜索功能 - 通过REST API调用
                    import requests
                    import os
                    
                    api_key = os.getenv('FIRECRAWL_API_KEY')
                    if not api_key:
                        logger.error("❌ FireCrawl API密钥未配置")
                        continue
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}'
                    }
                    
                    payload = {
                        'query': search_query,
                        'limit': 5,
                        'scrapeOptions': {
                            'formats': ['markdown', 'html']
                        }
                    }
                    
                    response = requests.post(
                        'https://api.firecrawl.dev/v1/search',
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        search_result = response.json()
                        
                        if search_result.get('success') and search_result.get('data'):
                            for item in search_result['data']:
                                doc = self._process_firecrawl_search_result(item, query, original_query)
                                if doc:
                                    documents.append(doc)
                            
                            logger.info(f"✅ FireCrawl搜索 '{search_query}' 返回 {len(search_result['data'])} 个结果")
                        else:
                            logger.warning(f"⚠️ FireCrawl搜索 '{search_query}' 无结果")
                    else:
                        logger.error(f"❌ FireCrawl搜索失败 '{search_query}': HTTP {response.status_code}")
                    
                    # 添加延迟避免API频率限制
                    time.sleep(random.uniform(0.5, 1.0))
                    
                except Exception as e:
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        logger.warning(f"⚠️ FireCrawl API频率限制，跳过查询: {search_query}")
                        time.sleep(2)
                        continue
                    else:
                        logger.error(f"❌ FireCrawl搜索失败 '{search_query}': {e}")
                        continue
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ FireCrawl搜索整体失败: {e}")
            return []
    
    def _generate_huawei_optimized_queries(self, user_query: str) -> List[str]:
        """
        生成华为优化的搜索查询
        
        Args:
            user_query: 用户查询
            
        Returns:
            优化后的查询列表
        """
        queries = []
        
        # 原始查询
        queries.append(user_query)
        
        # 添加华为域名限制的查询
        huawei_domains = [
            "site:developer.huawei.com",
            "site:developer.harmonyos.com", 
            "site:consumer.huawei.com",
            "site:forums.developer.huawei.com"
        ]
        
        for domain in huawei_domains:
            queries.append(f"{user_query} {domain}")
        
        return queries[:3]  # 限制查询数量避免过度调用API
    
    def _process_firecrawl_search_result(self, item: Dict, query: str, user_query: str) -> Optional[Document]:
        """
        处理FireCrawl搜索结果
        
        Args:
            item: FireCrawl搜索结果项
            query: 搜索查询
            user_query: 原始用户查询
            
        Returns:
            处理后的文档对象
        """
        try:
            url = item.get('url', '')
            title = item.get('title', '')
            # 优先使用markdown内容，如果没有则使用description
            content = item.get('markdown', '') or item.get('content', '') or item.get('description', '')
            description = item.get('description', '')
            
            if not content and not description:
                return None
            
            # 检查是否为华为官方内容
            is_huawei_official = self._is_huawei_official_content(url, title, content)
            
            # 计算相关性分数
            relevance_score = self._calculate_relevance_score(content, title, description, user_query)
            
            # 创建文档对象
            full_content = f"{title}\n\n{content}"
            if description and description not in content:
                full_content += f"\n\n{description}"
            
            metadata = {
                'source': url,
                'title': title,
                'description': description,
                'query': query,
                'user_query': user_query,
                'relevance_score': relevance_score,
                'is_huawei_official': is_huawei_official,
                'timestamp': time.time()
            }
            
            return Document(page_content=full_content, metadata=metadata)
            
        except Exception as e:
            logger.error(f"❌ 处理FireCrawl搜索结果失败: {e}")
            return None
    
    def _is_huawei_official_content(self, url: str, title: str, content: str) -> bool:
        """
        判断是否为华为官方内容
        
        Args:
            url: 页面URL
            title: 页面标题
            content: 页面内容
            
        Returns:
            是否为华为官方内容
        """
        huawei_domains = [
            'developer.huawei.com',
            'developer.harmonyos.com',
            'consumer.huawei.com',
            'forums.developer.huawei.com',
            'huaweicloud.com'
        ]
        
        # 检查URL域名
        for domain in huawei_domains:
            if domain in url.lower():
                return True
        
        # 检查标题和内容中的华为标识
        huawei_indicators = ['华为', 'huawei', 'hms', 'harmonyos', '鸿蒙']
        text_to_check = f"{title} {content}".lower()
        
        return any(indicator in text_to_check for indicator in huawei_indicators)
    
    def _calculate_relevance_score(self, content: str, title: str, description: str, user_query: str) -> float:
        """
        计算内容相关性分数
        
        Args:
            content: 页面内容
            title: 页面标题
            description: 页面描述
            user_query: 用户查询
            
        Returns:
            相关性分数 (0-1)
        """
        score = 0.0
        query_terms = user_query.lower().split()
        
        # 检查标题匹配
        title_lower = title.lower()
        title_matches = sum(1 for term in query_terms if term in title_lower)
        score += (title_matches / len(query_terms)) * 0.4
        
        # 检查内容匹配
        content_lower = content.lower()
        content_matches = sum(1 for term in query_terms if term in content_lower)
        score += (content_matches / len(query_terms)) * 0.4
        
        # 检查描述匹配
        if description:
            desc_lower = description.lower()
            desc_matches = sum(1 for term in query_terms if term in desc_lower)
            score += (desc_matches / len(query_terms)) * 0.2
        
        return min(score, 1.0)
    
    def _deduplicate_and_rank_documents(self, documents: List[Document], user_query: str) -> List[Document]:
        """
        去重和排序文档
        
        Args:
            documents: 文档列表
            user_query: 用户查询
            
        Returns:
            去重排序后的文档列表
        """
        if not documents:
            return []
        
        # 基于URL去重
        seen_urls = set()
        unique_docs = []
        
        for doc in documents:
            url = doc.metadata.get('source', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_docs.append(doc)
        
        # 排序：华为官方内容优先，然后按相关性分数排序
        def sort_key(doc):
            is_official = doc.metadata.get('is_huawei_official', False)
            relevance = doc.metadata.get('relevance_score', 0)
            return (not is_official, -relevance)  # 官方内容优先，相关性高的优先
        
        unique_docs.sort(key=sort_key)
        
        # 限制返回数量
        return unique_docs[:self.max_search_results]
    
    def _generate_comprehensive_answer_with_llm(self, 
                                               user_query: str, 
                                               documents: List[Document], 
                                               sub_queries: List[str],
                                               search_results_summary: Dict[str, int]) -> str:
        """
        使用LLM生成综合答案
        
        Args:
            user_query: 用户查询
            documents: 搜索到的文档
            sub_queries: 子查询列表
            search_results_summary: 搜索结果摘要
            
        Returns:
            生成的综合答案
        """
        try:
            if not self._ensure_components_initialized():
                logger.warning("⚠️ LLM未初始化，使用简单答案生成")
                return self._generate_simple_answer(user_query, documents)
            
            # 准备文档内容
            context_parts = []
            for i, doc in enumerate(documents, 1):
                title = doc.metadata.get('title', f'文档{i}')
                url = doc.metadata.get('source', '')
                content = doc.page_content[:1500]  # 限制长度避免token过多
                
                context_part = f"## 来源{i}: {title}\n"
                if url:
                    context_part += f"链接: {url}\n"
                context_part += f"内容: {content}\n"
                context_parts.append(context_part)
            
            context = "\n".join(context_parts)
            
            # 构建综合答案生成的提示词
            answer_prompt = f"""
作为华为技术专家，请基于以下搜索到的华为官方文档和技术资料，为用户提供准确、全面的答案。

用户问题: {user_query}

搜索策略: 
- 执行了 {len(sub_queries)} 个相关查询
- 共找到 {len(documents)} 个相关文档
- 查询分解: {', '.join(sub_queries)}

相关文档内容:
{context}

请遵循以下要求:
1. 基于提供的华为官方文档内容回答问题
2. 答案要准确、详细、实用
3. 如果涉及代码示例，请提供具体的实现方法
4. 突出华为技术栈的特点和优势
5. 如果有多个相关方面，请分点详细说明
6. 在答案末尾简要说明信息来源的可靠性

请生成一个专业、详细的答案:
"""
            
            # 调用LLM生成答案
            logger.info("🧠 正在使用LLM生成综合答案...")
            messages = [{"role": "user", "content": answer_prompt}]
            response = self.llm.chat(messages)
            
            answer = response.content.strip()
            logger.info(f"✅ LLM答案生成成功，长度: {len(answer)} 字符")
            
            return answer
            
        except Exception as e:
            logger.warning(f"⚠️ LLM答案生成失败: {e}，使用简单答案生成")
            return self._generate_simple_answer(user_query, documents)
    
    def _generate_simple_answer(self, user_query: str, documents: List[Document]) -> str:
        """
        生成简单答案（当LLM不可用时）
        
        Args:
            user_query: 用户查询
            documents: 搜索到的文档
            
        Returns:
            简单的答案
        """
        if not documents:
            return "抱歉，没有找到相关的华为技术文档。"
        
        answer_parts = [f"根据搜索到的 {len(documents)} 个华为技术文档，以下是相关信息：\n"]
        
        for i, doc in enumerate(documents, 1):
            title = doc.metadata.get('title', f'文档{i}')
            url = doc.metadata.get('source', '')
            content = doc.page_content[:300]  # 限制长度
            
            answer_parts.append(f"## {i}. {title}")
            if url:
                answer_parts.append(f"来源: {url}")
            answer_parts.append(f"{content}...\n")
        
        answer_parts.append("\n以上信息来自华为官方文档和技术资料，建议查看原始链接获取完整信息。")
        
        return "\n".join(answer_parts)
    
    def _generate_hybrid_answer(self, 
                              user_query: str, 
                              local_results: List[Dict], 
                              online_answer: str,
                              online_sources: List[Dict]) -> str:
        """
        生成混合搜索的综合答案
        
        Args:
            user_query: 用户查询
            local_results: 本地搜索结果
            online_answer: 在线搜索答案
            online_sources: 在线信息源
            
        Returns:
            综合答案
        """
        try:
            if not self._ensure_components_initialized():
                # 简单拼接答案
                answer_parts = []
                
                if local_results:
                    answer_parts.append("## 本地知识库信息:")
                    for i, result in enumerate(local_results[:3], 1):
                        title = result.get('title', f'文档{i}')
                        content = result.get('content', '')[:200]
                        answer_parts.append(f"{i}. {title}: {content}...")
                
                if online_answer:
                    answer_parts.append("\n## 在线搜索信息:")
                    answer_parts.append(online_answer)
                
                return "\n".join(answer_parts)
            
            # 使用LLM生成综合答案
            local_context = ""
            if local_results:
                local_parts = []
                for result in local_results[:3]:
                    title = result.get('title', '本地文档')
                    content = result.get('content', '')[:500]
                    local_parts.append(f"- {title}: {content}")
                local_context = "\n".join(local_parts)
            
            hybrid_prompt = f"""
作为华为技术专家，请基于本地知识库和在线搜索的信息，为用户提供综合性的答案。

用户问题: {user_query}

本地知识库信息:
{local_context if local_context else "无相关本地信息"}

在线搜索信息:
{online_answer if online_answer else "无在线搜索结果"}

请综合以上信息，生成一个准确、全面的答案：
1. 整合本地和在线信息
2. 去除重复内容
3. 突出最重要的信息
4. 保持逻辑清晰
"""
            
            messages = [{"role": "user", "content": hybrid_prompt}]
            response = self.llm.chat(messages)
            
            return response.content.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ 混合答案生成失败: {e}")
            # 返回简单拼接的答案
            answer_parts = []
            
            if local_results:
                answer_parts.append("## 本地知识库信息:")
                for i, result in enumerate(local_results[:3], 1):
                    title = result.get('title', f'文档{i}')
                    content = result.get('content', '')[:200]
                    answer_parts.append(f"{i}. {title}: {content}...")
            
            if online_answer:
                answer_parts.append("\n## 在线搜索信息:")
                answer_parts.append(online_answer)
            
            return "\n".join(answer_parts) if answer_parts else "未找到相关信息。"
    
    def _prepare_sources_info(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        准备信息源信息
        
        Args:
            documents: 文档列表
            
        Returns:
            信息源列表
        """
        sources = []
        for doc in documents:
            source_info = {
                'title': doc.metadata.get('title', '未知标题'),
                'url': doc.metadata.get('source', ''),
                'description': doc.metadata.get('description', ''),
                'relevance_score': doc.metadata.get('relevance_score', 0),
                'is_huawei_official': doc.metadata.get('is_huawei_official', False)
            }
            sources.append(source_info)
        
        return sources 