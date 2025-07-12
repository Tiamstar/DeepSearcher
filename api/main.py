#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Main Application
华为多Agent协作系统 - REST API接口
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from mcp_orchestrator.mcp_coordinator import MCPCoordinator
from mcp_agents.base import MCPMessage
from shared.config_loader import ConfigLoader

# 确保加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api.main")

# 全局协调器实例
coordinator: Optional[MCPCoordinator] = None


# Pydantic模型定义
class WorkflowRequest(BaseModel):
    """工作流执行请求"""
    workflow_name: str = Field(..., description="工作流名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="工作流参数")
    session_id: Optional[str] = Field(None, description="会话ID")


class AgentRequest(BaseModel):
    """Agent方法调用请求"""
    method: str = Field(..., description="Agent方法")
    params: Dict[str, Any] = Field(default_factory=dict, description="方法参数")


class CodeGenerationRequest(BaseModel):
    """代码生成请求"""
    user_input: str = Field(..., description="用户需求描述")
    language: str = Field(default="python", description="编程语言")
    framework: Optional[str] = Field(None, description="框架")
    context: Optional[str] = Field(None, description="上下文信息")
    workflow_type: str = Field(default="complete", description="工作流类型: complete, quick")


class CodeReviewRequest(BaseModel):
    """代码审查请求"""
    code: str = Field(..., description="待审查的代码")
    language: str = Field(..., description="编程语言")
    review_type: str = Field(default="comprehensive", description="审查类型")
    description: Optional[str] = Field(None, description="代码描述")
    optimization_type: str = Field(default="quality", description="优化类型")


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global coordinator
    
    # 启动时初始化
    try:
        logger.info("正在启动MCP协调器...")
        
        # 使用新的统一配置系统
        config_loader = ConfigLoader()
        config = config_loader.get_unified_config()
        
        # 如果配置为空，使用默认配置
        if not config:
            logger.warning("配置为空，使用默认配置")
            config = {
                "project": {
                    "name": "华为多Agent协作系统",
                    "version": "2.0.0"
                },
                "mcp": {
                    "protocol_version": "2024-11-05",
                    "timeout": 300,
                    "max_concurrent_requests": 10
                },
                "agents": {
                    "project_manager": {
                        "enabled": True,
                        "port": 8002
                    },
                    "search": {
                        "enabled": True,
                        "port": 8001
                    },
                    "code_generator": {
                        "enabled": True,
                        "port": 8003
                    },
                    "code_checker": {
                        "enabled": True,
                        "port": 8004
                    },
                    "final_generator": {
                        "enabled": True,
                        "port": 8005
                    }
                }
            }
        
        # 确保有必要的配置节
        if "mcp" not in config:
            config["mcp"] = {
                "protocol_version": "2024-11-05",
                "timeout": 300,
                "max_concurrent_requests": 10
            }
        
        if "agents" not in config:
            config["agents"] = {
                "project_manager": {"enabled": True, "port": 8002},
                "search": {"enabled": True, "port": 8001},
                "code_generator": {"enabled": True, "port": 8003},
                "code_checker": {"enabled": True, "port": 8004},
                "final_generator": {"enabled": True, "port": 8005}
            }
        
        logger.info("✅ 配置加载成功")
        logger.info(f"📋 项目: {config.get('project', {}).get('name', '未知')}")
        logger.info(f"🔌 MCP协议版本: {config.get('mcp', {}).get('protocol_version', '未知')}")
        
        # 记录启用的Agent
        enabled_agents = []
        for agent_name, agent_config in config.get("agents", {}).items():
            if agent_config.get("enabled", False):
                enabled_agents.append(f"{agent_name}:{agent_config.get('port', 'unknown')}")
        logger.info(f"🤖 启用的Agent: {', '.join(enabled_agents)}")
        
        coordinator = MCPCoordinator(config)
        await coordinator.initialize()
        
        logger.info("✅ MCP协调器启动成功")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 启动失败: {str(e)}")
        logger.error(f"错误详情: {type(e).__name__}: {e}")
        raise
    
    finally:
        # 关闭时清理
        if coordinator:
            logger.info("正在关闭MCP协调器...")
            await coordinator.shutdown()
            logger.info("MCP协调器已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="华为多Agent协作系统",
    description="基于MCP规范的多Agent代码生成系统",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API路由定义
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "华为多Agent协作系统 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    return {
        "status": "healthy",
        "timestamp": coordinator.stats["start_time"].isoformat(),
        "agents_count": len(coordinator.agents),
        "workflows_count": len(coordinator.workflow_manager.workflows)
    }


@app.post("/api/v1/generate-code")
async def generate_code(request: CodeGenerationRequest):
    """生成代码"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        # 选择工作流
        workflow_name = "complete_code_generation" if request.workflow_type == "complete" else "quick_code_generation"
        
        # 构建参数
        params = {
            "user_input": request.user_input,
            "language": request.language,
            "context": request.context or ""
        }
        
        if request.framework:
            params["framework"] = request.framework
        
        # 执行工作流
        workflow_request = {
            "workflow_name": workflow_name,
            "params": params
        }
        
        message = MCPMessage(
            method="coordinator.execute_workflow",
            params=workflow_request
        )
        
        response = await coordinator.handle_request(message)
        
        if response.error:
            raise HTTPException(status_code=500, detail=response.error)
        
        return response.result
        
    except Exception as e:
        logger.error(f"代码生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/review-code")
async def review_code(request: CodeReviewRequest):
    """审查代码"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        # 构建参数
        params = {
            "code": request.code,
            "language": request.language,
            "review_type": request.review_type,
            "description": request.description or "",
            "optimization_type": request.optimization_type
        }
        
        # 执行代码审查工作流
        workflow_request = {
            "workflow_name": "code_review_workflow",
            "params": params
        }
        
        message = MCPMessage(
            method="coordinator.execute_workflow",
            params=workflow_request
        )
        
        response = await coordinator.handle_request(message)
        
        if response.error:
            raise HTTPException(status_code=500, detail=response.error)
        
        return response.result
        
    except Exception as e:
        logger.error(f"代码审查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/execute-workflow")
async def execute_workflow(request: WorkflowRequest):
    """执行工作流"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        message = MCPMessage(
            method="coordinator.execute_workflow",
            params=request.dict()
        )
        
        response = await coordinator.handle_request(message)
        
        if response.error:
            raise HTTPException(status_code=500, detail=response.error)
        
        return response.result
        
    except Exception as e:
        logger.error(f"工作流执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/agent/{agent_id}")
async def call_agent(agent_id: str, request: AgentRequest):
    """调用特定Agent"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        method = f"agent.{agent_id}.{request.method}"
        
        message = MCPMessage(
            method=method,
            params=request.params
        )
        
        response = await coordinator.handle_request(message)
        
        if response.error:
            raise HTTPException(status_code=500, detail=response.error)
        
        return response.result
        
    except Exception as e:
        logger.error(f"Agent调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents")
async def get_agents():
    """获取所有Agent信息"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        message = MCPMessage(method="coordinator.get_agents")
        response = await coordinator.handle_request(message)
        
        if response.error:
            raise HTTPException(status_code=500, detail=response.error)
        
        return response.result
        
    except Exception as e:
        logger.error(f"获取Agent信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows")
async def get_workflows():
    """获取所有工作流信息"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        message = MCPMessage(method="coordinator.get_workflows")
        response = await coordinator.handle_request(message)
        
        if response.error:
            raise HTTPException(status_code=500, detail=response.error)
        
        return response.result
        
    except Exception as e:
        logger.error(f"获取工作流信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats")
async def get_stats():
    """获取系统统计信息"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        message = MCPMessage(method="coordinator.get_stats")
        response = await coordinator.handle_request(message)
        
        if response.error:
            raise HTTPException(status_code=500, detail=response.error)
        
        return response.result
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}")
async def get_session_status(session_id: str):
    """获取会话状态"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        session_status = await coordinator.get_session_status(session_id)
        
        if not session_status:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return session_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/sessions/{session_id}")
async def cancel_session(session_id: str):
    """取消会话"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        success = await coordinator.cancel_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或无法取消")
        
        return {"message": "会话已取消", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cleanup")
async def cleanup_sessions(background_tasks: BackgroundTasks, max_age_hours: int = 24):
    """清理过期会话"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="协调器未初始化")
    
    try:
        # 在后台执行清理
        background_tasks.add_task(coordinator.cleanup_sessions, max_age_hours)
        
        return {"message": "清理任务已启动", "max_age_hours": max_age_hours}
        
    except Exception as e:
        logger.error(f"启动清理任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 主函数
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 