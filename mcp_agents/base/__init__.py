"""
MCP Agents Base Module
华为多Agent协作系统 - MCP基础模块
"""

from .protocol import MCPMessage, MCPProtocol, MessageType, MCPError
from .mcp_agent import MCPAgent

__all__ = [
    'MCPMessage',
    'MCPProtocol', 
    'MessageType',
    'MCPError',
    'MCPAgent'
]

__version__ = "1.0.0" 