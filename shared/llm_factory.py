#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM工厂 - 根据配置创建LLM实例
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMFactory:
    """LLM工厂类"""
    
    @staticmethod
    def create_llm(llm_config: Dict[str, Any]) -> Optional[object]:
        """根据配置创建LLM实例"""
        try:
            provider = llm_config.get("provider", "").lower()
            
            if provider == "deepseek":
                return LLMFactory._create_deepseek_llm(llm_config)
            elif provider == "openai":
                return LLMFactory._create_openai_llm(llm_config)
            elif provider == "anthropic":
                return LLMFactory._create_anthropic_llm(llm_config)
            else:
                logger.warning(f"不支持的LLM提供商: {provider}")
                return None
                
        except Exception as e:
            logger.error(f"创建LLM实例失败: {e}")
            return None
    
    @staticmethod
    def _create_deepseek_llm(config: Dict[str, Any]) -> Optional[object]:
        """创建DeepSeek LLM实例"""
        try:
            # 首先尝试从环境变量获取API key
            import os
            api_key_env = config.get("api_key_env", "DEEPSEEK_API_KEY")
            api_key = config.get("api_key") or os.getenv(api_key_env)
            
            if not api_key:
                logger.error(f"LLM API key未找到，请检查环境变量 {api_key_env}")
                return None
            
            from deepsearcher.llm import DeepSeek
            
            # DeepSeek类不接受temperature和max_tokens参数，这些参数在chat方法中处理
            llm = DeepSeek(
                api_key=api_key,
                model=config.get("model", "deepseek-chat")
            )
            
            # 将temperature和max_tokens设置为实例属性，供后续使用
            llm._temperature = config.get("temperature", 0.7)
            llm._max_tokens = config.get("max_tokens", 2048)
            
            logger.info(f"✅ LLM创建成功")
            return llm
            
        except ImportError:
            logger.error("LLM不可用，请安装相关依赖")
            return None
        except Exception as e:
            logger.error(f"创建LLM失败: {e}")
            return None
    
    @staticmethod
    def _create_openai_llm(config: Dict[str, Any]) -> Optional[object]:
        """创建OpenAI LLM实例"""
        try:
            from deepsearcher.llm import OpenAI
            
            return OpenAI(
                api_key=config.get("api_key"),
                model=config.get("model", "gpt-3.5-turbo"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2048)
            )
        except ImportError:
            logger.error("LLM不可用，请安装相关依赖")
            return None
        except Exception as e:
            logger.error(f"创建LLM失败: {e}")
            return None
    
    @staticmethod
    def _create_anthropic_llm(config: Dict[str, Any]) -> Optional[object]:
        """创建Anthropic LLM实例"""
        try:
            from deepsearcher.llm import Anthropic
            
            return Anthropic(
                api_key=config.get("api_key"),
                model=config.get("model", "claude-3-sonnet-20240229"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2048)
            )
        except ImportError:
            logger.error("LLM不可用，请安装相关依赖")
            return None
        except Exception as e:
            logger.error(f"创建LLM失败: {e}")
            return None