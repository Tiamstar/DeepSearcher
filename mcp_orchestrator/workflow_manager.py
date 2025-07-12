#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Manager
华为多Agent协作系统 - 工作流管理器
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import uuid
import re
from copy import deepcopy


class WorkflowStep:
    """工作流步骤"""
    
    def __init__(self, step_config: Dict[str, Any]):
        self.agent = step_config.get("agent")
        self.method = step_config.get("method")
        self.params = step_config.get("params", {})
        self.output_mapping = step_config.get("output_mapping", {})
        self.condition = step_config.get("condition")
        self.retry_count = step_config.get("retry_count", 3)
        self.timeout = step_config.get("timeout", 60)
        self.parallel = step_config.get("parallel", False)
    
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """判断是否应该执行此步骤"""
        if not self.condition:
            return True
        
        # 简单的条件评估
        try:
            # 替换上下文变量
            condition = self._replace_variables(self.condition, context)
            return eval(condition)
        except:
            return True
    
    def _replace_variables(self, text: str, context: Dict[str, Any]) -> str:
        """替换文本中的变量"""
        if isinstance(text, str):
            pattern = r'\{([^}]+)\}'
            
            def replace_var(match):
                var_name = match.group(1)
                return str(context.get(var_name, match.group(0)))
            
            return re.sub(pattern, replace_var, text)
        return text


class Workflow:
    """工作流定义"""
    
    def __init__(self, workflow_config: Dict[str, Any]):
        self.name = workflow_config.get("name")
        self.description = workflow_config.get("description", "")
        self.version = workflow_config.get("version", "1.0")
        self.timeout = workflow_config.get("timeout", 300)  # 5分钟默认超时
        
        # 解析步骤
        self.steps = []
        for step_config in workflow_config.get("steps", []):
            self.steps.append(WorkflowStep(step_config))
        
        # 错误处理配置
        self.error_handling = workflow_config.get("error_handling", {
            "on_error": "stop",  # stop, continue, retry
            "max_retries": 3
        })
    
    def get_required_params(self) -> List[str]:
        """获取工作流所需的参数"""
        required_params = set()
        
        for step in self.steps:
            # 从参数中提取变量
            params_str = str(step.params)
            pattern = r'\{([^}]+)\}'
            matches = re.findall(pattern, params_str)
            required_params.update(matches)
        
        return list(required_params)


class WorkflowExecution:
    """工作流执行实例"""
    
    def __init__(self, workflow: Workflow, session_id: str, initial_params: Dict[str, Any]):
        self.workflow = workflow
        self.session_id = session_id
        self.execution_id = str(uuid.uuid4())
        self.initial_params = initial_params
        
        # 执行状态
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.current_step = 0
        self.context = deepcopy(initial_params)
        self.results = {}
        self.errors = []
        
        # 时间记录
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        
        # 日志
        self.logger = logging.getLogger(f"workflow.{workflow.name}.{self.execution_id[:8]}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取执行状态"""
        return {
            "execution_id": self.execution_id,
            "session_id": self.session_id,
            "workflow_name": self.workflow.name,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": len(self.workflow.steps),
            "progress": self.current_step / len(self.workflow.steps) if self.workflow.steps else 0,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors,
            "context": self.context
        }


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.logger = logging.getLogger("workflow.manager")
        
        # 执行器回调
        self.agent_executor: Optional[Callable] = None
    
    async def initialize(self):
        """初始化工作流管理器"""
        self.logger.info("工作流管理器初始化完成")
    
    def register_workflow(self, workflow_config: Dict[str, Any]):
        """注册工作流"""
        workflow = Workflow(workflow_config)
        self.workflows[workflow.name] = workflow
        self.logger.info(f"注册工作流: {workflow.name}")
    
    def set_agent_executor(self, executor: Callable):
        """设置Agent执行器"""
        self.agent_executor = executor
    
    async def execute_workflow(self, workflow_name: str, session_id: str, params: Dict[str, Any]) -> str:
        """执行工作流"""
        if workflow_name not in self.workflows:
            raise ValueError(f"工作流不存在: {workflow_name}")
        
        workflow = self.workflows[workflow_name]
        execution = WorkflowExecution(workflow, session_id, params)
        
        self.executions[execution.execution_id] = execution
        
        # 异步执行
        asyncio.create_task(self._execute_workflow_async(execution))
        
        return execution.execution_id
    
    async def _execute_workflow_async(self, execution: WorkflowExecution):
        """异步执行工作流"""
        try:
            execution.status = "running"
            execution.started_at = datetime.now()
            
            self.logger.info(f"开始执行工作流: {execution.workflow.name} (ID: {execution.execution_id})")
            
            # 执行步骤
            for i, step in enumerate(execution.workflow.steps):
                execution.current_step = i
                
                # 检查是否应该执行
                if not step.should_execute(execution.context):
                    self.logger.info(f"跳过步骤 {i}: 条件不满足")
                    continue
                
                try:
                    # 执行步骤
                    result = await self._execute_step(step, execution)
                    
                    # 更新上下文
                    if step.output_mapping:
                        for output_key, context_key in step.output_mapping.items():
                            if output_key in result:
                                execution.context[context_key] = result[output_key]
                    
                    execution.results[f"step_{i}"] = result
                    
                except Exception as e:
                    error_msg = f"步骤 {i} 执行失败: {str(e)}"
                    self.logger.error(error_msg)
                    execution.errors.append({
                        "step": i,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 根据错误处理策略决定是否继续
                    if execution.workflow.error_handling.get("on_error") == "stop":
                        execution.status = "failed"
                        return
            
            execution.status = "completed"
            execution.completed_at = datetime.now()
            execution.current_step = len(execution.workflow.steps)
            
            self.logger.info(f"工作流执行完成: {execution.workflow.name}")
            
        except Exception as e:
            execution.status = "failed"
            execution.completed_at = datetime.now()
            execution.errors.append({
                "step": "workflow",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            self.logger.error(f"工作流执行失败: {str(e)}")
    
    async def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """执行单个步骤"""
        if not self.agent_executor:
            raise RuntimeError("Agent执行器未设置")
        
        # 替换参数中的变量
        resolved_params = self._resolve_params(step.params, execution.context)
        
        self.logger.info(f"执行步骤: {step.agent}.{step.method}")
        
        # 执行Agent方法
        result = await self.agent_executor(step.agent, step.method, resolved_params)
        
        return result
    
    def _resolve_params(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """解析参数中的变量"""
        resolved = {}
        
        for key, value in params.items():
            resolved[key] = self._resolve_value(value, context)
        
        return resolved
    
    def _resolve_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """解析单个值中的变量"""
        if isinstance(value, str):
            # 检查是否是完整的变量替换（如 "{variable_name}"）
            if value.startswith('{') and value.endswith('}') and value.count('{') == 1:
                var_name = value[1:-1]  # 去掉大括号
                if var_name in context:
                    # 直接返回上下文中的值，保持原始类型
                    return context[var_name]
                else:
                    # 变量不存在，返回原始字符串
                    return value
            else:
                # 部分变量替换，使用字符串替换
                pattern = r'\{([^}]+)\}'
                
                def replace_var(match):
                    var_name = match.group(1)
                    context_value = context.get(var_name)
                    if context_value is not None:
                        return str(context_value)
                    else:
                        return match.group(0)  # 保持原始占位符
                
                return re.sub(pattern, replace_var, value)
        
        elif isinstance(value, dict):
            return {k: self._resolve_value(v, context) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._resolve_value(item, context) for item in value]
        
        else:
            return value
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        if execution_id in self.executions:
            return self.executions[execution_id].get_status()
        return None
    
    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            if execution.status in ["pending", "running"]:
                execution.status = "cancelled"
                execution.completed_at = datetime.now()
                self.logger.info(f"取消工作流执行: {execution_id}")
                return True
        return False
    
    def get_workflow_info(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """获取工作流信息"""
        if workflow_name in self.workflows:
            workflow = self.workflows[workflow_name]
            return {
                "name": workflow.name,
                "description": workflow.description,
                "version": workflow.version,
                "timeout": workflow.timeout,
                "steps_count": len(workflow.steps),
                "required_params": workflow.get_required_params()
            }
        return None
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        return [self.get_workflow_info(name) for name in self.workflows.keys()]
    
    def list_executions(self, status_filter: str = None) -> List[Dict[str, Any]]:
        """列出执行实例"""
        executions = []
        for execution in self.executions.values():
            if status_filter is None or execution.status == status_filter:
                executions.append(execution.get_status())
        return executions
    
    async def cleanup_executions(self, max_age_hours: int = 24):
        """清理旧的执行记录"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for execution_id, execution in self.executions.items():
            if execution.created_at.timestamp() < cutoff_time and execution.status in ["completed", "failed", "cancelled"]:
                to_remove.append(execution_id)
        
        for execution_id in to_remove:
            del self.executions[execution_id]
        
        if to_remove:
            self.logger.info(f"清理了 {len(to_remove)} 个旧的执行记录") 