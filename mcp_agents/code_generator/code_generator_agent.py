#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Generator Agent
华为多Agent协作系统 - 代码生成Agent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 确保加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from typing import Dict, Any, List
from datetime import datetime

from mcp_agents.base import MCPAgent, MCPMessage
from deepsearcher.llm.base import BaseLLM
from deepsearcher.llm import DeepSeek, OpenAI, Anthropic

# 移除硬编码模板，让LLM根据需求完全生成代码


class CodeGeneratorAgent(MCPAgent):
    """代码生成Agent - 负责根据需求和搜索结果生成代码"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("code_generator")
        self.config = config or {}
        self.llm_config = self.config.get("llm_config", {})
        self.llm_client = None
        self.temperature = 0.7
        self.max_tokens = 16000
        
        # 项目路径配置
        from pathlib import Path
        self.project_root = Path(__file__).parent.parent.parent
        self.myapplication2_path = self.project_root / "MyApplication2"
        
        # 声明能力
        self.declare_capability("code.generate", {
            "description": "根据需求和上下文生成代码",
            "parameters": ["requirement", "context", "language", "framework"]
        })
        self.declare_capability("code.template", {
            "description": "生成代码模板",
            "parameters": ["template_type", "language", "parameters"]
        })
        self.declare_capability("code.optimize", {
            "description": "优化现有代码", 
            "parameters": ["code", "optimization_type", "language"]
        })
        
        # 新增鸿蒙专用能力
        self.declare_capability("code.generate_harmonyos", {
            "description": "生成鸿蒙ArkTS代码",
            "parameters": ["requirement", "context", "target_files", "project_path", "is_fixing", "previous_errors"]
        })
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化代码生成Agent"""
        try:
            # 获取LLM配置
            if not self.llm_config or not self.llm_config.get("provider"):
                # 如果没有传入LLM配置，从配置加载器获取
                from shared.config_loader import ConfigLoader
                config_loader = ConfigLoader()
                self.llm_config = config_loader.get_llm_config("code_generator")
                self.logger.info("从配置加载器获取LLM配置")
            
            # 获取配置信息
            provider = self.llm_config.get("provider", "")
            llm_type = self.llm_config.get("type", provider.lower())
            model = self.llm_config.get("model", "")
            api_key = self.llm_config.get("api_key", "")
            base_url = self.llm_config.get("base_url", "")
            temperature = self.llm_config.get("temperature", 0.7)
            max_tokens = self.llm_config.get("max_tokens", 16000)
            
            
            
            if llm_type.lower() == "deepseek":
                # 确保有API密钥
                if not api_key:
                    api_key = os.getenv("DEEPSEEK_API_KEY")
                if not api_key:
                    raise ValueError("LLM API密钥未配置，请设置环境变量")
                
                self.llm_client = DeepSeek(
                    api_key=api_key,
                    base_url=base_url or "https://api.deepseek.com",
                    model=model or "deepseek-coder"
                )
                self.temperature = temperature
                self.max_tokens = max_tokens
            elif llm_type.lower() == "openai":
                # 确保有API密钥
                if not api_key:
                    api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("LLM API密钥未配置，请设置环境变量")
                
                self.llm_client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    model=model or "gpt-3.5-turbo"
                )
                self.temperature = temperature
                self.max_tokens = max_tokens
            elif llm_type.lower() == "anthropic":
                # 确保有API密钥（优先使用配置中的密钥）
                if not api_key:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("LLM API密钥未配置，请在配置文件中设置api_key或设置环境变量")
                
                self.llm_client = Anthropic(
                    api_key=api_key,
                    base_url=base_url,
                    model=model or "claude-3-haiku-20240307"
                )
                # 保存temperature和max_tokens参数用于后续调用
                self.temperature = temperature
                self.max_tokens = max_tokens
            else:
                raise ValueError(f"不支持的LLM类型: {llm_type}")
            
            self.logger.info(f"代码生成Agent初始化成功")
            
            return {
                "agent_id": self.agent_id,
                "capabilities": self.capabilities,
                "llm_type": llm_type,
                "llm_provider": provider,
                "llm_model": model,
                "supported_languages": ["python", "javascript", "typescript", "arkts", "cpp", "java", "go"],
                "initialized_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"代码生成Agent初始化失败: {str(e)}")
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理代码生成相关请求"""
        try:
            method = message.method
            params = message.params or {}
            
            if method == "code.generate":
                result = await self._generate_code(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "code.template":
                result = await self._generate_template(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "code.optimize":
                result = await self._optimize_code(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "code.generate_harmonyos":
                result = await self._generate_harmonyos_code(params)
                return self.protocol.create_response(message.id, result)
            
            else:
                return self.protocol.handle_method_not_found(message.id, method)
                
        except Exception as e:
            self.logger.error(f"处理代码生成请求失败: {str(e)}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _generate_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成代码"""
        requirement = params.get("requirement", "")
        context = params.get("context", "")
        language = params.get("language", "python")
        framework = params.get("framework", "")
        
        if not requirement:
            raise ValueError("需求描述不能为空")
        
        # 构建代码生成提示词
        system_prompt = self._build_code_generation_prompt(language, framework)
        
        user_prompt = f"""需求描述：{requirement}

上下文信息：{context}

请根据需求生成{language}代码，确保代码：
1. 符合最佳实践和编码规范
2. 包含必要的注释和文档
3. 处理异常情况
4. 可读性强，结构清晰
5. 如果是华为相关开发，请遵循华为开发规范

重要：请只输出纯ArkTS代码，不要包含任何markdown格式、说明文字或解释。
输出格式：直接输出ArkTS代码，从import语句或注释开始，到最后的}}结束。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.chat(messages)
            generated_code = self._extract_code_from_response(response.content)
            
            result = {
                "requirement": requirement,
                "language": language,
                "framework": framework,
                "generated_code": generated_code,
                "raw_response": response.content,
                "token_usage": response.total_tokens,
                "agent_id": self.agent_id,
                "generated_at": datetime.now().isoformat(),
                "metadata": {
                    "code_length": len(generated_code),
                    "estimated_lines": len(generated_code.split('\n')),
                    "context_provided": bool(context)
                }
            }
            
            self.logger.info(f"代码生成完成，语言: {language}")
            return result
            
        except Exception as e:
            self.logger.error(f"代码生成失败: {str(e)}")
            raise
    
    async def _generate_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成代码模板"""
        template_type = params.get("template_type", "")
        language = params.get("language", "python")
        template_params = params.get("parameters", {})
        
        if not template_type:
            raise ValueError("模板类型不能为空")
        
        # 构建模板生成提示词
        system_prompt = f"""你是一个专业的{language}代码模板生成器。
        
请参考指定的模板类型生成标准的代码模板，包含：
1. 基础结构和框架
2. 常用的方法和属性
3. 必要的注释和文档字符串
4. 错误处理机制
5. 最佳实践示例

模板不可直接使用"""
        
        user_prompt = f"""模板类型：{template_type}
编程语言：{language}
模板参数：{template_params}

请生成对应的代码模板。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.chat(messages)
            template_code = self._extract_code_from_response(response.content)
            
            result = {
                "template_type": template_type,
                "language": language,
                "parameters": template_params,
                "template_code": template_code,
                "raw_response": response.content,
                "token_usage": response.total_tokens,
                "agent_id": self.agent_id,
                "generated_at": datetime.now().isoformat(),
                "usage_instructions": self._generate_usage_instructions(template_type, language)
            }
            
            self.logger.info(f"代码模板生成完成，类型: {template_type}")
            return result
            
        except Exception as e:
            self.logger.error(f"代码模板生成失败: {str(e)}")
            raise
    
    async def _optimize_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """优化代码"""
        code = params.get("code", "")
        optimization_type = params.get("optimization_type", "general")
        language = params.get("language", "python")
        
        if not code:
            raise ValueError("代码内容不能为空")
        
        # 构建代码优化提示词
        system_prompt = f"""你是一个专业的{language}代码优化专家。

请对提供的代码进行优化，重点关注：
1. 性能优化
2. 代码可读性
3. 内存使用效率
4. 错误处理
5. 代码结构和组织
6. 最佳实践应用

优化类型：{optimization_type}

请提供优化后的代码，并说明主要的优化点。"""
        
        user_prompt = f"""需要优化的{language}代码：

```{language}
{code}
```

请进行{optimization_type}优化。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.chat(messages)
            optimized_code = self._extract_code_from_response(response.content)
            optimization_notes = self._extract_optimization_notes(response.content)
            
            result = {
                "original_code": code,
                "optimized_code": optimized_code,
                "optimization_type": optimization_type,
                "language": language,
                "optimization_notes": optimization_notes,
                "raw_response": response.content,
                "token_usage": response.total_tokens,
                "agent_id": self.agent_id,
                "optimized_at": datetime.now().isoformat(),
                "improvement_metrics": {
                    "original_lines": len(code.split('\n')),
                    "optimized_lines": len(optimized_code.split('\n')),
                    "size_change": len(optimized_code) - len(code)
                }
            }
            
            self.logger.info(f"代码优化完成，类型: {optimization_type}")
            return result
            
        except Exception as e:
            self.logger.error(f"代码优化失败: {str(e)}")
            raise
    
    def _build_code_generation_prompt(self, language: str, framework: str) -> str:
        """构建代码生成系统提示词"""
        base_prompt = f"""你是一个专业的{language}开发专家，擅长编写高质量、可维护的代码。"""
        
        if framework:
            base_prompt += f"你特别熟悉{framework}框架的开发。"
        
        if language.lower() == "arkts":
            base_prompt += """
你专精于华为ArkTS开发，熟悉：
- ArkTS语法和特性
- 华为鸿蒙开发规范
- ArkUI组件开发
- 状态管理和数据绑定
- 华为设备适配
"""
        elif language.lower() == "cpp":
            base_prompt += """
你专精于C++开发，熟悉：
- 现代C++特性（C++11/14/17/20）
- 内存管理和RAII
- STL容器和算法
- 多线程编程
- 性能优化
"""
        elif language.lower() == "python":
            base_prompt += """
你专精于Python开发，熟悉：
- Python最佳实践和PEP规范
- 异步编程和并发
- 数据处理和科学计算
- Web开发框架
- 测试驱动开发
"""
        
        base_prompt += """
请确保生成的代码：
1. 遵循语言的最佳实践和编码规范
2. 包含适当的错误处理
3. 有清晰的注释和文档
4. 结构良好，易于维护
5. 考虑性能和安全性
"""
        
        return base_prompt
    
    def _extract_code_from_response(self, response: str) -> str:
        """从LLM响应中提取纯代码"""
        # 移除思考标签
        response = BaseLLM.remove_think(response)
        
        import re
        
        # 1. 首先尝试提取代码块
        code_patterns = [
            r'```(?:arkts|typescript|ets|ts)?\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'```(.*?)```'
        ]
        
        extracted_code = ""
        for pattern in code_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                extracted_code = matches[0].strip()
                break
        
        # 如果没有从代码块中提取到，则使用整个响应
        if not extracted_code:
            extracted_code = response.strip()
        
        # 2. 清理代码 - 移除中文内容和非代码部分
        lines = extracted_code.split('\n')
        clean_lines = []
        
        # 用于检测代码段的标志
        has_found_import = False
        has_found_entry = False
        has_found_component = False
        in_code_section = False
        
        for line in lines:
            line = line.rstrip()
            
            # 检测代码开始标志
            if 'import ' in line:
                has_found_import = True
                in_code_section = True
            if '@Entry' in line:
                has_found_entry = True
                in_code_section = True
            if '@Component' in line:
                has_found_component = True
                in_code_section = True
            
            # 跳过明显的中文文档说明和注释
            skip_patterns = [
                r'^根据.*',
                r'^以下是.*',
                r'^主要.*',
                r'^修复.*',
                r'^这.*',
                r'^\d+\.',
                r'^[\u4e00-\u9fff]+[：:]',
                r'^```',
                r'^#',
                r'^>',
            ]
            
            should_skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line):
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # 跳过含有大量中文字符的行，除非是在字符串字面量中
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', line)
            if len(chinese_chars) > 3 and not ("'" in line or '"' in line):
                continue
            
            # 如果是代码行，添加到结果中
            if in_code_section or has_found_import or has_found_entry or has_found_component or line.strip().startswith("import "):
                # 如果有包含中文的字符串，替换为英文等效内容
                if "'" in line or '"' in line:
                    line = re.sub(r"'[^']*[\u4e00-\u9fff][^']*'", "'Text'", line)
                    line = re.sub(r'"[^"]*[\u4e00-\u9fff][^"]*"', '"Text"', line)
                
                # 跳过纯中文注释行
                if line.strip().startswith("//") and re.search(r'[\u4e00-\u9fff]', line):
                    continue
                
                clean_lines.append(line)
        
        # 如果没有有效代码行，返回空字符串
        if not clean_lines:
            self.logger.warning("无法提取有效代码")
            return ""
            
        return '\n'.join(clean_lines)
    
    def _clean_and_validate_code(self, code: str) -> str:
        """清理和验证代码内容"""
        import re
        
        lines = code.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行
            if not line:
                clean_lines.append('')
                continue
            
            # 跳过中文解释和说明
            skip_patterns = [
                r'^根据.*',
                r'^以下是.*',
                r'^主要.*',
                r'^修复.*',
                r'^这.*',
                r'^\d+\.',
                r'^[\u4e00-\u9fff]+：',
                r'^[\u4e00-\u9fff]+:',
                r'```'
            ]
            
            should_skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line):
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # 检查是否包含中文字符（除了字符串字面量）
            if re.search(r'[\u4e00-\u9fff]', line):
                # 如果是字符串字面量，保留但替换中文为英文
                if "'" in line or '"' in line:
                    line = re.sub(r"'[^']*[\u4e00-\u9fff][^']*'", "'Text'", line)
                    line = re.sub(r'"[^"]*[\u4e00-\u9fff][^"]*"', '"Text"', line)
                    clean_lines.append(line)
                else:
                    # 其他包含中文的行跳过
                    continue
            else:
                clean_lines.append(line)
        
        cleaned_code = '\n'.join(clean_lines)
        
        # 验证是否包含ArkTS基本结构
        if self._has_arkts_structure(cleaned_code):
            return cleaned_code
        
        return ""
    
    def _generate_basic_template(self) -> str:
        """生成基础ArkTS模板"""
        return """import prompt from '@ohos.promptAction';

@Entry
@Component
struct Index {
  @State count: number = 0;

  build() {
    Column() {
      Text('Hello World')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .margin({ bottom: 20 })
      
      Button('Click Me')
        .width(150)
        .height(40)
        .onClick(() => {
          this.count++;
          prompt.showToast({
            message: `Count: ${this.count}`,
            duration: 2000
          });
        })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}"""
    
    def _read_readme_content(self) -> str:
        """读取README.md文件的实际内容"""
        try:
            readme_path = self.project_root / "MyApplication2" / "README.md"
            if readme_path.exists():
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找自然语言描述部分
                lines = content.split('\n')
                description_lines = []
                start_capturing = False
                
                for line in lines:
                    if "自然语言描述" in line:
                        start_capturing = True
                        continue
                    
                    if start_capturing:
                        # 如果遇到新的markdown标题，停止捕获（但允许第三级标题）
                        if line.strip().startswith('##') and not line.strip().startswith('###'):
                            break
                        
                        # 跳过空行和markdown语法，但保留内容
                        if line.strip() and not line.strip().startswith('---'):
                            description_lines.append(line.strip())
                
                description = '\n'.join(description_lines)
                self.logger.info(f"代码生成Agent读取README.md描述: {len(description)} 字符")
                
                return description if description else content
            else:
                self.logger.warning("README.md文件不存在")
                return ""
                
        except Exception as e:
            self.logger.error(f"读取README.md失败: {e}")
            return ""
    
    def _extract_optimization_notes(self, response: str) -> List[str]:
        """从优化响应中提取优化说明"""
        response = BaseLLM.remove_think(response)
        
        # 简单的优化说明提取
        lines = response.split('\n')
        notes = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* ') or line.startswith('1. '):
                notes.append(line)
        
        return notes[:10]  # 最多返回10个优化点
    
    def _generate_usage_instructions(self, template_type: str, language: str) -> str:
        """生成模板使用说明"""
        return f"""
使用说明：
1. 这是一个{language} {template_type}模板
2. 请根据实际需求填写TODO标记的部分
3. 根据项目需要调整导入和依赖
4. 运行前请确保环境配置正确
5. 建议进行单元测试验证功能
"""
    
    async def get_prompts(self) -> List[Dict[str, Any]]:
        """获取支持的Prompts"""
        return [
            {
                "name": "generate_code",
                "description": "根据需求生成代码",
                "arguments": [
                    {
                        "name": "requirement",
                        "description": "代码需求描述",
                        "required": True
                    },
                    {
                        "name": "language",
                        "description": "编程语言",
                        "required": True
                    },
                    {
                        "name": "context",
                        "description": "上下文信息",
                        "required": False
                    }
                ]
            },
            {
                "name": "generate_template",
                "description": "生成代码模板",
                "arguments": [
                    {
                        "name": "template_type",
                        "description": "模板类型",
                        "required": True
                    },
                    {
                        "name": "language",
                        "description": "编程语言",
                        "required": True
                    }
                ]
            }
        ]
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取支持的Tools"""
        return [
            {
                "name": "code_generate",
                "description": "根据需求和上下文生成代码",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement": {
                            "type": "string",
                            "description": "代码需求描述"
                        },
                        "language": {
                            "type": "string",
                            "description": "编程语言",
                            "enum": ["python", "javascript", "typescript", "arkts", "cpp", "java", "go"]
                        },
                        "context": {
                            "type": "string",
                            "description": "上下文信息（搜索结果、文档等）"
                        },
                        "framework": {
                            "type": "string",
                            "description": "使用的框架或库"
                        }
                    },
                    "required": ["requirement", "language"]
                }
            },
            {
                "name": "code_template",
                "description": "生成代码模板",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "template_type": {
                            "type": "string",
                            "description": "模板类型（如：class, function, api, web_app等）"
                        },
                        "language": {
                            "type": "string",
                            "description": "编程语言"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "模板参数"
                        }
                    },
                    "required": ["template_type", "language"]
                }
            }
        ]
    
    # ==================== 鸿蒙专用方法 ====================
    
    async def _generate_harmonyos_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成鸿蒙ArkTS代码 - 支持上下文感知的任务处理"""
        try:
            # 从新的上下文系统获取参数
            user_requirement = params.get("user_requirement", params.get("requirement", ""))
            current_task_type = params.get("current_task_type", "initial_generation")
            current_phase = params.get("current_phase", "code_generation")
            fix_attempt = params.get("fix_attempt", 0)
            
            self.logger.info(f"代码生成Agent收到任务")
            self.logger.info(f"当前阶段: {current_phase}")
            self.logger.info(f"任务类型: {current_task_type}")
            self.logger.info(f"修复尝试: {fix_attempt}")
            self.logger.info(f"用户需求: {user_requirement}")
            
            if not user_requirement:
                raise ValueError("需求描述不能为空")
            
            # 根据任务类型选择处理方式
            if current_task_type == "error_fixing":
                result = await self._handle_error_fixing(params)
            else:
                result = await self._handle_initial_generation(params)
            
            self.logger.info(f"代码生成完成: {result.get('success', False)}")
            return result
                
        except Exception as e:
            self.logger.error(f"鸿蒙代码生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": [],
                "task_type": current_task_type
            }
    
    def _build_harmonyos_prompt(self, is_fixing: bool = False, previous_errors: List = None) -> str:
        """构建鸿蒙代码生成提示词"""
        base_prompt = """Generate HarmonyOS ArkTS code. Use @Entry @Component decorators, proper struct and build() method, appropriate state management."""

        if is_fixing and previous_errors:
            fix_prompt = f"""
Fix these errors:
{previous_errors}
Focus on imports, decorators, syntax, and types.
"""
            return base_prompt + fix_prompt
        
        return base_prompt
    
    async def _process_and_save_code(self, generated_content: str, target_files: List[Dict], project_path: str) -> List[Dict[str, Any]]:
        """处理生成的代码并保存到文件"""
        import re
        import os
        
        generated_files = []
        
        try:
            # 尝试从LLM响应中提取文件代码
            if "```" in generated_content:
                # 提取代码块
                code_blocks = re.findall(r'```(?:arkts|typescript|ets)?\n(.*?)\n```', generated_content, re.DOTALL)
                
                for i, target_file in enumerate(target_files):
                    file_path = target_file["path"]
                    file_type = target_file["type"]
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # 获取代码内容
                    if i < len(code_blocks):
                        code_content = code_blocks[i].strip()
                    else:
                        # 如果没有足够的代码块，使用备用方案
                        code_content = self._generate_fallback_code(file_type, file_path)
                    
                    # 保存文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(code_content)
                    
                    generated_files.append({
                        "path": file_path,
                        "type": file_type,
                        "size": len(code_content),
                        "content_preview": code_content[:200] + "..." if len(code_content) > 200 else code_content
                    })
                    
                    self.logger.info(f"已生成文件: {file_path}")
            
            else:
                # 如果没有代码块，尝试从整个响应中提取代码或生成备用代码
                for target_file in target_files:
                    file_path = target_file["path"]
                    file_type = target_file["type"]
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # 尝试提取纯代码内容
                    code_content = self._extract_pure_code(generated_content, file_type, file_path)
                    
                    # 保存文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(code_content)
                    
                    generated_files.append({
                        "path": file_path,
                        "type": file_type,
                        "size": len(code_content),
                        "content_preview": code_content[:200] + "..." if len(code_content) > 200 else code_content
                    })
                    
                    self.logger.info(f"已生成模板文件: {file_path}")
            
            return generated_files
            
        except Exception as e:
            self.logger.error(f"保存代码文件失败: {e}")
            raise
    
    def _generate_fallback_code(self, file_type: str, file_path: str) -> str:
        """禁用硬编码备用模板 - 强制使用LLM生成"""
        self.logger.error(f"❌ 试图使用硬编码备用模板，这已被禁用: {file_path}")
        self.logger.error(f"❌ 必须使用LLM生成代码，不允许硬编码模板")
        raise ValueError(f"硬编码备用模板已被禁用，必须使用LLM生成代码: {file_path}")
    
    def _extract_pure_code(self, generated_content: str, file_type: str, file_path: str) -> str:
        """从LLM响应中提取纯代码内容"""
        import re
        
        # 尝试多种方式提取代码
        
        # 1. 首先尝试提取代码块（更宽松的正则）
        code_block_patterns = [
            r'```(?:arkts|typescript|ets|ts)?\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'```(.*?)```'
        ]
        
        for pattern in code_block_patterns:
            matches = re.findall(pattern, generated_content, re.DOTALL)
            if matches:
                code = matches[0].strip()
                # 直接清理中文内容，不依赖验证
                cleaned_code = self._remove_chinese_from_code(code)
                if self._has_arkts_structure(cleaned_code):
                    return cleaned_code
        
        # 2. 如果没有代码块，尝试查找ArkTS结构
        lines = generated_content.split('\n')
        code_lines = []
        in_code_section = False
        
        for line in lines:
            line = line.strip()
            
            # 跳过明显的中文文档说明和解释
            skip_keywords = ['主要修复内容', '修复说明', '以下是', '根据', '这些修改', '修复点', '修复了', '修正了', '优化了', '应该能解决', '主要修复点', '这些修改应该能解决']
            if any(keyword in line for keyword in skip_keywords):
                continue
            
            # 跳过纯中文行和数字编号行
            if re.match(r'^\d+\.', line) or re.match(r'^[\u4e00-\u9fff]+：', line):
                continue
            
            # 跳过markdown标记行
            if line.startswith('```') or line.strip() == '```':
                continue
            
            # 检测代码开始
            if any(keyword in line for keyword in ['import ', '@Entry', '@Component', 'struct ', 'class ']):
                in_code_section = True
            
            # 如果在代码区域，收集代码行
            if in_code_section:
                # 只接受英文注释和代码行，跳过中文注释和解释
                if line and (not line.startswith('//') or (line.startswith('//') and not re.search(r'[\u4e00-\u9fff]', line))):
                    # 进一步过滤包含中文字符的行（除了字符串字面量）
                    if not re.search(r'[\u4e00-\u9fff]', line) or "'" in line or '"' in line:
                        code_lines.append(line)
        
        if code_lines:
            extracted_code = '\n'.join(code_lines)
            if self._is_valid_arkts_code(extracted_code):
                return extracted_code
        
        # 3. 最后备用方案 - 不使用硬编码模板
        self.logger.warning(f"⚠️ 无法从LLM响应中提取有效代码: {file_path}")
        self.logger.warning(f"⚠️ LLM响应内容: {generated_content[:500]}...")
        raise ValueError(f"无法从LLM响应中提取有效的ArkTS代码: {file_path}")
    
    def _is_valid_arkts_code(self, code: str) -> bool:
        """检查是否是有效的ArkTS代码"""
        import re
        
        # 基本的ArkTS代码特征检查
        arkts_keywords = ['@Entry', '@Component', 'struct', 'build()', 'import']
        has_arkts_structure = any(keyword in code for keyword in arkts_keywords)
        
        # 检查是否包含过多的中文文档说明
        doc_keywords = ['主要修复', '修复说明', '以下是', '这些修改解决了', '修复点', '修复了', '修正了', '优化了', '应该能解决']
        has_too_much_doc = any(keyword in code for keyword in doc_keywords)
        
        # 检查是否包含中文注释或中文字符在主要代码区域
        chinese_in_code = re.search(r'[\u4e00-\u9fff]', code)
        
        # 检查是否包含markdown标记
        has_markdown = '```' in code
        
        return has_arkts_structure and not has_too_much_doc and not chinese_in_code and not has_markdown
    
    def _has_arkts_structure(self, code: str) -> bool:
        """检查代码是否具有ArkTS结构"""
        arkts_keywords = ['@Entry', '@Component', 'struct', 'build()', 'import']
        return any(keyword in code for keyword in arkts_keywords)
    
    def _remove_chinese_from_code(self, code: str) -> str:
        """从代码中移除中文字符和解释文字"""
        import re
        lines = code.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳过明显的中文文档说明
            skip_keywords = ['主要修复内容', '修复说明', '以下是', '根据', '这些修改', '修复点', '修复了', '修正了', '优化了', '应该能解决', '主要修复点', '这些修改应该能解决']
            if any(keyword in line for keyword in skip_keywords):
                continue
            
            # 跳过纯中文行和数字编号行
            if re.match(r'^\d+\.', line) or re.match(r'^[\u4e00-\u9fff]+：', line):
                continue
            
            # 跳过markdown标记行
            if line.startswith('```') or line.strip() == '```':
                continue
            
            # 处理包含中文的代码行
            if re.search(r'[\u4e00-\u9fff]', line):
                # 如果是字符串字面量，替换为英文
                if "'" in line or '"' in line:
                    # 替换中文字符串为英文
                    line = re.sub(r"'[^']*[\u4e00-\u9fff][^']*'", "'Chinese text'", line)
                    line = re.sub(r'"[^"]*[\u4e00-\u9fff][^"]*"', '"Chinese text"', line)
                    clean_lines.append(line)
                # 如果是中文注释，跳过
                elif line.startswith('//'):
                    continue
                # 其他包含中文的行，跳过
                else:
                    continue
            else:
                clean_lines.append(line)
        
        cleaned_code = '\n'.join(clean_lines)
        
        # 最后一次清理，确保没有中文字符
        if re.search(r'[\u4e00-\u9fff]', cleaned_code):
            # 如果仍有中文，做最后的清理
            final_lines = []
            for line in cleaned_code.split('\n'):
                if not re.search(r'[\u4e00-\u9fff]', line):
                    final_lines.append(line)
            cleaned_code = '\n'.join(final_lines)
        
        return cleaned_code
    
    # ==================== 简化的代码生成方法 ====================
    
    def simple_generate_code(self, user_requirements: str, search_results: str = "") -> str:
        """简化的代码生成方法"""
        try:
            from .simple_prompts import INITIAL_CODE_GENERATION_PROMPT
            
            prompt = INITIAL_CODE_GENERATION_PROMPT.format(
                user_requirements=user_requirements,
                search_results=search_results or "No search results available"
            )
            
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages)
            
            # 简单的代码提取
            code = response.content.strip()
            
            # 移除markdown标记
            if code.startswith('```'):
                lines = code.split('\n')
                code = '\n'.join(lines[1:-1])
            
            # 移除中文行
            lines = code.split('\n')
            clean_lines = []
            for line in lines:
                if not self._contains_chinese(line) or "'" in line or '"' in line:
                    clean_lines.append(line)
            
            return '\n'.join(clean_lines)
            
        except Exception as e:
            self.logger.error(f"简化代码生成失败: {e}")
            # 不使用硬编码模板，抛出错误让调用者处理
            raise
    
    def simple_fix_code(self, user_requirements: str, original_code: str, error_info: str, search_results: str = "") -> str:
        """简化的代码修复方法"""
        try:
            from .simple_prompts import ERROR_FIXING_PROMPT
            
            prompt = ERROR_FIXING_PROMPT.format(
                user_requirements=user_requirements,
                original_code=original_code,
                error_info=error_info,
                search_results=search_results or "No search results available"
            )
            
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages)
            
            # 简单的代码提取
            code = response.content.strip()
            
            # 移除markdown标记
            if code.startswith('```'):
                lines = code.split('\n')
                code = '\n'.join(lines[1:-1])
            
            # 移除中文行
            lines = code.split('\n')
            clean_lines = []
            for line in lines:
                if not self._contains_chinese(line) or "'" in line or '"' in line:
                    clean_lines.append(line)
            
            return '\n'.join(clean_lines)
            
        except Exception as e:
            self.logger.error(f"简化代码修复失败: {e}")
            return original_code
    
    def _contains_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        import re
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def _simple_extract_code(self, response: str) -> str:
        """简化的代码提取方法 - 最小程度清理，保留LLM原始输出"""
        import re
        
        # 移除思考标签
        response = BaseLLM.remove_think(response)
        
        # 1. 首先尝试提取markdown代码块
        code_patterns = [
            r'```(?:arkts|typescript|ets|ts)?\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'```(.*?)```'
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                code = matches[0].strip()
                self.logger.info(f"🔍 从代码块中提取到代码，长度: {len(code)}")
                return code
        
        # 2. 如果没有代码块，检查是否整个响应就是代码
        # 检查是否包含ArkTS特征
        if any(keyword in response for keyword in ['@Entry', '@Component', 'struct', 'build()', 'import']):
            self.logger.info(f"🔍 检测到ArkTS关键词，使用整个响应作为代码")
            return response.strip()
        
        # 3. 尝试查找纯代码段（从import或@Entry开始）
        lines = response.split('\n')
        code_start = -1
        
        for i, line in enumerate(lines):
            line = line.strip()
            if any(keyword in line for keyword in ['import ', '@Entry', '@Component', 'struct ']):
                code_start = i
                break
        
        if code_start >= 0:
            code_lines = lines[code_start:]
            code = '\n'.join(code_lines).strip()
            self.logger.info(f"🔍 从第{code_start}行开始提取代码，长度: {len(code)}")
            return code
        
        # 4. 最后备用：使用原始响应
        self.logger.warning(f"⚠️ 无法识别代码结构，使用原始响应")
        return response.strip()

    # ==================== 上下文感知任务处理方法 ====================
    
    async def _handle_initial_generation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始代码生成任务"""
        try:
            self.logger.info("开始初始代码生成")
            
            # 从项目规划和参考资料中获取信息
            project_plan = params.get("project_plan", {})
            planned_files = params.get("planned_files", [])
            reference_materials = params.get("reference_materials", [])
            
            # 构建上下文信息
            context_info = self._build_generation_context(project_plan, reference_materials)
            
            # 为每个计划文件生成代码
            generated_files = []
            for file_plan in planned_files:
                file_content = await self._generate_file_content(file_plan, context_info)
                
                if file_content:
                    # 保存文件
                    file_path = file_plan.get("path", "")
                    if file_path:
                        await self._save_file_content(file_path, file_content)
                        generated_files.append({
                            "path": file_path,
                            "type": file_plan.get("type", "arkts"),
                            "content": file_content,
                            "status": "generated"
                        })
            
            self.logger.info(f"初始代码生成完成: {len(generated_files)} 个文件")
            
            return {
                "success": True,
                "generated_files": generated_files,
                "task_type": "initial_generation",
                "total_files": len(generated_files)
            }
            
        except Exception as e:
            self.logger.error(f"初始代码生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": [],
                "task_type": "initial_generation"
            }
    
    async def _handle_error_fixing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理错误修复任务"""
        try:
            self.logger.info("开始错误修复")
            
            # 确保获取完整的用户需求（包括README内容）
            user_requirement = params.get("user_requirement", params.get("requirement", ""))
            
            # 从MyApplication2/README.md读取完整的需求描述
            readme_content = self._read_readme_requirement()
            if readme_content:
                user_requirement = readme_content
                self.logger.info(f"从README.md读取到完整需求: {len(user_requirement)} 字符")
            
            # 优先使用项目管理Agent的精确分析结果
            error_analysis = params.get("error_analysis", [])
            files_to_fix = params.get("files_to_fix", [])
            target_files_with_locations = params.get("target_files_with_locations", [])
            precise_targeting = params.get("precise_targeting", False)
            
            # 备用：原始错误信息
            errors_to_fix = params.get("errors_to_fix", [])
            solution_references = params.get("solution_references", [])
            existing_files = params.get("existing_files", [])
            
            self.logger.info(f"📝 使用精确定位: {precise_targeting}")
            self.logger.info(f"📝 项目管理Agent分析: {len(error_analysis)} 个错误")
            self.logger.info(f"📝 确定修复文件: {len(files_to_fix)} 个文件")
            self.logger.info(f"📝 原始错误信息: {len(errors_to_fix)} 个")
            self.logger.info(f"📝 现有文件: {len(existing_files)} 个")
            
            # 使用增强的错误过滤器
            from shared.error_analysis import workflow_error_filter
            
            # 获取原始输出用于统计分析
            raw_outputs = []
            for error in errors_to_fix:
                if error.get('raw_output'):
                    raw_outputs.append(error.get('raw_output'))
                elif error.get('raw_message'):
                    raw_outputs.append(error.get('raw_message'))
            
            combined_output = '\n'.join(raw_outputs)
            
            # 记录原始错误数量用于验证
            original_error_count = len(errors_to_fix)
            self.logger.info(f"🔍 开始智能错误过滤，原始错误数: {original_error_count}")
            
            # 使用增强过滤器检查真实错误
            filtered_real_errors = workflow_error_filter.filter_errors_for_workflow(errors_to_fix, combined_output)
            
            self.logger.info(f"🔍 智能过滤后错误数: {len(filtered_real_errors)}")
            
            # 如果过滤器移除了所有错误，但原本有错误，可能存在误判
            if not filtered_real_errors and original_error_count > 0:
                self.logger.warning(f"⚠️ 智能过滤移除了所有{original_error_count}个错误，可能存在误判")
                self.logger.warning("⚠️ 保留原始错误进行修复尝试，避免遗漏真实问题")
                
                # 至少保留前3个错误进行修复尝试
                errors_to_fix = errors_to_fix[:3]
                self.logger.info(f"🔄 回退策略：保留前{len(errors_to_fix)}个原始错误进行修复")
            else:
                # 使用过滤后的结果
                errors_to_fix = filtered_real_errors
            self.logger.info(f"智能过滤后的真实错误数量: {len(errors_to_fix)}")
            
            if not errors_to_fix and not error_analysis:
                self.logger.warning("没有错误需要修复")
                return {
                    "success": True,
                    "fixed_files": [],
                    "task_type": "error_fixing",
                    "message": "没有错误需要修复"
                }
            
            # 按文件分组错误 - 优先使用项目管理Agent的精确分析
            errors_by_file = {}
            
            if precise_targeting and error_analysis:
                # 使用项目管理Agent的精确分析结果
                self.logger.info(f"🔎 使用项目管理Agent的精确分析: {len(error_analysis)} 个错误")
                
                for analysis in error_analysis:
                    target_file = analysis.get("target_file", "")
                    error_id = analysis.get("error_id", 0)
                    fix_description = analysis.get("fix_description", "")
                    fix_location = analysis.get("location", "")
                    
                    self.logger.info(f"   错误{error_id}: target_file='{target_file}', location='{fix_location}'")
                    
                    if target_file and target_file.startswith("MyApplication2/"):
                        if target_file not in errors_by_file:
                            errors_by_file[target_file] = []
                        
                        # 创建增强的错误对象
                        enhanced_error = {
                            "error_id": error_id,
                            "message": analysis.get("error_message", ""),
                            "file_path": target_file,
                            "fix_description": fix_description,
                            "fix_location": fix_location,
                            "root_cause": analysis.get("root_cause", ""),
                            "search_keywords": analysis.get("search_keywords", []),
                            "from_analysis": True,  # 标记来源于项目管理Agent分析
                            "severity": "error"  # 明确设置为错误级别
                        }
                        errors_by_file[target_file].append(enhanced_error)
                    
            else:
                # 备用方案：使用过滤后的原始错误信息
                self.logger.info(f"🔍 使用原始错误信息: {len(errors_to_fix)} 个错误")
                
                for i, error in enumerate(errors_to_fix):
                    file_path = error.get("file_path", "")
                    error_message = error.get("message", "Unknown error")
                    
                    self.logger.info(f"   错误{i+1}: file_path='{file_path}', message='{error_message[:100]}'")
                    
                    # 处理文件路径问题
                    if not file_path or file_path in ["unknown", "", " "]:
                        # 对于无法确定文件的错误，尝试从错误信息中推断
                        if "Resource Pack Error" in error_message or "string.json" in error_message or "base/element" in error_message:
                            # 资源错误通常涉及资源文件
                            file_path = "MyApplication2/entry/src/main/resources/base/element/string.json"
                        elif "module.json" in error_message or "module.json5" in error_message:
                            # module.json相关错误
                            file_path = "MyApplication2/entry/src/main/module.json5"
                        elif "build" in error_message or "compilation" in error_message:
                            # 编译错误，从现有文件中找到第一个.ets文件
                            first_ets_file = None
                            for existing_file in existing_files:
                                if existing_file.get("path", "").endswith(".ets"):
                                    first_ets_file = existing_file.get("path")
                                    break
                            file_path = first_ets_file or "MyApplication2/entry/src/main/ets/pages/Index.ets"
                        else:
                            # 默认使用Index.ets
                            file_path = "MyApplication2/entry/src/main/ets/pages/Index.ets"
                        self.logger.info(f"     -> 推断文件路径: {file_path}")
                    
                    # 处理特殊情况：如果是Index.ts，确保修改为Index.ets
                    if file_path.endswith("Index.ts"):
                        old_path = file_path
                        file_path = file_path.replace("Index.ts", "Index.ets")
                        self.logger.info(f"将文件路径从 {old_path} 更正为 {file_path}")
                    
                    if file_path not in errors_by_file:
                        errors_by_file[file_path] = []
                    errors_by_file[file_path].append(error)
            
            self.logger.info(f"📋 错误分组完成: {len(errors_by_file)} 个文件")
            
            # 修复每个文件的错误
            fixed_files = []
            
            for j, (file_path, file_errors) in enumerate(errors_by_file.items()):
                self.logger.info(f"=== 修复文件 {j+1}/{len(errors_by_file)}: {file_path} ===")
                self.logger.info(f"  文件错误数量: {len(file_errors)} 个")
                
                # 读取现有文件内容（初始代码）
                import os
                existing_content = ""
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            existing_content = f.read()
                    except Exception as e:
                        self.logger.warning(f"读取现有文件失败: {file_path} - {e}")
                
                # 使用新的工作流特定的修复方法，确保传递完整信息：用户需求、错误信息、初始代码
                fixed_content = await self._fix_file_errors_with_prompt(
                    file_path, 
                    file_errors, 
                    existing_files, 
                    solution_references,
                    workflow_type="error_fixing",
                    user_requirement=user_requirement,  # 传递完整用户需求
                    existing_content=existing_content   # 传递初始代码
                )
                
                if fixed_content:
                    try:
                        # 保存修复后的文件
                        await self._save_file_content(file_path, fixed_content)
                        
                        # 额外保障：直接确保文件被写入
                        success = self._ensure_file_written(file_path, fixed_content)
                        if not success:
                            self.logger.warning(f"  ⚠️ 额外文件写入尝试失败: {file_path}")
                        
                        fixed_files.append({
                            "path": file_path,
                            "type": "arkts",
                            "content": fixed_content,
                            "status": "fixed",
                            "errors_fixed": len(file_errors)
                        })
                        self.logger.info(f"  ✓ 文件修复成功: {file_path}")
                        
                        # 验证文件是否真的被保存
                        import os
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            self.logger.info(f"  ✓ 文件存在于磁盘: {file_path}, 大小: {file_size} 字节")
                            
                            # 验证文件内容
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    saved_content = f.read()
                                
                                if saved_content == fixed_content:
                                    self.logger.info(f"  ✓ 文件内容验证成功: {file_path}")
                                else:
                                    self.logger.warning(f"  ⚠️ 文件内容验证失败: {file_path}, 长度差异: {len(saved_content)} vs {len(fixed_content)}")
                            except Exception as read_error:
                                self.logger.warning(f"  ⚠️ 文件内容验证失败: {file_path} - {read_error}")
                        else:
                            self.logger.error(f"  ✗ 文件未保存到磁盘: {file_path}")
                    except Exception as save_error:
                        self.logger.error(f"  ✗ 保存文件失败: {file_path} - {save_error}")
                        import traceback
                        self.logger.error(f"  详细错误: {traceback.format_exc()}")
                        
                        # 最后尝试：直接写入文件
                        try:
                            self.logger.info(f"  🔄 最后尝试直接写入文件: {file_path}")
                            success = self._ensure_file_written(file_path, fixed_content)
                            if success:
                                self.logger.info(f"  ✓ 最后尝试成功: {file_path}")
                                fixed_files.append({
                                    "path": file_path,
                                    "type": "arkts",
                                    "content": fixed_content,
                                    "status": "fixed",
                                    "errors_fixed": len(file_errors)
                                })
                            else:
                                self.logger.error(f"  ✗ 最后尝试失败: {file_path}")
                        except Exception as final_error:
                            self.logger.error(f"  ✗ 最后尝试出错: {file_path} - {final_error}")
                else:
                    self.logger.error(f"  ✗ 文件修复失败: {file_path}")
            
            self.logger.info(f"错误修复完成: {len(fixed_files)} 个文件")
            
            return {
                "success": True,
                "fixed_files": fixed_files,
                "task_type": "error_fixing",
                "total_files_fixed": len(fixed_files),
                "total_errors_fixed": sum(len(errors_by_file[fp]) for fp in errors_by_file)
            }
            
        except Exception as e:
            self.logger.error(f"错误修复失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "fixed_files": [],
                "task_type": "error_fixing"
            }
    
    async def _generate_file_content(self, file_plan: Dict[str, Any], context_info: str) -> str:
        """为单个文件生成代码内容 - 直接使用LLM输出，避免过度清理"""
        try:
            file_path = file_plan.get("path", "")
            file_type = file_plan.get("type", "arkts")
            purpose = file_plan.get("purpose", "")
            content_outline = file_plan.get("content_outline", "")
            key_components = file_plan.get("key_components", [])
            
            # 获取README.md的实际内容作为用户需求
            readme_content = self._read_readme_content()
            if not readme_content:
                readme_content = "Generate a simple ArkTS page component"
            
            # 使用简化的代码生成方法，避免复杂的清理机制
            from .simple_prompts import INITIAL_CODE_GENERATION_PROMPT
            
            # 构建专门的代码生成prompt
            prompt = INITIAL_CODE_GENERATION_PROMPT.format(
                user_requirements=readme_content,
                search_results=context_info or "No search results available"
            )
            
            # 调用LLM生成代码
            if not self.llm_client:
                await self._initialize_llm()
            
            if self.llm_client:
                self.logger.info(f"📤 正在为文件 {file_path} 调用LLM生成代码")
                self.logger.info(f"📝 用户需求: {readme_content[:100]}...")
                
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_client.chat(messages)
                
                # 直接使用LLM的响应，最小程度的清理
                generated_code = self._simple_extract_code(response.content)
                
                self.logger.info(f"📥 LLM返回代码长度: {len(generated_code)} 字符")
                self.logger.info(f"📥 代码预览: {generated_code[:200]}...")
                
                if generated_code and len(generated_code.strip()) > 50:
                    self.logger.info(f"✅ 文件代码生成成功: {file_path}")
                    return generated_code
                else:
                    self.logger.warning(f"⚠️ LLM生成的代码太短或为空，长度: {len(generated_code)}")
                    # 记录原始响应用于调试
                    self.logger.warning(f"🔍 原始LLM响应: {response.content[:500]}...")
                    raise ValueError("LLM生成的代码无效或为空")
            else:
                raise ValueError("LLM客户端未初始化")
                
        except Exception as e:
            self.logger.error(f"❌ 文件代码生成失败: {e}")
            # 不要回退到硬编码模板，而是抛出错误让调用者处理
            raise
    
    async def _fix_file_content(self, file_path: str, existing_content: str, 
                              file_errors: List[Dict], solution_references: List[Dict]) -> str:
        """修复文件内容 - 使用简化方法，直接调用LLM"""
        try:
            # 构建错误信息
            error_messages = []
            for error in file_errors:
                error_msg = f"- 第{error.get('line', '?')}行: {error.get('message', '')}"
                error_messages.append(error_msg)
            
            error_info = "\n".join(error_messages)
            
            # 构建解决方案信息
            solutions_info = ""
            if solution_references:
                solutions_info = "参考解决方案:\n"
                for i, solution in enumerate(solution_references[:3]):
                    solutions_info += f"{i+1}. {solution.get('content', '')}\n"
            
            # 获取用户需求
            readme_content = self._read_readme_content()
            if not readme_content:
                readme_content = "Fix compilation errors in Index.ets file"
            
            # 使用简化的错误修复prompt
            from .simple_prompts import ERROR_FIXING_PROMPT
            
            prompt = ERROR_FIXING_PROMPT.format(
                user_requirements=readme_content,
                original_code=existing_content,
                error_info=error_info,
                search_results=solutions_info or "No search results available"
            )
            
            # 调用LLM修复代码
            if not self.llm_client:
                await self._initialize_llm()
            
            if self.llm_client:
                self.logger.info(f"📤 正在修复文件 {file_path} 的错误")
                self.logger.info(f"📝 错误数量: {len(file_errors)}")
                self.logger.info(f"📝 原代码长度: {len(existing_content)} 字符")
                self.logger.info(f"📝 用户需求长度: {len(readme_content)} 字符")
                self.logger.info(f"📝 错误信息长度: {len(error_info)} 字符")
                self.logger.info(f"📝 解决方案长度: {len(solutions_info)} 字符")
                
                # 记录发送给LLM的完整信息
                self.logger.info(f"📝 用户需求预览: {readme_content[:200]}...")
                self.logger.info(f"📝 错误信息预览: {error_info[:200]}...")
                
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_client.chat(messages)
                
                # 使用简化的代码提取方法
                fixed_code = self._simple_extract_code(response.content)
                
                self.logger.info(f"📥 LLM返回修复代码长度: {len(fixed_code)} 字符")
                self.logger.info(f"📥 修复代码预览: {fixed_code[:200]}...")
                
                if fixed_code and len(fixed_code.strip()) > 50:
                    # 检查修复后的代码是否与原代码完全相同
                    if fixed_code.strip() == existing_content.strip():
                        self.logger.warning(f"⚠️ LLM返回的修复代码与原代码完全相同，可能未进行实际修复")
                        self.logger.warning(f"🔍 错误信息: {error_info[:200]}...")
                        self.logger.warning(f"🔍 原始LLM响应: {response.content[:500]}...")
                        # 记录错误但仍返回代码，让后续流程检测到修复失败
                    
                    self.logger.info(f"✅ 文件错误修复成功: {file_path}")
                    return fixed_code
                else:
                    self.logger.warning(f"⚠️ LLM修复的代码太短或为空，长度: {len(fixed_code)}")
                    self.logger.warning(f"🔍 原始LLM响应: {response.content[:500]}...")
                    self.logger.warning(f"🔍 错误信息: {error_info[:200]}...")
                    # 返回原内容，但增加详细日志
                    self.logger.warning(f"🔄 修复失败，返回原内容")
                    return existing_content
            else:
                raise ValueError("LLM客户端未初始化")
                
        except Exception as e:
            self.logger.error(f"❌ 文件错误修复失败: {e}")
            # 如果出现异常，返回原内容而不是抛出错误
            return existing_content
    
    def _build_generation_context(self, project_plan: Dict, reference_materials: List[Dict]) -> str:
        """构建代码生成上下文信息"""
        context_parts = []
        
        # 项目分析信息
        if project_plan:
            analysis = project_plan.get("requirement_analysis", {})
            if analysis:
                context_parts.append(f"项目功能: {analysis.get('main_functionality', '')}")
                context_parts.append(f"关键特性: {', '.join(analysis.get('key_features', []))}")
        
        # 参考资料
        if reference_materials:
            context_parts.append("参考资料:")
            for i, material in enumerate(reference_materials[:3]):  # 最多使用3个参考资料
                content = material.get("content", "")[:200]  # 限制长度
                context_parts.append(f"{i+1}. {content}")
        
        return "\n".join(context_parts)
    
    def _find_existing_file_content(self, file_path: str, existing_files: List[Dict]) -> str:
        """查找现有文件内容"""
        self.logger.info(f"🔍 查找文件内容: {file_path}")
        
        # 先在现有文件列表中查找
        for file_info in existing_files:
            if file_info.get("path") == file_path:
                content = file_info.get("content", "")
                self.logger.info(f"   -> 在现有文件列表中找到，内容长度: {len(content)}")
                return content
        
        # 如果没有找到，尝试从文件系统读取
        try:
            import os
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.logger.info(f"   -> 从文件系统读取，内容长度: {len(content)}")
                return content
        except Exception as e:
            self.logger.warning(f"   -> 读取文件失败: {e}")
        
        self.logger.info(f"   -> 未找到文件内容，返回空字符串")
        return ""
    
    async def _save_file_content(self, file_path: str, content: str):
        """保存文件内容"""
        try:
            import os
            
            self.logger.info(f"开始保存文件: {file_path}")
            self.logger.info(f"文件内容长度: {len(content)} 字符")
            
            # 验证文件路径
            if not file_path or not file_path.strip():
                self.logger.error(f"文件路径为空，无法保存文件")
                raise ValueError("文件路径为空")
            
            # 验证内容
            if not content:
                self.logger.warning(f"文件内容为空: {file_path}")
                content = "// 空文件"
            
            # 验证文件路径格式
            if not file_path.startswith("MyApplication2/"):
                self.logger.warning(f"文件路径格式异常，尝试修复: {file_path}")
                if file_path.endswith(".ets"):
                    file_path = f"MyApplication2/entry/src/main/ets/pages/{os.path.basename(file_path)}"
                elif file_path.endswith(".json"):
                    file_path = f"MyApplication2/entry/src/main/resources/base/element/{os.path.basename(file_path)}"
                elif file_path.endswith(".json5"):
                    file_path = f"MyApplication2/entry/src/main/{os.path.basename(file_path)}"
                else:
                    # 没有扩展名，默认为.ets文件
                    file_path = f"MyApplication2/entry/src/main/ets/pages/{os.path.basename(file_path)}.ets"
                self.logger.info(f"修复后的文件路径: {file_path}")
            
            # 处理特殊情况：如果是Index.ts，确保修改为Index.ets
            if file_path.endswith("Index.ts"):
                old_path = file_path
                file_path = file_path.replace("Index.ts", "Index.ets")
                self.logger.info(f"将文件路径从 {old_path} 更正为 {file_path}")
            
            # 最终验证：确保路径不为空且有效
            if not file_path or file_path.strip() == "":
                raise ValueError("修复后的文件路径仍为空")
            
            # 确保目录存在
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
                self.logger.info(f"确保目录存在: {dir_path}")
            
            # 写入文件前，先检查文件是否存在
            file_exists = os.path.exists(file_path)
            if file_exists:
                self.logger.info(f"文件已存在，将被覆盖: {file_path}")
                # 备份原文件
                import shutil
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
                self.logger.info(f"已备份原文件: {backup_path}")
            
            # 使用确保文件写入的方法
            success = self._ensure_file_written(file_path, content)
            
            if success:
                self.logger.info(f"文件成功写入: {file_path}")
                
                # 额外验证：确认文件内容是否正确
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        saved_content = f.read()
                    
                    if saved_content == content:
                        self.logger.info(f"文件内容验证成功: {file_path}")
                    else:
                        self.logger.warning(f"文件内容验证失败: {file_path}, 长度差异: {len(saved_content)} vs {len(content)}")
                except Exception as e:
                    self.logger.warning(f"文件内容验证失败: {file_path} - {e}")
            else:
                self.logger.error(f"文件写入失败: {file_path}")
                raise ValueError(f"无法写入文件: {file_path}")
            
        except Exception as e:
            self.logger.error(f"文件保存失败: {file_path} - {e}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise
    
    async def _generate_file_content_with_prompt(self, file_plan: Dict[str, Any], project_plan: Dict[str, Any], reference_materials: List[Dict[str, Any]], workflow_type: str) -> str:
        """使用工作流特定的提示词生成文件内容"""
        try:
            # 构建工作流特定的提示词
            workflow_prompt = self._build_harmonyos_prompt(workflow_type, {"file_plan": file_plan})
            
            # 构建文件特定的生成请求
            file_generation_prompt = f"""
{workflow_prompt}

Generate {file_plan.get('path', '')} for: {project_plan.get('requirement_analysis', {}).get('main_functionality', '')}
Reference: {self._format_reference_materials(reference_materials)}
Output code only:
"""
            
            if self.llm_client:
                messages = [{"role": "user", "content": file_generation_prompt}]
                response = self.llm_client.chat(messages)
                
                if hasattr(response, 'content'):
                    return response.content.strip()
                else:
                    return str(response).strip()
            else:
                self.logger.error("LLM客户端未初始化")
                return ""
                
        except Exception as e:
            self.logger.error(f"文件内容生成失败: {e}")
            return ""
    
    def _format_reference_materials(self, reference_materials: List[Dict[str, Any]]) -> str:
        """格式化参考资料"""
        if not reference_materials:
            return "无参考资料"
        
        formatted = []
        for i, material in enumerate(reference_materials[:3]):  # 只显示前3个
            content = material.get('content', '')
            if len(content) > 200:
                content = content[:200] + "..."
            formatted.append(f"{i+1}. {content}")
        
        return "\n".join(formatted)
    
    async def _fix_file_errors_with_prompt(self, file_path: str, file_errors: List[Dict[str, Any]], existing_files: List[Dict[str, Any]], solution_references: List[Dict[str, Any]], workflow_type: str, user_requirement: str = "", existing_content: str = "") -> str:
        """使用工作流特定的提示词修复文件错误"""
        try:
            # 优先使用传入的现有内容（初始代码）
            current_content = existing_content
            
            # 如果没有传入现有内容，从文件系统读取
            if not current_content:
                for existing_file in existing_files:
                    if existing_file.get("path") == file_path:
                        current_content = existing_file.get("content", "")
                        break
            
            # 如果仍然没有内容，尝试从文件系统直接读取
            if not current_content and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                except Exception as e:
                    self.logger.warning(f"从文件系统读取现有内容失败: {e}")
            
            if not current_content:
                # 尝试从文件系统读取
                try:
                    import os
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            current_content = f.read()
                except Exception as e:
                    self.logger.warning(f"无法读取现有文件 {file_path}: {e}")
            
            # 获取README.md的需求内容
            readme_content = self._read_readme_content()
            if not readme_content:
                readme_content = "生成一个简单的ArkTS页面组件"
                
            self.logger.info(f"为错误修复读取README.md需求: {len(readme_content)} 字符")
            
            # 检查是否有项目管理Agent的精确分析
            has_analysis = any(error.get('from_analysis', False) for error in file_errors)
            
            # 获取原始错误输出（特别是对于编译错误）
            raw_error_outputs = []
            for error in file_errors:
                if error.get('raw_message') and error.get('raw_message') not in raw_error_outputs:
                    raw_error_outputs.append(error.get('raw_message'))
                elif error.get('raw_output') and error.get('raw_output') not in raw_error_outputs:
                    raw_error_outputs.append(error.get('raw_output'))
            
            # 从原始输出中提取编译统计信息
            import re
            error_stats = {}
            for raw_output in raw_error_outputs:
                if not raw_output:
                    continue
                # 查找编译统计信息
                stats_match = re.search(r'COMPILE RESULT:(?:FAIL|PASS) \{ERROR:(\d+) WARN:(\d+)\}', raw_output)
                if stats_match:
                    error_stats["errors"] = int(stats_match.group(1))
                    error_stats["warnings"] = int(stats_match.group(2))
                    self.logger.info(f"从原始输出中提取到编译统计: {error_stats['errors']}个错误, {error_stats['warnings']}个警告")
            
            # 如果统计信息显示没有错误，但我们收到了错误对象，可能是误报
            if error_stats.get("errors") == 0 and len(file_errors) > 0:
                self.logger.warning(f"编译统计显示没有错误，但收到了{len(file_errors)}个错误对象，可能是误报")
                # 我们仍然继续处理，但记录警告
            
            if has_analysis:
                # 使用项目管理Agent的精确分析
                errors_description = "\n".join([
                    f"**错误 {error.get('error_id', i+1)}:**\n"
                    f"- 原始错误: {error.get('message', '')}\n"
                    f"- 根本原因: {error.get('root_cause', '未知')}\n"
                    f"- 修复位置: {error.get('fix_location', '未指定')}\n"
                    f"- 修复描述: {error.get('fix_description', '需要修复错误')}\n"
                    for i, error in enumerate(file_errors)
                ])
            else:
                # 备用：使用原始错误信息
                errors_description = "\n".join([
                    f"- 类型: {error.get('error_type', 'unknown')}, 消息: {error.get('message', '')}, 行号: {error.get('line', 'N/A')}, 严重性: {error.get('severity', 'unknown')}"
                    for error in file_errors
                ])
                
                # 添加原始错误输出（特别是对于编译错误）
                if raw_error_outputs:
                    errors_description += "\n\n原始错误输出:\n"
                    for i, raw_output in enumerate(raw_error_outputs[:3]):  # 最多包含3个原始输出
                        errors_description += f"--- 原始输出 {i+1} ---\n{raw_output[:500]}...\n"  # 限制长度
            
            solution_info = "\n".join([
                f"- {solution.get('content', '')[:150]}..."
                for solution in solution_references[:3]
            ]) if solution_references else "无可用解决方案"
            
            # 使用简化的错误修复提示词
            from .simple_prompts import ERROR_FIXING_PROMPT
            
            fix_prompt = ERROR_FIXING_PROMPT.format(
                user_requirements=f"原始需求: {user_requirement}\n\n修复文件: {file_path}",
                original_code=current_content,
                error_info=errors_description,
                search_results=solution_info
            )
            
            # 确保LLM客户端已初始化
            await self._initialize_llm()
            
            if self.llm_client:
                # 添加系统提示词，强调只输出纯代码
                system_prompt = """You are a HarmonyOS ArkTS code repair specialist.

ABSOLUTE REQUIREMENTS - STRICTLY ENFORCED:
1. Output ONLY executable ArkTS code - ZERO explanations, comments, documentation
2. FORBIDDEN: ``` markdown blocks, 中文字符, explanatory text, code descriptions
3. START: Direct import statements or @Entry decorator
4. END: Final closing brace }
5. NO text before code, NO text after code, NO headers, NO summaries
6. Fix ONLY compilation-blocking ERROR level issues (ignore warnings)
7. Preserve original code logic, variable names, and structure
8. Use only standard HarmonyOS ArkTS syntax and APIs
9. Ensure @Entry, @Component decorators are properly placed
10. Maintain original functionality while fixing syntax/compilation errors

IMMEDIATE CODE OUTPUT REQUIRED - NO PREAMBLE:"""
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": fix_prompt}
                ]
                
                response = self.llm_client.chat(messages)
                
                # 使用增强的代码提取方法
                fixed_code = self._extract_code_from_response(response.content)
                
                self.logger.info(f"文件错误修复完成: {file_path}")
                self.logger.info(f"代码提取结果长度: {len(fixed_code)} 字符")
                
                # 验证提取的代码是否为空
                if not fixed_code.strip():
                    self.logger.warning("提取的代码为空，尝试简单清理")
                    # 备用方案：简单清理中文和markdown标记
                    fixed_code = self.simple_fix_code(
                        f"原始需求: {readme_content}\n\n修复文件: {file_path}", 
                        current_content, 
                        errors_description, 
                        solution_info
                    )
                
                return fixed_code
            else:
                self.logger.error("LLM客户端未初始化")
                return ""
                
        except Exception as e:
            self.logger.error(f"使用提示词修复文件错误失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return ""
            
    
    async def _initialize_llm(self):
        """初始化LLM客户端（如果未初始化）"""
        if not self.llm_client:
            try:
                await self.initialize()
            except Exception as e:
                self.logger.error(f"LLM初始化失败: {e}")
    
    def _read_existing_index_file(self) -> str:
        """读取现有的Index.ets文件内容"""
        try:
            index_file_path = self.myapplication2_path / "entry/src/main/ets/pages/Index.ets"
            
            if not index_file_path.exists():
                return ""
            
            with open(index_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content
            
        except Exception as e:
            self.logger.error(f"读取Index.ets文件失败: {e}")
            return ""
    
    def _read_project_dependencies(self) -> Dict[str, Any]:
        """读取项目依赖信息"""
        try:
            dependencies_info = {}
            
            # 读取oh-package.json5文件
            oh_package_path = self.myapplication2_path / "oh-package.json5"
            if oh_package_path.exists():
                with open(oh_package_path, 'r', encoding='utf-8') as f:
                    dependencies_info["oh_package"] = f.read()
            
            # 读取entry/oh-package.json5文件
            entry_package_path = self.myapplication2_path / "entry/oh-package.json5"
            if entry_package_path.exists():
                with open(entry_package_path, 'r', encoding='utf-8') as f:
                    dependencies_info["entry_package"] = f.read()
            
            # 读取module.json5文件
            module_path = self.myapplication2_path / "entry/src/main/module.json5"
            if module_path.exists():
                with open(module_path, 'r', encoding='utf-8') as f:
                    dependencies_info["module"] = f.read()
            
            return dependencies_info
            
        except Exception as e:
            self.logger.error(f"读取项目依赖失败: {e}")
            return {}
    
    def _get_project_context_for_code_generation(self) -> str:
        """为代码生成获取项目上下文"""
        try:
            context_parts = []
            
            # 读取现有的Index.ets文件
            existing_content = self._read_existing_index_file()
            if existing_content:
                context_parts.append("=== 现有Index.ets文件内容 ===")
                context_parts.append(existing_content)
            
            # 读取项目依赖信息
            dependencies = self._read_project_dependencies()
            if dependencies:
                context_parts.append("\n=== 项目依赖信息 ===")
                for dep_type, content in dependencies.items():
                    context_parts.append(f"\n--- {dep_type} ---")
                    context_parts.append(content[:500])  # 限制长度
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"获取项目上下文失败: {e}")
            return "" 
    
    def _ensure_file_written(self, file_path: str, content: str) -> bool:
        """确保文件被正确写入磁盘，使用多种方法尝试"""
        try:
            import os
            import pathlib
            
            self.logger.info(f"确保文件写入: {file_path}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 方法1: 使用标准open写入
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.info(f"方法1成功: {file_path}")
                
                # 验证文件是否存在
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return True
            except Exception as e:
                self.logger.warning(f"方法1失败: {e}")
            
            # 方法2: 使用pathlib写入
            try:
                pathlib.Path(file_path).write_text(content, encoding='utf-8')
                self.logger.info(f"方法2成功: {file_path}")
                
                # 验证文件是否存在
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return True
            except Exception as e:
                self.logger.warning(f"方法2失败: {e}")
            
            # 方法3: 使用临时文件然后重命名
            try:
                import tempfile
                import shutil
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp:
                    temp.write(content)
                    temp_name = temp.name
                
                # 复制临时文件到目标位置
                shutil.copy2(temp_name, file_path)
                os.unlink(temp_name)  # 删除临时文件
                
                self.logger.info(f"方法3成功: {file_path}")
                
                # 验证文件是否存在
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return True
            except Exception as e:
                self.logger.warning(f"方法3失败: {e}")
            
            # 所有方法都失败
            self.logger.error(f"所有写入方法都失败: {file_path}")
            return False
            
        except Exception as e:
            self.logger.error(f"确保文件写入失败: {file_path} - {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    def _read_readme_requirement(self) -> str:
        """读取MyApplication2/README.md中的用户需求描述"""
        try:
            readme_path = self.myapplication2_path / "README.md"
            
            if not readme_path.exists():
                self.logger.warning(f"README.md文件不存在: {readme_path}")
                return ""
            
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取自然语言描述部分
            lines = content.split('\n')
            description_lines = []
            start_capturing = False
            
            for line in lines:
                if "自然语言描述" in line:
                    start_capturing = True
                    continue
                
                if start_capturing:
                    # 如果遇到新的markdown标题，停止捕获
                    if line.strip().startswith('##') and not line.strip().startswith('###'):
                        break
                    
                    # 跳过空行和markdown语法，但保留内容
                    if line.strip() and not line.strip().startswith('---'):
                        description_lines.append(line.strip())
            
            description = '\n'.join(description_lines)
            self.logger.info(f"从README.md提取自然语言描述: {len(description)} 字符")
            
            return description if description else content
            
        except Exception as e:
            self.logger.error(f"读取README.md文件失败: {e}")
            return ""