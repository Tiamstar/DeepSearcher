#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Workflow Test
鸿蒙工作流测试
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_agents.harmonyos import HarmonyOSProjectAnalyzer, HarmonyOSCompilerService
from mcp_orchestrator.loop_manager import LoopManager
from mcp_orchestrator.harmonyos_workflow import HarmonyOSWorkflowManager

async def test_project_analyzer():
    """测试项目分析器"""
    print("\n=== 测试项目分析器 ===")
    
    analyzer = HarmonyOSProjectAnalyzer()
    
    # 测试项目健康检查
    project_info = analyzer.get_project_info()
    print(f"项目信息: {project_info}")
    
    # 测试需求分析
    test_requirements = [
        "创建一个用户登录页面",
        "实现一个商品列表组件",
        "添加数据存储功能"
    ]
    
    for requirement in test_requirements:
        print(f"\n分析需求: {requirement}")
        result = analyzer.analyze_requirement_and_plan_files(requirement)
        
        if result["success"]:
            print(f"  分析类型: {result['analysis']['primary_type']}")
            print(f"  复杂度: {result['analysis']['complexity']}")
            print(f"  文件计划: {len(result['file_plans'])} 个文件")
            
            for plan in result["file_plans"]:
                print(f"    - {plan['type']}: {os.path.basename(plan['path'])}")
        else:
            print(f"  分析失败: {result['error']}")

async def test_compiler_service():
    """测试编译服务"""
    print("\n=== 测试编译服务 ===")
    
    compiler = HarmonyOSCompilerService()
    
    # 测试项目健康检查
    health = compiler.check_project_health()
    print(f"项目健康状况: {health['health_status']} (得分: {health['health_score']})")
    
    if health.get("missing_files"):
        print(f"缺失文件: {health['missing_files']}")
    if health.get("missing_directories"):
        print(f"缺失目录: {health['missing_directories']}")
    
    # 测试codelinter（如果可用）
    if health.get("codelinter_available"):
        print("\n执行codelinter检查...")
        lint_result = compiler.run_codelinter_check()
        print(f"Linter结果: {'成功' if lint_result['success'] else '失败'}")
        print(f"问题数量: {lint_result.get('total_issues', 0)}")
        
        if lint_result.get("issues"):
            print("前3个问题:")
            for i, issue in enumerate(lint_result["issues"][:3]):
                print(f"  {i+1}. {issue.get('message', 'Unknown issue')}")
    else:
        print("codelinter不可用")

async def test_loop_manager():
    """测试循环管理器"""
    print("\n=== 测试循环管理器 ===")
    
    # 创建模拟协调器
    class MockCoordinator:
        pass
    
    coordinator = MockCoordinator()
    loop_manager = LoopManager(coordinator)
    
    # 测试循环启动
    session_id = "test_session_001"
    user_input = "创建一个简单的页面"
    
    context = await loop_manager.start_loop(session_id, user_input, max_iterations=2)
    print(f"循环上下文创建: {context.session_id}")
    print(f"最大迭代次数: {context.max_iterations}")
    
    # 模拟错误数据
    mock_compile_errors = [
        {
            "type": "error",
            "message": "Cannot find module 'unknown_module'",
            "file": "test.ets",
            "line": 10
        },
        {
            "type": "error", 
            "message": "Syntax error: expected ';'",
            "file": "test.ets",
            "line": 15
        }
    ]
    
    mock_static_issues = [
        {
            "severity": "error",
            "message": "Missing decorator @Component",
            "file": "test.ets",
            "line": 5,
            "rule": "decorator-required"
        }
    ]
    
    # 测试循环条件判断
    should_continue, reason = await loop_manager.should_continue_loop(
        session_id, 
        {"success": False, "errors": mock_compile_errors},
        {"success": False, "issues_found": mock_static_issues}
    )
    
    print(f"是否继续循环: {should_continue}")
    print(f"原因: {reason}")
    
    if should_continue:
        # 生成修复上下文
        fix_context = await loop_manager.generate_fix_context(session_id)
        print(f"修复上下文生成: {len(fix_context.get('fix_instructions', []))} 条指令")
        
        for instruction in fix_context.get("fix_instructions", [])[:3]:
            print(f"  - {instruction}")
    
    # 清理
    await loop_manager.cancel_loop(session_id)

async def main():
    """主测试函数"""
    print("🚀 开始鸿蒙工作流组件测试")
    
    try:
        await test_project_analyzer()
        await test_compiler_service()
        await test_loop_manager()
        
        print("\n✅ 所有测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())