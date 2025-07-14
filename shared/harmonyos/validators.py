#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Validators
鸿蒙验证器 - 验证生成的代码和配置
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class HarmonyOSValidators:
    """鸿蒙代码和配置验证器"""
    
    @staticmethod
    def validate_arkts_syntax(code: str) -> Tuple[bool, List[str]]:
        """验证ArkTS语法基础规范"""
        errors = []
        
        # 检查基本语法
        if "@Entry" in code and "@Component" not in code:
            errors.append("@Entry装饰器必须与@Component一起使用")
        
        if "struct " in code:
            # 检查结构体定义
            struct_pattern = r'struct\s+(\w+)\s*{'
            matches = re.findall(struct_pattern, code)
            for match in matches:
                if not match[0].isupper():
                    errors.append(f"结构体名 '{match}' 应该以大写字母开头")
        
        # 检查build方法
        if "@Component" in code and "build()" not in code:
            errors.append("@Component装饰的结构体必须包含build()方法")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_file_structure(file_path: str, file_type: str) -> Tuple[bool, List[str]]:
        """验证文件结构和命名"""
        errors = []
        
        # 验证文件扩展名
        if not file_path.endswith('.ets'):
            errors.append("鸿蒙代码文件应使用.ets扩展名")
        
        # 验证文件命名规范
        import os
        filename = os.path.basename(file_path).replace('.ets', '')
        
        if file_type == "page" and not filename.endswith("Page"):
            errors.append("页面文件名应以'Page'结尾")
        elif file_type == "component" and not filename.endswith("Component"):
            errors.append("组件文件名应以'Component'结尾")
        elif file_type == "service" and not filename.endswith("Service"):
            errors.append("服务文件名应以'Service'结尾")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_dependencies(code: str) -> Tuple[bool, List[str]]:
        """验证依赖导入"""
        errors = []
        
        # 检查导入语句
        import_pattern = r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]'
        imports = re.findall(import_pattern, code)
        
        for imp in imports:
            if imp.startswith('./') or imp.startswith('../'):
                # 相对路径导入，检查是否合理
                if '../../../' in imp:
                    errors.append(f"导入路径过深: {imp}")
            elif not imp.startswith('@'):
                # 非系统模块，可能需要检查
                pass
        
        return len(errors) == 0, errors