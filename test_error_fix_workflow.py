#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误修复工作流专用测试入口 - 工作流二测试工具
专门用于测试错误修复工作流，从现有错误代码开始进行静态检查、编译检查和循环修复
"""

import argparse
import asyncio
import json
import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_orchestrator import MCPCoordinator
from mcp_orchestrator.collaborative_workflow import CollaborativeWorkflowManager
from mcp_orchestrator.workflow_context import (
    WorkflowContext, WorkflowPhase, TaskType, FileInfo, ErrorInfo
)
from shared.config_loader import ConfigLoader

# 配置日志 - 强制显示
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('error_fix_workflow_test.log')
    ],
    force=True  # Python 3.8+ 强制重新配置
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 确保根logger也输出
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)


class ErrorFixWorkflowTester:
    """错误修复工作流测试器"""
    
    def __init__(self):
        self.coordinator = None
        self.workflow_manager = None
        self.config_loader = ConfigLoader()
    
    async def initialize(self, config_file: str = None) -> bool:
        """初始化协调器和工作流管理器"""
        try:
            # 加载配置
            if config_file:
                config = self.config_loader.load_config(config_file)
            else:
                config = self.config_loader.get_unified_config()
                if not config:
                    logger.warning("统一配置为空，使用默认配置")
                    config = self.config_loader._get_default_unified_config()
            
            # 创建协调器
            print("🔧 正在创建MCP协调器...")
            self.coordinator = MCPCoordinator(config)
            print("🔧 正在初始化协调器...")
            await self.coordinator.initialize()
            
            # 创建协作式工作流管理器
            print("🔧 正在创建协作式工作流管理器...")
            self.workflow_manager = CollaborativeWorkflowManager(self.coordinator)
            
            print("🚀 错误修复工作流测试器初始化成功")
            logger.info("🚀 错误修复工作流测试器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False
    
    async def test_error_fix_workflow(self, user_requirement: str = "测试错误修复工作流", 
                                    session_id: str = None) -> Dict[str, Any]:
        """
        测试错误修复工作流二
        
        Args:
            user_requirement: 模拟用户需求（用于搜索关键词生成）
            session_id: 会话ID，如果不提供则自动生成
        
        Returns:
            工作流执行结果
        """
        try:
            if not session_id:
                session_id = f"error_fix_test_{int(time.time())}"
            
            print("=" * 80)
            print("🔧 开始测试错误修复工作流二")
            print(f"   - 会话ID: {session_id}")
            print(f"   - 用户需求: {user_requirement}")
            print(f"   - 测试目标: Index.ets文件的错误检查和修复")
            print("=" * 80)
            
            logger.info("=" * 80)
            logger.info("🔧 开始测试错误修复工作流二")
            logger.info(f"   - 会话ID: {session_id}")
            logger.info(f"   - 用户需求: {user_requirement}")
            logger.info(f"   - 测试目标: Index.ets文件的错误检查和修复")
            logger.info("=" * 80)
            
            # 1. 检查Index.ets文件是否存在
            index_file_path = "/home/deepsearch/deep-searcher/MyApplication2/entry/src/main/ets/pages/Index.ets"
            if not os.path.exists(index_file_path):
                return {
                    "success": False,
                    "error": f"Index.ets文件不存在: {index_file_path}",
                    "suggestion": "请确保Index.ets文件已准备好并包含有错误的代码"
                }
            
            # 2. 创建错误修复工作流上下文
            context = self._create_error_fix_context(session_id, user_requirement, index_file_path)
            
            logger.info("✅ 错误修复工作流上下文创建成功")
            logger.info(f"   - 当前阶段: {context.current_phase.value}")
            logger.info(f"   - 任务类型: {context.current_task_type.value}")
            logger.info(f"   - 目标文件: {index_file_path}")
            
            # 3. 首先执行静态检查（代码检查Agent）
            logger.info("\n🔍 步骤1: 执行静态检查 (codelinter)")
            static_check_success = await self._execute_static_check(context)
            if not static_check_success:
                return {
                    "success": False,
                    "error": "静态检查失败",
                    "context": context.to_dict()
                }
            
            # 4. 执行编译检查（项目管理Agent）
            logger.info("\n🔧 步骤2: 执行编译检查 (hvigorw)")
            compile_check_success = await self._execute_compile_check(context)
            if not compile_check_success:
                return {
                    "success": False,
                    "error": "编译检查失败",
                    "context": context.to_dict()
                }
            
            # 5. 检查是否有错误需要修复 - 使用正确的错误检查方法
            has_actual_errors = context.has_errors()
            total_lint_count = len(context.lint_errors)
            total_compile_count = len(context.compile_errors)
            
            print(f"\n📊 错误检查结果:")
            print(f"   - 静态检查错误列表数量: {total_lint_count}")
            print(f"   - 编译错误列表数量: {total_compile_count}")
            print(f"   - 实际有错误需要修复: {has_actual_errors}")
            
            if not has_actual_errors:
                logger.info("✅ 没有发现实际错误，无需进入修复工作流")
                return {
                    "success": True,
                    "message": "代码检查通过，没有发现实际错误",
                    "static_errors": total_lint_count,
                    "compile_errors": total_compile_count,
                    "actual_errors": False,
                    "context": context.to_dict()
                }
            
            print(f"\n⚠️ 发现实际错误，开始执行错误修复工作流")
            logger.info(f"\n⚠️ 发现实际错误，开始执行错误修复工作流")
            logger.info(f"   - 静态检查错误列表: {total_lint_count}个")
            logger.info(f"   - 编译错误列表: {total_compile_count}个")
            logger.info(f"   - 实际需要修复: {has_actual_errors}")
            
            # 6. 执行错误修复工作流
            logger.info("\n🔄 开始执行错误修复循环")
            fix_result = await self.workflow_manager._execute_error_fixing_workflow(context)
            
            # 7. 生成最终结果
            final_result = self._generate_final_result(context, fix_result)
            
            logger.info("\n" + "=" * 80)
            logger.info("📊 错误修复工作流测试完成")
            self._print_test_summary(final_result)
            logger.info("=" * 80)
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 错误修复工作流测试失败: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "context": context.to_dict() if 'context' in locals() else {}
            }
    
    def _create_error_fix_context(self, session_id: str, user_requirement: str, 
                                 index_file_path: str) -> WorkflowContext:
        """创建错误修复工作流上下文"""
        # 读取当前Index.ets文件内容
        try:
            with open(index_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            logger.warning(f"无法读取Index.ets文件: {e}")
            file_content = ""
        
        # 创建工作流上下文，直接设置为错误修复模式
        context = WorkflowContext(
            session_id=session_id,
            user_requirement=user_requirement,
            current_phase=WorkflowPhase.STATIC_CHECK,  # 从静态检查开始
            current_task_type=TaskType.INITIAL_GENERATION  # 先设为初始生成，检查后会切换为修复
        )
        
        # 添加现有文件信息
        existing_file = FileInfo(
            path="MyApplication2/entry/src/main/ets/pages/Index.ets",
            type="arkts",
            content=file_content,
            status="generated"  # 假设文件已存在
        )
        context.generated_files.append(existing_file)
        
        return context
    
    async def _execute_static_check(self, context: WorkflowContext) -> bool:
        """执行静态检查"""
        try:
            context.current_phase = WorkflowPhase.STATIC_CHECK
            
            # 调用代码检查Agent
            agent_context = context.get_generation_context_for_agent("code_checker")
            logger.info(f"📤 发送给代码检查Agent的上下文: {list(agent_context.keys())}")
            logger.info(f"   - 检查文件数: {len(agent_context.get('files_to_check', []))}")
            logger.info(f"   - 项目路径: MyApplication2")
            
            result = await asyncio.wait_for(
                self.coordinator._execute_agent_method(
                    "code_checker", 
                    "code.check.harmonyos", 
                    agent_context
                ),
                timeout=90.0  # 1.5分钟超时
            )
            
            logger.info(f"📥 代码检查Agent返回结果: success={result.get('success')}")
            
            # 更新上下文
            context.update_from_agent_result("code_checker", result)
            
            total_errors = result.get('total_errors', 0)
            total_warnings = result.get('total_warnings', 0)
            
            if result.get("success"):
                logger.info(f"   - 错误数量: {total_errors}")
                logger.info(f"   - 警告数量: {total_warnings}")
                logger.info(f"   - 检查类型: {result.get('check_type', 'N/A')}")
                
                if len(context.lint_errors) > 0:
                    logger.warning(f"⚠️ 静态检查发现 {len(context.lint_errors)} 个错误")
                else:
                    logger.info(f"✅ 静态检查成功，无错误")
                return True
            else:
                logger.error(f"❌ 静态检查失败: {result.get('error', 'N/A')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 静态检查执行失败: {e}")
            return False
    
    async def _execute_compile_check(self, context: WorkflowContext) -> bool:
        """执行编译检查"""
        try:
            context.current_phase = WorkflowPhase.COMPILE_CHECK
            
            # 调用项目管理Agent进行编译检查
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
            
            # 更新上下文
            context.update_from_agent_result("project_manager", result)
            
            compile_result = result.get('compile_result', {})
            errors = compile_result.get('errors', [])
            warnings = compile_result.get('warnings', [])
            
            logger.info(f"   - 编译状态: {compile_result.get('status', 'N/A')}")
            logger.info(f"   - 返回码: {compile_result.get('returncode', 'N/A')}")
            logger.info(f"   - 错误数量: {len(errors)}")
            logger.info(f"   - 警告数量: {len(warnings)}")
            
            if result.get("success"):
                if len(context.compile_errors) > 0:
                    logger.warning(f"⚠️ 编译检查发现 {len(context.compile_errors)} 个编译错误")
                else:
                    logger.info(f"✅ 编译检查成功，无错误")
                return True
            else:
                logger.warning(f"⚠️ 编译检查失败: {result.get('error', 'N/A')}")
                # 显示前几个错误
                for i, error in enumerate(errors[:2]):
                    logger.info(f"     错误{i+1}: {error.get('message', 'N/A')}")
                return True  # 即使编译失败也继续，让修复工作流处理
                
        except Exception as e:
            logger.error(f"❌ 编译检查执行失败: {e}")
            return False
    
    def _generate_final_result(self, context: WorkflowContext, fix_result: bool) -> Dict[str, Any]:
        """生成最终测试结果"""
        # 使用正确的错误检查方法
        has_actual_errors = context.has_errors()
        lint_count = len(context.lint_errors)
        compile_count = len(context.compile_errors)
        
        return {
            "success": fix_result,
            "session_id": context.session_id,
            "workflow_type": "error_fix_test",
            "test_summary": {
                "fix_attempts": context.fix_attempts,
                "max_fix_attempts": context.max_fix_attempts,
                "workflow_completed": context.workflow_completed,
                "final_error_count": lint_count + compile_count,  # 列表数量
                "actual_errors": has_actual_errors,  # 实际是否有错误
                "static_errors": lint_count,
                "compile_errors": compile_count
            },
            "generated_files": [file.__dict__ for file in context.generated_files],
            "error_details": {
                "lint_errors": [error.__dict__ for error in context.lint_errors],
                "compile_errors": [error.__dict__ for error in context.compile_errors],
                "has_actual_errors": has_actual_errors
            },
            "context": context.to_dict()
        }
    
    def _print_test_summary(self, result: Dict[str, Any]):
        """打印测试摘要"""
        success = result.get("success", False)
        test_summary = result.get("test_summary", {})
        
        print(f"\n🎯 错误修复工作流测试摘要:")
        print(f"   状态: {'✅ 成功' if success else '❌ 失败'}")
        print(f"   修复循环次数: {test_summary.get('fix_attempts', 0)}")
        print(f"   最大循环次数: {test_summary.get('max_fix_attempts', 3)}")
        print(f"   工作流完成: {test_summary.get('workflow_completed', False)}")
        print(f"   错误列表数量: {test_summary.get('final_error_count', 0)}")
        print(f"     - 静态检查错误: {test_summary.get('static_errors', 0)}")
        print(f"     - 编译错误: {test_summary.get('compile_errors', 0)}")
        print(f"   实际有错误需要修复: {test_summary.get('actual_errors', False)}")
        
        generated_files = result.get("generated_files", [])
        if generated_files:
            print(f"   修复的文件数量: {len(generated_files)}")
            for file_info in generated_files[:3]:  # 只显示前3个
                print(f"     - {file_info.get('path', 'unknown')}: {file_info.get('status', 'unknown')}")
        
        # 根据实际错误状态显示结果
        actual_errors = test_summary.get('actual_errors', False)
        if not actual_errors:
            print(f"\n🎉 没有实际错误，检查通过！")
        elif test_summary.get('fix_attempts', 0) >= test_summary.get('max_fix_attempts', 3):
            print(f"\n⚠️ 达到最大修复次数，但仍有未解决的错误")
        
        print(f"\n📝 说明:")
        print(f"   - 此测试专门验证错误修复工作流二的功能")
        print(f"   - 从现有Index.ets文件开始进行错误检查和修复")
        print(f"   - 验证静态检查、编译检查和循环修复机制")
        print(f"   - 区分错误列表数量和实际需要修复的错误")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="错误修复工作流二专用测试工具")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--requirement", type=str, 
                       default="测试登录页面组件的错误修复", 
                       help="模拟用户需求（用于搜索关键词生成）")
    parser.add_argument("--session-id", type=str, help="会话ID")
    parser.add_argument("--output", choices=["text", "json"], default="text",
                       help="输出格式")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = ErrorFixWorkflowTester()
    
    if not await tester.initialize(args.config):
        sys.exit(1)
    
    # 执行错误修复工作流测试
    start_time = time.time()
    result = await tester.test_error_fix_workflow(
        user_requirement=args.requirement,
        session_id=args.session_id
    )
    end_time = time.time()
    
    # 输出结果
    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n⏱️ 总测试时间: {end_time - start_time:.2f}秒")
        
        if not result["success"]:
            print(f"❌ 测试失败: {result.get('error', '未知错误')}")
            if "suggestion" in result:
                print(f"💡 建议: {result['suggestion']}")


if __name__ == "__main__":
    asyncio.run(main())