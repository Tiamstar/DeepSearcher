#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为文档内容文件选择工具
帮助用户查看和选择要加载的内容文件
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# 添加上级目录到路径，以便导入模块
sys.path.append(str(Path(__file__).parent.parent.parent))

from huawei_rag.core.pipeline import HuaweiRAGPipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_file_size(size_mb: float) -> str:
    """格式化文件大小"""
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    else:
        return f"{size_mb:.2f} MB"

def format_modified_time(timestamp: float) -> str:
    """格式化修改时间"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def display_available_files(pipeline: HuaweiRAGPipeline):
    """显示所有可用的内容文件"""
    print("\n📁 可用的华为文档内容文件:")
    print("=" * 80)
    
    files_info = pipeline.list_content_files()
    
    if not any(files_info.values()):
        print("❌ 未找到任何内容文件")
        return
    
    # 显示扩展内容文件
    if files_info['expanded_files']:
        print("\n🚀 扩展内容文件 (已爬取详细内容):")
        print("-" * 50)
        for i, file in enumerate(files_info['expanded_files'], 1):
            print(f"  {i}. 📄 {file['name']}")
            print(f"     📊 大小: {format_file_size(file['size_mb'])}")
            print(f"     🕒 修改时间: {format_modified_time(file['modified'])}")
            print()
    
    # 显示基础内容文件
    if files_info['basic_files']:
        print("\n📚 基础内容文件:")
        print("-" * 50)
        for i, file in enumerate(files_info['basic_files'], 1):
            print(f"  {i}. 📄 {file['name']}")
            print(f"     📊 大小: {format_file_size(file['size_mb'])}")
            print(f"     🕒 修改时间: {format_modified_time(file['modified'])}")
            print()
    
    # 显示其他文件
    if files_info['other_files']:
        print("\n📋 其他相关文件:")
        print("-" * 50)
        for i, file in enumerate(files_info['other_files'], 1):
            print(f"  {i}. 📄 {file['name']}")
            print(f"     📊 大小: {format_file_size(file['size_mb'])}")
            print(f"     🕒 修改时间: {format_modified_time(file['modified'])}")
            print()

def select_content_type():
    """选择内容类型"""
    print("\n🎯 请选择内容加载策略:")
    print("=" * 50)
    print("1. 🚀 自动选择 (auto) - 自动选择最新的扩展内容文件")
    print("2. 📚 基础内容 (basic) - 仅加载 huawei_docs_content.json")
    print("3. 🌟 扩展内容 (expanded) - 仅加载最新的扩展内容文件")
    print("4. 🔄 合并所有 (all) - 合并所有可用的内容文件 (推荐)")
    
    while True:
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == "1":
            return "auto"
        elif choice == "2":
            return "basic"
        elif choice == "3":
            return "expanded"
        elif choice == "4":
            return "all"
        else:
            print("❌ 无效选项，请输入 1-4")

def select_collection_name():
    """选择集合名称"""
    print("\n📚 请选择集合名称:")
    print("=" * 30)
    print("1. huawei_docs (默认)")
    print("2. huawei_docs_basic (基础内容)")
    print("3. huawei_docs_expanded (扩展内容)")
    print("4. huawei_docs_merged (合并内容)")
    print("5. 自定义")
    
    while True:
        choice = input("\n请输入选项 (1-5): ").strip()
        
        if choice == "1":
            return "huawei_docs"
        elif choice == "2":
            return "huawei_docs_basic"
        elif choice == "3":
            return "huawei_docs_expanded"
        elif choice == "4":
            return "huawei_docs_merged"
        elif choice == "5":
            custom_name = input("请输入自定义集合名称: ").strip()
            if custom_name:
                return custom_name.replace(" ", "_").replace("-", "_")
            else:
                print("❌ 集合名称不能为空")
        else:
            print("❌ 无效选项，请输入 1-5")

def load_content_with_settings(pipeline: HuaweiRAGPipeline, 
                              content_type: str, 
                              collection_name: str):
    """使用选定的设置加载内容"""
    print(f"\n🚀 开始加载内容...")
    print("=" * 50)
    print(f"📋 内容类型: {content_type}")
    print(f"📚 集合名称: {collection_name}")
    
    # 询问是否强制重新创建集合
    force_new = input("\n是否强制重新创建集合? (y/N): ").strip().lower()
    force_new_collection = force_new in ['y', 'yes', '是']
    
    # 开始加载
    success = pipeline.load_to_vector_database(
        collection_name=collection_name,
        content_type=content_type,
        force_new_collection=force_new_collection,
        batch_size=64
    )
    
    if success:
        print("\n🎉 内容加载成功!")
        
        # 显示集合状态
        adapter = pipeline.initialize_adapter(collection_name, content_type)
        collection_info = adapter.get_collection_info()
        
        if collection_info.get('exists'):
            print(f"📊 集合状态:")
            print(f"   📚 集合名称: {collection_info['name']}")
            print(f"   📄 文档数量: {collection_info.get('count', 0):,}")
    else:
        print("\n❌ 内容加载失败!")
    
    return success

def main():
    """主函数"""
    try:
        print("📁 华为文档内容文件选择工具")
        print("=" * 60)
        
        # 初始化流水线
        pipeline = HuaweiRAGPipeline()
        
        # 设置DeepSearcher
        pipeline.setup_deepsearcher()
        
        while True:
            # 显示可用文件
            display_available_files(pipeline)
            
            # 显示菜单
            print("\n🎯 操作选项:")
            print("=" * 30)
            print("1. 加载内容到向量数据库")
            print("2. 刷新文件列表")
            print("3. 退出")
            
            choice = input("\n请输入选项 (1-3): ").strip()
            
            if choice == "1":
                # 选择内容类型
                content_type = select_content_type()
                
                # 选择集合名称
                collection_name = select_collection_name()
                
                # 确认选择
                print(f"\n✅ 确认设置:")
                print(f"   📋 内容类型: {content_type}")
                print(f"   📚 集合名称: {collection_name}")
                
                confirm = input("\n确认加载? (Y/n): ").strip().lower()
                if confirm not in ['n', 'no', '否']:
                    load_content_with_settings(pipeline, content_type, collection_name)
                else:
                    print("❌ 已取消加载")
                
                input("\n⏸️ 按 Enter 继续...")
                
            elif choice == "2":
                print("🔄 刷新文件列表...")
                continue
                
            elif choice == "3":
                print("👋 再见!")
                break
                
            else:
                print("❌ 无效选项，请输入 1-3")
                input("\n⏸️ 按 Enter 继续...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 工具执行失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        sys.exit(1) 