#!/bin/bash

echo "🔧 修复SonarQube离线模式问题..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 停止现有容器
echo -e "${YELLOW}停止现有SonarQube容器...${NC}"
docker-compose down

# 清理可能的问题数据
echo -e "${YELLOW}清理问题数据...${NC}"
docker volume rm sonarqube_sonarqube_extensions 2>/dev/null || true

# 等待一下
sleep 3

# 重新启动
echo -e "${YELLOW}重新启动SonarQube（离线模式）...${NC}"
docker-compose up -d

# 等待启动
echo -e "${YELLOW}等待SonarQube启动...${NC}"
sleep 30

# 检查状态
echo -e "${YELLOW}检查SonarQube状态...${NC}"
for i in {1..12}; do
    if curl -s http://localhost:9000/api/system/status | grep -q "UP"; then
        echo -e "${GREEN}✅ SonarQube已成功启动！${NC}"
        echo -e "${GREEN}访问地址: http://localhost:9000${NC}"
        echo -e "${GREEN}默认账户: admin/admin${NC}"
        exit 0
    else
        echo -e "${YELLOW}等待中... ($i/12)${NC}"
        sleep 10
    fi
done

echo -e "${RED}❌ SonarQube启动超时，请检查日志:${NC}"
echo "docker logs sonarqube"
exit 1 