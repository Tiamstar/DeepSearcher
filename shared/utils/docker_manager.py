#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker服务管理器
管理代码检查相关的Docker服务，特别是SonarQube
"""

import os
import sys
import subprocess
import time
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional

# 配置日志
logger = logging.getLogger(__name__)


class DockerServicesManager:
    """Docker服务管理器"""
    
    def __init__(self, project_root: Optional[Path] = None):
        """初始化Docker服务管理器
        
        Args:
            project_root: 项目根目录，如果为None则自动检测
        """
        if project_root is None:
            # 从当前文件位置推导项目根目录
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = project_root
            
        self.services_config = {
            "sonarqube": {
                "compose_file": "docker-services/sonarqube/docker-compose.yml",
                "services": ["sonarqube", "postgresql"],
                "health_check_url": "http://localhost:9000/api/system/status",
                "startup_timeout": 180,
                "ports": [9000, 5432]
            }
        }
    
    def _run_docker_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """运行Docker命令，处理权限问题"""
        try:
            # 首先尝试不使用sudo
            return subprocess.run(command, **kwargs)
        except (subprocess.CalledProcessError, PermissionError):
            # 如果权限失败，使用sudo
            sudo_command = ["sudo"] + command
            return subprocess.run(sudo_command, **kwargs)
    
    def check_docker_installed(self) -> bool:
        """检查Docker是否已安装"""
        try:
            self._run_docker_command(["docker", "--version"], 
                                   capture_output=True, check=True)
            self._run_docker_command(["docker-compose", "--version"], 
                                   capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_service_running(self, service_name: str) -> bool:
        """检查服务是否正在运行"""
        if service_name not in self.services_config:
            logger.error(f"未知服务: {service_name}")
            return False
        
        try:
            # 直接使用docker ps检查容器状态
            result = self._run_docker_command([
                "docker", "ps", "--format", "{{.Names}}", "--filter", "status=running"
            ], capture_output=True, text=True, check=True)
            
            running_containers = [line.strip() for line in result.stdout.split('\n') 
                                if line.strip()]
            
            config = self.services_config[service_name]
            expected_services = config["services"]
            
            # 检查期望的服务是否都在运行
            for service in expected_services:
                if service not in running_containers:
                    return False
            
            return True
        except subprocess.CalledProcessError:
            return False
    
    def start_service(self, service_name: str) -> bool:
        """启动服务"""
        if service_name not in self.services_config:
            logger.error(f"未知服务: {service_name}")
            return False
        
        config = self.services_config[service_name]
        compose_file = self.project_root / config["compose_file"]
        
        if not compose_file.exists():
            logger.error(f"Docker Compose文件不存在: {compose_file}")
            return False
        
        try:
            logger.info(f"启动{service_name}服务...")
            
            # 启动服务
            self._run_docker_command([
                "docker-compose", "-f", str(compose_file), "up", "-d"
            ], check=True)
            
            # 等待服务启动
            logger.info("等待服务启动...")
            return self._wait_for_service_ready(service_name)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"启动{service_name}服务失败: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """停止服务"""
        if service_name not in self.services_config:
            logger.error(f"未知服务: {service_name}")
            return False
        
        config = self.services_config[service_name]
        compose_file = self.project_root / config["compose_file"]
        
        try:
            logger.info(f"停止{service_name}服务...")
            self._run_docker_command([
                "docker-compose", "-f", str(compose_file), "down"
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"停止{service_name}服务失败: {e}")
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """重启服务"""
        self.stop_service(service_name)
        time.sleep(3)
        return self.start_service(service_name)
    
    def _wait_for_service_ready(self, service_name: str) -> bool:
        """等待服务就绪"""
        config = self.services_config[service_name]
        health_check_url = config.get("health_check_url")
        timeout = config.get("startup_timeout", 120)
        
        if not health_check_url:
            # 没有健康检查URL，等待固定时间
            time.sleep(30)
            return True
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(health_check_url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"{service_name}服务就绪")
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(10)
            logger.info(f"等待{service_name}服务启动...")
        
        logger.error(f"{service_name}服务启动超时")
        return False
    
    def get_service_status(self, service_name: str) -> Dict:
        """获取服务状态"""
        if service_name not in self.services_config:
            return {"error": f"未知服务: {service_name}"}
        
        config = self.services_config[service_name]
        status = {
            "service_name": service_name,
            "running": self.check_service_running(service_name),
            "ports": config["ports"],
            "services": config["services"]
        }
        
        # 检查健康状态
        if status["running"] and config.get("health_check_url"):
            try:
                response = requests.get(config["health_check_url"], timeout=5)
                status["healthy"] = response.status_code == 200
                status["health_check"] = response.status_code
            except requests.RequestException:
                status["healthy"] = False
                status["health_check"] = "timeout"
        
        return status
    
    def list_all_services(self) -> List[Dict]:
        """列出所有服务状态"""
        return [self.get_service_status(name) for name in self.services_config.keys()]
    
    def setup_sonarqube_project(self) -> bool:
        """设置SonarQube项目"""
        if not self.check_service_running("sonarqube"):
            logger.error("SonarQube服务未运行，请先启动服务")
            return False
        
        # 等待SonarQube完全启动
        time.sleep(30)
        
        try:
            # 检查项目配置文件
            sonar_properties = self.project_root / "docker-services/sonarqube/sonar-project.properties"
            if sonar_properties.exists():
                logger.info("SonarQube项目配置已存在")
                return True
            else:
                logger.error("SonarQube项目配置文件不存在")
                return False
        except Exception as e:
            logger.error(f"设置SonarQube项目失败: {e}")
            return False


def get_docker_manager() -> DockerServicesManager:
    """获取Docker服务管理器实例"""
    return DockerServicesManager() 