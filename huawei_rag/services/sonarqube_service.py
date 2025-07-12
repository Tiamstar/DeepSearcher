#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SonarQube 代码检查服务

基于Docker部署的SonarQube进行多语言代码质量检查
支持通过REST API进行代码分析和结果获取
"""

import asyncio
import json
import os
import tempfile
import time
import subprocess
import requests
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import uuid
import shutil

from huawei_rag.core.search_agent import CodeReviewInterface, CodeReviewRequest, CodeReviewResult

logger = logging.getLogger(__name__)

class SonarQubeService(CodeReviewInterface):
    """SonarQube 代码检查服务"""
    
    def __init__(self, **kwargs):
        """
        初始化 SonarQube 服务
        
        Args:
            **kwargs: 配置参数
                - sonar_host_url: SonarQube服务地址 (默认: http://localhost:9000)
                - sonar_token: 访问令牌 (推荐使用token而非用户名密码)
                - sonar_login: 登录用户名 (默认: admin)
                - sonar_password: 密码 (默认: deepsearch)
                - project_key: 项目键 (默认: deep-searcher)
                - timeout: 分析超时时间 (默认: 300秒)
                - scanner_path: SonarQube Scanner路径 (可选)
        """
        self.sonar_host_url = kwargs.get('sonar_host_url', 'http://localhost:9000')
        self.sonar_token = kwargs.get('sonar_token', 'squ_a78414aeaaaf4a1b0f91ecdcdd9f7c508a28b45e')
        self.sonar_login = kwargs.get('sonar_login', 'admin')
        self.sonar_password = kwargs.get('sonar_password', 'deepsearch')
        self.project_key = kwargs.get('project_key', 'deep-searcher')
        self.timeout = kwargs.get('timeout', 300)
        self.scanner_path = kwargs.get('scanner_path', 'sonar-scanner')
        
        # 创建临时工作目录
        self.temp_dir = Path(tempfile.gettempdir()) / "sonarqube_service"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 支持的语言和文件扩展名映射
        self.extension_mapping = {
            'python': '.py',
            'javascript': '.js', 
            'js': '.js',
            'typescript': '.ts',
            'ts': '.ts',
            'java': '.java',
            'html': '.html',
            'css': '.css',
            'xml': '.xml',
            'json': '.json',
            'yaml': '.yaml',
            'yml': '.yml',
            'c': '.c',
            'cpp': '.cpp',
            'c++': '.cpp',
            'cxx': '.cpp',
            'cc': '.cpp',
            'h': '.h',
            'hpp': '.hpp',
            'hxx': '.hpp'
        }
        
        logger.info(f"SonarQube服务初始化完成: {self.sonar_host_url}")
        logger.info(f"项目键: {self.project_key}")
        logger.info(f"认证方式: 用户名密码 (admin/deepsearch)")
        
        # 支持的语言映射
        self.language_mapping = {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
            'csharp': 'cs',
            'c#': 'cs',
            'go': 'go',
            'kotlin': 'kotlin',
            'scala': 'scala',
            'php': 'php',
            'ruby': 'ruby',
            'swift': 'swift',
            'html': 'web',
            'css': 'css',
            'xml': 'xml'
        }
        
    @property
    def _auth_header(self):
        """获取认证头"""
        if hasattr(self, '_cached_auth_header'):
            return self._cached_auth_header
        
        # 优先使用用户名密码认证（更稳定）
        import base64
        credentials = base64.b64encode(f"{self.sonar_login}:{self.sonar_password}".encode()).decode()
        self._cached_auth_header = {
            'Authorization': f'Basic {credentials}'
        }
        
        return self._cached_auth_header

    @_auth_header.setter
    def _auth_header(self, value):
        """设置认证头"""
        self._cached_auth_header = value
    
    def is_available(self) -> bool:
        """检查 SonarQube 服务是否可用"""
        try:
            # 检查SonarQube服务状态
            response = requests.get(
                f"{self.sonar_host_url}/api/system/status",
                headers=self._auth_header,
                timeout=10
            )
            
            if response.status_code == 200:
                status_data = response.json()
                return status_data.get('status') == 'UP'
            else:
                logger.warning(f"SonarQube状态检查失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"SonarQube 不可用: {e}")
            return False
    
    async def review_code(self, request: CodeReviewRequest) -> CodeReviewResult:
        """
        使用 SonarQube 检查代码
        
        Args:
            request: 代码检查请求
            
        Returns:
            代码检查结果
        """
        start_time = time.time()
        request_id = f"sonarqube_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        try:
            # 检查语言支持
            if not self._is_language_supported(request.language):
                return self._create_unsupported_result(request_id, request, start_time)
            
            # 创建项目Key
            project_key = f"temp-project-{request_id}"
            
            # 创建临时项目目录
            project_dir = await self._create_temp_project(request.code, request.language, project_key)
            
            # 执行SonarQube分析
            analysis_result = await self._run_sonar_analysis(project_dir, project_key)
            
            if not analysis_result['success']:
                return self._create_error_result(request_id, request, analysis_result['error'], start_time)
            
            # 获取分析结果
            issues = await self._get_analysis_results(project_key)
            
            # 解析结果
            result = self._parse_sonarqube_result(
                request_id, request, issues, start_time
            )
            
            # 清理临时文件和项目
            await self._cleanup_temp_project(project_dir, project_key)
            
            return result
            
        except Exception as e:
            logger.error(f"SonarQube 检查失败: {e}")
            return self._create_error_result(request_id, request, str(e), start_time)
    
    def _is_language_supported(self, language: str) -> bool:
        """检查语言是否支持"""
        return language.lower() in self.language_mapping
    
    async def _create_temp_project(self, code: str, language: str, project_key: str) -> Path:
        """创建临时项目目录"""
        project_dir = self.temp_dir / project_key
        project_dir.mkdir(exist_ok=True)
        
        # 确定文件扩展名
        ext = self.extension_mapping.get(language.lower(), '.txt')
        code_file = project_dir / f"source{ext}"
        
        # 写入代码文件
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 创建sonar-project.properties文件 - 使用更严格的配置
        properties_content = f"""# SonarQube项目配置
sonar.projectKey={project_key}
sonar.projectName=Temp Analysis Project
sonar.projectVersion=1.0
sonar.sources=.
sonar.sourceEncoding=UTF-8
sonar.host.url={self.sonar_host_url}
sonar.login={self.sonar_login}
sonar.password={self.sonar_password}

# 启用详细日志以便调试
sonar.verbose=true
sonar.log.level=DEBUG

# 质量门禁设置
sonar.qualitygate.wait=true

# 安全扫描设置
sonar.security.hotspots.inheritFromParent=true

# Python特定配置
sonar.python.pylint.reportPath=
sonar.python.bandit.reportPaths=

# 代码重复检测配置
sonar.cpd.minimumTokens=50
sonar.cpd.minimumLines=5

# 确保包含所有文件
sonar.inclusions=**/*.py,**/*.js,**/*.ts,**/*.java,**/*.html,**/*.css,**/*.xml
sonar.exclusions=
"""
        
        properties_file = project_dir / "sonar-project.properties"
        with open(properties_file, 'w', encoding='utf-8') as f:
            f.write(properties_content)
        
        return project_dir
    
    async def _run_sonar_analysis(self, project_dir: Path, project_key: str) -> Dict[str, Any]:
        """运行SonarQube分析"""
        try:
            # 构建sonar-scanner命令
            cmd = [
                self.scanner_path,
                f"-Dsonar.projectKey={project_key}",
                f"-Dsonar.host.url={self.sonar_host_url}",
                f"-Dsonar.login={self.sonar_login}",
                f"-Dsonar.password={self.sonar_password}"
            ]
            
            # 执行分析
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            
            logger.debug(f"SonarQube分析输出: {stdout_text}")
            if stderr_text:
                logger.debug(f"SonarQube分析错误: {stderr_text}")
            
            if process.returncode == 0:
                return {"success": True, "output": stdout_text}
            else:
                return {"success": False, "error": f"分析失败: {stderr_text or stdout_text}"}
                
        except asyncio.TimeoutError:
            return {"success": False, "error": "分析超时"}
        except FileNotFoundError:
            return {"success": False, "error": "sonar-scanner命令未找到，请确保已安装SonarQube Scanner"}
        except Exception as e:
            return {"success": False, "error": f"执行分析时出错: {str(e)}"}
    
    async def _get_analysis_results(self, project_key: str) -> List[Dict[str, Any]]:
        """获取分析结果"""
        try:
            # 等待分析完成 - 增加等待时间
            await asyncio.sleep(5)
            
            all_issues = []
            
            # 获取问题列表
            issues_url = f"{self.sonar_host_url}/api/issues/search"
            params = {
                'componentKeys': project_key,
                'ps': 500,  # 每页数量
                'resolved': 'false'  # 只获取未解决的问题
            }
            
            response = requests.get(
                issues_url,
                headers=self._auth_header,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                all_issues.extend(issues)
                logger.info(f"获取到 {len(issues)} 个常规问题")
            else:
                logger.warning(f"获取问题列表失败: HTTP {response.status_code}")
            
            # 获取安全热点
            hotspots_url = f"{self.sonar_host_url}/api/hotspots/search"
            hotspot_params = {
                'projectKey': project_key,
                'ps': 500
            }
            
            try:
                hotspot_response = requests.get(
                    hotspots_url,
                    headers=self._auth_header,
                    params=hotspot_params,
                    timeout=30
                )
                
                if hotspot_response.status_code == 200:
                    hotspot_data = hotspot_response.json()
                    hotspots = hotspot_data.get('hotspots', [])
                    
                    # 将安全热点转换为问题格式
                    for hotspot in hotspots:
                        issue = {
                            'key': hotspot.get('key'),
                            'rule': hotspot.get('ruleKey'),
                            'severity': hotspot.get('vulnerabilityProbability', 'MEDIUM'),
                            'message': hotspot.get('message', '安全热点'),
                            'component': hotspot.get('component'),
                            'line': hotspot.get('line'),
                            'type': 'SECURITY_HOTSPOT',
                            'status': hotspot.get('status', 'TO_REVIEW')
                        }
                        all_issues.append(issue)
                    
                    logger.info(f"获取到 {len(hotspots)} 个安全热点")
                
            except Exception as e:
                logger.debug(f"获取安全热点失败: {e}")
            
            # 获取代码异味（如果还没有获取到足够的问题）
            if len(all_issues) == 0:
                logger.info("尝试获取所有类型的问题...")
                params_all = {
                    'componentKeys': project_key,
                    'ps': 500,
                    'types': 'CODE_SMELL,BUG,VULNERABILITY,SECURITY_HOTSPOT'
                }
                
                response_all = requests.get(
                    issues_url,
                    headers=self._auth_header,
                    params=params_all,
                    timeout=30
                )
                
                if response_all.status_code == 200:
                    data_all = response_all.json()
                    all_issues.extend(data_all.get('issues', []))
                    logger.info(f"获取到所有类型问题: {len(all_issues)} 个")
            
            logger.info(f"总共获取到 {len(all_issues)} 个问题")
            return all_issues
                
        except Exception as e:
            logger.error(f"获取分析结果时出错: {e}")
            return []
    
    def _parse_sonarqube_result(self, 
                               request_id: str, 
                               request: CodeReviewRequest,
                               issues: List[Dict[str, Any]],
                               start_time: float) -> CodeReviewResult:
        """解析 SonarQube 结果"""
        
        issues_found = []
        suggestions = []
        score = 100.0
        
        # 统计各类问题
        bug_count = 0
        vulnerability_count = 0
        code_smell_count = 0
        
        for issue in issues:
            issue_type = issue.get('type', 'CODE_SMELL')
            severity = issue.get('severity', 'INFO')
            rule = issue.get('rule', 'unknown')
            message = issue.get('message', '')
            line = issue.get('line', 0)
            
            # 统计问题类型
            if issue_type == 'BUG':
                bug_count += 1
            elif issue_type == 'VULNERABILITY':
                vulnerability_count += 1
            elif issue_type == 'CODE_SMELL':
                code_smell_count += 1
            
            # 映射严重程度
            mapped_severity = self._map_severity(severity)
            
            issue_data = {
                "type": mapped_severity,
                "message": message,
                "line": line,
                "rule": rule,
                "severity": severity,
                "issue_type": issue_type,
                "effort": issue.get('effort', ''),
                "debt": issue.get('debt', '')
            }
            issues_found.append(issue_data)
            
            # 根据问题类型和严重程度扣分
            if issue_type == 'BUG':
                if severity in ['BLOCKER', 'CRITICAL']:
                    score -= 20
                elif severity == 'MAJOR':
                    score -= 10
                else:
                    score -= 5
            elif issue_type == 'VULNERABILITY':
                if severity in ['BLOCKER', 'CRITICAL']:
                    score -= 25
                elif severity == 'MAJOR':
                    score -= 15
                else:
                    score -= 8
            elif issue_type == 'CODE_SMELL':
                if severity in ['BLOCKER', 'CRITICAL']:
                    score -= 8
                elif severity == 'MAJOR':
                    score -= 4
                else:
                    score -= 2
        
        # 生成建议
        if issues_found:
            suggestions = self._generate_suggestions(bug_count, vulnerability_count, code_smell_count, request.language)
        else:
            suggestions = ["代码质量优秀，未发现明显问题"]
        
        # 生成报告
        report = self._generate_report(bug_count, vulnerability_count, code_smell_count, request.language)
        
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            review_report=report,
            issues_found=issues_found,
            suggestions=suggestions,
            score=max(score, 0.0),
            review_metadata={
                "service": "SonarQube",
                "language": request.language,
                "review_type": request.review_type,
                "sonar_host": self.sonar_host_url,
                "bug_count": bug_count,
                "vulnerability_count": vulnerability_count,
                "code_smell_count": code_smell_count,
                "total_issues": len(issues_found)
            },
            processing_time=time.time() - start_time
        )
    
    def _map_severity(self, severity: str) -> str:
        """映射 SonarQube 严重程度到标准类型"""
        severity_map = {
            'BLOCKER': 'error',
            'CRITICAL': 'error',
            'MAJOR': 'warning',
            'MINOR': 'warning',
            'INFO': 'info'
        }
        return severity_map.get(severity, 'info')
    
    def _generate_suggestions(self, bug_count: int, vulnerability_count: int, 
                            code_smell_count: int, language: str) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if bug_count > 0:
            suggestions.append(f"发现 {bug_count} 个潜在错误，建议优先修复")
        
        if vulnerability_count > 0:
            suggestions.append(f"发现 {vulnerability_count} 个安全漏洞，请立即处理")
        
        if code_smell_count > 0:
            suggestions.append(f"发现 {code_smell_count} 个代码异味，建议重构改进")
        
        # 针对特定语言的建议
        if language.lower() == 'python':
            suggestions.append("建议遵循PEP 8编码规范")
        elif language.lower() in ['javascript', 'typescript']:
            suggestions.append("建议使用现代ES6+语法和最佳实践")
        elif language.lower() in ['java']:
            suggestions.append("建议遵循Java编码规范和最佳实践")
        
        return suggestions
    
    def _generate_report(self, bug_count: int, vulnerability_count: int, 
                        code_smell_count: int, language: str) -> str:
        """生成检查报告"""
        total_issues = bug_count + vulnerability_count + code_smell_count
        
        if total_issues == 0:
            return f"SonarQube分析完成，{language}代码质量优秀，未发现问题。"
        
        report = f"SonarQube分析完成，共发现 {total_issues} 个问题：\n"
        
        if bug_count > 0:
            report += f"- 🐛 错误: {bug_count} 个\n"
        
        if vulnerability_count > 0:
            report += f"- 🔒 安全漏洞: {vulnerability_count} 个\n"
        
        if code_smell_count > 0:
            report += f"- 👃 代码异味: {code_smell_count} 个\n"
        
        report += f"\n建议按优先级修复：安全漏洞 > 错误 > 代码异味"
        
        return report
    
    async def _cleanup_temp_project(self, project_dir: Path, project_key: str):
        """清理临时项目"""
        try:
            # 删除临时目录
            if project_dir.exists():
                shutil.rmtree(project_dir)
            
            # 尝试删除SonarQube中的临时项目
            try:
                delete_url = f"{self.sonar_host_url}/api/projects/delete"
                data = {'project': project_key}
                
                requests.post(
                    delete_url,
                    headers=self._auth_header,
                    data=data,
                    timeout=10
                )
            except Exception as e:
                logger.debug(f"删除SonarQube临时项目失败: {e}")
                
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def _create_unsupported_result(self, request_id: str, request: CodeReviewRequest, start_time: float) -> CodeReviewResult:
        """创建不支持语言的结果"""
        supported_languages = list(self.language_mapping.keys())
        
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            review_report=f"SonarQube 不支持 {request.language} 语言",
            issues_found=[{
                "type": "info",
                "message": f"不支持的语言: {request.language}",
                "severity": "info"
            }],
            suggestions=[f"SonarQube支持的语言: {', '.join(supported_languages)}"],
            score=0.0,
            review_metadata={
                "service": "SonarQube",
                "language": request.language,
                "supported": False,
                "supported_languages": supported_languages
            },
            processing_time=time.time() - start_time
        )
    
    def _create_error_result(self, request_id: str, request: CodeReviewRequest, error: str, start_time: float) -> CodeReviewResult:
        """创建错误结果"""
        return CodeReviewResult(
            request_id=request_id,
            original_query=request.original_query,
            code=request.code,
            review_report=f"SonarQube 检查失败: {error}",
            issues_found=[{
                "type": "error",
                "message": error,
                "severity": "error"
            }],
            suggestions=[
                "检查SonarQube服务是否正常运行",
                "确认sonar-scanner已正确安装",
                "检查网络连接和认证配置"
            ],
            score=0.0,
            review_metadata={
                "service": "SonarQube",
                "error": error,
                "sonar_host": self.sonar_host_url
            },
            processing_time=time.time() - start_time
        ) 