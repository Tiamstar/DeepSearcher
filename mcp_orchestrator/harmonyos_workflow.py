#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Workflow Manager
鸿蒙工作流管理器 - 负责管理完整的鸿蒙代码生成工作流
"""

import logging
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .loop_manager import LoopManager, LoopStatus

logger = logging.getLogger(__name__)

class WorkflowStep(Enum):
    """工作流步骤枚举"""
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    SEARCH_INFORMATION = "search_information"
    GENERATE_CODE = "generate_code"
    STATIC_CHECK = "static_check"
    COMPILE_CHECK = "compile_check"
    FINALIZE = "finalize"

@dataclass
class WorkflowExecutionState:
    """工作流执行状态"""
    session_id: str
    user_input: str
    current_step: WorkflowStep
    context: Dict[str, Any]
    is_fixing: bool = False
    loop_count: int = 0
    max_loops: int = 3
    errors: List[Dict[str, Any]] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class HarmonyOSWorkflowManager:
    """
    鸿蒙工作流管理器
    负责：
    1. 管理完整的工作流程
    2. 协调各个Agent的调用
    3. 处理循环修复逻辑
    4. 管理工作流状态
    """
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.loop_manager = LoopManager(coordinator)
        self.active_workflows: Dict[str, WorkflowExecutionState] = {}
        
        # 工作流步骤配置
        self.workflow_steps = {
            WorkflowStep.ANALYZE_REQUIREMENTS: {
                "agent": "project_manager",
                "method": "project.analyze_harmonyos_requirements",
                "next_step": WorkflowStep.SEARCH_INFORMATION,
                "required_params": ["requirement", "project_path"],
                "can_skip": False
            },
            WorkflowStep.SEARCH_INFORMATION: {
                "agent": "search",
                "method": "search.harmonyos",
                "next_step": WorkflowStep.GENERATE_CODE,
                "required_params": ["query"],
                "can_skip": False
            },
            WorkflowStep.GENERATE_CODE: {
                "agent": "code_generator",
                "method": "code.generate_harmonyos",
                "next_step": WorkflowStep.STATIC_CHECK,
                "required_params": ["requirement", "context", "target_files"],
                "can_skip": False
            },
            WorkflowStep.STATIC_CHECK: {
                "agent": "code_checker",
                "method": "code.check.codelinter",
                "next_step": WorkflowStep.COMPILE_CHECK,
                "required_params": ["project_path"],
                "can_skip": False
            },
            WorkflowStep.COMPILE_CHECK: {
                "agent": "project_manager",
                "method": "project.hvigor_compile",
                "next_step": WorkflowStep.FINALIZE,
                "required_params": ["project_path"],
                "can_skip": False
            },
            WorkflowStep.FINALIZE: {
                "agent": "final_generator",
                "method": "code.finalize_harmonyos",
                "next_step": None,
                "required_params": [],
                "can_skip": False
            }
        }
    
    async def execute_harmonyos_workflow(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        执行完整的鸿蒙工作流
        
        Args:
            user_input: 用户需求输入
            session_id: 会话ID，如果不提供则自动生成
            
        Returns:
            工作流执行结果
        """
        try:
            # 初始化会话
            if not session_id:
                session_id = str(uuid.uuid4())
            
            logger.info(f"开始执行鸿蒙工作流: {session_id}")
            
            # 创建工作流状态
            state = WorkflowExecutionState(
                session_id=session_id,
                user_input=user_input,
                current_step=WorkflowStep.ANALYZE_REQUIREMENTS,
                context={
                    "user_input": user_input,
                    "session_id": session_id,
                    "project_path": "MyApplication2"
                }
            )
            self.active_workflows[session_id] = state
            
            # 启动循环管理器
            loop_context = await self.loop_manager.start_loop(session_id, user_input)
            
            # 执行工作流
            result = await self._execute_workflow_loop(state)
            
            # 完成循环
            final_result = await self.loop_manager.finalize_loop(session_id, result)
            
            # 清理工作流状态
            if session_id in self.active_workflows:
                del self.active_workflows[session_id]
            
            logger.info(f"鸿蒙工作流执行完成: {session_id}")
            
            return final_result
            
        except Exception as e:
            logger.error(f"鸿蒙工作流执行失败: {e}")
            # 清理状态
            if session_id and session_id in self.active_workflows:
                del self.active_workflows[session_id]
            raise
    
    async def _execute_workflow_loop(self, state: WorkflowExecutionState) -> Dict[str, Any]:
        """执行工作流循环"""
        while state.loop_count <= state.max_loops:
            try:
                # 执行当前工作流
                workflow_result = await self._execute_single_workflow(state)
                
                if workflow_result["success"]:
                    # 检查是否需要循环修复
                    need_loop, reason = await self._check_loop_condition(state, workflow_result)
                    
                    if not need_loop:
                        logger.info(f"工作流成功完成: {reason}")
                        return workflow_result
                    else:
                        # 准备下一次循环
                        await self._prepare_next_loop(state, workflow_result, reason)
                else:
                    logger.error(f"工作流执行失败: {workflow_result.get('error', 'Unknown error')}")
                    return workflow_result
                
            except Exception as e:
                logger.error(f"工作流循环执行失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "session_id": state.session_id,
                    "loop_count": state.loop_count
                }
        
        # 达到最大循环次数
        logger.warning(f"达到最大循环次数: {state.max_loops}")
        return {
            "success": False,
            "error": f"达到最大循环次数 ({state.max_loops})",
            "session_id": state.session_id,
            "loop_count": state.loop_count
        }
    
    async def _execute_single_workflow(self, state: WorkflowExecutionState) -> Dict[str, Any]:
        """执行单次完整工作流"""
        try:
            logger.info(f"开始执行工作流 (第{state.loop_count + 1}次): {state.session_id}")
            
            # 重置步骤到开始
            current_step = WorkflowStep.ANALYZE_REQUIREMENTS if not state.is_fixing else WorkflowStep.SEARCH_INFORMATION
            step_results = {}
            
            while current_step:
                # 执行当前步骤
                step_result = await self._execute_step(state, current_step)
                
                if not step_result["success"]:
                    return {
                        "success": False,
                        "error": f"步骤 {current_step.value} 执行失败: {step_result.get('error', 'Unknown')}",
                        "failed_step": current_step.value,
                        "step_results": step_results
                    }
                
                # 保存步骤结果
                step_results[current_step.value] = step_result["data"]
                
                # 更新上下文
                state.context.update(step_result["data"])
                
                # 更新循环管理器进度
                await self.loop_manager.update_loop_progress(
                    state.session_id, current_step.value, step_result["data"]
                )
                
                # 获取下一步
                current_step = self._get_next_step(current_step)
            
            return {
                "success": True,
                "session_id": state.session_id,
                "step_results": step_results,
                "final_context": state.context
            }
            
        except Exception as e:
            logger.error(f"单次工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": state.session_id
            }
    
    async def _execute_step(self, state: WorkflowExecutionState, step: WorkflowStep) -> Dict[str, Any]:
        """执行单个工作流步骤"""
        try:
            step_config = self.workflow_steps[step]
            agent_id = step_config["agent"]
            method = step_config["method"]
            
            logger.info(f"执行步骤: {step.value} -> {agent_id}.{method}")
            
            # 准备参数
            params = await self._prepare_step_params(state, step)
            
            # 调用Agent
            result = await self.coordinator._execute_agent_method(agent_id, method, params)
            
            return {
                "success": True,
                "step": step.value,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"步骤 {step.value} 执行失败: {e}")
            return {
                "success": False,
                "step": step.value,
                "error": str(e)
            }
    
    async def _prepare_step_params(self, state: WorkflowExecutionState, step: WorkflowStep) -> Dict[str, Any]:
        """为步骤准备参数"""
        base_params = {
            "session_id": state.session_id
        }
        
        if step == WorkflowStep.ANALYZE_REQUIREMENTS:
            base_params.update({
                "requirement": state.user_input,
                "project_path": "MyApplication2"
            })
            
        elif step == WorkflowStep.SEARCH_INFORMATION:
            if state.is_fixing:
                # 修复模式下的搜索参数
                fix_context = await self.loop_manager.generate_fix_context(state.session_id)
                base_params.update({
                    "query": f"修复鸿蒙代码错误: {state.user_input}",
                    "search_mode": "error_fixing",
                    "error_context": fix_context,
                    "focus_keywords": fix_context.get("search_keywords", []),
                    "fix_instructions": fix_context.get("fix_instructions", [])
                })
            else:
                # 正常模式搜索参数
                base_params.update({
                    "query": state.user_input,
                    "search_mode": "normal",
                    "focus_keywords": ["鸿蒙开发", "ArkTS", "HarmonyOS"]
                })
                
        elif step == WorkflowStep.GENERATE_CODE:
            base_params.update({
                "requirement": state.user_input,
                "context": state.context.get("search_context", ""),
                "target_files": state.context.get("target_files", []),
                "project_path": "MyApplication2",
                "is_fixing": state.is_fixing,
                "previous_errors": state.errors if state.is_fixing else []
            })
            
        elif step == WorkflowStep.STATIC_CHECK:
            base_params.update({
                "project_path": "MyApplication2"
            })
            
        elif step == WorkflowStep.COMPILE_CHECK:
            base_params.update({
                "project_path": "MyApplication2"
            })
            
        elif step == WorkflowStep.FINALIZE:
            base_params.update({
                "session_id": state.session_id,
                "generated_files": state.context.get("generated_files", []),
                "loop_count": state.loop_count,
                "final_context": state.context,
                "is_loop_completion": state.is_fixing
            })
        
        return base_params
    
    async def _check_loop_condition(self, state: WorkflowExecutionState, workflow_result: Dict[str, Any]) -> tuple[bool, str]:
        """检查是否需要循环修复"""
        try:
            step_results = workflow_result.get("step_results", {})
            
            # 获取编译和静态检查结果
            compile_result = step_results.get("compile_check", {})
            static_result = step_results.get("static_check", {})
            
            # 使用循环管理器判断
            should_continue, reason = await self.loop_manager.should_continue_loop(
                state.session_id, compile_result, static_result
            )
            
            return should_continue, reason
            
        except Exception as e:
            logger.error(f"检查循环条件失败: {e}")
            return False, f"循环条件检查失败: {str(e)}"
    
    async def _prepare_next_loop(self, state: WorkflowExecutionState, workflow_result: Dict[str, Any], reason: str):
        """准备下一次循环"""
        try:
            logger.info(f"准备下一次循环修复: {reason}")
            
            state.loop_count += 1
            state.is_fixing = True
            
            # 收集错误信息
            step_results = workflow_result.get("step_results", {})
            compile_result = step_results.get("compile_check", {})
            static_result = step_results.get("static_check", {})
            
            # 收集所有错误
            new_errors = []
            if compile_result.get("errors"):
                new_errors.extend(compile_result["errors"])
            if static_result.get("issues_found"):
                new_errors.extend(static_result["issues_found"])
            
            state.errors.extend(new_errors)
            
            logger.info(f"收集到 {len(new_errors)} 个新错误，开始下一轮修复")
            
        except Exception as e:
            logger.error(f"准备下一次循环失败: {e}")
            raise
    
    def _get_next_step(self, current_step: WorkflowStep) -> Optional[WorkflowStep]:
        """获取下一个步骤"""
        step_config = self.workflow_steps.get(current_step)
        if step_config:
            return step_config["next_step"]
        return None
    
    def get_workflow_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        state = self.active_workflows.get(session_id)
        if state:
            return {
                "session_id": session_id,
                "current_step": state.current_step.value,
                "is_fixing": state.is_fixing,
                "loop_count": state.loop_count,
                "max_loops": state.max_loops,
                "total_errors": len(state.errors),
                "created_at": state.created_at
            }
        
        # 检查循环管理器中的状态
        return self.loop_manager.get_loop_status(session_id)
    
    def get_active_workflows(self) -> List[str]:
        """获取活跃工作流列表"""
        return list(self.active_workflows.keys())
    
    async def cancel_workflow(self, session_id: str) -> bool:
        """取消工作流"""
        try:
            cancelled = False
            
            # 取消工作流状态
            if session_id in self.active_workflows:
                del self.active_workflows[session_id]
                cancelled = True
            
            # 取消循环管理器中的循环
            loop_cancelled = await self.loop_manager.cancel_loop(session_id)
            
            if cancelled or loop_cancelled:
                logger.info(f"工作流已取消: {session_id}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"取消工作流失败: {e}")
            return False