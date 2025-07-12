#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chain of Search - 只搜索不生成答案的RAG变体
基于ChainOfRAG但移除了LLM生成答案的部分
"""

from typing import List, Tuple, Dict, Any, Optional
import logging
from deepsearcher.agent.base import RAGAgent, describe_class
from deepsearcher.agent.chain_of_rag import ChainOfRAG, FOLLOWUP_QUERY_PROMPT
from deepsearcher.agent.collection_router import CollectionRouter
from deepsearcher.llm.base import BaseLLM
from deepsearcher.embedding.base import BaseEmbedding
from deepsearcher.vector_db.base import BaseVectorDB, RetrievalResult
from deepsearcher.utils.log_utils import get_logger
from deepsearcher.utils.rag_utils import deduplicate_results

log = get_logger(__name__)

@describe_class(
    "This agent can decompose complex queries and find relevant documents without generating answers. "
    "It is suitable for search-only mode where you want to examine raw search results."
)
class ChainOfSearchOnly(ChainOfRAG):
    """
    Chain of Search Only agent implementation.
    
    This agent implements a multi-step search process where each step can refine
    the query based on previous results, but doesn't generate answers using LLM.
    It only returns the retrieved documents.
    """

    def __init__(
        self,
        llm: BaseLLM,
        embedding_model: BaseEmbedding,
        vector_db: BaseVectorDB,
        max_iter: int = 2,  # 默认减少迭代次数，因为只是搜索
        early_stopping: bool = False,
        route_collection: bool = True,
        text_window_splitter: bool = True,
        **kwargs,
    ):
        """
        Initialize the ChainOfSearchOnly agent with configuration parameters.

        Args:
            llm (BaseLLM): The language model to use for query reformulation only.
            embedding_model (BaseEmbedding): The embedding model to use for embedding queries.
            vector_db (BaseVectorDB): The vector database to search for relevant documents.
            max_iter (int, optional): The maximum number of iterations for the search process. Defaults to 2.
            early_stopping (bool, optional): Whether to use early stopping. Defaults to False.
            route_collection (bool, optional): Whether to route the query to specific collections. Defaults to True.
            text_window_splitter (bool, optional): Whether use text_window splitter. Defaults to True.
        """
        super().__init__(
            llm=llm,
            embedding_model=embedding_model,
            vector_db=vector_db,
            max_iter=max_iter,
            early_stopping=early_stopping,
            route_collection=route_collection,
            text_window_splitter=text_window_splitter,
            **kwargs
        )
    
    def search_only_query(self, query: str, **kwargs) -> Tuple[List[RetrievalResult], int, dict]:
        """
        执行仅搜索查询，返回检索结果但不生成答案
        
        Args:
            query (str): 搜索查询
            **kwargs: 额外参数
                - max_iter (int): 最大迭代次数
                
        Returns:
            Tuple[List[RetrievalResult], int, dict]: 检索结果、token消耗和额外信息
        """
        # 直接调用父类的retrieve方法，它只执行搜索不生成答案
        return self.retrieve(query, **kwargs)
    
    def query(self, query: str, **kwargs) -> Tuple[str, List[RetrievalResult], int]:
        """
        重写query方法，不生成最终答案，只返回检索结果
        
        Args:
            query (str): 搜索查询
            **kwargs: 额外参数
            
        Returns:
            Tuple[str, List[RetrievalResult], int]: 空答案字符串、检索结果和token消耗
        """
        # 只执行检索
        all_retrieved_results, n_token_retrieval, additional_info = self.retrieve(query, **kwargs)
        
        # 不生成答案，直接返回检索结果
        log.color_print(f"<think> Search completed. Found {len(all_retrieved_results)} relevant documents. </think>\n")
        
        # 返回空答案字符串、检索结果和token消耗
        return "", all_retrieved_results, n_token_retrieval 