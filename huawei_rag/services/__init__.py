"""
华为代码检查服务模块

提供统一的代码检查服务：
- UnifiedCodeChecker: 统一代码检查服务（推荐使用）
- ESLintService: JavaScript/TypeScript/ArkTS 检查
- CppcheckService: C/C++ 静态分析
- SonarQubeService: 多语言代码质量检查（Docker版）

推荐使用 UnifiedCodeChecker，它会自动选择最合适的检查器。
"""

# 统一服务（推荐使用）
from .unified_checker import UnifiedCodeChecker, create_simple_config, create_advanced_config

# 单独的检查服务
from .eslint_service import ESLintService
from .cppcheck_service import CppcheckService

# SonarQube服务（需要Docker环境）
try:
    from .sonarqube_service import SonarQubeService
    SONARQUBE_AVAILABLE = True
except ImportError as e:
    # 如果依赖缺失，提供占位符
    class SonarQubeService:
        def __init__(self, **kwargs):
            raise ImportError(f"SonarQube服务依赖缺失: {e}")
    SONARQUBE_AVAILABLE = False

# 配置相关
try:
    from ..config.code_checker_config import (
        get_config_by_environment,
        load_config_from_env,
        quick_config_for_frontend,
        quick_config_for_backend,
        quick_config_for_harmonyos
    )
except ImportError:
    # 如果配置模块不存在，提供空的函数
    def get_config_by_environment(env: str = "development"): return {}
    def load_config_from_env(): return {}
    def quick_config_for_frontend(): return {}
    def quick_config_for_backend(): return {}
    def quick_config_for_harmonyos(): return {}

# 便捷配置函数
def create_sonarqube_config(
    sonar_host_url: str = "http://localhost:9000",
    sonar_login: str = "admin", 
    sonar_password: str = "deepsearch",
    project_key: str = "deep-searcher",
    timeout: int = 300
) -> dict:
    """
    创建SonarQube配置
    
    Args:
        sonar_host_url: SonarQube服务地址
        sonar_login: 登录用户名
        sonar_password: 密码
        project_key: 项目键
        timeout: 分析超时时间（秒）
    
    Returns:
        SonarQube配置字典
    """
    return {
        "sonarqube": {
            "enabled": True,
            "sonar_host_url": sonar_host_url,
            "sonar_login": sonar_login,
            "sonar_password": sonar_password,
            "project_key": project_key,
            "timeout": timeout
        }
    }

def create_comprehensive_config(
    enable_sonarqube: bool = True,
    enable_eslint: bool = True,
    enable_cppcheck: bool = True,
    sonar_host_url: str = "http://localhost:9000"
) -> dict:
    """
    创建全面的代码检查配置
    
    Args:
        enable_sonarqube: 是否启用SonarQube
        enable_eslint: 是否启用ESLint
        enable_cppcheck: 是否启用Cppcheck
        sonar_host_url: SonarQube服务地址
    
    Returns:
        完整的检查器配置
    """
    config = {}
    
    if enable_sonarqube:
        config["sonarqube"] = {
            "enabled": True,
            "sonar_host_url": sonar_host_url,
            "sonar_login": "admin",
            "sonar_password": "deepsearch",
            "project_key": "deep-searcher",
            "timeout": 300
        }
    
    if enable_eslint:
        config["eslint"] = {
            "enabled": True,
            "timeout": 30
        }
    
    if enable_cppcheck:
        config["cppcheck"] = {
            "enabled": True,
            "enable_cert_rules": True,
            "timeout": 30
        }
    
    return config

__all__ = [
    # 统一服务（推荐）
    'UnifiedCodeChecker',
    'create_simple_config',
    'create_advanced_config',
    
    # 单独服务
    'ESLintService',
    'CppcheckService',
    'SonarQubeService',
    
    # 配置函数
    'get_config_by_environment',
    'load_config_from_env',
    'quick_config_for_frontend',
    'quick_config_for_backend',
    'quick_config_for_harmonyos',
    'create_sonarqube_config',
    'create_comprehensive_config',
    
    # 状态标识
    'SONARQUBE_AVAILABLE'
] 