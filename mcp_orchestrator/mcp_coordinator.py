#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Coordinator
华为多Agent协作系统 - MCP协调器
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from mcp_agents.base import MCPAgent, MCPMessage, MCPProtocol
from mcp_agents.project_manager import ProjectManagerAgent
from mcp_agents.search import SearchAgent
from mcp_agents.code_generator import CodeGeneratorAgent
from mcp_agents.code_checker import CodeCheckerAgent
from mcp_agents.final_generator import FinalGeneratorAgent
from mcp_agents.harmonyos_compiler import HarmonyOSCompilerAgent

from .workflow_manager import WorkflowManager
from .harmonyos_workflow import HarmonyOSWorkflowManager
from .collaborative_workflow import CollaborativeWorkflowManager


class MCPCoordinator:
    """MCP协调器 - 管理多Agent协作"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agents: Dict[str, MCPAgent] = {}
        self.protocol = MCPProtocol()
        self.workflow_manager = WorkflowManager()
        self.harmonyos_workflow = HarmonyOSWorkflowManager(self)  # 旧的鸿蒙工作流管理器
        self.collaborative_workflow = CollaborativeWorkflowManager(self)  # 新的协作式工作流管理器
        self.logger = logging.getLogger("mcp.coordinator")
        
        # 会话管理
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "agent_usage": {},
            "workflow_usage": {},
            "start_time": datetime.now()
        }
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化协调器和所有Agent"""
        try:
            self.logger.info("开始初始化MCP协调器...")
            
            # 初始化各个Agent
            await self._initialize_agents()
            
            # 初始化工作流管理器
            await self.workflow_manager.initialize()
            
            # 设置Agent执行器
            self.workflow_manager.set_agent_executor(self._execute_agent_method)
            
            # 注册预定义工作流
            await self._register_workflows()
            
            self.logger.info("MCP协调器初始化完成")
            
            return {
                "coordinator_id": "mcp_coordinator",
                "agents": list(self.agents.keys()),
                "workflows": list(self.workflow_manager.workflows.keys()),
                "initialized_at": datetime.now().isoformat(),
                "status": "ready"
            }
            
        except Exception as e:
            self.logger.error(f"MCP协调器初始化失败: {str(e)}")
            raise
    
    async def _initialize_agents(self):
        """初始化所有Agent"""
        agent_configs = self.config.get("agents", {})
        
        # 创建配置加载器
        from shared.config_loader import ConfigLoader
        config_loader = ConfigLoader()
        
        # 初始化项目管理Agent
        pm_config = agent_configs.get("project_manager", {})
        # 从配置加载器获取LLM配置
        if "llm_config" not in pm_config or not pm_config["llm_config"]:
            pm_config["llm_config"] = config_loader.get_llm_config("project_manager")
        self.agents["project_manager"] = ProjectManagerAgent(pm_config)
        
        # 初始化搜索Agent
        search_config = agent_configs.get("search", {})
        # 搜索Agent可能有独立的配置文件，不需要特殊处理LLM配置
        self.agents["search"] = SearchAgent(search_config)
        
        # 初始化代码生成Agent
        cg_config = agent_configs.get("code_generator", {})
        # 从配置加载器获取LLM配置
        if "llm_config" not in cg_config or not cg_config["llm_config"]:
            cg_config["llm_config"] = config_loader.get_llm_config("code_generator")
        self.agents["code_generator"] = CodeGeneratorAgent(cg_config)
        
        # 初始化代码检查Agent
        cc_config = agent_configs.get("code_checker", {})
        self.agents["code_checker"] = CodeCheckerAgent("code_checker", cc_config)
        
        # 初始化最终代码生成Agent
        fg_config = agent_configs.get("final_generator", {})
        # 从配置加载器获取LLM配置
        if "llm_config" not in fg_config or not fg_config["llm_config"]:
            fg_config["llm_config"] = config_loader.get_llm_config("final_generator")
        self.agents["final_generator"] = FinalGeneratorAgent(fg_config)
        
        # 初始化HarmonyOS编译器Agent
        hc_config = agent_configs.get("harmonyos_compiler", {})
        self.agents["harmonyos_compiler"] = HarmonyOSCompilerAgent(hc_config)
        
        # 启动所有Agent
        for agent_id, agent in self.agents.items():
            try:
                await agent.start()  # 使用start方法而不是直接调用initialize
                self.logger.info(f"Agent {agent_id} 启动成功")
                self.stats["agent_usage"][agent_id] = 0
            except Exception as e:
                self.logger.error(f"Agent {agent_id} 启动失败: {str(e)}")
                raise
    
    async def _register_workflows(self):
        """注册预定义工作流"""
        # 完整代码生成工作流
        complete_workflow = {
            "name": "complete_code_generation",
            "description": "完整的代码生成流程",
            "steps": [
                {
                    "agent": "project_manager",
                    "method": "project.decompose",
                    "params": {
                        "requirement": "{user_input}",
                        "context": "{context}"
                    },
                    "output_mapping": {
                        "decomposed_tasks": "tasks",
                        "estimated_complexity": "complexity"
                    }
                },
                {
                    "agent": "search",
                    "method": "search.online",
                    "params": {
                        "query": "{user_input}",
                        "top_k": 5,
                        "context": {
                            "session_id": "{session_id}"
                        }
                    },
                    "output_mapping": {
                        "answer": "search_context",
                        "sources": "reference_sources"
                    }
                },
                {
                    "agent": "code_generator",
                    "method": "code.generate",
                    "params": {
                        "requirement": "{user_input}",
                        "context": "{search_context}",
                        "language": "{language}",
                        "framework": "{framework}"
                    },
                    "output_mapping": {
                        "generated_code": "initial_code"
                    }
                },
                {
                    "agent": "code_checker",
                    "method": "code.check.unified",
                    "params": {
                        "code": "{initial_code}",
                        "language": "{language}",
                        "review_type": "comprehensive",
                        "original_query": "{user_input}"
                    },
                    "output_mapping": {
                        "formatted_review_data": "code_review_result"
                    }
                },
                {
                    "agent": "final_generator",
                    "method": "code.finalize",
                    "params": {
                        "initial_code": "{initial_code}",
                        "review_result": "{code_review_result}",
                        "requirement": "{user_input}",
                        "language": "{language}"
                    },
                    "output_mapping": {
                        "code": "final_code"
                    }
                }
            ]
        }
        
        # 快速代码生成工作流
        quick_workflow = {
            "name": "quick_code_generation",
            "description": "快速代码生成流程",
            "steps": [
                {
                    "agent": "search",
                    "method": "search.local",
                    "params": {
                        "query": "{user_input}",
                        "top_k": 3
                    },
                    "output_mapping": {
                        "answer": "search_context"
                    }
                },
                {
                    "agent": "code_generator",
                    "method": "code.generate",
                    "params": {
                        "requirement": "{user_input}",
                        "context": "{search_context}",
                        "language": "{language}"
                    },
                    "output_mapping": {
                        "generated_code": "final_code"
                    }
                }
            ]
        }
        
        # 代码审查工作流
        review_workflow = {
            "name": "code_review_workflow",
            "description": "代码审查和优化流程",
            "steps": [
                {
                    "agent": "code_checker",
                    "method": "code.check.unified",
                    "params": {
                        "code": "{code}",
                        "language": "{language}",
                        "review_type": "{review_type}",
                        "original_query": "{description}"
                    },
                    "output_mapping": {
                        "review_report": "review_result"
                    }
                },
                {
                    "agent": "final_generator",
                    "method": "code.optimize",
                    "params": {
                        "code": "{code}",
                        "optimization_goals": ["{optimization_type}"],
                        "language": "{language}"
                    },
                    "output_mapping": {
                        "code": "final_code"
                    }
                }
            ]
        }
        
        # 注册工作流
        self.workflow_manager.register_workflow(complete_workflow)
        self.workflow_manager.register_workflow(quick_workflow)
        self.workflow_manager.register_workflow(review_workflow)
        
        self.logger.info("预定义工作流注册完成")
    
    async def _execute_agent_method(self, agent_id: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Agent方法 - 供工作流管理器调用"""
        if agent_id not in self.agents:
            raise ValueError(f"未知的Agent: {agent_id}")
        
        agent = self.agents[agent_id]
        
        # 输出Agent执行开始信息
        self.logger.info(f"🤖 开始执行Agent: {agent_id}")
        self.logger.info(f"   方法: {method}")
        self.logger.info(f"   参数键: {list(params.keys()) if params else '无'}")
        
        # 创建Agent请求消息
        agent_message = MCPMessage(
            id=str(uuid.uuid4()),
            method=method,
            params=params
        )
        
        try:
            # 执行请求
            response = await agent.handle_request(agent_message)
            
            # 输出Agent执行结果信息
            if response.error:
                self.logger.error(f"❌ Agent {agent_id} 执行失败: {response.error}")
                raise Exception(f"Agent {agent_id} 处理失败: {response.error}")
            else:
                self.logger.info(f"✅ Agent {agent_id} 执行成功")
                if response.result:
                    result_keys = list(response.result.keys()) if isinstance(response.result, dict) else "非字典结果"
                    self.logger.info(f"   返回结果键: {result_keys}")
                    
                    # 显示部分关键结果信息
                    if isinstance(response.result, dict):
                        if "success" in response.result:
                            self.logger.info(f"   成功标志: {response.result['success']}")
                        if "generated_files" in response.result:
                            files_count = len(response.result['generated_files'])
                            self.logger.info(f"   生成文件数: {files_count}")
                        if "errors" in response.result:
                            errors_count = len(response.result['errors'])
                            self.logger.info(f"   错误数量: {errors_count}")
                        if "answer" in response.result:
                            answer_preview = response.result['answer'][:100] + "..." if len(response.result['answer']) > 100 else response.result['answer']
                            self.logger.info(f"   答案预览: {answer_preview}")
            
            # 更新Agent使用统计
            self.stats["agent_usage"][agent_id] = self.stats["agent_usage"].get(agent_id, 0) + 1
            
            return response.result
            
        except Exception as e:
            self.logger.error(f"❌ Agent {agent_id} 执行异常: {str(e)}")
            # 更新Agent使用统计
            self.stats["agent_usage"][agent_id] = self.stats["agent_usage"].get(agent_id, 0) + 1
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理MCP请求"""
        self.stats["total_requests"] += 1
        
        try:
            method = message.method
            params = message.params or {}
            
            if method == "coordinator.execute_workflow":
                result = await self._execute_workflow(params)
                self.stats["successful_requests"] += 1
                return self.protocol.create_response(message.id, result)
            
            elif method == "coordinator.get_agents":
                result = await self._get_agents_info()
                self.stats["successful_requests"] += 1
                return self.protocol.create_response(message.id, result)
            
            elif method == "coordinator.get_workflows":
                result = await self._get_workflows_info()
                self.stats["successful_requests"] += 1
                return self.protocol.create_response(message.id, result)
            
            elif method == "coordinator.get_stats":
                result = self._get_stats()
                self.stats["successful_requests"] += 1
                return self.protocol.create_response(message.id, result)
            
            elif method.startswith("agent."):
                # 直接转发给特定Agent
                result = await self._forward_to_agent(method, params)
                self.stats["successful_requests"] += 1
                return self.protocol.create_response(message.id, result)
            
            else:
                self.stats["failed_requests"] += 1
                return self.protocol.handle_method_not_found(message.id, method)
                
        except Exception as e:
            self.logger.error(f"处理请求失败: {str(e)}")
            self.stats["failed_requests"] += 1
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _execute_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流"""
        workflow_name = params.get("workflow_name")
        workflow_params = params.get("params", {})
        session_id = params.get("session_id", str(uuid.uuid4()))
        
        if not workflow_name:
            raise ValueError("工作流名称不能为空")
        
        # 鸿蒙专用工作流
        if workflow_name == "harmonyos_complete_development":
            return await self._execute_harmonyos_workflow(workflow_params, session_id)
        
        # 创建会话
        self._create_session(session_id, workflow_name, workflow_params)
        
        try:
            # 执行原有工作流
            execution_id = await self.workflow_manager.execute_workflow(
                workflow_name, session_id, workflow_params
            )
            
            # 等待执行完成（简化版本，实际应该异步处理）
            execution_status = None
            max_wait_time = 300  # 5分钟超时
            wait_time = 0
            
            while wait_time < max_wait_time:
                execution_status = self.workflow_manager.get_execution_status(execution_id)
                if execution_status and execution_status["status"] in ["completed", "failed", "cancelled"]:
                    break
                await asyncio.sleep(1)
                wait_time += 1
            
            if not execution_status or execution_status["status"] == "running":
                raise TimeoutError("工作流执行超时")
            
            # 更新统计
            self.stats["workflow_usage"][workflow_name] = \
                self.stats["workflow_usage"].get(workflow_name, 0) + 1
            
            # 更新会话状态
            self.active_sessions[session_id]["status"] = execution_status["status"]
            self.active_sessions[session_id]["execution_id"] = execution_id
            self.active_sessions[session_id]["completed_at"] = datetime.now().isoformat()
            
            self.logger.info(f"工作流 {workflow_name} 执行完成，会话: {session_id}")
            
            return {
                "workflow_name": workflow_name,
                "session_id": session_id,
                "execution_id": execution_id,
                "status": execution_status["status"],
                "context": execution_status.get("context", {}),
                "errors": execution_status.get("errors", [])
            }
            
        except Exception as e:
            # 更新会话状态
            self.active_sessions[session_id]["status"] = "failed"
            self.active_sessions[session_id]["error"] = str(e)
            self.active_sessions[session_id]["failed_at"] = datetime.now().isoformat()
            
            self.logger.error(f"工作流 {workflow_name} 执行失败: {str(e)}")
            raise
    
    async def _forward_to_agent(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """转发请求给特定Agent"""
        # 解析Agent ID和方法
        parts = method.split(".", 2)
        if len(parts) < 3:
            raise ValueError(f"无效的Agent方法格式: {method}")
        
        agent_id = parts[1]
        agent_method = ".".join(parts[2:])
        
        return await self._execute_agent_method(agent_id, agent_method, params)
    
    def _create_session(self, session_id: str, workflow_name: str, params: Dict[str, Any]):
        """创建会话"""
        self.active_sessions[session_id] = {
            "workflow_name": workflow_name,
            "params": params,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "steps_completed": 0,
            "total_steps": 0
        }
    
    async def _get_agents_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        agents_info = {}
        
        for agent_id, agent in self.agents.items():
            agents_info[agent_id] = {
                "agent_id": agent.agent_id,
                "capabilities": agent.capabilities,
                "status": agent.status,
                "is_initialized": agent.is_initialized,
                "usage_count": self.stats["agent_usage"].get(agent_id, 0)
            }
        
        return {
            "total_agents": len(self.agents),
            "agents": agents_info
        }
    
    async def _get_workflows_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        workflows_info = {}
        
        for workflow_name in self.workflow_manager.workflows.keys():
            workflow_info = self.workflow_manager.get_workflow_info(workflow_name)
            if workflow_info:
                workflows_info[workflow_name] = {
                    **workflow_info,
                    "usage_count": self.stats["workflow_usage"].get(workflow_name, 0)
                }
        
        return {
            "total_workflows": len(self.workflow_manager.workflows),
            "workflows": workflows_info
        }
    
    def _get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = datetime.now() - self.stats["start_time"]
        
        return {
            **self.stats,
            "uptime_seconds": uptime.total_seconds(),
            "active_sessions": len(self.active_sessions),
            "success_rate": (
                self.stats["successful_requests"] / max(1, self.stats["total_requests"])
            ) * 100
        }
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        return self.active_sessions.get(session_id)
    
    async def cancel_session(self, session_id: str) -> bool:
        """取消会话"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            execution_id = session.get("execution_id")
            
            # 取消工作流执行
            if execution_id:
                self.workflow_manager.cancel_execution(execution_id)
            
            session["status"] = "cancelled"
            session["cancelled_at"] = datetime.now().isoformat()
            return True
        return False
    
    async def cleanup_sessions(self, max_age_hours: int = 24):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            created_at = datetime.fromisoformat(session["created_at"])
            age_hours = (current_time - created_at).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        # 清理工作流执行记录
        await self.workflow_manager.cleanup_executions(max_age_hours)
        
        self.logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
        return len(expired_sessions)
    
    async def shutdown(self):
        """关闭协调器"""
        self.logger.info("正在关闭MCP协调器...")
        
        # 取消所有活跃会话
        for session_id in list(self.active_sessions.keys()):
            await self.cancel_session(session_id)
        
        # 关闭所有Agent
        for agent_id, agent in self.agents.items():
            try:
                if hasattr(agent, 'shutdown'):
                    await agent.shutdown()
                self.logger.info(f"Agent {agent_id} 已关闭")
            except Exception as e:
                self.logger.error(f"关闭Agent {agent_id} 失败: {str(e)}")
        
        self.logger.info("MCP协调器已关闭")
    
    # ==================== 鸿蒙工作流专用方法 ====================
    
    async def _execute_harmonyos_workflow(self, workflow_params: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """执行鸿蒙专用工作流"""
        try:
            user_input = workflow_params.get("user_input", "")
            if not user_input:
                raise ValueError("用户需求不能为空")
            
            self.logger.info(f"开始执行鸿蒙工作流: {session_id}")
            
            # 使用新的协作式工作流管理器执行
            result = await self.collaborative_workflow.execute_harmonyos_workflow(user_input, session_id)
            
            # 更新统计
            self.stats["workflow_usage"]["harmonyos_complete_development"] = \
                self.stats["workflow_usage"].get("harmonyos_complete_development", 0) + 1
            
            self.logger.info(f"鸿蒙工作流执行完成: {session_id}")
            
            # 改进状态判断逻辑
            workflow_status = result.get("status", "failed")
            final_context = result.get("final_context", {})
            
            # 检查是否有未解决的错误
            has_unresolved_errors = False
            if final_context:
                lint_errors = len(final_context.get("lint_errors", []))
                compile_errors = len(final_context.get("compile_errors", []))
                has_unresolved_errors = (lint_errors > 0 or compile_errors > 0)
            
            # 根据实际情况确定最终状态
            if workflow_status == "success":
                if has_unresolved_errors:
                    final_status = "completed_with_errors"
                else:
                    final_status = "completed"
            else:
                final_status = "failed"
            
            self.logger.info(f"鸿蒙工作流状态确定: {workflow_status} -> {final_status}")
            self.logger.info(f"  lint_errors: {final_context.get('lint_errors', []) if final_context else 0}")
            self.logger.info(f"  compile_errors: {final_context.get('compile_errors', []) if final_context else 0}")
            self.logger.info(f"  has_unresolved_errors: {has_unresolved_errors}")
            
            return {
                "workflow_name": "harmonyos_complete_development",
                "session_id": session_id,
                "status": final_status,
                "result": result,
                "loop_count": result.get("total_iterations", 0),
                "total_errors_fixed": result.get("total_errors_fixed", 0),
                "has_unresolved_errors": has_unresolved_errors
            }
            
        except Exception as e:
            self.logger.error(f"鸿蒙工作流执行失败: {e}")
            raise
    
    async def get_harmonyos_workflow_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取鸿蒙工作流状态"""
        return self.harmonyos_workflow.get_workflow_status(session_id)
    
    async def cancel_harmonyos_workflow(self, session_id: str) -> bool:
        """取消鸿蒙工作流"""
        return await self.harmonyos_workflow.cancel_workflow(session_id)
    
    def get_active_harmonyos_workflows(self) -> List[str]:
        """获取活跃的鸿蒙工作流"""
        return self.harmonyos_workflow.get_active_workflows() 