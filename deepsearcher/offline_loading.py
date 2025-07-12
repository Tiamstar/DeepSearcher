import os
from typing import List, Union, Set, Optional
import hashlib

from tqdm import tqdm

# from deepsearcher.configuration import embedding_model, vector_db, file_loader
from deepsearcher import configuration
from deepsearcher.loader.splitter import split_docs_to_chunks
from deepsearcher.utils import log


def _generate_document_id(file_path: str, content_hash: str = None) -> str:
    """
    生成文档唯一ID
    
    Args:
        file_path: 文件路径
        content_hash: 内容哈希值（可选）
    
    Returns:
        文档唯一ID
    """
    if content_hash:
        return f"{os.path.basename(file_path)}_{content_hash[:8]}"
    else:
        return f"{os.path.basename(file_path)}_{hash(file_path) % 1000000}"


def _get_existing_document_ids(vector_db, collection_name: str, embedding_model) -> Set[str]:
    """
    获取现有文档ID集合
    
    Args:
        vector_db: 向量数据库实例
        collection_name: 集合名称
        embedding_model: 嵌入模型实例
        
    Returns:
        现有文档ID的集合
    """
    try:
        # 检查集合是否存在
        if hasattr(vector_db, 'client') and hasattr(vector_db.client, 'has_collection'):
            if not vector_db.client.has_collection(collection_name):
                log.color_print(f"Collection [{collection_name}] does not exist, will create new collection")
                return set()
        
        # 创建测试向量进行搜索
        test_vector = embedding_model.embed_query("test document")
        
        # 搜索现有文档（使用大的top_k值尝试获取所有文档）
        try:
            results = vector_db.search_data(
                collection=collection_name,
                vector=test_vector,
                top_k=10000  # 尝试获取尽可能多的文档
            )
            
            # 提取文档ID
            existing_ids = set()
            for result in results:
                if hasattr(result, 'metadata') and result.metadata:
                    doc_id = result.metadata.get('document_id')
                    if doc_id:
                        existing_ids.add(doc_id)
            
            log.color_print(f"Found {len(existing_ids)} existing documents in collection [{collection_name}]")
            return existing_ids
            
        except Exception as e:
            log.warning(f"Cannot retrieve existing document IDs: {e}")
            return set()
            
    except Exception as e:
        log.warning(f"Failed to get existing document IDs: {e}")
        return set()


def _filter_new_chunks(chunks: List, existing_ids: Set[str]) -> List:
    """
    过滤出新的文档块（不在现有ID集合中的）
    
    Args:
        chunks: 所有文档块列表
        existing_ids: 现有文档ID集合
        
    Returns:
        新文档块列表
    """
    if not existing_ids:
        return chunks
    
    new_chunks = []
    for chunk in chunks:
        doc_id = chunk.metadata.get('document_id')
        if doc_id and doc_id not in existing_ids:
            new_chunks.append(chunk)
        elif not doc_id:
            # 如果没有document_id，也认为是新文档
            new_chunks.append(chunk)
    
    return new_chunks


def load_from_local_files(
    paths_or_directory: Union[str, List[str]],
    collection_name: str = None,
    collection_description: str = None,
    force_new_collection: bool = False,
    incremental_update: bool = True,  # 新增：启用增量更新
    chunk_size: int = 1500,
    chunk_overlap: int = 100,
    batch_size: int = 256,
):
    """
    Load knowledge from local files or directories into the vector database with incremental update support.

    This function processes files from the specified paths or directories,
    splits them into chunks, embeds the chunks, and stores them in the vector database.
    Now supports incremental updates to avoid re-processing existing documents.

    Args:
        paths_or_directory: A single path or a list of paths to files or directories to load.
        collection_name: Name of the collection to store the data in. If None, uses the default collection.
        collection_description: Description of the collection. If None, no description is set.
        force_new_collection: If True, drops the existing collection and creates a new one.
        incremental_update: If True, only process new documents not already in the collection.
        chunk_size: Size of each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.
        batch_size: Number of chunks to process at once during embedding.

    Raises:
        FileNotFoundError: If any of the specified paths do not exist.
    """
    vector_db = configuration.vector_db
    if collection_name is None:
        collection_name = vector_db.default_collection
    collection_name = collection_name.replace(" ", "_").replace("-", "_")
    embedding_model = configuration.embedding_model
    file_loader = configuration.file_loader
    
    # 检查现有文档ID（如果启用增量更新且不强制重建）
    existing_ids = set()
    if incremental_update and not force_new_collection:
        log.color_print("🔍 Checking existing documents for incremental update...")
        existing_ids = _get_existing_document_ids(vector_db, collection_name, embedding_model)
    
    # 初始化集合
    vector_db.init_collection(
        dim=embedding_model.dimension,
        collection=collection_name,
        description=collection_description,
        force_new_collection=force_new_collection,
    )
    
    if isinstance(paths_or_directory, str):
        paths_or_directory = [paths_or_directory]
    
    all_docs = []
    for path in tqdm(paths_or_directory, desc="Loading files"):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Error: File or directory '{path}' does not exist.")
        if os.path.isdir(path):
            docs = file_loader.load_directory(path)
        else:
            docs = file_loader.load_file(path)
        
        # 为每个文档添加document_id到metadata中
        for doc in docs:
            if hasattr(doc, 'metadata') and doc.metadata is not None:
                # 生成基于文件路径和内容的唯一ID
                content_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
                doc_id = _generate_document_id(path, content_hash)
                doc.metadata['document_id'] = doc_id
                doc.metadata['source_file'] = path
        
        all_docs.extend(docs)
    
    log.color_print(f"Loaded {len(all_docs)} documents from {len(paths_or_directory)} paths")
    
    # 分块处理
    chunks = split_docs_to_chunks(
        all_docs,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    # 过滤新文档块（如果启用增量更新）
    if incremental_update and existing_ids:
        original_count = len(chunks)
        chunks = _filter_new_chunks(chunks, existing_ids)
        log.color_print(f"Incremental update: {len(chunks)}/{original_count} chunks are new")
        
        if not chunks:
            log.color_print("✅ No new documents to process. Collection is up to date.")
            return
    
    # 生成嵌入向量
    log.color_print(f"Generating embeddings for {len(chunks)} chunks...")
    chunks = embedding_model.embed_chunks(chunks, batch_size=batch_size)
    
    # 插入数据
    log.color_print(f"Inserting {len(chunks)} chunks into collection [{collection_name}]...")
    vector_db.insert_data(collection=collection_name, chunks=chunks)
    
    log.color_print(f"✅ Successfully loaded {len(chunks)} chunks into vector database!")


def load_from_website(
    urls: Union[str, List[str]],
    collection_name: str = None,
    collection_description: str = None,
    force_new_collection: bool = False,
    incremental_update: bool = True,  # 新增：启用增量更新
    chunk_size: int = 1500,
    chunk_overlap: int = 100,
    batch_size: int = 256,
    **crawl_kwargs,
):
    """
    Load knowledge from websites into the vector database with incremental update support.

    This function crawls the specified URLs, processes the content,
    splits it into chunks, embeds the chunks, and stores them in the vector database.
    Now supports incremental updates to avoid re-processing existing documents.

    Args:
        urls: A single URL or a list of URLs to crawl.
        collection_name: Name of the collection to store the data in. If None, uses the default collection.
        collection_description: Description of the collection. If None, no description is set.
        force_new_collection: If True, drops the existing collection and creates a new one.
        incremental_update: If True, only process new documents not already in the collection.
        chunk_size: Size of each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.
        batch_size: Number of chunks to process at once during embedding.
        **crawl_kwargs: Additional keyword arguments to pass to the web crawler.
    """
    if isinstance(urls, str):
        urls = [urls]
    vector_db = configuration.vector_db
    if collection_name is None:
        collection_name = vector_db.default_collection
    collection_name = collection_name.replace(" ", "_").replace("-", "_")
    embedding_model = configuration.embedding_model
    web_crawler = configuration.web_crawler

    # 检查现有文档ID（如果启用增量更新且不强制重建）
    existing_ids = set()
    if incremental_update and not force_new_collection:
        log.color_print("🔍 Checking existing documents for incremental update...")
        existing_ids = _get_existing_document_ids(vector_db, collection_name, embedding_model)

    # 初始化集合
    vector_db.init_collection(
        dim=embedding_model.dimension,
        collection=collection_name,
        description=collection_description,
        force_new_collection=force_new_collection,
    )

    # 爬取网页内容
    all_docs = web_crawler.crawl_urls(urls, **crawl_kwargs)
    
    # 为每个文档添加document_id到metadata中
    for doc in all_docs:
        if hasattr(doc, 'metadata') and doc.metadata is not None:
            # 生成基于URL和内容的唯一ID
            url = doc.metadata.get('source', 'unknown_url')
            content_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
            doc_id = _generate_document_id(url, content_hash)
            doc.metadata['document_id'] = doc_id
            doc.metadata['source_url'] = url

    log.color_print(f"Crawled {len(all_docs)} documents from {len(urls)} URLs")

    # 分块处理
    chunks = split_docs_to_chunks(
        all_docs,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    # 过滤新文档块（如果启用增量更新）
    if incremental_update and existing_ids:
        original_count = len(chunks)
        chunks = _filter_new_chunks(chunks, existing_ids)
        log.color_print(f"Incremental update: {len(chunks)}/{original_count} chunks are new")
        
        if not chunks:
            log.color_print("✅ No new documents to process. Collection is up to date.")
            return

    # 生成嵌入向量
    log.color_print(f"Generating embeddings for {len(chunks)} chunks...")
    chunks = embedding_model.embed_chunks(chunks, batch_size=batch_size)
    
    # 插入数据
    log.color_print(f"Inserting {len(chunks)} chunks into collection [{collection_name}]...")
    vector_db.insert_data(collection=collection_name, chunks=chunks)
    
    log.color_print(f"✅ Successfully loaded {len(chunks)} chunks into vector database!")
