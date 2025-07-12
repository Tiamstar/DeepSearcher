#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一代码检查服务

整合ESLint、Cppcheck和SonarQube工具，提供统一的接口和配置
简化用户使用体验，减少维护成本
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from shared.interfaces import CodeReviewInterface, CodeReviewRequest, CodeReviewResult

logger = logging.getLogger(__name__)

class CheckerType(Enum):
    """检查器类型"""
    ESLINT = "eslint"           # JavaScript/TypeScript/ArkTS
    CPPCHECK = "cppcheck"       # C/C++
    SONARQUBE = "sonarqube"     # 多语言支持

@dataclass
class CheckerConfig:
    """检查器配置"""
    enabled: bool = True
    priority: int = 1  # 1=高优先级, 2=中优先级, 3=低优先级
    timeout: int = 120
    custom_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_rules is None:
            self.custom_rules = {}

class UnifiedCodeChecker(CodeReviewInterface):
    """统一代码检查服务"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化统一代码检查服务
        
        Args:
            config: 配置字典，包含各检查器的配置
        """
        self.config = config or {}
        self.checkers = {}
        
        # 扩展语言映射，调整优先级
        self.language_map = {
            # JavaScript/TypeScript/ArkTS -> 优先ESLint，回退SonarQube
            'javascript': [CheckerType.ESLINT, CheckerType.SONARQUBE],
            'typescript': [CheckerType.ESLINT, CheckerType.SONARQUBE], 
            'arkts': [CheckerType.ESLINT],  # ArkTS专用处理器
            'ets': [CheckerType.ESLINT],    # ArkTS文件扩展名支持
            'hml': [CheckerType.ESLINT],    # 华为HML文件支持
            
            # C/C++ -> 优先SonarQube，回退Cppcheck
            'c': [CheckerType.SONARQUBE, CheckerType.CPPCHECK],
            'cpp': [CheckerType.SONARQUBE, CheckerType.CPPCHECK],
            'c++': [CheckerType.SONARQUBE, CheckerType.CPPCHECK],
            
            # Python -> 优先SonarQube，回退内置检查器
            'python': [CheckerType.SONARQUBE],
            
            # SonarQube独有支持的语言
            'java': [CheckerType.SONARQUBE],
            'csharp': [CheckerType.SONARQUBE],
            'c#': [CheckerType.SONARQUBE],
            'go': [CheckerType.SONARQUBE],
            'kotlin': [CheckerType.SONARQUBE],
            'scala': [CheckerType.SONARQUBE],
            'php': [CheckerType.SONARQUBE],
            'ruby': [CheckerType.SONARQUBE],
            'swift': [CheckerType.SONARQUBE],
            'html': [CheckerType.SONARQUBE],
            'css': [CheckerType.SONARQUBE],
            'xml': [CheckerType.SONARQUBE],
        }
        
        self._initialize_checkers()
    
    def _initialize_checkers(self):
        """初始化检查器"""
        # 初始化 SonarQube 检查器（优先级最高）
        try:
            if self._is_checker_enabled(CheckerType.SONARQUBE):
                from shared.services.sonarqube_service import SonarQubeService
                
                # 获取SonarQube配置，使用更新后的默认值
                sonar_config = self.config.get('sonarqube', {})
                
                # 设置默认配置
                default_sonar_config = {
                    'sonar_host_url': 'http://localhost:9000',
                    'sonar_login': 'admin',
                    'sonar_password': 'deepsearch',
                    'project_key': 'deep-searcher',
                    'timeout': 300
                }
                
                # 合并配置
                final_config = {**default_sonar_config, **sonar_config}
                
                self.checkers[CheckerType.SONARQUBE] = SonarQubeService(**final_config)
                logger.info("✅ SonarQube 检查器初始化成功")
                logger.info(f"   - 服务地址: {final_config['sonar_host_url']}")
                logger.info(f"   - 项目键: {final_config['project_key']}")
                logger.info(f"   - 认证方式: 用户名密码 (admin/deepsearch)")
        except Exception as e:
            logger.warning(f"SonarQube 检查器初始化失败: {e}")
        
        # 初始化 ESLint 检查器
        try:
            if self._is_checker_enabled(CheckerType.ESLINT):
                from shared.services.eslint_service import ESLintService
                self.checkers[CheckerType.ESLINT] = ESLintService(
                    config=self.config.get('eslint', {})
                )
                logger.info("✅ ESLint 检查器初始化成功")
        except Exception as e:
            logger.warning(f"ESLint 检查器初始化失败: {e}")
        
        # 初始化 Cppcheck 检查器
        try:
            if self._is_checker_enabled(CheckerType.CPPCHECK):
                from shared.services.cppcheck_service import CppcheckService
                self.checkers[CheckerType.CPPCHECK] = CppcheckService(
                    **self.config.get('cppcheck', {})
                )
                logger.info("✅ Cppcheck 检查器初始化成功")
        except Exception as e:
            logger.warning(f"Cppcheck 检查器初始化失败: {e}")
    
    def _is_checker_enabled(self, checker_type: CheckerType) -> bool:
        """检查指定检查器是否启用"""
        checker_config = self.config.get(checker_type.value, {})
        return checker_config.get('enabled', True)
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return len(self.checkers) > 0
    
    async def review_code(self, request: CodeReviewRequest) -> CodeReviewResult:
        """
        统一代码检查入口
        
        Args:
            request: 代码检查请求
            
        Returns:
            代码检查结果
        """
        start_time = time.time()
        request_id = f"unified_{int(time.time())}_{hash(request.code) % 10000}"
        
        try:
            # 选择合适的检查器（支持优先级和回退）
            checker_type, checker = self._select_best_checker(request.language)
            
            if not checker_type:
                return self._create_unsupported_result(request_id, request, start_time)
            
            if not checker or not checker.is_available():
                return self._create_unavailable_result(request_id, request, checker_type, start_time)
            
            # 执行检查
            result = await checker.review_code(request)
            
            # 添加统一服务的元数据
            if result.metadata is None:
                result.metadata = {}
            
            result.metadata.update({
                "unified_service": True,
                "selected_checker": checker_type.value,
                "total_processing_time": time.time() - start_time,
                "available_checkers": [ct.value for ct in self.checkers.keys()],
                "language_support": self._get_language_support_info(request.language)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"统一代码检查失败: {e}")
            return self._create_error_result(request_id, request, str(e), start_time)
    
    def _select_best_checker(self, language: str) -> tuple[Optional[CheckerType], Optional[CodeReviewInterface]]:
        """根据语言选择最佳的检查器，支持优先级和回退"""
        # 获取该语言支持的检查器列表（按优先级排序）
        preferred_checkers = self.language_map.get(language.lower(), [])
        
        # 按优先级尝试每个检查器
        for checker_type in preferred_checkers:
            if checker_type in self.checkers:
                checker = self.checkers[checker_type]
                if checker.is_available():
                    logger.info(f"为 {language} 选择检查器: {checker_type.value}")
                    return checker_type, checker
                else:
                    logger.warning(f"检查器 {checker_type.value} 不可用，尝试下一个")
        
        # 如果没有找到合适的检查器
        logger.warning(f"没有找到支持 {language} 语言的可用检查器")
        return None, None
    
    def _get_language_support_info(self, language: str) -> Dict[str, Any]:
        """获取语言支持信息"""
        preferred_checkers = self.language_map.get(language.lower(), [])
        available_checkers = [ct.value for ct in preferred_checkers if ct in self.checkers]
        
        return {
            "language": language,
            "preferred_checkers": [ct.value for ct in preferred_checkers],
            "available_checkers": available_checkers,
            "is_supported": len(available_checkers) > 0
        }
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        supported = []
        for language, checkers in self.language_map.items():
            # 检查是否有可用的检查器
            if any(ct in self.checkers for ct in checkers):
                supported.append(language)
        
        return sorted(supported)
    
    def get_checker_status(self) -> Dict[str, Any]:
        """获取检查器状态信息"""
        status = {}
        for checker_type in CheckerType:
            if checker_type in self.checkers:
                checker = self.checkers[checker_type]
                status[checker_type.value] = {
                    "available": checker.is_available(),
                    "enabled": self._is_checker_enabled(checker_type)
                }
            else:
                status[checker_type.value] = {
                    "available": False,
                    "enabled": self._is_checker_enabled(checker_type)
                }
        
        return status
    
    def get_language_checker_mapping(self) -> Dict[str, List[str]]:
        """获取语言到检查器的映射"""
        return {
            lang: [ct.value for ct in checkers]
            for lang, checkers in self.language_map.items()
        }
    
    def _create_unsupported_result(self, request_id: str, request: CodeReviewRequest, start_time: float) -> CodeReviewResult:
        """创建不支持语言的结果"""
        supported_languages = self.get_supported_languages()
        
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            language=request.language,
            checker="UnifiedChecker",
            score=0,
            issues=[],
            suggestions=[
                f"统一检查器暂不支持 {request.language} 语言",
                f"支持的语言: {', '.join(supported_languages)}"
            ],
            report=f"不支持的语言: {request.language}\n支持的语言: {', '.join(supported_languages)}",
            execution_time=time.time() - start_time,
            metadata={
                'error': 'unsupported_language',
                'supported_languages': supported_languages
            }
        )
    
    def _create_unavailable_result(self, request_id: str, request: CodeReviewRequest, 
                                 checker_type: CheckerType, start_time: float) -> CodeReviewResult:
        """创建检查器不可用的结果"""
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            language=request.language,
            checker="UnifiedChecker",
            score=0,
            issues=[],
            suggestions=[
                f"选定的检查器 {checker_type.value} 不可用",
                "请检查相关工具是否正确安装和配置"
            ],
            report=f"检查器 {checker_type.value} 不可用",
            execution_time=time.time() - start_time,
            metadata={
                'error': 'checker_unavailable',
                'selected_checker': checker_type.value
            }
        )
    
    def _create_error_result(self, request_id: str, request: CodeReviewRequest, 
                           error: str, start_time: float) -> CodeReviewResult:
        """创建错误结果"""
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            language=request.language,
            checker="UnifiedChecker",
            score=0,
            issues=[],
            suggestions=["检查统一检查器配置", "查看日志获取详细错误信息"],
            report=f"统一检查器执行失败: {error}",
            execution_time=time.time() - start_time,
            metadata={'error': error}
        )

# 便捷配置函数

def create_simple_config(
    enable_eslint: bool = True,
    enable_cppcheck: bool = True,
    enable_sonarqube: bool = True,
    enable_deveco_integration: bool = False,
    deveco_path: str = ''
) -> Dict[str, Any]:
    """
    创建简单配置
    
    Args:
        enable_eslint: 是否启用ESLint
        enable_cppcheck: 是否启用Cppcheck
        enable_sonarqube: 是否启用SonarQube
        enable_deveco_integration: 是否启用DevEco Studio集成(针对ArkTS)
        deveco_path: DevEco Studio可执行文件路径
        
    Returns:
        配置字典
        
    注意:
        ESLint配置已增强，支持ArkTS语言检查和专用规则
    """
    return {
        'eslint': {
            'enabled': enable_eslint,
            'priority': 1,
            'timeout': 120,
            'languages': ['javascript', 'typescript', 'arkts', 'ets', 'hml'],
            'enable_deveco_integration': enable_deveco_integration,
            'deveco_path': deveco_path
        },
        'cppcheck': {
            'enabled': enable_cppcheck,
            'priority': 2,
            'timeout': 120,
            'languages': ['c', 'cpp', 'c++']
        },
        'sonarqube': {
            'enabled': enable_sonarqube,
            'timeout': 300,
            'sonar_host_url': 'http://localhost:9000',
            'sonar_login': 'admin',
            'sonar_password': 'deepsearch',
            'project_key': 'deep-searcher'
        }
    }

def create_advanced_config() -> Dict[str, Any]:
    """创建高级配置示例"""
    return {
        'eslint': {
            'enabled': True,
            'timeout': 45,
            'eslint_path': 'npx eslint',
            'custom_rules': {
                'no-console': 'warn',
                'prefer-const': 'error'
            }
        },
        'cppcheck': {
            'enabled': True,
            'timeout': 60,
            'cppcheck_path': 'cppcheck',
            'enable_cert_rules': True,
            'enable_misra_rules': False
        },
        'sonarqube': {
            'enabled': True,
            'timeout': 600,
            'sonar_host_url': 'http://localhost:9000',
            'sonar_login': 'admin',
            'sonar_password': 'deepsearch',
            'project_key': 'deep-searcher',
            'sonar_sources': '.',
            'sonar_exclusions': '**/*test*/**,**/node_modules/**'
        }
    } 