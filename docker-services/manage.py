#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker服务管理脚本
简化的Docker服务管理接口
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.docker_manager import DockerServicesManager


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Docker服务管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python manage.py start sonarqube    # 启动SonarQube服务
  python manage.py stop sonarqube     # 停止SonarQube服务
  python manage.py status sonarqube   # 查看SonarQube状态
  python manage.py list               # 列出所有服务状态
        """
    )
    
    parser.add_argument("action", 
                       choices=["start", "stop", "restart", "status", "list"],
                       help="要执行的操作")
    parser.add_argument("service", nargs="?", 
                       choices=["sonarqube"],
                       help="要操作的服务名称")
    
    args = parser.parse_args()
    
    manager = DockerServicesManager()
    
    # 检查Docker是否安装
    if not manager.check_docker_installed():
        print("❌ Docker或Docker Compose未安装，请先安装Docker")
        sys.exit(1)
    
    if args.action == "list":
        print("📋 Docker服务状态:")
        print("=" * 60)
        services = manager.list_all_services()
        for service in services:
            print(f"🔧 {service['service_name']}:")
            print(f"   运行状态: {'✅ 运行中' if service['running'] else '❌ 已停止'}")
            if 'healthy' in service:
                print(f"   健康状态: {'✅ 健康' if service['healthy'] else '❌ 不健康'}")
            print(f"   端口: {', '.join(map(str, service['ports']))}")
            print()
        return
    
    # status命令可以不指定服务名，显示所有服务状态
    if args.action == "status" and not args.service:
        print("📋 所有Docker服务状态:")
        print("=" * 60)
        services = manager.list_all_services()
        for service in services:
            print(f"🔧 {service['service_name']}:")
            print(f"   运行状态: {'✅ 运行中' if service['running'] else '❌ 已停止'}")
            if 'healthy' in service:
                print(f"   健康状态: {'✅ 健康' if service['healthy'] else '❌ 不健康'}")
            print(f"   端口: {', '.join(map(str, service['ports']))}")
            print()
        return
    
    if not args.service and args.action != "status":
        print("❌ 请指定要操作的服务名称")
        sys.exit(1)
    
    if args.action == "start":
        success = manager.start_service(args.service)
        if success:
            print(f"✅ {args.service}服务启动成功")
            if args.service == "sonarqube":
                print("🌐 SonarQube访问地址: http://localhost:9000")
                print("👤 默认用户名/密码: admin/admin")
        else:
            print(f"❌ {args.service}服务启动失败")
            sys.exit(1)
    
    elif args.action == "stop":
        success = manager.stop_service(args.service)
        if success:
            print(f"✅ {args.service}服务停止成功")
        else:
            print(f"❌ {args.service}服务停止失败")
            sys.exit(1)
    
    elif args.action == "restart":
        success = manager.restart_service(args.service)
        if success:
            print(f"✅ {args.service}服务重启成功")
        else:
            print(f"❌ {args.service}服务重启失败")
            sys.exit(1)
    
    elif args.action == "status":
        status = manager.get_service_status(args.service)
        print(f"🔧 {args.service}服务状态:")
        print(f"   运行状态: {'✅ 运行中' if status['running'] else '❌ 已停止'}")
        if 'healthy' in status:
            print(f"   健康状态: {'✅ 健康' if status['healthy'] else '❌ 不健康'}")
        print(f"   端口: {', '.join(map(str, status['ports']))}")


if __name__ == "__main__":
    main() 