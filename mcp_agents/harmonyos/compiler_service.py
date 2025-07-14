#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Compiler Service
鸿蒙编译服务 - 封装hvigorw和codelinter调用
"""

import os
import subprocess
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CompilerError:
    """编译错误信息"""
    file: str
    line: Optional[int]
    column: Optional[int]
    message: str
    type: str  # error, warning, info
    category: str  # syntax, type, import, etc.

@dataclass
class LinterIssue:
    """代码检查问题"""
    file: str
    line: Optional[int] 
    column: Optional[int]
    message: str
    rule: str
    severity: str  # error, warning, info

class HarmonyOSCompilerService:
    """
    鸿蒙编译服务
    封装hvigorw编译和codelinter静态检查
    """
    
    def __init__(self, project_root: str = "/home/deepsearch/deep-searcher/MyApplication2"):
        self.project_root = project_root
        self.hvigor_command = "hvigorw --mode project -p product=default assembleApp --analyze=normal --parallel --incremental --daemon"
        self.codelinter_command = "codelinter"
        
        # 错误模式匹配
        self.error_patterns = {
            "typescript_error": r"error TS(\d+): (.+)",
            "arkts_error": r"ArkTS:(\d+):(\d+): (.+)",
            "build_error": r"BUILD FAILED",
            "import_error": r"Cannot find module '([^']+)'",
            "syntax_error": r"SyntaxError: (.+)",
        }
        
        self.warning_patterns = {
            "typescript_warning": r"warning TS(\d+): (.+)",
            "deprecation": r"deprecated: (.+)",
        }
    
    def run_codelinter_check(self) -> Dict[str, Any]:
        """
        运行codelinter静态检查
        
        Returns:
            检查结果字典
        """
        try:
            logger.info("开始运行codelinter检查...")
            
            result = subprocess.run(
                [self.codelinter_command],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120  # 2分钟超时
            )
            
            # 解析codelinter输出
            issues = self._parse_codelinter_output(result.stdout)
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "issues": [issue.__dict__ for issue in issues],
                "total_issues": len(issues),
                "error_count": len([i for i in issues if i.severity == "error"]),
                "warning_count": len([i for i in issues if i.severity == "warning"]),
                "raw_output": result.stdout,
                "stderr": result.stderr,
                "execution_time": "N/A"  # codelinter不提供时间信息
            }
            
        except subprocess.TimeoutExpired:
            logger.error("codelinter检查超时")
            return {
                "success": False,
                "error": "codelinter检查超时",
                "issues": [],
                "total_issues": 0
            }
        except Exception as e:
            logger.error(f"codelinter检查失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "issues": [],
                "total_issues": 0
            }
    
    def run_hvigor_compile(self) -> Dict[str, Any]:
        """
        运行hvigor编译
        
        Returns:
            编译结果字典
        """
        try:
            logger.info("开始运行hvigor编译...")
            
            # 分割命令
            cmd_parts = self.hvigor_command.split()
            
            result = subprocess.run(
                cmd_parts,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 解析编译输出
            errors = self._parse_compiler_output(result.stdout + result.stderr)
            
            # 判断编译是否成功
            compile_success = result.returncode == 0 and "BUILD SUCCESSFUL" in result.stdout
            
            return {
                "success": compile_success,
                "returncode": result.returncode,
                "status": "success" if compile_success else "failed",
                "errors": [error.__dict__ for error in errors],
                "total_errors": len([e for e in errors if e.type == "error"]),
                "total_warnings": len([e for e in errors if e.type == "warning"]),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "build_successful": "BUILD SUCCESSFUL" in result.stdout,
                "build_failed": "BUILD FAILED" in result.stdout
            }
            
        except subprocess.TimeoutExpired:
            logger.error("hvigor编译超时")
            return {
                "success": False,
                "status": "failed",
                "error": "编译超时",
                "errors": [],
                "total_errors": 1
            }
        except Exception as e:
            logger.error(f"hvigor编译失败: {e}")
            return {
                "success": False,
                "status": "failed", 
                "error": str(e),
                "errors": [],
                "total_errors": 1
            }
    
    def _parse_codelinter_output(self, output: str) -> List[LinterIssue]:
        """解析codelinter输出"""
        issues = []
        
        if not output.strip():
            return issues
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # codelinter输出格式通常为: file:line:column: severity: message [rule]
            # 例如: src/main/ets/pages/Index.ets:10:5: error: Expected ';' [semicolon]
            
            # 尝试解析标准格式
            match = re.match(r'^(.+?):(\d+):(\d+):\s*(\w+):\s*(.+?)(?:\s*\[(.+?)\])?$', line)
            if match:
                file_path, line_num, col_num, severity, message, rule = match.groups()
                
                issues.append(LinterIssue(
                    file=file_path,
                    line=int(line_num) if line_num else None,
                    column=int(col_num) if col_num else None,
                    message=message.strip(),
                    rule=rule or "unknown",
                    severity=severity.lower()
                ))
                continue
            
            # 尝试解析简化格式: file:line: severity: message
            match = re.match(r'^(.+?):(\d+):\s*(\w+):\s*(.+)$', line)
            if match:
                file_path, line_num, severity, message = match.groups()
                
                issues.append(LinterIssue(
                    file=file_path,
                    line=int(line_num) if line_num else None,
                    column=None,
                    message=message.strip(),
                    rule="unknown",
                    severity=severity.lower()
                ))
                continue
            
            # 如果包含错误关键词，作为通用错误处理
            if any(keyword in line.lower() for keyword in ['error', 'warning', 'fail']):
                issues.append(LinterIssue(
                    file="unknown",
                    line=None,
                    column=None,
                    message=line,
                    rule="parse_error",
                    severity="error" if "error" in line.lower() else "warning"
                ))
        
        logger.info(f"解析codelinter输出: {len(issues)} 个问题")
        return issues
    
    def _parse_compiler_output(self, output: str) -> List[CompilerError]:
        """解析编译器输出"""
        errors = []
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            error = self._parse_error_line(line)
            if error:
                errors.append(error)
        
        logger.info(f"解析编译输出: {len(errors)} 个错误/警告")
        return errors
    
    def _parse_error_line(self, line: str) -> Optional[CompilerError]:
        """解析单行错误信息"""
        
        # TypeScript错误
        match = re.search(self.error_patterns["typescript_error"], line)
        if match:
            code, message = match.groups()
            return CompilerError(
                file=self._extract_file_from_line(line),
                line=self._extract_line_number(line),
                column=self._extract_column_number(line),
                message=message,
                type="error",
                category="typescript"
            )
        
        # ArkTS错误
        match = re.search(self.error_patterns["arkts_error"], line)
        if match:
            line_num, col_num, message = match.groups()
            return CompilerError(
                file=self._extract_file_from_line(line),
                line=int(line_num) if line_num.isdigit() else None,
                column=int(col_num) if col_num.isdigit() else None,
                message=message,
                type="error",
                category="arkts"
            )
        
        # 导入错误
        match = re.search(self.error_patterns["import_error"], line)
        if match:
            module = match.group(1)
            return CompilerError(
                file=self._extract_file_from_line(line),
                line=self._extract_line_number(line),
                column=None,
                message=f"Cannot find module '{module}'",
                type="error",
                category="import"
            )
        
        # 构建失败
        if "BUILD FAILED" in line:
            return CompilerError(
                file="build",
                line=None,
                column=None,
                message="Build failed",
                type="error",
                category="build"
            )
        
        # TypeScript警告
        match = re.search(self.warning_patterns["typescript_warning"], line)
        if match:
            code, message = match.groups()
            return CompilerError(
                file=self._extract_file_from_line(line),
                line=self._extract_line_number(line),
                column=self._extract_column_number(line),
                message=message,
                type="warning",
                category="typescript"
            )
        
        # 通用错误检测
        if any(keyword in line.lower() for keyword in ['error:', 'failed', 'exception']):
            return CompilerError(
                file=self._extract_file_from_line(line) or "unknown",
                line=self._extract_line_number(line),
                column=None,
                message=line,
                type="error",
                category="general"
            )
        
        return None
    
    def _extract_file_from_line(self, line: str) -> Optional[str]:
        """从错误行中提取文件路径"""
        # 查找常见的文件路径模式
        patterns = [
            r'([a-zA-Z0-9_/\\.-]+\.ets)',
            r'([a-zA-Z0-9_/\\.-]+\.ts)',
            r'([a-zA-Z0-9_/\\.-]+\.js)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_line_number(self, line: str) -> Optional[int]:
        """从错误行中提取行号"""
        # 查找 :数字: 模式
        match = re.search(r':(\d+):', line)
        if match:
            return int(match.group(1))
        
        # 查找 (数字, 或 (数字) 模式
        match = re.search(r'\((\d+)[,)]', line)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_column_number(self, line: str) -> Optional[int]:
        """从错误行中提取列号"""
        # 查找 :数字:数字: 模式
        match = re.search(r':(\d+):(\d+):', line)
        if match:
            return int(match.group(2))
        
        # 查找 (数字,数字) 模式
        match = re.search(r'\((\d+),(\d+)\)', line)
        if match:
            return int(match.group(2))
        
        return None
    
    def generate_fix_suggestions(self, errors: List[CompilerError], issues: List[LinterIssue]) -> List[str]:
        """根据错误和问题生成修复建议"""
        suggestions = []
        
        # 分析编译错误
        for error in errors:
            if error.category == "import":
                suggestions.append(f"检查模块导入: {error.message}")
            elif error.category == "typescript":
                suggestions.append(f"修复TypeScript类型错误: {error.message}")
            elif error.category == "arkts":
                suggestions.append(f"修复ArkTS语法错误: {error.message}")
            elif error.category == "syntax":
                suggestions.append(f"修复语法错误: {error.message}")
        
        # 分析Linter问题
        for issue in issues:
            if issue.severity == "error":
                suggestions.append(f"修复代码规范错误 [{issue.rule}]: {issue.message}")
        
        # 去重并限制数量
        suggestions = list(set(suggestions))[:10]
        
        return suggestions
    
    def check_project_health(self) -> Dict[str, Any]:
        """检查项目健康状况"""
        try:
            # 检查关键文件是否存在
            key_files = [
                "entry/src/main/module.json5",
                "entry/src/main/ets/pages/Index.ets", 
                "entry/src/main/ets/entryability/EntryAbility.ets",
                "build-profile.json5",
                "oh-package.json5"
            ]
            
            missing_files = []
            for file in key_files:
                full_path = os.path.join(self.project_root, file)
                if not os.path.exists(full_path):
                    missing_files.append(file)
            
            # 检查目录结构
            required_dirs = [
                "entry/src/main/ets/pages",
                "entry/src/main/ets/entryability",
                "entry/src/main/resources"
            ]
            
            missing_dirs = []
            for dir_path in required_dirs:
                full_path = os.path.join(self.project_root, dir_path)
                if not os.path.exists(full_path):
                    missing_dirs.append(dir_path)
            
            health_score = 100 - len(missing_files) * 10 - len(missing_dirs) * 5
            health_status = "excellent" if health_score >= 90 else "good" if health_score >= 70 else "poor"
            
            return {
                "health_score": max(0, health_score),
                "health_status": health_status,
                "missing_files": missing_files,
                "missing_directories": missing_dirs,
                "project_root_exists": os.path.exists(self.project_root),
                "codelinter_available": self._check_codelinter_available(),
                "hvigor_available": self._check_hvigor_available()
            }
            
        except Exception as e:
            logger.error(f"项目健康检查失败: {e}")
            return {
                "health_score": 0,
                "health_status": "error",
                "error": str(e)
            }
    
    def _check_codelinter_available(self) -> bool:
        """检查codelinter是否可用"""
        try:
            result = subprocess.run(
                [self.codelinter_command, "--version"],
                cwd=self.project_root,
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_hvigor_available(self) -> bool:
        """检查hvigor是否可用"""
        try:
            result = subprocess.run(
                ["hvigorw", "--version"],
                cwd=self.project_root,
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False