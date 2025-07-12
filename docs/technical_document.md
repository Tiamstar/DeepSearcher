# 华为多Agent协作系统 - 技术文档

## 1. 系统架构

系统基于MCP（Multi-Agent Collaboration Protocol）协议构建，采用模块化设计，由多个专业Agent协作完成代码生成与优化任务。

### 1.1 目录结构

```
project/
├── api/                  # API接口服务
├── config/               # 配置文件
│   └── config.yaml       # 统一配置文件
├── mcp_agents/           # 各专业Agent
│   ├── base/             # 基础Agent类
│   ├── project_manager/  # 项目管理Agent
│   ├── search/           # 搜索Agent
│   ├── code_generator/   # 代码生成Agent
│   ├── code_checker/     # 代码检查Agent
│   └── final_generator/  # 最终代码生成Agent
├── mcp_orchestrator/     # 协调器
│   ├── mcp_coordinator.py   # MCP协调器
│   └── workflow_manager.py  # 工作流管理器
├── shared/               # 共享组件
│   ├── interfaces.py     # 接口定义
│   └── services/         # 通用服务
└── mcp_main.py           # 主入口文件
```
<!--  -->
## 2. 核心组件

### 2.1 协调器（MCPCoordinator）

协调器是系统的核心组件，负责初始化和管理各Agent，以及执行预定义的工作流。

主要功能：
- Agent生命周期管理（初始化、关闭）
- 工作流定义、注册与执行
- 消息路由与处理
- 会话状态追踪

### 2.2 工作流管理器（WorkflowManager）

负责工作流的注册、执行和状态管理。

主要功能：
- 工作流定义与注册
- 工作流执行与步骤调度
- 参数传递与上下文管理
- 执行状态监控

### 2.3 专业Agent

系统包含五种专业Agent，各司其职：

#### 2.3.1 项目管理Agent

- 负责将用户输入拆分为子问题
- 协调整体项目规划
- 需求分析与任务分配

#### 2.3.2 搜索Agent

- 支持本地知识库搜索
- 集成基于firecrawl的在线搜索
- 提供混合搜索和链式搜索能力
- 基于deepsearcher实现，替代原有huawei_rag

#### 2.3.3 代码生成Agent

- 根据用户需求生成初始代码
- 集成搜索结果作为参考上下文
- 支持多种编程语言（Python、C++、ArkTS等）

#### 2.3.4 代码检查Agent

代码检查采用多种工具组合：
- **ESLint**：ArkTS/JavaScript/TypeScript代码检查
- **CppCheck**：C/C++代码检查
- **SonarQube**：通用代码质量与安全检查
- 支持定制检查规则和报告格式

#### 2.3.5 最终代码生成Agent

- 根据检查结果优化代码
- 修复问题并应用改进建议
- 生成高质量最终代码

## 3. 通信协议

系统使用基于JSON-RPC的MCP协议，实现Agent间标准化通信。

### 3.1 消息格式

```json
{
  "id": "请求ID",
  "method": "方法名称",
  "params": {
    "参数名": "参数值"
  },
  "result": {
    "结果字段": "结果值"
  },
  "error": {
    "code": 错误码,
    "message": "错误信息"
  }
}
```

### 3.2 方法命名规范

方法名使用点分隔的命名空间：
- `agent.{agent_id}.{capability}`：Agent特定功能
- `coordinator.{action}`：协调器操作
- `workflow.{workflow_name}`：工作流执行

## 4. 核心工作流

系统定义了三种标准工作流：

### 4.1 完整代码生成工作流

1. 搜索相关文档和示例
2. 生成初始代码
3. 执行代码检查
4. 生成最终优化代码

### 4.2 快速代码生成工作流

1. 搜索相关文档和示例
2. 直接生成代码（无检查步骤）

### 4.3 代码审查工作流

1. 执行代码检查
2. 优化代码

## 5. 核心依赖

- **deepsearcher**：向量搜索引擎
- **大语言模型**：支持多种提供商（DeepSeek、OpenAI、Anthropic等）
- **firecrawl**：在线搜索组件
- **代码检查工具**：ESLint、CppCheck、SonarQube等
- **FastAPI**：API服务框架

## 6. 配置系统

系统使用统一配置文件`config/config.yaml`，主要配置项：

- **LLM配置**：提供商、模型、API密钥等
- **向量数据库配置**：集合名称、维度等
- **搜索服务配置**：本地/在线搜索参数
- **代码检查配置**：检查规则、阈值等
- **工作流配置**：步骤定义、超时设置等

## 7. 扩展性设计

系统支持以下扩展方式：

### 7.1 添加新Agent

1. 继承基类`MCPAgent`
2. 实现`initialize`和`handle_request`方法
3. 声明Agent能力
4. 在协调器中注册新Agent

### 7.2 定义新工作流

1. 创建工作流配置（步骤、参数映射等）
2. 在协调器的`_register_workflows`方法中注册

### 7.3 添加新代码检查工具

1. 创建新的检查服务类
2. 实现接口方法
3. 在统一检查服务中集成

## 8. 日志与监控

- 系统使用结构化日志
- 支持按Agent、工作流和会话ID过滤日志
- 提供统计数据API用于监控
- 记录工作流执行状态和性能指标 