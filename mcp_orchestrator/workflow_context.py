#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流上下文管理 - 负责Agent间的数据传递和状态管理
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import re

logger = logging.getLogger(__name__)


class WorkflowPhase(Enum):
    """工作流阶段"""
    REQUIREMENT_ANALYSIS = "requirement_analysis"      # 需求分析
    INFORMATION_SEARCH = "information_search"          # 信息搜索
    CODE_GENERATION = "code_generation"                # 代码生成
    STATIC_CHECK = "static_check"                      # 静态检查
    COMPILE_CHECK = "compile_check"                    # 编译检查
    ERROR_FIXING = "error_fixing"                      # 错误修复
    COMPLETED = "completed"                            # 已完成


class TaskType(Enum):
    """任务类型 - 帮助Agent理解当前任务"""
    INITIAL_GENERATION = "initial_generation"          # 初始代码生成
    ERROR_FIXING = "error_fixing"                      # 错误修复
    FEATURE_ENHANCEMENT = "feature_enhancement"        # 功能增强
    SEARCH_FOR_SOLUTIONS = "search_for_solutions"      # 搜索解决方案
    SEARCH_FOR_REFERENCE = "search_for_reference"      # 搜索参考资料


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    type: str  # arkts, json, etc.
    content: str = ""
    status: str = "planned"  # planned, generated, checked, error, fixed
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ErrorInfo:
    """错误信息"""
    file_path: str
    error_type: str  # syntax, compile, lint
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    severity: str = "error"  # error, warning, info
    raw_output: Optional[str] = None # 新增：用于存储codelinter的原始输出
    
    def to_search_keywords(self) -> List[str]:
        """转换为搜索关键词"""
        keywords = ["HarmonyOS", "ArkTS", "鸿蒙"]
        keywords.append(self.error_type)
        # 提取错误消息中的关键词
        if "Cannot find" in self.message:
            keywords.extend(["import", "module", "找不到"])
        elif "Type" in self.message:
            keywords.extend(["类型", "type", "定义"])
        elif "Syntax" in self.message:
            keywords.extend(["语法", "syntax", "错误"])
        
        return keywords


@dataclass
class WorkflowContext:
    """工作流上下文 - 在Agent间传递的完整上下文"""
    session_id: str
    user_requirement: str
    current_phase: WorkflowPhase
    current_task_type: TaskType
    
    # 项目管理Agent输出
    project_analysis: Dict[str, Any] = field(default_factory=dict)
    planned_files: List[FileInfo] = field(default_factory=list)
    
    # 搜索Agent输出
    search_results: Dict[str, Any] = field(default_factory=dict)
    reference_materials: List[Dict[str, Any]] = field(default_factory=list)
    
    # 代码生成Agent输出
    generated_files: List[FileInfo] = field(default_factory=list)
    
    # 检查Agent输出
    lint_errors: List[ErrorInfo] = field(default_factory=list)
    compile_errors: List[ErrorInfo] = field(default_factory=list)
    
    # 修复相关
    fix_attempts: int = 0
    max_fix_attempts: int = 3
    current_errors: List[ErrorInfo] = field(default_factory=list)
    
    # 工作流控制
    should_continue_fixing: bool = True
    workflow_completed: bool = False
    
    def add_error(self, error: ErrorInfo):
        """添加错误"""
        if error.error_type == "lint":
            self.lint_errors.append(error)
        elif error.error_type == "compile":
            self.compile_errors.append(error)
        self.current_errors.append(error)
    
    def get_all_errors(self) -> List[ErrorInfo]:
        """获取所有错误"""
        return self.lint_errors + self.compile_errors
    
    def _parse_error_statistics(self, raw_output: str) -> Dict[str, int]:
        """解析codelinter输出中的统计信息"""
        stats = {"errors": 0, "warns": 0, "defects": 0, "suggestions": 0}
        
        if not raw_output:
            return stats
            
        # 寻找类似"-Defects: 4; Errors: 0; Warns: 4; Suggestions: 0;"的行
        stats_match = re.search(r'-?Defects:\s*(\d+);\s*Errors:\s*(\d+);\s*Warns:\s*(\d+);\s*Suggestions:\s*(\d+)', raw_output)
        
        if stats_match:
            stats["defects"] = int(stats_match.group(1))
            stats["errors"] = int(stats_match.group(2))
            stats["warns"] = int(stats_match.group(3))
            stats["suggestions"] = int(stats_match.group(4))
            
        return stats
        
    def has_errors(self) -> bool:
        """是否有错误（只统计严重性为error级别的错误，忽略warning）"""
        # 过滤获取严重性为error的错误
        error_level_errors = [error for error in self.get_all_errors() if error.severity.lower() == "error"]
        
        logger.debug(f"检查是否有错误: lint_errors={len(self.lint_errors)}, compile_errors={len(self.compile_errors)}, 总计error级别={len(error_level_errors)}")
        return len(error_level_errors) > 0
    
    def clear_current_errors(self):
        """清除当前错误（修复后调用）"""
        self.current_errors.clear()
    
    def can_continue_fixing(self) -> bool:
        """是否可以继续修复"""
        has_errors = self.has_errors()
        can_continue = (self.fix_attempts < self.max_fix_attempts and 
                       self.should_continue_fixing and 
                       has_errors)
        
        logger.info(f"检查是否可以继续修复:")
        logger.info(f"  fix_attempts={self.fix_attempts}, max_fix_attempts={self.max_fix_attempts}")
        logger.info(f"  should_continue_fixing={self.should_continue_fixing}")
        logger.info(f"  has_errors={has_errors}")
        logger.info(f"  can_continue={can_continue}")
        
        return can_continue
    
    def prepare_for_fixing(self):
        """准备进入修复阶段"""
        self.current_phase = WorkflowPhase.ERROR_FIXING
        self.current_task_type = TaskType.ERROR_FIXING
        self.fix_attempts += 1
        
        # 将所有lint和compile错误合并到current_errors中
        self.current_errors.clear()
        self.current_errors.extend(self.lint_errors)
        self.current_errors.extend(self.compile_errors)
        
        logger.info(f"开始第{self.fix_attempts}次错误修复")
        logger.info(f"准备修复 {len(self.current_errors)} 个错误 (lint: {len(self.lint_errors)}, compile: {len(self.compile_errors)})")
    
    def get_search_context_for_errors(self) -> Dict[str, Any]:
        """为错误修复生成搜索上下文"""
        if not self.current_errors:
            return {}
        
        # 收集所有错误的关键词
        all_keywords = []
        error_messages = []
        
        for error in self.current_errors:
            all_keywords.extend(error.to_search_keywords())
            error_messages.append(error.message)
        
        return {
            "search_type": "error_solving",
            "keywords": list(set(all_keywords)),  # 去重
            "error_messages": error_messages,
            "file_types": list(set([error.file_path.split('.')[-1] for error in self.current_errors])),
            "error_count": len(self.current_errors)
        }
    
    def get_generation_context_for_agent(self, agent_type: str) -> Dict[str, Any]:
        """为特定Agent生成上下文，根据工作流类型提供差异化信息"""
        base_context = {
            "session_id": self.session_id,
            "user_requirement": self.user_requirement,
            "current_phase": self.current_phase.value,
            "current_task_type": self.current_task_type.value,
            "fix_attempt": self.fix_attempts,
            "workflow_type": self._get_workflow_type_description(),
            "workflow_guidance": self._get_workflow_guidance_for_agent(agent_type)
        }
        
        if agent_type == "project_manager":
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 错误修复阶段需要项目管理器分析错误并确定修复策略
                return {
                    **base_context,
                    "task_description": "分析Index.ets文件的编译和静态检查错误，生成精确的搜索关键词用于查找解决方案",
                    "is_error_analysis": True,
                    "is_fixing": True,  # 增加这个参数给项目管理Agent使用
                    "errors": [error.__dict__ for error in self.current_errors],  # analyze_errors_and_generate_keywords期望的参数名
                    "original_requirement": self.user_requirement,  # analyze_errors_and_generate_keywords期望的参数名
                    "project_path": "MyApplication2",  # analyze_errors_and_generate_keywords期望的参数名
                    "current_errors": [error.__dict__ for error in self.current_errors],
                    "error_types": list(set([error.error_type for error in self.current_errors])),
                    "affected_files": list(set([error.file_path for error in self.current_errors])),
                    "fix_attempt": self.fix_attempts,
                    "existing_files": [file.__dict__ for file in self.generated_files]
                }
            elif self.current_phase == WorkflowPhase.COMPILE_CHECK:
                # 编译检查阶段需要项目管理器执行编译检查
                return {
                    **base_context,
                    "task_description": "执行hvigorw编译检查，验证生成的Index.ets文件能否正常编译",
                    "is_compilation_check": True,
                    "project_path": "MyApplication2",
                    "generated_files": [file.__dict__ for file in self.generated_files]
                }
            else:
                return {
                    **base_context,
                    "task_description": "分析Index.ets文件中的自然语言描述，规划单个页面组件的内容结构",
                    "is_initial_planning": True,
                    "project_structure_required": True,
                    "target_file_path": "MyApplication2/entry/src/main/ets/pages/Index.ets",
                    "single_file_generation": True
                }
        
        elif agent_type == "search":
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 使用项目管理Agent分析出的精确搜索关键词
                error_keywords = []
                error_summary = []
                
                # 优先使用项目管理Agent分析的搜索关键词
                if hasattr(self, 'search_results') and 'error_analysis_keywords' in self.search_results:
                    error_keywords = self.search_results['error_analysis_keywords']
                elif hasattr(self, 'project_analysis') and 'search_queries' in self.project_analysis:
                    error_keywords = self.project_analysis['search_queries']
                else:
                    # 备用方案：根据错误类型生成精确关键词
                    for error in self.current_errors:
                        specific_keywords = self._generate_specific_error_keywords(error)
                        error_keywords.extend(specific_keywords)
                        error_summary.append(f"{error.file_path}: {error.message}")
                
                # 构建精确的搜索查询
                search_query = " ".join(set(error_keywords)) if error_keywords else self._build_fallback_error_query()
                
                return {
                    **base_context,
                    "task_description": "搜索精确的错误解决方案",
                    "query": search_query,
                    "search_mode": "error_fixing",
                    "error_context": self.get_search_context_for_errors(),
                    "errors_to_fix": [error.__dict__ for error in self.current_errors],
                    "error_summary": error_summary,
                    "focus_on_solutions": True,
                    "search_priority": "problem_solving"
                }
            else:
                # 优先使用项目管理Agent分析的搜索关键词
                search_keywords = []
                if hasattr(self, 'project_analysis') and 'search_queries' in self.project_analysis:
                    search_keywords = self.project_analysis['search_queries']
                else:
                    # 备用方案：从需求中提取搜索关键词
                    search_keywords = self._extract_search_keywords_from_requirements()
                
                # 构建搜索查询
                search_query = " ".join(search_keywords) if search_keywords else self.user_requirement
                
                return {
                    **base_context,
                    "task_description": "搜索技术参考资料",
                    "query": search_query,  # 搜索Agent期望的参数
                    "search_mode": "code_generation",
                    "search_keywords": search_keywords,
                    "planned_files": [file.__dict__ for file in self.planned_files],
                    "focus_on_examples": True,
                    "search_priority": "reference_materials"
                }
        
        elif agent_type == "code_generator":
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 优先使用项目管理Agent分析的精确修复信息
                error_analysis = self.project_analysis.get("error_analysis", [])
                files_to_fix = self.project_analysis.get("files_to_fix", [])
                
                return {
                    **base_context,
                    "task_description": "根据项目管理Agent的错误分析结果进行Index.ets文件的精确代码修复",
                    "errors_to_fix": [error.__dict__ for error in self.current_errors],  # 原始错误信息
                    "error_analysis": error_analysis,  # 项目管理Agent的详细分析
                    "files_to_fix": files_to_fix,  # 项目管理Agent确定的具体文件
                    "target_files_with_locations": error_analysis,  # 包含具体位置信息
                    "solution_references": self.search_results.get("error_solutions", []),
                    "existing_files": [file.__dict__ for file in self.generated_files],
                    "operation_mode": "error_fixing",
                    "preserve_existing_structure": True,
                    "focus_on_fixes": True,
                    "modification_only": True,
                    "precise_targeting": True  # 标记使用精确定位
                }
            else:
                return {
                    **base_context,
                    "task_description": "根据Index.ets文件的自然语言描述和搜索资料生成单个页面组件代码",
                    "project_plan": self.project_analysis,
                    "planned_files": [file.__dict__ for file in self.planned_files],
                    "reference_materials": self.reference_materials,
                    "operation_mode": "initial_generation",
                    "create_new_files": True,
                    "focus_on_structure": True,
                    "complete_implementation": True
                }
        
        elif agent_type == "code_checker":
            checker_context = {
                **base_context,
                "files_to_check": [file.__dict__ for file in self.generated_files if file.status in ["generated", "fixed"]]
            }
            
            if self.current_task_type == TaskType.ERROR_FIXING:
                checker_context.update({
                    "task_description": "检查修复后的Index.ets文件是否解决了问题",
                    "check_mode": "verification",
                    "previous_errors": [error.__dict__ for error in self.current_errors],
                    "focus_on_fixes": True
                })
            else:
                checker_context.update({
                    "task_description": "对新生成的Index.ets文件进行静态检查",
                    "check_mode": "initial_check",
                    "comprehensive_check": True
                })
            
            return checker_context
        
        elif agent_type == "compiler":
            compiler_context = {
                **base_context,
                "project_path": "MyApplication2"
            }
            
            if self.current_task_type == TaskType.ERROR_FIXING:
                compiler_context.update({
                    "task_description": "验证修复后的代码是否能正常编译",
                    "compile_mode": "verification",
                    "previous_errors": [error.__dict__ for error in self.current_errors],
                    "expect_improvement": True
                })
            else:
                compiler_context.update({
                    "task_description": "对新生成的代码进行编译检查",
                    "compile_mode": "initial_check",
                    "full_compilation": True
                })
            
            return compiler_context
        
        return base_context
    
    def _extract_search_keywords_from_requirements(self) -> List[str]:
        """从需求中生成具体的搜索问题"""
        search_queries = []
        
        # 根据用户需求生成针对性的搜索问题
        if "登录" in self.user_requirement:
            search_queries.extend([
                "HarmonyOS ArkTS如何使用TextInput和Button组件创建登录页面的完整示例",
                "鸿蒙应用中用户认证和表单验证的最佳实践和@State状态管理"
            ])
        elif "计时器" in self.user_requirement:
            search_queries.extend([
                "HarmonyOS ArkTS如何使用setInterval实现倒计时功能和暂停操作",
                "鸿蒙应用中如何使用@State和@Watch管理计时器状态变化和时间显示更新"
            ])
        elif "列表" in self.user_requirement or "数据" in self.user_requirement:
            search_queries.extend([
                "HarmonyOS ArkTS中List组件的高性能数据渲染和动态更新实现方法",
                "鸿蒙应用中数据绑定和状态管理的最佳实践和性能优化"
            ])
        elif "导航" in self.user_requirement or "路由" in self.user_requirement:
            search_queries.extend([
                "HarmonyOS ArkTS Navigation组件的使用方法和页面路由管理",
                "鸿蒙应用多页面导航和参数传递的完整实现指南"
            ])
        else:
            # 通用情况：基于关键词生成问题
            if "页面" in self.user_requirement:
                search_queries.append("HarmonyOS ArkTS @Entry @Component装饰器的正确使用和页面生命周期管理")
            if "组件" in self.user_requirement:
                search_queries.append("鸿蒙应用中自定义组件的创建和复用最佳实践")
            if not search_queries:  # 如果还是没有，提供默认的通用问题
                search_queries.extend([
                    f"HarmonyOS ArkTS实现{self.user_requirement}的技本方案和代码示例",
                    "鸿蒙应用开发的基础组件使用和项目结构最佳实践"
                ])
        
        return search_queries
    
    def _get_workflow_type_description(self) -> str:
        """获取工作流类型描述"""
        if self.current_task_type == TaskType.ERROR_FIXING:
            return f"错误修复工作流 (第{self.fix_attempts}次修复尝试)"
        elif self.current_task_type == TaskType.INITIAL_GENERATION:
            return "初始代码生成工作流"
        else:
            return f"工作流: {self.current_task_type.value}"
    
    def _get_workflow_guidance_for_agent(self, agent_type: str) -> str:
        """为特定Agent提供工作流指导"""
        if self.current_task_type == TaskType.ERROR_FIXING:
            guidance = {
                "project_manager": "错误修复阶段不需要重新规划，直接跳过此步骤",
                "search": "专注于搜索特定错误的解决方案，优先使用在线搜索获取最新信息",
                "code_generator": "只修复错误相关的代码，不要重写整个文件，保持现有功能不变",
                "code_checker": "重点检查之前的错误是否已修复，少关注其他新问题",
                "compiler": "验证修复后的代码是否能正常编译，关注错误数量的减少"
            }
        else:
            guidance = {
                "project_manager": "全面分析用户需求，制定完整的文件生成计划",
                "search": "搜索相关技术参考资料和开发示例，为代码生成提供基础",
                "code_generator": "根据项目规划创建完整的文件结构，实现所有计划功能",
                "code_checker": "对新生成的代码进行全面静态检查，确保代码质量",
                "compiler": "编译检查新生成的代码，识别编译错误和警告"
            }
        
        return guidance.get(agent_type, "遵循当前工作流阶段的标准操作流程")
    
    def update_from_agent_result(self, agent_type: str, result: Dict[str, Any]):
        """根据Agent执行结果更新上下文"""
        logger.info(f"更新上下文: {agent_type} -> {self.current_phase.value} (工作流: {self.current_task_type.value})")
        
        if agent_type == "project_manager":
            # 处理项目分析结果
            self.project_analysis = result.get("analysis", {})
            
            # 错误修复阶段：保存顶级错误分析字段
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 将顶级字段合并到project_analysis中
                self.project_analysis['error_analysis'] = result.get("error_analysis", [])
                self.project_analysis['files_to_fix'] = result.get("files_to_fix", [])
                self.project_analysis['fix_strategies'] = result.get("fix_strategies", [])
                logger.info(f"保存错误分析结果: {len(self.project_analysis['error_analysis'])}个错误分析")
            
            # 保存搜索关键词供搜索Agent使用（两种工作流都需要）
            search_queries = result.get("search_queries", [])
            if search_queries:
                self.project_analysis['search_queries'] = search_queries
                if self.current_task_type == TaskType.ERROR_FIXING:
                    # 错误修复阶段额外保存为error_analysis_keywords
                    self.project_analysis['error_analysis_keywords'] = search_queries
            
            # 更新计划文件列表
            planned_files_data = result.get("planned_files", [])
            self.planned_files = [
                FileInfo(
                    path=file_data["path"],
                    type=file_data["type"],
                    status="planned"
                ) for file_data in planned_files_data
            ]
            
            # 处理编译检查结果（当项目管理Agent执行编译检查时）
            if self.current_phase == WorkflowPhase.COMPILE_CHECK or "compile_result" in result:
                # 处理编译错误
                compile_result = result.get("compile_result", {})
                errors_data = result.get("errors", []) or compile_result.get("errors", [])
                raw_output = compile_result.get("stdout", "") + compile_result.get("stderr", "")
                
                if self.current_task_type == TaskType.ERROR_FIXING:
                    # 错误修复阶段，比较修复前后的错误
                    previous_error_count = len(self.compile_errors)
                    logger.info(f"  修复验证: 编译错误从{previous_error_count}个变为{len(errors_data)}个")
                    
                    # 清除之前的编译错误，添加新的
                    self.compile_errors.clear()
                    
                    for error_data in errors_data:
                        error = ErrorInfo(
                            file_path=error_data.get("file", "unknown"),
                            error_type="compile",
                            message=error_data.get("message", "Unknown compile error"),
                            line=error_data.get("line"),
                            severity="error",
                            raw_output=raw_output  # 保存原始输出
                        )
                        self.add_error(error)
                        
                    if len(errors_data) < previous_error_count:
                        logger.info(f"  修复效果: 编译错误减少了{previous_error_count - len(errors_data)}个")
                    elif len(errors_data) == 0:
                        logger.info(f"  修复成功: 所有编译错误已解决")
                        
                else:
                    # 初始检查阶段
                    logger.info(f"  初始编译检查: 发现{len(errors_data)}个编译错误")
                    
                    for error_data in errors_data:
                        error = ErrorInfo(
                            file_path=error_data.get("file", "unknown"),
                            error_type="compile",
                            message=error_data.get("message", "Unknown compile error"),
                            line=error_data.get("line"),
                            severity="error",
                            raw_output=raw_output  # 保存原始输出
                        )
                        self.add_error(error)
            
        elif agent_type == "search":
            self.search_results = result
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 保存错误解决方案
                self.search_results["error_solutions"] = result.get("sources", [])
            else:
                # 保存参考资料 - SearchAgent返回的是sources字段
                self.reference_materials = result.get("sources", [])
                # 同时保存完整的搜索上下文供后续使用
                if result.get("answer"):
                    self.reference_materials.append({
                        "type": "search_summary",
                        "content": result["answer"],
                        "source": "search_agent"
                    })
                
        elif agent_type == "code_generator":
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 更新修复后的文件
                fixed_files = result.get("fixed_files", [])
                files_modified = 0
                
                logger.info(f"代码生成Agent返回了 {len(fixed_files)} 个修复后的文件")
                
                for fixed_file in fixed_files:
                    file_path = fixed_file.get("path", "")
                    file_content = fixed_file.get("content", "")
                    
                    logger.info(f"处理修复后的文件: {file_path}, 内容长度: {len(file_content)} 字符")
                    
                    # 查找现有文件
                    existing_file_found = False
                    for existing_file in self.generated_files:
                        if existing_file.path == file_path:
                            # 更新现有文件
                            existing_file.content = file_content
                            existing_file.status = "fixed"
                            existing_file.errors.clear()
                            files_modified += 1
                            existing_file_found = True
                            logger.info(f"更新了现有文件: {file_path}")
                            break
                    
                    # 如果没有找到现有文件，添加为新文件
                    if not existing_file_found and file_content:
                        logger.info(f"添加新文件: {file_path}")
                        new_file = FileInfo(
                            path=file_path,
                            type=fixed_file.get("type", "arkts"),
                            content=file_content,
                            status="fixed"
                        )
                        self.generated_files.append(new_file)
                        files_modified += 1
                
                logger.info(f"  修复模式: 更新了{files_modified}个文件")
                
                # 检查是否有新生成的文件(不常见但有可能)
                generated_files_data = result.get("generated_files", [])
                if generated_files_data:
                    logger.info(f"  修复过程中生成了{len(generated_files_data)}个新文件")
                    new_files = [
                        FileInfo(
                            path=file_data["path"],
                            type=file_data["type"],
                            content=file_data.get("content", ""),
                            status="generated"
                        ) for file_data in generated_files_data
                    ]
                    self.generated_files.extend(new_files)
            else:
                # 添加新生成的文件
                generated_files_data = result.get("generated_files", [])
                self.generated_files = [
                    FileInfo(
                        path=file_data["path"],
                        type=file_data["type"],
                        content=file_data.get("content", ""),
                        status="generated"
                    ) for file_data in generated_files_data
                ]
                logger.info(f"  初始生成模式: 创建了{len(self.generated_files)}个新文件")
        
        elif agent_type == "code_checker":
            # 处理静态检查错误，注意只处理真正的错误，忽略警告
            errors_data = result.get("errors", [])  # 只获取error字段，不是所有issues
            raw_output = result.get("raw_output", "")  # 获取原始输出
            
            # 首先检查统计信息
            stats = self._parse_error_statistics(raw_output)
            if stats["errors"] == 0:
                logger.info(f"  codelinter统计信息显示没有实际错误 (Errors: 0)，清空lint错误")
                # 即使没有新错误，也要清空之前的lint错误
                self.lint_errors.clear()
                return
            
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 错误修复阶段，比较修复前后的错误
                logger.info(f"  修复验证: 发现{len(errors_data)}个静态检查错误")
                
                # 清除之前的lint错误，添加新的
                self.lint_errors.clear()
                
                for error_data in errors_data:
                    error = ErrorInfo(
                        file_path=error_data["file"],
                        error_type="lint",
                        message=error_data["message"],
                        line=error_data.get("line"),
                        severity=error_data.get("severity", "error"),  # 应该已经是错误级别
                        raw_output=raw_output  # 保存原始输出
                    )
                    self.add_error(error)
            else:
                # 初始检查阶段
                logger.info(f"  初始检查: 发现{len(errors_data)}个静态检查错误")
                
                for error_data in errors_data:
                    error = ErrorInfo(
                        file_path=error_data["file"],
                        error_type="lint",
                        message=error_data["message"],
                        line=error_data.get("line"),
                        severity=error_data.get("severity", "error"),  # 应该已经是错误级别
                        raw_output=raw_output  # 保存原始输出
                    )
                    self.add_error(error)
                
        elif agent_type == "compiler":
            # 处理编译错误 - 修复错误数据结构获取
            # 编译Agent可能返回两种格式的错误：直接errors字段或compilation_result中的errors
            errors_data = result.get("errors", [])
            raw_output = result.get("stdout", "") + result.get("stderr", "")
            if not raw_output and "compilation_result" in result:
                compilation_result = result["compilation_result"]
                raw_output = compilation_result.get("stdout", "") + compilation_result.get("stderr", "")
            
            if not errors_data and "compilation_result" in result:
                compilation_result = result["compilation_result"]
                errors_data = compilation_result.get("errors", [])
            
            # 检查编译输出中的统计信息
            import re
            error_count_match = re.search(r'COMPILE RESULT:(?:FAIL|PASS) \{ERROR:(\d+) WARN:(\d+)\}', raw_output)
            if error_count_match:
                error_count = int(error_count_match.group(1))
                warn_count = int(error_count_match.group(2))
                logger.info(f"  编译统计: {error_count}个错误, {warn_count}个警告")
                
                # 如果统计显示没有错误，但返回了错误对象，可能是误报
                if error_count == 0 and errors_data:
                    logger.info(f"  编译统计显示没有实际错误 (ERROR:0)，但返回了{len(errors_data)}个错误对象，可能是误报")
                    # 过滤掉可能的误报，只保留真正的错误
                    errors_data = [error for error in errors_data if error.get("type", "").lower() == "error"]
            
            if self.current_task_type == TaskType.ERROR_FIXING:
                # 错误修复阶段，比较修复前后的错误
                previous_error_count = len(self.compile_errors)
                logger.info(f"  修复验证: 编译错误从{previous_error_count}个变为{len(errors_data)}个")
                
                # 清除之前的编译错误，添加新的
                self.compile_errors.clear()
                
                for error_data in errors_data:
                    error = ErrorInfo(
                        file_path=error_data.get("file", "unknown"),
                        error_type="compile", 
                        message=error_data.get("message", "Unknown compile error"),
                        line=error_data.get("line"),
                        severity=error_data.get("type", "error"),
                        raw_output=raw_output  # 保存原始输出
                    )
                    self.add_error(error)
                    
                if len(errors_data) < previous_error_count:
                    logger.info(f"  修复效果: 编译错误减少了{previous_error_count - len(errors_data)}个")
                elif len(errors_data) == 0:
                    logger.info(f"  修复成功: 所有编译错误已解决")
            else:
                # 初始编译检查阶段
                logger.info(f"  初始编译: 发现{len(errors_data)}个编译错误")
                
                for error_data in errors_data:
                    error = ErrorInfo(
                        file_path=error_data.get("file", "unknown"),
                        error_type="compile", 
                        message=error_data.get("message", "Unknown compile error"),
                        line=error_data.get("line"),
                        severity=error_data.get("type", "error"),
                        raw_output=raw_output  # 保存原始输出
                    )
                    self.add_error(error)
                    
                logger.info(f"  编译错误已添加到上下文: 总计{len(self.compile_errors)}个编译错误")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "session_id": self.session_id,
            "user_requirement": self.user_requirement,
            "current_phase": self.current_phase.value,
            "current_task_type": self.current_task_type.value,
            "project_analysis": self.project_analysis,
            "planned_files": [file.__dict__ for file in self.planned_files],
            "search_results": self.search_results,
            "reference_materials": self.reference_materials,
            "generated_files": [file.__dict__ for file in self.generated_files],
            "lint_errors": [error.__dict__ for error in self.lint_errors],
            "compile_errors": [error.__dict__ for error in self.compile_errors],
            "fix_attempts": self.fix_attempts,
            "current_errors": [error.__dict__ for error in self.current_errors],
            "workflow_completed": self.workflow_completed
        }
    
    def _generate_specific_error_keywords(self, error: ErrorInfo) -> List[str]:
        """根据错误类型生成精确的搜索关键词"""
        base_keywords = ["HarmonyOS", "ArkTS"]
        
        if "Resource Pack Error" in error.message:
            return base_keywords + ["string.json 格式错误", "element 资源目录", "JSON 资源文件 修复"]
        elif "CompileResource" in error.message:
            return base_keywords + ["@Entry @Component 语法", "组件定义 编译错误", "ArkTS 代码 修复"]
        elif "Tools execution failed" in error.message:
            return base_keywords + ["hvigor 构建失败", "build tools 错误", "构建工具 解决方案"]
        elif "Build failed" in error.message:
            return base_keywords + ["整体构建失败", "module.json5 配置", "项目结构 错误"]
        else:
            return base_keywords + ["代码错误 修复", "编译问题 解决"]
    
    def _build_fallback_error_query(self) -> str:
        """构建备用的错误搜索查询"""
        return "HarmonyOS ArkTS 编译错误 修复 解决方案"