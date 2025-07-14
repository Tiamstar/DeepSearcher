#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Integration Test
鸿蒙系统集成测试 - 测试完整的工作流程
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_orchestrator.mcp_coordinator import MCPCoordinator
from shared.config_loader import ConfigLoader

async def test_harmonyos_workflow_integration():
    """测试鸿蒙工作流集成"""
    print("\n=== 鸿蒙工作流集成测试 ===")
    
    try:
        # 初始化配置
        config_loader = ConfigLoader()
        config = config_loader.get_unified_config()
        if not config:
            config = config_loader._get_default_unified_config()
        
        # 初始化协调器
        coordinator = MCPCoordinator(config)
        await coordinator.initialize()
        
        print("✅ MCP协调器初始化成功")
        print(f"已初始化Agent: {list(coordinator.agents.keys())}")
        
        # 测试项目管理Agent的鸿蒙功能
        print("\n--- 测试项目管理Agent ---")
        
        # 测试需求分析
        pm_agent = coordinator.agents.get("project_manager")
        if pm_agent:
            from mcp_agents.base.protocol import MCPMessage
            
            message = MCPMessage(
                id="test_001",
                method="project.analyze_harmonyos_requirements",
                params={
                    "requirement": "创建一个简单的计算器页面",
                    "project_path": "MyApplication2"
                }
            )
            
            response = await pm_agent.handle_request(message)
            if not response.error:
                result = response.result
                print(f"✅ 需求分析成功: {result.get('analysis', {}).get('primary_type', 'unknown')}")
                print(f"   文件计划: {len(result.get('target_files', []))} 个文件")
            else:
                print(f"❌ 需求分析失败: {response.error}")
        
        # 测试代码检查Agent的codelinter功能
        print("\n--- 测试代码检查Agent ---")
        
        cc_agent = coordinator.agents.get("code_checker")
        if cc_agent:
            message = MCPMessage(
                id="test_002",
                method="code.check.codelinter", 
                params={
                    "project_path": "MyApplication2"
                }
            )
            
            response = await cc_agent.handle_request(message)
            if not response.error:
                result = response.result
                lint_data = result.get("formatted_review_data", {})
                print(f"✅ codelinter检查成功: {lint_data.get('total_issues', 0)} 个问题")
            else:
                print(f"❌ codelinter检查失败: {response.error}")
        
        # 测试鸿蒙工作流状态查询
        print("\n--- 测试工作流管理器 ---")
        
        active_workflows = coordinator.get_active_harmonyos_workflows()
        print(f"活跃工作流数量: {len(active_workflows)}")
        
        # 关闭协调器
        await coordinator.shutdown()
        print("✅ 协调器已正常关闭")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_workflow_status_management():
    """测试工作流状态管理"""
    print("\n=== 工作流状态管理测试 ===")
    
    try:
        from mcp_orchestrator.harmonyos_workflow import HarmonyOSWorkflowManager
        
        # 创建模拟协调器
        class MockCoordinator:
            async def _execute_agent_method(self, agent_id, method, params):
                # 模拟Agent响应
                return {
                    "success": True,
                    "data": f"mock response from {agent_id}.{method}"
                }
        
        coordinator = MockCoordinator()
        workflow_manager = HarmonyOSWorkflowManager(coordinator)
        
        # 获取工作流状态
        active_workflows = workflow_manager.get_active_workflows()
        print(f"初始活跃工作流: {len(active_workflows)}")
        
        # 测试状态查询
        status = workflow_manager.get_workflow_status("non_existent_session")
        print(f"不存在会话的状态: {status}")
        
        print("✅ 工作流状态管理测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 状态管理测试失败: {e}")
        return False

async def test_error_handling():
    """测试错误处理"""
    print("\n=== 错误处理测试 ===")
    
    try:
        from mcp_orchestrator.loop_manager import LoopManager
        
        class MockCoordinator:
            pass
        
        coordinator = MockCoordinator()
        loop_manager = LoopManager(coordinator)
        
        # 测试无效会话处理
        should_continue, reason = await loop_manager.should_continue_loop(
            "invalid_session", {}, {}
        )
        print(f"无效会话处理: {should_continue}, 原因: {reason}")
        
        # 测试错误分类
        test_errors = [
            {
                "type": "error",
                "message": "Cannot find module 'test'",
                "category": "import_error"
            },
            {
                "type": "error", 
                "message": "Syntax error at line 10",
                "category": "syntax_error"
            }
        ]
        
        # 使用私有方法测试（仅用于测试）
        critical_errors = loop_manager._analyze_error_severity(test_errors, [])
        print(f"错误分析结果: {len(critical_errors)} 个关键错误")
        
        print("✅ 错误处理测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🧪 开始鸿蒙系统集成测试")
    
    test_results = []
    
    # 运行各项测试
    test_results.append(await test_harmonyos_workflow_integration())
    test_results.append(await test_workflow_status_management())
    test_results.append(await test_error_handling())
    
    # 统计结果
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有集成测试通过！")
    else:
        print("⚠️ 部分测试失败，需要检查")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)