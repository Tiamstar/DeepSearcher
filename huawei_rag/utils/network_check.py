#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络连接检查和诊断工具
专门解决华为RAG在线搜索的网络连接问题
"""

import logging
import time
import os
import sys
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse
import socket
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

logger = logging.getLogger(__name__)

class NetworkDiagnostics:
    """网络连接诊断工具"""
    
    def __init__(self):
        """初始化网络诊断工具"""
        self.test_urls = {
            'baidu': 'https://www.baidu.com',
            'google': 'https://www.google.com', 
            'brave_api': 'https://api.search.brave.com',
            'serper_api': 'https://google.serper.dev',
            'serpapi': 'https://serpapi.com',
            'google_api': 'https://www.googleapis.com',
            'firecrawl': 'https://api.firecrawl.dev'
        }
        
        self.proxy_configs = []
        self.session = None
        
    def check_basic_connectivity(self) -> Dict[str, any]:
        """检查基本网络连通性"""
        print("🌐 检查网络连接状态...")
        results = {}
        
        for name, url in self.test_urls.items():
            try:
                print(f"   - 测试连接: {url}")
                
                # 设置较短的超时时间
                response = requests.get(url, timeout=10, verify=True)
                
                if response.status_code == 200:
                    print(f"     ✅ 状态码: {response.status_code}")
                    results[name] = {
                        'status': 'success',
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                else:
                    print(f"     ⚠️ 状态码: {response.status_code}")
                    results[name] = {
                        'status': 'warning',
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                    
            except ConnectionError as e:
                print(f"     ❌ 连接失败: {str(e)[:100]}...")
                results[name] = {
                    'status': 'connection_error',
                    'error': str(e),
                    'error_type': 'ConnectionError'
                }
            except Timeout as e:
                print(f"     ⏰ 连接超时: {str(e)}")
                results[name] = {
                    'status': 'timeout',
                    'error': str(e),
                    'error_type': 'Timeout'
                }
            except Exception as e:
                print(f"     ❌ 其他错误: {str(e)}")
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                
        return results
    
    def check_dns_resolution(self) -> Dict[str, any]:
        """检查DNS解析"""
        print("\n🔍 检查DNS解析...")
        results = {}
        
        for name, url in self.test_urls.items():
            try:
                hostname = urlparse(url).hostname
                ip_address = socket.gethostbyname(hostname)
                print(f"   - {hostname} -> {ip_address} ✅")
                results[name] = {
                    'hostname': hostname,
                    'ip_address': ip_address,
                    'status': 'success'
                }
            except socket.gaierror as e:
                print(f"   - {hostname} -> DNS解析失败: {e} ❌")
                results[name] = {
                    'hostname': hostname,
                    'status': 'dns_error',
                    'error': str(e)
                }
            except Exception as e:
                print(f"   - {hostname} -> 错误: {e} ❌")
                results[name] = {
                    'hostname': hostname,
                    'status': 'error',
                    'error': str(e)
                }
                
        return results
    
    def check_proxy_settings(self) -> Dict[str, any]:
        """检查代理设置"""
        print("\n🔧 检查代理设置...")
        
        proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
        proxy_info = {}
        
        for var in proxy_vars:
            value = os.environ.get(var)
            if value:
                proxy_info[var] = value
                print(f"   - {var}: {value}")
        
        if not proxy_info:
            print("   - 未检测到代理设置")
            return {'status': 'no_proxy', 'proxies': {}}
        else:
            print(f"   - 检测到 {len(proxy_info)} 个代理设置")
            return {'status': 'proxy_detected', 'proxies': proxy_info}
    
    def test_with_different_configs(self) -> Dict[str, any]:
        """测试不同的网络配置"""
        print("\n🧪 测试不同网络配置...")
        
        configs = [
            {'name': '默认配置', 'proxies': None, 'verify': True},
            {'name': '禁用SSL验证', 'proxies': None, 'verify': False},
            {'name': '使用系统代理', 'proxies': {'http': None, 'https': None}, 'verify': True}
        ]
        
        # 如果检测到代理，添加无代理配置
        proxy_info = os.environ.get('http_proxy') or os.environ.get('https_proxy')
        if proxy_info:
            configs.append({'name': '绕过代理', 'proxies': {'http': '', 'https': ''}, 'verify': True})
        
        results = {}
        test_url = 'https://www.baidu.com'  # 使用国内可访问的网站测试
        
        for config in configs:
            print(f"\n   测试配置: {config['name']}")
            try:
                response = requests.get(
                    test_url,
                    proxies=config['proxies'],
                    verify=config['verify'],
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"     ✅ 成功 (状态码: {response.status_code})")
                    results[config['name']] = {
                        'status': 'success',
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                else:
                    print(f"     ⚠️ 部分成功 (状态码: {response.status_code})")
                    results[config['name']] = {
                        'status': 'partial_success',
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                print(f"     ❌ 失败: {str(e)[:50]}...")
                results[config['name']] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return results
    
    def diagnose_api_connectivity(self) -> Dict[str, any]:
        """诊断搜索引擎API连接问题"""
        print("\n🔍 诊断搜索引擎API连接...")
        
        # 检查API密钥配置
        api_keys = {
            'BRAVE_API_KEY': os.getenv('BRAVE_API_KEY'),
            'SERPER_API_KEY': os.getenv('SERPER_API_KEY'),
            'SERPAPI_KEY': os.getenv('SERPAPI_KEY'),
            'GOOGLE_SEARCH_API_KEY': os.getenv('GOOGLE_SEARCH_API_KEY'),
            'GOOGLE_CSE_ID': os.getenv('GOOGLE_CSE_ID'),
            'FIRECRAWL_API_KEY': os.getenv('FIRECRAWL_API_KEY')
        }
        
        print("   API密钥配置:")
        configured_apis = []
        for key, value in api_keys.items():
            if value:
                print(f"     ✅ {key}: 已配置 ({value[:8]}...)")
                configured_apis.append(key)
            else:
                print(f"     ❌ {key}: 未配置")
        
        # 测试已配置的API
        api_test_results = {}
        
        if api_keys['BRAVE_API_KEY']:
            api_test_results['brave'] = self._test_brave_api(api_keys['BRAVE_API_KEY'])
        
        if api_keys['SERPER_API_KEY']:
            api_test_results['serper'] = self._test_serper_api(api_keys['SERPER_API_KEY'])
            
        if api_keys['SERPAPI_KEY']:
            api_test_results['serpapi'] = self._test_serpapi(api_keys['SERPAPI_KEY'])
            
        if api_keys['GOOGLE_SEARCH_API_KEY'] and api_keys['GOOGLE_CSE_ID']:
            api_test_results['google'] = self._test_google_api(
                api_keys['GOOGLE_SEARCH_API_KEY'], 
                api_keys['GOOGLE_CSE_ID']
            )
        
        return {
            'configured_apis': configured_apis,
            'api_test_results': api_test_results
        }
    
    def _test_brave_api(self, api_key: str) -> Dict[str, any]:
        """测试Brave API"""
        print("     🧪 测试Brave API...")
        
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                'Accept': 'application/json',
                'X-Subscription-Token': api_key,
                'User-Agent': 'Mozilla/5.0 (compatible; HuaweiRAG/1.0)'
            }
            params = {'q': 'test', 'count': 1}
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                print("       ✅ Brave API可用")
                return {'status': 'success', 'status_code': 200}
            elif response.status_code == 401:
                print("       ❌ API密钥无效")
                return {'status': 'auth_error', 'status_code': 401}
            elif response.status_code == 429:
                print("       ⚠️ API调用限制")
                return {'status': 'rate_limit', 'status_code': 429}
            else:
                print(f"       ❌ API错误: {response.status_code}")
                return {'status': 'api_error', 'status_code': response.status_code}
                
        except ConnectionError as e:
            print("       ❌ 网络连接失败")
            return {'status': 'connection_error', 'error': str(e)}
        except Exception as e:
            print(f"       ❌ 其他错误: {str(e)[:50]}...")
            return {'status': 'error', 'error': str(e)}
    
    def _test_serper_api(self, api_key: str) -> Dict[str, any]:
        """测试Serper API"""
        print("     🧪 测试Serper API...")
        
        try:
            url = "https://google.serper.dev/search"
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
            data = {'q': 'test', 'num': 1}
            
            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            if response.status_code == 200:
                print("       ✅ Serper API可用")
                return {'status': 'success', 'status_code': 200}
            else:
                print(f"       ❌ API错误: {response.status_code}")
                return {'status': 'api_error', 'status_code': response.status_code}
                
        except Exception as e:
            print(f"       ❌ 错误: {str(e)[:50]}...")
            return {'status': 'error', 'error': str(e)}
    
    def _test_serpapi(self, api_key: str) -> Dict[str, any]:
        """测试SerpAPI"""
        print("     🧪 测试SerpAPI...")
        
        try:
            url = "https://serpapi.com/search"
            params = {
                'engine': 'google',
                'q': 'test',
                'num': 1,
                'api_key': api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                print("       ✅ SerpAPI可用")
                return {'status': 'success', 'status_code': 200}
            else:
                print(f"       ❌ API错误: {response.status_code}")
                return {'status': 'api_error', 'status_code': response.status_code}
                
        except Exception as e:
            print(f"       ❌ 错误: {str(e)[:50]}...")
            return {'status': 'error', 'error': str(e)}
    
    def _test_google_api(self, api_key: str, cse_id: str) -> Dict[str, any]:
        """测试Google Custom Search API"""
        print("     🧪 测试Google Custom Search API...")
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': cse_id,
                'q': 'test',
                'num': 1
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                print("       ✅ Google API可用")
                return {'status': 'success', 'status_code': 200}
            else:
                print(f"       ❌ API错误: {response.status_code}")
                return {'status': 'api_error', 'status_code': response.status_code}
                
        except Exception as e:
            print(f"       ❌ 错误: {str(e)[:50]}...")
            return {'status': 'error', 'error': str(e)}
    
    def generate_solutions(self, diagnostic_results: Dict[str, any]) -> List[str]:
        """根据诊断结果生成解决方案"""
        solutions = []
        
        connectivity_results = diagnostic_results.get('connectivity', {})
        dns_results = diagnostic_results.get('dns', {})
        proxy_results = diagnostic_results.get('proxy', {})
        config_results = diagnostic_results.get('config_test', {})
        api_results = diagnostic_results.get('api_diagnosis', {})
        
        # 分析连接问题
        connection_failures = [k for k, v in connectivity_results.items() 
                             if v.get('status') in ['connection_error', 'timeout']]
        
        if connection_failures:
            if 'google' in connection_failures and 'brave_api' in connection_failures:
                solutions.append("🌐 网络连接问题：")
                solutions.append("   - 您的网络可能无法访问国外网站")
                solutions.append("   - 建议使用VPN或代理服务器")
                solutions.append("   - 或者配置国内可用的搜索API（如使用中转服务）")
        
        # 分析DNS问题
        dns_failures = [k for k, v in dns_results.items() 
                       if v.get('status') == 'dns_error']
        
        if dns_failures:
            solutions.append("🔍 DNS解析问题：")
            solutions.append("   - 尝试更换DNS服务器：8.8.8.8 或 114.114.114.114")
            solutions.append("   - 检查本地hosts文件配置")
        
        # 代理设置建议
        if proxy_results.get('status') == 'proxy_detected':
            solutions.append("🔧 代理配置建议：")
            solutions.append("   - 确认代理服务器正常工作")
            solutions.append("   - 尝试在代理中添加搜索API域名到白名单")
        
        # API配置建议
        api_test_results = api_results.get('api_test_results', {})
        working_apis = [k for k, v in api_test_results.items() 
                       if v.get('status') == 'success']
        
        if working_apis:
            solutions.append(f"✅ 可用的搜索API：{', '.join(working_apis).upper()}")
        else:
            solutions.append("🔑 搜索API配置建议：")
            solutions.append("   1. 注册Brave搜索API (推荐，免费额度高)：")
            solutions.append("      https://api.search.brave.com/")
            solutions.append("   2. 或注册Serper API：")
            solutions.append("      https://serper.dev/")
            solutions.append("   3. 在.env文件中配置对应的API密钥")
        
        # 网络配置优化建议
        successful_configs = [k for k, v in config_results.items() 
                            if v.get('status') == 'success']
        
        if '禁用SSL验证' in successful_configs and '默认配置' not in successful_configs:
            solutions.append("🔐 SSL证书问题：")
            solutions.append("   - 您的环境可能存在SSL证书验证问题")
            solutions.append("   - 可以临时禁用SSL验证（不推荐用于生产环境）")
        
        return solutions
    
    def run_full_diagnosis(self) -> Dict[str, any]:
        """运行完整的网络诊断"""
        print("="*60)
        print("🔧 华为RAG网络连接诊断工具")
        print("="*60)
        
        results = {}
        
        # 1. 基本连通性检查
        results['connectivity'] = self.check_basic_connectivity()
        
        # 2. DNS解析检查
        results['dns'] = self.check_dns_resolution()
        
        # 3. 代理设置检查
        results['proxy'] = self.check_proxy_settings()
        
        # 4. 不同配置测试
        results['config_test'] = self.test_with_different_configs()
        
        # 5. API连接诊断
        results['api_diagnosis'] = self.diagnose_api_connectivity()
        
        # 6. 生成解决方案
        solutions = self.generate_solutions(results)
        
        print("\n" + "="*60)
        print("💡 诊断建议")
        print("="*60)
        
        if solutions:
            for solution in solutions:
                print(solution)
        else:
            print("✅ 网络连接正常，未发现明显问题")
        
        print("\n" + "="*60)
        print("🔧 手动配置建议")
        print("="*60)
        print("如果问题仍然存在，可以尝试以下配置：")
        print("")
        print("1. 设置环境变量（在 .env文件中）：")
        print("   BRAVE_API_KEY=your_brave_api_key")
        print("   SERPER_API_KEY=your_serper_api_key")
        print("")
        print("2. 如果在企业网络环境中，联系网络管理员：")
        print("   - 开放以下域名的访问权限：")
        print("     * api.search.brave.com")
        print("     * google.serper.dev")
        print("     * serpapi.com")
        print("     * api.firecrawl.dev")
        print("")
        print("3. 如果在中国大陆，可能需要：")
        print("   - 使用VPN或代理服务器")
        print("   - 或寻找提供中国大陆访问的API服务商")
        
        return results

def main():
    """主函数 - 命令行工具入口"""
    diagnostics = NetworkDiagnostics()
    results = diagnostics.run_full_diagnosis()
    
    # 可以选择保存诊断结果
    save_results = input("\n💾 是否保存诊断结果到文件？(y/N): ").strip().lower()
    if save_results in ['y', 'yes']:
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"network_diagnosis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"📁 诊断结果已保存到: {filename}")

if __name__ == "__main__":
    main() 