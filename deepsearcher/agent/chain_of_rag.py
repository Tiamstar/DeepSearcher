from typing import List, Tuple

from deepsearcher.agent.base import RAGAgent, describe_class
from deepsearcher.agent.collection_router import CollectionRouter
from deepsearcher.embedding.base import BaseEmbedding
from deepsearcher.llm.base import BaseLLM
from deepsearcher.utils import log
from deepsearcher.vector_db import RetrievalResult
from deepsearcher.vector_db.base import BaseVectorDB, deduplicate_results

FOLLOWUP_QUERY_PROMPT = """You are using a search tool to answer the main query by iteratively searching the database. Given the following intermediate queries and answers, generate a new simple follow-up question that can help answer the main query. You may rephrase or decompose the main query when previous answers are not helpful. Ask simple follow-up questions only as the search tool may not understand complex questions.

## Previous intermediate queries and answers
{intermediate_context}

## Main query to answer
{query}

Respond with a simple follow-up question that will help answer the main query, do not explain yourself or output anything else.
"""

INTERMEDIATE_ANSWER_PROMPT = """Given the following documents, generate an appropriate answer for the query. DO NOT hallucinate any information, only use the provided documents to generate the answer. Respond "No relevant information found" if the documents do not contain useful information.

## Documents
{retrieved_documents}

## Query
{sub_query}

Respond with a concise answer only, do not explain yourself or output anything else.
"""

FINAL_ANSWER_PROMPT = """Given the following intermediate queries and answers, generate a final answer for the main query by combining relevant information. Note that intermediate answers are generated by an LLM and may not always be accurate.

## Documents
{retrieved_documents}

## Intermediate queries and answers
{intermediate_context}

## Main query
{query}

Respond with an appropriate answer only, do not explain yourself or output anything else.
"""

REFLECTION_PROMPT = """Given the following intermediate queries and answers, judge whether you have enough information to answer the main query. If you believe you have enough information, respond with "Yes", otherwise respond with "No".

## Intermediate queries and answers
{intermediate_context}

## Main query
{query}

Respond with "Yes" or "No" only, do not explain yourself or output anything else.
"""

GET_SUPPORTED_DOCS_PROMPT = """Given the following documents, select the ones that are support the Q-A pair.

## Documents
{retrieved_documents}

## Q-A Pair
### Question
{query}
### Answer
{answer}

Respond with ONLY a python list of indices of the selected documents. For example: [0, 1, 2]
Do not include any explanation or other text, just the list.
"""


@describe_class(
    "This agent can decompose complex queries and gradually find the fact information of sub-queries. "
    "It is very suitable for handling concrete factual queries and multi-hop questions."
)
class ChainOfRAG(RAGAgent):
    """
    Chain of Retrieval-Augmented Generation (RAG) agent implementation.

    This agent implements a multi-step RAG process where each step can refine
    the query and retrieval process based on previous results, creating a chain
    of increasingly focused and relevant information retrieval and generation.
    Inspired by: https://arxiv.org/pdf/2501.14342

    """

    def __init__(
        self,
        llm: BaseLLM,
        embedding_model: BaseEmbedding,
        vector_db: BaseVectorDB,
        max_iter: int = 4,
        early_stopping: bool = False,
        route_collection: bool = True,
        text_window_splitter: bool = True,
        **kwargs,
    ):
        """
        Initialize the ChainOfRAG agent with configuration parameters.

        Args:
            llm (BaseLLM): The language model to use for generating answers.
            embedding_model (BaseEmbedding): The embedding model to use for embedding queries.
            vector_db (BaseVectorDB): The vector database to search for relevant documents.
            max_iter (int, optional): The maximum number of iterations for the RAG process. Defaults to 4.
            early_stopping (bool, optional): Whether to use early stopping. Defaults to False.
            route_collection (bool, optional): Whether to route the query to specific collections. Defaults to True.
            text_window_splitter (bool, optional): Whether use text_window splitter. Defaults to True.
        """
        self.llm = llm
        self.embedding_model = embedding_model
        self.vector_db = vector_db
        self.max_iter = max_iter
        self.early_stopping = early_stopping
        self.route_collection = route_collection
        self.collection_router = CollectionRouter(
            llm=self.llm, vector_db=self.vector_db, dim=embedding_model.dimension
        )
        self.text_window_splitter = text_window_splitter

    def _reflect_get_subquery(self, query: str, intermediate_context: List[str]) -> Tuple[str, int]:
        chat_response = self.llm.chat(
            [
                {
                    "role": "user",
                    "content": FOLLOWUP_QUERY_PROMPT.format(
                        query=query,
                        intermediate_context="\n".join(intermediate_context),
                    ),
                }
            ]
        )
        return self.llm.remove_think(chat_response.content), chat_response.total_tokens

    def _retrieve_and_answer(self, query: str) -> Tuple[str, List[RetrievalResult], int]:
        consume_tokens = 0
        if self.route_collection:
            selected_collections, n_token_route = self.collection_router.invoke(
                query=query, dim=self.embedding_model.dimension
            )
        else:
            selected_collections = self.collection_router.all_collections
            n_token_route = 0
        consume_tokens += n_token_route
        all_retrieved_results = []
        for collection in selected_collections:
            log.color_print(f"<search> Search [{query}] in [{collection}]...  </search>\n")
            query_vector = self.embedding_model.embed_query(query)
            retrieved_results = self.vector_db.search_data(
                collection=collection, vector=query_vector, query_text=query
            )
            all_retrieved_results.extend(retrieved_results)
        all_retrieved_results = deduplicate_results(all_retrieved_results)
        chat_response = self.llm.chat(
            [
                {
                    "role": "user",
                    "content": INTERMEDIATE_ANSWER_PROMPT.format(
                        retrieved_documents=self._format_retrieved_results(all_retrieved_results),
                        sub_query=query,
                    ),
                }
            ]
        )
        return (
            self.llm.remove_think(chat_response.content),
            all_retrieved_results,
            consume_tokens + chat_response.total_tokens,
        )

    def _get_supported_docs(
        self,
        retrieved_results: List[RetrievalResult],
        query: str,
        intermediate_answer: str,
    ) -> Tuple[List[RetrievalResult], int]:
        supported_retrieved_results = []
        token_usage = 0
        if "No relevant information found" not in intermediate_answer:
            chat_response = self.llm.chat(
                [
                    {
                        "role": "user",
                        "content": GET_SUPPORTED_DOCS_PROMPT.format(
                            retrieved_documents=self._format_retrieved_results(retrieved_results),
                            query=query,
                            answer=intermediate_answer,
                        ),
                    }
                ]
            )
            try:
                # 清理响应内容，移除可能的解释文本
                response_content = self.llm.remove_think(chat_response.content).strip()
                
                # 如果响应包含多行，尝试找到看起来像列表的行
                if '\n' in response_content:
                    lines = response_content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('[') and line.endswith(']'):
                            response_content = line
                            break
                
                supported_doc_indices = self.llm.literal_eval(response_content)
                
                # 确保返回的是列表
                if not isinstance(supported_doc_indices, list):
                    supported_doc_indices = [supported_doc_indices] if supported_doc_indices is not None else []
                
                supported_retrieved_results = [
                    retrieved_results[int(i)]
                    for i in supported_doc_indices
                    if isinstance(i, (int, str)) and str(i).isdigit() and int(i) < len(retrieved_results)
                ]
                token_usage = chat_response.total_tokens
                
            except Exception as e:
                log.color_print(f"<error> Error parsing supported docs indices: {e} </error>\n")
                log.color_print(f"<error> LLM response was: {chat_response.content} </error>\n")
                # 发生错误时，返回所有检索到的文档作为备选
                supported_retrieved_results = retrieved_results
                token_usage = chat_response.total_tokens
                
        return supported_retrieved_results, token_usage

    def _check_has_enough_info(
        self, query: str, intermediate_contexts: List[str]
    ) -> Tuple[bool, int]:
        if not intermediate_contexts:
            return False, 0

        chat_response = self.llm.chat(
            [
                {
                    "role": "user",
                    "content": REFLECTION_PROMPT.format(
                        query=query,
                        intermediate_context="\n".join(intermediate_contexts),
                    ),
                }
            ]
        )
        has_enough_info = self.llm.remove_think(chat_response.content).strip().lower() == "yes"
        return has_enough_info, chat_response.total_tokens

    def retrieve(self, query: str, **kwargs) -> Tuple[List[RetrievalResult], int, dict]:
        """
        Retrieves relevant documents based on the input query and iteratively refines the search.

        This method iteratively refines the search query based on intermediate results, retrieves documents,
        and filters out supported documents. It keeps track of the intermediate contexts and token usage.

        Args:
            query (str): The initial search query.
            **kwargs: Additional keyword arguments.
                - max_iter (int, optional): The maximum number of iterations for refinement. Defaults to self.max_iter.

        Returns:
            Tuple[List[RetrievalResult], int, dict]: A tuple containing:
                - List[RetrievalResult]: The list of all retrieved and deduplicated results.
                - int: The total token usage across all iterations.
                - dict: A dictionary containing additional information, including the intermediate contexts.
        """
        max_iter = kwargs.pop("max_iter", self.max_iter)
        intermediate_contexts = []
        all_retrieved_results = []
        token_usage = 0
        for iter in range(max_iter):
            log.color_print(f">> Iteration: {iter + 1}\n")
            followup_query, n_token0 = self._reflect_get_subquery(query, intermediate_contexts)
            intermediate_answer, retrieved_results, n_token1 = self._retrieve_and_answer(
                followup_query
            )
            supported_retrieved_results, n_token2 = self._get_supported_docs(
                retrieved_results, followup_query, intermediate_answer
            )

            all_retrieved_results.extend(supported_retrieved_results)
            intermediate_idx = len(intermediate_contexts) + 1
            intermediate_contexts.append(
                f"Intermediate query{intermediate_idx}: {followup_query}\nIntermediate answer{intermediate_idx}: {intermediate_answer}"
            )
            token_usage += n_token0 + n_token1 + n_token2

            if self.early_stopping:
                has_enough_info, n_token_check = self._check_has_enough_info(
                    query, intermediate_contexts
                )
                token_usage += n_token_check

                if has_enough_info:
                    log.color_print(
                        f"<think> Early stopping after iteration {iter + 1}: Have enough information to answer the main query. </think>\n"
                    )
                    break

        all_retrieved_results = deduplicate_results(all_retrieved_results)
        additional_info = {"intermediate_context": intermediate_contexts}
        return all_retrieved_results, token_usage, additional_info

    def query(self, query: str, **kwargs) -> Tuple[str, List[RetrievalResult], int]:
        """
        Executes a query and returns the final answer along with all retrieved results and total token usage.

        This method initiates a query, retrieves relevant documents, and then summarizes the answer based on the retrieved documents and intermediate contexts. It logs the final answer and returns the answer content, all retrieved results, and the total token usage including the tokens used for the final answer.

        Args:
            query (str): The initial query to execute.
            **kwargs: Additional keyword arguments to pass to the `retrieve` method.

        Returns:
            Tuple[str, List[RetrievalResult], int]: A tuple containing:
                - str: The final answer content.
                - List[RetrievalResult]: The list of all retrieved and deduplicated results.
                - int: The total token usage across all iterations, including the final answer.
        """
        all_retrieved_results, n_token_retrieval, additional_info = self.retrieve(query, **kwargs)
        intermediate_context = additional_info["intermediate_context"]
        log.color_print(
            f"<think> Summarize answer from all {len(all_retrieved_results)} retrieved chunks... </think>\n"
        )
        chat_response = self.llm.chat(
            [
                {
                    "role": "user",
                    "content": FINAL_ANSWER_PROMPT.format(
                        retrieved_documents=self._format_retrieved_results(all_retrieved_results),
                        intermediate_context="\n".join(intermediate_context),
                        query=query,
                    ),
                }
            ]
        )
        log.color_print("\n==== FINAL ANSWER====\n")
        log.color_print(self.llm.remove_think(chat_response.content))
        return (
            self.llm.remove_think(chat_response.content),
            all_retrieved_results,
            n_token_retrieval + chat_response.total_tokens,
        )

    def _format_retrieved_results(self, retrieved_results: List[RetrievalResult]) -> str:
        formatted_documents = []
        for i, result in enumerate(retrieved_results):
            if self.text_window_splitter and "wider_text" in result.metadata:
                text = result.metadata["wider_text"]
            else:
                text = result.text
            formatted_documents.append(f"<Document {i}>\n{text}\n<\Document {i}>")
        return "\n".join(formatted_documents)
