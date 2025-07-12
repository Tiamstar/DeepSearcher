#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为文档内容爬取脚本
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加上级目录到路径，以便导入模块
sys.path.append(str(Path(__file__).parent.parent.parent))

from huawei_rag.core.crawler import HuaweiContentCrawler
from huawei_rag.core.config import CrawlerConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    try:
        logger.info("🚀 开始华为文档内容爬取...")
        
        # 初始化配置和爬虫
        config = CrawlerConfig()
        crawler = HuaweiContentCrawler(config=config)
        
        # 加载链接
        urls = crawler.load_links()
        if not urls:
            logger.error("❌ 没有找到链接文件或链接为空")
            return False
        
        logger.info(f"📋 找到 {len(urls)} 个链接")
        
        # 开始爬取
        crawled_content = await crawler.crawl_content(urls)
        
        if crawled_content:
            # 生成统计信息
            stats = crawler.generate_statistics()
            
            logger.info("🎉 爬取完成!")
            logger.info("📊 统计信息:")
            logger.info(f"   ✅ 成功页面: {stats['total_pages']}")
            logger.info(f"   ❌ 失败页面: {stats['failed_pages']}")
            logger.info(f"   ⏩ 跳过页面: {stats['skipped_pages']}")
            logger.info(f"   📝 总文本长度: {stats['total_text_length']:,} 字符")
            logger.info(f"   💻 总代码块: {stats['total_code_blocks']} 个")
            logger.info(f"   📄 内容文件: {config.PROCESSED_DATA_DIR / config.OUTPUT_FILE}")
            
            return True
        else:
            logger.error("❌ 爬取失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 脚本执行失败: {e}")
        return False

if __name__ == "__main__":
    # 运行爬虫
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 爬取完成！内容已保存。")
        print("💡 接下来可以运行向量数据库加载脚本。")
    else:
        print("\n❌ 爬取失败！")
        sys.exit(1) 