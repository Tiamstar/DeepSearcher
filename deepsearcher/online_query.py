from typing import List, Tuple

# from deepsearcher.configuration import vector_db, embedding_model, llm
from deepsearcher import configuration
from deepsearcher.vector_db.base import RetrievalResult


def query(original_query: str, max_iter: int = 3) -> Tuple[str, List[RetrievalResult], int]:
    """
    Query the knowledge base with a question and get an answer.

    This function uses the default searcher to query the knowledge base and generate
    an answer based on the retrieved information.

    Args:
        original_query: The question or query to search for.
        max_iter: Maximum number of iterations for the search process.

    Returns:
        A tuple containing:
            - The generated answer as a string
            - A list of retrieval results that were used to generate the answer
            - The number of tokens consumed during the process
    """
    default_searcher = configuration.default_searcher
    return default_searcher.query(original_query, max_iter=max_iter)


def retrieve(
    original_query: str, max_iter: int = 3
) -> Tuple[List[RetrievalResult], List[str], int]:
    """
    Retrieve relevant information from the knowledge base without generating an answer.

    This function uses the default searcher to retrieve information from the knowledge base
    that is relevant to the query.

    Args:
        original_query: The question or query to search for.
        max_iter: Maximum number of iterations for the search process.

    Returns:
        A tuple containing:
            - A list of retrieval results
            - An empty list (placeholder for future use)
            - The number of tokens consumed during the process
    """
    default_searcher = configuration.default_searcher
    retrieved_results, consume_tokens, metadata = default_searcher.retrieve(
        original_query, max_iter=max_iter
    )
    return retrieved_results, [], consume_tokens


def naive_retrieve(query: str, collection: str = None, top_k=10) -> List[RetrievalResult]:
    """
    Perform a simple retrieval from the knowledge base using the naive RAG approach.

    This function uses the naive RAG agent to retrieve information from the knowledge base
    without any advanced techniques like iterative refinement.

    Args:
        query: The question or query to search for.
        collection: The name of the collection to search in. If None, searches in all collections.
        top_k: The maximum number of results to return.

    Returns:
        A list of retrieval results.
    """
    naive_rag = configuration.naive_rag
    all_retrieved_results, consume_tokens, _ = naive_rag.retrieve(query)
    return all_retrieved_results


def naive_rag_query(
    query: str, collection: str = None, top_k=10
) -> Tuple[str, List[RetrievalResult]]:
    """
    Query the knowledge base using the naive RAG approach and get an answer.

    This function uses the naive RAG agent to query the knowledge base and generate
    an answer based on the retrieved information, without any advanced techniques.

    Args:
        query: The question or query to search for.
        collection: The name of the collection to search in. If None, searches in all collections.
        top_k: The maximum number of results to consider.

    Returns:
        A tuple containing:
            - The generated answer as a string
            - A list of retrieval results that were used to generate the answer
    """
    naive_rag = configuration.naive_rag
    answer, retrieved_results, consume_tokens = naive_rag.query(query)
    return answer, retrieved_results


def search_only_query(
    query: str, collection: str = None, max_iter: int = 2, top_k: int = 10
) -> Tuple[List[RetrievalResult], int]:
    """
    只搜索不生成答案的查询模式
    
    使用ChainOfSearchOnly代理进行查询，只返回检索结果，不生成答案
    
    Args:
        query: 查询问题
        collection: 要搜索的集合名称，如果为None，则搜索所有集合
        max_iter: 最大迭代次数
        top_k: 要考虑的最大结果数
        
    Returns:
        包含以下内容的元组:
            - 检索结果列表
            - 消耗的token数量
    """
    from deepsearcher.agent.chain_of_search import ChainOfSearchOnly
    
    # 确保配置已初始化
    if not hasattr(configuration, "llm") or not configuration.llm:
        raise ValueError("LLM not configured. Please initialize configuration first.")
    
    # 创建ChainOfSearchOnly实例
    search_only_agent = ChainOfSearchOnly(
        llm=configuration.llm,
        embedding_model=configuration.embedding,
        vector_db=configuration.vector_db,
        max_iter=max_iter,
        early_stopping=False,
        route_collection=collection is None,  # 如果指定了集合，则不需要路由
    )
    
    # 执行仅搜索查询
    _, retrieved_results, token_usage = search_only_agent.query(query, max_iter=max_iter)
    
    return retrieved_results, token_usage
