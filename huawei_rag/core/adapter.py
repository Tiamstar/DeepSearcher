#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为文档DeepSearcher适配器 - 重构版
将华为文档爬虫结果适配到DeepSearcher框架
"""

import json
import os
import hashlib
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document
from deepsearcher.configuration import vector_db, embedding_model
from deepsearcher.loader.splitter import Chunk, split_docs_to_chunks

from .config import RAGConfig

logger = logging.getLogger(__name__)

@dataclass
class HuaweiDocument:
    """华为文档数据结构"""
    url: str
    title: str
    content: str
    content_type: str  # 'text', 'code'
    language: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class HuaweiDeepSearcherAdapter:
    """华为文档DeepSearcher适配器 - 重构版"""
    
    def __init__(self, 
                 content_file: str = None,
                 collection_name: str = None,
                 chunk_size: int = None,
                 chunk_overlap: int = None,
                 content_type: str = "auto"):  # 新增：内容类型选择
        """
        初始化华为文档适配器
        
        Args:
            content_file: 指定的内容文件路径
            collection_name: 集合名称
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            content_type: 内容类型选择 ("auto", "expanded", "basic", "all")
                - "auto": 自动选择最新的扩展内容文件
                - "expanded": 优先选择扩展内容文件
                - "basic": 选择基础内容文件 (huawei_docs_content.json)
                - "all": 合并所有内容文件
        """
        
        # 使用配置默认值
        self.content_type = content_type
        self.content_file = Path(content_file) if content_file else self._find_content_file(content_type)
        self.collection_name = (collection_name or RAGConfig.DEFAULT_COLLECTION_NAME).replace(" ", "_").replace("-", "_")
        self.chunk_size = chunk_size or RAGConfig.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or RAGConfig.DEFAULT_CHUNK_OVERLAP
        
        # 延迟初始化全局组件
        self._vector_db = None
        self._embedding_model = None
        
        logger.info(f"✅ 华为文档适配器初始化完成")
        logger.info(f"   集合名称: {self.collection_name}")
        logger.info(f"   内容类型: {self.content_type}")
        logger.info(f"   内容文件: {self.content_file}")
    
    @property
    def vector_db(self):
        """延迟获取向量数据库"""
        if self._vector_db is None:
            from deepsearcher.configuration import vector_db
            if vector_db is None:
                raise RuntimeError("向量数据库未初始化，请先调用 init_config()")
            self._vector_db = vector_db
            logger.info(f"   向量数据库: {type(self._vector_db).__name__}")
        return self._vector_db
    
    @property
    def embedding_model(self):
        """延迟获取嵌入模型"""
        if self._embedding_model is None:
            from deepsearcher.configuration import embedding_model
            if embedding_model is None:
                raise RuntimeError("嵌入模型未初始化，请先调用 init_config()")
            self._embedding_model = embedding_model
            logger.info(f"   嵌入模型: {type(self._embedding_model).__name__}")
        return self._embedding_model
    
    def _find_content_file(self, content_type: str = "auto") -> Path:
        """根据内容类型查找华为文档内容文件"""
        data_dir = Path("data/processed")
        
        if content_type == "basic":
            # 选择基础内容文件
            basic_file = data_dir / "huawei_docs_content.json"
            if basic_file.exists():
                logger.info(f"🔍 选择基础内容文件: {basic_file}")
                return basic_file
            else:
                logger.warning(f"⚠️ 基础内容文件不存在: {basic_file}")
        
        elif content_type == "expanded":
            # 优先选择扩展内容文件
            expanded_files = [f for f in data_dir.glob("huawei_docs_expanded_content_*.json") 
                             if not f.name.endswith('_stats.json') and not f.name.endswith('_failed.json')]
            if expanded_files:
                latest_file = max(expanded_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"🔍 选择扩展内容文件: {latest_file}")
                return latest_file
            else:
                logger.warning(f"⚠️ 未找到扩展内容文件")
        
        elif content_type == "all":
            # 这种情况下，我们返回一个标记，后续在load_huawei_content中处理
            logger.info(f"🔍 将合并所有可用的内容文件")
            return data_dir / "ALL_CONTENT_FILES"
        
        # content_type == "auto" 或其他情况的默认逻辑
        # 查找扩展内容文件（排除统计文件和失败文件）
        expanded_files = [f for f in data_dir.glob("huawei_docs_expanded_content_*.json") 
                         if not f.name.endswith('_stats.json') and not f.name.endswith('_failed.json')]
        if expanded_files:
            latest_file = max(expanded_files, key=lambda x: x.stat().st_mtime)
            logger.info(f"🔍 自动选择最新扩展内容文件: {latest_file}")
            return latest_file
        
        # 查找普通内容文件（排除统计文件和失败文件）
        content_files = [f for f in data_dir.glob("huawei_docs_content*.json") 
                        if not f.name.endswith('_stats.json') and not f.name.endswith('_failed.json')]
        if content_files:
            latest_file = max(content_files, key=lambda x: x.stat().st_mtime)
            logger.info(f"🔍 找到基础内容文件: {latest_file}")
            return latest_file
        
        # 默认路径
        default_path = data_dir / "huawei_docs_content.json"
        logger.warning(f"⚠️ 未找到华为文档内容文件，使用默认路径: {default_path}")
        return default_path
    
    def list_available_content_files(self) -> Dict[str, Any]:
        """列出所有可用的内容文件"""
        data_dir = Path("data/processed")
        
        files_info = {
            'expanded_files': [],
            'basic_files': [],
            'other_files': []
        }
        
        # 查找扩展内容文件
        expanded_files = [f for f in data_dir.glob("huawei_docs_expanded_content_*.json") 
                         if not f.name.endswith('_stats.json') and not f.name.endswith('_failed.json')]
        for file in expanded_files:
            files_info['expanded_files'].append({
                'name': file.name,
                'path': str(file),
                'size_mb': round(file.stat().st_size / 1024 / 1024, 2),
                'modified': file.stat().st_mtime
            })
        
        # 查找基础内容文件
        basic_files = [f for f in data_dir.glob("huawei_docs_content*.json") 
                      if not f.name.startswith('huawei_docs_expanded_content') 
                      and not f.name.endswith('_stats.json') 
                      and not f.name.endswith('_failed.json')]
        for file in basic_files:
            files_info['basic_files'].append({
                'name': file.name,
                'path': str(file),
                'size_mb': round(file.stat().st_size / 1024 / 1024, 2),
                'modified': file.stat().st_mtime
            })
        
        # 查找其他相关文件
        other_files = [f for f in data_dir.glob("huawei_docs_*.json") 
                      if not any(f.name.startswith(prefix) for prefix in 
                               ['huawei_docs_content', 'huawei_docs_expanded_content'])
                      and not f.name.endswith('_stats.json') 
                      and not f.name.endswith('_failed.json')]
        for file in other_files:
            files_info['other_files'].append({
                'name': file.name,
                'path': str(file),
                'size_mb': round(file.stat().st_size / 1024 / 1024, 2),
                'modified': file.stat().st_mtime
            })
        
        return files_info
    
    def load_huawei_content(self) -> Dict[str, Any]:
        """加载华为文档内容 - 支持多文件合并，增强编码处理"""
        try:
            content_path = Path(self.content_file)
            
            # 特殊处理：合并所有内容文件
            if content_path.name == "ALL_CONTENT_FILES":
                return self._load_merged_content()
            
            # 常规单文件加载
            if not content_path.exists():
                raise FileNotFoundError(f"华为文档内容文件不存在: {content_path}")
            
            # 增强的文件读取，支持多种编码
            content = None
            encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(content_path, 'r', encoding=encoding) as f:
                        content = json.load(f)
                    logger.info(f"✅ 使用 {encoding} 编码成功读取文件")
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    if encoding == encodings[-1]:  # 最后一个编码也失败
                        raise e
                    continue
            
            if content is None:
                raise Exception("无法使用任何支持的编码读取文件")
            
            logger.info(f"📚 成功加载 {len(content)} 个页面的华为文档内容")
            logger.info(f"   文件: {content_path.name}")
            logger.info(f"   大小: {content_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            return content
            
        except Exception as e:
            logger.error(f"❌ 加载华为文档内容失败: {e}")
            return {}
    
    def _load_merged_content(self) -> Dict[str, Any]:
        """合并加载所有可用的内容文件，增强编码处理"""
        logger.info("🔄 开始合并加载所有内容文件...")
        
        data_dir = Path("data/processed")
        merged_content = {}
        loaded_files = []
        
        def safe_load_json(file_path: Path) -> Dict[str, Any]:
            """安全加载JSON文件，支持多种编码"""
            encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return json.load(f)
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    if encoding == encodings[-1]:
                        raise e
                    continue
            
            raise Exception(f"无法使用任何支持的编码读取文件: {file_path}")
        
        # 1. 加载基础内容文件
        basic_file = data_dir / "huawei_docs_content.json"
        if basic_file.exists():
            try:
                basic_content = safe_load_json(basic_file)
                merged_content.update(basic_content)
                loaded_files.append(f"基础内容: {basic_file.name} ({len(basic_content)} 页)")
                logger.info(f"   ✅ 加载基础内容: {len(basic_content)} 页")
            except Exception as e:
                logger.warning(f"   ⚠️ 加载基础内容失败: {e}")
        
        # 2. 加载扩展内容文件（只加载不重复的内容）
        expanded_files = [f for f in data_dir.glob("huawei_docs_expanded_content_*.json") 
                         if not f.name.endswith('_stats.json') and not f.name.endswith('_failed.json')]
        
        for expanded_file in expanded_files:
            try:
                expanded_content = safe_load_json(expanded_file)
                
                # 只添加新的URL，避免重复
                new_urls = 0
                for url, content in expanded_content.items():
                    if url not in merged_content:
                        merged_content[url] = content
                        new_urls += 1
                
                loaded_files.append(f"扩展内容: {expanded_file.name} (+{new_urls} 新页)")
                logger.info(f"   ✅ 加载扩展内容: +{new_urls} 新页面")
                
            except Exception as e:
                logger.warning(f"   ⚠️ 加载扩展内容失败 {expanded_file.name}: {e}")
        
        logger.info(f"📊 合并完成:")
        logger.info(f"   总页面数: {len(merged_content)}")
        logger.info(f"   加载的文件:")
        for file_info in loaded_files:
            logger.info(f"     - {file_info}")
        
        return merged_content
    
    def create_document_id(self, url: str, chunk_index: int, content_type: str) -> str:
        """创建文档ID"""
        content_hash = hashlib.md5(f"{url}_{chunk_index}_{content_type}".encode()).hexdigest()[:8]
        return f"huawei_{content_type}_{content_hash}_{chunk_index}"
    
    def split_text_smartly(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """智能文本分块 - 优化的中文分割"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # 寻找句子结尾
            sentence_endings = ['。', '！', '？', '\n\n', '；', '. ', '! ', '? ', '\n\n']
            best_split = end
            
            for i in range(end - overlap, end):
                if i > start:
                    for ending in sentence_endings:
                        if text[i:i+len(ending)] == ending:
                            best_split = i + len(ending)
                            break
                    if best_split != end:
                        break
            
            chunks.append(text[start:best_split])
            start = best_split - overlap if best_split > start + overlap else best_split
        
        return chunks
    
    def process_page_content(self, url: str, page_data: Dict[str, Any]) -> List[HuaweiDocument]:
        """处理单个页面内容，生成多个文档对象，增强编码处理"""
        documents = []
        title = self._safe_decode_text(page_data.get('title', 'Unknown'))
        page_type = page_data.get('page_type', 'unknown')
        
        # 1. 处理主要文本内容
        text_content = self._safe_decode_text(page_data.get('text_content', '')).strip()
        if text_content and len(text_content) > 50:
            if len(text_content) > self.chunk_size:
                text_chunks = self.split_text_smartly(text_content, self.chunk_size, self.chunk_overlap)
                for i, chunk in enumerate(text_chunks):
                    documents.append(HuaweiDocument(
                        url=url,
                        title=f"{title} (第{i+1}部分)",
                        content=chunk,
                        content_type='text',
                        metadata={
                            'chunk_index': i,
                            'total_chunks': len(text_chunks),
                            'page_type': page_type,
                            'original_title': title,
                            'original_url': url
                        }
                    ))
            else:
                documents.append(HuaweiDocument(
                    url=url,
                    title=title,
                    content=text_content,
                    content_type='text',
                    metadata={
                        'page_type': page_type,
                        'original_title': title,
                        'original_url': url
                    }
                ))
        
        # 2. 处理代码块
        code_blocks = page_data.get('code_blocks', [])
        for i, code_block in enumerate(code_blocks):
            code_content = self._safe_decode_text(code_block.get('code', '')).strip()
            if not code_content or len(code_content) < 20:
                continue
                
            language = code_block.get('language', 'unknown')
            
            # 构建代码内容
            enhanced_content = f"代码语言: {language}\n代码内容:\n{code_content}"
            
            documents.append(HuaweiDocument(
                url=url,
                title=f"{title} - 代码示例 {i+1}",
                content=enhanced_content,
                content_type='code',
                language=language,
                metadata={
                    'code_index': i,
                    'code_language': language,
                    'raw_code': code_content,
                    'page_type': page_type,
                    'original_title': title,
                    'original_url': url
                }
            ))
        
        return documents
    
    def convert_to_langchain_documents(self, huawei_docs: List[HuaweiDocument]) -> List[Document]:
        """将HuaweiDocument转换为LangChain Document格式"""
        langchain_docs = []
        
        for doc in huawei_docs:
            metadata = {
                **doc.metadata,
                'content_type': doc.content_type,
                'language': doc.language,
                'document_id': self.create_document_id(doc.url, 
                                                     doc.metadata.get('chunk_index', 0), 
                                                     doc.content_type),
                'title': doc.title,
                'url': doc.url,
                'reference': f"{doc.title} ({doc.url})"
            }
            
            langchain_doc = Document(
                page_content=doc.content,
                metadata=metadata
            )
            
            langchain_docs.append(langchain_doc)
        
        return langchain_docs
    
    def load_huawei_documents(self) -> List[HuaweiDocument]:
        """加载华为文档内容并转换为HuaweiDocument对象列表"""
        try:
            # 1. 加载原始内容
            raw_content = self.load_huawei_content()
            if not raw_content:
                logger.error("❌ 没有加载到任何内容")
                return []
            
            logger.info(f"📚 开始处理 {len(raw_content)} 个页面")
            
            # 2. 处理每个页面，转换为HuaweiDocument对象
            all_documents = []
            processed_count = 0
            
            for url, page_data in raw_content.items():
                try:
                    # 处理单个页面内容
                    page_documents = self.process_page_content(url, page_data)
                    all_documents.extend(page_documents)
                    processed_count += 1
                    
                    # 定期显示进度
                    if processed_count % 100 == 0:
                        logger.info(f"   📄 已处理 {processed_count}/{len(raw_content)} 个页面")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 处理页面失败 {url}: {e}")
                    continue
            
            logger.info(f"✅ 文档处理完成:")
            logger.info(f"   📄 处理页面数: {processed_count}")
            logger.info(f"   📝 生成文档数: {len(all_documents)}")
            
            # 3. 统计信息
            text_docs = sum(1 for doc in all_documents if doc.content_type == 'text')
            code_docs = sum(1 for doc in all_documents if doc.content_type == 'code')
            
            logger.info(f"   📃 文本文档: {text_docs}")
            logger.info(f"   💻 代码文档: {code_docs}")
            
            return all_documents
            
        except Exception as e:
            logger.error(f"❌ 加载华为文档失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []
    
    def load_to_vector_database(self, 
                               force_new_collection: bool = False,
                               incremental_update: bool = True,  # 新增：增量更新参数
                               batch_size: int = 64) -> bool:
        """加载华为文档到向量数据库 - 使用统一的加载函数"""
        try:
            logger.info("💾 开始加载内容到向量数据库...")
            
            # 1. 加载文档并转换为LangChain格式
            huawei_docs = self.load_huawei_documents()
            if not huawei_docs:
                logger.error("❌ 没有找到可加载的文档")
                return False
            
            logger.info(f"📚 加载了 {len(huawei_docs)} 个文档")
            
            # 2. 转换为LangChain文档格式
            langchain_docs = self.convert_to_langchain_documents(huawei_docs)
            
            # 3. 保存为临时文件以供offline_loading使用
            import tempfile
            import json
            from pathlib import Path
            
            # 创建临时文件来存储文档
            temp_dir = Path(tempfile.mkdtemp())
            temp_file = temp_dir / "temp_huawei_docs.json"
            
            # 转换为可序列化格式
            serializable_docs = []
            for doc in langchain_docs:
                serializable_docs.append({
                    'page_content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            # 保存到临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_docs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 创建临时文件: {temp_file}")
            
            try:
                # 4. 使用统一的offline_loading函数
                from deepsearcher.offline_loading import load_from_local_files
                
                # 创建自定义文件加载器，从JSON文件加载我们的文档
                from deepsearcher.configuration import file_loader
                
                # 临时替换file_loader的load_file方法
                original_load_file = file_loader.load_file
                
                def custom_load_file(file_path: str):
                    """自定义文件加载器，从JSON加载转换后的文档"""
                    if str(file_path) == str(temp_file):
                        from langchain_core.documents import Document
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        documents = []
                        for item in data:
                            doc = Document(
                                page_content=item['page_content'],
                                metadata=item['metadata']
                            )
                            documents.append(doc)
                        
                        return documents
                    else:
                        return original_load_file(file_path)
                
                # 临时替换加载器
                file_loader.load_file = custom_load_file
                
                # 调用统一的加载函数
                load_from_local_files(
                    paths_or_directory=str(temp_file),
                    collection_name=self.collection_name,
                    collection_description=f"华为文档集合 - {self.content_type}",
                    force_new_collection=force_new_collection,
                    incremental_update=incremental_update,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    batch_size=batch_size
                )
                
                # 恢复原始加载器
                file_loader.load_file = original_load_file
                
                logger.info("🎉 向量数据库加载完成!")
                return True
                
            finally:
                # 清理临时文件
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                    if temp_dir.exists():
                        temp_dir.rmdir()
                    logger.info("🧹 清理临时文件完成")
                except Exception as e:
                    logger.warning(f"⚠️ 清理临时文件失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ 加载到向量数据库失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def search_huawei_docs(self, 
                          query: str, 
                          top_k: int = 5,
                          content_type: str = None) -> List[Dict]:
        """搜索华为文档，增强编码处理"""
        try:
            logger.info(f"🔍 搜索华为文档: {query}")
            
            # 生成查询向量
            query_vector = self.embedding_model.embed_query(query)
            
            # 使用向量数据库的正确搜索方法
            results = self.vector_db.search_data(
                collection=self.collection_name,
                vector=query_vector,
                top_k=top_k * 2,  # 多获取一些结果用于过滤
                query_text=query  # 传递原始查询文本，支持混合搜索
            )
            
            if not results:
                logger.info("📭 没有找到相关结果")
                return []
            
            # 格式化结果
            formatted_results = []
            for result in results:
                # 过滤内容类型
                if content_type and result.metadata.get('content_type') != content_type:
                    continue
                
                # 增强的文本内容处理
                text_content = self._safe_decode_text(result.text)
                
                # 安全获取元数据
                metadata = getattr(result, 'metadata', {}) or {}
                title = self._safe_decode_text(metadata.get('title', 'Unknown'))
                url = metadata.get('url', '')
                
                formatted_result = {
                    'title': title,
                    'content': text_content,
                    'url': url,
                    'content_type': metadata.get('content_type', 'unknown'),
                    'language': metadata.get('language', 'unknown'),
                    'score': getattr(result, 'score', 0.0),
                    'metadata': metadata
                }
                formatted_results.append(formatted_result)
            
            # 按相关性排序并限制数量
            formatted_results.sort(key=lambda x: x['score'])
            # final_results = formatted_results[0]
            # prompt=f"""
            # 请检查以下内容的正确性，生成一个简洁的总结，字数不超过100字。
            # 内容:
            # {final_results}
            # 总结:
            # """
            # 调用deepseek api
            # response = deepseek_api.chat.completions.create(
            #     model="deepseek-chat",
            #     messages=[{"role": "user", "content": prompt}]
            # )
            # 返回总结
            # 总结+最初输入送到deepseek api
            return formatted_results[:top_k]
            
        except Exception as e:
            logger.error(f"搜索华为文档失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []
    
    def _safe_decode_text(self, text_content: Any) -> str:
        """安全解码文本内容，处理各种编码问题"""
        if text_content is None:
            return ""
        
        # 如果已经是字符串，直接返回
        if isinstance(text_content, str):
            return text_content
        
        # 如果是字节类型，尝试解码
        if isinstance(text_content, bytes):
            encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1']
            
            for encoding in encodings:
                try:
                    return text_content.decode(encoding)
                except UnicodeDecodeError:
                    continue
                except Exception:
                    continue
            
            # 如果所有编码都失败，使用errors='ignore'
            try:
                return text_content.decode('utf-8', errors='ignore')
            except Exception:
                return str(text_content)
        
        # 其他类型转换为字符串
        try:
            return str(text_content)
        except Exception:
            return ""
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息 - 修复版，正确处理Milvus的统计信息"""
        try:
            # 对于Milvus，使用正确的API调用
            vector_db_type = type(self.vector_db).__name__
            logger.debug(f"向量数据库类型: {vector_db_type}")
            
            if "Milvus" in vector_db_type:
                try:
                    # 使用MilvusClient的has_collection方法
                    has_collection = self.vector_db.client.has_collection(self.collection_name)
                    if not has_collection:
                        return {'exists': False, 'name': self.collection_name}
                    
                    # 尝试直接使用pymilvus获取实体数量
                    try:
                        from pymilvus import Collection
                        collection = Collection(self.collection_name)
                        collection.load()  # 确保集合已加载
                        
                        # 获取实体数量
                        num_entities = collection.num_entities
                        logger.debug(f"Milvus集合 {self.collection_name} 实体数量: {num_entities}")
                        
                        return {
                            'name': self.collection_name,
                            'count': num_entities,
                            'exists': True,
                            'type': 'Milvus'
                        }
                        
                    except Exception as milvus_error:
                        logger.warning(f"直接查询Milvus实体数量失败: {milvus_error}")
                        
                        # 回退方法：尝试搜索来判断是否有数据
                        try:
                            # 创建一个测试向量
                            sample_vector = [0.0] * 768  # 假设768维，后面会用实际维度
                            
                            # 尝试获取实际的嵌入维度
                            try:
                                test_embedding = self.embedding_model.embed_query("test")
                                sample_vector = [0.0] * len(test_embedding)
                            except Exception:
                                # 如果无法获取实际维度，使用常见维度
                                for dim in [768, 1024, 512, 1536]:
                                    try:
                                        sample_vector = [0.0] * dim
                                        break
                                    except Exception:
                                        continue
                            
                            # 执行测试搜索
                            search_results = self.vector_db.search_data(
                                collection=self.collection_name,
                                vector=sample_vector,
                                top_k=1
                            )
                            
                            if search_results:
                                # 如果能搜到结果，说明有数据，但无法精确计数
                                return {
                                    'name': self.collection_name,
                                    'count': -1,  # 用-1表示有数据但无法精确计数
                                    'exists': True,
                                    'type': 'Milvus',
                                    'note': '集合存在且有数据，但无法获取精确数量'
                                }
                            else:
                                # 搜索无结果，可能集合为空
                                return {
                                    'name': self.collection_name,
                                    'count': 0,
                                    'exists': True,
                                    'type': 'Milvus',
                                    'note': '集合存在但可能为空'
                                }
                                
                        except Exception as search_error:
                            logger.warning(f"测试搜索失败: {search_error}")
                            
                            # 最后的回退：确认集合存在但无法获取详细信息
                            return {
                                'name': self.collection_name,
                                'count': -1,
                                'exists': True,
                                'type': 'Milvus',
                                'note': '集合存在但无法获取统计信息'
                            }
                            
                except Exception as e:
                    logger.error(f"检查Milvus集合失败: {e}")
                    return {'exists': False, 'error': str(e), 'name': self.collection_name}
            
            # 对于其他类型的向量数据库，使用通用方法
            else:
                # 检查集合是否存在（适用于有has_collection方法的向量数据库）
                if hasattr(self.vector_db, 'has_collection'):
                    has_collection = self.vector_db.has_collection(self.collection_name)
                    if not has_collection:
                        return {'exists': False, 'name': self.collection_name}
                
                # 通过list_collections获取信息
                collections = self.vector_db.list_collections()
                
                for collection in collections:
                    # 尝试不同可能的属性名称获取集合名
                    collection_name = None
                    if hasattr(collection, 'collection_name'):
                        collection_name = collection.collection_name
                    elif hasattr(collection, 'name'):
                        collection_name = collection.name
                    elif hasattr(collection, 'id'):
                        collection_name = collection.id
                    elif isinstance(collection, str):
                        collection_name = collection
                    else:
                        collection_name = str(collection)
                    
                    if collection_name == self.collection_name:
                        # 尝试获取实体数量
                        num_entities = 0
                        
                        # 尝试多种方式获取实体数量
                        count_methods = ['num_entities', 'count', 'size', 'length']
                        for method in count_methods:
                            if hasattr(collection, method):
                                try:
                                    value = getattr(collection, method)
                                    # 如果是方法，调用它
                                    if callable(value):
                                        num_entities = value()
                                    else:
                                        num_entities = value
                                    logger.debug(f"通过 {method} 获取数量: {num_entities}")
                                    break
                                except Exception as e:
                                    logger.debug(f"尝试方法 {method} 失败: {e}")
                                    continue
                        
                        return {
                            'name': collection_name,
                            'count': num_entities,
                            'exists': True,
                            'type': vector_db_type
                        }
                
                # 如果通过list_collections没找到，但可能集合仍然存在
                return {
                    'name': self.collection_name,
                    'count': -1,
                    'exists': False,  # 无法确认存在
                    'type': vector_db_type,
                    'note': '无法通过list_collections找到集合'
                }
            
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {
                'exists': False, 
                'error': str(e),
                'name': self.collection_name
            } 