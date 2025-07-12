#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP主入口文件
华为多Agent协作系统 - 基于MCP协议的主入口
"""

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path
import time
import logging
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_orchestrator import MCPCoordinator
from mcp_agents.base import MCPMessage
from shared.config_loader import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPCli:
    """MCP命令行接口"""
    
    def __init__(self):
        self.coordinator = None
        self.config_loader = ConfigLoader()
    
    async def initialize_coordinator(self, config_file: str = None) -> bool:
        """初始化MCP协调器"""
        try:
            # 加载配置
            if config_file:
                config = self.config_loader.load_config(config_file)
            else:
                # 使用统一配置而不是已删除的 mcp_config.yaml
                config = self.config_loader.get_unified_config()
                if not config:
                    logger.warning("统一配置为空，使用默认配置")
                    config = self.config_loader._get_default_unified_config()
            
            # 创建协调器
            self.coordinator = MCPCoordinator(config)
            await self.coordinator.initialize()
            
            logger.info("🚀 MCP协调器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ MCP协调器初始化失败: {e}")
            return False
    
    async def interactive_mode(self):
        """交互式模式"""
        print("🤖 华为多Agent协作系统 - MCP版本")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'help' 查看帮助")
        print("输入 'stats' 查看统计信息")
        print("输入 'agents' 查看可用Agent")
        print("输入 'workflows' 查看可用工作流")
        print("-" * 60)
        
        while True:
            try:
                user_input = input("\n🔍 请输入命令或需求: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见！")
                    break
                
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                elif user_input.lower() == 'stats':
                    await self._show_stats()
                    continue
                
                elif user_input.lower() == 'agents':
                    await self._show_agents()
                    continue
                
                elif user_input.lower() == 'workflows':
                    await self._show_workflows()
                    continue
                
                # 处理代码生成请求
                start_time = time.time()
                result = await self._process_request(user_input)
                end_time = time.time()
                
                self._print_result(result, end_time - start_time)
                
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                logger.error(f"处理请求失败: {e}")
                print(f"❌ 处理失败: {e}")
    
    async def _process_request(self, user_input: str) -> Dict[str, Any]:
        """处理用户请求"""
        # 创建MCP消息 - 修正方法名称
        message = MCPMessage(
            method="coordinator.execute_workflow",
            params={
                "workflow_name": "complete_code_generation",
                "params": {
                    "user_input": user_input,
                    "language": "python",
                    "context": ""
                }
            },
            id=f"interactive_{int(time.time())}"
        )
        
        # 发送给协调器处理
        response = await self.coordinator.handle_request(message)
        
        if response.error:
            return {
                "success": False,
                "error": response.error,
                "result": None
            }
        
        return {
            "success": True,
            "error": None,
            "result": response.result
        }
    
    def _print_result(self, result: Dict[str, Any], processing_time: float):
        """打印处理结果"""
        print(f"\n{'='*80}")
        print(f"📝 处理结果")
        print(f"⏱️ 处理时间: {processing_time:.2f}秒")
        print(f"{'='*80}")
        
        if result["success"]:
            if result["result"] and "context" in result["result"]:
                context = result["result"]["context"]
                if "final_code" in context:
                    print("\n💻 生成的代码:")
                    print("-" * 60)
                    print(context["final_code"])
                    print("\n// 以上代码基于华为官方文档和MCP协议生成")
                    print("// 已经过多Agent协作优化，建议根据具体环境调整")
                else:
                    print("\n📋 处理结果:")
                    print("-" * 60)
                    print(json.dumps(result["result"], indent=2, ensure_ascii=False))
            else:
                print("\n📋 处理结果:")
                print("-" * 60)
                print(json.dumps(result["result"], indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ 处理失败: {result['error']}")
        
        print(f"\n{'='*80}")
    
    def _show_help(self):
        """显示帮助信息"""
        print("""
💡 MCP系统帮助信息:
  
📋 基本命令:
  - help     : 显示此帮助信息
  - stats    : 显示系统统计信息
  - agents   : 显示可用的Agent
  - workflows: 显示可用的工作流
  - quit/exit: 退出系统

🔨 使用方式:
  - 直接输入您的需求描述，系统会自动选择合适的工作流处理
  - 支持代码生成、代码审查、技术咨询等多种功能
  - 基于华为开发规范和最佳实践
  
🎯 示例:
  - "帮我生成一个Python HTTP服务器"
  - "创建一个ArkTS页面组件"
  - "写一个C++排序算法"
        """)
    
    async def _show_stats(self):
        """显示统计信息"""
        if not self.coordinator:
            print("❌ 协调器未初始化")
            return
        
        stats = self.coordinator._get_stats()
        print(f"""
📊 系统统计信息:
  总请求数: {stats['total_requests']}
  成功请求数: {stats['successful_requests']}
  失败请求数: {stats['failed_requests']}
  运行时间: {stats.get('uptime_seconds', 0):.2f}秒
  
🤖 Agent使用情况:""")
        
        for agent_id, count in stats.get('agent_usage', {}).items():
            print(f"  {agent_id}: {count}次")
    
    async def _show_agents(self):
        """显示可用Agent"""
        if not self.coordinator:
            print("❌ 协调器未初始化")
            return
        
        agents_info = await self.coordinator._get_agents_info()
        print(f"""
🤖 可用Agent ({len(agents_info['agents'])}个):""")
        
        for agent_id, info in agents_info['agents'].items():
            print(f"  {agent_id}: {info.get('status', 'unknown')}")
    
    async def _show_workflows(self):
        """显示可用工作流"""
        if not self.coordinator:
            print("❌ 协调器未初始化")
            return
        
        workflows_info = await self.coordinator._get_workflows_info()
        print(f"""
🔄 可用工作流 ({len(workflows_info['workflows'])}个):""")
        
        for workflow_name, info in workflows_info['workflows'].items():
            print(f"  {workflow_name}: {info.get('description', '无描述')}")
    
    async def single_request(self, user_input: str, workflow: str = "complete_code_generation", 
                           language: str = "python", output_format: str = "text"):
        """单次请求处理"""
        start_time = time.time()
        
        try:
            result = await self._process_request(user_input)
            end_time = time.time()
            
            if output_format == "json":
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                self._print_result(result, end_time - start_time)
            
        except Exception as e:
            logger.error(f"处理单次请求失败: {e}")
            print(f"❌ 处理失败: {e}")


def create_web_api():
    """创建Web API服务"""
    from api.main import app
    return app


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="华为多Agent协作系统 - MCP版本")
    parser.add_argument("--mode", choices=["interactive", "api", "single"], 
                       default="interactive", help="运行模式")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--query", type=str, help="单次查询内容")
    parser.add_argument("--workflow", type=str, default="complete_code_generation",
                       help="工作流名称")
    parser.add_argument("--language", type=str, default="python", help="编程语言")
    parser.add_argument("--output", choices=["text", "json"], default="text",
                       help="输出格式")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API服务地址")
    parser.add_argument("--port", type=int, default=8000, help="API服务端口")
    
    args = parser.parse_args()
    
    if args.mode == "api":
        # 启动Web API服务 - 修复事件循环冲突
        try:
            import uvicorn
            app = create_web_api()
            
            # 使用uvicorn的配置方式，避免事件循环冲突
            config = uvicorn.Config(
                app=app,
                host=args.host,
                port=args.port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"启动API服务失败: {e}")
            sys.exit(1)
    
    else:
        # 命令行模式
        cli = MCPCli()
        
        if not await cli.initialize_coordinator(args.config):
            sys.exit(1)
        
        if args.mode == "interactive":
            await cli.interactive_mode()
        elif args.mode == "single":
            if not args.query:
                print("❌ 单次模式需要提供 --query 参数")
                sys.exit(1)
            
            await cli.single_request(args.query, args.workflow, args.language, args.output)


if __name__ == "__main__":
    asyncio.run(main()) 