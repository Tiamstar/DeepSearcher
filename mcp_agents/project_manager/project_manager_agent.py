#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目管理Agent - MCP实现
使用原项目相同的LLM方式，确保功能完全一致
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_agents.base.mcp_agent import MCPAgent
from mcp_agents.base.protocol import MCPMessage, MessageType
from shared.config_loader import get_config_loader

# 导入DeepSearcher组件 - 与原项目保持一致
try:
    from deepsearcher.configuration import config, init_config
    # 初始化DeepSearcher配置
    try:
        init_config(config)
        from deepsearcher.configuration import llm, embedding_model, vector_db
        logging.info("✅ DeepSearcher组件初始化成功")
    except Exception as init_error:
        logging.warning(f"DeepSearcher组件初始化失败: {init_error}")
        llm = embedding_model = vector_db = None
except ImportError as e:
    logging.warning(f"DeepSearcher模块导入失败: {e}")
    llm = embedding_model = vector_db = None

logger = logging.getLogger(__name__)

class ProjectManagerAgent(MCPAgent):
    """
    项目管理Agent - MCP实现
    使用原项目相同的LLM方式，确保功能完全一致
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("project_manager", config)
        
        # 获取配置加载器
        self.config_loader = get_config_loader()
        
        # 使用原项目相同的LLM对象
        self.llm = llm
        
        # 注册MCP方法
        self._register_mcp_methods()
        
        # 项目管理提示词
        self.system_prompts = {
            "decompose": """你是一个专业的项目管理专家，专门负责华为技术栈的项目管理。
请将用户的需求分解为具体的、可执行的任务。每个任务应该包含：
1. 任务描述
2. 优先级（高/中/低）
3. 预估工作量（小时）
4. 依赖关系
5. 技术要求
6. 验收标准

特别关注华为鸿蒙系统、ArkTS、ArkUI等技术栈的特殊要求。""",
            
            "validate": """你是一个项目需求验证专家，请验证项目需求的：
1. 完整性 - 需求是否完整清晰
2. 可行性 - 技术实现是否可行
3. 合理性 - 时间和资源估算是否合理
4. 一致性 - 需求之间是否存在冲突
5. 华为技术栈兼容性 - 是否符合华为开发规范

请提供详细的验证报告和改进建议。""",
            
            "estimate": """你是一个项目工作量评估专家，请对项目任务进行准确的工作量估算：
1. 开发工作量（编码、测试、调试）
2. 设计工作量（架构设计、UI设计）
3. 集成工作量（系统集成、API对接）
4. 文档工作量（技术文档、用户手册）
5. 风险缓冲时间

考虑华为技术栈的学习曲线和特殊要求。"""
        }
    
    def _register_mcp_methods(self):
        """注册MCP方法"""
        self.methods = {
            "project.decompose": self._decompose_project,
            "project.validate": self._validate_requirements,
            "project.estimate": self._estimate_workload,
            "project.analyze": self._analyze_project,
            "project.plan": self._create_project_plan,
            "project.status": self._get_project_status
        }
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化项目管理Agent"""
        try:
            # 声明Agent能力
            self.declare_capability("project.decompose", {
                "description": "项目需求分解",
                "parameters": ["requirements", "context", "tech_stack"]
            })
            self.declare_capability("project.validate", {
                "description": "需求验证",
                "parameters": ["requirements", "context"]
            })
            self.declare_capability("project.estimate", {
                "description": "工作量估算",
                "parameters": ["tasks", "team_size", "experience_level"]
            })
            self.declare_capability("project.analyze", {
                "description": "项目分析",
                "parameters": ["requirements", "constraints"]
            })
            self.declare_capability("project.plan", {
                "description": "项目规划",
                "parameters": ["tasks", "timeline", "resources"]
            })
            
            self.logger.info("项目管理Agent初始化成功")
            
            return {
                "agent_id": self.agent_id,
                "capabilities": self.capabilities,
                "methods": list(self.methods.keys()),
                "llm_available": self.llm is not None,
                "status": "initialized"
            }
            
        except Exception as e:
            self.logger.error(f"项目管理Agent初始化失败: {str(e)}")
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理项目管理相关请求"""
        try:
            method = message.method
            params = message.params or {}
            
            if method in self.methods:
                result = await self.methods[method](params)
                return self.protocol.create_response(message.id, result)
            else:
                return self.protocol.handle_method_not_found(message.id, method)
                
        except Exception as e:
            self.logger.error(f"处理项目管理请求失败: {str(e)}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _decompose_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        项目需求分解
        """
        try:
            if not self.llm:
                return {
                    "success": False,
                    "error": "LLM未初始化",
                    "tasks": []
                }
            
            requirements = params.get("requirements", "")
            context = params.get("context", "")
            tech_stack = params.get("tech_stack", "华为鸿蒙系统")
            
            if not requirements:
                return {
                    "success": False,
                    "error": "项目需求不能为空",
                    "tasks": []
                }
            
            # 构建提示词 - 使用原项目相同的方式
            prompt = f"""
{self.system_prompts['decompose']}

项目需求：
{requirements}

上下文信息：
{context}

技术栈：
{tech_stack}

请将上述需求分解为具体的任务清单，以JSON格式返回。
"""
            
            # 调用LLM - 使用原项目相同的方式
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = self.llm.remove_think(response.content) if hasattr(self.llm, 'remove_think') else response.content
            
            # 解析LLM响应
            tasks = self._parse_task_decomposition(content)
            
            return {
                "success": True,
                "requirements": requirements,
                "tech_stack": tech_stack,
                "tasks": tasks,
                "total_tasks": len(tasks),
                "llm_response": content,
                "token_usage": getattr(response, 'total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"项目需求分解失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "tasks": []
            }
    
    async def _validate_requirements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        需求验证
        """
        try:
            if not self.llm:
                return {
                    "success": False,
                    "error": "LLM未初始化",
                    "validation_result": {}
                }
            
            requirements = params.get("requirements", "")
            context = params.get("context", "")
            
            if not requirements:
                return {
                    "success": False,
                    "error": "项目需求不能为空",
                    "validation_result": {}
                }
            
            # 构建提示词 - 使用原项目相同的方式
            prompt = f"""
{self.system_prompts['validate']}

项目需求：
{requirements}

上下文信息：
{context}

请对上述需求进行全面验证，包括完整性、可行性、合理性、一致性和华为技术栈兼容性。
"""
            
            # 调用LLM - 使用原项目相同的方式
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = self.llm.remove_think(response.content) if hasattr(self.llm, 'remove_think') else response.content
            
            # 解析验证结果
            validation_result = self._parse_validation_result(content)
            
            return {
                "success": True,
                "requirements": requirements,
                "validation_result": validation_result,
                "llm_response": content,
                "token_usage": getattr(response, 'total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"需求验证失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "validation_result": {}
            }
    
    async def _estimate_workload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        工作量估算
        """
        try:
            if not self.llm:
                return {
                    "success": False,
                    "error": "LLM未初始化",
                    "estimation": {}
                }
            
            tasks = params.get("tasks", [])
            team_size = params.get("team_size", 3)
            experience_level = params.get("experience_level", "中级")
            
            if not tasks:
                return {
                    "success": False,
                    "error": "任务清单不能为空",
                    "estimation": {}
                }
            
            # 构建估算提示词
            prompt = f"""
你是一个项目工作量评估专家，请对项目任务进行准确的工作量估算：

任务清单：
{tasks}

团队规模：{team_size}人
经验水平：{experience_level}

请对上述任务进行详细的工作量估算，以JSON格式返回估算结果。
"""
            
            # 调用LLM - 使用原项目相同的方式
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = self.llm.remove_think(response.content) if hasattr(self.llm, 'remove_think') else response.content
            
            # 解析估算结果
            estimation = self._parse_estimation_result(content)
            
            return {
                "success": True,
                "tasks": tasks,
                "team_size": team_size,
                "experience_level": experience_level,
                "estimation": estimation,
                "llm_response": content,
                "token_usage": getattr(response, 'total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"工作量估算失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "estimation": {}
            }
    
    async def _analyze_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        项目分析
        """
        try:
            if not self.llm:
                return {
                    "success": False,
                    "error": "LLM未初始化",
                    "analysis": {}
                }
            
            requirements = params.get("requirements", "")
            constraints = params.get("constraints", [])
            goals = params.get("goals", [])
            
            # 构建分析提示词
            prompt = f"""
作为项目分析专家，请对以下项目进行全面分析：

项目需求：
{requirements}

约束条件：
{constraints}

项目目标：
{goals}

请从技术可行性、资源需求、风险评估、时间规划等角度进行分析。
"""
            
            # 调用LLM - 使用原项目相同的方式
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = self.llm.remove_think(response.content) if hasattr(self.llm, 'remove_think') else response.content
            
            return {
                "success": True,
                "requirements": requirements,
                "analysis": {
                    "content": content,
                    "constraints": constraints,
                    "goals": goals
                },
                "llm_response": content,
                "token_usage": getattr(response, 'total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"项目分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": {}
            }
    
    async def _create_project_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建项目计划
        """
        try:
            if not self.llm:
                return {
                    "success": False,
                    "error": "LLM未初始化",
                    "plan": {}
                }
            
            tasks = params.get("tasks", [])
            timeline = params.get("timeline", "4周")
            resources = params.get("resources", {})
            
            # 构建计划提示词
            prompt = f"""
作为项目计划专家，请为以下任务创建详细的项目计划：

任务清单：
{tasks}

项目时间线：{timeline}
可用资源：{resources}

请创建包含时间安排、资源分配、里程碑的详细项目计划。
"""
            
            # 调用LLM - 使用原项目相同的方式
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = self.llm.remove_think(response.content) if hasattr(self.llm, 'remove_think') else response.content
            
            return {
                "success": True,
                "tasks": tasks,
                "timeline": timeline,
                "plan": {
                    "content": content,
                    "resources": resources
                },
                "llm_response": content,
                "token_usage": getattr(response, 'total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"创建项目计划失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "plan": {}
            }
    
    async def _get_project_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取项目管理状态"""
        try:
            return {
                "success": True,
                "status": {
                    "agent_initialized": True,
                    "llm_client_available": self.llm is not None,
                    "llm_config": self.config_loader.get_llm_config("project_manager"),
                    "capabilities": {
                        "project_decomposition": True,
                        "requirements_validation": True,
                        "workload_estimation": True,
                        "project_analysis": True,
                        "project_planning": True
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取项目状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_task_decomposition(self, response: str) -> List[Dict[str, Any]]:
        """解析任务分解结果"""
        try:
            # 尝试解析JSON格式的响应
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                tasks_json = json_match.group(0)
                tasks = json.loads(tasks_json)
                return tasks
            
            # 如果无法解析JSON，返回文本解析结果
            return self._parse_text_to_tasks(response)
            
        except Exception as e:
            logger.error(f"解析任务分解结果失败: {e}")
            return []
    
    def _parse_text_to_tasks(self, text: str) -> List[Dict[str, Any]]:
        """从文本中解析任务"""
        tasks = []
        lines = text.split('\n')
        current_task = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('任务') or line.startswith('Task'):
                if current_task:
                    tasks.append(current_task)
                current_task = {"description": line, "priority": "中", "hours": 8}
            elif '优先级' in line or 'priority' in line.lower():
                if current_task:
                    current_task["priority"] = line.split(':')[-1].strip()
            elif '工作量' in line or 'hours' in line.lower():
                if current_task:
                    try:
                        hours = int(re.search(r'\d+', line).group())
                        current_task["hours"] = hours
                    except:
                        current_task["hours"] = 8
        
        if current_task:
            tasks.append(current_task)
        
        return tasks
    
    def _parse_validation_result(self, response: str) -> Dict[str, Any]:
        """解析验证结果"""
        try:
            import json
            import re
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result_json = json_match.group(0)
                result = json.loads(result_json)
                return result
            
            # 文本解析
            return {
                "completeness": "需要进一步分析",
                "feasibility": "技术可行",
                "reasonableness": "基本合理",
                "consistency": "无明显冲突",
                "huawei_compatibility": "符合华为规范",
                "details": response
            }
            
        except Exception as e:
            logger.error(f"解析验证结果失败: {e}")
            return {"details": response}
    
    def _parse_estimation_result(self, response: str) -> Dict[str, Any]:
        """解析估算结果"""
        try:
            import json
            import re
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result_json = json_match.group(0)
                result = json.loads(result_json)
                return result
            
            # 文本解析
            total_hours = 40  # 默认值
            try:
                hours_match = re.search(r'(\d+)\s*小时', response)
                if hours_match:
                    total_hours = int(hours_match.group(1))
            except:
                pass
            
            return {
                "total_hours": total_hours,
                "development_hours": total_hours * 0.6,
                "design_hours": total_hours * 0.2,
                "integration_hours": total_hours * 0.15,
                "documentation_hours": total_hours * 0.05,
                "details": response
            }
            
        except Exception as e:
            logger.error(f"解析估算结果失败: {e}")
            return {"total_hours": 40, "details": response}
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力"""
        return {
            "name": "project_manager",
            "description": "华为项目管理Agent - 支持需求分解、验证、估算和计划",
            "version": "1.0.0",
            "methods": list(self.methods.keys()),
            "resources": [
                {
                    "name": "project_tasks",
                    "description": "项目任务资源",
                    "type": "application/json"
                },
                {
                    "name": "project_plan",
                    "description": "项目计划资源",
                    "type": "application/json"
                }
            ],
            "tools": [
                {
                    "name": "task_decomposition",
                    "description": "任务分解工具"
                },
                {
                    "name": "requirement_validation",
                    "description": "需求验证工具"
                },
                {
                    "name": "workload_estimation",
                    "description": "工作量估算工具"
                },
                {
                    "name": "project_planning",
                    "description": "项目规划工具"
                }
            ]
        } 