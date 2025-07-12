#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Agent Base Class
华为多Agent协作系统 - MCP Agent基类
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from .protocol import MCPMessage, MCPProtocol, MCPError


class MCPAgent(ABC):
    """MCP Agent基类"""
    
    def __init__(self, agent_id: str, capabilities: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.capabilities = capabilities or {}
        self.protocol = MCPProtocol()
        self.logger = logging.getLogger(f"mcp.agent.{agent_id}")
        self.is_initialized = False
        self.status = "stopped"
        self.start_time = None
    
    @abstractmethod
    async def initialize(self) -> Dict[str, Any]:
        """初始化Agent并返回能力声明"""
        pass
    
    @abstractmethod
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理MCP请求"""
        pass
    
    async def get_prompts(self) -> List[Dict[str, Any]]:
        """获取Agent支持的Prompts"""
        return []
    
    async def get_resources(self) -> List[Dict[str, Any]]:
        """获取Agent提供的Resources"""
        return []
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取Agent提供的Tools"""
        return []
    
    def declare_capability(self, capability: str, details: Dict[str, Any] = None):
        """声明Agent能力"""
        self.capabilities[capability] = details or {}
        self.logger.debug(f"声明能力: {capability}")
    
    async def start(self):
        """启动Agent"""
        try:
            if self.status == "running":
                self.logger.warning(f"Agent {self.agent_id} 已经在运行")
                return
            
            self.logger.info(f"启动Agent: {self.agent_id}")
            self.start_time = datetime.now()
            self.status = "starting"
            
            # 初始化Agent
            if not self.is_initialized:
                await self.initialize()
                self.is_initialized = True
            
            self.status = "running"
            self.logger.info(f"Agent {self.agent_id} 启动成功")
            
        except Exception as e:
            self.status = "error"
            self.logger.error(f"Agent {self.agent_id} 启动失败: {str(e)}")
            raise
    
    async def stop(self):
        """停止Agent"""
        try:
            self.logger.info(f"停止Agent: {self.agent_id}")
            self.status = "stopping"
            
            # 执行清理操作
            await self.cleanup()
            
            self.status = "stopped"
            self.logger.info(f"Agent {self.agent_id} 已停止")
            
        except Exception as e:
            self.status = "error"
            self.logger.error(f"Agent {self.agent_id} 停止失败: {str(e)}")
            raise
    
    async def cleanup(self):
        """清理资源（子类可以重写）"""
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "is_initialized": self.is_initialized,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "capabilities": self.capabilities,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }
    
    async def _handle_standard_methods(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理标准MCP方法"""
        try:
            if message.method == "initialize":
                if not self.is_initialized:
                    init_result = await self.initialize()
                    self.is_initialized = True
                    return self.protocol.create_response(message.id, init_result)
                else:
                    return self.protocol.create_response(
                        message.id, 
                        error=self.protocol.create_error(
                            MCPError.INTERNAL_ERROR, 
                            "Already initialized"
                        )
                    )
            
            elif message.method == "prompts/list":
                prompts = await self.get_prompts()
                return self.protocol.create_response(message.id, {"prompts": prompts})
            
            elif message.method == "resources/list":
                resources = await self.get_resources()
                return self.protocol.create_response(message.id, {"resources": resources})
            
            elif message.method == "tools/list":
                tools = await self.get_tools()
                return self.protocol.create_response(message.id, {"tools": tools})
            
            elif message.method == "agent/status":
                status = await self.get_status()
                return self.protocol.create_response(message.id, status)
            
            elif message.method == "agent/ping":
                return self.protocol.create_response(
                    message.id, 
                    {
                        "pong": True,
                        "timestamp": datetime.now().isoformat(),
                        "agent_id": self.agent_id
                    }
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"处理标准方法 {message.method} 失败: {str(e)}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def process_message(self, message: MCPMessage) -> MCPMessage:
        """处理消息的主入口"""
        try:
            # 验证消息格式
            if not self.protocol.validate_message(message):
                return self.protocol.handle_invalid_request(message.id)
            
            # 检查Agent状态
            if self.status != "running":
                return self.protocol.create_response(
                    message.id,
                    error=self.protocol.create_error(
                        MCPError.AGENT_BUSY,
                        f"Agent {self.agent_id} is not running (status: {self.status})"
                    )
                )
            
            self.logger.debug(f"处理消息: {message.method}")
            
            # 先尝试处理标准方法
            standard_response = await self._handle_standard_methods(message)
            if standard_response:
                return standard_response
            
            # 处理Agent特定方法
            return await self.handle_request(message)
            
        except Exception as e:
            self.logger.error(f"处理消息失败: {str(e)}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    def __str__(self) -> str:
        return f"MCPAgent(id={self.agent_id}, status={self.status})"
    
    def __repr__(self) -> str:
        return self.__str__() 