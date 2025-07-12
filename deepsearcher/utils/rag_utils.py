#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG utilities - RAG相关工具函数
"""

from typing import List, Dict, Any, Union
import hashlib


def deduplicate_results(results: List[Dict[str, Any]], 
                       key_field: str = 'content',
                       similarity_threshold: float = 0.9) -> List[Dict[str, Any]]:
    """
    去重搜索结果
    
    Args:
        results: 搜索结果列表
        key_field: 用于去重的字段名
        similarity_threshold: 相似度阈值
        
    Returns:
        去重后的结果列表
    """
    if not results:
        return results
    
    # 简单的基于内容哈希的去重
    seen_hashes = set()
    deduplicated = []
    
    for result in results:
        content = result.get(key_field, '')
        if not content:
            continue
            
        # 生成内容哈希
        content_hash = hashlib.md5(str(content).encode('utf-8')).hexdigest()
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            deduplicated.append(result)
    
    return deduplicated


def merge_search_results(results_list: List[List[Dict[str, Any]]], 
                        weights: List[float] = None) -> List[Dict[str, Any]]:
    """
    合并多个搜索结果列表
    
    Args:
        results_list: 多个搜索结果列表
        weights: 各结果列表的权重
        
    Returns:
        合并后的结果列表
    """
    if not results_list:
        return []
    
    if weights is None:
        weights = [1.0] * len(results_list)
    
    all_results = []
    
    for i, results in enumerate(results_list):
        weight = weights[i] if i < len(weights) else 1.0
        
        for result in results:
            # 调整分数权重
            if 'score' in result:
                result = result.copy()
                result['score'] = result['score'] * weight
            
            all_results.append(result)
    
    # 按分数排序
    all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 去重
    return deduplicate_results(all_results)


def calculate_relevance_score(query: str, content: str) -> float:
    """
    计算查询和内容的相关性分数
    
    Args:
        query: 查询文本
        content: 内容文本
        
    Returns:
        相关性分数 (0-1)
    """
    if not query or not content:
        return 0.0
    
    # 简单的关键词匹配计算相关性
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    
    if not query_words:
        return 0.0
    
    # 计算交集比例
    intersection = query_words.intersection(content_words)
    return len(intersection) / len(query_words)


__all__ = ['deduplicate_results', 'merge_search_results', 'calculate_relevance_score'] 