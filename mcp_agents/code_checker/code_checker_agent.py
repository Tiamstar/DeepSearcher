#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Checker Agent
华为多Agent协作系统 - 代码检查Agent
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Dict, Any, List
from datetime import datetime

from mcp_agents.base import MCPAgent, MCPMessage
from shared.interfaces import CodeReviewRequest, CodeReviewResult
from shared.services import UnifiedCodeChecker, create_simple_config

# 导入鸿蒙编译服务
from mcp_agents.harmonyos import HarmonyOSCompilerService

logger = logging.getLogger(__name__)

class CodeCheckerAgent(MCPAgent):
    """代码检查Agent - 负责代码质量检查和审查"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """初始化代码检查Agent"""
        super().__init__(agent_id, config)
        
        # 华为ArkTS项目只使用codelinter，不使用其他检查器
        # 初始化统一代码检查器（禁用ESLint，只保留必要的检查器用于其他语言）
        checker_config = create_simple_config(
            enable_eslint=False,        # 禁用ESLint
            enable_cppcheck=True,       # 保留C/C++检查
            enable_sonarqube=False      # 禁用SonarQube
        )
        
        # 合并用户配置
        if 'code_checker' in config:
            checker_config.update(config['code_checker'])
        
        self.code_checker = UnifiedCodeChecker(checker_config)
        
        # 初始化鸿蒙编译服务（用于codelinter）
        self.harmonyos_compiler = HarmonyOSCompilerService()
        
        logger.info(f"✅ CodeChecker Agent {agent_id} 初始化完成")
        logger.info(f"   - 支持的语言: {', '.join(self.code_checker.get_supported_languages())}")
        
        # 只显示实际启用的检查器，过滤掉ESLint和SonarQube
        checker_status = self.code_checker.get_checker_status()
        enabled_checkers = []
        for checker_name, status in checker_status.items():
            if checker_name not in ['eslint', 'sonarqube'] and status.get('enabled', False):
                enabled_checkers.append(checker_name)
        # 为华为ArkTS项目，主要使用codelinter
        enabled_checkers.append('codelinter')
        logger.info(f"   - 可用检查器: {enabled_checkers}")
        
        # 声明能力 - 华为ArkTS项目专用
        # 移除ESLint和SonarQube，只保留codelinter和必要的检查器
        self.declare_capability("code.check.cppcheck", {
            "description": "使用Cppcheck检查C/C++代码（非ArkTS项目）",
            "parameters": ["code", "language", "standards"]
        })
        self.declare_capability("code.check.codelinter", {
            "description": "使用codelinter检查HarmonyOS ArkTS代码（主要检查器）",
            "parameters": ["project_path", "files_to_check"]
        })
        self.declare_capability("code.check.harmonyos", {
            "description": "鸿蒙静态代码检查（仅使用codelinter）",
            "parameters": ["project_path", "generated_files", "check_mode"]
        })
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化代码检查Agent"""
        try:
            # 获取检查器状态
            checker_status = self.code_checker.get_checker_status()
            supported_languages = self.code_checker.get_supported_languages()
            
            self.logger.info("代码检查Agent初始化成功")
            
            return {
                "agent_id": self.agent_id,
                "capabilities": self.capabilities,
                "checker_status": checker_status,
                "supported_languages": supported_languages,
                "language_checker_mapping": self.code_checker.get_language_checker_mapping(),
                "initialized_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"代码检查Agent初始化失败: {str(e)}")
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理代码检查相关请求"""
        try:
            method = message.method
            params = message.params or {}
            
            # 华为ArkTS项目只支持codelinter检查
            if method == "code.check.cppcheck":
                result = await self._cppcheck_check(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "code.check.codelinter":
                result = await self._codelinter_check(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "code.check.harmonyos":
                result = await self._harmonyos_check(params)
                return self.protocol.create_response(message.id, result)
            
            # 废弃的方法提示
            elif method in ["code.check.eslint", "code.check.sonarqube", "code.check.unified"]:
                return self.protocol.create_response(message.id, {
                    "success": False,
                    "error": f"方法 {method} 已废弃。华为ArkTS项目请使用 code.check.harmonyos",
                    "suggestion": "使用 code.check.harmonyos 进行鸿蒙代码检查"
                })
            
            else:
                return self.protocol.handle_method_not_found(message.id, method)
                
        except Exception as e:
            self.logger.error(f"处理代码检查请求失败: {str(e)}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _unified_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """统一代码检查"""
        code = params.get("code", "")
        language = params.get("language", "unknown")
        review_type = params.get("review_type", "comprehensive")
        original_query = params.get("original_query", "")
        
        if not code:
            raise ValueError("代码内容不能为空")
        
        try:
            # 创建检查请求
            request = CodeReviewRequest(
                original_query=original_query,
                code=code,
                language=language,
                review_type=review_type,
                metadata={"agent_id": self.agent_id}
            )
            
            # 执行检查
            result = await self.code_checker.review_code(request)
            
            # 格式化结果
            formatted_result = self._format_check_result(result)
            self.logger.info(f"统一代码检查完成，语言: {language}，评分: {result.score}")
            return {"formatted_review_data": formatted_result}
            
        except Exception as e:
            self.logger.error(f"统一代码检查失败: {str(e)}")
            raise
    
    async def _eslint_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ESLint检查"""
        code = params.get("code", "")
        language = params.get("language", "javascript")
        rules = params.get("rules", [])
        original_query = params.get("original_query", "")
        
        if not code:
            raise ValueError("代码内容不能为空")
        
        # 确保语言支持ESLint
        if language.lower() not in ["javascript", "typescript", "arkts"]:
            raise ValueError(f"ESLint不支持语言: {language}")
        
        try:
            request = CodeReviewRequest(
                original_query=original_query,
                code=code,
                language=language,
                review_type="eslint",
                metadata={
                    "agent_id": self.agent_id,
                    "custom_rules": rules,
                    "force_checker": "eslint"
                }
            )
            
            result = await self.code_checker.review_code(request)
            formatted_result = self._format_check_result(result)
            self.logger.info(f"ESLint检查完成，语言: {language}")
            return {"formatted_review_data": formatted_result}
            
        except Exception as e:
            self.logger.error(f"ESLint检查失败: {str(e)}")
            raise
    
    async def _cppcheck_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cppcheck检查"""
        code = params.get("code", "")
        language = params.get("language", "cpp")
        standards = params.get("standards", [])
        original_query = params.get("original_query", "")
        
        if not code:
            raise ValueError("代码内容不能为空")
        
        # 确保语言支持Cppcheck
        if language.lower() not in ["c", "cpp", "c++"]:
            raise ValueError(f"Cppcheck不支持语言: {language}")
        
        try:
            request = CodeReviewRequest(
                original_query=original_query,
                code=code,
                language=language,
                review_type="cppcheck",
                metadata={
                    "agent_id": self.agent_id,
                    "standards": standards,
                    "force_checker": "cppcheck"
                }
            )
            
            result = await self.code_checker.review_code(request)
            formatted_result = self._format_check_result(result)
            self.logger.info(f"Cppcheck检查完成，语言: {language}")
            return {"formatted_review_data": formatted_result}
            
        except Exception as e:
            self.logger.error(f"Cppcheck检查失败: {str(e)}")
            raise
    
    async def _sonarqube_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """SonarQube检查"""
        code = params.get("code", "")
        language = params.get("language", "python")
        quality_gate = params.get("quality_gate", "default")
        original_query = params.get("original_query", "")
        
        if not code:
            raise ValueError("代码内容不能为空")
        
        try:
            request = CodeReviewRequest(
                original_query=original_query,
                code=code,
                language=language,
                review_type="sonarqube",
                metadata={
                    "agent_id": self.agent_id,
                    "quality_gate": quality_gate,
                    "force_checker": "sonarqube"
                }
            )
            
            result = await self.code_checker.review_code(request)
            formatted_result = self._format_check_result(result)
            self.logger.info(f"SonarQube检查完成，语言: {language}")
            return {"formatted_review_data": formatted_result}
            
        except Exception as e:
            self.logger.error(f"SonarQube检查失败: {str(e)}")
            raise
    
    def _format_check_result(self, result: CodeReviewResult) -> Dict[str, Any]:
        """格式化检查结果"""
        return {
            "request_id": result.request_id,
            "original_query": result.original_query,
            "code": result.code,
            "review_report": result.report,
            "issues_found": result.issues,
            "suggestions": result.suggestions,
            "score": result.score,
            "review_metadata": result.metadata,
            "processing_time": result.execution_time,
            "agent_id": self.agent_id,
            "checked_at": datetime.now().isoformat()
        }
    
    async def get_resources(self) -> List[Dict[str, Any]]:
        """获取代码检查资源"""
        return [
            {
                "uri": "checker://eslint/rules",
                "name": "ESLint规则配置",
                "description": "JavaScript/TypeScript/ArkTS代码检查规则",
                "mimeType": "application/json"
            },
            {
                "uri": "checker://cppcheck/standards",
                "name": "Cppcheck标准配置",
                "description": "C/C++代码检查标准和规则",
                "mimeType": "application/json"
            },
            {
                "uri": "checker://sonarqube/quality_gates",
                "name": "SonarQube质量门禁",
                "description": "多语言代码质量门禁配置",
                "mimeType": "application/json"
            }
        ]
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取代码检查工具"""
        return [
            {
                "name": "unified_code_check",
                "description": "统一代码检查，自动选择最佳检查器",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要检查的代码"
                        },
                        "language": {
                            "type": "string",
                            "description": "代码语言",
                            "enum": ["javascript", "typescript", "arkts", "c", "cpp", "python", "java", "go"]
                        },
                        "review_type": {
                            "type": "string",
                            "description": "检查类型",
                            "enum": ["comprehensive", "syntax", "security", "performance"],
                            "default": "comprehensive"
                        },
                        "original_query": {
                            "type": "string",
                            "description": "原始需求描述"
                        }
                    },
                    "required": ["code", "language"]
                }
            },
            {
                "name": "eslint_check",
                "description": "使用ESLint检查JavaScript/TypeScript/ArkTS代码",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要检查的代码"
                        },
                        "language": {
                            "type": "string",
                            "description": "代码语言",
                            "enum": ["javascript", "typescript", "arkts"]
                        },
                        "rules": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "自定义ESLint规则"
                        },
                        "original_query": {
                            "type": "string",
                            "description": "原始需求描述"
                        }
                    },
                    "required": ["code", "language"]
                }
            },
            {
                "name": "cppcheck_check",
                "description": "使用Cppcheck检查C/C++代码",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要检查的代码"
                        },
                        "language": {
                            "type": "string",
                            "description": "代码语言",
                            "enum": ["c", "cpp", "c++"]
                        },
                        "standards": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "C++标准（如c++11, c++14, c++17）"
                        },
                        "original_query": {
                            "type": "string",
                            "description": "原始需求描述"
                        }
                    },
                    "required": ["code", "language"]
                }
            },
            {
                "name": "sonarqube_check",
                "description": "使用SonarQube检查代码",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要检查的代码"
                        },
                        "language": {
                            "type": "string",
                            "description": "代码语言"
                        },
                        "quality_gate": {
                            "type": "string",
                            "description": "质量门禁配置",
                            "default": "default"
                        },
                        "original_query": {
                            "type": "string",
                            "description": "原始需求描述"
                        }
                    },
                    "required": ["code", "language"]
                }
            }
        ]
    
    async def get_checker_status(self) -> Dict[str, Any]:
        """获取检查器状态"""
        if self.code_checker:
            status = self.code_checker.get_checker_status()
            status["agent_id"] = self.agent_id
            return status
        return {"agent_id": self.agent_id, "error": "代码检查器未初始化"}
    
    async def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        if self.code_checker:
            return self.code_checker.get_supported_languages()
        return []
    
    async def _codelinter_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """使用codelinter检查HarmonyOS项目"""
        try:
            project_path = params.get("project_path", "MyApplication2")
            
            # 验证项目路径
            if not project_path.endswith("MyApplication2"):
                raise ValueError("codelinter只能在MyApplication2项目中使用")
            
            logger.info(f"开始codelinter检查: {project_path}")
            
            # 执行codelinter检查
            result = self.harmonyos_compiler.run_codelinter_check()
            
            # 格式化结果
            formatted_result = {
                "request_id": f"codelinter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "project_path": project_path,
                "success": result["success"],
                "issues_found": result.get("issues", []),
                "total_issues": result.get("total_issues", 0),
                "error_count": result.get("error_count", 0),
                "warning_count": result.get("warning_count", 0),
                "raw_output": result.get("raw_output", ""),
                "stderr": result.get("stderr", ""),
                "agent_id": self.agent_id,
                "checked_at": datetime.now().isoformat(),
                "tool": "codelinter"
            }
            
            logger.info(f"codelinter检查完成: {formatted_result['total_issues']} 个问题")
            
            return {"formatted_review_data": formatted_result}
            
        except Exception as e:
            logger.error(f"codelinter检查失败: {str(e)}")
            raise
    
    async def _harmonyos_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """鸿蒙静态代码检查 - 工作流专用方法"""
        try:
            # 从工作流上下文获取参数
            files_to_check = params.get("files_to_check", [])
            project_path = params.get("project_path", "MyApplication2")
            current_phase = params.get("current_phase", "static_check")
            
            logger.info(f"🔍 开始鸿蒙静态检查")
            logger.info(f"   - 检查文件数: {len(files_to_check)}")
            logger.info(f"   - 项目路径: {project_path}")
            logger.info(f"   - 当前阶段: {current_phase}")
            
            # 显示要检查的文件
            for i, file_info in enumerate(files_to_check[:3]):
                logger.info(f"   - 文件{i+1}: {file_info.get('path', 'N/A')}")
            
            logger.info(f"📋 执行codelinter检查命令...")
            # 执行codelinter检查
            result = self.harmonyos_compiler.run_codelinter_check()
            
            logger.info(f"📋 codelinter检查结果: success={result.get('success')}")
            logger.info(f"   - 原始输出长度: {len(result.get('raw_output', ''))}")
            logger.info(f"   - 问题数量: {len(result.get('issues', []))}")
            
            # 格式化错误信息供工作流使用
            errors = []
            warnings = []
            if result.get("issues"):  # 只要有issues就处理，不管success状态
                for issue in result["issues"]:
                    if isinstance(issue, dict):
                        # 规范化严重性级别
                        severity = issue.get("severity", "")
                        if not severity:
                            # 尝试从消息中判断严重性
                            message = issue.get("message", "").lower()
                            if any(word in message for word in ["error", "fatal", "failed", "critical", "致命", "错误"]):
                                severity = "error"
                            else:
                                severity = "warning"
                        else:
                            severity = severity.lower()
                        
                        error = {
                            "file": issue.get("file", "unknown"),
                            "line": issue.get("line", 1),
                            "column": issue.get("column", 1),
                            "message": issue.get("message", "Unknown error"),
                            "severity": severity,
                            "rule": issue.get("rule", "unknown"),
                            "error_type": "lint"
                        }
                        
                        # 严格区分错误和警告
                        if severity == "error":
                            errors.append(error)
                        else:
                            warnings.append(error)
            
            # 工作流返回格式
            workflow_result = {
                "success": result["success"],
                "errors": errors,  # 只包含真正的错误
                "warnings": warnings,  # 只包含警告
                "all_issues": errors + warnings,  # 所有问题
                "total_errors": len(errors),  # 只统计真正的错误
                "total_warnings": len(warnings),
                "files_checked": len(files_to_check),
                "check_type": "codelinter",
                "project_path": project_path,
                "raw_output": result.get("raw_output", ""),
                "checked_at": datetime.now().isoformat()
            }
            
            logger.info(f"静态检查完成: {len(errors)} 个错误, {len(warnings)} 个警告")
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"鸿蒙静态检查失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "errors": [],
                "total_errors": 0,
                "total_warnings": 0,
                "files_checked": 0,
                "check_type": "codelinter"
            } 