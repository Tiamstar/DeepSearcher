# 华为多Agent协作系统 - 配置文档

## 📋 概述

本文档介绍华为多Agent协作系统的配置管理方式。系统采用统一的`config.yaml`配置文件，支持：

- 🔄 **注释/解注释方式**切换不同LLM提供商
- 🎯 **Agent专用配置**覆盖全局设置
- 🌐 **多提供商支持**（DeepSeek、OpenAI、SiliconFlow等）
- ⚙️ **灵活的服务配置**（嵌入模型、向量数据库、爬虫等）

## 🚀 快速开始

### 1. 环境变量设置

首先在项目根目录创建`.env`文件，配置API密钥：

```bash
# DeepSeek API密钥
DEEPSEEK_API_KEY=sk-your-deepseek-key

# OpenAI API密钥
OPENAI_API_KEY=sk-your-openai-key

# SiliconFlow API密钥
SILICONFLOW_API_KEY=your-siliconflow-key

# 其他提供商API密钥...
```

### 2. 基本配置切换

编辑`config/config.yaml`文件，通过注释/解注释切换不同提供商：

```yaml
provide_settings:
  llm:
    # 当前启用DeepSeek
    provider: "DeepSeek"
    config:
      model: "deepseek-coder"
      api_key_env: "DEEPSEEK_API_KEY"

    # 切换到OpenAI：注释上面的DeepSeek配置，解注释下面的OpenAI配置
    # provider: "OpenAI"
    # config:
    #   model: "o1-mini"
    #   api_key_env: "OPENAI_API_KEY"
```

### 3. 验证配置

使用内置的配置验证脚本检查配置是否正确：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行配置验证
python config/validate_config.py
```

验证脚本会检查：
- ✅ 环境变量是否正确设置
- ✅ 配置文件格式是否正确
- ✅ 所有Agent配置是否正常
- ✅ 工作流配置是否有效

## 🎯 Agent专用配置

### 为什么需要Agent专用配置？

不同Agent有不同的任务特点，可能需要使用不同的模型：

- **项目管理Agent**：需要强推理能力 → 使用`deepseek-v3`
- **代码生成Agent**：需要平衡创造性和准确性 → 使用`deepseek-reasoner`
- **代码优化Agent**：需要高准确性 → 使用`deepseek-coder`

### 配置Agent专用LLM

在`agents`部分为特定Agent添加`llm_override`配置：

```yaml
agents:
  code_generator:
    description: 代码生成Agent
    enabled: true
    # 专用LLM配置
    llm_override:
      provider: "DeepSeek"
      config:
        model: "deepseek-reasoner"
        api_key_env: "DEEPSEEK_API_KEY"
        temperature: 0.3
        max_tokens: 8000
```

### 配置优先级

系统按以下优先级加载配置：

1. **Agent专用配置** (`agents.{agent_name}.llm_override`)
2. **全局配置** (`provide_settings.llm`)
3. **默认配置** (系统内置)

## 🔧 支持的提供商

### LLM提供商

| 提供商 | 模型示例 | 特点 |
|--------|----------|------|
| DeepSeek | `deepseek-coder`, `deepseek-v3`, `deepseek-reasoner` | 代码生成专用，推理能力强 |
| OpenAI | `o1-mini`, `gpt-4-turbo-preview` | 通用能力强 |
| SiliconFlow | `deepseek-ai/DeepSeek-R1` | 国内访问稳定 |
| PPIO | `deepseek/deepseek-r1-turbo` | 高性价比 |
| Ollama | `qwq`, `llama3` | 本地部署 |
| AzureOpenAI | 企业级OpenAI服务 | 企业合规 |

### 嵌入模型提供商

| 提供商 | 模型示例 | 特点 |
|--------|----------|------|
| SiliconflowEmbedding | `BAAI/bge-m3` | 中文支持好 |
| OpenAIEmbedding | `text-embedding-ada-002` | 通用性强 |
| OllamaEmbedding | `bge-m3` | 本地部署 |

## 📖 配置示例

### 示例1：全局使用DeepSeek，代码生成Agent使用专用模型

```yaml
# 全局LLM配置
provide_settings:
  llm:
    provider: "DeepSeek"
    config:
      model: "deepseek-coder"
      api_key_env: "DEEPSEEK_API_KEY"
      temperature: 0.1

# Agent专用配置
agents:
  code_generator:
    enabled: true
    llm_override:
      provider: "DeepSeek"
      config:
        model: "deepseek-reasoner"  # 使用推理模型
        api_key_env: "DEEPSEEK_API_KEY"
        temperature: 0.3            # 更高的创造性
        max_tokens: 8000
```

### 示例2：混合使用多个提供商

```yaml
# 全局使用OpenAI
provide_settings:
  llm:
    provider: "OpenAI"
    config:
      model: "gpt-4-turbo-preview"
      api_key_env: "OPENAI_API_KEY"

# 不同Agent使用不同提供商
agents:
  project_manager:
    llm_override:
      provider: "DeepSeek"
      config:
        model: "deepseek-v3"        # 用于项目规划
        api_key_env: "DEEPSEEK_API_KEY"
  
  code_generator:
    llm_override:
      provider: "SiliconFlow"
      config:
        model: "deepseek-ai/DeepSeek-R1"  # 用于代码生成
        api_key_env: "SILICONFLOW_API_KEY"
```

### 示例3：本地部署Ollama

```yaml
provide_settings:
  llm:
    provider: "Ollama"
    config:
      model: "qwq"
      base_url: "http://localhost:11434"
      temperature: 0.1
```

## 🔄 配置切换操作指南

### 切换全局LLM提供商

1. **编辑** `config/config.yaml`
2. **注释** 当前启用的提供商配置
3. **解注释** 目标提供商配置
4. **验证配置** `python config/validate_config.py`
5. **重启** 系统服务

```yaml
# 从DeepSeek切换到OpenAI
provide_settings:
  llm:
    # 注释DeepSeek配置
    # provider: "DeepSeek"
    # config:
    #   model: "deepseek-coder"
    
    # 解注释OpenAI配置
    provider: "OpenAI"
    config:
      model: "o1-mini"
      api_key_env: "OPENAI_API_KEY"
```

### 启用Agent专用配置

1. **找到** 目标Agent配置部分
2. **解注释** `llm_override`配置块
3. **修改** 模型参数（可选）
4. **验证配置** `python config/validate_config.py`
5. **重启** 系统服务

```yaml
agents:
  project_manager:
    enabled: true
    # 解注释下面的配置启用专用LLM
    llm_override:
      provider: "DeepSeek"
      config:
        model: "deepseek-v3"
        api_key_env: "DEEPSEEK_API_KEY"
        temperature: 0.2
        max_tokens: 16000
```

### 禁用Agent专用配置

1. **找到** Agent的`llm_override`配置
2. **注释** 整个`llm_override`块
3. **验证配置** `python config/validate_config.py`
4. **重启** 系统服务

```yaml
agents:
  project_manager:
    enabled: true
    # 注释专用配置，恢复使用全局配置
    # llm_override:
    #   provider: "DeepSeek"
    #   config:
    #     model: "deepseek-v3"
```

## 🧪 配置验证

### 使用验证脚本（推荐）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行完整的配置验证
python config/validate_config.py
```

验证脚本输出示例：
```
============================================================
🔧 华为多Agent协作系统 - 配置验证工具
============================================================

🔐 环境变量检查:
  ✅ DEEPSEEK_API_KEY: sk-12345...
  ✅ SILICONFLOW_API_KEY: sk-67890...

📋 全局配置验证:
  LLM提供商: DeepSeek
  LLM模型: deepseek-coder
  API密钥: ✅ 已设置

🤖 Agent配置验证:
  project_manager: ✅ 启用
    └─ 使用全局LLM: DeepSeek - deepseek-coder
  code_generator: ✅ 启用
    └─ 使用专用LLM: DeepSeek - deepseek-reasoner

🚀 系统已准备就绪，可以启动服务！
```

### 手动验证配置

```bash
# 激活虚拟环境
source .venv/bin/activate

# 简单的配置加载测试
python -c "
from shared.config_loader import ConfigLoader
config = ConfigLoader()
print('✅ 配置加载成功')
print(f'全局LLM: {config.get_llm_config()}')
print(f'项目管理Agent LLM: {config.get_llm_config(\"project_manager\")}')
"
```

### 测试Agent专用配置

```bash
# 测试不同Agent的LLM配置
python -c "
from shared.config_loader import ConfigLoader
config = ConfigLoader()

agents = ['project_manager', 'code_generator', 'final_generator']
for agent in agents:
    llm_config = config.get_llm_config(agent)
    print(f'{agent}: {llm_config[\"provider\"]} - {llm_config[\"model\"]}')
"
```

## 🚨 常见问题

### Q1: 环境变量未设置

**问题**：系统提示API密钥未设置

**解决**：
1. 检查`.env`文件是否存在
2. 确认环境变量名称正确
3. 重启终端或重新加载环境变量
4. 运行验证脚本检查：`python config/validate_config.py`

### Q2: Agent专用配置不生效

**问题**：Agent仍使用全局配置

**解决**：
1. 确认`llm_override`配置正确解注释
2. 检查YAML格式是否正确（注意缩进）
3. 运行验证脚本检查：`python config/validate_config.py`
4. 重启系统服务

### Q3: 配置文件语法错误

**问题**：YAML解析失败

**解决**：
1. 使用验证脚本检查：`python config/validate_config.py`
2. 使用YAML验证工具检查语法
3. 注意缩进必须使用空格，不能使用Tab
4. 确保字符串值用引号包围

### Q4: 配置验证脚本报错

**问题**：运行验证脚本时出现导入错误

**解决**：
1. 确保已激活虚拟环境：`source .venv/bin/activate`
2. 安装所有依赖：`pip install -r requirements.txt`
3. 检查项目路径是否正确

## 📞 技术支持

如需更多帮助，请：

1. **首先运行验证脚本**：`python config/validate_config.py`
2. 查看系统日志：`logs/mcp_system.log`
3. 检查环境变量设置
4. 确认网络连接和API密钥有效性

---

**最后更新**：2024年1月
**版本**：2.0.0 