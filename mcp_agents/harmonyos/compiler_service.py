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
    type: str  # error, warning
    category: str = "unknown"  # syntax, type, import, etc.
    raw_message: Optional[str] = None  # 原始错误消息

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
            
            # 统计真正的错误数量（不包括警告）
            error_count = len([e for e in errors if e.type.lower() == "error"])
            warning_count = len([e for e in errors if e.type.lower() == "warning"])
            
            # 检查编译输出中的统计信息
            import re
            error_count_match = re.search(r'COMPILE RESULT:(?:FAIL|PASS) \{ERROR:(\d+) WARN:(\d+)\}', result.stdout + result.stderr)
            if error_count_match:
                reported_error_count = int(error_count_match.group(1))
                reported_warning_count = int(error_count_match.group(2))
                logger.info(f"编译统计: {reported_error_count}个错误, {reported_warning_count}个警告")
                
                # 只在统计错误数为0时清空错误列表，不进行裁剪
                if reported_error_count == 0:
                    logger.info("编译统计显示没有错误，清空错误列表")
                    errors = [e for e in errors if e.type.lower() == "warning"]
                    error_count = 0
                elif reported_error_count != error_count:
                    logger.info(f"统计错误数({reported_error_count})与解析出的错误数({error_count})不一致，保持解析结果")
            
            return {
                "success": compile_success,
                "returncode": result.returncode,
                "status": "success" if compile_success else "failed",
                "errors": [error.__dict__ for error in errors],
                "total_errors": error_count,
                "total_warnings": warning_count,
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
        
        # 首先检查是否有统计摘要行，获取实际错误数量
        import re
        actual_error_count = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 解析统计摘要行
            if line.startswith('-Defects:') or re.match(r'^-?Defects:\s*\d+;\s*Errors:', line):
                logger.info(f"检测到统计摘要行: {line}")
                stats_match = re.search(r'-?Defects:\s*\d+;\s*Errors:\s*(\d+);\s*Warns:', line)
                if stats_match:
                    actual_error_count = int(stats_match.group(1))
                    logger.info(f"统计摘要显示实际错误数量: {actual_error_count}")
        
        # 如果统计摘要明确显示没有错误，则直接返回空列表
        if actual_error_count is not None and actual_error_count == 0:
            logger.info("统计摘要显示没有实际错误，返回空列表")
            return []
        
        # 处理每一行
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 跳过统计摘要行
            if line.startswith('-Defects:') or re.match(r'^-?Defects:\s*\d+;\s*Errors:', line):
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
            
            # 尝试解析HarmonyOS特有格式: /path/file(line) severity [rule]
            match = re.match(r'^(.+?)\((\d+)\)\s+(\w+)\s+(.+?)(?:\s+\[(.+?)\])?$', line)
            if match:
                file_path, line_num, severity, message, rule = match.groups() if len(match.groups()) == 5 else (*match.groups(), "unknown")
                
                issues.append(LinterIssue(
                    file=file_path,
                    line=int(line_num) if line_num else None,
                    column=None,
                    message=message.strip(),
                    rule=rule or "unknown",
                    severity=severity.lower()
                ))
                continue
            
            # 如果包含错误关键词，作为通用错误处理，但跳过摘要行
            if any(keyword in line.lower() for keyword in ['error', 'warning', 'fail']) and not any(keyword in line.lower() for keyword in ['defects:', 'errors:', 'warns:', 'suggestions:']):
                issues.append(LinterIssue(
                    file="unknown",
                    line=None,
                    column=None,
                    message=line,
                    rule="parse_error",
                    severity="error" if "error" in line.lower() else "warning"
                ))
        
        # 只返回错误类型的问题，忽略警告
        if actual_error_count is not None:
            # 只保留严重性为error的问题
            error_issues = [issue for issue in issues if issue.severity == "error"]
            logger.info(f"过滤后的错误数量: {len(error_issues)}，统计中的错误数量: {actual_error_count}")
            
            # 完全使用实际解析出的错误，不进行任何裁剪
            # 移除了之前的裁剪逻辑，确保所有实际错误都被保留
            issues = error_issues
        else:
            # 如果没有统计信息，也只保留错误类型
            issues = [issue for issue in issues if issue.severity == "error"]
        
        logger.info(f"解析codelinter输出: {len(issues)} 个问题")
        return issues
    
    def _parse_compiler_output(self, output: str) -> List[CompilerError]:
        """解析编译器输出 - 简化版本，只判断是否有错误并提取错误信息"""
        errors = []
        
        if not output.strip():
            return errors
        
        # 清理ANSI颜色代码
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        clean_output = ansi_escape.sub('', output)
        
        # 检查是否有编译失败和错误统计
        has_compile_failure = False
        error_count = 0
        
        # 查找编译统计信息
        stats_match = re.search(r'COMPILE RESULT:(?:FAIL|PASS) \{ERROR:(\d+) WARN:(\d+)\}', clean_output)
        if stats_match:
            error_count = int(stats_match.group(1))
            warning_count = int(stats_match.group(2))
            logger.info(f"编译统计: {error_count}个错误, {warning_count}个警告")
            
            # 如果有错误，则表示编译失败
            if error_count > 0:
                has_compile_failure = True
        
        # 检查是否有BUILD FAILED标记
        if 'BUILD FAILED' in clean_output or 'COMPILE RESULT:FAIL' in clean_output:
            has_compile_failure = True
        
        # 如果没有编译失败，返回空错误列表
        if not has_compile_failure:
            logger.info("编译成功，没有错误")
            return []
        
        # 如果有编译失败，创建一个包含完整错误信息的错误对象
        logger.info(f"编译失败，检测到{error_count}个错误")
        
        # 提取错误相关的输出行
        error_lines = []
        for line in clean_output.split('\n'):
            line = line.strip()
            if any(keyword in line for keyword in ['ERROR:', 'Error Message:', 'ArkTS Compiler Error', 'COMPILE RESULT:FAIL']):
                error_lines.append(line)
        
        # 创建一个包含所有错误信息的错误对象
        if error_lines or has_compile_failure:
            full_error_message = '\n'.join(error_lines) if error_lines else "编译失败但无详细错误信息"
            
            errors.append(CompilerError(
                file="MyApplication2/entry/src/main/ets/pages/Index.ets",  # 默认文件
                line=None,
                column=None,
                message=full_error_message,
                type="error",
                category="compilation_failure",
                raw_message=clean_output  # 保存完整的原始输出
            ))
        
        return errors
    
    def _parse_error_line(self, line: str) -> Optional[CompilerError]:
        """解析单行错误日志"""
        try:
            line = line.strip()
            
            # 检查行是否为空
            if not line:
                return None
                
            # 忽略总结信息行
            if any(pattern in line for pattern in [
                "BUILD FAILED in", 
                "COMPILE RESULT:", 
                "> hvigor ERROR: BUILD FAILED",
                "> Task :entry:default@CompileArkTS"
            ]):
                logger.debug(f"忽略总结信息行: {line}")
                return None
            
            # 先判断是错误还是警告
            severity = "error"  # 默认严重性为error
            
            if "WARN:" in line or "warning:" in line or "WARN " in line:
                severity = "warning"
            elif "ERROR:" in line or "error:" in line or "ERROR " in line:
                severity = "error"
            else:
                # 对于不明确的行，根据关键词判断
                if any(keyword in line.lower() for keyword in ["warn", "deprecation", "注意", "提示"]):
                    severity = "warning"
                elif any(keyword in line.lower() for keyword in ["error", "fail", "failed", "错误", "失败"]):
                    severity = "error"
            
            # ArkTS错误格式: 1 ERROR: 10505001 ArkTS Compiler Error
            error_match = re.search(r'(\d+)\s+(ERROR|WARN):\s+([\d]+)\s+(.*)', line)
            if error_match:
                error_id, err_type, error_code, message = error_match.groups()
                # 根据匹配到的类型确定严重性
                actual_severity = "error" if err_type == "ERROR" else "warning"
                return CompilerError(
                    type=actual_severity,
                    file="unknown",
                    line=None,
                    column=None,
                    message=message.strip(),
                    category="compiler",
                    raw_message=line
                )
            
            # 文件特定错误格式: Error Message: xxx At File: /path/to/file.ets:10:5
            file_match = re.search(r'Error Message:\s+(.*?)(?:\s+At File:\s+([^:]+):(\d+):(\d+))?', line)
            if file_match:
                message = file_match.group(1)
                file_path = file_match.group(2) if file_match.group(2) else "unknown"
                line_num = int(file_match.group(3)) if file_match.group(3) else None
                column = int(file_match.group(4)) if file_match.group(4) else None
                
                return CompilerError(
                    type=severity,
                    file=file_path,
                    line=line_num,
                    column=column,
                    message=message,
                    category="syntax",
                    raw_message=line
                )
            
            # 警告特定格式: 1 WARN: ArkTS:WARN File: /path/to/file.ets:10:5
            warn_match = re.search(r'(\d+)\s+WARN:\s+ArkTS:WARN\s+File:\s+([^:]+):(\d+):(\d+)', line)
            if warn_match:
                warn_id, file_path, line_num, column = warn_match.groups()
                # 提取警告消息（通常在下一行或者同一行后面）
                message = line.split(f"{file_path}:{line_num}:{column}")[-1].strip()
                if not message:
                    message = "ArkTS Warning"
                return CompilerError(
                    type="warning",
                    file=file_path,
                    line=int(line_num) if line_num else None,
                    column=int(column) if column else None,
                    message=message,
                    category="warning",
                    raw_message=line
                )
            
            # 匹配一般错误
            general_error_match = re.search(r'(ERROR|WARN|error|warning)(?:\s+|:)(.+)', line)
            if general_error_match:
                err_type, message = general_error_match.groups()
                return CompilerError(
                    type="error" if "error" in err_type.lower() else "warning",
                    file="unknown",
                    line=None,
                    column=None,
                    message=message.strip(),
                    category="general",
                    raw_message=line
                )
            
            # 如果包含错误相关字符串，视为通用错误
            if any(keyword in line.lower() for keyword in ["error", "fail", "failed", "错误", "失败"]):
                return CompilerError(
                    type="error",
                    file="unknown", 
                    line=None,
                    column=None,
                    message=line,
                    category="unknown",
                    raw_message=line
                )
            
            # 如果包含警告相关字符串，视为通用警告
            if any(keyword in line.lower() for keyword in ["warn", "warning", "deprecation", "注意", "提示"]):
                return CompilerError(
                    type="warning",
                    file="unknown",
                    line=None,
                    column=None,
                    message=line,
                    category="unknown",
                    raw_message=line
                )
                
            # 不是错误或警告行
            return None
            
        except Exception as e:
            logger.error(f"解析错误行失败: {line} - {e}")
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
        
        # 分析编译错误（兼容对象和字典格式）
        for error in errors:
            # 处理CompilerError对象
            if hasattr(error, 'category'):
                category = error.category
                message = error.message
            # 处理字典格式
            elif isinstance(error, dict):
                category = error.get('category', 'unknown')
                message = error.get('message', str(error))
            else:
                # 其他格式，转换为字符串
                category = 'unknown'
                message = str(error)
            
            if category == "import":
                suggestions.append(f"检查模块导入: {message}")
            elif category == "typescript":
                suggestions.append(f"修复TypeScript类型错误: {message}")
            elif category == "arkts":
                suggestions.append(f"修复ArkTS语法错误: {message}")
            elif category == "syntax":
                suggestions.append(f"修复语法错误: {message}")
            else:
                suggestions.append(f"修复编译错误: {message}")
        
        # 分析Linter问题（兼容对象和字典格式）
        for issue in issues:
            # 处理LinterIssue对象
            if hasattr(issue, 'severity'):
                severity = issue.severity
                rule = getattr(issue, 'rule', 'unknown')
                message = issue.message
            # 处理字典格式
            elif isinstance(issue, dict):
                severity = issue.get('severity', 'unknown')
                rule = issue.get('rule', 'unknown')
                message = issue.get('message', str(issue))
            else:
                # 其他格式，转换为字符串
                severity = 'error'
                rule = 'unknown'
                message = str(issue)
            
            if severity == "error":
                suggestions.append(f"修复代码规范错误 [{rule}]: {message}")
        
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
    
    async def check_hvigorw_available(self) -> bool:
        """异步检查hvigorw是否可用"""
        return self._check_hvigor_available()
    
    async def compile_project(self, project_path: str = None, build_mode: str = "project", product: str = "default") -> Dict[str, Any]:
        """异步编译项目"""
        if project_path:
            original_root = self.project_root
            self.project_root = project_path
        
        try:
            result = self.run_hvigor_compile()
            return result
        finally:
            if project_path:
                self.project_root = original_root