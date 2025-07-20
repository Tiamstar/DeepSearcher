# 错误修复工作流二测试工具使用说明

## 概述

`test_error_fix_workflow.py` 是专门用于测试错误修复工作流二的独立入口函数，完全基于现有的 `collaborative_workflow.py` 中的错误修复机制实现。

## 工作流二（错误修复工作流）流程

1. **静态检查**：使用代码检查Agent执行 codelinter 静态检查
2. **编译检查**：使用项目管理Agent执行 hvigorw 编译检查  
3. **错误分析**：项目管理Agent分析错误信息并决定搜索关键词
4. **搜索解决方案**：搜索Agent根据关键词搜索修复方案
5. **代码修复**：代码生成Agent执行具体的代码修复
6. **循环验证**：重复检查直到错误修复完成或达到最大循环次数（3次）

## 使用方法

### 基本用法

```bash
python test_error_fix_workflow.py
```

### 带参数用法

```bash
# 指定用户需求描述
python test_error_fix_workflow.py --requirement "修复登录页面的输入验证错误"

# 指定会话ID
python test_error_fix_workflow.py --session-id "test_session_001"

# 使用JSON输出格式
python test_error_fix_workflow.py --output json

# 指定配置文件
python test_error_fix_workflow.py --config custom_config.yaml
```

## 参数说明

- `--requirement`: 模拟用户需求描述，用于生成搜索关键词（默认："测试登录页面组件的错误修复"）
- `--session-id`: 指定会话ID，用于跟踪工作流状态（可选，自动生成）
- `--config`: 指定配置文件路径（可选，使用默认统一配置）
- `--output`: 输出格式，可选 "text" 或 "json"（默认："text"）

## 前置条件

1. **Index.ets文件存在**：确保 `/home/deepsearch/deep-searcher/MyApplication2/entry/src/main/ets/pages/Index.ets` 文件存在
2. **文件包含错误**：Index.ets文件应包含一些可以被检测到的错误（语法错误、编译错误等）
3. **环境配置**：确保系统中已安装和配置好：
   - codelinter（静态检查工具）
   - hvigorw（鸿蒙编译工具）
   - 各种Agent的依赖环境

## 输出说明

### 文本格式输出

测试工具会显示详细的执行过程：

```
================================================================================
🔧 开始测试错误修复工作流二
   - 会话ID: error_fix_test_1642345678
   - 用户需求: 测试登录页面组件的错误修复  
   - 测试目标: Index.ets文件的错误检查和修复
================================================================================

🔍 步骤1: 执行静态检查 (codelinter)
📥 代码检查Agent返回结果: success=True
   - 错误数量: 2
   - 警告数量: 1
   - 检查类型: codelinter

🔧 步骤2: 执行编译检查 (hvigorw)  
📥 项目管理Agent编译结果: success=True
   - 编译状态: FAILED
   - 返回码: 1
   - 错误数量: 1
   - 警告数量: 0

⚠️ 发现错误，开始执行错误修复工作流
   - 静态检查错误: 2个
   - 编译错误: 1个
   - 总错误数: 3个

🔄 开始执行错误修复循环
[错误修复过程详细日志...]

================================================================================
📊 错误修复工作流测试完成

🎯 错误修复工作流测试摘要:
   状态: ✅ 成功
   修复循环次数: 2
   最大循环次数: 3
   工作流完成: True
   最终错误数: 0
     - 静态检查错误: 0
     - 编译错误: 0
   修复的文件数量: 1
     - MyApplication2/entry/src/main/ets/pages/Index.ets: fixed

🎉 所有错误已修复！

📝 说明:
   - 此测试专门验证错误修复工作流二的功能
   - 从现有Index.ets文件开始进行错误检查和修复
   - 验证静态检查、编译检查和循环修复机制
================================================================================

⏱️ 总测试时间: 45.67秒
```

### JSON格式输出

```json
{
  "success": true,
  "session_id": "error_fix_test_1642345678",
  "workflow_type": "error_fix_test",
  "test_summary": {
    "fix_attempts": 2,
    "max_fix_attempts": 3,
    "workflow_completed": true,
    "final_error_count": 0,
    "static_errors": 0,
    "compile_errors": 0
  },
  "generated_files": [
    {
      "path": "MyApplication2/entry/src/main/ets/pages/Index.ets",
      "type": "arkts", 
      "status": "fixed",
      "content": "..."
    }
  ],
  "error_details": {
    "lint_errors": [],
    "compile_errors": []
  }
}
```

## 测试场景

### 场景1：无错误代码
如果Index.ets文件没有错误，工具会显示：
```
✅ 没有发现错误，无需进入修复工作流
```

### 场景2：成功修复
错误被完全修复后，会显示成功信息和修复统计。

### 场景3：部分修复
达到最大修复次数但仍有未解决错误时，会显示：
```
⚠️ 达到最大修复次数，但仍有未解决的错误
```

## 与完整工作流的一致性

这个测试工具完全基于 `mcp_orchestrator/collaborative_workflow.py` 中的实现：

- **使用相同的WorkflowContext**：确保Agent间的上下文传递一致
- **调用相同的Agent方法**：使用相同的Agent接口和参数
- **遵循相同的错误修复流程**：严格按照工作流二的4个步骤执行
- **保持相同的输出格式**：与完整工作流的日志格式保持一致

## 常见问题

### Q: 文件不存在错误
**A**: 确保Index.ets文件路径正确，或者先运行完整工作流生成文件。

### Q: Agent初始化失败  
**A**: 检查配置文件和环境变量是否正确设置。

### Q: 工具执行失败
**A**: 确认codelinter和hvigorw工具在MyApplication2目录下可正常使用。

### Q: 修复不成功
**A**: 查看详细日志，检查是否是搜索或代码生成环节的问题。

## 调试建议

1. 使用 `--output json` 获取结构化的结果数据
2. 查看 `error_fix_workflow_test.log` 文件获取详细日志
3. 检查各个Agent的返回结果和错误信息
4. 验证codelinter和hvigorw在项目目录下的执行情况