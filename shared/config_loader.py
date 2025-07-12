#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 基于现有provide_settings结构
支持为不同Agent配置不同的LLM模型
"""

import os
import sys
import yaml
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# 自动加载.env文件
try:
    from dotenv import load_dotenv
    # 加载项目根目录下的.env文件
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量文件: {env_path}")
    else:
        print(f"⚠️  环境变量文件不存在: {env_path}")
except ImportError:
    print("⚠️  python-dotenv未安装，无法自动加载.env文件")
    print("   请运行: pip install python-dotenv")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class ConfigLoader:
    """
    配置加载器 - 基于现有provide_settings结构
    支持为不同Agent配置不同的LLM模型
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else project_root / "config"
        self.config_file = self.config_dir / "config.yaml"
        self.project_root = project_root
        
        # 加载配置
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            # 处理环境变量
            self._process_env_vars()
            
            logger.info("✅ 配置加载成功")
            
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            raise
    
    def _process_env_vars(self):
        """处理配置中的环境变量"""
        def process_dict(d):
            keys_to_update = []
            for key, value in d.items():
                if isinstance(value, dict):
                    process_dict(value)
                elif isinstance(value, str) and key.endswith("_env"):
                    # 处理环境变量引用
                    env_var_name = value
                    env_value = os.environ.get(env_var_name)
                    if env_value:
                        # 将 api_key_env 替换为 api_key
                        new_key = key.replace("_env", "")
                        keys_to_update.append((key, new_key, env_value))
                        logger.debug(f"环境变量 {env_var_name} 已加载到 {new_key}")
                    else:
                        logger.warning(f"环境变量 {env_var_name} 未设置")
            
            # 更新字典
            for old_key, new_key, new_value in keys_to_update:
                d[new_key] = new_value
                del d[old_key]
        
        if self._config:
            process_dict(self._config)
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config or {}
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置（兼容旧接口）"""
        return self.get_config()
    
    def get_llm_config(self, agent_name: str = None) -> Dict[str, Any]:
        """
        获取LLM配置
        
        Args:
            agent_name: Agent名称，如果指定则尝试获取Agent专用配置
            
        Returns:
            LLM配置字典
        """
        try:
            # 1. 尝试获取Agent专用配置
            if agent_name:
                agents_config = self._config.get("agents", {})
                agent_config = agents_config.get(agent_name, {})
                
                # 检查是否有专用的LLM配置
                if "llm_override" in agent_config:
                    llm_override = agent_config["llm_override"]
                    provider = llm_override.get("provider", "")
                    config = llm_override.get("config", {})
                    
                    logger.info(f"使用Agent {agent_name} 专用LLM配置: {provider}")
                    
                    return {
                        "type": provider.lower(),
                        "provider": provider,
                        "model": config.get("model", ""),
                        "api_key": config.get("api_key", ""),
                        "base_url": config.get("base_url", ""),
                        "temperature": config.get("temperature", 0.7),
                        "max_tokens": config.get("max_tokens", 4000),
                        **config  # 包含所有原始配置
                    }
            
            # 2. 使用全局provide_settings配置
            provide_settings = self._config.get("provide_settings", {})
            llm_config = provide_settings.get("llm", {})
            
            if llm_config:
                provider = llm_config.get("provider", "")
                config = llm_config.get("config", {})
                
                return {
                    "type": provider.lower(),
                    "provider": provider,
                    "model": config.get("model", ""),
                    "api_key": config.get("api_key", ""),
                    "base_url": config.get("base_url", ""),
                    "temperature": config.get("temperature", 0.7),
                    "max_tokens": config.get("max_tokens", 4000),
                    **config  # 包含所有原始配置
                }
            
            # 3. 返回默认配置
            return self._get_fallback_llm_config()
            
        except Exception as e:
            logger.warning(f"获取LLM配置失败，使用默认配置: {e}")
            return self._get_fallback_llm_config()
    
    def get_embedding_config(self, agent_name: str = None) -> Dict[str, Any]:
        """获取嵌入模型配置"""
        try:
            # 1. 尝试获取Agent专用配置
            if agent_name:
                agents_config = self._config.get("agents", {})
                agent_config = agents_config.get(agent_name, {})
                
                if "embedding_override" in agent_config:
                    embedding_override = agent_config["embedding_override"]
                    provider = embedding_override.get("provider", "")
                    config = embedding_override.get("config", {})
                    
                    logger.info(f"使用Agent {agent_name} 专用嵌入模型配置: {provider}")
                    
                    return {
                        "provider": provider,
                        "model": config.get("model", ""),
                        "api_key": config.get("api_key", ""),
                        "base_url": config.get("base_url", ""),
                        "dimension": config.get("dimension", 1024),
                        **config
                    }
            
            # 2. 使用全局provide_settings配置
            provide_settings = self._config.get("provide_settings", {})
            embedding_config = provide_settings.get("embedding", {})
            
            if embedding_config:
                provider = embedding_config.get("provider", "")
                config = embedding_config.get("config", {})
                
                return {
                    "provider": provider,
                    "model": config.get("model", ""),
                    "api_key": config.get("api_key", ""),
                    "base_url": config.get("base_url", ""),
                    "dimension": config.get("dimension", 1024),
                    **config
                }
            
            return self._get_fallback_embedding_config()
            
        except Exception as e:
            logger.warning(f"获取嵌入模型配置失败，使用默认配置: {e}")
            return self._get_fallback_embedding_config()
    
    def get_vector_db_config(self, agent_name: str = None) -> Dict[str, Any]:
        """获取向量数据库配置"""
        try:
            # 1. 尝试获取Agent专用配置
            if agent_name:
                agents_config = self._config.get("agents", {})
                agent_config = agents_config.get(agent_name, {})
                
                if "vector_db_override" in agent_config:
                    vector_db_override = agent_config["vector_db_override"]
                    provider = vector_db_override.get("provider", "")
                    config = vector_db_override.get("config", {})
                    
                    logger.info(f"使用Agent {agent_name} 专用向量数据库配置: {provider}")
                    
                    return {
                        "provider": provider,
                        "default_collection": config.get("default_collection", "default"),
                        "uri": config.get("uri", ""),
                        "token": config.get("token", ""),
                        "host": config.get("host", ""),
                        "port": config.get("port", 19530),
                        **config
                    }
            
            # 2. 使用全局provide_settings配置
            provide_settings = self._config.get("provide_settings", {})
            vector_db_config = provide_settings.get("vector_db", {})
            
            if vector_db_config:
                provider = vector_db_config.get("provider", "")
                config = vector_db_config.get("config", {})
                
                return {
                    "provider": provider,
                    "default_collection": config.get("default_collection", "default"),
                    "uri": config.get("uri", ""),
                    "token": config.get("token", ""),
                    "host": config.get("host", ""),
                    "port": config.get("port", 19530),
                    **config
                }
            
            return self._get_fallback_vector_db_config()
            
        except Exception as e:
            logger.warning(f"获取向量数据库配置失败，使用默认配置: {e}")
            return self._get_fallback_vector_db_config()
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """获取Agent配置"""
        agents = self._config.get("agents", {})
        return agents.get(agent_name, {})
    
    def get_deepsearcher_config(self) -> Dict[str, Any]:
        """获取DeepSearcher配置"""
        # 直接返回provide_settings部分，这与DeepSearcher期望的格式一致
        provide_settings = self._config.get("provide_settings", {})
        deepsearcher_config = self._config.get("deepsearcher", {})
        
        return {
            "provide_settings": provide_settings,
            **deepsearcher_config
        }
    
    def get_huawei_rag_config(self) -> Dict[str, Any]:
        """获取华为RAG配置（兼容性方法）"""
        try:
            llm_config = self.get_llm_config()
            embedding_config = self.get_embedding_config()
            vector_db_config = self.get_vector_db_config()
            
            return {
                "DEFAULT_LLM_PROVIDER": llm_config.get("provider", "DeepSeek"),
                "DEFAULT_LLM_MODEL": llm_config.get("model", "deepseek-coder"),
                "DEFAULT_EMBEDDING_PROVIDER": embedding_config.get("provider", "SiliconflowEmbedding"),
                "DEFAULT_EMBEDDING_MODEL": embedding_config.get("model", "BAAI/bge-m3"),
                "DEFAULT_VECTOR_DB_PROVIDER": vector_db_config.get("provider", "Milvus"),
                "DEFAULT_VECTOR_DB_CONFIG": {
                    "uri": vector_db_config.get("uri", "./milvus.db"),
                    "token": vector_db_config.get("token", "root:Milvus")
                },
                "DEFAULT_COLLECTION_NAME": vector_db_config.get("default_collection", "huawei_docs"),
                "DEFAULT_SEARCH_TOP_K": 5,
                "DEFAULT_SEARCH_THRESHOLD": 0.7
            }
        except Exception as e:
            logger.warning(f"获取华为RAG配置失败，使用默认配置: {e}")
            return self._get_fallback_huawei_rag_config()
    
    def get_search_agent_config(self) -> Dict[str, Any]:
        """获取搜索Agent配置"""
        search_config = self.get_agent_config("search")
        
        # 合并默认配置
        default_config = {
            "enabled": True,
            "port": 8001,
            "description": "智能搜索Agent",
            "local_search": True,
            "online_search": True,
            "max_results": 10,
            "search_timeout": 30
        }
        
        return {**default_config, **search_config}
    
    def get_code_checker_config(self, environment: str = "development") -> Dict[str, Any]:
        """获取代码检查Agent配置"""
        checker_config = self.get_agent_config("code_checker")
        
        default_config = {
            "enabled": True,
            "port": 8004,
            "description": "代码检查Agent",
            "eslint_enabled": True,
            "cppcheck_enabled": True,
            "sonarqube_enabled": False,
            "timeout": 120
        }
        
        return {**default_config, **checker_config}
    
    def get_workflow_config(self, workflow_name: str) -> Dict[str, Any]:
        """获取工作流配置"""
        workflows = self._config.get("workflows", {})
        return workflows.get(workflow_name, {})
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        
        try:
            # 检查基本结构
            required_sections = ["project", "provide_settings", "agents"]
            for section in required_sections:
                if section not in self._config:
                    validation_result["errors"].append(f"缺少必需的配置段: {section}")
                    validation_result["valid"] = False
            
            # 检查Agent配置
            agents = self._config.get("agents", {})
            enabled_agents = [name for name, config in agents.items() if config.get("enabled", False)]
            validation_result["summary"]["enabled_agents"] = enabled_agents
            validation_result["summary"]["total_agents"] = len(agents)
            validation_result["summary"]["enabled_agents_count"] = len(enabled_agents)
            
        except Exception as e:
            validation_result["errors"].append(f"配置验证过程中出错: {e}")
            validation_result["valid"] = False
        
        return validation_result
    
    # ===========================================
    # 向后兼容方法
    # ===========================================
    
    def _get_fallback_llm_config(self) -> Dict[str, Any]:
        """获取默认LLM配置"""
        return {
            "type": "deepseek",
            "provider": "DeepSeek",
            "model": "deepseek-coder",
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "base_url": "",
            "temperature": 0.7,
            "max_tokens": 4000
        }
    
    def _get_fallback_embedding_config(self) -> Dict[str, Any]:
        """获取默认嵌入模型配置"""
        return {
            "provider": "SiliconflowEmbedding",
            "model": "BAAI/bge-m3",
            "api_key": os.environ.get("SILICONFLOW_API_KEY", ""),
            "dimension": 1024
        }
    
    def _get_fallback_vector_db_config(self) -> Dict[str, Any]:
        """获取默认向量数据库配置"""
        return {
            "provider": "Milvus",
            "default_collection": "huawei_agents",
            "uri": "./milvus.db",
            "token": "root:Milvus"
        }
    
    def _get_fallback_huawei_rag_config(self) -> Dict[str, Any]:
        """获取默认华为RAG配置"""
        return {
            "DEFAULT_LLM_PROVIDER": "DeepSeek",
            "DEFAULT_LLM_MODEL": "deepseek-coder",
            "DEFAULT_EMBEDDING_PROVIDER": "SiliconflowEmbedding",
            "DEFAULT_EMBEDDING_MODEL": "BAAI/bge-m3",
            "DEFAULT_VECTOR_DB_PROVIDER": "Milvus",
            "DEFAULT_VECTOR_DB_CONFIG": {"uri": "./milvus.db", "token": "root:Milvus"},
            "DEFAULT_COLLECTION_NAME": "huawei_docs",
            "DEFAULT_SEARCH_TOP_K": 5,
            "DEFAULT_SEARCH_THRESHOLD": 0.7
        }
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
    
    # ===========================================
    # MCP系统专用方法
    # ===========================================
    
    def get_unified_config(self) -> Dict[str, Any]:
        """获取MCP系统的统一配置"""
        try:
            if not self._config:
                logger.warning("配置未加载，返回默认统一配置")
                return self._get_default_unified_config()
            
            # 构建MCP系统需要的统一配置
            unified_config = {
                # 项目信息
                "project": self._config.get("project", {}),
                
                # MCP协议配置
                "mcp": self._config.get("mcp", {
                    "protocol_version": "2024-11-05",
                    "timeout": 300,
                    "max_concurrent_requests": 10
                }),
                
                # API服务配置
                "api": self._config.get("api", {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "debug": False
                }),
                
                # 日志配置
                "logging": self._config.get("logging", {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "file": "logs/mcp_system.log"
                }),
                
                # Agent配置
                "agents": self._config.get("agents", {}),
                
                # 工作流配置
                "workflows": self._config.get("workflows", {}),
                
                # 全局服务配置
                "provide_settings": self._config.get("provide_settings", {})
            }
            
            logger.info("✅ 统一配置获取成功")
            return unified_config
            
        except Exception as e:
            logger.error(f"获取统一配置失败: {e}")
            return self._get_default_unified_config()
    
    def _get_default_unified_config(self) -> Dict[str, Any]:
        """获取默认的统一配置"""
        return {
            "project": {
                "name": "华为多Agent协作项目",
                "description": "基于MCP协议的华为技术栈多Agent协作代码生成系统",
                "version": "2.0.0"
            },
            "mcp": {
                "protocol_version": "2024-11-05",
                "timeout": 300,
                "max_concurrent_requests": 10
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/mcp_system.log"
            },
            "agents": {
                "search": {
                    "description": "智能搜索Agent",
                    "enabled": True,
                    "port": 8001
                },
                "project_manager": {
                    "description": "项目管理Agent",
                    "enabled": True,
                    "port": 8002
                },
                "code_generator": {
                    "description": "代码生成Agent",
                    "enabled": True,
                    "port": 8003
                },
                "code_checker": {
                    "description": "代码检查Agent",
                    "enabled": True,
                    "port": 8004
                },
                "final_generator": {
                    "description": "最终代码生成Agent",
                    "enabled": True,
                    "port": 8005
                }
            },
            "workflows": {
                "complete_code_generation": {
                    "enabled": True,
                    "timeout": 600,
                    "steps": [
                        {"agent": "project_manager", "method": "project.decompose", "timeout": 120},
                        {"agent": "search", "method": "search.online", "timeout": 120},
                        {"agent": "code_generator", "method": "code.generate", "timeout": 180},
                        {"agent": "code_checker", "method": "code.check.unified", "timeout": 120},
                        {"agent": "final_generator", "method": "code.finalize", "timeout": 120}
                    ]
                }
            },
            "provide_settings": {
                "llm": {
                    "provider": "DeepSeek",
                    "config": {
                        "model": "deepseek-coder",
                        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
                        "base_url": "",
                        "temperature": 0.1,
                        "max_tokens": 8000
                    }
                },
                "embedding": {
                    "provider": "SiliconflowEmbedding",
                    "config": {
                        "model": "BAAI/bge-m3",
                        "api_key": os.environ.get("SILICONFLOW_API_KEY", ""),
                        "dimension": 1024
                    }
                },
                "vector_db": {
                    "provider": "Milvus",
                    "config": {
                        "default_collection": "huawei_agents",
                        "uri": "./milvus.db",
                        "token": "root:Milvus"
                    }
                }
            }
        }


def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """获取全局配置加载器实例"""
    global _config_loader
    if '_config_loader' not in globals() or _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    return _config_loader

# 全局实例
_config_loader = None 