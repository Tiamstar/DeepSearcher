#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为RAG在线搜索演示脚本
展示实时在线搜索功能
"""

import logging
import sys
import os
from pathlib import Path

# 添加上级目录到路径，以便导入模块
sys.path.append(str(Path(__file__).parent.parent.parent))

from huawei_rag import HuaweiRAG
from huawei_rag.core.online_search import EnhancedOnlineSearchEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_search_result(query: str, result: dict):
    """打印搜索结果"""
    print(f"\n{'='*60}")
    print(f"🔍 查询: {query}")
    print(f"{'='*60}")
    
    # 打印最终答案
    if result.get('final_answer'):
        print("\n📝 综合答案:")
        print("-" * 40)
        print(result['final_answer'])
    
    # 打印本地搜索结果
    if result.get('local_results'):
        print(f"\n📚 本地搜索结果 ({len(result['local_results'])} 个):")
        print("-" * 40)
        for i, local_result in enumerate(result['local_results'][:3], 1):
            print(f"{i}. {local_result.get('title', '未知标题')}")
            print(f"   来源: {local_result.get('url', '无URL')}")
            print(f"   相关度: {local_result.get('score', 0):.4f}")
            content = local_result.get('content', '')[:150]
            print(f"   内容: {content}...")
            print()
    
    # 打印在线搜索结果
    if result.get('online_results') and result['online_results'].get('sources'):
        online_sources = result['online_results']['sources']
        print(f"\n🌐 在线搜索结果 ({len(online_sources)} 个):")
        print("-" * 40)
        for i, source in enumerate(online_sources[:3], 1):
            print(f"{i}. {source.get('title', '未知标题')}")
            print(f"   来源: {source.get('url', '无URL')}")
            print(f"   相关度: {source.get('relevance_score', 0)}")
            content = source.get('content_preview', '')
            print(f"   预览: {content}")
            print()
    
    # 打印所有来源
    if result.get('sources'):
        print(f"\n📋 信息来源汇总:")
        print("-" * 40)
        for i, source in enumerate(result['sources'], 1):
            source_type = "🏠 本地" if source.get('type') == 'local' else "🌐 在线"
            print(f"{i}. {source_type} - {source.get('title', '未知标题')}")
            if source.get('url'):
                print(f"   链接: {source['url']}")

def demo_online_search():
    """演示纯在线搜索功能"""
    print("\n🌐 纯在线搜索演示")
    print("="*50)
    
    # 检查FireCrawl API Key
    if not os.getenv('FIRECRAWL_API_KEY'):
        print("❌ 未设置 FIRECRAWL_API_KEY 环境变量")
        print("💡 请先设置FireCrawl API密钥：")
        print("   export FIRECRAWL_API_KEY='your_api_key'")
        return False
    
    try:
        # 初始化华为RAG系统
        rag = HuaweiRAG()
        
        # 演示查询
        demo_queries = [
            "如何在Android应用中集成华为推送服务",
            "HarmonyOS应用开发入门教程",
            "华为HMS Core最新功能介绍"
        ]
        
        for query in demo_queries:
            try:
                print(f"\n🔍 开始在线搜索: {query}")
                answer, sources = rag.online_search(query)
                
                print(f"\n📝 在线搜索答案:")
                print("-" * 40)
                print(answer)
                
                if sources:
                    print(f"\n📋 信息来源 ({len(sources)} 个):")
                    print("-" * 40)
                    for i, source in enumerate(sources, 1):
                        print(f"{i}. {source.get('title', '未知标题')}")
                        print(f"   URL: {source.get('url', '无URL')}")
                        print(f"   相关度: {source.get('relevance_score', 0)}")
                        print()
                
                # 等待用户确认继续
                if query != demo_queries[-1]:
                    input("\n⏸️ 按 Enter 继续下一个查询...")
                
            except Exception as e:
                print(f"❌ 查询失败: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ 在线搜索演示失败: {e}")
        return False

def demo_hybrid_search():
    """演示混合搜索功能"""
    print("\n🔀 混合搜索演示")
    print("="*50)
    
    try:
        # 初始化华为RAG系统
        rag = HuaweiRAG()
        
        # 检查本地数据库状态
        status = rag.get_status()
        has_local_data = status.get('collection_exists', False)
        
        print(f"📊 系统状态:")
        print(f"   本地数据库: {'✅ 可用' if has_local_data else '❌ 不可用'}")
        print(f"   在线搜索: {'✅ 可用' if os.getenv('FIRECRAWL_API_KEY') else '❌ 需要API密钥'}")
        
        # 演示查询
        demo_queries = [
            "Android华为服务开发指南",
            "如何使用华为地图服务API"
        ]
        
        for query in demo_queries:
            try:
                print(f"\n🔍 混合搜索: {query}")
                
                # 执行混合搜索
                result = rag.hybrid_search(
                    query=query,
                    use_local=has_local_data,
                    use_online=bool(os.getenv('FIRECRAWL_API_KEY'))
                )
                
                # 打印结果
                print_search_result(query, result)
                
                # 等待用户确认继续
                if query != demo_queries[-1]:
                    input("\n⏸️ 按 Enter 继续下一个查询...")
                
            except Exception as e:
                print(f"❌ 混合搜索失败: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ 混合搜索演示失败: {e}")
        return False

def interactive_search():
    """交互式搜索"""
    print("\n💬 交互式搜索模式")
    print("="*50)
    print("💡 输入查询内容，输入 'quit' 退出")
    print("💡 输入 'mode' 切换搜索模式")
    
    try:
        rag = HuaweiRAG()
        search_mode = "hybrid"  # hybrid, online, local
        
        # 检查系统状态
        status = rag.get_status()
        has_local_data = status.get('collection_exists', False)
        has_online_api = bool(os.getenv('FIRECRAWL_API_KEY'))
        
        print(f"\n📊 系统状态:")
        print(f"   本地数据: {'✅' if has_local_data else '❌'}")
        print(f"   在线API: {'✅' if has_online_api else '❌'}")
        print(f"   当前模式: {search_mode}")
        
        while True:
            try:
                query = input(f"\n🔍 [{search_mode}] 请输入查询: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见！")
                    break
                
                if query.lower() == 'mode':
                    print("选择搜索模式:")
                    print("1. hybrid - 混合搜索")
                    print("2. online - 纯在线搜索")
                    print("3. local - 纯本地搜索")
                    
                    mode_choice = input("请选择 (1-3): ").strip()
                    if mode_choice == "1":
                        search_mode = "hybrid"
                    elif mode_choice == "2":
                        search_mode = "online"
                    elif mode_choice == "3":
                        search_mode = "local"
                    
                    print(f"✅ 已切换到 {search_mode} 模式")
                    continue
                
                if not query:
                    print("⚠️ 请输入有效查询")
                    continue
                
                # 执行搜索
                if search_mode == "hybrid":
                    result = rag.hybrid_search(query, use_local=has_local_data, use_online=has_online_api)
                    print_search_result(query, result)
                    
                elif search_mode == "online":
                    if not has_online_api:
                        print("❌ 在线搜索需要 FIRECRAWL_API_KEY")
                        continue
                    answer, sources = rag.online_search(query)
                    print(f"\n📝 在线答案:\n{answer}")
                    
                elif search_mode == "local":
                    if not has_local_data:
                        print("❌ 本地搜索需要先构建数据库")
                        continue
                    results = rag.search(query)
                    if results:
                        print(f"\n📚 本地搜索结果:")
                        for i, result in enumerate(results[:3], 1):
                            print(f"{i}. {result.get('title', '未知标题')}")
                            print(f"   {result.get('content', '')[:200]}...")
                    else:
                        print("📭 未找到相关结果")
                
            except KeyboardInterrupt:
                print("\n\n👋 搜索结束！")
                break
            except Exception as e:
                print(f"❌ 搜索出错: {e}")
        
    except Exception as e:
        print(f"❌ 交互式搜索启动失败: {e}")

def main():
    """主函数"""
    print("🚀 华为RAG在线搜索演示")
    print("="*50)
    
    # 检查环境配置
    print("🔧 检查环境配置...")
    has_firecrawl = bool(os.getenv('FIRECRAWL_API_KEY'))
    print(f"   FireCrawl API: {'✅' if has_firecrawl else '❌ 需要设置 FIRECRAWL_API_KEY'}")
    
    if not has_firecrawl:
        print("\n💡 要使用在线搜索功能，请设置FireCrawl API密钥:")
        print("   1. 注册 https://firecrawl.dev/ 账号")
        print("   2. 获取API密钥")
        print("   3. 设置环境变量: export FIRECRAWL_API_KEY='your_key'")
        print("   4. 重新运行脚本")
        
        use_demo = input("\n是否继续演示 (仅展示本地搜索)? (y/N): ").strip().lower()
        if use_demo not in ['y', 'yes']:
            return False
    
    # 选择演示模式
    print("\n请选择演示模式:")
    print("1. 🌐 纯在线搜索演示")
    print("2. 🔀 混合搜索演示") 
    print("3. 💬 交互式搜索")
    
    choice = input("\n请输入选项 (1-3): ").strip()
    
    if choice == "1":
        return demo_online_search()
    elif choice == "2":
        return demo_hybrid_search()
    elif choice == "3":
        interactive_search()
        return True
    else:
        print("❌ 无效选项")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n❌ 演示未完成")
        sys.exit(1)
    else:
        print("\n✅ 演示完成！") 