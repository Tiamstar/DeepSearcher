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


class CodeGeneratorAgent(MCPAgent):
    """代码生成Agent - 负责根据需求和搜索结果生成代码"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("code_generator")
        self.config = config or {}
        self.llm_config = self.config.get("llm_config", {})
        self.llm_client = None
        
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
            
            self.logger.info(f"初始化LLM: provider={provider}, model={model}, api_key_length={len(api_key) if api_key else 0}")
            
            if llm_type.lower() == "deepseek":
                # 确保有API密钥
                if not api_key:
                    api_key = os.getenv("DEEPSEEK_API_KEY")
                if not api_key:
                    raise ValueError("DeepSeek API密钥未配置，请设置DEEPSEEK_API_KEY环境变量")
                
                self.llm_client = DeepSeek(
                    api_key=api_key,
                    base_url=base_url or "https://api.deepseek.com",
                    model=model or "deepseek-coder"
                )
            elif llm_type.lower() == "openai":
                # 确保有API密钥
                if not api_key:
                    api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OpenAI API密钥未配置，请设置OPENAI_API_KEY环境变量")
                
                self.llm_client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    model=model or "gpt-3.5-turbo"
                )
            elif llm_type.lower() == "anthropic":
                # 确保有API密钥
                if not api_key:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("Anthropic API密钥未配置，请设置ANTHROPIC_API_KEY环境变量")
                
                self.llm_client = Anthropic(
                    api_key=api_key,
                    model=model or "claude-3-sonnet-20240229"
                )
            else:
                raise ValueError(f"不支持的LLM类型: {llm_type}")
            
            self.logger.info(f"代码生成Agent初始化成功，使用LLM: {provider} - {model}")
            
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

请直接生成代码，不需要额外的解释。"""
        
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
        
请根据指定的模板类型生成标准的代码模板，包含：
1. 基础结构和框架
2. 常用的方法和属性
3. 必要的注释和文档字符串
4. 错误处理机制
5. 最佳实践示例

模板应该是可直接使用的，包含占位符供用户填写具体实现。"""
        
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
        """从LLM响应中提取代码"""
        # 移除思考标签
        response = BaseLLM.remove_think(response)
        
        # 查找代码块
        import re
        
        # 匹配代码块
        code_pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            # 返回第一个代码块
            return matches[0].strip()
        
        # 如果没有代码块，返回整个响应（去除多余空白）
        return response.strip()
    
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