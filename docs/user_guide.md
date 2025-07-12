# 华为多Agent协作系统 - 使用说明

本文档提供华为多Agent协作系统（MCP版本）的详细使用说明，帮助用户快速上手并有效利用系统功能。

## 1. 系统简介

华为多Agent协作系统是一个基于多Agent协作的智能代码生成平台，专为华为技术栈设计。系统通过多个专业Agent协同工作，能够高效生成、检查和优化代码，支持多种编程语言。

## 2. 安装与配置

### 2.1 系统要求

- Python 3.9+
- Node.js 14+（用于ESLint代码检查）
- 足够的存储空间用于向量数据库

### 2.2 安装步骤

1. 克隆代码仓库
```bash
git clone https://github.com/your-org/deep-searcher.git
cd deep-searcher
```

2. 创建并激活虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 安装代码检查工具
```bash
npm install -g eslint
# 确保cppcheck和sonarqube已安装（如需使用）
```

### 2.3 配置系统

1. 复制环境变量模板
```bash
cp .env.example .env
```

2. 编辑`.env`文件，配置必要的API密钥和服务URL
```
OPENAI_API_KEY=your_api_key_here
DEEPSEEK_API_KEY=your_api_key_here
# 其他配置项...
```

3. 检查并根据需要修改`config/config.yaml`中的配置

## 3. 运行系统

### 3.1 命令行模式

系统支持三种运行模式：交互式、单次请求和API服务模式。

#### 3.1.1 交互式模式

```bash
python mcp_main.py --mode interactive
```

在交互式模式下，您可以直接输入需求，系统会实时生成代码并提供结果。支持的命令：
- `help`：显示帮助信息
- `stats`：显示系统统计信息
- `agents`：查看可用Agent列表
- `workflows`：查看可用工作流列表
- `quit`或`exit`：退出系统

#### 3.1.2 单次请求模式

```bash
python mcp_main.py --mode single --query "创建一个Python HTTP服务器" --language python
```

参数说明：
- `--query`：请求内容
- `--language`：编程语言（默认：python）
- `--workflow`：使用的工作流（默认：complete_code_generation）
- `--output`：输出格式（text或json，默认：text）

#### 3.1.3 API服务模式

```bash
python mcp_main.py --mode api --host 0.0.0.0 --port 8000
```

启动后，API服务将在指定的主机和端口上运行，您可以通过HTTP请求与系统交互。

### 3.2 API使用方法

系统提供RESTful API，支持以下端点：

#### 3.2.1 生成代码

```
POST /api/v1/generate-code
```

请求体：
```json
{
  "user_input": "创建一个Python HTTP服务器",
  "language": "python",
  "framework": "flask",
  "context": "需要支持文件上传功能",
  "workflow_type": "complete"
}
```

参数说明：
- `user_input`：（必填）用户需求描述
- `language`：（可选）编程语言，默认为"python"
- `framework`：（可选）使用的框架
- `context`：（可选）额外的上下文信息
- `workflow_type`：（可选）工作流类型，可选值为"complete"或"quick"，默认为"complete"

响应示例：
```json
{
  "workflow_name": "complete_code_generation",
  "session_id": "f5a9c3d2-7e6b-4a1f-8d9c-0e5f4a2b3c6d",
  "execution_id": "b2c3d4e5-f6a7-b8c9-d0e1-f2a3b4c5d6e7",
  "status": "completed",
  "context": {
    "final_code": "import http.server\nimport socketserver\nfrom urllib.parse import parse_qs\nimport cgi\nimport os\n\nPORT = 8000\n\nclass FileUploadHandler(http.server.SimpleHTTPRequestHandler):\n    def do_POST(self):\n        content_length = int(self.headers['Content-Length'])\n        form = cgi.FieldStorage(\n            fp=self.rfile,\n            headers=self.headers,\n            environ={'REQUEST_METHOD': 'POST'}\n        )\n        \n        # 获取上传文件\n        uploaded_file = form['file']\n        \n        # 保存文件\n        file_path = os.path.join('uploads', uploaded_file.filename)\n        os.makedirs('uploads', exist_ok=True)\n        \n        with open(file_path, 'wb') as f:\n            f.write(uploaded_file.file.read())\n        \n        # 发送响应\n        self.send_response(200)\n        self.send_header('Content-type', 'text/html')\n        self.end_headers()\n        self.wfile.write(f\"文件 {uploaded_file.filename} 上传成功\".encode())\n\nwith socketserver.TCPServer((\"\", PORT), FileUploadHandler) as httpd:\n    print(f\"服务器运行在端口 {PORT}\")\n    print(f\"上传文件请访问 http://localhost:{PORT}\")\n    httpd.serve_forever()"
  },
  "errors": []
}
```

#### 3.2.2 代码审查与优化

```
POST /api/v1/review-code
```

请求体：
```json
{
  "code": "function test() {\n  var x = 1;\n  console.log(x);\n}",
  "language": "javascript",
  "review_type": "comprehensive",
  "description": "简单的测试函数",
  "optimization_type": "quality"
}
```

参数说明：
- `code`：（必填）需要审查的代码
- `language`：（必填）代码语言
- `review_type`：（可选）审查类型，可选值为"comprehensive"（全面）、"security"（安全）、"performance"（性能），默认为"comprehensive"
- `description`：（可选）代码描述或上下文
- `optimization_type`：（可选）优化类型，可选值为"quality"（质量）、"performance"（性能）、"security"（安全），默认为"quality"

响应示例：
```json
{
  "workflow_name": "code_review_workflow",
  "session_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "execution_id": "c7d8e9f0-a1b2-c3d4-e5f6-7a8b9c0d1e2f",
  "status": "completed",
  "context": {
    "review_result": {
      "issues": [
        {
          "type": "code_style",
          "description": "使用var声明变量，推荐使用let或const",
          "line": 2,
          "severity": "low"
        }
      ],
      "suggestions": [
        {
          "description": "将var x = 1替换为const x = 1，因为变量值未被修改",
          "code": "function test() {\n  const x = 1;\n  console.log(x);\n}"
        }
      ],
      "score": 85,
      "summary": "代码结构简单清晰，但有一些小的改进空间"
    },
    "final_code": "function test() {\n  const x = 1;\n  console.log(x);\n}"
  },
  "errors": []
}
```

#### 3.2.3 执行自定义工作流

```
POST /api/v1/execute-workflow
```

请求体：
```json
{
  "workflow_name": "complete_code_generation",
  "params": {
    "user_input": "创建一个ArkTS页面组件，包含图片展示和滚动效果",
    "language": "arkts",
    "framework": "harmony"
  },
  "session_id": "custom-session-001"
}
```

参数说明：
- `workflow_name`：（必填）工作流名称
- `params`：（必填）工作流参数，根据不同工作流有不同的要求
- `session_id`：（可选）会话ID，用于追踪和管理请求，如不提供则自动生成

响应示例：与代码生成接口类似

#### 3.2.4 获取可用工作流

```
GET /api/v1/workflows
```

响应示例：
```json
{
  "total_workflows": 3,
  "workflows": {
    "complete_code_generation": {
      "name": "complete_code_generation",
      "description": "完整的代码生成流程",
      "steps_count": 5,
      "usage_count": 12
    },
    "quick_code_generation": {
      "name": "quick_code_generation",
      "description": "快速代码生成流程",
      "steps_count": 2,
      "usage_count": 8
    },
    "code_review_workflow": {
      "name": "code_review_workflow",
      "description": "代码审查和优化流程",
      "steps_count": 2,
      "usage_count": 5
    }
  }
}
```

#### 3.2.5 获取可用Agent列表

```
GET /api/v1/agents
```

响应示例：
```json
{
  "total_agents": 5,
  "agents": {
    "project_manager": {
      "agent_id": "project_manager",
      "capabilities": ["project.decompose", "project.analyze"],
      "status": "ready",
      "is_initialized": true,
      "usage_count": 15
    },
    "search": {
      "agent_id": "search",
      "capabilities": ["search.online", "search.local"],
      "status": "ready",
      "is_initialized": true,
      "usage_count": 20
    },
    "code_generator": {
      "agent_id": "code_generator",
      "capabilities": ["code.generate"],
      "status": "ready",
      "is_initialized": true,
      "usage_count": 18
    },
    "code_checker": {
      "agent_id": "code_checker",
      "capabilities": ["code.check.unified", "code.lint"],
      "status": "ready",
      "is_initialized": true,
      "usage_count": 12
    },
    "final_generator": {
      "agent_id": "final_generator",
      "capabilities": ["code.finalize", "code.optimize"],
      "status": "ready",
      "is_initialized": true,
      "usage_count": 10
    }
  }
}
```

#### 3.2.6 获取系统统计信息

```
GET /api/v1/stats
```

响应示例：
```json
{
  "total_requests": 45,
  "successful_requests": 42,
  "failed_requests": 3,
  "agent_usage": {
    "project_manager": 15,
    "search": 20,
    "code_generator": 18,
    "code_checker": 12,
    "final_generator": 10
  },
  "workflow_usage": {
    "complete_code_generation": 12,
    "quick_code_generation": 8,
    "code_review_workflow": 5
  },
  "start_time": "2023-05-15T10:30:45.123456",
  "uptime_seconds": 3600,
  "active_sessions": 2,
  "success_rate": 93.33
}
```

#### 3.2.7 调用特定Agent方法

```
POST /api/v1/agent/{agent_id}
```

请求体：
```json
{
  "method": "search.online",
  "params": {
    "query": "Python HTTP服务器最佳实践",
    "top_k": 3
  }
}
```

参数说明：
- `method`：（必填）要调用的Agent方法
- `params`：（必填）方法参数，根据不同方法有不同的要求

响应示例：
```json
{
  "answer": "Python HTTP服务器的最佳实践包括...",
  "sources": [
    {
      "title": "Python Web服务器比较",
      "url": "https://example.com/python-web-servers",
      "snippet": "..."
    },
    {
      "title": "HTTP服务器性能优化",
      "url": "https://example.com/http-optimization",
      "snippet": "..."
    }
  ]
}
```

### 3.3 Docker服务配置

系统使用Docker封装了部分外部服务，以简化部署和确保环境一致性。这些服务位于`docker-services`目录中。

#### 3.3.1 SonarQube配置

SonarQube用于高级代码分析和质量检查，是代码检查Agent的重要组件之一。

1. 确保已安装Docker和Docker Compose
```bash
docker --version
docker-compose --version
```

2. 启动SonarQube服务
```bash
cd docker-services/sonarqube
docker-compose up -d
```

3. 验证SonarQube服务状态
```bash
docker ps | grep sonarqube
```

4. 首次使用时配置SonarQube
   - 访问 http://localhost:9000
   - 默认登录凭证：admin/admin
   - 首次登录需要更改密码
   - 创建一个新的项目令牌，并将其添加到`.env`文件中
```
SONAR_TOKEN=your_generated_token
SONAR_HOST_URL=http://localhost:9000
```

5. 停止SonarQube服务
```bash
cd docker-services/sonarqube
docker-compose down
```


注意：Docker服务的配置可以在docker-service目录下的`docker-compose.yml`文件中进行修改，例如更改端口、数据卷等。

## 4. 常见问题

### 4.1 API密钥配置

Q: 如何配置多种LLM提供商？
A: 在`.env`文件中设置对应的API密钥，然后在`config/config.yaml`中选择启用的提供商。

### 4.2 代码检查问题

Q: 代码检查支持哪些语言？
A: 当前支持ArkTS/JavaScript/TypeScript（ESLint）、C/C++（CppCheck）和多种语言的通用检查（SonarQube）。

### 4.3 性能优化

Q: 系统运行很慢，如何优化？
A: 尝试调整配置文件中的`max_tokens`参数，或在本地部署更轻量的模型。

### 4.4 Docker相关问题

Q: Docker容器无法启动怎么办？
A: 检查端口占用情况，可能是端口已被其他应用占用。使用`docker logs <container_name>`查看具体错误信息。

Q: SonarQube分析速度慢怎么办？
A: 可以在`docker-services/sonarqube/docker-compose.yml`中增加内存分配，或减少分析的代码范围。

Q: 如何备份Docker服务的数据？
A: 数据存储在各服务的数据卷中，可以使用`docker volume ls`查看所有数据卷，然后使用`docker volume backup`命令进行备份。

## 5. 高级功能

### 5.1 自定义工作流

您可以通过编辑`mcp_orchestrator/mcp_coordinator.py`文件中的`_register_workflows`方法来定义自定义工作流。

### 5.2 集成新的代码检查工具

如需添加新的代码检查工具，请在`shared/services`目录下创建新的服务类，并在统一检查服务中集成。

### 5.3 扩展搜索能力

系统默认使用deepsearcher进行本地搜索，可以通过以下步骤扩展搜索能力：
1. 准备新的文档库
2. 使用向量化工具建立索引
3. 在配置文件中更新集合名称

## 6. 资源与支持

- 技术文档：[docs/technical_document.md](docs/technical_document.md)
- 配置参考：[config/README.md](config/README.md) 