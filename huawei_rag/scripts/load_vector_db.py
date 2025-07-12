#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为文档向量数据库加载脚本 - 支持多种内容类型
"""

import logging
import sys
import argparse
from pathlib import Path

# 添加上级目录到路径，以便导入模块
sys.path.append(str(Path(__file__).parent.parent.parent))

from huawei_rag.core.pipeline import HuaweiRAGPipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="华为文档向量数据库加载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
内容类型说明:
  auto      - 自动选择最新的扩展内容文件 (默认)
  basic     - 仅加载基础内容文件 (huawei_docs_content.json)
  expanded  - 仅加载最新的扩展内容文件
  all       - 合并所有可用的内容文件 (推荐)

使用示例:
  python -m huawei_rag.scripts.load_vector_db --content-type basic
  python -m huawei_rag.scripts.load_vector_db --content-type all --collection huawei_docs_merged
  python -m huawei_rag.scripts.load_vector_db --force-new --batch-size 32
  python -m huawei_rag.scripts.load_vector_db --no-incremental --content-type all
  python -m huawei_rag.scripts.load_vector_db --incremental --collection huawei_docs_updated
        """
    )
    
    parser.add_argument(
        '--content-type', 
        choices=['auto', 'basic', 'expanded', 'all'],
        default='auto',
        help='内容类型选择 (默认: auto)'
    )
    
    parser.add_argument(
        '--collection', 
        default='huawei_docs',
        help='集合名称 (默认: huawei_docs)'
    )
    
    parser.add_argument(
        '--force-new', 
        action='store_true',
        help='强制创建新集合，删除已存在的集合'
    )
    
    parser.add_argument(
        '--batch-size', 
        type=int, 
        default=64,
        help='批处理大小 (默认: 64)'
    )
    
    parser.add_argument(
        '--incremental', 
        action='store_true',
        help='启用增量更新，仅处理新文档 (默认启用)'
    )
    
    parser.add_argument(
        '--no-incremental', 
        action='store_true',
        help='禁用增量更新，重新处理所有文档'
    )
    
    parser.add_argument(
        '--interactive', 
        action='store_true',
        help='交互式选择模式'
    )
    
    return parser.parse_args()

def interactive_selection(pipeline: HuaweiRAGPipeline):
    """交互式选择模式"""
    print("\n📁 华为文档内容文件:")
    print("=" * 60)
    
    # 显示可用文件
    files_info = pipeline.list_content_files()
    
    if files_info['expanded_files']:
        print("\n🚀 扩展内容文件:")
        for file in files_info['expanded_files']:
            size_mb = file['size_mb']
            print(f"  📄 {file['name']} ({size_mb:.2f} MB)")
    
    if files_info['basic_files']:
        print("\n📚 基础内容文件:")
        for file in files_info['basic_files']:
            size_mb = file['size_mb']
            print(f"  📄 {file['name']} ({size_mb:.2f} MB)")
    
    # 选择内容类型
    print("\n🎯 请选择内容加载策略:")
    print("1. 🚀 自动选择 (auto)")
    print("2. 📚 基础内容 (basic)")
    print("3. 🌟 扩展内容 (expanded)")
    print("4. 🔄 合并所有 (all) - 推荐")
    
    while True:
        choice = input("\n请输入选项 (1-4): ").strip()
        if choice == "1":
            content_type = "auto"
            break
        elif choice == "2":
            content_type = "basic"
            break
        elif choice == "3":
            content_type = "expanded"
            break
        elif choice == "4":
            content_type = "all"
            break
        else:
            print("❌ 无效选项，请输入 1-4")
    
    # 选择集合名称
    collection_name = input(f"\n📚 集合名称 (默认: huawei_docs): ").strip()
    if not collection_name:
        collection_name = "huawei_docs"
    
    # 其他选项
    force_new = input("\n🔄 是否强制重新创建集合? (y/N): ").strip().lower()
    force_new_collection = force_new in ['y', 'yes', '是']
    
    incremental = input("\n⚡ 启用增量更新 (仅处理新文档)? (Y/n): ").strip().lower()
    incremental_update = incremental not in ['n', 'no', '否']
    
    batch_size_input = input("\n⚙️ 批处理大小 (默认: 64): ").strip()
    try:
        batch_size = int(batch_size_input) if batch_size_input else 64
    except ValueError:
        batch_size = 64
    
    return {
        'content_type': content_type,
        'collection_name': collection_name,
        'force_new_collection': force_new_collection,
        'incremental_update': incremental_update,
        'batch_size': batch_size
    }

def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        print("💾 华为文档向量数据库加载工具")
        print("=" * 60)
        
        # 初始化流水线
        pipeline = HuaweiRAGPipeline()
        
        # 设置DeepSearcher
        pipeline.setup_deepsearcher()
        
        # 获取配置
        if args.interactive:
            config = interactive_selection(pipeline)
        else:
            # 确定增量更新设置：默认启用，除非明确禁用
            incremental_update = not args.no_incremental  # 默认True，除非指定--no-incremental
            
            config = {
                'content_type': args.content_type,
                'collection_name': args.collection,
                'force_new_collection': args.force_new,
                'incremental_update': incremental_update,
                'batch_size': args.batch_size
            }
        
        # 显示配置信息
        print(f"\n⚙️ 加载配置:")
        print(f"   📋 内容类型: {config['content_type']}")
        print(f"   📚 集合名称: {config['collection_name']}")
        print(f"   🔄 强制重新创建: {'是' if config['force_new_collection'] else '否'}")
        print(f"   ⚡ 增量更新: {'是' if config.get('incremental_update', True) else '否'}")
        print(f"   📦 批处理大小: {config['batch_size']}")
        
        # 开始加载
        success = pipeline.load_to_vector_database(
            collection_name=config['collection_name'],
            content_type=config['content_type'],
            force_new_collection=config['force_new_collection'],
            incremental_update=config['incremental_update'],
            batch_size=config['batch_size']
        )
        
        if success:
            print("\n🎉 加载完成!")
            
            # 显示最终状态
            adapter = pipeline.initialize_adapter(
                config['collection_name'], 
                config['content_type']
            )
            collection_info = adapter.get_collection_info()
            
            if collection_info.get('exists'):
                print(f"\n📊 最终状态:")
                print(f"   📚 集合名称: {collection_info['name']}")
                print(f"   📄 文档数量: {collection_info.get('count', 0):,}")
                print(f"\n💡 现在可以使用搜索功能:")
                print(f"   python -m huawei_rag.scripts.search_demo")
            
            return True
        else:
            print("\n❌ 加载失败!")
            return False
        
    except Exception as e:
        logger.error(f"❌ 加载脚本执行失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        sys.exit(1) 