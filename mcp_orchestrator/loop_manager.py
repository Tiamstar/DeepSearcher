#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Loop Manager
循环修复管理器 - 负责管理代码生成的循环修复流程
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class LoopStatus(Enum):
    """循环状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"

@dataclass
class LoopContext:
    """循环上下文"""
    session_id: str
    user_input: str
    current_iteration: int = 0
    max_iterations: int = 3
    status: LoopStatus = LoopStatus.PENDING
    errors: List[Dict[str, Any]] = None
    fix_suggestions: List[str] = None
    search_context: str = ""
    generated_files: List[Dict[str, Any]] = None
    last_error_step: str = ""
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.fix_suggestions is None:
            self.fix_suggestions = []
        if self.generated_files is None:
            self.generated_files = []

class LoopManager:
    """
    循环修复管理器
    负责：
    1. 管理循环修复流程
    2. 错误分析和修复建议生成
    3. 上下文传递和状态管理
    4. 循环条件判断和退出控制
    """
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.active_loops: Dict[str, LoopContext] = {}
        
        # 错误分类和修复策略
        self.error_categories = {
            "import_error": {
                "keywords": ["import", "module", "cannot find", "not found"],
                "search_focus": ["模块导入", "依赖配置", "包管理"],
                "priority": "high"
            },
            "syntax_error": {
                "keywords": ["syntax", "unexpected", "expected", "missing"],
                "search_focus": ["ArkTS语法", "代码规范", "语法修复"],
                "priority": "high"
            },
            "type_error": {
                "keywords": ["type", "typescript", "arkts", "interface"],
                "search_focus": ["类型定义", "接口规范", "类型检查"],
                "priority": "medium"
            },
            "decorator_error": {
                "keywords": ["decorator", "@", "component", "entry"],
                "search_focus": ["鸿蒙装饰器", "组件装饰器", "装饰器用法"],
                "priority": "medium"
            },
            "build_error": {
                "keywords": ["build", "compile", "failed", "error"],
                "search_focus": ["编译问题", "构建配置", "项目配置"],
                "priority": "high"
            }
        }
    
    async def start_loop(self, session_id: str, user_input: str, max_iterations: int = 3) -> LoopContext:
        """开始循环修复流程"""
        try:
            context = LoopContext(
                session_id=session_id,
                user_input=user_input,
                max_iterations=max_iterations,
                status=LoopStatus.RUNNING
            )
            
            self.active_loops[session_id] = context
            logger.info(f"开始循环修复流程: {session_id}, 最大迭代次数: {max_iterations}")
            
            return context
            
        except Exception as e:
            logger.error(f"启动循环修复失败: {e}")
            raise
    
    async def should_continue_loop(self, session_id: str, 
                                 compile_result: Dict[str, Any], 
                                 static_result: Dict[str, Any]) -> Tuple[bool, str]:
        """
        判断是否应该继续循环
        
        Returns:
            (should_continue, reason)
        """
        try:
            context = self.active_loops.get(session_id)
            if not context:
                return False, "循环上下文不存在"
            
            # 检查是否达到最大迭代次数
            if context.current_iteration >= context.max_iterations:
                context.status = LoopStatus.MAX_ITERATIONS_REACHED
                return False, f"达到最大迭代次数 ({context.max_iterations})"
            
            # 检查编译结果
            compile_success = compile_result.get("success", False)
            compile_errors = compile_result.get("errors", [])
            
            # 检查静态检查结果
            static_success = static_result.get("success", False)
            static_issues = static_result.get("issues_found", [])
            
            # 分析错误严重程度
            critical_errors = self._analyze_error_severity(compile_errors, static_issues)
            
            if compile_success and static_success:
                context.status = LoopStatus.SUCCESS
                return False, "编译和静态检查都成功"
            
            if critical_errors:
                context.errors.extend(critical_errors)
                context.current_iteration += 1
                logger.info(f"检测到{len(critical_errors)}个关键错误，继续修复循环 (第{context.current_iteration}次)")
                return True, f"存在{len(critical_errors)}个需要修复的错误"
            
            # 如果没有关键错误，但编译失败，也继续循环
            if not compile_success:
                context.current_iteration += 1
                logger.info(f"编译失败，继续修复循环 (第{context.current_iteration}次)")
                return True, "编译失败需要修复"
            
            context.status = LoopStatus.SUCCESS
            return False, "没有需要修复的关键错误"
            
        except Exception as e:
            logger.error(f"循环条件判断失败: {e}")
            return False, f"判断失败: {str(e)}"
    
    def _analyze_error_severity(self, compile_errors: List[Dict[str, Any]], 
                              static_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析错误严重程度，返回需要修复的关键错误"""
        critical_errors = []
        
        # 分析编译错误
        for error in compile_errors:
            if isinstance(error, dict):
                error_type = error.get("type", "").lower()
                error_message = error.get("message", "").lower()
                
                if error_type == "error" or any(keyword in error_message for keyword in ["error", "failed", "cannot"]):
                    critical_errors.append({
                        "source": "compile",
                        "type": error.get("type", "error"),
                        "message": error.get("message", ""),
                        "file": error.get("file", ""),
                        "line": error.get("line"),
                        "category": self._categorize_error(error_message)
                    })
        
        # 分析静态检查问题
        for issue in static_issues:
            if isinstance(issue, dict):
                severity = issue.get("severity", "").lower()
                issue_message = issue.get("message", "").lower()
                
                if severity == "error":
                    critical_errors.append({
                        "source": "static",
                        "type": "error",
                        "message": issue.get("message", ""),
                        "file": issue.get("file", ""),
                        "line": issue.get("line"),
                        "rule": issue.get("rule", ""),
                        "category": self._categorize_error(issue_message)
                    })
        
        return critical_errors
    
    def _categorize_error(self, error_message: str) -> str:
        """对错误进行分类"""
        error_message_lower = error_message.lower()
        
        for category, config in self.error_categories.items():
            if any(keyword in error_message_lower for keyword in config["keywords"]):
                return category
        
        return "general"
    
    async def generate_fix_context(self, session_id: str) -> Dict[str, Any]:
        """为下一次迭代生成修复上下文"""
        try:
            context = self.active_loops.get(session_id)
            if not context:
                raise ValueError(f"循环上下文不存在: {session_id}")
            
            # 分析错误模式
            error_analysis = self._analyze_error_patterns(context.errors)
            
            # 生成搜索关键词
            search_keywords = self._generate_search_keywords(context.errors)
            
            # 生成修复指导
            fix_instructions = self._generate_fix_instructions(context.errors)
            
            # 更新上下文
            context.fix_suggestions = fix_instructions
            
            fix_context = {
                "is_fixing_mode": True,
                "iteration": context.current_iteration,
                "max_iterations": context.max_iterations,
                "original_requirement": context.user_input,
                "previous_errors": context.errors,
                "error_analysis": error_analysis,
                "search_keywords": search_keywords,
                "fix_instructions": fix_instructions,
                "search_focus": self._get_search_focus(context.errors),
                "priority_areas": self._get_priority_repair_areas(context.errors)
            }
            
            logger.info(f"生成修复上下文: {len(fix_instructions)} 条修复指令")
            
            return fix_context
            
        except Exception as e:
            logger.error(f"生成修复上下文失败: {e}")
            raise
    
    def _analyze_error_patterns(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析错误模式"""
        patterns = {
            "total_errors": len(errors),
            "error_types": {},
            "affected_files": set(),
            "common_issues": [],
            "error_categories": {}
        }
        
        for error in errors:
            # 统计错误类型
            error_type = error.get("type", "unknown")
            patterns["error_types"][error_type] = patterns["error_types"].get(error_type, 0) + 1
            
            # 收集受影响的文件
            if error.get("file"):
                patterns["affected_files"].add(error["file"])
            
            # 统计错误分类
            category = error.get("category", "general")
            patterns["error_categories"][category] = patterns["error_categories"].get(category, 0) + 1
        
        patterns["affected_files"] = list(patterns["affected_files"])
        
        # 识别常见问题
        if patterns["error_categories"].get("import_error", 0) > 0:
            patterns["common_issues"].append("模块导入问题")
        if patterns["error_categories"].get("syntax_error", 0) > 0:
            patterns["common_issues"].append("语法错误")
        if patterns["error_categories"].get("type_error", 0) > 0:
            patterns["common_issues"].append("类型错误")
        
        return patterns
    
    def _generate_search_keywords(self, errors: List[Dict[str, Any]]) -> List[str]:
        """生成搜索关键词"""
        keywords = set()
        
        for error in errors:
            category = error.get("category", "general")
            if category in self.error_categories:
                keywords.update(self.error_categories[category]["search_focus"])
            
            # 从错误消息中提取关键词
            message = error.get("message", "")
            if "import" in message.lower():
                keywords.add("鸿蒙模块导入")
            if "component" in message.lower():
                keywords.add("ArkTS组件")
            if "decorator" in message.lower():
                keywords.add("鸿蒙装饰器")
        
        # 添加通用搜索词
        keywords.update(["鸿蒙开发", "ArkTS", "错误修复"])
        
        return list(keywords)[:10]  # 限制数量
    
    def _generate_fix_instructions(self, errors: List[Dict[str, Any]]) -> List[str]:
        """生成修复指令"""
        instructions = []
        
        # 按类别组织修复指令
        category_counts = {}
        for error in errors:
            category = error.get("category", "general")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 根据错误分类生成修复指令
        for category, count in category_counts.items():
            if category == "import_error":
                instructions.append(f"修复{count}个模块导入错误：检查import语句和模块路径")
            elif category == "syntax_error":
                instructions.append(f"修复{count}个语法错误：检查ArkTS语法规范")
            elif category == "type_error":
                instructions.append(f"修复{count}个类型错误：检查变量类型定义和接口")
            elif category == "decorator_error":
                instructions.append(f"修复{count}个装饰器错误：检查@Component、@Entry等装饰器用法")
            elif category == "build_error":
                instructions.append(f"修复{count}个构建错误：检查项目配置和依赖")
            else:
                instructions.append(f"修复{count}个一般错误：仔细检查代码逻辑")
        
        return instructions
    
    def _get_search_focus(self, errors: List[Dict[str, Any]]) -> List[str]:
        """获取搜索重点"""
        focus_areas = set()
        
        for error in errors:
            category = error.get("category", "general")
            if category in self.error_categories:
                focus_areas.update(self.error_categories[category]["search_focus"])
        
        return list(focus_areas)
    
    def _get_priority_repair_areas(self, errors: List[Dict[str, Any]]) -> List[str]:
        """获取优先修复区域"""
        high_priority = []
        medium_priority = []
        
        for error in errors:
            category = error.get("category", "general")
            if category in self.error_categories:
                priority = self.error_categories[category]["priority"]
                error_desc = f"{error.get('file', 'unknown')}:{error.get('line', '?')} - {error.get('message', '')[:50]}"
                
                if priority == "high":
                    high_priority.append(error_desc)
                else:
                    medium_priority.append(error_desc)
        
        return high_priority + medium_priority[:5]  # 限制数量
    
    async def update_loop_progress(self, session_id: str, step: str, result: Dict[str, Any]):
        """更新循环进度"""
        try:
            context = self.active_loops.get(session_id)
            if context:
                context.last_error_step = step
                
                # 更新生成的文件
                if "generated_files" in result:
                    context.generated_files = result["generated_files"]
                
                # 更新搜索上下文
                if "search_context" in result:
                    context.search_context = result["search_context"]
                
                logger.debug(f"更新循环进度: {session_id}, 步骤: {step}")
                
        except Exception as e:
            logger.error(f"更新循环进度失败: {e}")
    
    async def finalize_loop(self, session_id: str, final_result: Dict[str, Any]) -> Dict[str, Any]:
        """完成循环修复"""
        try:
            context = self.active_loops.get(session_id)
            if not context:
                raise ValueError(f"循环上下文不存在: {session_id}")
            
            # 准备最终结果
            result = {
                "session_id": session_id,
                "status": context.status.value,
                "total_iterations": context.current_iteration,
                "max_iterations": context.max_iterations,
                "original_requirement": context.user_input,
                "final_result": final_result,
                "total_errors_fixed": len(context.errors),
                "generated_files": context.generated_files,
                "fix_suggestions": context.fix_suggestions,
                "completion_time": datetime.now().isoformat()
            }
            
            # 清理循环上下文
            del self.active_loops[session_id]
            
            logger.info(f"循环修复完成: {session_id}, 状态: {context.status.value}, 迭代次数: {context.current_iteration}")
            
            return result
            
        except Exception as e:
            logger.error(f"完成循环修复失败: {e}")
            raise
    
    def get_loop_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取循环状态"""
        context = self.active_loops.get(session_id)
        if context:
            return {
                "session_id": session_id,
                "status": context.status.value,
                "current_iteration": context.current_iteration,
                "max_iterations": context.max_iterations,
                "total_errors": len(context.errors),
                "last_error_step": context.last_error_step
            }
        return None
    
    def get_active_loops(self) -> List[str]:
        """获取活跃循环列表"""
        return list(self.active_loops.keys())
    
    async def cancel_loop(self, session_id: str) -> bool:
        """取消循环修复"""
        try:
            if session_id in self.active_loops:
                context = self.active_loops[session_id]
                context.status = LoopStatus.FAILED
                del self.active_loops[session_id]
                logger.info(f"取消循环修复: {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"取消循环修复失败: {e}")
            return False