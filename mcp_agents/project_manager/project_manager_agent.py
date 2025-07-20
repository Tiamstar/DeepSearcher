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

# 导入鸿蒙相关组件
from mcp_agents.harmonyos import HarmonyOSProjectAnalyzer, HarmonyOSCompilerService

# 导入工作流Prompt系统
from shared.workflow_prompts import WorkflowType, workflow_prompts

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
        
        # 优先使用配置加载器的LLM，备用DeepSearcher的LLM
        try:
            llm_config = self.config_loader.get_llm_config("project_manager")
            logger.info(f"🔍 获取到项目管理Agent LLM配置")
            
            if llm_config and llm_config.get("provider"):
                from shared.llm_factory import LLMFactory
                self.llm = LLMFactory.create_llm(llm_config)
                if self.llm:
                    logger.info("✅ 项目管理Agent LLM初始化成功（使用配置加载器）")
                else:
                    logger.warning("配置加载器返回了None，尝试使用DeepSearcher LLM")
                    self.llm = llm
            else:
                logger.info("未找到项目管理Agent专用配置，使用DeepSearcher LLM")
                self.llm = llm
                if self.llm:
                    logger.info("✅ 项目管理Agent LLM初始化成功（使用DeepSearcher LLM）")
                else:
                    logger.warning("DeepSearcher LLM也为None")
        except Exception as e:
            logger.error(f"项目管理Agent LLM初始化失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.llm = llm
        
        # 初始化鸿蒙组件
        self.harmonyos_analyzer = HarmonyOSProjectAnalyzer()
        self.harmonyos_compiler = HarmonyOSCompilerService()
        
        # 项目路径配置
        self.project_root = Path(__file__).parent.parent.parent
        self.myapplication2_path = self.project_root / "MyApplication2"
        
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
            "project.status": self._get_project_status,
            # 新增鸿蒙专用方法
            "project.analyze_harmonyos": self._analyze_harmonyos_requirements,
            "project.analyze_harmonyos_requirements": self._analyze_harmonyos_requirements,
            "project.hvigor_compile": self._hvigor_compile,
            "project.check_project_health": self._check_project_health,
            "project.analyze_errors_and_generate_keywords": self._analyze_errors_and_generate_keywords
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
            self.declare_capability("project.analyze_errors_and_generate_keywords", {
                "description": "分析错误信息并生成搜索关键词",
                "parameters": ["errors", "original_requirement", "project_path"]
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
    
    # ==================== 鸿蒙专用方法 ====================
    
    async def _analyze_harmonyos_requirements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析鸿蒙需求并规划文件生成 - 工作流第一步
        
        根据用户需求，详细分析并规划需要生成的文件结构和内容大纲
        为后续的搜索和代码生成提供明确的指导
        """
        try:
            # 从新的上下文系统获取参数
            user_requirement = params.get("user_requirement", params.get("requirement", ""))
            project_path = params.get("project_path", "MyApplication2")
            task_description = params.get("task_description", "")
            current_phase = params.get("current_phase", "requirement_analysis")
            
            if not user_requirement:
                return {
                    "success": False,
                    "error": "需求描述不能为空"
                }
            
            logger.info(f"项目管理Agent开始分析鸿蒙需求")
            logger.info(f"当前阶段: {current_phase}")
            logger.info(f"任务描述: {task_description}")
            logger.info(f"用户需求: {user_requirement}")
            
            # 读取MyApplication2项目结构
            project_structure = self._read_myapplication2_structure()
            logger.info(f"成功读取MyApplication2项目结构信息")
            
            # 读取README.md文件中的自然语言描述（单个文件生成模式）
            readme_content = self._read_readme_description()
            if readme_content:
                # 无论是初始生成还是错误修复，都要确保README内容完整传递
                original_user_requirement = user_requirement
                user_requirement = readme_content
                logger.info(f"从README.md文件读取到自然语言描述: {len(user_requirement)} 字符")
                logger.info(f"原始用户需求: {original_user_requirement}")
                # 在上下文中同时保存原始需求和README内容
                self._readme_content = readme_content
                self._original_requirement = original_user_requirement
            
            # 使用工作流Prompt系统进行需求分析和文件规划

            llm_available = self.llm is not None
            logger.info(f"🤖 项目管理Agent LLM状态: {'可用' if llm_available else '不可用'}")
            logger.info(f"🔍 LLM对象类型: {type(self.llm)}")
            
            if llm_available:
                logger.info(f"🚀 开始LLM分析需求...")
                
                # 确定工作流类型（初始生成或错误修复）
                is_fixing = params.get('is_fixing', False)
                workflow_type = WorkflowType.ERROR_FIXING if is_fixing else WorkflowType.INITIAL_GENERATION
                
                logger.info(f"🔄 工作流类型: {workflow_type.value}")
                
                # 获取适合的prompt
                system_prompt = workflow_prompts.get_prompt('project_manager', workflow_type, 'system')
                if workflow_type == WorkflowType.ERROR_FIXING:
                    current_errors = params.get('current_errors', [])
                    existing_files = params.get('existing_files', [])
                    user_prompt = workflow_prompts.format_user_prompt(
                        'project_manager', workflow_type,
                        user_requirement=user_requirement,
                        current_errors=current_errors,
                        existing_files=existing_files
                    )
                else:
                    # 获取项目文件内容用于更好的需求分析
                    project_context = self._get_project_context_for_llm()
                    user_prompt = workflow_prompts.format_user_prompt(
                        'project_manager', workflow_type,
                        user_requirement=user_requirement,
                        project_structure=project_structure,
                        project_context=project_context
                    )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = self.llm.chat(messages)
                content = self.llm.remove_think(response.content)
                logger.info(f"📝 LLM返回内容长度: {len(content)} 字符")
                
                # 尝试解析JSON
                import json
                try:
                    analysis_data = json.loads(content)
                    # 验证所有文件路径都在MyApplication2中
                    analysis_data = self._validate_and_fix_file_paths(analysis_data)
                except:
                    # 如果解析失败，从文本中提取关键信息
                    if workflow_type == WorkflowType.ERROR_FIXING:
                        analysis_data = self._extract_error_analysis_from_text(content, params.get('current_errors', []))
                    else:
                        analysis_data = self._extract_analysis_from_text(content, user_requirement)
            else:
                # 没有LLM时的备用分析
                if workflow_type == WorkflowType.ERROR_FIXING:
                    analysis_data = self._extract_error_analysis_from_text("", params.get('current_errors', []))
                else:
                    analysis_data = self._generate_basic_analysis(user_requirement)
            
            # 根据工作流类型返回不同的结果格式
            if workflow_type == WorkflowType.ERROR_FIXING:
                # 错误修复阶段返回错误分析结果
                logger.info(f"错误分析完成，分析了{len(analysis_data.get('error_analysis', []))}个错误")
                
                # 打印错误分析详情用于调试
                for i, error_info in enumerate(analysis_data.get('error_analysis', [])):
                    logger.info(f"  错误{i+1}: {error_info.get('target_file', 'N/A')}")
                
                return {
                    "success": True,
                    "analysis": analysis_data,
                    "error_analysis": analysis_data.get("error_analysis", []),
                    "files_to_fix": analysis_data.get("files_to_fix", []),
                    "search_queries": analysis_data.get("search_queries", []),
                    "fix_strategies": analysis_data.get("error_analysis", []),  # 为与工作流协调器兼容
                    "project_path": project_path
                }
            else:
                # 初始生成阶段返回文件规划结果
                logger.info(f"需求分析完成，规划了{len(analysis_data.get('planned_files', []))}个文件")
                
                # 打印文件路径详情用于调试
                for i, file_info in enumerate(analysis_data.get('planned_files', [])):
                    logger.info(f"  文件{i+1}: {file_info.get('path', 'N/A')}")
                
                return {
                    "success": True,
                    "analysis": analysis_data,
                    "planned_files": analysis_data.get("planned_files", []),
                    "search_keywords": analysis_data.get("search_keywords", []),
                    "requirement_analysis": analysis_data.get("requirement_analysis", {}),
                    "project_path": project_path
                }
                
        except Exception as e:
            logger.error(f"鸿蒙需求分析失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_analysis_from_text(self, content: str, user_requirement: str) -> Dict[str, Any]:
        """从LLM文本输出中提取分析结果 - 单个文件生成模式"""
        # 单个文件生成模式：只返回Index.ets文件
        analysis_data = {
            "requirement_analysis": {
                "main_functionality": f"基于Index.ets文件自然语言描述生成ArkTS页面组件",
                "key_features": ["页面组件", "UI界面", "状态管理"],
                "technical_requirements": ["ArkTS语言", "ArkUI组件", "@Entry @Component装饰器"]
            },
            "planned_files": [
                {
                    "path": "MyApplication2/entry/src/main/ets/pages/Index.ets",
                    "type": "page",
                    "purpose": "应用入口页面组件",
                    "content_outline": "@Entry @Component 页面组件，包含完整的UI界面和状态管理",
                    "key_components": ["Column", "Text", "Button", "Image"],
                    "dependencies": ["@ohos.router"]
                }
            ],
            "search_queries": [
                "HarmonyOS ArkTS页面组件开发方法和@Entry @Component装饰器使用",
                "鸿蒙应用ArkUI页面布局和状态管理最佳实践",
                "ArkTS页面组件UI组件使用方法和样式设置"
            ]
        }
        
        # 验证和修复文件路径
        return self._validate_and_fix_file_paths(analysis_data)
    
    def _generate_basic_analysis(self, user_requirement: str) -> Dict[str, Any]:
        """生成基础分析（没有LLM时的备用方案）"""
        return self._extract_analysis_from_text("", user_requirement)
    
    def _extract_error_analysis_from_text(self, content: str, current_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从文本中提取错误分析结果（备用方案）"""
        # 基础错误分析结果
        error_analysis = []
        files_to_fix = []
        search_queries = []
        
        # 智能分析错误并推断文件路径
        for i, error in enumerate(current_errors):
            error_message = error.get("message", "")
            # 智能推断文件路径
            target_file = self._infer_target_file_from_error(error_message, error.get("file_path", "unknown"))
            
            # 生成精确的搜索关键词
            search_keywords = self._generate_specific_search_keywords(error_message)
            
            error_analysis.append({
                "error_id": i + 1,
                "error_message": error_message,
                "root_cause": self._analyze_error_root_cause(error_message),
                "target_file": target_file,
                "fix_location": self._infer_fix_location(error_message, error.get('line')),
                "fix_description": self._generate_fix_description(error_message),
                "search_keywords": search_keywords
            })
            
            # 添加到修复文件列表
            if target_file != "unknown" and target_file not in [f["file_path"] for f in files_to_fix]:
                files_to_fix.append({
                    "file_path": target_file,
                    "errors": [i + 1],
                    "priority": "high"
                })
            
            # 添加精确的搜索关键词
            search_queries.extend(search_keywords)
        
        return {
            "error_analysis": error_analysis,
            "files_to_fix": files_to_fix,
            "search_queries": list(set(search_queries))  # 去重
        }
    
    def _infer_target_file_from_error(self, error_message: str, original_file_path: str) -> str:
        """根据错误信息智能推断目标文件 - 单个文件生成模式固定为Index.ets"""
        # 单个文件生成模式：所有错误都指向Index.ets文件
        return "MyApplication2/entry/src/main/ets/pages/Index.ets"
    
    def _analyze_error_root_cause(self, error_message: str) -> str:
        """分析错误根本原因"""
        if "Resource Pack Error" in error_message:
            return "JSON资源文件格式错误或内容不合法"
        elif "CompileResource" in error_message:
            return "ArkTS代码编译错误，可能是语法或类型问题"
        elif "Tools execution failed" in error_message:
            return "构建工具执行失败，可能是依赖或配置问题"
        elif "Build failed" in error_message:
            return "整体构建失败，需要检查代码质量和依赖"
        else:
            return "需要进一步分析的代码错误"
    
    def _infer_fix_location(self, error_message: str, line_number: int) -> str:
        """推断修复位置"""
        if line_number:
            return f"行 {line_number}"
        elif "Resource Pack Error" in error_message:
            return "JSON文件的整体结构"
        elif "CompileResource" in error_message:
            return "组件定义或导入语句"
        else:
            return "文件整体结构"
    
    def _generate_fix_description(self, error_message: str) -> str:
        """生成修复描述"""
        if "Resource Pack Error" in error_message:
            return "检查并修复JSON资源文件的格式和内容"
        elif "CompileResource" in error_message:
            return "修复ArkTS代码的语法错误和类型问题"
        elif "Tools execution failed" in error_message:
            return "检查与修复构建工具和依赖问题"
        elif "Build failed" in error_message:
            return "全面检查代码质量和项目结构"
        else:
            return f"修复错误: {error_message}"
    
    def _generate_specific_search_keywords(self, error_message: str) -> List[str]:
        """生成具体的搜索问题"""
        
        if "Resource Pack Error" in error_message:
            return [
                "HarmonyOS中string.json文件出现Resource Pack Error如何修复格式错误和结构问题",
                "鸿蒙应用element目录下资源文件的正确格式和配置方法"
            ]
        elif "CompileResource" in error_message:
            return [
                "ArkTS @Entry @Component装饰器CompileResource错误的常见原因和解决方法",
                "HarmonyOS ArkTS组件定义的正确语法和编译错误修复技巧"
            ]
        elif "Tools execution failed" in error_message:
            return [
                "HarmonyOS hvigor构建出现Tools execution failed错误的排查和修复步骤",
                "鸿蒙应用构建工具配置问题和依赖管理的解决方案"
            ]
        elif "Build failed" in error_message:
            return [
                "HarmonyOS项目整体构建失败Build failed的排查步骤和常见解决方法",
                "鸿蒙应用module.json5和项目结构配置错误的修复指南"
            ]
        else:
            return [
                f"HarmonyOS ArkTS中出现编译错误{error_message[:50]}的解决方法和修复技巧",
                "鸿蒙应用开发中常见代码错误的调试和修复方法"
            ]
    
    async def _hvigor_compile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行hvigor编译检查"""
        try:
            project_path = params.get("project_path", "MyApplication2")
            
            logger.info(f"开始hvigor编译检查: {project_path}")
            
            # 使用编译服务执行编译
            compile_result = self.harmonyos_compiler.run_hvigor_compile()
            
            # 生成修复建议
            if not compile_result["success"] and compile_result.get("errors"):
                suggestions = self.harmonyos_compiler.generate_fix_suggestions(
                    compile_result["errors"], 
                    []
                )
                compile_result["fix_suggestions"] = suggestions
            
            logger.info(f"编译检查完成: {'成功' if compile_result['success'] else '失败'}")
            
            return {
                "success": compile_result["success"],  # 基于编译结果返回正确的成功状态
                "project_path": project_path,
                "compile_result": compile_result,
                "status": "success" if compile_result["success"] else "failed",
                "errors": compile_result.get("errors", []),
                "total_errors": compile_result.get("total_errors", 0),
                "fix_suggestions": compile_result.get("fix_suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"hvigor编译失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed",
                "compile_result": {}
            }
    
    async def _check_project_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """检查项目健康状况"""
        try:
            logger.info("开始检查项目健康状况")
            
            # 使用编译服务检查项目健康状况
            health_result = self.harmonyos_compiler.check_project_health()
            
            # 获取项目结构信息
            project_info = self.harmonyos_analyzer.get_project_info()
            
            logger.info(f"项目健康检查完成: {health_result.get('health_status', 'unknown')}")
            
            return {
                "success": True,
                "health_check": health_result,
                "project_info": project_info,
                "health_score": health_result.get("health_score", 0),
                "health_status": health_result.get("health_status", "unknown"),
                "recommendations": self._generate_health_recommendations(health_result)
            }
            
        except Exception as e:
            logger.error(f"项目健康检查失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "health_score": 0,
                "health_status": "error"
            }
    
    def _generate_health_recommendations(self, health_result: Dict[str, Any]) -> List[str]:
        """根据健康检查结果生成建议"""
        recommendations = []
        
        missing_files = health_result.get("missing_files", [])
        missing_dirs = health_result.get("missing_directories", [])
        
        if missing_files:
            recommendations.append(f"缺少关键文件: {', '.join(missing_files)}")
        
        if missing_dirs:
            recommendations.append(f"缺少必要目录: {', '.join(missing_dirs)}")
        
        if not health_result.get("codelinter_available", False):
            recommendations.append("codelinter工具不可用，请检查安装")
        
        if not health_result.get("hvigor_available", False):
            recommendations.append("hvigor工具不可用，请检查安装")
        
        health_score = health_result.get("health_score", 0)
        if health_score < 50:
            recommendations.append("项目结构存在严重问题，建议重新初始化")
        elif health_score < 80:
            recommendations.append("项目结构需要完善，建议补充缺失文件")
        
        return recommendations
    
    # ==================== MyApplication2结构读取和验证方法 ====================
    
    def _read_myapplication2_structure(self) -> str:
        """
        读取MyApplication2项目结构信息
        为项目管理Agent提供详细的项目结构知识和实际文件内容
        """
        try:
            structure_info = """
鸿蒙应用项目结构(HarmonyOS NEXT Stage模型):

MyApplication2/                              # 项目根目录
├── AppScope/                           # 应用全局信息
│   ├── app.json5                        # 应用全局配置文件
│   └── resources/                       # 应用全局资源
├── entry/                              # 应用主模块
│   ├── src/main/                        # 主源码目录
│   │   ├── ets/                         # TypeScript源码目录
│   │   │   ├── pages/                   # 页面文件目录 (**页面文件必须放在这里**)
│   │   │   │   ├── Index.ets            # 首页
│   │   │   │   ├── LoginPage.ets        # 登录页面
│   │   │   │   └── Index.ets    # 应用入口页面文件
│   │   │   ├── services/                # 服务类目录 (**服务文件放在这里**)
│   │   │   │   └── ApiService.ets       # API服务
│   │   │   ├── entryability/            # 应用入口能力
│   │   │   │   └── EntryAbility.ets     # 主入口能力
│   │   │   └── entrybackupability/      # 备份恢复能力
│   │   │       └── EntryBackupAbility.ets
│   │   ├── module.json5                 # 模块配置文件
│   │   └── resources/                   # 模块资源
│   │       └── base/element/            # 基础资源元素 (**资源文件放在这里**)
│   │           ├── string.json      # 字符串资源
│   │           ├── color.json       # 颜色资源
│   │           └── float.json       # 浮点数资源
│   ├── build-profile.json5              # 构建配置
│   ├── hvigorfile.ts                    # 构建脚本
│   └── oh-package.json5                 # 依赖管理
└── hvigorfile.ts                           # 项目构建脚本

**关键路径规则：**
1. 页面文件：MyApplication2/entry/src/main/ets/pages/
2. 服务文件：MyApplication2/entry/src/main/ets/services/
3. 能力文件：MyApplication2/entry/src/main/ets/entryability/
4. 资源文件：MyApplication2/entry/src/main/resources/base/element/
5. 模块配置：MyApplication2/entry/src/main/module.json5

**代码生成要求：**
- 所有文件路径必须以"MyApplication2/"开头
- 页面组件使用@Entry和@Component装饰器
- 服务类提供数据处理和业务逻辑
- 资源文件使用JSON格式存储字符串、颜色等资源
            """
            
            # 实际读取目录结构和关键配置文件
            if self.myapplication2_path.exists():
                existing_files = self._scan_existing_files_with_content()
                structure_info += f"\n\n当前项目实际状态：\n{existing_files}"
            else:
                structure_info += "\n\n注意：MyApplication2项目尚不存在，需要先创建项目结构。"
            
            return structure_info
            
        except Exception as e:
            logger.error(f"读取MyApplication2结构失败: {e}")
            return "无法读取项目结构信息"
    
    def _read_readme_description(self) -> str:
        """读取README.md文件中的自然语言描述"""
        try:
            readme_file_path = self.myapplication2_path / "README.md"
            
            if not readme_file_path.exists():
                logger.warning(f"README.md文件不存在: {readme_file_path}")
                return ""
            
            with open(readme_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找自然语言描述部分
            # 寻找包含"自然语言描述"的部分
            lines = content.split('\n')
            description_lines = []
            start_capturing = False
            
            for line in lines:
                if "自然语言描述" in line:
                    start_capturing = True
                    continue
                
                if start_capturing:
                    # 如果遇到新的markdown标题，停止捕获（但允许第三级标题）
                    if line.strip().startswith('##') and not line.strip().startswith('###'):
                        break
                    
                    # 跳过空行和markdown语法，但保留内容
                    if line.strip() and not line.strip().startswith('---'):
                        description_lines.append(line.strip())
            
            description = '\n'.join(description_lines)
            logger.info(f"从README.md提取自然语言描述: {len(description)} 字符")
            
            return description if description else content
            
        except Exception as e:
            logger.error(f"读取README.md文件描述失败: {e}")
            return ""
    
    def _read_project_files_content(self) -> Dict[str, str]:
        """读取项目中的关键文件内容，用于更好的需求分析"""
        files_content = {}
        
        try:
            # 读取关键配置文件
            config_files = [
                "oh-package.json5",
                "build-profile.json5",
                "entry/build-profile.json5",
                "entry/oh-package.json5",
                "entry/src/main/module.json5"
            ]
            
            for config_file in config_files:
                file_path = self.myapplication2_path / config_file
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            files_content[config_file] = f.read()
                    except Exception as e:
                        logger.warning(f"读取配置文件失败 {config_file}: {e}")
            
            # 读取现有的代码文件
            code_dirs = [
                "entry/src/main/ets/pages",
                "entry/src/main/ets/services",
                "entry/src/main/ets/entryability"
            ]
            
            for code_dir in code_dirs:
                dir_path = self.myapplication2_path / code_dir
                if dir_path.exists():
                    for file_path in dir_path.glob("*.ets"):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                relative_path = str(file_path.relative_to(self.myapplication2_path))
                                files_content[relative_path] = f.read()
                        except Exception as e:
                            logger.warning(f"读取代码文件失败 {file_path}: {e}")
            
            logger.info(f"成功读取 {len(files_content)} 个项目文件")
            return files_content
            
        except Exception as e:
            logger.error(f"读取项目文件失败: {e}")
            return {}
    
    def _get_project_context_for_llm(self) -> str:
        """为LLM提供项目上下文信息"""
        try:
            project_files = self._read_project_files_content()
            
            if not project_files:
                return "项目文件读取失败，无法提供项目上下文"
            
            context_parts = []
            context_parts.append("=== 项目文件内容 ===")
            
            # 重要文件优先显示
            priority_files = [
                "entry/src/main/ets/pages/Index.ets",
                "entry/src/main/module.json5",
                "entry/build-profile.json5"
            ]
            
            for file_path in priority_files:
                if file_path in project_files:
                    content = project_files[file_path]
                    context_parts.append(f"\n--- {file_path} ---")
                    context_parts.append(content[:1000])  # 限制长度
            
            # 其他文件
            for file_path, content in project_files.items():
                if file_path not in priority_files:
                    context_parts.append(f"\n--- {file_path} ---")
                    context_parts.append(content[:500])  # 限制长度
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"生成项目上下文失败: {e}")
            return "项目上下文生成失败"
    
    def _scan_existing_files(self) -> str:
        """扫描存在的文件并返回结构信息"""
        try:
            existing_files = []
            
            # 扫描主要目录
            main_dirs = [
                "entry/src/main/ets/pages",
                "entry/src/main/ets/services", 
                "entry/src/main/ets/entryability",
                "entry/src/main/resources/base/element"
            ]
            
            for dir_path in main_dirs:
                full_path = self.myapplication2_path / dir_path
                if full_path.exists():
                    files = list(full_path.glob("*"))
                    if files:
                        existing_files.append(f"  {dir_path}/: {', '.join([f.name for f in files if f.is_file()])}")
            
            return "\n".join(existing_files) if existing_files else "未找到现有文件"
            
        except Exception as e:
            logger.error(f"扫描现有文件失败: {e}")
            return "无法扫描现有文件"
    
    def _scan_existing_files_with_content(self) -> str:
        """扫描存在的文件并返回结构信息以及关键文件内容"""
        try:
            result = []
            
            # 扫描主要目录
            main_dirs = [
                "entry/src/main/ets/pages",
                "entry/src/main/ets/services", 
                "entry/src/main/ets/entryability",
                "entry/src/main/resources/base/element"
            ]
            
            files_found = 0
            for dir_path in main_dirs:
                full_path = self.myapplication2_path / dir_path
                if full_path.exists():
                    files = list(full_path.glob("*"))
                    file_names = [f.name for f in files if f.is_file()]
                    if file_names:
                        result.append(f"📁 {dir_path}/: {', '.join(file_names)}")
                        files_found += len(file_names)
            
            # 读取关键配置文件内容
            key_files = [
                ("entry/src/main/module.json5", "模块配置"),
                ("entry/src/main/resources/base/element/string.json", "字符串资源"),
                ("entry/src/main/resources/base/element/color.json", "颜色资源"),
                ("AppScope/app.json5", "应用配置")
            ]
            
            for file_path, description in key_files:
                full_path = self.myapplication2_path / file_path
                if full_path.exists():
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 限制内容长度以避免过长
                            if len(content) > 500:
                                content = content[:500] + "..."
                            result.append(f"📄 {description} ({file_path}):")
                            result.append(f"```json\n{content}\n```")
                    except Exception as e:
                        result.append(f"📄 {description} ({file_path}): 读取失败 - {e}")
            
            # 扫描现有的.ets文件并读取简要内容
            pages_dir = self.myapplication2_path / "entry/src/main/ets/pages"
            if pages_dir.exists():
                ets_files = list(pages_dir.glob("*.ets"))
                if ets_files:
                    result.append(f"\n📝 现有页面文件内容预览:")
                    for ets_file in ets_files[:3]:  # 最多显示3个文件
                        try:
                            with open(ets_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # 提取关键信息：@Entry, @Component, export等
                                lines = content.split('\n')
                                key_lines = []
                                for line in lines[:20]:  # 只看前20行
                                    if any(keyword in line for keyword in ['@Entry', '@Component', 'export', 'import', 'struct']):
                                        key_lines.append(line.strip())
                                if key_lines:
                                    result.append(f"  📄 {ets_file.name}:")
                                    result.append(f"    {'; '.join(key_lines[:5])}")
                        except Exception as e:
                            result.append(f"  📄 {ets_file.name}: 读取失败 - {e}")
            
            summary = f"总计发现 {files_found} 个文件"
            if result:
                return f"{summary}\n\n" + "\n".join(result)
            else:
                return "未找到现有文件"
            
        except Exception as e:
            logger.error(f"扫描文件内容失败: {e}")
            return "无法扫描文件内容"
    
    def _validate_and_fix_file_paths(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并修复文件路径，单个文件生成模式下强制只返回Index.ets文件
        """
        try:
            # 单个文件生成模式：强制只返回Index.ets文件
            fixed_files = [{
                "path": "MyApplication2/entry/src/main/ets/pages/Index.ets",
                "type": "page",
                "purpose": "应用入口页面组件",
                "content_outline": "包含@Entry @Component装饰器、页面状态管理、UI显示组件",
                "key_components": analysis_data.get("planned_files", [{}])[0].get("key_components", []),
                "dependencies": analysis_data.get("planned_files", [{}])[0].get("dependencies", [])
            }]
            
            logger.info(f"单个文件生成模式: 强制设置为Index.ets文件")
            logger.info(f"目标文件路径: MyApplication2/entry/src/main/ets/pages/Index.ets")
            
            # 更新分析数据
            analysis_data["planned_files"] = fixed_files
            
            return analysis_data
            
        except Exception as e:
            logger.error(f"验证文件路径失败: {e}")
            return analysis_data
    
    def _fix_file_path(self, original_path: str, file_type: str) -> str:
        """
        修复单个文件路径，确保在正确的MyApplication2目录中
        """
        try:
            # 如果已经以MyApplication2开头，检查路径是否正确
            if original_path.startswith("MyApplication2/"):
                # 检查路径是否符合规范
                if self._is_valid_harmonyos_path(original_path, file_type):
                    return original_path
            
            # 提取文件名
            import os
            filename = os.path.basename(original_path) if original_path else "GeneratedFile.ets"
            if not filename.endswith(".ets") and file_type == "arkts":
                filename = filename + ".ets"
            elif not filename.endswith(".json") and file_type == "json":
                filename = filename + ".json"
            
            # 根据文件类型决定正确路径
            if file_type == "arkts":
                if "Page" in filename or "page" in filename.lower():
                    return f"MyApplication2/entry/src/main/ets/pages/{filename}"
                elif "Service" in filename or "service" in filename.lower():
                    return f"MyApplication2/entry/src/main/ets/services/{filename}"
                elif "Ability" in filename:
                    return f"MyApplication2/entry/src/main/ets/entryability/{filename}"
                else:
                    # 默认放在pages目录
                    return f"MyApplication2/entry/src/main/ets/pages/{filename}"
            elif file_type == "json":
                return f"MyApplication2/entry/src/main/resources/base/element/{filename}"
            else:
                # 默认放在pages目录
                return f"MyApplication2/entry/src/main/ets/pages/{filename}"
                
        except Exception as e:
            logger.error(f"修复文件路径失败: {e}")
            return f"MyApplication2/entry/src/main/ets/pages/GeneratedFile.ets"
    
    def _is_valid_harmonyos_path(self, path: str, file_type: str) -> bool:
        """
        检查路径是否符合HarmonyOS项目规范
        """
        valid_patterns = [
            "MyApplication2/entry/src/main/ets/pages/",
            "MyApplication2/entry/src/main/ets/services/",
            "MyApplication2/entry/src/main/ets/entryability/",
            "MyApplication2/entry/src/main/ets/entrybackupability/",
            "MyApplication2/entry/src/main/resources/base/element/"
        ]
        
        return any(path.startswith(pattern) for pattern in valid_patterns)
    
    # ==================== 错误分析方法 ====================
    
    async def _analyze_errors_and_plan_fixes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """分析错误并制定修复策略"""
        try:
            current_errors = params.get("current_errors", [])
            affected_files = params.get("affected_files", [])
            error_types = params.get("error_types", [])
            fix_attempt = params.get("fix_attempt", 0)
            existing_files = params.get("existing_files", [])
            
            logger.info(f"错误分析开始: {len(current_errors)} 个错误")
            logger.info(f"受影响文件: {affected_files}")
            logger.info(f"错误类型: {error_types}")
            logger.info(f"修复尝试次数: {fix_attempt}")
            
            if not current_errors:
                return {
                    "success": True,
                    "message": "没有错误需要分析",
                    "fix_strategies": []
                }
            
            # 读取项目结构
            project_structure = self._read_myapplication2_structure()
            
            # 构建错误分析提示词
            error_summary = "\n".join([
                f"错误{i+1}: 文件={error.get('file_path', 'unknown')}, 类型={error.get('error_type', 'unknown')}, 消息={error.get('message', '')[:100]}"
                for i, error in enumerate(current_errors[:5])  # 只显示前5个错误
            ])
            
            existing_files_info = "\n".join([
                f"文件{i+1}: {file_info.get('path', 'unknown')} (状态: {file_info.get('status', 'unknown')})"
                for i, file_info in enumerate(existing_files[:5])  # 只显示前5个文件
            ])
            
            analysis_prompt = f"""作为鸿蒙应用项目管理专家，请分析以下编译和静态检查错误，并制定修复策略。

项目结构信息:
{project_structure}

当前错误信息:
{error_summary}

现有文件信息:
{existing_files_info}

修复尝试次数: {fix_attempt}

请执行以下分析：
1. 错误分类：将错误按类型和文件分组
2. 根因分析：分析错误的根本原因
3. 修复策略：制定具体的修复策略
4. 文件定位：确定需要修复的准确文件路径

**重要要求：**
- 所有文件路径必须以"MyApplication2/"开头
- 确保文件路径准确，避免生成在错误位置
- 优先修复编译错误，再处理静态检查错误
- 提供具体的修复指导

输出格式(JSON)：
{{
  "error_analysis": {{
    "total_errors": {len(current_errors)},
    "error_groups": [
      {{
        "file_path": "MyApplication2/entry/src/main/ets/pages/LoginPage.ets",
        "error_type": "compile",
        "error_count": 2,
        "priority": "high"
      }}
    ],
    "root_causes": ["原因1", "原因2"]
  }},
  "fix_strategies": [
    {{
      "target_file": "MyApplication2/entry/src/main/ets/pages/LoginPage.ets",
      "strategy": "修复导入语句错误",
      "specific_actions": ["修改导入路径", "添加缺失的导入"],
      "priority": "high"
    }}
  ]
}}"""

            if self.llm:
                messages = [{"role": "user", "content": analysis_prompt}]
                response = self.llm.chat(messages)
                content = self.llm.remove_think(response.content)
                
                # 尝试解析JSON
                import json
                try:
                    analysis_data = json.loads(content)
                    # 验证和修复文件路径
                    analysis_data = self._validate_fix_strategies(analysis_data)
                except:
                    # 如果解析失败，生成基础分析
                    analysis_data = self._generate_basic_error_analysis(current_errors, affected_files)
            else:
                # 没有LLM时的备用分析
                analysis_data = self._generate_basic_error_analysis(current_errors, affected_files)
            
            logger.info(f"错误分析完成，生成了{len(analysis_data.get('fix_strategies', []))}个修复策略")
            
            return {
                "success": True,
                "analysis": analysis_data,
                "fix_strategies": analysis_data.get("fix_strategies", []),
                "error_analysis": analysis_data.get("error_analysis", {}),
                "project_path": "MyApplication2"
            }
                
        except Exception as e:
            logger.error(f"错误分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "fix_strategies": []
            }
    
    def _validate_fix_strategies(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证和修复策略中的文件路径"""
        try:
            fix_strategies = analysis_data.get("fix_strategies", [])
            validated_strategies = []
            
            for strategy in fix_strategies:
                target_file = strategy.get("target_file", "")
                
                # 验证和修复文件路径
                if target_file and not target_file.startswith("MyApplication2/"):
                    # 尝试修复路径
                    if target_file.endswith(".ets"):
                        if "Page" in target_file or "page" in target_file.lower():
                            target_file = f"MyApplication2/entry/src/main/ets/pages/{os.path.basename(target_file)}"
                        else:
                            target_file = f"MyApplication2/entry/src/main/ets/services/{os.path.basename(target_file)}"
                    elif target_file.endswith(".json"):
                        target_file = f"MyApplication2/entry/src/main/resources/base/element/{os.path.basename(target_file)}"
                    
                    logger.info(f"修复策略文件路径: {strategy.get('target_file', '')} -> {target_file}")
                    strategy["target_file"] = target_file
                
                validated_strategies.append(strategy)
            
            analysis_data["fix_strategies"] = validated_strategies
            return analysis_data
            
        except Exception as e:
            logger.error(f"验证修复策略失败: {e}")
            return analysis_data
    
    def _generate_basic_error_analysis(self, current_errors: List[Dict], affected_files: List[str]) -> Dict[str, Any]:
        """生成基础错误分析（备用方案）"""
        try:
            # 按文件分组错误
            error_groups = {}
            for error in current_errors:
                file_path = error.get("file_path", "unknown")
                error_type = error.get("error_type", "unknown")
                
                # 修复文件路径
                if file_path == "unknown" or not file_path.startswith("MyApplication2/"):
                    file_path = "MyApplication2/entry/src/main/ets/pages/Index.ets"
                
                if file_path not in error_groups:
                    error_groups[file_path] = {"compile": 0, "lint": 0}
                
                error_groups[file_path][error_type] = error_groups[file_path].get(error_type, 0) + 1
            
            # 生成修复策略
            fix_strategies = []
            for file_path, error_counts in error_groups.items():
                total_errors = sum(error_counts.values())
                strategy = {
                    "target_file": file_path,
                    "strategy": f"修复{file_path}中的{total_errors}个错误",
                    "specific_actions": ["检查语法错误", "修复导入语句", "验证类型定义"],
                    "priority": "high" if error_counts.get("compile", 0) > 0 else "medium"
                }
                fix_strategies.append(strategy)
            
            return {
                "error_analysis": {
                    "total_errors": len(current_errors),
                    "error_groups": [
                        {
                            "file_path": file_path,
                            "error_type": "mixed",
                            "error_count": sum(counts.values()),
                            "priority": "high"
                        }
                        for file_path, counts in error_groups.items()
                    ],
                    "root_causes": ["语法错误", "导入问题", "类型定义问题"]
                },
                "fix_strategies": fix_strategies
            }
            
        except Exception as e:
            logger.error(f"生成基础错误分析失败: {e}")
            return {
                "error_analysis": {"total_errors": len(current_errors)},
                "fix_strategies": []
            }
    
    async def _analyze_errors_and_generate_keywords(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """分析错误信息并生成搜索关键词"""
        try:
            errors = params.get("errors", [])
            original_requirement = params.get("original_requirement", "")
            project_path = params.get("project_path", "MyApplication2")
            
            logger.info(f"开始分析错误并生成搜索关键词: {len(errors)} 个错误")
            
            if not errors:
                return {
                    "success": True,
                    "search_keywords": ["鸿蒙开发", "ArkTS", "HarmonyOS"],
                    "error_analysis": "未检测到具体错误"
                }
            
            # 将所有错误信息转换为字符串
            error_text = "\n".join([str(error) for error in errors])
            
            prompt = f"""作为鸿蒙开发专家，请分析以下错误信息并生成5-8个搜索关键词，用于搜索解决方案。

原始需求: {original_requirement}
项目: {project_path}

错误信息:
{error_text}

请生成能帮助修复这些错误的搜索关键词，重点关注:
1. 鸿蒙/ArkTS相关的解决方案
2. 具体的错误类型和修复方法
3. 相关的技术文档和最佳实践

直接返回关键词列表，用逗号分隔，例如:
ArkTS语法错误修复, 鸿蒙导入模块问题, HarmonyOS编译错误解决, 鸿蒙组件装饰器用法"""

            if self.llm:
                messages = [{"role": "user", "content": prompt}]
                response = self.llm.chat(messages)
                content = self.llm.remove_think(response.content).strip()
                
                # 解析关键词
                keywords = [kw.strip() for kw in content.split(',') if kw.strip()]
                
                if not keywords:
                    keywords = ["鸿蒙开发问题", "ArkTS错误修复", "HarmonyOS代码问题"]
                
                logger.info(f"生成搜索关键词: {keywords}")
                
                return {
                    "success": True,
                    "search_keywords": keywords,
                    "error_analysis": f"分析了 {len(errors)} 个错误",
                    "fix_strategy": "根据搜索结果制定修复方案"
                }
            else:
                return {
                    "success": False,
                    "error": "LLM未初始化"
                }
                
        except Exception as e:
            logger.error(f"分析错误并生成搜索关键词失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }