#!/bin/bash

# 配置代理例外脚本
# 避免代理设置干扰本地 SonarQube 访问

echo "=== 配置 SonarQube 代理例外 ==="

# 检查当前代理设置
echo "当前代理设置:"
echo "  http_proxy: $http_proxy"
echo "  https_proxy: $https_proxy"
echo "  no_proxy: $no_proxy"
echo ""

# 配置代理例外
echo "配置代理例外..."

# 定义需要绕过代理的地址
BYPASS_ADDRESSES="localhost,127.0.0.1,10.10.11.211,::1"

# 如果已经有 no_proxy 设置，则追加
if [ -n "$no_proxy" ]; then
    export no_proxy="$no_proxy,$BYPASS_ADDRESSES"
else
    export no_proxy="$BYPASS_ADDRESSES"
fi

echo "✅ 已配置代理例外: $no_proxy"

# 将配置添加到 .bashrc 以永久生效
BASHRC_FILE="$HOME/.bashrc"
PROXY_CONFIG="# SonarQube 代理例外配置
export no_proxy=\"$no_proxy\""

if ! grep -q "SonarQube 代理例外配置" "$BASHRC_FILE" 2>/dev/null; then
    echo "" >> "$BASHRC_FILE"
    echo "$PROXY_CONFIG" >> "$BASHRC_FILE"
    echo "✅ 已将配置添加到 ~/.bashrc"
else
    echo "ℹ️  配置已存在于 ~/.bashrc"
fi

echo ""
echo "=== 配置完成 ==="
echo ""
echo "现在可以正常访问 SonarQube："
echo "  - 本地访问: http://localhost:9000"
echo "  - 外部访问: http://10.10.11.211:9000"
echo ""
echo "测试访问:"
curl -s http://localhost:9000/api/system/status | python3 -m json.tool

echo ""
echo "注意: 新的代理配置将在下次登录时自动生效"
echo "当前会话已立即生效" 