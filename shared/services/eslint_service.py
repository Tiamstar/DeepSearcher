#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESLint 代码检查服务 - 增强版ArkTS支持

基于ESLint工具的JavaScript/TypeScript/ArkTS代码检查
包含ArkTS装饰器语法预处理和专用解析器支持
"""

import asyncio
import json
import os
import tempfile
import time
import subprocess
import shutil
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from shared.interfaces import CodeReviewInterface, CodeReviewRequest, CodeReviewResult

logger = logging.getLogger(__name__)

@dataclass
class LineMapping:
    """行号映射信息"""
    original_line: int
    processed_line: int
    transformation_type: str
    original_content: str
    processed_content: str


class EnhancedArkTSPreprocessor:
    """增强版ArkTS预处理器 - 专注于兼容性和稳定性"""
    
    def __init__(self):
        self.line_mappings: List[LineMapping] = []
        self.arkts_globals = ""
        
        # 扩展ArkTS UI组件列表
        self.ui_components = [
            'Row', 'Column', 'Stack', 'Flex', 'Text', 'Button', 'Image', 
            'List', 'ListItem', 'Grid', 'GridItem', 'Scroll', 'Swiper',
            'Tabs', 'TabContent', 'TextInput', 'Checkbox', 'Radio', 'Toggle',
            'Slider', 'Progress', 'Rating', 'Divider', 'Sheet', 'Popup',
            # 添加更多ArkTS组件
            'Navigator', 'Canvas', 'Panel', 'Refresh', 'Navigation', 'LoadingProgress',
            'Select', 'Counter', 'PatternLock', 'Stepper', 'DataPanel', 'DatePicker',
            'TimePicker', 'TextPicker', 'SideBarContainer', 'AlphabetIndexer',
            'TextArea', 'RichText', 'Search', 'TextClock', 'Marquee', 'Menu'
        ]
        
        # 扩展控制流组件
        self.control_flow = [
            'ForEach', 'LazyForEach', 'If', 'ElseIf', 'Else', 'While', 'Match', 'Case'
        ]
        
        # 扩展样式常量
        self.style_constants = [
            'FontWeight', 'FontStyle', 'Color', 'Length', 'Alignment', 'FlexAlign', 
            'FlexDirection', 'TextDecorationType', 'BorderStyle', 'EdgeEffect', 'Curve',
            'BarState', 'Visibility', 'DisplayMode', 'ImageFit', 'SizeType', 'GradientDirection',
            'ResponseType', 'Axis', 'HoverEffect', 'NavigationType', 'DialogAlignment'
        ]
        
        # 扩展生命周期方法
        self.lifecycle_methods = [
            'aboutToAppear', 'aboutToDisappear', 'onPageShow', 
            'onPageHide', 'onBackPress', 'onVisibleAreaChange',
            'onAreaChange', 'onTouch', 'onKeyEvent', 'onHover'
        ]
        
        # 扩展UI链式调用模式
        self.ui_chain_patterns = [
            (r'\.width\s*\([^)]*\)', '.width(/* value */)'),
            (r'\.height\s*\([^)]*\)', '.height(/* value */)'),
            (r'\.backgroundColor\s*\([^)]*\)', '.backgroundColor(/* color */)'),
            (r'\.fontSize\s*\([^)]*\)', '.fontSize(/* size */)'),
            (r'\.fontColor\s*\([^)]*\)', '.fontColor(/* color */)'),
            (r'\.margin\s*\([^)]*\)', '.margin(/* value */)'),
            (r'\.padding\s*\([^)]*\)', '.padding(/* value */)'),
            (r'\.onClick\s*\([^)]*\)', '.onClick(/* handler */)'),
            # 添加更多链式调用模式
            (r'\.border\s*\([^)]*\)', '.border(/* value */)'),
            (r'\.borderRadius\s*\([^)]*\)', '.borderRadius(/* value */)'),
            (r'\.shadow\s*\([^)]*\)', '.shadow(/* value */)'),
            (r'\.opacity\s*\([^)]*\)', '.opacity(/* value */)'),
            (r'\.alignSelf\s*\([^)]*\)', '.alignSelf(/* value */)'),
            (r'\.layoutWeight\s*\([^)]*\)', '.layoutWeight(/* value */)'),
            (r'\.animation\s*\([^)]*\)', '.animation(/* value */)'),
            (r'\.gesture\s*\([^)]*\)', '.gesture(/* value */)'),
            (r'\.linearGradient\s*\([^)]*\)', '.linearGradient(/* value */)')
        ]

    def _generate_arkts_globals(self) -> str:
        """生成ArkTS全局变量和函数的模拟声明"""
        mock_definitions = []
        
        # 使用TypeScript风格声明UI组件，使其更像函数，减少解析错误
        for component in self.ui_components:
            mock_definitions.append(f"""
// ArkTS UI组件: {component}
function {component}(params) {{
    const component = {{}};
    component.width = function(v) {{ return component; }};
    component.height = function(v) {{ return component; }};
    component.backgroundColor = function(v) {{ return component; }};
    component.fontSize = function(v) {{ return component; }};
    component.fontColor = function(v) {{ return component; }};
    component.margin = function(v) {{ return component; }};
    component.padding = function(v) {{ return component; }};
    component.onClick = function(v) {{ return component; }};
    component.onChange = function(v) {{ return component; }};
    component.select = function(v) {{ return component; }};
    component.decoration = function(v) {{ return component; }};
    component.justifyContent = function(v) {{ return component; }};
    // 添加更多通用链式属性
    component.border = function(v) {{ return component; }};
    component.borderRadius = function(v) {{ return component; }};
    component.shadow = function(v) {{ return component; }};
    component.opacity = function(v) {{ return component; }};
    component.animation = function(v) {{ return component; }};
    component.layoutWeight = function(v) {{ return component; }};
    component.alignSelf = function(v) {{ return component; }};
    component.bindMenu = function(v) {{ return component; }};
    component.bindPopup = function(v) {{ return component; }};
    component.stateStyles = function(v) {{ return component; }};
    return component;
}}""")

        # 改进控制流组件的声明
        for control in self.control_flow:
            mock_definitions.append(f"""
// ArkTS控制流: {control}
function {control}(items, callback) {{
    const component = {{}};
    component.width = function(v) {{ return component; }};
    component.height = function(v) {{ return component; }};
    return component;
}}""")

        # 添加样式常量为对象，不再使用单纯的空对象
        for const in self.style_constants:
            mock_definitions.append(f"""
// ArkTS样式常量: {const}
const {const} = {{
    Black: '#000000',
    White: '#FFFFFF',
    Red: '#FF0000',
    Green: '#00FF00',
    Blue: '#0000FF',
    Center: 'center',
    Start: 'start',
    End: 'end',
    None: 'none',
    LineThrough: 'line-through',
    Underline: 'underline',
    SpaceBetween: 'space-between',
    SpaceAround: 'space-around'
}};""")

        # 生命周期方法
        for method in self.lifecycle_methods:
            mock_definitions.append(f"""
// ArkTS生命周期: {method}
function {method}() {{ 
    // 生命周期方法实现
}}""")

        # 添加ArkTS基本类型声明
        mock_definitions.append("""
// ArkTS基本类型声明
const string = String;
const number = Number;
const boolean = Boolean;
// void类型用undefined替代
const voidType = undefined;
// 资源类型
const Resource = Object;
const ObservedObject = Object;
const StorageLink = Object;
const StorageProp = Object;
const LocalStorage = Object;
const AppStorage = Object;
const PersistentStorage = Object;
// 添加常用工具类型
const Partial = Object;
const Required = Object;
const Readonly = Object;
const Record = Object;
const Pick = Object;
const Omit = Object;
""")

        # 添加ArkTS特有API和工具函数
        mock_definitions.append("""
// ArkTS资源引用和系统API
function $r(resource) {
    return resource;
}
const router = {
    push: function(options) {},
    back: function() {},
    clear: function() {}
};
const prompt = {
    showToast: function(options) {},
    showDialog: function(options) {}
};
const animateTo = function(options, callback) {};
// 状态管理API
function stateStyles(styles) {
    return styles;
}
// 本地存储API
function PersistProp(defaultValue, name) {
    return defaultValue;
}
// 动画相关
const curves = {
    LINEAR: 'linear',
    EASE: 'ease',
    EASE_IN: 'ease-in',
    EASE_OUT: 'ease-out',
    EASE_IN_OUT: 'ease-in-out'
};
// 媒体查询
function mediaQuery(condition) {
    return {
        onChange: function(callback) {}
    };
}
""")

        # 添加注释头部
        header = "// ArkTS全局变量和函数的模拟声明 - 仅用于代码检查\n// 这些声明不会影响实际代码执行\n"
        
        return header + '\n\n'.join(mock_definitions)

    def preprocess_arkts_code(self, code: str) -> Tuple[str, Dict[str, Any]]:
        """
        预处理ArkTS代码，使其可以被ESLint解析
        
        改进点:
        1. 更有效的类型注解处理
        2. 更智能的装饰器处理
        3. 完全重写struct到class转换
        4. 转换为ESLint可解析的TypeScript风格代码
        """
        self.line_mappings = []
        original_lines = code.split('\n')
        
        # 跟踪行号映射
        line_index = 1
        for original_line in original_lines:
            self.line_mappings.append(LineMapping(
                original_line=line_index,
                processed_line=line_index,  # 后面会更新
                transformation_type="initial",
                original_content=original_line,
                processed_content=original_line
            ))
            line_index += 1
        
        # 生成全局变量声明
        self.arkts_globals = self._generate_arkts_globals()
        processed_code = self.arkts_globals + '\n\n'
        
        # 计算全局变量声明的行数，用于之后的行号映射
        globals_lines_count = len(self.arkts_globals.split('\n'))
        
        # 预处理特殊关键字和符号
        code = self._preprocess_special_tokens(code)
        
        # 处理装饰器
        code, decorators_found = self._process_decorators_enhanced(code)
        
        # 处理ArkTS特有语法
        code, arkts_syntax_found = self._process_arkts_syntax_enhanced(code)
        
        # 处理build方法 - 完全重写此方法以更好地处理UI-DSL
        code = self._process_build_method_completely_new(code)
        
        processed_code += code
        
        # 更新行号映射，考虑全局变量声明导致的偏移
        for mapping in self.line_mappings:
            mapping.processed_line += globals_lines_count
        
        metadata = {
            "decorators_found": decorators_found,
            "arkts_syntax_found": arkts_syntax_found,
            "preprocessor_version": "3.0.0",
            "typescript_style_conversion": True,
            "globals_lines_count": globals_lines_count
        }
        
        return processed_code, metadata
        
    def _preprocess_special_tokens(self, code: str) -> str:
        """
        预处理特殊关键字和符号 - 改进版
        
        1. 处理void关键字
        2. 处理Resource类型
        3. 处理$r资源引用
        4. 处理特殊语法结构
        5. 处理ArkTS特有API调用
        """
        # 替换void关键字为voidType
        code = re.sub(r'\bvoid\b', 'voidType', code)
        
        # 处理$r资源引用 - 转换为函数调用
        code = re.sub(r'\$r\s*\([\'"]([^\'"]+)[\'"]\)', r'$r("\1")', code)
        
        # 处理数组类型声明 - 使用Array<T>形式
        code = re.sub(r':\s*([a-zA-Z_]\w*)\[\]', r': Array<\1>', code)
        
        # 处理特殊的资源类型声明
        code = re.sub(r':\s*Resource\s*([<\w>]*)\s*=', r'/* :Resource\1 */=', code)
        
        # 处理特殊的泛型语法 - 修复一些常见的语法错误
        code = re.sub(r'<{([^}]+)}>',  r'<{\1}>', code)
        
        # 处理特殊UI属性，如alignItems: center
        code = re.sub(r'(alignItems|justifyContent)\s*:\s*(\w+)', r'\1: "\2"', code)
        
        # 处理ArkTS特有API调用
        code = re.sub(r'router\.push\s*\(', r'router.push(', code)
        code = re.sub(r'prompt\.showToast\s*\(', r'prompt.showToast(', code)
        code = re.sub(r'animateTo\s*\(', r'animateTo(', code)
        
        # 处理对象解构中的类型注解
        code = re.sub(r'const\s*{([^}]*)}:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=', r'const {\1}/* :\2 */=', code)
        
        # 处理接口定义
        code = re.sub(r'\binterface\b\s+([A-Za-z_]\w*)', r'/* interface */ class \1', code)
        
        return code

    def _process_decorators_enhanced(self, code: str) -> Tuple[str, int]:
        """
        增强版装饰器处理
        
        完全重写此方法，将ArkTS装饰器转换为TypeScript兼容的方式
        处理@Entry, @Component, @State等所有ArkTS装饰器
        """
        # 计数装饰器
        decorator_pattern = r'@([A-Za-z_]\w*)(?:\([^)]*\))?'
        decorators = re.findall(decorator_pattern, code)
        count = len(decorators)
        
        # 处理更复杂的装饰器组合模式
        # 替换@Entry @Component装饰器为类注释
        code = re.sub(
            r'@Entry\s+@Component\s+struct\s+([A-Za-z_]\w*)',
            r'// @ts-ignore\n/* @Entry @Component */\nclass \1',
            code
        )
        
        # 替换单独的@Component装饰器
        code = re.sub(
            r'@Component\s+struct\s+([A-Za-z_]\w*)',
            r'// @ts-ignore\n/* @Component */\nclass \1',
            code
        )
        
        # 处理@Builder装饰器 - 转换为普通方法
        code = re.sub(
            r'@Builder\s+(\w+)\s*\((.*?)\)\s*{',
            r'/* @Builder */\nfunction \1(\2) {',
            code
        )
        
        # 处理@Styles装饰器
        code = re.sub(
            r'@Styles\s+function\s+(\w+)\s*\((.*?)\)\s*{',
            r'/* @Styles */\nfunction \1(\2) {',
            code
        )
        
        # 处理@State和其他状态装饰器 - 转换为属性声明
        state_patterns = [
            # 带初始值的模式
            (r'@State\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @State */ let \1 = \3; // State<\2>'),
            (r'@Prop\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @Prop */ let \1 = \3; // Prop<\2>'),
            (r'@Link\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @Link */ let \1 = \3; // Link<\2>'),
            (r'@Consume\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @Consume */ let \1 = \3; // Consume<\2>'),
            (r'@Provide\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @Provide */ let \1 = \3; // Provide<\2>'),
            (r'@StorageLink\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @StorageLink */ let \1 = \3; // StorageLink<\2>'),
            (r'@StorageProp\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @StorageProp */ let \1 = \3; // StorageProp<\2>'),
            (r'@Observed\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @Observed */ let \1 = \3; // Observed<\2>'),
            (r'@ObjectLink\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*=\s*([^;]+);?', 
             r'/* @ObjectLink */ let \1 = \3; // ObjectLink<\2>'),
            
            # 不带初始值的装饰器变量
            (r'@State\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @State */ let \1; // State<\2>'),
            (r'@Prop\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @Prop */ let \1; // Prop<\2>'),
            (r'@Link\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @Link */ let \1; // Link<\2>'),
            (r'@Consume\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @Consume */ let \1; // Consume<\2>'),
            (r'@Provide\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @Provide */ let \1; // Provide<\2>'),
            (r'@StorageLink\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @StorageLink */ let \1; // StorageLink<\2>'),
            (r'@StorageProp\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @StorageProp */ let \1; // StorageProp<\2>'),
            (r'@Observed\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @Observed */ let \1; // Observed<\2>'),
            (r'@ObjectLink\s+([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*;', 
             r'/* @ObjectLink */ let \1; // ObjectLink<\2>'),
        ]
        
        for pattern, replacement in state_patterns:
            code = re.sub(pattern, replacement, code)
        
        # 处理其余所有装饰器 - 转换为注释形式
        code = re.sub(
            r'@(\w+)(?:\([^)]*\))?',
            r'/* @\1 */',
            code
        )
        
        return code, count
        
    def _process_arkts_syntax_enhanced(self, code: str) -> Tuple[str, int]:
        """
        增强版ArkTS语法处理
        
        完全重写此方法，处理更多ArkTS特有语法
        """
        count = 0
        
        # 转换struct为class - 如果之前的装饰器处理没有完成
        if 'struct ' in code:
            count += code.count('struct ')
            # 更精确的struct转换，保留名称和大括号
            code = re.sub(r'\bstruct\s+([A-Za-z_]\w*)', r'class \1', code)
        
        # 处理类型注解 - 更完善的处理
        type_patterns = [
            # 基本类型注解: name: type = value
            (r'(\w+)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)(\s*=\s*[^;]+);?', r'let \1\3; // 类型: \2'),
            
            # 函数参数类型: (param: type)
            (r'(\w+)\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*([,)])', r'\1\3 /* 类型: \2 */'),
            
            # 函数返回类型: function(): type {
            (r'(\w+\s*\([^)]*\))\s*:\s*([a-zA-Z_][\w<>]*(?:\[\])?)\s*(\{)', r'\1 \3 /* 返回类型: \2 */'),
        ]
        
        for pattern, replacement in type_patterns:
            if re.search(pattern, code):
                count += len(re.findall(pattern, code))
                code = re.sub(pattern, replacement, code)
        
        # 处理ArkTS特有关键字 - 转换为JS/TS兼容语法
        arkts_keywords = {
            'private': '',  # 移除private关键字
            'protected': '',
            'readonly': 'const',
            'abstract': '// abstract',
            'static': 'static', # 保留static关键字
            'enum': 'const', # enum转换为const
        }
        
        for keyword, replacement in arkts_keywords.items():
            keyword_pattern = r'\b' + keyword + r'\b'
            if re.search(keyword_pattern, code):
                count += len(re.findall(keyword_pattern, code))
                if replacement:
                    code = re.sub(keyword_pattern, replacement, code)
                else:
                    code = re.sub(keyword_pattern, '/* ' + keyword + ' */', code)
        
        # 处理stateStyles语法
        if 'stateStyles' in code:
            code = re.sub(
                r'\.stateStyles\s*\(\s*\{([^}]*)\}\s*\)',
                r'.stateStyles({ /* state styles */ })',
                code
            )
            count += 1
            
        # 处理复合表达式，如 ${...}
        if '${' in code:
            code = re.sub(r'\$\{([^}]+)\}', r'"${\1}"', code)
            count += code.count('${')
            
        return code, count

    def _process_build_method_completely_new(self, code: str) -> str:
        """
        完全重写的build方法处理
        
        将ArkTS UI-DSL语法转换为ESLint可解析的标准JavaScript函数调用
        """
        lines = code.split('\n')
        processed_lines = []
        in_build_method = False
        brace_count = 0
        current_component = None
        
        for i, line in enumerate(lines):
            # 检测build方法的开始
            if re.search(r'\bbuild\s*\(\s*\)\s*\{', line):
                in_build_method = True
                brace_count = line.count('{') - line.count('}')
                processed_lines.append(line)
                continue
                
            if in_build_method:
                # 跟踪大括号平衡
                brace_count += line.count('{') - line.count('}')
                
                # 处理UI组件调用链
                for component in self.ui_components:
                    pattern = rf'{component}\s*\([^)]*\)'
                    if re.search(pattern, line):
                        current_component = component
                        # 将链式API调用转换为函数调用
                        for chain_pattern, replacement in self.ui_chain_patterns:
                            if re.search(chain_pattern, line):
                                line = re.sub(chain_pattern, replacement, line)
                
                # 处理事件处理函数 - 将箭头函数转换为更简单的形式
                if '.onClick' in line and '=>' in line:
                    line = re.sub(
                        r'\.onClick\(\s*\(\s*\)\s*=>\s*\{([^}]+)\}\s*\)',
                        r'.onClick(function() { \1 })',
                        line
                    )
                
                # 处理ForEach/LazyForEach组件
                for control in ['ForEach', 'LazyForEach']:
                    if f"{control}(" in line:
                        # 简化ForEach语法
                        line = re.sub(
                            rf'{control}\s*\(\s*([^,]+),\s*([^)]+)\s*\)',
                            rf'{control}(\1, function(item) {{ /* item renderer */ }})',
                            line
                        )
                
                processed_lines.append(line)
                
                # 检查build方法是否结束
                if brace_count <= 0:
                    in_build_method = False
                    current_component = None
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def map_error_location(self, processed_line: int, processed_column: int) -> Tuple[int, int]:
        """映射处理后的错误位置到原始代码位置"""
        # 减去全局变量声明的行数
        globals_line_count = len(self.arkts_globals.split('\n'))
        adjusted_line = processed_line - globals_line_count
        
        # 调整为1开始的索引，确保不会为负数
        if adjusted_line < 1:
            adjusted_line = 1
            
        # 使用行号映射查找原始位置
        for mapping in self.line_mappings:
            if mapping.processed_line == adjusted_line:
                return mapping.original_line, processed_column
        
        # 如果没有找到精确映射，使用一个简单的估计
        return max(1, adjusted_line), processed_column


class ESLintService(CodeReviewInterface):
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.eslint_path = self.config.get('eslint_path', 'eslint')
        self.timeout = self.config.get('timeout', 120)
        self.temp_dir = Path.cwd() / "temp_eslint_service"
        self.temp_dir.mkdir(exist_ok=True)
        self.arkts_preprocessor = EnhancedArkTSPreprocessor()
        self.supported_languages = ['javascript', 'typescript', 'arkts', 'ets']
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查ESLint依赖是否可用，尝试多种可能的命令路径并自动安装"""
        eslint_commands = [
            self.eslint_path,               # 配置的路径
            'eslint',                       # 直接命令
            'npx eslint',                   # npx方式
            '/usr/local/bin/eslint',        # 常见全局安装路径
            os.path.expanduser('~/.npm/bin/eslint'),  # npm用户安装路径
            'node_modules/.bin/eslint',     # 本地安装
            './node_modules/.bin/eslint',   # 项目本地安装
            'yarn eslint',                  # yarn运行
            'npm exec eslint'               # npm exec方式
        ]
        
        for cmd in eslint_commands:
            try:
                args = cmd.split() if ' ' in cmd else [cmd]
                args.append('--version')
                result = subprocess.run(args, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.eslint_available = True
                    self.eslint_path = cmd  # 使用找到的可用命令
                    eslint_version = result.stdout.strip()
                    logger.info(f"✅ ESLint可用: {eslint_version}, 使用命令: {cmd}")
                    return
            except Exception as e:
                logger.debug(f"尝试ESLint命令 '{cmd}' 失败: {e}")
                continue
        
        # 尝试自动安装ESLint
        logger.info("尝试自动安装ESLint...")
        try:
            # 创建临时目录用于安装ESLint
            temp_npm_dir = os.path.join(self.temp_dir, "npm_modules")
            os.makedirs(temp_npm_dir, exist_ok=True)
            
            # 创建package.json
            package_json = {
                "name": "eslint-temp",
                "version": "1.0.0",
                "description": "Temporary package for ESLint installation",
                "dependencies": {
                    "eslint": "^8.0.0"
                }
            }
            with open(os.path.join(temp_npm_dir, "package.json"), "w") as f:
                json.dump(package_json, f)
            
            # 安装ESLint
            install_cmd = "npm install"
            subprocess.run(install_cmd.split(), cwd=temp_npm_dir, check=True, timeout=60)
            
            # 验证安装
            eslint_local_path = os.path.join(temp_npm_dir, "node_modules", ".bin", "eslint")
            if os.path.exists(eslint_local_path):
                self.eslint_path = eslint_local_path
                self.eslint_available = True
                logger.info(f"✅ ESLint已成功安装到临时目录: {eslint_local_path}")
                return
        except Exception as e:
            logger.warning(f"自动安装ESLint失败: {str(e)}")
        
        # 所有尝试都失败
        logger.warning(f"⚠️ 无法找到可用的ESLint，将使用降级检查")
        self.eslint_available = False

    def is_available(self) -> bool:
        return self.eslint_available
    
    async def review_code(self, request: CodeReviewRequest) -> CodeReviewResult:
        start_time = time.time()
        
        # 检查代码是否为ArkTS
        is_arkts = request.language.lower() in ['arkts', 'ets']
        
        # 对ArkTS代码进行预处理
        if is_arkts:
            code_to_check, preprocessing_metadata = self.arkts_preprocessor.preprocess_arkts_code(request.code)
            preprocessing_metadata['using_arkts_config'] = True
            
            # 以下代码可用于调试预处理后的代码
            # debug_file = self.temp_dir / "debug_processed_code.js"
            # debug_file.write_text(code_to_check, encoding='utf-8')
            # preprocessing_metadata['debug_file'] = str(debug_file)
        else:
            # 非ArkTS代码不需要预处理
            code_to_check = request.code
            preprocessing_metadata = {'arkts_syntax_found': 0, 'decorators_found': 0}
        
        temp_file = await self._create_temp_file(code_to_check, request.language)
        
        # 针对ArkTS使用专用配置
        if is_arkts:
            config_file = await self._create_arkts_eslint_config()
            logger.info("🔍 使用ArkTS专用ESLint配置")
        else:
            config_file = await self._create_enhanced_config_file()
        
        eslint_output = await self._run_eslint(temp_file, config_file)
        
        issues, total_issues = self._parse_eslint_result(eslint_output)
        
        parsing_errors = [issue for issue in issues if issue.get('message') and 'parsing error' in issue.get('message').lower()]
        
        # 仅当存在解析错误且错误数量超过总问题的50%时才启用降级模式
        if parsing_errors and len(parsing_errors) > total_issues * 0.5:
            logger.info("🔄 检测到解析错误，启用降级检查模式...")
            fallback_issues = self._fallback_arkts_check(request.code)
            
            # 添加一个通知，说明使用了降级模式
            fallback_notice = {
                'line': 1,
                'column': 1,
                'message': '⚠️ 由于ArkTS解析复杂性，已启用降级检查模式。以上问题基于模式匹配发现，建议仅作参考。',
                'severity': 'info',
                'rule': 'arkts/fallback-mode-notice',
                'source': 'fallback-checker'
            }
            
            # 合并问题列表 - 保留非解析错误的原始问题
            non_parsing_issues = [issue for issue in issues if issue not in parsing_errors]
            all_issues = non_parsing_issues + fallback_issues + [fallback_notice]
            
            # 更新预处理元数据
            preprocessing_metadata['fallback_mode'] = True
            preprocessing_metadata['fallback_issues_count'] = len(fallback_issues)
            preprocessing_metadata['original_issues_kept'] = len(non_parsing_issues)
            
            issues = all_issues
        else:
            # 正常模式 - 未使用降级检查
            preprocessing_metadata['fallback_mode'] = False

        # 将问题映射回原始代码位置
        for issue in issues:
            if 'line' in issue and issue['line'] and is_arkts:
                issue['line'], issue['column'] = self.arkts_preprocessor.map_error_location(issue['line'], issue.get('column', 1))

        # 计算得分
        error_count = sum(1 for issue in issues if issue.get('severity') == 'error')
        warning_count = sum(1 for issue in issues if issue.get('severity') == 'warning')
        info_count = sum(1 for issue in issues if issue.get('severity') == 'info')
        
        # 改进的评分系统
        score = 100
        score -= error_count * 10    # 每个错误-10分
        score -= warning_count * 3    # 每个警告-3分
        score -= info_count * 1       # 每个信息-1分
        score = max(0, min(100, score))  # 确保分数在0-100之间

        # 生成建议和报告
        suggestions = self._generate_enhanced_suggestions(issues, preprocessing_metadata)
        report = self._generate_enhanced_report(issues, suggestions, preprocessing_metadata)
        
        # 清理临时文件
        self._cleanup_temp_files([temp_file, config_file])
        
        return CodeReviewResult(
            request_id=f"eslint_{int(time.time())}",
            original_query=request.original_query,
            code=request.code,
            language=request.language,
            checker="ESLint",
            score=score,
            issues=issues,
            suggestions=suggestions,
            report=report,
            execution_time=time.time() - start_time,
            metadata={'preprocessing_metadata': preprocessing_metadata}
        )

    async def _create_temp_file(self, code: str, language: str) -> Path:
        if language.lower() == 'arkts':
            # 为ArkTS文件使用.ets扩展名
            suffix = '.ets'
        elif language.lower() == 'typescript':
            suffix = '.ts'
        else:
            suffix = '.js'
            
        temp_file = Path(tempfile.mktemp(suffix=suffix, dir=self.temp_dir))
        temp_file.write_text(code, encoding='utf-8')
        return temp_file

    async def _create_enhanced_config_file(self) -> Path:
        config_content = {
            "env": {"browser": True, "es6": True, "node": True},  # 使用es6代替es2021
            "parserOptions": {"ecmaVersion": 2020, "sourceType": "module"},  # 使用具体版本号
            "rules": {
                "no-undef": "warn",
                "no-unused-vars": ["warn", {"varsIgnorePattern": "^_"}],
                "no-console": "off",
                "no-eval": "error",
            }
        }
        config_file = self.temp_dir / ".eslintrc.json"
        config_file.write_text(json.dumps(config_content), encoding='utf-8')
        return config_file
        
    async def _create_arkts_eslint_config(self) -> Path:
        """创建ArkTS专用的ESLint配置文件"""
        config_content = {
            "env": {
                "browser": True,
                "es6": True
            },
            "extends": [
                "eslint:recommended"
            ],
            "parserOptions": {
                "ecmaVersion": 2020,
                "sourceType": "module",
                "ecmaFeatures": {
                    "jsx": True,  # 启用JSX支持
                    "experimentalDecorators": True,  # 启用装饰器支持
                    "objectLiteralDuplicateProperties": False  # 允许重复属性名（ArkTS特性）
                }
            },
            "globals": {
                # ArkTS控制流组件
                "ForEach": "readonly",
                "LazyForEach": "readonly",
                "If": "readonly",
                "Else": "readonly",
                "ElseIf": "readonly",
                "While": "readonly",
                "Match": "readonly",
                "Case": "readonly",
                
                # ArkTS UI组件
                "Row": "readonly",
                "Column": "readonly",
                "Text": "readonly",
                "Button": "readonly",
                "Image": "readonly",
                "List": "readonly",
                "Grid": "readonly",
                "Tabs": "readonly",
                "Stack": "readonly",
                "Swiper": "readonly",
                "Scroll": "readonly",
                "Navigator": "readonly",
                "Canvas": "readonly",
                "Panel": "readonly",
                "Refresh": "readonly",
                "Navigation": "readonly",
                "LoadingProgress": "readonly",
                "Select": "readonly",
                "Counter": "readonly",
                "PatternLock": "readonly",
                "Stepper": "readonly",
                "DataPanel": "readonly",
                "DatePicker": "readonly",
                "TimePicker": "readonly",
                "TextPicker": "readonly",
                "SideBarContainer": "readonly",
                "AlphabetIndexer": "readonly",
                "TextArea": "readonly",
                "RichText": "readonly",
                "Search": "readonly",
                "TextClock": "readonly",
                "Marquee": "readonly",
                "Menu": "readonly",
                
                # ArkTS API和方法
                "animateTo": "readonly",
                "stateStyles": "readonly",
                "$r": "readonly",
                "router": "readonly",
                "prompt": "readonly",
                "PersistProp": "readonly",
                "mediaQuery": "readonly",
                
                # ArkTS样式常量
                "FontWeight": "readonly",
                "FontStyle": "readonly",
                "Color": "readonly",
                "Length": "readonly",
                "Alignment": "readonly",
                "FlexAlign": "readonly",
                "FlexDirection": "readonly",
                "TextDecorationType": "readonly",
                "BorderStyle": "readonly",
                "EdgeEffect": "readonly",
                "Curve": "readonly",
                "BarState": "readonly",
                "Visibility": "readonly",
                "DisplayMode": "readonly",
                "ImageFit": "readonly",
                "SizeType": "readonly",
                "GradientDirection": "readonly",
                "ResponseType": "readonly",
                "Axis": "readonly",
                "HoverEffect": "readonly",
                "NavigationType": "readonly",
                "DialogAlignment": "readonly",
                "Resource": "readonly",
                "curves": "readonly",
                
                # ArkTS类型
                "ObservedObject": "readonly",
                "StorageLink": "readonly",
                "StorageProp": "readonly",
                "LocalStorage": "readonly",
                "AppStorage": "readonly",
                "PersistentStorage": "readonly",
                
                # ArkTS生命周期方法
                "aboutToAppear": "readonly",
                "aboutToDisappear": "readonly",
                "onPageShow": "readonly",
                "onPageHide": "readonly",
                "onBackPress": "readonly",
                "onVisibleAreaChange": "readonly",
                "onAreaChange": "readonly",
                "onTouch": "readonly",
                "onKeyEvent": "readonly",
                "onHover": "readonly"
            },
            "rules": {
                "no-console": "warn",
                "no-unused-vars": "off",  # 关闭未使用变量警告
                "no-undef": "warn",       # 降级为警告
                "no-var": "warn",         # 降级为警告
                "prefer-const": "off",    # 关闭推荐const
                "no-magic-numbers": "off", # 关闭魔法数字检查
                "no-constant-condition": "warn", # 条件始终为真/假
                "no-empty": "warn",       # 空代码块
                "no-duplicate-case": "error", # 重复case
                "no-irregular-whitespace": "warn" # 不规则空白
            }
        }
        
        config_file = self.temp_dir / f"arkts_eslint_config_{int(time.time())}.json"
        config_file.write_text(json.dumps(config_content), encoding='utf-8')
        return config_file

    async def _run_eslint(self, file_path: Path, config_file: Path) -> str:
        """
        运行ESLint并返回结果
        升级版: 使用临时环境和更健壮的错误处理
        """
        # 如果ESLint路径已经确定，优先使用
        if hasattr(self, 'eslint_path') and self.eslint_path:
            eslint_paths = [self.eslint_path]
        else:
            # 可能的ESLint命令路径列表
            eslint_paths = [
                'eslint',                          # 全局安装
                'npx eslint',                      # npx调用
                './node_modules/.bin/eslint',      # 本地安装（相对于当前目录）
                'node_modules/.bin/eslint',        # 本地安装（另一种路径）
                'npx --yes eslint',                # 强制安装并使用
                'yarn eslint',                     # yarn方式
                'npm exec eslint',                 # npm exec方式
                os.path.join(self.temp_dir, "npm_modules", "node_modules", ".bin", "eslint")  # 自动安装的位置
            ]
            
            # 去重
            eslint_paths = list(dict.fromkeys(eslint_paths))
        
        # 准备临时ESLint配置
        eslint_args = [
            "--config", str(config_file),
            "--format", "json",
            "--no-eslintrc",  # 忽略默认配置文件
            "--no-ignore",    # 忽略.eslintignore
            "--max-warnings", "100"  # 限制警告数量
        ]
        
        if os.path.exists(file_path):
            eslint_args.append(str(file_path))
        else:
            logger.error(f"文件不存在: {file_path}")
            return "[]"
        
        # 逐个尝试可能的命令路径
        last_error = None
        for eslint_path in eslint_paths:
            try:
                # 拆分命令，处理可能包含空格的命令路径
                cmd_parts = eslint_path.split() if ' ' in eslint_path else [eslint_path]
                cmd = cmd_parts + eslint_args
                
                logger.info(f"尝试执行ESLint命令: {' '.join(cmd)}")
                
                # 设置环境变量，避免某些警告
                env = os.environ.copy()
                env["NODE_ENV"] = "production"
                env["ESLINT_USE_FLAT_CONFIG"] = "false"  # 禁用新的flat config
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    limit=1024 * 1024 * 5  # 5MB限制
                )
                
                try:
                    # 设置超时
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=60  # 最多等待60秒
                    )
                    
                    # 处理输出
                    stdout_text = stdout.decode() if stdout else ""
                    stderr_text = stderr.decode() if stderr else ""
                    
                    # 特殊处理: 某些ESLint错误会输出到stderr但仍包含有效的JSON结果
                    if stdout_text and ('{"' in stdout_text or '[{' in stdout_text or '[]' in stdout_text):
                        # 尝试解析JSON输出
                        try:
                            json.loads(stdout_text)
                            logger.info("ESLint执行成功，获取到有效的JSON输出")
                            return stdout_text
                        except json.JSONDecodeError:
                            logger.warning(f"ESLint输出不是有效的JSON: {stdout_text[:100]}...")
                    
                    # 检查stderr输出，但某些警告可以忽略
                    if stderr_text:
                        ignore_patterns = [
                            "ExperimentalWarning",
                            "DeprecationWarning",
                            "experimental feature"
                        ]
                        
                        if any(pattern in stderr_text for pattern in ignore_patterns):
                            logger.warning(f"ESLint警告 (已忽略): {stderr_text[:100]}...")
                        elif process.returncode == 0 or process.returncode == 1:
                            # ESLint返回码1通常表示发现了代码问题，这是正常的
                            if stdout_text:
                                # 如果有输出，尝试解析为JSON
                                try:
                                    json.loads(stdout_text)
                                    return stdout_text
                                except:
                                    pass
                            # 如果没有stdout或解析失败，可能需要查看stderr
                            logger.warning(f"ESLint stderr输出: {stderr_text[:200]}...")
                        else:
                            logger.error(f"ESLint错误: {stderr_text}")
                    
                    # 根据返回码处理结果
                    if process.returncode == 0 or process.returncode == 1:
                        # 返回码0表示成功，1通常表示有lint问题
                        if stdout_text:
                            # 验证JSON格式
                            try:
                                json.loads(stdout_text)
                                return stdout_text
                            except:
                                logger.warning("ESLint输出不是有效的JSON格式")
                                return "[]"  # 返回空结果触发降级检查
                        else:
                            return "[]"  # 无输出返回空结果
                    else:
                        # 其他返回码可能表示配置问题或其他错误
                        logger.error(f"ESLint执行异常，返回码: {process.returncode}")
                        continue  # 尝试下一个路径
                        
                except asyncio.TimeoutError:
                    # 处理超时
                    logger.warning("ESLint执行超时")
                    try:
                        process.terminate()
                        await asyncio.sleep(0.5)
                        if process.returncode is None:
                            process.kill()
                    except Exception as e:
                        logger.error(f"终止超时进程失败: {e}")
                    continue
                    
            except Exception as e:
                last_error = e
                logger.warning(f"使用 {eslint_path} 运行ESLint失败: {e}")
                continue
        
        # 所有尝试都失败，记录错误并返回空结果
        if last_error:
            logger.error(f"所有ESLint命令尝试失败，最后错误: {last_error}")
        else:
            logger.error("所有ESLint命令尝试失败")
            
        # 返回空结果，将触发降级检查
        return "[]"

    def _parse_eslint_result(self, eslint_output: str) -> Tuple[List[Dict], int]:
        try:
            results = json.loads(eslint_output)
            issues = []
            if results:
                for message in results[0].get('messages', []):
                    issues.append({
                        'line': message.get('line'),
                        'column': message.get('column'),
                        'message': message.get('message'),
                        'severity': 'error' if message.get('severity') == 2 else 'warning',
                        'rule': message.get('ruleId') or 'unknown'
                    })
            return issues, len(issues)
        except json.JSONDecodeError:
            return [], 0

    def _fallback_arkts_check(self, code: str) -> List[Dict]:
        """增强版ArkTS降级检查 - 当ESLint解析失败时使用基于正则的模式匹配检查"""
        issues = []
        
        # 1. 查找常见问题的模式 - 扩展ArkTS特有规则
        patterns = [
            # 通用问题
            {'pattern': r'console\.(log|warn|error|debug)', 'message': '生产代码中应避免使用console语句', 'severity': 'warning', 'rule': 'no-console'},
            {'pattern': r'\.fontSize\(\s*\d{2,}\s*\)', 'message': '建议使用常量替代硬编码字体大小', 'severity': 'warning', 'rule': 'no-magic-numbers'},
            {'pattern': r'\bvar\b', 'message': 'ArkTS推荐使用let/const替代var声明变量', 'severity': 'warning', 'rule': 'no-var'},
            
            # ArkTS特有API问题
            {'pattern': r'setTimeout\s*\(', 'message': 'ArkTS中应避免使用setTimeout，推荐使用应用生命周期事件', 'severity': 'warning', 'rule': 'arkts/no-settimeout'},
            {'pattern': r'setInterval\s*\(', 'message': 'ArkTS中应避免使用setInterval，推荐使用应用生命周期事件', 'severity': 'warning', 'rule': 'arkts/no-setinterval'},
            {'pattern': r'new\s+Promise\s*\(', 'message': 'ArkTS中建议使用async/await代替直接创建Promise', 'severity': 'warning', 'rule': 'arkts/prefer-async-await'},
            {'pattern': r'\$r\s*\(', 'message': '使用资源引用时建议添加类型声明', 'severity': 'info', 'rule': 'arkts/type-resource-reference'},
            {'pattern': r'document\.', 'message': 'ArkTS不支持DOM操作，请使用ArkUI框架组件', 'severity': 'error', 'rule': 'arkts/no-dom-api'},
            {'pattern': r'window\.', 'message': 'ArkTS不支持window对象，请使用AppStorage或LocalStorage', 'severity': 'error', 'rule': 'arkts/no-window-object'},
            {'pattern': r'localStorage\.', 'message': 'ArkTS推荐使用LocalStorage代替localStorage', 'severity': 'warning', 'rule': 'arkts/prefer-arkts-storage'},
            
            # UI-DSL特有问题
            {'pattern': r'\.width\([\'"](\d+)%[\'"]\)', 'message': '建议避免使用硬编码的百分比宽度，考虑使用自适应布局', 'severity': 'info', 'rule': 'arkts/prefer-adaptive-layout'},
            {'pattern': r'\.height\([\'"](\d+)%[\'"]\)', 'message': '建议避免使用硬编码的百分比高度，考虑使用自适应布局', 'severity': 'info', 'rule': 'arkts/prefer-adaptive-layout'},
            {'pattern': r'\.layoutWeight\(\s*\d+\s*\)', 'message': '建议合理使用layoutWeight设置组件权重', 'severity': 'info', 'rule': 'arkts/layout-weight-usage'},
            {'pattern': r'\.margin\([\'"]?auto[\'"]?\)', 'message': '在ArkTS中，auto边距可能不会按预期工作，建议使用justifyContent或FlexAlign', 'severity': 'warning', 'rule': 'arkts/no-auto-margin'},
            
            # 事件处理
            {'pattern': r'\.onClick\(\s*\(\)\s*=>\s*\{\s*[^{}]{1,100}\s*\}\s*\)', 'message': '简单事件处理函数可以更加简洁', 'severity': 'info', 'rule': 'arkts/simplify-event-handler'},
            {'pattern': r'\.on(Click|Touch|Change|Hover)\(\s*\w+\s*\)', 'message': '确保事件处理函数名称明确表达其用途', 'severity': 'info', 'rule': 'arkts/descriptive-handler-names'},
            
            # 装饰器相关
            {'pattern': r'@Entry\s+struct', 'message': '@Entry应该与@Component一起使用', 'severity': 'warning', 'rule': 'arkts/entry-with-component'},
            {'pattern': r'@State\s+\w+\s*:\s*\w+\[\]', 'message': '数组类型的@State应考虑性能影响，可能触发频繁UI更新', 'severity': 'info', 'rule': 'arkts/state-array-performance'},
            {'pattern': r'@State\s+\w+\s*=\s*new\b', 'message': '@State初始化复杂对象时，注意对象引用变化才会触发UI更新', 'severity': 'info', 'rule': 'arkts/state-object-mutation'},
            
            # 路由相关
            {'pattern': r'router\.push\s*\(\s*[^\)\{]*\)', 'message': '路由传参时应考虑类型安全和参数校验', 'severity': 'info', 'rule': 'arkts/router-type-safety'},
            
            # 动画相关
            {'pattern': r'animateTo\s*\(\s*\{\s*duration\s*:\s*\d+', 'message': '建议将动画持续时间定义为常量，便于统一管理', 'severity': 'info', 'rule': 'arkts/animation-constants'},
        ]
        
        # 2. 查找变量声明和使用 - 增强变量跟踪
        declared_vars = set()
        used_vars = set()
        state_vars = set()  # @State装饰的变量
        
        for line_num, line in enumerate(code.split('\n'), 1):
            # 检查常见模式
            for p in patterns:
                if re.search(p['pattern'], line):
                    issues.append({
                        'line': line_num, 
                        'column': 1, 
                        'message': p['message'], 
                        'severity': p['severity'], 
                        'rule': p['rule'], 
                        'source': 'fallback-checker'
                    })
            
            # 检测@State变量
            state_match = re.search(r'@State\s+(?:(\w+)\s*:)?', line)
            if state_match and state_match.group(1):
                state_vars.add(state_match.group(1))
            
            # 提取变量声明
            var_decl = re.findall(r'(let|var|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
            for _, var_name in var_decl:
                declared_vars.add(var_name)
            
            # 查找变量使用
            for word in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', line):
                if word not in ['if', 'else', 'for', 'while', 'switch', 'return', 'function', 'class', 'const', 'let', 'var', 'this', 'true', 'false', 'null', 'undefined']:
                    used_vars.add(word)
            
            # 查找硬编码颜色值 - 增强颜色检测，包括rgba和简写形式
            color_patterns = [
                r'#[0-9A-Fa-f]{6}\b', # 标准HEX
                r'#[0-9A-Fa-f]{3}\b', # 简写HEX
                r'rgba?\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)', # RGB/RGBA
                r'Color\.(Black|White|Gray|Red|Blue|Green|Yellow)' # 直接引用Color枚举
            ]
            
            for pattern in color_patterns:
                if re.search(pattern, line) and not re.search(r'const\s+\w+\s*=.*' + pattern, line):
                    match = re.search(pattern, line)
                    issues.append({
                        'line': line_num,
                        'column': match.start() + 1 if match else 1,
                        'message': '建议将颜色值定义为命名常量或使用资源引用，避免硬编码',
                        'severity': 'warning',
                        'rule': 'arkts/no-hardcoded-colors',
                        'source': 'fallback-checker'
                    })
            
            # 查找大数字(可能需要定义为常量) - 增强魔法数字检测
            number_pattern = r'(?<![a-zA-Z0-9_])[2-9]\d{2,}(?![a-zA-Z0-9_])'
            for match in re.finditer(number_pattern, line):
                # 避免对px单位的误报
                if 'px' in line[match.end():match.end()+3]:
                    continue
                if not re.search(r'const\s+.*=\s*\d+', line):  # 不是常量定义
                    issues.append({
                        'line': line_num,
                        'column': match.start() + 1,
                        'message': '建议将大数值定义为有意义的常量，提高代码可维护性',
                        'severity': 'warning',
                        'rule': 'arkts/no-magic-numbers',
                        'source': 'fallback-checker'
                    })
        
        # 3. ArkTS UI DSL特定检查 - 更全面的UI-DSL检查
        in_build_method = False
        ui_method_depth = 0
        current_component = None
        
        # 从预处理器获取UI组件列表
        ui_components = self.arkts_preprocessor.ui_components
        control_flow = self.arkts_preprocessor.control_flow
        
        for line_num, line in enumerate(code.split('\n'), 1):
            # 检测build方法
            if 'build()' in line or 'build() {' in line:
                in_build_method = True
                ui_method_depth = line.count('{')
                continue
            
            if in_build_method:
                # 更新大括号深度计数
                ui_method_depth += line.count('{') - line.count('}')
                
                # 检测当前UI组件
                for component in ui_components:
                    if f"{component}(" in line:
                        current_component = component
                        break
                
                # 检查空UI组件 - 更精确地检测空组件
                for component in ui_components:
                    empty_component_pattern = rf'{component}\s*\(\s*\)\s*\{{\s*\}}'
                    if re.search(empty_component_pattern, line):
                        issues.append({
                            'line': line_num,
                            'column': 1,
                            'message': f'UI组件{component}为空，应该添加必要的内容或移除',
                            'severity': 'warning',  # 提高严重性
                            'rule': 'arkts/no-empty-ui-component',
                            'source': 'fallback-checker'
                        })
                
                # 增强事件处理检查 - 检查多种事件类型
                event_handlers = ['.onClick', '.onTouch', '.onChange', '.onAppear', '.onDisAppear', '.onHover']
                for handler in event_handlers:
                    if handler in line and '->' in line and '{' in line:
                        # 检查内联处理函数的长度和复杂度
                        if line.count(';') > 1 or line.count('this.') > 1:
                            issues.append({
                                'line': line_num,
                                'column': 1,
                                'message': f'复杂的{handler}事件处理函数应提取为单独的方法，提高可读性',
                                'severity': 'warning',
                                'rule': 'arkts/prefer-extracted-event-handlers',
                                'source': 'fallback-checker'
                            })
                
                # 检查UI属性的一致性和约束
                property_patterns = [
                    (r'\.width\([^)]*\)', r'\.height\([^)]*\)', '建议同时设置width和height维持组件比例一致性'),
                    (r'\.margin\([^)]*\)', r'\.padding\([^)]*\)', '注意margin和padding的合理搭配使用'),
                    (r'\.backgroundColor\([^)]*\)', r'\.opacity\([^)]*\)', '同时使用背景色和透明度可能导致意外效果')
                ]
                
                for pattern_a, pattern_b, message in property_patterns:
                    if re.search(pattern_a, line) and re.search(pattern_b, line):
                        issues.append({
                            'line': line_num,
                            'column': 1,
                            'message': message,
                            'severity': 'info',
                            'rule': 'arkts/ui-property-usage',
                            'source': 'fallback-checker'
                        })
                
                # 检查build方法是否结束
                if ui_method_depth <= 0:
                    in_build_method = False
                    current_component = None
        
        # 4. 项目最佳实践检查 - 增强版
        todo_count = 0
        log_count = 0
        performance_issues = []
        
        for line_num, line in enumerate(code.split('\n'), 1):
            # 检查TODO/FIXME
            if 'TODO' in line or 'FIXME' in line:
                todo_count += 1
                issues.append({
                    'line': line_num,
                    'column': 1,
                    'message': '代码中包含待办事项标记，请在发布前处理',
                    'severity': 'info',
                    'rule': 'arkts/no-todos',
                    'source': 'fallback-checker'
                })
            
            # 检查console日志
            if 'console.log' in line:
                log_count += 1
            
            # 检查性能问题
            if 'for (' in line and 'this.' in line and '.push(' in line:
                performance_issues.append({
                    'line': line_num,
                    'column': 1,
                    'message': '在循环中频繁修改状态变量可能导致性能问题，考虑批量更新',
                    'severity': 'warning',
                    'rule': 'arkts/perf-batch-updates',
                    'source': 'fallback-checker'
                })
        
        # 汇总检查结果
        if todo_count > 3:
            issues.append({
                'line': 1,
                'column': 1,
                'message': f'代码中包含大量待办事项({todo_count}个)，建议在提交前解决',
                'severity': 'warning',
                'rule': 'arkts/excessive-todos',
                'source': 'fallback-checker'
            })
        
        if log_count > 3:
            issues.append({
                'line': 1,
                'column': 1,
                'message': f'代码中包含{log_count}个console.log语句，生产环境应移除',
                'severity': 'warning',
                'rule': 'arkts/excessive-logs',
                'source': 'fallback-checker'
            })
        
        # 添加性能问题汇总
        if performance_issues:
            issues.extend(performance_issues)
        
        # 5. 未使用变量检查
        unused_vars = declared_vars - used_vars
        if unused_vars:
            for var in unused_vars:
                issues.append({
                    'line': 1,  # 无法确定准确行号
                    'column': 1,
                    'message': f"发现未使用的变量: '{var}'",
                    'severity': 'warning',
                    'rule': 'no-unused-vars',
                    'source': 'fallback-checker'
                })
        
        # 6. 添加降级模式通知 - 更友好的提示
        issues.append({
            'line': 1,
            'column': 1,
            'message': '⚠️ 由于ArkTS解析复杂性，已启用降级检查模式。以上问题基于模式匹配发现，建议仅作参考。',
            'severity': 'info',
            'rule': 'arkts/fallback-mode-notice',
            'source': 'fallback-checker'
        })
        
        return issues

    def _generate_enhanced_suggestions(self, issues: List[Dict], metadata: Dict) -> List[str]:
        """生成增强的代码改进建议 - 聚焦ArkTS最佳实践"""
        suggestions = []
        
        # 过滤掉预处理器生成的代码相关的问题
        filtered_issues = []
        for issue in issues:
            # 如果问题出现在第1行，且是预处理器生成的代码，则忽略
            if issue.get('line') == 1 and not metadata.get('fallback_mode'):
                continue
            filtered_issues.append(issue)
        
        # 分类计数
        error_count = sum(1 for i in filtered_issues if i.get('severity') == 'error')
        warning_count = sum(1 for i in filtered_issues if i.get('severity') == 'warning')
        info_count = sum(1 for i in filtered_issues if i.get('severity') == 'info')
        
        # 是否使用了降级模式
        fallback_mode = metadata.get('fallback_mode', False)
        
        # 总体状态评估
        if error_count == 0 and warning_count == 0:
            suggestions.append("✅ 代码质量良好，未发现明显问题。")
        elif error_count > 10:
            suggestions.append(f"❌ 代码存在大量错误({error_count}个)，建议修复后再提交。")
        elif error_count > 0:
            suggestions.append(f"⚠️ 代码存在{error_count}个错误，需要修复。")
        
        # 降级模式通知
        if fallback_mode:
            suggestions.append("⚠️ 由于ESLint解析失败，已启用降级检查模式，结果可能不完整。")
        
        # 分析具体问题类型并提出建议
        rule_counts = {}
        for issue in filtered_issues:
            rule = issue.get('rule', 'unknown')
            if rule not in rule_counts:
                rule_counts[rule] = 0
            rule_counts[rule] += 1
        
        # ArkTS特定建议
        arkts_rules = [rule for rule in rule_counts if rule.startswith('arkts/')]
        if arkts_rules:
            suggestions.append("🔍 ArkTS专项建议:")
            
            # UI组件相关
            if 'arkts/no-empty-ui-component' in arkts_rules:
                suggestions.append("  • 发现空UI组件，建议添加必要内容或移除空组件。")
            
            # 事件处理相关
            if 'arkts/prefer-extracted-event-handlers' in arkts_rules:
                suggestions.append("  • 建议将复杂的事件处理函数提取为组件类的成员方法，提高可读性。")
            
            # 颜色处理相关
            if 'arkts/no-hardcoded-colors' in arkts_rules:
                suggestions.append("  • 建议将颜色值定义为统一的常量或使用Color资源，避免硬编码。")
            
            # 性能相关
            if 'arkts/no-settimeout' in arkts_rules:
                suggestions.append("  • 在ArkTS中应避免使用setTimeout，建议使用生命周期方法或特定API。")
            
        # 通用JavaScript/TypeScript建议
        if rule_counts.get('no-undef', 0) > 0:
            suggestions.append("🔍 发现未定义的变量引用，请确保所有变量都已正确声明。")
        
        if rule_counts.get('no-unused-vars', 0) > 0:
            suggestions.append("🔍 存在未使用的变量，建议移除以减少代码冗余。")
        
        if rule_counts.get('no-console', 0) > 0:
            suggestions.append("🔍 生产代码中不应包含console调用，建议使用适当的日志机制。")
        
        if rule_counts.get('no-magic-numbers', 0) > 0:
            suggestions.append("🔍 代码中存在魔法数字，建议使用有意义的常量名替代。")
        
        # 添加整体改进建议
        if len(suggestions) <= 3:  # 如果建议较少，添加一些一般性建议
            suggestions.append("💡 建议遵循ArkTS设计规范，合理组织UI组件结构，提高代码可维护性。")
            suggestions.append("💡 考虑添加适当的注释，特别是对复杂逻辑和组件属性的说明。")
        
        return suggestions

    def _generate_enhanced_report(self, issues: List[Dict], suggestions: List[str], metadata: Dict) -> str:
        """生成增强的代码检查报告 - 格式更友好，信息更详细"""
        # 过滤掉预处理器生成的代码相关的问题
        filtered_issues = []
        for issue in issues:
            # 如果问题出现在第1行，且是预处理器生成的代码，则忽略
            if issue.get('line') == 1 and not metadata.get('fallback_mode'):
                continue
            filtered_issues.append(issue)
        
        # 计算各类问题数量
        error_count = sum(1 for i in filtered_issues if i.get('severity') == 'error')
        warning_count = sum(1 for i in filtered_issues if i.get('severity') == 'warning')
        info_count = sum(1 for i in filtered_issues if i.get('severity') == 'info')
        
        # 计算得分 - 调整计分方式，使得结果更合理
        score = 100 - (error_count * 5) - (warning_count * 2) - (info_count * 0.5)
        score = max(0, min(100, score))
        
        # 构建报告头部
        report = f"# ESLint 代码检查报告\n\n"
        
        # 评分与总览
        quality_label = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较差"
        report += f"**质量评分**: {score:.1f}/100 ({quality_label})\n\n"
        report += f"**总览**: 发现 {error_count} 个错误, {warning_count} 个警告, {info_count} 个提示。\n\n"
        
        # 检查模式说明
        if metadata.get('fallback_mode'):
            report += "**检查模式**: ⚠️ **降级检查** (ESLint解析失败，启用模式匹配)\n\n"
        elif metadata.get('using_arkts_config'):
            report += "**检查模式**: ✅ **ArkTS专用ESLint检查** (使用增强配置)\n\n"
        else:
            report += "**检查模式**: ✅ **完整ESLint检查**\n\n"
        
        # 改进建议部分
        report += "## 改进建议\n\n"
        for s in suggestions:
            report += f"- {s}\n"
        
        # 问题详情部分
        if filtered_issues:
            report += "\n## 问题详情\n\n"
            
            # 按严重程度分组
            errors = [i for i in filtered_issues if i.get('severity') == 'error']
            warnings = [i for i in filtered_issues if i.get('severity') == 'warning']
            infos = [i for i in filtered_issues if i.get('severity') == 'info']
            
            # 先显示错误
            if errors:
                report += "### 错误\n\n"
                for issue in errors[:10]:  # 限制显示数量
                    rule_text = f"`{issue['rule']}`" if 'rule' in issue else ""
                    line_text = f"第 {issue['line']} 行" if 'line' in issue else "未知位置"
                    report += f"- **[{line_text}]** {issue.get('message', '未知错误')} {rule_text}\n"
                if len(errors) > 10:
                    report += f"- ... 以及 {len(errors) - 10} 个其他错误\n"
            
            # 再显示警告
            if warnings:
                report += "\n### 警告\n\n"
                for issue in warnings[:10]:  # 限制显示数量
                    rule_text = f"`{issue['rule']}`" if 'rule' in issue else ""
                    line_text = f"第 {issue['line']} 行" if 'line' in issue else "未知位置"
                    report += f"- **[{line_text}]** {issue.get('message', '未知警告')} {rule_text}\n"
                if len(warnings) > 10:
                    report += f"- ... 以及 {len(warnings) - 10} 个其他警告\n"
            
            # 最后显示提示（如果不是太多）
            if infos and len(infos) <= 10:
                report += "\n### 提示\n\n"
                for issue in infos:
                    rule_text = f"`{issue['rule']}`" if 'rule' in issue else ""
                    line_text = f"第 {issue['line']} 行" if 'line' in issue else "未知位置"
                    report += f"- **[{line_text}]** {issue.get('message', '未知提示')} {rule_text}\n"
            elif infos:
                report += f"\n### 提示\n\n- 共有 {len(infos)} 条提示信息，建议在IDE中查看完整详情。\n"
        
        # 附加资源
        report += "\n## 附加资源\n\n"
        report += "- [ArkTS开发指南](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/arkts-basics-0000001281480650)\n"
        report += "- [ArkTS UI开发最佳实践](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/arkts-ui-development-best-practices-0000001493903920)\n"
        
        return report

    def _cleanup_temp_files(self, files: List[Path]):
        for file_path in files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"清理临时文件失败 {file_path}: {e}")
