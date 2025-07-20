#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS编译器Agent - 专门处理hvigorw编译检查
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime

from mcp_agents.base import MCPAgent, MCPMessage
from mcp_agents.harmonyos import HarmonyOSCompilerService

logger = logging.getLogger(__name__)


class HarmonyOSCompilerAgent(MCPAgent):
    """HarmonyOS编译器Agent - 负责hvigorw编译检查"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("harmonyos_compiler")
        self.config = config or {}
        
        # 编译服务
        self.compiler_service = HarmonyOSCompilerService()
        
        # 声明能力
        self.declare_capability("compile.hvigorw", {
            "description": "使用hvigorw进行鸿蒙项目编译检查",
            "parameters": ["project_path", "build_mode", "product"]
        })
        
        self.declare_capability("compile.check", {
            "description": "检查项目编译状态",
            "parameters": ["project_path"]
        })
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化编译器Agent"""
        try:
            # 检查hvigorw是否可用
            hvigorw_available = await self.compiler_service.check_hvigorw_available()
            
            logger.info(f"HarmonyOS编译器Agent初始化成功，hvigorw可用: {hvigorw_available}")
            
            return {
                "agent_id": self.agent_id,
                "capabilities": self.capabilities,
                "hvigorw_available": hvigorw_available,
                "status": "initialized"
            }
            
        except Exception as e:
            logger.error(f"HarmonyOS编译器Agent初始化失败: {e}")
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理编译请求"""
        try:
            method = message.method
            params = message.params or {}
            
            if method == "compile.hvigorw":
                result = await self._compile_with_hvigorw(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "compile.check":
                result = await self._check_compile_status(params)
                return self.protocol.create_response(message.id, result)
            
            else:
                return self.protocol.handle_method_not_found(message.id, method)
                
        except Exception as e:
            logger.error(f"处理编译请求失败: {e}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _compile_with_hvigorw(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """使用hvigorw进行编译"""
        project_path = params.get("project_path", "MyApplication2")
        build_mode = params.get("build_mode", "project")
        product = params.get("product", "default")
        
        logger.info(f"🔧 开始hvigorw编译检查")
        logger.info(f"   - 项目路径: {project_path}")
        logger.info(f"   - 构建模式: {build_mode}")
        logger.info(f"   - 产品配置: {product}")
        logger.info(f"📋 执行hvigorw编译命令...")
        
        try:
            # 使用编译服务进行编译
            compile_result = await self.compiler_service.compile_project(
                project_path=project_path,
                build_mode=build_mode,
                product=product
            )
            
            success = compile_result.get("success", False)
            errors = compile_result.get("errors", [])
            warnings = compile_result.get("warnings", [])
            
            logger.info(f"📋 hvigorw编译结果: success={success}")
            logger.info(f"   - 错误数量: {len(errors)}")
            logger.info(f"   - 警告数量: {len(warnings)}")
            logger.info(f"   - 原始输出长度: {len(compile_result.get('raw_output', ''))}")
            
            # 显示前几个错误
            for i, error in enumerate(errors[:2]):
                logger.info(f"   - 错误{i+1}: {error}")
            
            # 显示前几个警告
            for i, warning in enumerate(warnings[:2]):
                logger.info(f"   - 警告{i+1}: {warning}")
            
            return {
                "success": success,
                "compilation_result": compile_result,
                "errors": errors,
                "warnings": warnings,
                "project_path": project_path,
                "build_mode": build_mode,
                "product": product
            }
            
        except Exception as e:
            logger.error(f"hvigorw编译失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "compilation_result": {},
                "errors": [{"message": str(e), "type": "compilation_error"}],
                "warnings": [],
                "project_path": project_path
            }
    
    async def _check_compile_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """检查编译状态"""
        project_path = params.get("project_path", "MyApplication2")
        
        try:
            # 检查项目是否存在编译产物
            build_dir = os.path.join(project_path, "build")
            has_build_output = os.path.exists(build_dir) and os.listdir(build_dir)
            
            # 检查hvigorw是否可用
            hvigorw_available = await self.compiler_service.check_hvigorw_available()
            
            return {
                "success": True,
                "project_path": project_path,
                "has_build_output": has_build_output,
                "hvigorw_available": hvigorw_available,
                "build_directory": build_dir
            }
            
        except Exception as e:
            logger.error(f"检查编译状态失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }