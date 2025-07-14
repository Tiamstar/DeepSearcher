#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Code Generator Extension
鸿蒙代码生成器扩展 - 专门用于鸿蒙ArkTS代码生成
"""

import logging
from typing import Dict, Any, List, Optional
from shared.harmonyos import HarmonyOSTemplates

logger = logging.getLogger(__name__)

class HarmonyOSCodeGeneratorExt:
    """
    鸿蒙代码生成器扩展
    提供鸿蒙专用的代码生成功能
    """
    
    def __init__(self):
        self.templates = HarmonyOSTemplates()
    
    def generate_code_by_plan(self, file_plans: List[Dict[str, Any]], 
                             requirement: str, context: str = "") -> Dict[str, Any]:
        """根据文件计划生成代码"""
        try:
            generated_files = []
            
            for plan in file_plans:
                file_type = plan.get("type", "page")
                file_path = plan.get("path", "")
                template_type = plan.get("template", "harmonyos_page")
                
                # 生成代码内容
                if file_type == "page":
                    code_content = self.templates.get_page_template(
                        page_name=self._extract_class_name(file_path),
                        has_state=True
                    )
                elif file_type == "component":
                    code_content = self.templates.get_component_template(
                        component_name=self._extract_class_name(file_path),
                        has_props=True
                    )
                elif file_type == "service":
                    code_content = self.templates.get_service_template(
                        service_name=self._extract_class_name(file_path)
                    )
                elif file_type == "model":
                    code_content = self.templates.get_model_template(
                        model_name=self._extract_class_name(file_path)
                    )
                elif file_type == "util":
                    code_content = self.templates.get_util_template(
                        util_name=self._extract_class_name(file_path)
                    )
                else:
                    code_content = f"// 未知文件类型: {file_type}\n// TODO: 实现具体功能"
                
                generated_files.append({
                    "path": file_path,
                    "content": code_content,
                    "type": file_type,
                    "size": len(code_content)
                })
            
            return {
                "success": True,
                "generated_files": generated_files,
                "total_files": len(generated_files),
                "requirement": requirement
            }
            
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": []
            }
    
    def _extract_class_name(self, file_path: str) -> str:
        """从文件路径提取类名"""
        import os
        filename = os.path.basename(file_path)
        class_name = filename.replace(".ets", "").replace(".ts", "")
        
        # 确保首字母大写
        if class_name:
            class_name = class_name[0].upper() + class_name[1:]
        
        return class_name or "Generated"