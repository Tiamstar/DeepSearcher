#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
协作式工作流管理器 - 真正实现Agent间的协作
"""

import logging
from typing import Dict, Any, Optional
import asyncio
from .workflow_context import (
    WorkflowContext, WorkflowPhase, TaskType, FileInfo, ErrorInfo
)

logger = logging.getLogger(__name__)


class CollaborativeWorkflowManager:
    """协作式工作流管理器"""
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.active_contexts: Dict[str, WorkflowContext] = {}
    
    async def execute_harmonyos_workflow(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """执行鸿蒙完整开发工作流"""
        logger.info(f"🚀 开始协作式鸿蒙工作流")
        logger.info(f"   - 会话ID: {session_id}")
        logger.info(f"   - 用户需求: {user_input}")
        
        # 创建工作流上下文
        context = WorkflowContext(
            session_id=session_id,
            user_requirement=user_input,
            current_phase=WorkflowPhase.REQUIREMENT_ANALYSIS,
            current_task_type=TaskType.INITIAL_GENERATION
        )
        
        logger.info(f"✅ 工作流上下文创建成功")
        logger.info(f"   - 初始阶段: {context.current_phase.value}")
        logger.info(f"   - 任务类型: {context.current_task_type.value}")
        
        self.active_contexts[session_id] = context
        
        try:
            # 执行完整工作流 - 添加超时控制
            logger.info("📋 开始执行完整工作流")
            success = await asyncio.wait_for(
                self._execute_complete_workflow(context), 
                timeout=300.0  # 5分钟超时
            )
            
            logger.info(f"📊 工作流执行结果: {'成功' if success else '失败'}")
            logger.info(f"   - 工作流完成: {context.workflow_completed}")
            logger.info(f"   - 生成文件数: {len(context.generated_files)}")
            logger.info(f"   - 错误修复次数: {context.fix_attempts}")
            
            return {
                "status": "success" if success else "failed",
                "session_id": session_id,
                "workflow_completed": context.workflow_completed,
                "generated_files": len(context.generated_files),
                "errors_fixed": context.fix_attempts,
                "final_context": context.to_dict()
            }
            
        except asyncio.TimeoutError:
            logger.error(f"❌ 工作流执行超时: 5分钟")
            return {
                "status": "failed",
                "session_id": session_id,
                "error": "工作流执行超时",
                "context": context.to_dict() if hasattr(context, 'to_dict') else {}
            }
        except Exception as e:
            logger.error(f"❌ 工作流执行失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return {
                "status": "failed",
                "session_id": session_id,
                "error": str(e),
                "context": context.to_dict() if hasattr(context, 'to_dict') else {}
            }
        
        finally:
            # 清理上下文（可选，用于调试时保留）
            # del self.active_contexts[session_id]
            pass
    
    async def _execute_complete_workflow(self, context: WorkflowContext) -> bool:
        """执行完整工作流 - 严格按照用户定义的流程"""
        try:
            # 工作流一：初始代码生成工作流
            logger.info("=== 工作流一：初始代码生成 ===")
            
            # 1. 需求分析
            success = await self._step_requirement_analysis(context)
            if not success:
                return False
            
            # 2. 信息搜索
            success = await self._step_information_search(context)
            if not success:
                return False
            
            # 3. 代码生成
            success = await self._step_code_generation(context)
            if not success:
                return False
            
            # 4. 静态检查 (codelinter)
            success = await self._step_static_check(context)
            if not success:
                return False
            
            # 检查是否有静态检查错误
            if len(context.lint_errors) > 0:
                logger.info(f"静态检查发现错误，开始工作流二")
                return await self._execute_error_fixing_workflow(context)
            
            # 5. 编译检查 (hvigorw)
            success = await self._step_compile_check(context)
            if not success:
                return False
            
            # 6. 检查编译结果
            if len(context.compile_errors) > 0:
                logger.info(f"编译检查发现错误，开始工作流二")
                return await self._execute_error_fixing_workflow(context)
            
            # 工作流一成功完成
            context.workflow_completed = True
            logger.info("✅ 工作流一完成：代码生成成功，无错误")
            return True
            
        except Exception as e:
            logger.error(f"工作流一执行异常: {e}")
            return False
    
    async def _step_requirement_analysis(self, context: WorkflowContext) -> bool:
        """步骤1：需求分析和项目规划"""
        logger.info("=== 📋 执行步骤1: 需求分析和项目规划 ===")
        
        context.current_phase = WorkflowPhase.REQUIREMENT_ANALYSIS
        context.current_task_type = TaskType.INITIAL_GENERATION
        
        try:
            # 调用项目管理Agent
            agent_context = context.get_generation_context_for_agent("project_manager")
            logger.info(f"📤 发送给项目管理Agent的上下文: {list(agent_context.keys())}")
            logger.info(f"   - 用户需求: {agent_context.get('user_requirement', 'N/A')}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "project_manager", 
                    "project.analyze_harmonyos", 
                    agent_context
                ),
                timeout=60.0  # 1分钟超时
            )
            
            logger.info(f"📥 项目管理Agent返回结果: success={result.get('success')}")
            if result.get("success"):
                logger.info(f"   - 计划文件数: {len(result.get('planned_files', []))}")
                logger.info(f"   - 分析结果: {result.get('analysis', {}).get('main_functionality', 'N/A')}")
                for i, file_plan in enumerate(result.get('planned_files', [])[:3]):  # 显示前3个
                    logger.info(f"     文件{i+1}: {file_plan.get('path', 'N/A')}")
            else:
                logger.error(f"❌ 项目管理Agent执行失败: {result}")
                return False
            
            # 更新上下文
            context.update_from_agent_result("project_manager", result)
            
            logger.info(f"✅ 需求分析完成，规划了{len(context.planned_files)}个文件")
            return True
            
        except Exception as e:
            logger.error(f"❌ 需求分析失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _step_information_search(self, context: WorkflowContext) -> bool:
        """步骤2：信息搜索"""
        logger.info("=== 🔍 执行步骤2: 信息搜索 ===")
        
        context.current_phase = WorkflowPhase.INFORMATION_SEARCH
        
        try:
            # 调用搜索Agent
            agent_context = context.get_generation_context_for_agent("search")
            logger.info(f"📤 发送给搜索Agent的上下文: {list(agent_context.keys())}")
            logger.info(f"   - 搜索查询: {agent_context.get('query', 'N/A')}")
            logger.info(f"   - 搜索模式: {agent_context.get('search_mode', 'N/A')}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "search", 
                    "search.harmonyos", 
                    agent_context
                ),
                timeout=90.0  # 1.5分钟超时
            )
            
            logger.info(f"📥 搜索Agent返回结果: success={result.get('success')}")
            if result.get("success"):
                logger.info(f"   - 搜索方法: {result.get('search_method', 'N/A')}")
                logger.info(f"   - 资源数量: {len(result.get('sources', []))}")
                logger.info(f"   - 答案长度: {len(result.get('answer', ''))}")
                logger.info(f"   - 答案预览: {result.get('answer', '')[:100]}...")
            else:
                logger.error(f"❌ 搜索Agent执行失败: {result}")
                return False
            
            # 更新上下文
            context.update_from_agent_result("search", result)
            
            logger.info(f"✅ 信息搜索完成，获得{len(context.reference_materials)}个参考资料")
            return True
            
        except Exception as e:
            logger.error(f"❌ 信息搜索失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _step_code_generation(self, context: WorkflowContext) -> bool:
        """步骤3：代码生成"""
        logger.info("=== 💻 执行步骤3: 代码生成 ===")
        
        context.current_phase = WorkflowPhase.CODE_GENERATION
        
        try:
            # 调用代码生成Agent
            agent_context = context.get_generation_context_for_agent("code_generator")
            logger.info(f"📤 发送给代码生成Agent的上下文: {list(agent_context.keys())}")
            logger.info(f"   - 任务类型: {agent_context.get('current_task_type', 'N/A')}")
            logger.info(f"   - 计划文件数: {len(agent_context.get('planned_files', []))}")
            logger.info(f"   - 参考资料数: {len(agent_context.get('reference_materials', []))}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "code_generator", 
                    "code.generate_harmonyos", 
                    agent_context
                ),
                timeout=120.0  # 2分钟超时
            )
            
            logger.info(f"📥 代码生成Agent返回结果: success={result.get('success')}")
            if result.get("success"):
                logger.info(f"   - 生成文件数: {len(result.get('generated_files', []))}")
                logger.info(f"   - 任务类型: {result.get('task_type', 'N/A')}")
                for i, file_info in enumerate(result.get('generated_files', [])[:3]):
                    logger.info(f"     文件{i+1}: {file_info.get('path', 'N/A')}")
            else:
                logger.error(f"❌ 代码生成Agent执行失败: {result}")
                return False
            
            # 更新上下文
            context.update_from_agent_result("code_generator", result)
            
            logger.info(f"✅ 代码生成完成，生成了{len(context.generated_files)}个文件")
            return True
            
        except Exception as e:
            logger.error(f"❌ 代码生成失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _step_static_check(self, context: WorkflowContext) -> bool:
        """步骤4：静态检查"""
        logger.info("=== 🔍 执行步骤4: 静态检查 (codelinter) ===")
        
        context.current_phase = WorkflowPhase.STATIC_CHECK
        
        try:
            # 调用代码检查Agent
            agent_context = context.get_generation_context_for_agent("code_checker")
            logger.info(f"📤 发送给代码检查Agent的上下文: {list(agent_context.keys())}")
            logger.info(f"   - 检查文件数: {len(agent_context.get('files_to_check', []))}")
            logger.info(f"   - 项目路径: {agent_context.get('project_path', 'N/A')}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "code_checker", 
                    "code.check.harmonyos", 
                    agent_context
                ),
                timeout=90.0  # 1.5分钟超时
            )
            
            logger.info(f"📥 代码检查Agent返回结果: success={result.get('success')}")
            
            # 不管检查是否成功，都要更新上下文和记录错误
            context.update_from_agent_result("code_checker", result)
            
            total_errors = result.get('total_errors', 0)
            total_warnings = result.get('total_warnings', 0)
            
            if result.get("success"):
                logger.info(f"   - 错误数量: {total_errors}")
                logger.info(f"   - 警告数量: {total_warnings}")
                logger.info(f"   - 检查类型: {result.get('check_type', 'N/A')}")
                
                # 检查是否有lint错误
                if len(context.lint_errors) > 0:
                    logger.warning(f"⚠️ 静态检查发现 {len(context.lint_errors)} 个错误，需要立即修复")
                    return True  # 有错误但检查成功，继续到编译步骤让编译检查也运行
                else:
                    logger.info(f"✅ 静态检查成功，无错误")
                    return True
            else:
                # 静态检查失败
                logger.error(f"❌ 静态检查失败")
                logger.info(f"   - 错误数量: {total_errors}")
                logger.info(f"   - 警告数量: {total_warnings}")
                logger.info(f"   - 检查类型: {result.get('check_type', 'N/A')}")
                logger.info(f"   - 错误信息: {result.get('error', 'N/A')}")
                return False  # 检查失败，停止工作流
            
            logger.info(f"📋 静态检查完成，发现{len(context.lint_errors)}个lint错误")
            
        except Exception as e:
            logger.error(f"❌ 静态检查失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _step_compile_check(self, context: WorkflowContext) -> bool:
        """步骤5：编译检查"""
        logger.info("=== 🔧 执行步骤5: 编译检查 (hvigorw) ===")
        
        context.current_phase = WorkflowPhase.COMPILE_CHECK
        
        try:
            # 调用项目管理Agent进行编译检查（按照设计规范）
            agent_context = context.get_generation_context_for_agent("project_manager")
            logger.info(f"📤 发送给项目管理Agent的编译上下文: {list(agent_context.keys())}")
            logger.info(f"   - 项目路径: {agent_context.get('project_path', 'N/A')}")
            logger.info(f"   - 任务描述: {agent_context.get('task_description', 'N/A')}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "project_manager", 
                    "project.hvigor_compile", 
                    agent_context
                ),
                timeout=180.0  # 3分钟超时
            )
            
            logger.info(f"📥 项目管理Agent编译结果: success={result.get('success')}")
            
            # 不管编译是否成功，都要更新上下文和记录错误
            context.update_from_agent_result("project_manager", result)
            
            compile_result = result.get('compile_result', {})
            errors = compile_result.get('errors', [])
            warnings = compile_result.get('warnings', [])
            
            logger.info(f"   - 编译状态: {compile_result.get('status', 'N/A')}")
            logger.info(f"   - 返回码: {compile_result.get('returncode', 'N/A')}")
            logger.info(f"   - 错误数量: {len(errors)}")
            logger.info(f"   - 警告数量: {len(warnings)}")
            
            if result.get("success"):
                # 检查是否有编译错误
                if len(context.compile_errors) > 0:
                    logger.warning(f"⚠️ 编译检查发现 {len(context.compile_errors)} 个编译错误，继续到错误修复")
                    return True  # 有错误，继续到错误修复步骤
                else:
                    logger.info(f"✅ 编译检查成功，无错误")
                    return True
            else:
                # 编译检查失败，但仍然继续到错误修复步骤
                logger.warning(f"⚠️ 编译检查失败，但继续到错误修复步骤")
                logger.info(f"   - 错误信息: {result.get('error', 'N/A')}")
                
                # 显示前几个错误
                for i, error in enumerate(errors[:2]):
                    logger.info(f"     错误{i+1}: {error.get('message', 'N/A')}")
                
                # 即使编译检查失败，也继续到错误修复步骤
                # 因为可能有编译错误被记录到context中
                if len(context.compile_errors) > 0:
                    logger.info(f"检测到 {len(context.compile_errors)} 个编译错误，将进入修复流程")
                    return True
                else:
                    # 编译检查失败但没有具体错误信息
                    logger.error(f"❌ 编译检查失败且无法获取错误信息，停止工作流")
                    return False
            
            logger.info(f"📋 编译检查完成，发现{len(context.compile_errors)}个编译错误")
            
        except Exception as e:
            logger.error(f"❌ 编译检查失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _execute_error_fixing_workflow(self, context: WorkflowContext) -> bool:
        """工作流二：错误修复工作流"""
        logger.info("=== 工作流二：错误修复 ===")
        
        max_fix_attempts = 3
        fix_attempt = 0
        
        while fix_attempt < max_fix_attempts:
            fix_attempt += 1
            logger.info(f"错误修复循环 第{fix_attempt}次")
            
            # 设置修复上下文
            context.current_task_type = TaskType.ERROR_FIXING
            context.fix_attempts = fix_attempt
            context.prepare_for_fixing()  # 准备修复阶段，合并所有错误到current_errors
            
            # 1. 项目管理Agent分析错误并生成搜索关键词
            logger.info("=== 🔍 执行步骤1: 项目管理Agent错误分析 ===")
            success = await self._substep_analyze_errors(context)
            if not success:
                logger.warning(f"第{fix_attempt}次错误分析失败，使用原始错误信息继续")
            
            # 2. 搜索Agent根据关键词搜索解决方案
            logger.info("=== 🔍 执行步骤2: 搜索错误解决方案 ===")
            success = await self._substep_search_solutions(context)
            if not success:
                logger.warning(f"第{fix_attempt}次搜索解决方案失败，尝试继续")
            
            # 3. 代码生成Agent参考解决方案进行修复
            logger.info("=== 🔍 执行步骤3: 代码生成Agent修复代码 ===")
            success = await self._step_code_generation(context)
            if not success:
                logger.error(f"第{fix_attempt}次修复失败")
                continue
            
            # 4. 重新进行静态检查
            logger.info("=== 🔍 执行步骤4: 重新静态检查 ===")
            success = await self._step_static_check(context)
            if not success:
                continue
                
            # 5. 重新进行编译检查
            logger.info("=== 🔍 执行步骤5: 重新编译检查 ===")
            success = await self._step_compile_check(context)
            if not success:
                continue
            
            # 6. 检查是否还有错误
            total_errors = len(context.lint_errors) + len(context.compile_errors)
            if total_errors == 0:
                logger.info(f"✅ 第{fix_attempt}次修复成功，所有错误已解决")
                context.workflow_completed = True
                return True
            else:
                logger.info(f"第{fix_attempt}次修复后仍有{total_errors}个错误")
        
        logger.warning(f"错误修复工作流完成，但仍有未解决的错误")
        return True  # 即使有错误也返回True，让工作流完成
    
    async def _step_error_fixing_loop(self, context: WorkflowContext) -> bool:
        """步骤6：错误修复循环"""
        logger.info("=== 📋 执行步骤6: 错误修复循环 ===")
        
        # 在循环开始前显示详细状态
        logger.info(f"📊 错误修复循环开始前状态:")
        logger.info(f"   - 当前修复次数: {context.fix_attempts}")
        logger.info(f"   - 最大修复次数: {context.max_fix_attempts}")
        logger.info(f"   - 是否应该继续: {context.should_continue_fixing}")
        logger.info(f"   - 是否有错误: {context.has_errors()}")
        logger.info(f"   - 可以继续修复: {context.can_continue_fixing()}")
        
        while context.can_continue_fixing():
            logger.info(f"🔄 开始第{context.fix_attempts + 1}次错误修复")
            
            # 准备修复上下文
            context.prepare_for_fixing()
            
            # 6.1 项目管理Agent分析错误并确定修复策略
            success = await self._substep_analyze_errors(context)
            if not success:
                logger.warning("错误分析失败，尝试继续")
            
            # 6.2 搜索错误解决方案
            success = await self._substep_search_solutions(context)
            if not success:
                logger.warning("搜索解决方案失败，尝试继续")
            
            # 6.3 修复代码
            success = await self._substep_fix_code(context)
            if not success:
                logger.error("代码修复失败")
                break
            
            # 6.4 重新检查
            success = await self._substep_recheck_code(context)
            if not success:
                logger.error("重新检查失败")
                break
            
            # 检查是否还有错误
            if not context.has_errors():
                logger.info("所有错误已修复")
                break
            
            logger.info(f"第{context.fix_attempts}次修复后仍有{len(context.current_errors)}个错误")
        
        if context.has_errors():
            logger.warning(f"修复完成但仍有{len(context.get_all_errors())}个未解决的错误")
        
        return True
    
    async def _substep_analyze_errors(self, context: WorkflowContext) -> bool:
        """子步骤：项目管理Agent分析错误"""
        try:
            logger.info("=== 子步骤: 项目管理Agent分析错误 ===")
            
            agent_context = context.get_generation_context_for_agent("project_manager")
            logger.info(f"📤 发送给项目管理Agent的错误分析上下文: {list(agent_context.keys())}")
            logger.info(f"   - 错误数量: {len(agent_context.get('current_errors', []))}")
            logger.info(f"   - 受影响文件: {agent_context.get('affected_files', [])}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "project_manager", 
                    "project.analyze_harmonyos", 
                    agent_context
                ),
                timeout=60.0  # 1分钟超时
            )
            
            logger.info(f"📥 项目管理Agent错误分析结果: success={result.get('success')}")
            if result.get("success"):
                logger.info(f"   - 分析结果: {result.get('analysis', {}).get('main_functionality', 'N/A')}")
                logger.info(f"   - 修复策略: {len(result.get('fix_strategies', []))} 个策略")
                logger.info(f"   - 搜索查询: {result.get('search_queries', [])}")
            else:
                logger.error(f"❌ 项目管理Agent错误分析失败: {result}")
            
            # 更新上下文
            context.update_from_agent_result("project_manager", result)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 错误分析失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _substep_search_solutions(self, context: WorkflowContext) -> bool:
        """子步骤：搜索错误解决方案"""
        try:
            logger.info("=== 子步骤: 搜索Agent搜索错误解决方案 ===")
            
            agent_context = context.get_generation_context_for_agent("search")
            logger.info(f"📤 发送给搜索Agent的上下文: {list(agent_context.keys())}")
            logger.info(f"   - 搜索查询: {agent_context.get('query', 'N/A')}")
            logger.info(f"   - 搜索模式: {agent_context.get('search_mode', 'N/A')}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "search", 
                    "search.harmonyos", 
                    agent_context
                ),
                timeout=90.0  # 1.5分钟超时
            )
            
            logger.info(f"📥 搜索Agent返回结果: success={result.get('success')}")
            if result.get("success"):
                logger.info(f"   - 搜索方法: {result.get('search_method', 'N/A')}")
                logger.info(f"   - 资源数量: {len(result.get('sources', []))}")
                logger.info(f"   - 答案长度: {len(result.get('answer', ''))}")
            else:
                logger.error(f"❌ 搜索Agent执行失败: {result}")
            
            context.update_from_agent_result("search", result)
            return True
            
        except Exception as e:
            logger.error(f"搜索解决方案失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _substep_fix_code(self, context: WorkflowContext) -> bool:
        """子步骤：修复代码"""
        try:
            logger.info("=== 子步骤: 代码生成Agent修复代码 ===")
            
            agent_context = context.get_generation_context_for_agent("code_generator")
            logger.info(f"📤 发送给代码生成Agent的修复上下文: {list(agent_context.keys())}")
            logger.info(f"   - 任务类型: {agent_context.get('current_task_type', 'N/A')}")
            logger.info(f"   - 错误数量: {len(agent_context.get('errors_to_fix', []))}")
            logger.info(f"   - 参考资料数: {len(agent_context.get('solution_references', []))}")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "code_generator", 
                    "code.generate_harmonyos", 
                    agent_context
                ),
                timeout=120.0  # 2分钟超时
            )
            
            logger.info(f"📥 代码生成Agent修复结果: success={result.get('success')}")
            if result.get("success"):
                logger.info(f"   - 修复文件数: {len(result.get('generated_files', []))}")
                logger.info(f"   - 任务类型: {result.get('task_type', 'N/A')}")
            else:
                logger.error(f"❌ 代码生成Agent修复失败: {result}")
            
            context.update_from_agent_result("code_generator", result)
            context.clear_current_errors()  # 清除当前错误，准备重新检查
            return True
            
        except Exception as e:
            logger.error(f"代码修复失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _substep_recheck_code(self, context: WorkflowContext) -> bool:
        """子步骤：重新检查代码"""
        try:
            # 重新进行静态检查
            context.current_phase = WorkflowPhase.STATIC_CHECK
            agent_context = context.get_generation_context_for_agent("code_checker")
            result = await self.coordinator._execute_agent_method(
                "code_checker", 
                "code.check.harmonyos", 
                agent_context
            )
            context.update_from_agent_result("code_checker", result)
            
            # 重新进行编译检查（使用项目管理Agent）
            context.current_phase = WorkflowPhase.COMPILE_CHECK
            agent_context = context.get_generation_context_for_agent("project_manager")
            result = await self.coordinator._execute_agent_method(
                "project_manager", 
                "project.hvigor_compile", 
                agent_context
            )
            context.update_from_agent_result("project_manager", result)
            
            return True
            
        except Exception as e:
            logger.error(f"重新检查失败: {e}")
            return False
    
    def get_workflow_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        if session_id not in self.active_contexts:
            return None
        
        context = self.active_contexts[session_id]
        return {
            "session_id": session_id,
            "current_phase": context.current_phase.value,
            "current_task_type": context.current_task_type.value,
            "fix_attempts": context.fix_attempts,
            "has_errors": context.has_errors(),
            "error_count": len(context.get_all_errors()),
            "completed": context.workflow_completed
        }