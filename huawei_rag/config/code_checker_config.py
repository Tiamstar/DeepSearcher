#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码检查器配置文件

提供不同使用场景的配置示例
"""

import os
from typing import Dict, Any

# 基础配置 - 最简单的设置
BASIC_CONFIG = {
    "eslint": {
        "enabled": True,
        "timeout": 30
    },
    "cppcheck": {
        "enabled": True,
        "enable_cert_rules": True,
        "timeout": 30
    }
}

# 开发环境配置 - 快速检查
DEVELOPMENT_CONFIG = {
    "eslint": {
        "enabled": True,
        "timeout": 15,  # 快速检查
        "custom_rules": {
            "extends": ["eslint:recommended", "@typescript-eslint/recommended"],
            "rules": {
                "@typescript-eslint/no-explicit-any": "warn",  # 警告而非错误
                "prefer-const": "error",
                "no-unused-vars": "warn"
            }
        }
    },
    "cppcheck": {
        "enabled": True,
        "enable_cert_rules": False,  # 开发时禁用严格规则
        "timeout": 20
    }
}

# 生产环境配置 - 严格检查
PRODUCTION_CONFIG = {
    "eslint": {
        "enabled": True,
        "timeout": 60,
        "custom_rules": {
            "extends": [
                "eslint:recommended", 
                "@typescript-eslint/recommended",
                "@typescript-eslint/recommended-requiring-type-checking"
            ],
            "rules": {
                "@typescript-eslint/no-explicit-any": "error",
                "@typescript-eslint/explicit-function-return-type": "error",
                "prefer-const": "error",
                "no-unused-vars": "error",
                "no-console": "error"
            }
        }
    },
    "cppcheck": {
        "enabled": True,
        "enable_cert_rules": True,
        "enable_misra_rules": True,  # 生产环境启用MISRA
        "timeout": 120
    }
}

# 华为专用配置 - 针对华为技术栈优化
HUAWEI_OPTIMIZED_CONFIG = {
    "eslint": {
        "enabled": True,
        "timeout": 45,
        "custom_rules": {
            "extends": [
                "@typescript-eslint/recommended"
            ],
            "rules": {
                # ArkTS特殊规则
                "@typescript-eslint/no-explicit-any": "error",
                "prefer-const": "error",
                "no-unused-vars": "error",
                
                # 安全规则
                "no-eval": "error",
                "no-implied-eval": "error"
            }
        }
    },
    "cppcheck": {
        "enabled": True,
        "enable_cert_rules": True,
        "timeout": 90
    }
}

def get_config_by_environment(env: str = "development") -> Dict[str, Any]:
    """
    根据环境获取配置
    
    Args:
        env: 环境名称 (development, production, huawei)
        
    Returns:
        配置字典
    """
    configs = {
        "basic": BASIC_CONFIG,
        "development": DEVELOPMENT_CONFIG,
        "dev": DEVELOPMENT_CONFIG,
        "production": PRODUCTION_CONFIG,
        "prod": PRODUCTION_CONFIG,
        "huawei": HUAWEI_OPTIMIZED_CONFIG
    }
    
    return configs.get(env.lower(), DEVELOPMENT_CONFIG)

def load_config_from_env() -> Dict[str, Any]:
    """
    从环境变量加载配置
    
    环境变量:
        CODE_CHECKER_ENV: 配置环境 (development/production/huawei)
        
    Returns:
        配置字典
    """
    env = os.getenv("CODE_CHECKER_ENV", "development")
    config = get_config_by_environment(env)
    
    return config

def create_custom_config(
    environment: str = "development",
    eslint_strict: bool = False,
    cppcheck_security: bool = True
) -> Dict[str, Any]:
    """
    创建自定义配置
    
    Args:
        environment: 基础环境配置
        eslint_strict: ESLint是否使用严格模式
        cppcheck_security: Cppcheck是否启用安全检查
        
    Returns:
        自定义配置字典
    """
    config = get_config_by_environment(environment)
    
    # ESLint严格模式
    if eslint_strict:
        config["eslint"]["custom_rules"]["rules"].update({
            "@typescript-eslint/no-explicit-any": "error",
            "@typescript-eslint/explicit-function-return-type": "error",
            "no-console": "error"
        })
    
    # Cppcheck安全检查
    if cppcheck_security:
        config["cppcheck"]["enable_cert_rules"] = True
    
    return config

# 预定义的快速配置函数
def quick_config_for_frontend() -> Dict[str, Any]:
    """前端项目快速配置"""
    return {
        "eslint": {
            "enabled": True,
            "timeout": 30,
            "custom_rules": {
                "extends": ["eslint:recommended", "@typescript-eslint/recommended"],
                "rules": {
                    "prefer-const": "error",
                    "no-unused-vars": "warn",
                    "@typescript-eslint/no-explicit-any": "warn"
                }
            }
        },
        "cppcheck": {"enabled": False}
    }

def quick_config_for_backend() -> Dict[str, Any]:
    """后端项目快速配置"""
    return {
        "eslint": {"enabled": False},
        "cppcheck": {
            "enabled": True,
            "enable_cert_rules": True,
            "timeout": 60
        }
    }

def quick_config_for_harmonyos() -> Dict[str, Any]:
    """鸿蒙系统项目快速配置"""
    return HUAWEI_OPTIMIZED_CONFIG 