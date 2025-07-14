#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Main Test
测试鸿蒙工作流在主程序中的运行
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_main import MCPCli

async def test_harmonyos_workflow_main():
    """测试鸿蒙工作流在主程序中的运行"""
    print("🚀 测试鸿蒙工作流主程序集成")
    
    try:
        # 创建CLI实例
        cli = MCPCli()
        
        # 初始化协调器
        success = await cli.initialize_coordinator()
        if not success:
            print("❌ 协调器初始化失败")
            return False
        
        print("✅ MCP CLI初始化成功")
        
        # 测试查看可用Agent
        agents_info = await cli.coordinator._get_agents_info()
        print(f"可用Agent: {list(agents_info['agents'].keys())}")
        
        # 测试查看可用工作流
        workflows_info = await cli.coordinator._get_workflows_info()
        print(f"可用工作流: {list(workflows_info['workflows'].keys())}")
        
        # 测试鸿蒙工作流状态查询
        active_workflows = cli.coordinator.get_active_harmonyos_workflows()
        print(f"活跃鸿蒙工作流: {len(active_workflows)}")
        
        print("✅ 鸿蒙工作流主程序集成测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 主程序测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    success = await test_harmonyos_workflow_main()
    
    if success:
        print("\n🎉 鸿蒙工作流主程序集成测试成功！")
        print("\n📋 可以使用的命令:")
        print("1. 交互模式: python mcp_main.py --mode interactive")
        print("2. 单次请求: python mcp_main.py --mode single --query '创建一个鸿蒙登录页面'")
        print("3. API模式: python mcp_main.py --mode api")
    else:
        print("\n❌ 主程序集成测试失败")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)