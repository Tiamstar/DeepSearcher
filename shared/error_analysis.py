#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误分析和修复策略系统
提供智能的错误分析和修复建议
"""

import logging
import re
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """错误类型枚举"""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    RESOURCE_ERROR = "resource_error"
    COMPILATION_ERROR = "compilation_error"
    TYPE_ERROR = "type_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"      # 阻止编译的严重错误
    HIGH = "high"             # 影响功能的高级错误
    MEDIUM = "medium"         # 影响代码质量的中级错误
    LOW = "low"              # 轻微的代码风格问题

class ErrorAnalyzer:
    """错误分析器"""
    
    def __init__(self):
        self.error_patterns = {
            ErrorType.SYNTAX_ERROR: [
                r"SyntaxError",
                r"Unexpected token",
                r"Missing semicolon",
                r"Invalid syntax"
            ],
            ErrorType.IMPORT_ERROR: [
                r"Cannot resolve symbol",
                r"Module not found",
                r"Import.*not found",
                r"Cannot import"
            ],
            ErrorType.RESOURCE_ERROR: [
                r"Resource Pack Error",
                r"Failed to parse.*JSON",
                r"string\.json",
                r"base/element"
            ],
            ErrorType.COMPILATION_ERROR: [
                r"CompileResource",
                r"Tools execution failed",
                r"Build failed",
                r"hvigor ERROR"
            ],
            ErrorType.TYPE_ERROR: [
                r"Type.*not assignable",
                r"Property.*does not exist",
                r"Cannot find name"
            ]
        }
        
        self.severity_patterns = {
            ErrorSeverity.CRITICAL: [
                r"hvigor ERROR",
                r"Build failed",
                r"Tools execution failed"
            ],
            ErrorSeverity.HIGH: [
                r"SyntaxError",
                r"Cannot resolve symbol",
                r"Module not found"
            ],
            ErrorSeverity.MEDIUM: [
                r"Resource Pack Error",
                r"Type.*not assignable"
            ],
            ErrorSeverity.LOW: [
                r"Warning",
                r"Unused variable"
            ]
        }
    
    def analyze_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个错误"""
        message = error.get("message", "")
        file_path = error.get("file_path", "")
        
        # 识别错误类型
        error_type = self._classify_error(message)
        
        # 评估严重程度
        severity = self._assess_severity(message)
        
        # 确定修复策略
        fix_strategy = self._determine_fix_strategy(error_type, message, file_path)
        
        return {
            "original_error": error,
            "error_type": error_type,
            "severity": severity,
            "fix_strategy": fix_strategy,
            "priority": self._calculate_priority(error_type, severity),
            "can_auto_fix": fix_strategy.get("can_auto_fix", False),
            "fix_description": fix_strategy.get("description", "")
        }
    
    def _classify_error(self, message: str) -> ErrorType:
        """根据错误消息分类错误类型"""
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return error_type
        return ErrorType.UNKNOWN_ERROR
    
    def _assess_severity(self, message: str) -> ErrorSeverity:
        """评估错误严重程度"""
        for severity, patterns in self.severity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return severity
        return ErrorSeverity.MEDIUM
    
    def _determine_fix_strategy(self, error_type: ErrorType, message: str, file_path: str) -> Dict[str, Any]:
        """确定修复策略"""
        strategies = {
            ErrorType.SYNTAX_ERROR: {
                "can_auto_fix": True,
                "description": "修复语法错误",
                "approach": "syntax_fix",
                "priority": "high"
            },
            ErrorType.IMPORT_ERROR: {
                "can_auto_fix": True,
                "description": "修复导入错误",
                "approach": "import_fix",
                "priority": "high"
            },
            ErrorType.RESOURCE_ERROR: {
                "can_auto_fix": True,
                "description": "修复资源文件错误",
                "approach": "resource_fix",
                "priority": "medium"
            },
            ErrorType.COMPILATION_ERROR: {
                "can_auto_fix": False,
                "description": "需要分析编译错误根本原因",
                "approach": "compilation_analysis",
                "priority": "critical"
            },
            ErrorType.TYPE_ERROR: {
                "can_auto_fix": True,
                "description": "修复类型错误",
                "approach": "type_fix",
                "priority": "medium"
            },
            ErrorType.UNKNOWN_ERROR: {
                "can_auto_fix": False,
                "description": "需要人工分析",
                "approach": "manual_review",
                "priority": "low"
            }
        }
        
        return strategies.get(error_type, strategies[ErrorType.UNKNOWN_ERROR])
    
    def _calculate_priority(self, error_type: ErrorType, severity: ErrorSeverity) -> int:
        """计算错误优先级（数字越大优先级越高）"""
        type_weights = {
            ErrorType.COMPILATION_ERROR: 100,
            ErrorType.SYNTAX_ERROR: 80,
            ErrorType.IMPORT_ERROR: 70,
            ErrorType.TYPE_ERROR: 60,
            ErrorType.RESOURCE_ERROR: 50,
            ErrorType.UNKNOWN_ERROR: 30
        }
        
        severity_weights = {
            ErrorSeverity.CRITICAL: 40,
            ErrorSeverity.HIGH: 30,
            ErrorSeverity.MEDIUM: 20,
            ErrorSeverity.LOW: 10
        }
        
        return type_weights.get(error_type, 30) + severity_weights.get(severity, 20)

class ErrorFixingStrategy:
    """错误修复策略"""
    
    def __init__(self):
        self.analyzer = ErrorAnalyzer()
    
    def analyze_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析错误列表并生成修复计划"""
        analyzed_errors = []
        
        for error in errors:
            analyzed_error = self.analyzer.analyze_error(error)
            analyzed_errors.append(analyzed_error)
        
        # 按优先级排序
        analyzed_errors.sort(key=lambda x: x["priority"], reverse=True)
        
        # 生成修复计划
        fix_plan = self._generate_fix_plan(analyzed_errors)
        
        return {
            "analyzed_errors": analyzed_errors,
            "fix_plan": fix_plan,
            "summary": self._generate_summary(analyzed_errors)
        }
    
    def _generate_fix_plan(self, analyzed_errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成修复计划"""
        fix_plan = []
        
        # 按文件分组
        files_to_fix = {}
        for error in analyzed_errors:
            if error["can_auto_fix"]:
                file_path = error["original_error"].get("file_path", "unknown")
                if file_path not in files_to_fix:
                    files_to_fix[file_path] = []
                files_to_fix[file_path].append(error)
        
        # 为每个文件创建修复任务
        for file_path, file_errors in files_to_fix.items():
            fix_task = {
                "file_path": file_path,
                "errors": file_errors,
                "priority": max(error["priority"] for error in file_errors),
                "fix_approaches": list(set(error["fix_strategy"]["approach"] for error in file_errors))
            }
            fix_plan.append(fix_task)
        
        # 按优先级排序
        fix_plan.sort(key=lambda x: x["priority"], reverse=True)
        
        return fix_plan
    
    def _generate_summary(self, analyzed_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成错误摘要"""
        total_errors = len(analyzed_errors)
        auto_fixable = sum(1 for error in analyzed_errors if error["can_auto_fix"])
        
        error_types = {}
        severity_counts = {}
        
        for error in analyzed_errors:
            error_type = error["error_type"].value
            severity = error["severity"].value
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_errors": total_errors,
            "auto_fixable": auto_fixable,
            "manual_review_needed": total_errors - auto_fixable,
            "error_types": error_types,
            "severity_distribution": severity_counts,
            "recommendation": self._generate_recommendation(analyzed_errors)
        }
    
    def _generate_recommendation(self, analyzed_errors: List[Dict[str, Any]]) -> str:
        """生成修复建议"""
        if not analyzed_errors:
            return "无错误需要修复"
        
        critical_errors = [e for e in analyzed_errors if e["severity"] == ErrorSeverity.CRITICAL]
        high_errors = [e for e in analyzed_errors if e["severity"] == ErrorSeverity.HIGH]
        
        if critical_errors:
            return f"发现 {len(critical_errors)} 个严重错误，需要立即修复以确保编译通过"
        elif high_errors:
            return f"发现 {len(high_errors)} 个高级错误，建议优先修复以提高代码质量"
        else:
            return "主要是中低级错误，可以逐步修复"

class WorkflowErrorFilter:
    """工作流错误过滤器 - 专门用于改进代码修复工作流"""
    
    def __init__(self):
        self.success_patterns = [
            r'BUILD SUCCESSFUL',
            r'COMPILE RESULT:PASS',
            r'compilation passed',
            r'success'
        ]
        
        self.warning_patterns = [
            r'warning',
            r'warn',
            r'deprecat',
            r'注意',
            r'提示'
        ]
        
        self.stats_patterns = [
            r'-?Defects:\s*\d+;\s*Errors:\s*\d+',
            r'COMPILE RESULT:(?:FAIL|PASS)\s*\{ERROR:\d+',
            r'Total.*issues:'
        ]
    
    def extract_real_error_count(self, output: str) -> tuple[int, int]:
        """从输出中提取真实的错误和警告数量"""
        error_count = 0
        warning_count = 0
        
        # hvigor编译统计
        hvigor_match = re.search(r'COMPILE RESULT:(?:FAIL|PASS)\s*\{ERROR:(\d+)\s*WARN:(\d+)\}', output)
        if hvigor_match:
            error_count = int(hvigor_match.group(1))
            warning_count = int(hvigor_match.group(2))
            logger.info(f"提取hvigor统计: {error_count}错误, {warning_count}警告")
            return error_count, warning_count
        
        # codelinter统计
        codelinter_match = re.search(r'-?Defects:\s*\d+;\s*Errors:\s*(\d+);\s*Warns:\s*(\d+)', output)
        if codelinter_match:
            error_count = int(codelinter_match.group(1))
            warning_count = int(codelinter_match.group(2))
            logger.info(f"提取codelinter统计: {error_count}错误, {warning_count}警告")
            return error_count, warning_count
        
        return 0, 0
    
    def is_real_error(self, error_dict: Dict[str, Any]) -> bool:
        """判断是否为真正的错误"""
        message = error_dict.get('message', '')
        severity = error_dict.get('severity', '').lower()
        
        # 过滤成功状态
        for pattern in self.success_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False
        
        # 过滤统计摘要
        for pattern in self.stats_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False
        
        # 严格检查是否为真正的错误级别
        if severity != 'error':
            return False
        
        # 检查是否为伪装成错误的警告
        for pattern in self.warning_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False
        
        return True
    
    def infer_target_file(self, error_dict: Dict[str, Any]) -> str:
        """智能推断目标文件路径"""
        message = error_dict.get('message', '')
        file_path = error_dict.get('file_path', '')
        
        # 如果已有合适的文件路径
        if file_path and file_path.startswith('MyApplication2/'):
            return file_path
        
        # 根据错误类型推断
        if any(keyword in message for keyword in ['Resource Pack Error', 'string.json', 'base/element']):
            return 'MyApplication2/entry/src/main/resources/base/element/string.json'
        elif any(keyword in message for keyword in ['CompileResource', 'ArkTS', '@Entry', '@Component']):
            return 'MyApplication2/entry/src/main/ets/pages/Index.ets'
        elif any(keyword in message for keyword in ['module.json']):
            return 'MyApplication2/entry/src/main/module.json5'
        else:
            # 默认Index.ets
            return 'MyApplication2/entry/src/main/ets/pages/Index.ets'
    
    def filter_errors_for_workflow(self, errors: List[Dict[str, Any]], raw_output: str = "") -> List[Dict[str, Any]]:
        """为工作流过滤真正需要修复的错误"""
        if not errors:
            return []
        
        # 获取真实错误数量
        actual_error_count, _ = self.extract_real_error_count(raw_output)
        
        # 如果统计显示没有错误，返回空列表
        if actual_error_count == 0:
            logger.info("统计显示没有真实错误，跳过修复")
            return []
        
        # 过滤真正的错误
        real_errors = []
        for error in errors:
            if self.is_real_error(error):
                # 修正文件路径
                error['file_path'] = self.infer_target_file(error)
                real_errors.append(error)
        
        # 如果过滤后数量超过统计数量，进行裁剪
        if len(real_errors) > actual_error_count:
            logger.warning(f"过滤后错误数({len(real_errors)})超过统计数({actual_error_count})，裁剪到{actual_error_count}")
            real_errors = real_errors[:actual_error_count]
        
        logger.info(f"工作流错误过滤完成: {len(real_errors)}个真实错误")
        return real_errors

# 全局实例
error_fixing_strategy = ErrorFixingStrategy()
workflow_error_filter = WorkflowErrorFilter()