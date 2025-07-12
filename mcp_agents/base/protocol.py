#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Protocol Implementation
华为多Agent协作系统 - MCP协议实现
"""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import logging
from datetime import datetime

class MessageType(Enum):
    """MCP消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"

@dataclass
class MCPMessage:
    """MCP消息基础结构"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """从字典创建消息"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """从JSON字符串创建消息"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_request(self) -> bool:
        """判断是否为请求消息"""
        return self.method is not None and self.result is None and self.error is None
    
    def is_response(self) -> bool:
        """判断是否为响应消息"""
        return self.method is None and (self.result is not None or self.error is not None)
    
    def is_notification(self) -> bool:
        """判断是否为通知消息"""
        return self.method is not None and self.id is None

class MCPError:
    """MCP错误代码定义"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # 自定义错误代码
    AGENT_NOT_FOUND = -32001
    AGENT_BUSY = -32002
    WORKFLOW_ERROR = -32003
    TIMEOUT_ERROR = -32004

class MCPProtocol:
    """MCP协议处理器"""
    
    def __init__(self):
        self.capabilities = {}
        self.version = "1.0"
        self.logger = logging.getLogger("mcp.protocol")
    
    def create_request(self, method: str, params: Dict[str, Any] = None) -> MCPMessage:
        """创建请求消息"""
        return MCPMessage(
            id=str(uuid.uuid4()),
            method=method,
            params=params or {}
        )
    
    def create_response(self, request_id: str, result: Any = None, error: Dict[str, Any] = None) -> MCPMessage:
        """创建响应消息"""
        if error:
            return MCPMessage(
                id=request_id,
                error=error
            )
        else:
            return MCPMessage(
                id=request_id,
                result=result
            )
    
    def create_notification(self, method: str, params: Dict[str, Any] = None) -> MCPMessage:
        """创建通知消息"""
        return MCPMessage(
            method=method,
            params=params or {}
        )
    
    def create_error(self, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """创建错误对象"""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
        return error
    
    def validate_message(self, message: MCPMessage) -> bool:
        """验证消息格式"""
        try:
            # 检查基本字段
            if message.jsonrpc != "2.0":
                return False
            
            # 检查请求消息
            if message.is_request():
                return message.method is not None and message.id is not None
            
            # 检查响应消息
            if message.is_response():
                return message.id is not None and (message.result is not None or message.error is not None)
            
            # 检查通知消息
            if message.is_notification():
                return message.method is not None and message.id is None
            
            return False
            
        except Exception as e:
            self.logger.error(f"消息验证失败: {str(e)}")
            return False
    
    def handle_parse_error(self, request_id: str = None) -> MCPMessage:
        """处理解析错误"""
        return self.create_response(
            request_id,
            error=self.create_error(MCPError.PARSE_ERROR, "Parse error")
        )
    
    def handle_invalid_request(self, request_id: str = None) -> MCPMessage:
        """处理无效请求错误"""
        return self.create_response(
            request_id,
            error=self.create_error(MCPError.INVALID_REQUEST, "Invalid Request")
        )
    
    def handle_method_not_found(self, request_id: str, method: str) -> MCPMessage:
        """处理方法未找到错误"""
        return self.create_response(
            request_id,
            error=self.create_error(
                MCPError.METHOD_NOT_FOUND, 
                f"Method not found: {method}"
            )
        )
    
    def handle_invalid_params(self, request_id: str, message: str = None) -> MCPMessage:
        """处理无效参数错误"""
        return self.create_response(
            request_id,
            error=self.create_error(
                MCPError.INVALID_PARAMS,
                message or "Invalid params"
            )
        )
    
    def handle_internal_error(self, request_id: str, message: str = None) -> MCPMessage:
        """处理内部错误"""
        return self.create_response(
            request_id,
            error=self.create_error(
                MCPError.INTERNAL_ERROR,
                message or "Internal error"
            )
        ) 