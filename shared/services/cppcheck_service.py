#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cppcheck 静态分析服务

基于开源 Cppcheck 工具的 C/C++ 代码静态分析
"""

import asyncio
import json
import os
import tempfile
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from shared.interfaces import CodeReviewInterface, CodeReviewRequest, CodeReviewResult

logger = logging.getLogger(__name__)

class CppcheckService(CodeReviewInterface):
    """Cppcheck 静态分析服务"""
    
    def __init__(self, **kwargs):
        """
        初始化 Cppcheck 服务
        
        Args:
            **kwargs: 配置参数
        """
        self.cppcheck_path = kwargs.get('cppcheck_path', 'cppcheck')
        self.enable_cert_rules = kwargs.get('enable_cert_rules', True)
        self.enable_misra_rules = kwargs.get('enable_misra_rules', False)
        self.timeout = kwargs.get('timeout', 120)
        self.temp_dir = Path(tempfile.gettempdir()) / "cppcheck_service"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 支持的语言
        self.supported_languages = ['c', 'cpp', 'c++']
        
    def is_available(self) -> bool:
        """检查 Cppcheck 是否可用"""
        try:
            result = subprocess.run(
                [self.cppcheck_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Cppcheck 不可用: {e}")
            return False
    
    async def review_code(self, request: CodeReviewRequest) -> CodeReviewResult:
        """
        使用 Cppcheck 检查代码
        
        Args:
            request: 代码检查请求
            
        Returns:
            代码检查结果
        """
        start_time = time.time()
        request_id = f"cppcheck_{int(time.time())}_{hash(request.code) % 10000}"
        
        try:
            # 检查语言支持
            if request.language not in self.supported_languages:
                return self._create_unsupported_result(request_id, request, start_time)
            
            # 创建临时文件
            temp_file = await self._create_temp_file(request.code, request.language)
            
            # 执行检查
            check_result = await self._run_cppcheck(temp_file, request.review_type)
            
            # 解析结果
            result = self._parse_cppcheck_result(
                request_id, request, check_result, start_time
            )
            
            # 清理临时文件
            self._cleanup_temp_files([temp_file])
            
            return result
            
        except Exception as e:
            logger.error(f"Cppcheck 检查失败: {e}")
            return self._create_error_result(request_id, request, str(e), start_time)
    
    async def _create_temp_file(self, code: str, language: str) -> Path:
        """创建临时代码文件"""
        ext_map = {
            'c': '.c',
            'cpp': '.cpp',
            'c++': '.cpp'
        }
        ext = ext_map.get(language, '.cpp')
        
        temp_file = self.temp_dir / f"code_{int(time.time())}{ext}"
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return temp_file
    
    async def _run_cppcheck(self, code_file: Path, review_type: str) -> Dict[str, Any]:
        """运行 Cppcheck"""
        try:
            cmd = [
                self.cppcheck_path,
                str(code_file),
                "--xml",
                "--xml-version=2",
                "--enable=all"
            ]
            
            # 暂时不使用addon，因为可能不存在
            # 根据检查类型添加参数
            # if review_type == "security" and self.enable_cert_rules:
            #     cmd.extend(["--addon=cert"])
            # 
            # if self.enable_misra_rules:
            #     cmd.extend(["--addon=misra"])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            
            # Cppcheck 输出到 stderr
            output = stderr.decode() if stderr else stdout.decode()
            
            return {"xml_output": output, "return_code": process.returncode}
            
        except Exception as e:
            logger.error(f"运行 Cppcheck 失败: {e}")
            return {"error": str(e)}
    
    def _parse_cppcheck_result(self, 
                             request_id: str, 
                             request: CodeReviewRequest,
                             check_result: Dict[str, Any],
                             start_time: float) -> CodeReviewResult:
        """解析 Cppcheck 结果"""
        
        issues_found = []
        suggestions = []
        score = 100.0
        
        # 检查是否有错误
        if "error" in check_result:
            logger.error(f"Cppcheck执行错误: {check_result['error']}")
            return self._create_error_result(request_id, request, check_result['error'], start_time)
        
        # 解析XML输出
        xml_output = check_result.get("xml_output", "")
        logger.debug(f"Cppcheck XML输出: {xml_output}")
        
        if xml_output and "<?xml" in xml_output and "<results" in xml_output:
            try:
                root = ET.fromstring(xml_output)
                errors = root.findall(".//error")
                
                logger.debug(f"找到 {len(errors)} 个错误")
                
                for error in errors:
                    severity = error.get("severity", "style")
                    error_id = error.get("id", "unknown")
                    
                    # 过滤掉信息性消息，只保留真正的问题
                    if severity == "information" and error_id in ["missingIncludeSystem", "checkersReport"]:
                        continue
                    
                    # 获取位置信息
                    location = error.find("location")
                    line = int(location.get("line", 0)) if location is not None else 0
                    column = int(location.get("column", 0)) if location is not None else 0
                    
                    issue = {
                        "type": self._map_severity(severity),
                        "message": error.get("msg", ""),
                        "line": line,
                        "column": column,
                        "rule": error_id,
                        "severity": severity,
                        "cwe": error.get("cwe", "")
                    }
                    issues_found.append(issue)
                    
                # 计算评分
                error_count = sum(1 for issue in issues_found if issue["type"] == "error")
                warning_count = sum(1 for issue in issues_found if issue["type"] == "warning")
                score = max(0, 100 - error_count * 15 - warning_count * 5)
                
                # 生成建议
                suggestions = self._generate_suggestions(issues_found, request.language)
                
            except ET.ParseError as e:
                logger.error(f"解析Cppcheck XML失败: {e}")
                logger.debug(f"XML内容: {xml_output}")
                # 即使解析失败，也返回基本结果
        
        # 生成报告
        report = self._generate_report(issues_found, suggestions, request.language)
        
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            language=request.language,
            checker="Cppcheck",
            score=score,
            issues=issues_found,
            suggestions=suggestions,
            report=report,
            execution_time=time.time() - start_time,
            metadata={
                "service": "Cppcheck",
                "language": request.language,
                "review_type": request.review_type,
                "total_issues": len(issues_found)
            }
        )
    
    def _map_severity(self, severity: str) -> str:
        """映射严重程度"""
        severity_map = {
            "error": "error",
            "warning": "warning",
            "style": "info",
            "performance": "warning",
            "portability": "info",
            "information": "info"
        }
        return severity_map.get(severity, "info")
    
    def _generate_suggestions(self, issues: List[Dict], language: str) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if not issues:
            suggestions.append("✅ 代码质量良好，未发现明显问题")
            return suggestions
        
        # 统计问题类型
        error_count = sum(1 for issue in issues if issue["type"] == "error")
        warning_count = sum(1 for issue in issues if issue["type"] == "warning")
        
        if error_count > 0:
            suggestions.append(f"🔴 发现 {error_count} 个错误，需要立即修复")
        
        if warning_count > 0:
            suggestions.append(f"🟡 发现 {warning_count} 个警告，建议优化")
        
        # 常见问题建议
        rule_counts = {}
        for issue in issues:
            rule = issue.get("rule", "unknown")
            rule_counts[rule] = rule_counts.get(rule, 0) + 1
        
        if "nullPointer" in rule_counts:
            suggestions.append("🔍 检查空指针解引用问题")
        
        if "arrayIndexOutOfBounds" in rule_counts:
            suggestions.append("📊 检查数组边界访问")
        
        if "memoryLeak" in rule_counts:
            suggestions.append("💾 修复内存泄漏问题")
        
        if "uninitvar" in rule_counts:
            suggestions.append("🔧 初始化所有变量")
        
        suggestions.append("📚 建议使用静态分析工具进行持续代码检查")
        
        return suggestions
    
    def _generate_report(self, issues: List[Dict], suggestions: List[str], language: str) -> str:
        """生成检查报告"""
        report = f"# Cppcheck 静态分析报告\n\n"
        report += f"**检查语言**: {language.upper()}\n"
        report += f"**检查时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**检查工具**: Cppcheck\n\n"
        
        # 问题统计
        error_count = sum(1 for issue in issues if issue["type"] == "error")
        warning_count = sum(1 for issue in issues if issue["type"] == "warning")
        info_count = sum(1 for issue in issues if issue["type"] == "info")
        
        report += "## 问题统计\n\n"
        report += f"- **错误**: {error_count} 个\n"
        report += f"- **警告**: {warning_count} 个\n"
        report += f"- **信息**: {info_count} 个\n"
        report += f"- **总计**: {len(issues)} 个问题\n\n"
        
        # 详细问题列表
        if issues:
            report += "## 详细问题\n\n"
            for i, issue in enumerate(issues, 1):
                type_icon = {"error": "🔴", "warning": "🟡", "info": "ℹ️"}.get(issue["type"], "❓")
                report += f"{i}. {type_icon} **{issue.get('rule', 'unknown')}** (第{issue.get('line', 0)}行)\n"
                report += f"   {issue.get('message', '')}\n"
                
                cwe = issue.get('cwe')
                if cwe:
                    report += f"   🔒 *CWE*: {cwe}\n"
                report += "\n"
        
        # 改进建议
        if suggestions:
            report += "## 改进建议\n\n"
            for suggestion in suggestions:
                report += f"- {suggestion}\n"
        
        return report
    
    def _create_unsupported_result(self, request_id: str, request: CodeReviewRequest, start_time: float) -> CodeReviewResult:
        """创建不支持语言的结果"""
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            language=request.language,
            checker="Cppcheck",
            score=0,
            issues=[],
            suggestions=[f"Cppcheck暂不支持 {request.language} 语言的代码检查"],
            report=f"Cppcheck不支持 {request.language} 语言",
            execution_time=time.time() - start_time,
            metadata={'error': 'unsupported_language'}
        )
    
    def _create_error_result(self, request_id: str, request: CodeReviewRequest, error: str, start_time: float) -> CodeReviewResult:
        """创建错误结果"""
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            language=request.language,
            checker="Cppcheck",
            score=0,
            issues=[],
            suggestions=["检查Cppcheck环境配置", "确认Cppcheck已正确安装"],
            report=f"Cppcheck检查失败: {error}",
            execution_time=time.time() - start_time,
            metadata={'error': error}
        )
    
    def _cleanup_temp_files(self, files: List[Path]):
        """清理临时文件"""
        for file in files:
            try:
                if file.exists():
                    file.unlink()
            except Exception as e:
                logger.warning(f"清理临时文件失败 {file}: {e}") 