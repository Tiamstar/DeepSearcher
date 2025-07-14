#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HarmonyOS Code Templates
鸿蒙代码模板 - 提供标准的ArkTS代码模板
"""

from typing import Dict, Any, Optional

class HarmonyOSTemplates:
    """鸿蒙ArkTS代码模板管理器"""
    
    @staticmethod
    def get_page_template(page_name: str = "GeneratedPage", has_state: bool = True) -> str:
        """生成页面模板"""
        state_code = """
  @State message: string = 'Hello World';
  @State isLoading: boolean = false;""" if has_state else ""
        
        return f"""@Entry
@Component
struct {page_name} {{
{state_code}

  build() {{
    RelativeContainer() {{
      Text(this.message)
        .id('{page_name}Text')
        .fontSize($r('app.float.page_text_font_size'))
        .fontWeight(FontWeight.Bold)
        .alignRules({{
          center: {{ anchor: '__container__', align: VerticalAlign.Center }},
          middle: {{ anchor: '__container__', align: HorizontalAlign.Center }}
        }})
        .onClick(() => {{
          this.message = 'Welcome to {page_name}';
        }})
    }}
    .height('100%')
    .width('100%')
  }}
}}"""

    @staticmethod
    def get_component_template(component_name: str = "CustomComponent", has_props: bool = True) -> str:
        """生成组件模板"""
        props_code = """
  @Prop title: string = '';
  @Prop content: string = '';""" if has_props else ""
        
        props_usage = "this.title" if has_props else "'Custom Component'"
        
        return f"""@Component
export struct {component_name} {{
{props_code}

  build() {{
    Column() {{
      Text({props_usage})
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .margin({{ bottom: 8 }})
      
      Text(this.content)
        .fontSize(14)
        .fontColor('#666666')
    }}
    .padding(16)
    .backgroundColor('#FFFFFF')
    .borderRadius(8)
    .width('100%')
  }}
}}"""

    @staticmethod
    def get_service_template(service_name: str = "DataService") -> str:
        """生成服务模板"""
        return f"""/**
 * {service_name}
 * 数据服务类
 */
export class {service_name} {{
  private static instance: {service_name};
  
  private constructor() {{
    // 私有构造函数，实现单例模式
  }}
  
  /**
   * 获取服务实例
   */
  public static getInstance(): {service_name} {{
    if (!{service_name}.instance) {{
      {service_name}.instance = new {service_name}();
    }}
    return {service_name}.instance;
  }}
  
  /**
   * 获取数据
   */
  public async getData(): Promise<any> {{
    try {{
      // TODO: 实现数据获取逻辑
      return {{}};
    }} catch (error) {{
      console.error('{service_name} getData error:', error);
      throw error;
    }}
  }}
  
  /**
   * 保存数据
   */
  public async saveData(data: any): Promise<boolean> {{
    try {{
      // TODO: 实现数据保存逻辑
      console.log('{service_name} saving data:', data);
      return true;
    }} catch (error) {{
      console.error('{service_name} saveData error:', error);
      return false;
    }}
  }}
}}"""

    @staticmethod
    def get_model_template(model_name: str = "DataModel") -> str:
        """生成数据模型模板"""
        return f"""/**
 * {model_name}
 * 数据模型类
 */
export interface I{model_name} {{
  id: string;
  name: string;
  createTime: string;
  updateTime?: string;
}}

export class {model_name} implements I{model_name} {{
  id: string = '';
  name: string = '';
  createTime: string = '';
  updateTime?: string;
  
  constructor(data?: Partial<I{model_name}>) {{
    if (data) {{
      this.id = data.id || '';
      this.name = data.name || '';
      this.createTime = data.createTime || new Date().toISOString();
      this.updateTime = data.updateTime;
    }}
  }}
  
  /**
   * 转换为JSON对象
   */
  toJSON(): I{model_name} {{
    return {{
      id: this.id,
      name: this.name,
      createTime: this.createTime,
      updateTime: this.updateTime
    }};
  }}
  
  /**
   * 从JSON对象创建实例
   */
  static fromJSON(json: I{model_name}): {model_name} {{
    return new {model_name}(json);
  }}
  
  /**
   * 验证数据有效性
   */
  validate(): boolean {{
    return !!(this.id && this.name && this.createTime);
  }}
}}"""

    @staticmethod
    def get_util_template(util_name: str = "CommonUtil") -> str:
        """生成工具类模板"""
        return f"""/**
 * {util_name}
 * 通用工具类
 */
export class {util_name} {{
  
  /**
   * 格式化日期
   */
  static formatDate(date: Date | string, format: string = 'YYYY-MM-DD HH:mm:ss'): string {{
    const d = typeof date === 'string' ? new Date(date) : date;
    
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    
    return format
      .replace('YYYY', year.toString())
      .replace('MM', month)
      .replace('DD', day)
      .replace('HH', hours)
      .replace('mm', minutes)
      .replace('ss', seconds);
  }}
  
  /**
   * 生成UUID
   */
  static generateUUID(): string {{
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    }});
  }}
  
  /**
   * 防抖函数
   */
  static debounce<T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void {{
    let timeoutId: number;
    return (...args: Parameters<T>) => {{
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    }};
  }}
  
  /**
   * 节流函数
   */
  static throttle<T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void {{
    let lastCall = 0;
    return (...args: Parameters<T>) => {{
      const now = Date.now();
      if (now - lastCall >= delay) {{
        lastCall = now;
        func.apply(this, args);
      }}
    }};
  }}
  
  /**
   * 深拷贝对象
   */
  static deepClone<T>(obj: T): T {{
    if (obj === null || typeof obj !== 'object') {{
      return obj;
    }}
    
    if (obj instanceof Date) {{
      return new Date(obj.getTime()) as T;
    }}
    
    if (obj instanceof Array) {{
      return obj.map(item => {util_name}.deepClone(item)) as T;
    }}
    
    if (typeof obj === 'object') {{
      const cloned = {{}} as T;
      for (const key in obj) {{
        if (obj.hasOwnProperty(key)) {{
          cloned[key] = {util_name}.deepClone(obj[key]);
        }}
      }}
      return cloned;
    }}
    
    return obj;
  }}
}}"""

    @staticmethod
    def get_list_page_template(page_name: str = "ListPage", item_type: str = "DataItem") -> str:
        """生成列表页面模板"""
        return f"""@Entry
@Component
struct {page_name} {{
  @State dataList: {item_type}[] = [];
  @State isLoading: boolean = false;
  @State searchText: string = '';

  aboutToAppear() {{
    this.loadData();
  }}

  async loadData() {{
    this.isLoading = true;
    try {{
      // TODO: 加载数据逻辑
      // this.dataList = await DataService.getInstance().getData();
    }} catch (error) {{
      console.error('加载数据失败:', error);
    }} finally {{
      this.isLoading = false;
    }}
  }}

  build() {{
    Column() {{
      // 搜索框
      Row() {{
        TextInput({{ placeholder: '搜索...' }})
          .layoutWeight(1)
          .onChange((value: string) => {{
            this.searchText = value;
          }})
        
        Button('搜索')
          .margin({{ left: 8 }})
          .onClick(() => {{
            this.performSearch();
          }})
      }}
      .width('100%')
      .padding(16)
      
      // 列表内容
      if (this.isLoading) {{
        LoadingDialog()
      }} else {{
        List() {{
          ForEach(this.dataList, (item: {item_type}, index: number) => {{
            ListItem() {{
              {item_type}Card({{ item: item }})
            }}
            .onClick(() => {{
              this.onItemClick(item, index);
            }})
          }}, item => item.id)
        }}
        .width('100%')
        .layoutWeight(1)
      }}
    }}
    .height('100%')
    .width('100%')
    .backgroundColor('#F5F5F5')
  }}

  performSearch() {{
    // TODO: 实现搜索逻辑
    console.log('搜索:', this.searchText);
  }}

  onItemClick(item: {item_type}, index: number) {{
    // TODO: 处理点击事件
    console.log('点击项目:', item, index);
  }}
}}

@Component
struct {item_type}Card {{
  @Prop item: {item_type};

  build() {{
    Column() {{
      Text(this.item.name || '未知')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .margin({{ bottom: 4 }})
      
      Text(this.item.description || '')
        .fontSize(14)
        .fontColor('#666666')
    }}
    .alignItems(HorizontalAlign.Start)
    .padding(16)
    .backgroundColor('#FFFFFF')
    .borderRadius(8)
    .margin({{ horizontal: 16, vertical: 4 }})
    .width('100%')
  }}
}}

@Component
struct LoadingDialog {{
  build() {{
    Column() {{
      LoadingProgress()
        .width(50)
        .height(50)
      
      Text('加载中...')
        .fontSize(14)
        .margin({{ top: 16 }})
    }}
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .width('100%')
    .height('100%')
  }}
}}"""

    @staticmethod
    def get_template_by_type(template_type: str, **kwargs) -> str:
        """根据类型获取模板"""
        templates = {
            "harmonyos_page": HarmonyOSTemplates.get_page_template,
            "harmonyos_component": HarmonyOSTemplates.get_component_template,
            "harmonyos_service": HarmonyOSTemplates.get_service_template,
            "harmonyos_model": HarmonyOSTemplates.get_model_template,
            "harmonyos_util": HarmonyOSTemplates.get_util_template,
            "harmonyos_list_page": HarmonyOSTemplates.get_list_page_template,
        }
        
        template_func = templates.get(template_type)
        if template_func:
            return template_func(**kwargs)
        else:
            return f"// 未知模板类型: {template_type}"
    
    @staticmethod
    def get_available_templates() -> Dict[str, str]:
        """获取可用模板列表"""
        return {
            "harmonyos_page": "基础页面模板",
            "harmonyos_component": "自定义组件模板", 
            "harmonyos_service": "数据服务模板",
            "harmonyos_model": "数据模型模板",
            "harmonyos_util": "工具类模板",
            "harmonyos_list_page": "列表页面模板"
        }