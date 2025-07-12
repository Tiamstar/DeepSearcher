#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final Generator Agent
华为多Agent协作系统 - 最终代码生成Agent
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


class FinalGeneratorAgent(MCPAgent):
    """最终代码生成Agent - 根据检查结果优化和生成最终代码"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("final_generator")
        self.config = config or {}
        self.llm_config = self.config.get("llm_config", {})
        self.llm_client = None
        
        # 声明能力
        self.declare_capability("code.finalize", {
            "description": "根据初版代码和检查结果生成最终代码",
            "parameters": ["initial_code", "review_result", "requirement", "language"]
        })
        self.declare_capability("code.optimize", {
            "description": "优化代码质量和性能",
            "parameters": ["code", "optimization_goals", "language"]
        })
        self.declare_capability("code.refactor", {
            "description": "重构代码结构",
            "parameters": ["code", "refactor_type", "language"]
        })
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化最终代码生成Agent"""
        try:
            # 获取LLM配置
            if not self.llm_config or not self.llm_config.get("provider"):
                # 如果没有传入LLM配置，从配置加载器获取
                from shared.config_loader import ConfigLoader
                config_loader = ConfigLoader()
                self.llm_config = config_loader.get_llm_config("final_generator")
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
            
            self.logger.info(f"最终代码生成Agent初始化成功，使用LLM: {provider} - {model}")
            
            return {
                "agent_id": self.agent_id,
                "capabilities": self.capabilities,
                "llm_type": llm_type,
                "llm_provider": provider,
                "llm_model": model,
                "optimization_types": ["performance", "readability", "security", "maintainability"],
                "refactor_types": ["structure", "naming", "pattern", "architecture"],
                "initialized_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"最终代码生成Agent初始化失败: {str(e)}")
            raise
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理最终代码生成相关请求"""
        try:
            method = message.method
            params = message.params or {}
            
            if method == "code.finalize":
                result = await self._finalize_code(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "code.optimize":
                result = await self._optimize_code(params)
                return self.protocol.create_response(message.id, result)
            
            elif method == "code.refactor":
                result = await self._refactor_code(params)
                return self.protocol.create_response(message.id, result)
            
            else:
                return self.protocol.handle_method_not_found(message.id, method)
                
        except Exception as e:
            self.logger.error(f"处理最终代码生成请求失败: {str(e)}")
            return self.protocol.handle_internal_error(message.id, str(e))
    
    async def _finalize_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终代码"""
        initial_code = params.get("initial_code", "")
        review_result = params.get("review_result", {})
        requirement = params.get("requirement", "")
        language = params.get("language", "python")
        
        if not initial_code:
            raise ValueError("初版代码不能为空")
        
        # 构建最终代码生成提示词
        system_prompt = self._build_finalization_prompt(language)
        
        # 提取检查结果中的问题和建议
        issues = review_result.get("issues_found", [])
        suggestions = review_result.get("suggestions", [])
        score = review_result.get("score", 0)
        
        issues_text = "\n".join([f"- {issue.get('message', str(issue))}" for issue in issues[:10]])
        suggestions_text = "\n".join([f"- {suggestion}" for suggestion in suggestions[:10]])
        
        user_prompt = f"""原始需求：{requirement}

初版代码：
```{language}
{initial_code}
```

代码检查结果：
评分：{score}/100

发现的问题：
{issues_text if issues_text else "无严重问题"}

改进建议：
{suggestions_text if suggestions_text else "无特殊建议"}

请根据检查结果优化代码，生成最终版本。确保：
1. 修复所有发现的问题
2. 应用改进建议
3. 提高代码质量和可读性
4. 保持功能完整性
5. 符合{language}最佳实践

请直接输出优化后的完整代码。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.chat(messages)
            final_code = self._extract_code_from_response(response.content)
            
            # 只返回最终代码，不包含其他元数据
            result = {
                "code": final_code
            }
            
            self.logger.info(f"最终代码生成完成，语言: {language}")
            return result
            
        except Exception as e:
            self.logger.error(f"最终代码生成失败: {str(e)}")
            raise
    
    async def _optimize_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """优化代码"""
        code = params.get("code", "")
        optimization_goals = params.get("optimization_goals", ["performance"])
        language = params.get("language", "python")
        
        if not code:
            raise ValueError("代码内容不能为空")
        
        # 构建优化提示词
        goals_text = ", ".join(optimization_goals)
        system_prompt = f"""你是一个专业的{language}代码优化专家。

请对提供的代码进行优化，重点关注以下目标：{goals_text}

优化原则：
1. 性能优化：减少时间复杂度，优化算法效率
2. 可读性：改善代码结构，增加清晰注释
3. 安全性：修复潜在安全漏洞，增强输入验证
4. 可维护性：模块化设计，降低耦合度
5. 内存效率：优化内存使用，避免内存泄漏

请提供优化后的代码和详细的优化说明。"""
        
        user_prompt = f"""需要优化的{language}代码：

```{language}
{code}
```

优化目标：{goals_text}

请进行相应优化。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.chat(messages)
            optimized_code = self._extract_code_from_response(response.content)
            
            # 只返回优化后的代码
            result = {
                "code": optimized_code
            }
            
            self.logger.info(f"代码优化完成，目标: {goals_text}")
            return result
            
        except Exception as e:
            self.logger.error(f"代码优化失败: {str(e)}")
            raise
    
    async def _refactor_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """重构代码"""
        code = params.get("code", "")
        refactor_type = params.get("refactor_type", "structure")
        language = params.get("language", "python")
        
        if not code:
            raise ValueError("代码内容不能为空")
        
        # 构建重构提示词
        system_prompt = f"""你是一个专业的{language}代码重构专家。

重构类型：{refactor_type}

重构指导原则：
- structure: 改善代码结构，提取函数/类，减少嵌套
- naming: 优化变量、函数、类的命名
- pattern: 应用设计模式，改善代码设计
- architecture: 重新组织代码架构，提高模块化

请进行相应的重构，保持功能不变的同时提高代码质量。"""
        
        user_prompt = f"""需要重构的{language}代码：

```{language}
{code}
```

重构类型：{refactor_type}

请进行重构。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.chat(messages)
            refactored_code = self._extract_code_from_response(response.content)
            
            # 只返回重构后的代码
            result = {
                "code": refactored_code
            }
            
            self.logger.info(f"代码重构完成，类型: {refactor_type}")
            return result
            
        except Exception as e:
            self.logger.error(f"代码重构失败: {str(e)}")
            raise
    
    def _build_finalization_prompt(self, language: str) -> str:
        """构建最终代码生成系统提示词"""
        base_prompt = f"""你是一个专业的{language}代码优化专家，擅长根据代码检查结果生成高质量的最终代码。"""
        
        if language.lower() == "arkts":
            base_prompt += """
你专精于华为ArkTS开发，熟悉：
- ArkTS语法和最佳实践
- 华为鸿蒙开发规范
- ArkUI组件优化
- 性能调优技巧
"""
        elif language.lower() == "cpp":
            base_prompt += """
你专精于C++开发，熟悉：
- 现代C++最佳实践
- 内存管理优化
- STL高效使用
- 多线程安全
"""
        elif language.lower() == "python":
            base_prompt += """
你专精于Python开发，熟悉：
- Python最佳实践和PEP规范
- 性能优化技巧
- 异步编程模式
- 代码可读性提升
"""
        
        base_prompt += """
你的任务是：
1. 分析代码检查结果中的问题和建议
2. 修复所有发现的bug和安全问题
3. 应用性能优化建议
4. 提高代码可读性和可维护性
5. 确保代码符合最佳实践
6. 保持原有功能完整性

请生成经过充分优化的最终代码。"""
        
        return base_prompt
    
    def _extract_code_from_response(self, response: str) -> str:
        """从LLM响应中提取代码"""
        response = BaseLLM.remove_think(response)
        
        import re
        code_pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        return response.strip()
    
    def _extract_optimization_notes(self, response: str) -> List[str]:
        """提取优化说明"""
        response = BaseLLM.remove_think(response)
        
        lines = response.split('\n')
        notes = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* ') or line.startswith('1. '):
                notes.append(line)
        
        return notes[:15]
    
    def _extract_refactor_notes(self, response: str) -> List[str]:
        """提取重构说明"""
        return self._extract_optimization_notes(response)
    
    def _analyze_improvements(self, initial_code: str, final_code: str, 
                            issues: List[Dict], suggestions: List[str]) -> List[Dict[str, Any]]:
        """分析代码改进情况"""
        improvements = []
        
        # 基于问题数量估算修复情况
        for issue in issues[:5]:  # 最多分析5个问题
            improvements.append({
                "type": "bug_fix",
                "description": f"修复问题: {issue.get('message', str(issue))[:100]}",
                "impact": "high" if "error" in str(issue).lower() else "medium"
            })
        
        # 基于建议估算增强情况
        for suggestion in suggestions[:5]:  # 最多分析5个建议
            improvements.append({
                "type": "enhancement",
                "description": f"应用建议: {suggestion[:100]}",
                "impact": "medium"
            })
        
        # 基于代码长度变化分析
        length_change = len(final_code) - len(initial_code)
        if abs(length_change) > 50:
            improvements.append({
                "type": "structure",
                "description": f"代码结构调整，长度变化: {length_change}字符",
                "impact": "low"
            })
        
        return improvements
    
    async def get_prompts(self) -> List[Dict[str, Any]]:
        """获取支持的Prompts"""
        return [
            {
                "name": "finalize_code",
                "description": "根据检查结果生成最终代码",
                "arguments": [
                    {
                        "name": "initial_code",
                        "description": "初版代码",
                        "required": True
                    },
                    {
                        "name": "review_result",
                        "description": "代码检查结果",
                        "required": True
                    },
                    {
                        "name": "requirement",
                        "description": "原始需求",
                        "required": False
                    }
                ]
            }
        ]
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取支持的Tools"""
        return [
            {
                "name": "code_finalize",
                "description": "根据初版代码和检查结果生成最终优化代码",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "initial_code": {
                            "type": "string",
                            "description": "初版代码"
                        },
                        "review_result": {
                            "type": "object",
                            "description": "代码检查结果"
                        },
                        "requirement": {
                            "type": "string",
                            "description": "原始需求描述"
                        },
                        "language": {
                            "type": "string",
                            "description": "编程语言"
                        }
                    },
                    "required": ["initial_code", "review_result", "language"]
                }
            },
            {
                "name": "code_optimize",
                "description": "优化代码质量和性能",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要优化的代码"
                        },
                        "optimization_goals": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["performance", "readability", "security", "maintainability"]
                            },
                            "description": "优化目标"
                        },
                        "language": {
                            "type": "string",
                            "description": "编程语言"
                        }
                    },
                    "required": ["code", "language"]
                }
            }
        ] 