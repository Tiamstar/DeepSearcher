#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为文档搜索演示脚本
"""

import logging
import sys
import os
from pathlib import Path

# 设置环境编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 设置标准输入输出编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加上级目录到路径，以便导入模块
sys.path.append(str(Path(__file__).parent.parent.parent))

from huawei_rag.core.pipeline import HuaweiRAGPipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_str(obj) -> str:
    """安全的字符串转换，处理编码问题"""
    if obj is None:
        return ""
    try:
        if isinstance(obj, str):
            return obj
        else:
            return str(obj)
    except Exception:
        return "[无法转换的内容]"

def print_search_results(query: str, results: list, max_content_length: int = 200):
    """打印搜索结果"""
    print(f"\n🔍 搜索查询: {safe_str(query)}")
    print("=" * 60)
    
    if not results:
        print("📭 没有找到相关结果")
        return
    
    for i, result in enumerate(results, 1):
        try:
            print(f"\n📄 结果 {i}:")
            print(f"   📖 标题: {safe_str(result.get('title', '未知标题'))}")
            print(f"   🔗 链接: {safe_str(result.get('url', '无链接'))}")
            print(f"   📊 类型: {safe_str(result.get('content_type', '未知类型'))}")
            print(f"   🎯 相关度: {result.get('score', 0):.4f}")
            
            # 显示内容摘要
            content = safe_str(result.get('content', ''))
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            
            print(f"   📝 内容:")
            print(f"      {content}")
        except Exception as e:
            print(f"   ❌ 显示结果 {i} 时出错: {safe_str(e)}")

def interactive_search(pipeline: HuaweiRAGPipeline):
    """交互式搜索"""
    print("\n🎯 华为文档交互式搜索")
    print("=" * 50)
    print("💡 输入搜索关键词，输入 'quit' 退出")
    print("💡 输入 'help' 查看示例查询")
    
    while True:
        try:
            query = input("\n🔍 请输入搜索查询: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break
            
            if query.lower() == 'help':
                print("\n💡 示例查询:")
                print("   - Android开发")
                print("   - 如何创建应用")
                print("   - API接口调用")
                print("   - 推送服务")
                print("   - 鸿蒙系统")
                print("   - HMS Core")
                continue
            
            if not query:
                print("⚠️ 请输入有效的搜索查询")
                continue
            
            # 搜索
            results = pipeline.search(query, top_k=3, collection_name="huawei_docs")
            print_search_results(query, results)
            
        except KeyboardInterrupt:
            print("\n\n👋 搜索结束！")
            break
        except Exception as e:
            print(f"❌ 搜索出错: {safe_str(e)}")

def demo_searches(pipeline: HuaweiRAGPipeline):
    """演示搜索"""
    demo_queries = [
        "Android应用开发",
        "如何集成HMS Core",
        "推送服务配置", 
        "鸿蒙系统开发",
        "API密钥管理",
        "应用签名",
        "云数据库操作",
        "统计分析服务"
    ]
    
    print("\n🎯 华为文档搜索演示")
    print("=" * 50)
    
    for query in demo_queries:
        try:
            results = pipeline.search(query, top_k=2, collection_name="huawei_docs")
            print_search_results(query, results, max_content_length=150)
        except Exception as e:
            print(f"❌ 搜索 '{safe_str(query)}' 时出错: {safe_str(e)}")
            continue
        
        # 等待用户按键继续
        if query != demo_queries[-1]:  # 不是最后一个
            try:
                input("\n⏸️ 按 Enter 继续下一个搜索...")
            except:
                pass

def advanced_rag_demo(pipeline: HuaweiRAGPipeline, use_chain_of_rag: bool):
    """高级RAG搜索演示"""
    rag_type = "ChainOfRAG" if use_chain_of_rag else "DeepSearch"
    print(f"\n🧠 华为文档高级RAG搜索演示 ({rag_type})")
    print("=" * 60)
    
    # 更复杂的查询，适合展示RAG的优势
    complex_queries = [
        "如何在HarmonyOS中实现应用的后台任务管理和资源优化？",
        "华为HMS Core的推送服务如何集成，有哪些配置步骤？",
        "ArkUI框架相比传统Android开发有什么优势和特点？",
        "HarmonyOS应用签名和发布流程是怎样的？"
    ]
    
    for query in complex_queries:
        try:
            print(f"\n🔍 复杂查询: {safe_str(query)}")
            print("=" * 80)
            print("🤖 正在使用高级RAG进行深度分析...")
            
            # 使用高级RAG搜索
            results = pipeline.search_with_rag(
                query=query, 
                top_k=3, 
                collection_name="huawei_docs",
                use_chain_of_rag=use_chain_of_rag
            )
            
            if results:
                # 显示RAG生成的答案（如果有）
                if results[0].get('rag_answer'):
                    print(f"\n💡 RAG生成的答案:")
                    print("─" * 60)
                    print(safe_str(results[0]['rag_answer']))
                    print("─" * 60)
                
                # 显示相关文档
                print(f"\n📚 相关文档 ({len(results)} 个):")
                for i, result in enumerate(results, 1):
                    print(f"\n📄 文档 {i}:")
                    print(f"   📖 标题: {safe_str(result.get('title', '未知标题'))}")
                    print(f"   🔗 链接: {safe_str(result.get('url', '无链接'))[:80]}...")
                    print(f"   🎯 相关度: {result.get('score', 0):.4f}")
                    
                    # 显示内容摘要
                    content = safe_str(result.get('content', ''))
                    if len(content) > 200:
                        content = content[:200] + "..."
                    print(f"   📝 内容: {content}")
            else:
                print("📭 没有找到相关结果")
                
        except Exception as e:
            print(f"❌ 高级RAG搜索 '{safe_str(query)}' 时出错: {safe_str(e)}")
            continue
        
        # 等待用户按键继续
        if query != complex_queries[-1]:  # 不是最后一个
            try:
                input(f"\n⏸️ 按 Enter 继续下一个{rag_type}搜索...")
            except:
                pass

def main():
    """主函数"""
    try:
        print("🚀 华为文档搜索演示")
        print("=" * 50)
        
        # 初始化流水线
        pipeline = HuaweiRAGPipeline()
        
        # 设置DeepSearcher
        pipeline.setup_deepsearcher()
        
        # 使用正确的集合名称初始化适配器
        adapter = pipeline.initialize_adapter("huawei_docs")
        
        # 检查集合状态
        collection_info = adapter.get_collection_info()
        
        if not collection_info.get('exists'):
            print("❌ 向量数据库集合不存在！")
            print("💡 请先运行 load_vector_db.py 脚本加载数据")
            return False
        
        print(f"✅ 找到向量数据库集合: {safe_str(collection_info.get('name'))}")
        
        # 更好地处理文档数量显示
        doc_count = collection_info.get('count', 0)
        if doc_count == -1:
            print(f"📊 文档数量: 有数据 (无法精确计数)")
            if collection_info.get('note'):
                print(f"   💡 说明: {safe_str(collection_info['note'])}")
        elif doc_count == 0:
            print(f"📊 文档数量: {doc_count}")
            print(f"   ⚠️ 显示为0可能是计数方法问题，但集合存在且可以搜索")
        else:
            print(f"📊 文档数量: {doc_count:,}")
            
        # 如果显示数量为0，做一个快速测试搜索
        if doc_count == 0:
            print("🔍 正在测试搜索功能...")
            try:
                test_results = pipeline.search("测试", top_k=1, collection_name="huawei_docs")
                if test_results:
                    print("✅ 搜索功能正常，集合确实包含数据")
                else:
                    print("❌ 测试搜索无结果，集合可能为空")
            except Exception as e:
                print(f"❌ 测试搜索失败: {safe_str(e)}")
        
        # 选择演示模式
        print("\n请选择运行模式:")
        print("1. 预设演示搜索 (基础向量搜索)")
        print("2. 交互式搜索 (基础向量搜索)")
        print("3. 高级RAG搜索演示 (DeepSearch)")
        print("4. 链式RAG搜索演示 (ChainOfRAG)")
        
        choice = input("请输入选项 (1/2/3/4): ").strip()
        
        if choice == "1":
            demo_searches(pipeline)
        elif choice == "2":
            interactive_search(pipeline)
        elif choice == "3":
            advanced_rag_demo(pipeline, use_chain_of_rag=False)
        elif choice == "4":
            advanced_rag_demo(pipeline, use_chain_of_rag=True)
        else:
            print("❌ 无效选项，运行预设演示...")
            demo_searches(pipeline)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 演示脚本执行失败: {e}")
        print(f"❌ 演示脚本执行失败: {safe_str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        sys.exit(1) 