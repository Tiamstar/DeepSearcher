#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为RAG流水线 - 整合爬虫和向量化功能
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

from deepsearcher.configuration import Configuration, init_config

from .config import CrawlerConfig, RAGConfig
from .crawler import HuaweiContentCrawler
from .adapter import HuaweiDeepSearcherAdapter

logger = logging.getLogger(__name__)

class HuaweiRAGPipeline:
    """华为RAG流水线 - 完整的内容处理流程"""
    
    def __init__(self, config_file: str = None):
        """
        初始化RAG流水线
        
        Args:
            config_file: 配置文件路径，暂未使用，为将来扩展预留
        """
        self.crawler_config = CrawlerConfig()
        self.rag_config = RAGConfig()
        
        self.crawler = None
        self.adapter = None
        
        # 确保目录存在
        self.crawler_config.ensure_directories()
        
        logger.info("🚀 华为RAG流水线初始化完成")
    
    def setup_deepsearcher(self, 
                          llm_model: str = None,
                          embedding_model: str = None,
                          vector_db_config: Dict = None):
        """
        设置DeepSearcher配置
        
        Args:
            llm_model: LLM模型名称
            embedding_model: 嵌入模型名称  
            vector_db_config: 向量数据库配置
        """
        logger.info("⚙️ 设置DeepSearcher配置...")
        
        # 使用默认配置或传入的配置
        llm_model = llm_model or self.rag_config.DEFAULT_LLM_MODEL
        embedding_model = embedding_model or self.rag_config.DEFAULT_EMBEDDING_MODEL
        vector_db_config = vector_db_config or self.rag_config.DEFAULT_VECTOR_DB_CONFIG
        
        # 创建配置
        config = Configuration()
        config.set_provider_config("llm", self.rag_config.DEFAULT_LLM_PROVIDER, {"model": llm_model})
        config.set_provider_config("embedding", self.rag_config.DEFAULT_EMBEDDING_PROVIDER, {"model": embedding_model})
        config.set_provider_config("vector_db", self.rag_config.DEFAULT_VECTOR_DB_PROVIDER, vector_db_config)
        
        # 应用配置
        init_config(config)
        
        logger.info(f"✅ DeepSearcher配置完成")
        logger.info(f"   LLM: {self.rag_config.DEFAULT_LLM_PROVIDER}/{llm_model}")
        logger.info(f"   嵌入模型: {self.rag_config.DEFAULT_EMBEDDING_PROVIDER}/{embedding_model}")
        logger.info(f"   向量数据库: {self.rag_config.DEFAULT_VECTOR_DB_PROVIDER}")
    
    def initialize_crawler(self, links_file: str = None) -> HuaweiContentCrawler:
        """初始化爬虫"""
        if self.crawler is None:
            logger.info("🕷️ 初始化华为内容爬虫...")
            links_file = links_file or self.crawler_config.LINKS_FILE
            self.crawler = HuaweiContentCrawler(links_file, self.crawler_config)
            logger.info("✅ 爬虫初始化完成")
        return self.crawler
    
    def initialize_adapter(self, 
                          collection_name: str = None, 
                          content_type: str = "auto") -> HuaweiDeepSearcherAdapter:
        """
        初始化适配器
        
        Args:
            collection_name: 集合名称
            content_type: 内容类型选择 ("auto", "expanded", "basic", "all")
        """
        if self.adapter is None:
            logger.info("🔄 初始化DeepSearcher适配器...")
            
            # 确保DeepSearcher已配置
            try:
                from deepsearcher.configuration import vector_db, embedding_model
                if vector_db is None or embedding_model is None:
                    logger.info("⚙️ DeepSearcher未配置，正在自动配置...")
                    self.setup_deepsearcher()
            except Exception as e:
                logger.warning(f"⚠️ 检查DeepSearcher配置时出错: {e}")
                logger.info("⚙️ 重新配置DeepSearcher...")
                self.setup_deepsearcher()
            
            collection_name = collection_name or self.rag_config.DEFAULT_COLLECTION_NAME
            
            self.adapter = HuaweiDeepSearcherAdapter(
                collection_name=collection_name,
                chunk_size=self.rag_config.DEFAULT_CHUNK_SIZE,
                chunk_overlap=self.rag_config.DEFAULT_CHUNK_OVERLAP,
                content_type=content_type
            )
            logger.info("✅ 适配器初始化完成")
        return self.adapter
    
    async def crawl_content(self, 
                           links_file: str = None, 
                           force_recrawl: bool = False) -> bool:
        """
        爬取华为文档内容
        
        Args:
            links_file: 链接文件路径
            force_recrawl: 是否强制重新爬取
        """
        try:
            logger.info("🕷️ 开始爬取华为文档内容...")
            
            # 检查是否已有内容且不强制重新爬取
            content_file = self.crawler_config.PROCESSED_DATA_DIR / self.crawler_config.OUTPUT_FILE
            if content_file.exists() and not force_recrawl:
                logger.info(f"📂 发现已存在的内容文件: {content_file}")
                logger.info("💡 如需重新爬取，请设置 force_recrawl=True")
                return True
            
            # 初始化爬虫
            crawler = self.initialize_crawler(links_file)
            
            # 加载链接
            urls = crawler.load_links()
            if not urls:
                logger.error("❌ 没有找到可爬取的链接")
                return False
            
            # 开始爬取
            logger.info(f"📋 开始爬取 {len(urls)} 个页面...")
            crawled_content = await crawler.crawl_content(urls)
            
            if not crawled_content:
                logger.error("❌ 爬取失败，没有获得任何内容")
                return False
            
            # 生成统计信息
            stats = crawler.generate_statistics()
            logger.info("📊 爬取完成统计:")
            logger.info(f"   ✅ 成功: {stats['total_pages']} 页")
            logger.info(f"   ❌ 失败: {stats['failed_pages']} 页")
            logger.info(f"   ⏩ 跳过: {stats['skipped_pages']} 页")
            logger.info(f"   📝 总文本长度: {stats['total_text_length']:,} 字符")
            logger.info(f"   💻 总代码块: {stats['total_code_blocks']} 个")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 爬取内容失败: {e}")
            return False
    
    def load_to_vector_database(self, 
                               collection_name: str = None,
                               force_new_collection: bool = False,
                               incremental_update: bool = True,
                               batch_size: int = 64,
                               content_type: str = "auto") -> bool:
        """
        加载内容到向量数据库
        
        Args:
            collection_name: 集合名称
            force_new_collection: 是否强制创建新集合
            incremental_update: 是否启用增量更新，仅处理新文档
            batch_size: 批处理大小
            content_type: 内容类型选择 ("auto", "expanded", "basic", "all")
        """
        try:
            logger.info("💾 开始加载内容到向量数据库...")
            
            # 初始化适配器
            adapter = self.initialize_adapter(collection_name, content_type)
            
            # 检查内容文件是否存在
            content_file = Path(adapter.content_file)
            if not content_file.exists() and adapter.content_type != "all":
                logger.error(f"❌ 内容文件不存在: {content_file}")
                logger.info("💡 请先运行爬虫生成内容文件")
                return False
            
            # 如果强制重建集合，则禁用增量更新
            if force_new_collection:
                incremental_update = False
                logger.info("🔄 强制重建集合，禁用增量更新")
            
            # 加载到向量数据库
            success = adapter.load_to_vector_database(
                force_new_collection=force_new_collection,
                incremental_update=incremental_update,
                batch_size=batch_size
            )
            
            if success:
                # 显示集合信息
                collection_info = adapter.get_collection_info()
                if collection_info.get('exists'):
                    logger.info(f"📚 集合信息: {collection_info['name']} ({collection_info.get('count', 0)} 个文档)")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 加载到向量数据库失败: {e}")
            return False
    
    def search(self, 
              query: str, 
              top_k: int = 5,
              content_type: str = None,
              collection_name: str = None) -> List[Dict]:
        """
        搜索华为文档
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            content_type: 内容类型过滤 ('text', 'code')
            collection_name: 集合名称
        """
        try:
            # 初始化适配器
            adapter = self.initialize_adapter(collection_name)
            
            # 执行搜索
            results = adapter.search_huawei_docs(
                query=query,
                top_k=top_k,
                content_type=content_type
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            return []
    
    def search_with_rag(self, 
                       query: str, 
                       top_k: int = 5,
                       content_type: str = None,
                       collection_name: str = None,
                       use_chain_of_rag: bool = False) -> List[Dict]:
        """
        使用DeepSearcher的高级RAG功能搜索华为文档
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            content_type: 内容类型过滤 ('text', 'code')
            collection_name: 集合名称
            use_chain_of_rag: 是否使用ChainOfRAG进行多步推理搜索
        """
        try:
            # 初始化适配器
            adapter = self.initialize_adapter(collection_name)
            
            # 使用DeepSearcher的高级RAG功能
            from deepsearcher.configuration import llm, embedding_model, vector_db
            from deepsearcher.agent.naive_rag import NaiveRAG
            from deepsearcher.agent.chain_of_rag import ChainOfRAG
            from deepsearcher.agent.deep_search import DeepSearch
            
            if use_chain_of_rag:
                # 使用ChainOfRAG进行多步推理搜索
                rag_agent = ChainOfRAG(
                    llm=llm,
                    embedding_model=embedding_model,
                    vector_db=vector_db,
                    max_iter=3,
                    early_stopping=True
                )
                logger.info("🔗 使用ChainOfRAG进行多步推理搜索")
            else:
                # 使用DeepSearch进行深度搜索
                rag_agent = DeepSearch(
                    llm=llm,
                    embedding_model=embedding_model,
                    vector_db=vector_db,
                    top_k=top_k
                )
                logger.info("🔍 使用DeepSearch进行深度搜索")
            
            # 执行RAG查询
            answer, retrieved_results, token_usage = rag_agent.query(query, top_k=top_k)
            
            # 转换结果格式
            formatted_results = []
            for result in retrieved_results:
                formatted_result = {
                    'title': result.metadata.get('title', '未知标题'),
                    'url': result.metadata.get('url', '无链接'),
                    'content': result.text,
                    'content_type': result.metadata.get('content_type', 'text'),
                    'score': result.score,
                    'reference': result.reference,
                    'rag_answer': answer  # 添加RAG生成的答案
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"✅ RAG搜索完成，使用了 {token_usage} tokens")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ RAG搜索失败: {e}")
            # 降级到普通搜索
            logger.info("🔄 降级到普通向量搜索")
            return self.search(query, top_k, content_type, collection_name)
    
    async def run_full_pipeline(self, 
                         links_file: str = None,
                         collection_name: str = None,
                         force_recrawl: bool = False,
                         force_new_collection: bool = False,
                         batch_size: int = 64) -> bool:
        """
        运行完整的RAG流水线
        
        Args:
            links_file: 链接文件路径
            collection_name: 集合名称
            force_recrawl: 是否强制重新爬取
            force_new_collection: 是否强制创建新集合
            batch_size: 批处理大小
        """
        try:
            logger.info("🚀 开始运行完整的华为RAG流水线...")
            
            # 1. 设置DeepSearcher
            self.setup_deepsearcher()
            
            # 2. 爬取内容
            logger.info("\n" + "="*50)
            logger.info("📋 第1步: 爬取华为文档内容")
            logger.info("="*50)
            
            crawl_success = await self.crawl_content(
                links_file=links_file,
                force_recrawl=force_recrawl
            )
            
            if not crawl_success:
                logger.error("❌ 爬取阶段失败，停止流水线")
                return False
            
            # 3. 加载到向量数据库
            logger.info("\n" + "="*50)
            logger.info("📋 第2步: 加载到向量数据库")
            logger.info("="*50)
            
            load_success = self.load_to_vector_database(
                collection_name=collection_name,
                force_new_collection=force_new_collection,
                batch_size=batch_size
            )
            
            if not load_success:
                logger.error("❌ 向量化阶段失败，停止流水线")
                return False
            
            logger.info("\n" + "="*50)
            logger.info("🎉 华为RAG流水线完成!")
            logger.info("="*50)
            logger.info("✅ 所有步骤成功完成")
            logger.info("💡 现在可以使用 search() 方法进行文档搜索")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 流水线执行失败: {e}")
            return False

    def run_full_pipeline_sync(self, 
                              links_file: str = None,
                              collection_name: str = None,
                              force_recrawl: bool = False,
                              force_new_collection: bool = False,
                              batch_size: int = 64) -> bool:
        """
        运行完整的RAG流水线 (同步版本)
        
        Args:
            links_file: 链接文件路径
            collection_name: 集合名称  
            force_recrawl: 是否强制重新爬取
            force_new_collection: 是否强制创建新集合
            batch_size: 批处理大小
        """
        return run_pipeline_async(
            self.run_full_pipeline,
            links_file=links_file,
            collection_name=collection_name,
            force_recrawl=force_recrawl,
            force_new_collection=force_new_collection,
            batch_size=batch_size
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取流水线状态"""
        status = {
            'crawler_initialized': self.crawler is not None,
            'adapter_initialized': self.adapter is not None,
            'content_file_exists': False,
            'collection_exists': False,
            'collection_info': {}
        }
        
        # 检查内容文件
        content_file = self.crawler_config.PROCESSED_DATA_DIR / self.crawler_config.OUTPUT_FILE
        status['content_file_exists'] = content_file.exists()
        if content_file.exists():
            status['content_file_path'] = str(content_file)
        
        # 检查集合信息
        if self.adapter:
            try:
                collection_info = self.adapter.get_collection_info()
                status['collection_exists'] = collection_info.get('exists', False)
                status['collection_info'] = collection_info
            except:
                pass
        
        return status
    
    def print_status(self):
        """打印流水线状态"""
        status = self.get_status()
        
        logger.info("📊 华为RAG流水线状态:")
        logger.info(f"   🕷️ 爬虫: {'✅' if status['crawler_initialized'] else '❌'}")
        logger.info(f"   🔄 适配器: {'✅' if status['adapter_initialized'] else '❌'}")
        logger.info(f"   📄 内容文件: {'✅' if status['content_file_exists'] else '❌'}")
        logger.info(f"   📚 向量集合: {'✅' if status['collection_exists'] else '❌'}")
        
        if status['collection_exists']:
            info = status['collection_info']
            logger.info(f"       集合名称: {info.get('name', 'Unknown')}")
            logger.info(f"       文档数量: {info.get('count', 0):,}")
        
        if status['content_file_exists']:
            logger.info(f"       内容文件: {status.get('content_file_path', 'Unknown')}")

    def list_content_files(self) -> Dict[str, Any]:
        """列出所有可用的内容文件"""
        try:
            # 创建一个临时适配器来获取文件列表
            temp_adapter = HuaweiDeepSearcherAdapter()
            return temp_adapter.list_available_content_files()
        except Exception as e:
            logger.error(f"❌ 列出内容文件失败: {e}")
            return {}


# 异步运行助手函数
def run_pipeline_async(pipeline_func, *args, **kwargs):
    """运行异步流水线的助手函数"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(pipeline_func(*args, **kwargs)) 