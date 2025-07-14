#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Project Analyzer
鸿蒙项目结构分析器 - 负责分析项目结构并规划代码生成
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FileGenerationPlan:
    """文件生成计划"""
    path: str
    type: str  # page, component, service, util, ability
    template: str
    priority: int = 1
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class HarmonyOSProjectStructure:
    """鸿蒙项目结构"""
    project_root: str
    main_path: str
    paths: Dict[str, str]
    existing_files: Dict[str, List[str]]
    
class HarmonyOSProjectAnalyzer:
    """
    鸿蒙项目结构分析器
    负责：
    1. 分析现有项目结构
    2. 根据需求规划代码生成
    3. 确定文件放置位置
    4. 生成目录创建计划
    """
    
    def __init__(self, project_root: str = "/home/deepsearch/deep-searcher/MyApplication2"):
        self.project_root = project_root
        self.main_path = f"{project_root}/entry/src/main"
        
        # 鸿蒙项目标准结构
        self.structure = HarmonyOSProjectStructure(
            project_root=project_root,
            main_path=self.main_path,
            paths={
                "pages": f"{self.main_path}/ets/pages",
                "components": f"{self.main_path}/ets/components", 
                "common": f"{self.main_path}/ets/common",
                "models": f"{self.main_path}/ets/models",
                "services": f"{self.main_path}/ets/services",
                "utils": f"{self.main_path}/ets/utils",
                "abilities": f"{self.main_path}/ets/entryability",
                "backup_abilities": f"{self.main_path}/ets/entrybackupability",
                "resources": f"{self.main_path}/resources",
                "module_config": f"{self.main_path}/module.json5"
            },
            existing_files={}
        )
        
        # 需求类型映射
        self.requirement_mappings = {
            "页面": {"type": "page", "priority": 1},
            "界面": {"type": "page", "priority": 1},
            "组件": {"type": "component", "priority": 2},
            "功能": {"type": "service", "priority": 3},
            "服务": {"type": "service", "priority": 3},
            "工具": {"type": "util", "priority": 4},
            "数据": {"type": "model", "priority": 3},
            "列表": {"type": "component", "priority": 2},
            "按钮": {"type": "component", "priority": 2},
            "表单": {"type": "page", "priority": 1},
            "网络": {"type": "service", "priority": 3},
            "存储": {"type": "service", "priority": 3}
        }
        
        self._scan_existing_structure()
    
    def _scan_existing_structure(self):
        """扫描现有项目结构"""
        try:
            for path_type, path in self.structure.paths.items():
                if os.path.exists(path) and os.path.isdir(path):
                    files = []
                    for file in os.listdir(path):
                        if file.endswith(('.ets', '.ts', '.js', '.json5', '.json')):
                            files.append(file)
                    self.structure.existing_files[path_type] = files
                else:
                    self.structure.existing_files[path_type] = []
                    
            logger.info(f"扫描项目结构完成: {len(self.structure.existing_files)} 个目录")
            
        except Exception as e:
            logger.error(f"扫描项目结构失败: {e}")
            # 确保至少有基础结构
            for path_type in self.structure.paths.keys():
                if path_type not in self.structure.existing_files:
                    self.structure.existing_files[path_type] = []
    
    def analyze_requirement_and_plan_files(self, requirement: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析需求并规划文件生成
        
        Args:
            requirement: 用户需求描述
            context: 附加上下文信息
            
        Returns:
            包含文件生成计划的字典
        """
        try:
            context = context or {}
            requirement_lower = requirement.lower()
            
            # 分析需求类型
            requirement_analysis = self._analyze_requirement_type(requirement)
            
            # 生成文件计划
            file_plans = self._generate_file_plans(requirement, requirement_analysis)
            
            # 检查需要创建的目录
            directories_to_create = self._check_required_directories(file_plans)
            
            # 生成文件名建议
            file_plans = self._generate_file_names(file_plans, requirement)
            
            result = {
                "success": True,
                "requirement": requirement,
                "analysis": requirement_analysis,
                "file_plans": [plan.__dict__ for plan in file_plans],
                "target_files": [{"path": plan.path, "type": plan.type} for plan in file_plans],
                "directories_to_create": directories_to_create,
                "project_structure": {
                    "paths": self.structure.paths,
                    "existing_files": self.structure.existing_files
                },
                "generation_strategy": self._determine_generation_strategy(file_plans)
            }
            
            logger.info(f"需求分析完成: {len(file_plans)} 个文件计划")
            return result
            
        except Exception as e:
            logger.error(f"需求分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_plans": [],
                "target_files": []
            }
    
    def _analyze_requirement_type(self, requirement: str) -> Dict[str, Any]:
        """分析需求类型"""
        requirement_lower = requirement.lower()
        
        analysis = {
            "primary_type": "page",  # 默认为页面
            "secondary_types": [],
            "complexity": "simple",
            "ui_components": [],
            "business_logic": [],
            "data_requirements": []
        }
        
        # 检测主要类型
        type_scores = {}
        for keyword, mapping in self.requirement_mappings.items():
            if keyword in requirement_lower:
                type_name = mapping["type"]
                type_scores[type_name] = type_scores.get(type_name, 0) + mapping["priority"]
        
        if type_scores:
            analysis["primary_type"] = max(type_scores, key=type_scores.get)
            analysis["secondary_types"] = [t for t in type_scores.keys() if t != analysis["primary_type"]]
        
        # 检测UI组件需求
        ui_keywords = ["按钮", "列表", "输入框", "图片", "文本", "滚动", "网格", "卡片"]
        for keyword in ui_keywords:
            if keyword in requirement_lower:
                analysis["ui_components"].append(keyword)
        
        # 检测业务逻辑需求
        logic_keywords = ["点击", "提交", "验证", "计算", "处理", "跳转", "刷新"]
        for keyword in logic_keywords:
            if keyword in requirement_lower:
                analysis["business_logic"].append(keyword)
        
        # 检测数据需求
        data_keywords = ["数据", "接口", "存储", "缓存", "网络", "数据库"]
        for keyword in data_keywords:
            if keyword in requirement_lower:
                analysis["data_requirements"].append(keyword)
        
        # 评估复杂度
        complexity_score = len(analysis["ui_components"]) + len(analysis["business_logic"]) + len(analysis["data_requirements"])
        if complexity_score >= 5:
            analysis["complexity"] = "complex"
        elif complexity_score >= 2:
            analysis["complexity"] = "medium"
        
        return analysis
    
    def _generate_file_plans(self, requirement: str, analysis: Dict[str, Any]) -> List[FileGenerationPlan]:
        """生成文件计划"""
        plans = []
        primary_type = analysis["primary_type"]
        
        # 主要文件
        if primary_type == "page":
            plans.append(FileGenerationPlan(
                path="",  # 稍后生成具体路径
                type="page",
                template="harmonyos_page",
                priority=1
            ))
            
        elif primary_type == "component":
            plans.append(FileGenerationPlan(
                path="",
                type="component", 
                template="harmonyos_component",
                priority=2
            ))
            
        elif primary_type == "service":
            plans.append(FileGenerationPlan(
                path="",
                type="service",
                template="harmonyos_service", 
                priority=3
            ))
            
        # 根据复杂度添加辅助文件
        if analysis["complexity"] in ["medium", "complex"]:
            # 中等复杂度：可能需要数据模型
            if analysis["data_requirements"]:
                plans.append(FileGenerationPlan(
                    path="",
                    type="model",
                    template="harmonyos_model",
                    priority=4
                ))
        
        if analysis["complexity"] == "complex":
            # 高复杂度：可能需要工具类和额外服务
            plans.append(FileGenerationPlan(
                path="",
                type="util",
                template="harmonyos_util",
                priority=5
            ))
        
        return plans
    
    def _generate_file_names(self, file_plans: List[FileGenerationPlan], requirement: str) -> List[FileGenerationPlan]:
        """为文件计划生成具体的文件名和路径"""
        
        # 从需求中提取关键词作为文件名基础
        import re
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', requirement)
        base_name = ''.join([word.capitalize() for word in words[:2]]) or "Generated"
        
        # 确保文件名符合命名规范
        base_name = re.sub(r'[^a-zA-Z0-9]', '', base_name)
        if not base_name or not base_name[0].isupper():
            base_name = "Generated" + base_name
        
        for i, plan in enumerate(file_plans):
            if plan.type == "page":
                file_name = f"{base_name}Page.ets"
                plan.path = f"{self.structure.paths['pages']}/{file_name}"
                
            elif plan.type == "component":
                file_name = f"{base_name}Component.ets"
                plan.path = f"{self.structure.paths['components']}/{file_name}"
                
            elif plan.type == "service":
                file_name = f"{base_name}Service.ets"
                plan.path = f"{self.structure.paths['services']}/{file_name}"
                
            elif plan.type == "model":
                file_name = f"{base_name}Model.ets"
                plan.path = f"{self.structure.paths['models']}/{file_name}"
                
            elif plan.type == "util":
                file_name = f"{base_name}Util.ets"
                plan.path = f"{self.structure.paths['utils']}/{file_name}"
        
        return file_plans
    
    def _check_required_directories(self, file_plans: List[FileGenerationPlan]) -> List[str]:
        """检查需要创建的目录"""
        directories = []
        
        for plan in file_plans:
            if plan.path:
                directory = os.path.dirname(plan.path)
                if not os.path.exists(directory) and directory not in directories:
                    directories.append(directory)
        
        return directories
    
    def _determine_generation_strategy(self, file_plans: List[FileGenerationPlan]) -> str:
        """确定生成策略"""
        if len(file_plans) == 1:
            return "single_file"
        elif len(file_plans) <= 3:
            return "incremental"
        else:
            return "comprehensive"
    
    def get_project_info(self) -> Dict[str, Any]:
        """获取项目信息"""
        return {
            "project_root": self.project_root,
            "main_path": self.main_path,
            "structure": self.structure.paths,
            "existing_files": self.structure.existing_files,
            "total_existing_files": sum(len(files) for files in self.structure.existing_files.values())
        }
    
    def validate_file_path(self, file_path: str) -> bool:
        """验证文件路径是否合法"""
        try:
            # 检查路径是否在项目范围内
            abs_path = os.path.abspath(file_path)
            project_abs = os.path.abspath(self.project_root)
            
            if not abs_path.startswith(project_abs):
                return False
            
            # 检查文件扩展名
            valid_extensions = ['.ets', '.ts', '.js', '.json5', '.json']
            if not any(file_path.endswith(ext) for ext in valid_extensions):
                return False
            
            return True
            
        except Exception:
            return False