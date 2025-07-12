# 华为多Agent协作系统 - 使用指南

## 📋 系统概述

这是一个基于MCP协议的多Agent协作代码生成系统，专门针对华为技术栈优化，支持鸿蒙系统、ArkTS、ArkUI等技术的代码生成和检查。

### 🤖 Agent架构

系统包含5个专业化Agent：

1. **项目管理Agent** - 负责需求分析和任务分解
2. **搜索Agent** - 提供本地知识库和在线搜索功能
3. **代码生成Agent** - 根据需求生成初始代码
4. **代码检查Agent** - 使用ESLint、CppCheck、SonarQube进行代码质量检查
5. **最终代码生成Agent** - 根据检查结果优化和生成最终代码

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖（如需要）
uv sync --extra all
```

### 2. 配置API密钥

复制环境变量模板并填入您的API密钥：

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的API密钥：
# - DEEPSEEK_API_KEY（必需）
# - SILICONFLOW_API_KEY（必需）
# - FIRECRAWL_API_KEY（可选，用于在线搜索）
```

### 3. 运行方式

#### 方式一：API服务模式

```bash
# 启动API服务器
python api/main.py
# 或者
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，可通过以下API端点使用：

- **代码生成**: `POST /api/v1/generate-code`
- **代码审查**: `POST /api/v1/review-code`
- **Agent调用**: `POST /api/v1/agent/{agent_id}`
- **工作流执行**: `POST /api/v1/execute-workflow`

#### 方式二：命令行模式

```bash
# 交互式模式
python mcp_main.py --mode interactive

# 单次执行模式
python mcp_main.py --mode single --query "创建一个鸿蒙系统的HTTP服务器"

# API模式
python mcp_main.py --mode api --host 0.0.0.0 --port 8000
```

#### 方式三：直接测试

```bash
# 运行系统功能测试
python test_mcp_system.py
```

## 📝 使用示例

### API调用示例

#### 1. 生成鸿蒙应用代码

```bash
curl -X POST "http://localhost:8000/api/v1/generate-code" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "创建一个鸿蒙系统的计算器应用",
    "language": "arkts",
    "framework": "ArkUI",
    "workflow_type": "complete"
  }'
```

#### 2. 代码质量检查

```bash
curl -X POST "http://localhost:8000/api/v1/review-code" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "@Entry\n@Component\nstruct Index {\n  build() {\n    Text(\"Hello\")\n  }\n}",
    "language": "arkts",
    "review_type": "comprehensive"
  }'
```

#### 3. 调用特定Agent

```bash
# 项目管理Agent - 需求分解
curl -X POST "http://localhost:8000/api/v1/agent/project_manager" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "project.decompose",
    "params": {
      "requirement": "开发鸿蒙音乐播放器",
      "tech_stack": "华为鸿蒙系统"
    }
  }'

# 搜索Agent - 技术搜索
curl -X POST "http://localhost:8000/api/v1/agent/search" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "search.online",
    "params": {
      "query": "ArkTS组件开发最佳实践",
      "top_k": 5
    }
  }'
```

### Python API示例

```python
import asyncio
from mcp_orchestrator.mcp_coordinator import MCPCoordinator
from mcp_agents.base.protocol import MCPMessage
from shared.config_loader import ConfigLoader

async def main():
    # 初始化系统
    config_loader = ConfigLoader()
    config = config_loader.get_unified_config()
    coordinator = MCPCoordinator(config)
    await coordinator.initialize()
    
    # 执行完整代码生成工作流
    request = MCPMessage(
        method="coordinator.execute_workflow",
        params={
            "workflow_name": "complete_code_generation",
            "params": {
                "user_input": "创建一个鸿蒙系统的todo应用",
                "language": "arkts",
                "framework": "ArkUI"
            }
        }
    )
    
    response = await coordinator.handle_request(request)
    print(f"生成结果: {response.result}")
    
    await coordinator.shutdown()

asyncio.run(main())
```

## ⚙️ 配置说明

### 主配置文件：`config/config.yaml`

系统使用统一配置文件，支持：

1. **LLM配置** - 支持多种大语言模型（DeepSeek、OpenAI、Anthropic等）
2. **Agent专用配置** - 每个Agent可以使用不同的LLM模型
3. **嵌入模型配置** - 支持多种嵌入模型
4. **向量数据库配置** - 支持Milvus、Qdrant等
5. **工作流配置** - 定义多种预设工作流

### Agent专用LLM配置示例

```yaml
agents:
  code_generator:
    llm_override:
      provider: "DeepSeek"
      config:
        model: "deepseek-coder"      # 专用代码生成模型
        api_key_env: "DEEPSEEK_API_KEY"
        temperature: 0.3
        max_tokens: 8000
```

## 🎯 支持的技术栈

### 编程语言
- **ArkTS** - 华为鸿蒙系统主要开发语言
- **JavaScript/TypeScript** - Web和移动应用开发
- **Python** - 后端服务和脚本
- **C/C++** - 系统级开发
- **Java** - 企业级应用

### 框架支持
- **ArkUI** - 华为鸿蒙系统UI框架
- **React/Vue** - 前端框架
- **FastAPI/Flask** - Python后端框架
- **Spring Boot** - Java后端框架

### 代码检查工具
- **ESLint** - JavaScript/TypeScript/ArkTS代码检查
- **CppCheck** - C/C++静态分析
- **SonarQube** - 多语言代码质量分析

## 🔧 故障排除

### 常见问题

1. **API密钥未配置**
   ```
   错误: DeepSeek API密钥未配置
   解决: 在.env文件中设置DEEPSEEK_API_KEY
   ```

2. **模型访问失败**
   ```
   错误: HTTP Request failed
   解决: 检查网络连接和API密钥有效性
   ```

3. **代码检查工具未安装**
   ```
   错误: ESLint 检查器初始化失败
   解决: npm install -g eslint
   ```

### 调试模式

启用详细日志：

```bash
export LOG_LEVEL=DEBUG
python test_mcp_system.py
```

### 性能优化

1. **并发处理** - 系统支持多Agent并发执行
2. **缓存机制** - 搜索结果和向量嵌入自动缓存
3. **超时控制** - 每个Agent和工作流都有超时保护

## 📊 监控和统计

### 系统状态查询

```bash
# 获取所有Agent状态
curl "http://localhost:8000/api/v1/agents"

# 获取工作流信息
curl "http://localhost:8000/api/v1/workflows"

# 获取系统统计
curl "http://localhost:8000/api/v1/stats"
```

### 健康检查

```bash
curl "http://localhost:8000/health"
```

## 🔄 工作流类型

### 1. 完整代码生成工作流 (`complete_code_generation`)
执行顺序：项目分解 → 在线搜索 → 代码生成 → 代码检查 → 最终优化

### 2. 快速代码生成工作流 (`quick_code_generation`)
执行顺序：本地搜索 → 代码生成

### 3. 代码审查工作流 (`code_review_workflow`)
执行顺序：代码检查 → 代码优化

## 📚 进阶用法

### 自定义工作流

您可以在配置文件中定义自己的工作流：

```yaml
workflows:
  custom_workflow:
    enabled: true
    timeout: 300
    steps:
      - agent: search
        method: search.adaptive
        params:
          query: "{user_input}"
      - agent: code_generator
        method: code.generate
        params:
          requirement: "{user_input}"
          context: "{search_result}"
```

### 扩展Agent

继承基类创建新的Agent：

```python
from mcp_agents.base.mcp_agent import MCPAgent

class CustomAgent(MCPAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("custom_agent", config)
    
    async def initialize(self) -> Dict[str, Any]:
        # 初始化逻辑
        pass
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        # 请求处理逻辑
        pass
```

## 📄 许可证

本项目遵循项目根目录下的LICENSE文件中指定的许可证。

## 🤝 贡献指南

欢迎贡献代码和建议！请查看CONTRIBUTING.md了解详细的贡献指南。

---

**注意**: 这是一个防御性安全工具，仅用于合法的代码生成和质量检查用途。请确保遵守相关法律法规和使用条款。