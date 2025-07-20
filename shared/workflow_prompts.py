#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流Prompt管理系统
为不同工作流阶段的Agent提供专门的prompt模板
"""

from typing import Dict, Any
from enum import Enum

class WorkflowType(Enum):
    INITIAL_GENERATION = "initial_generation"
    ERROR_FIXING = "error_fixing"

class WorkflowPrompts:
    """工作流Prompt管理器"""
    
    def __init__(self):
        self.prompts = {
            # 项目管理Agent prompts
            "project_manager": {
                WorkflowType.INITIAL_GENERATION: {
                    "system": """你是一个专业的鸿蒙应用项目管理专家。你的任务是分析用户需求，专注于单个页面文件的生成。

核心职责：
1. 分析README.md文件中的自然语言描述，理解要实现的功能
2. 分析现有项目结构，确定目标文件位置
3. 专注于单个页面文件的生成（路径：MyApplication2/entry/src/main/ets/pages/）
4. 为搜索Agent生成高质量的搜索问题（非关键词）

重要：
- 只生成单个页面文件，不是整个项目结构
- 搜索问题必须针对具体的ArkTS页面组件实现
- 关注鸿蒙ArkUI组件的使用和页面布局

输出要求：
- 生成目标文件路径（MyApplication2/entry/src/main/ets/pages/Index.ets）
- 文件类型为"page"
- 提供2-3个具体的搜索问题
- 考虑ArkTS页面组件的开发规范""",
                    
                    "user_template": """作为鸿蒙应用项目管理专家，请分析README.md文件中的自然语言描述并制定单个页面文件生成计划：

Index.ets文件中的自然语言描述：
{user_requirement}

现有项目结构：
{project_structure}

项目文件内容：
{project_context}

请完成以下任务：

1. **功能分析**：理解README.md文件中描述的具体功能需求
2. **文件规划**：确定要生成的目标文件（Index.ets）的内容和结构
3. **搜索问题设计**：为ArkTS页面组件实现生成2-3个具体的搜索问题

**搜索问题要求：**
- 每个问题应该是完整的句子，不是关键词列表
- 问题应该针对具体的ArkTS页面组件实现细节
- 根据README.md中的自然语言描述生成3个针对性问题

例如：
- 不要："HarmonyOS ArkTS 图片预览"
- 要："HarmonyOS ArkTS中如何使用ImagePreview组件实现图片缩放和滑动功能"
- 要："鸿蒙应用中如何使用@State管理图片列表和Swiper组件的当前索引"

请严格按照以下 JSON 格式输出：
{{
  "requirement_analysis": {{
    "main_functionality": "主要功能描述",
    "key_features": ["功能点1", "功能点2"],
    "technical_requirements": ["技术要求1", "技术要求2"]
  }},
  "planned_files": [
    {{
      "path": "MyApplication2/entry/src/main/ets/pages/Index.ets",
      "type": "page",
      "purpose": "应用入口页面",
      "content_outline": "包含@Entry @Component装饰器、页面状态管理、UI显示组件",
      "key_components": ["根据自然语言描述确定的组件"],
      "dependencies": ["根据自然语言描述确定的依赖"]
    }}
  ],
  "search_queries": [
    "根据README.md中的自然语言描述生成的具体搜索问题1",
    "根据README.md中的自然语言描述生成的具体搜索问题2",
    "根据README.md中的自然语言描述生成的具体搜索问题3"
  ]
}}"""
                },
                
                WorkflowType.ERROR_FIXING: {
                    "system": """你是一个专业的鸿蒙应用项目管理专家，专门负责Index.ets文件的错误分析和修复策略制定。

核心职责：
1. 深度分析Index.ets文件的编译错误和静态检查错误，理解错误的根本原因
2. 专注于单个页面文件的错误修复，主要关注Index.ets文件
3. 为搜索Agent生成3个高质量的搜索问题（非关键词）
4. 提供详细的修复指导和解决方案

重要：
- 专注于单个页面文件的错误修复，不是整个项目
- 搜索问题必须针对具体错误类型和ArkTS页面组件解决方案
- 关注ArkTS语法错误、组件使用错误、状态管理错误等
- 生成的搜索问题要能帮助找到具体的解决方案

错误类型分析指导：
- "CompileResource" → ArkTS页面代码编译错误，关注Index.ets文件
- 语法错误 → ArkTS语法问题，关注装饰器、组件、状态管理
- 组件错误 → ArkUI组件使用错误，关注组件属性和方法
- 导入错误 → 模块导入问题，关注依赖和路径
- “Build failed” → 整体构建失败，需要检查主要代码文件

重要要求：
- 错误文件路径为“unknown”或“build”时，必须智能推断真正的目标文件
- 所有文件路径必须以“MyApplication2/”开头
- 搜索关键词必须具体、有针对性，避免泛化的词汇
- 为代码生成Agent提供明确的修复指导和解决方案""",
                    
                    "user_template": """作为鸿蒙应用项目管理专家，请对以下编译错误进行深度分析：

用户需求：{user_requirement}

编译错误列表：
{current_errors}

已生成的文件：
{existing_files}

对于每个错误，请进行如下分析：

1. **错误类型识别**：
   - 如果错误消息包含"Resource Pack Error"，则是JSON资源文件问题
   - 如果包含"CompileResource"，则是ArkTS代码编译问题
   - 如果包含"Tools execution failed"，则是构建工具问题
   - 如果包含"Build failed"，则是整体构建失败

2. **文件路径推断**：
   - 如果错误文件路径为"unknown"或"build"，必须根据错误类型推断真正的目标文件
   - JSON资源错误 → MyApplication2/entry/src/main/resources/base/element/string.json
   - ArkTS编译错误 → MyApplication2/entry/src/main/ets/pages/Index.ets
   - 服务类错误 → MyApplication2/entry/src/main/ets/services/DataService.ets

3. **精确搜索问题设计**：
   - 避免泛化词汇如"鸿蒙 ArkTS 错误修复"
   - 生成具体的、针对性强的搜索问题（不是关键词列表）
   - 每个错误提供3个具体的搜索问题，这些问题将帮助找到具体的解决方案
   
   例如：
   * JSON错误: "HarmonyOS中 string.json文件出现Resource Pack Error如何修复格式错误"
   * 编译错误: "ArkTS @Entry @Component装饰器CompileResource错误的常见原因和解决方法"
   * 构建错误: "HarmonyOS hvigor构建出现Tools execution failed错误的排查和修复步骤"

请严格按照以下 JSON 格式输出：
{{
  "error_analysis": [
    {{
      "error_id": 1,
      "error_message": "原始错误消息",
      "root_cause": "深度分析的错误根本原因",
      "target_file": "根据错误类型推断的具体文件路径",
      "fix_location": "具体的修复位置和范围",
      "fix_description": "详细的修复操作指导",
      "search_queries": ["具体的搜索问题1", "具体的搜索问题2", "具体的搜索问题3"]
    }}
  ],
  "files_to_fix": [
    {{
      "file_path": "具体文件路径",
      "errors": [错误编号列表],
      "priority": "high"
    }}
  ],
  "search_queries": [
    "HarmonyOS ArkTS中CompileResource错误的常见原因和@Entry @Component装饰器的正确使用方法",
    "鸿蒙应用string.json文件Resource Pack Error错误的修复步骤和element目录结构要求",
    "hvigor构建失败Tools execution failed错误的排查方法和HarmonyOS项目配置修复"
  ]
}}"""
                }
            },
            
            # 搜索Agent prompts
            "search": {
                WorkflowType.INITIAL_GENERATION: {
                    "system": """你是一个专业的鸿蒙开发技术搜索专家。你的任务是搜索与单个页面组件生成相关的技术资料。

核心职责：
1. 搜索鸿蒙ArkTS页面组件的API文档和示例
2. 获取ArkTS语法和ArkUI组件使用方法
3. 收集页面组件开发的最佳实践和开发规范
4. 为单个页面文件生成提供技术参考

搜索重点：
- ArkTS页面组件开发模式
- @Entry @Component装饰器使用方法
- 页面状态管理和@State使用
- 页面布局和UI组件使用
- 页面组件的生命周期管理""",
                    
                    "search_keywords_template": "{search_keywords} HarmonyOS 鸿蒙 ArkTS ArkUI 代码示例 开发指南 API文档"
                },
                
                WorkflowType.ERROR_FIXING: {
                    "system": """你是一个专业的鸿蒙开发问题解决专家。你的任务是搜索Index.ets页面文件错误解决方案和调试方法。

核心职责：
1. 搜索ArkTS页面组件的具体错误解决方案
2. 查找类似页面组件问题的修复方法
3. 获取页面组件调试和问题诊断信息
4. 为Index.ets文件错误修复提供技术参考

搜索重点：
- ArkTS页面组件错误解决方案
- 页面组件调试方法和工具
- @Entry @Component装饰器相关问题
- 页面状态管理错误修复
- 页面布局和UI组件错误处理""",
                    
                    "search_keywords_template": "{error_keywords} HarmonyOS 鸿蒙 ArkTS ArkUI 错误修复 问题解决 调试"
                }
            },
            
            # 代码生成Agent prompts
            "code_generator": {
                WorkflowType.INITIAL_GENERATION: {
                    "system": """Generate HarmonyOS ArkTS code. Output only pure code, no explanations or markdown.""",
                    
                    "user_template": """Generate Index.ets code:

{user_requirement}

Reference:
{reference_materials}

Output code only:"""
                },
                
                WorkflowType.ERROR_FIXING: {
                    "system": """Fix ArkTS code compilation errors. Output only complete fixed code.""",
                    
                    "user_template": """Fix Index.ets errors:

Errors:
{error_analysis}

Solutions:
{solution_references}

Current code:
{existing_files}

Output fixed code:"""
                }
            }
        }
    
    def get_prompt(self, agent_type: str, workflow_type: WorkflowType, prompt_type: str = "system") -> str:
        """获取特定Agent和工作流的prompt"""
        try:
            return self.prompts[agent_type][workflow_type][prompt_type]
        except KeyError:
            return self.prompts[agent_type][WorkflowType.INITIAL_GENERATION][prompt_type]
    
    def format_user_prompt(self, agent_type: str, workflow_type: WorkflowType, **kwargs) -> str:
        """格式化用户prompt模板"""
        template = self.get_prompt(agent_type, workflow_type, "user_template")
        return template.format(**kwargs)
    
    def format_search_keywords(self, workflow_type: WorkflowType, **kwargs) -> str:
        """格式化搜索关键词模板"""
        template = self.get_prompt("search", workflow_type, "search_keywords_template")
        return template.format(**kwargs)

# 全局实例
workflow_prompts = WorkflowPrompts()