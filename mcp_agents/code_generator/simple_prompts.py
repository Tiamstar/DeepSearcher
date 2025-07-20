#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的代码生成Prompt系统
"""

# 初始代码生成Prompt
INITIAL_CODE_GENERATION_PROMPT = """Generate HarmonyOS ArkTS code for Index.ets based on requirements.

Requirements:
{user_requirements}

Reference:
{search_results}

Output only pure ArkTS code - no explanations, no markdown:"""

# 错误修复Prompt
ERROR_FIXING_PROMPT = """Fix HarmonyOS ArkTS code compilation errors.

Original requirements:
{user_requirements}

Current code:
{original_code}

Errors to fix:
{error_info}

Reference solutions:
{search_results}

Output only the complete fixed ArkTS code:"""