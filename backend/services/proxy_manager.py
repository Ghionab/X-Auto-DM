"""
Proxy Management Service for twitterapi.io integration
Handles proxy validation, testing, and rotation
"""

import re
import requests
import logging
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed


class ProxyManager:
    """
    Manages proxy validation, testing, and rotation for API requests
    """
    
    def __init__(self, default_timeout: int = 10):
        """
        Initialize proxy manager
        
        Args:
            default_timeout: Default timeout for proxy tests in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.default_timeout = default_timeout
        self.test_urls = [
            'https://httpbin.org/ip',
            'https://api.ipify.org?format=json',
            'https://ifconfig.me/ip'
        ]
    
    def validate_proxy_format(self, proxy: str) -> Dict[str, Any]:
        """
        Validate proxy URL format and extract components
        
        Args:
            proxy: Proxy URL to validate
            
        Returns:
            Validation result with parsed components
        """
        if not proxy or not isinstance(proxy, str):
            return {
                'valid': False,
                'error': 'Proxy must be a non-empty string'
            }
        
        # Expected format: http://username:password@ip:port or https://username:password@ip:port
        pattern = r'^(https?)://([^:]+):([^@]+)@([^:]+):(\d+)$'
        match = re.match(pattern, proxy.strip())
        
        if not match:
            return {
                'valid': False,
                'error': 'Invalid proxy format. Expected: http://username:password@ip:port'
            }
        
        protocol, username, password, host, port = match.groups()
        
        # Validate port range
        try:
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                return {
                    'valid': False,
                    'error': 'Port must be between 1 and 65535'
                }
        except ValueError:
            return {
                'valid': False,
                'error': 'Port must be a valid number'
            }
        
        # Validate IP address format (basic check)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, host):
            return {
                'valid': False,
                'error': 'Invalid IP address format'
            }
        
        # Check IP address octets
        octets = host.split('.')
        for octet in octets:
            if not (0 <= int(octet) <= 255):
                return {
                    'valid': False,
                    'error': 'Invalid IP address - octets must be 0-255'
                }
        
        return {
            'valid': True,
            'protocol': protocol,
            'username': username,
            'password': password,
            'host': host,
            'port': port_num,
            'formatted_proxy': proxy.strip()
        }
    
    def test_proxy_connection(self, proxy: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Test proxy connectivity and performance
        
        Args:
            proxy: Proxy URL to test
            timeout: Request timeout in seconds
            
        Returns:
            Test result with performance metrics
        """
        timeout = timeout or self.default_timeout
        
        # First validate format
        validation = self.validate_proxy_format(proxy)
        if not validation['valid']:
            return {
                'success': False,
                'error': validation['error'],
                'proxy': proxy
            }
        
        # Configure proxy for requests
        proxies = {
            'http': proxy,
            'https': proxy
        }
        
        test_results = []
        
        for test_url in self.test_urls:
            start_time = time.time()
            
            try:
                self.logger.info(f"Testing proxy {proxy} with {test_url}")
                
                response = requests.get(
                    test_url,
                    proxies=proxies,
                    timeout=timeout,
                    headers={'User-Agent': 'ProxyTester/1.0'}
                )
                
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status_code == 200:
                    # Try to get IP from response
                    try:
                        if 'json' in response.headers.get('content-type', ''):
                            data = response.json()
                            ip = data.get('ip', data.get('origin', 'unknown'))
                        else:
                            ip = response.text.strip()
                    except:
                        ip = 'unknown'
                    
                    test_results.append({
                        'url': test_url,
                        'success': True,
                        'response_time_ms': round(response_time, 2),
                        'ip': ip,
                        'status_code': response.status_code
                    })
                else:
                    test_results.append({
                        'url': test_url,
                        'success': False,
                        'error': f'HTTP {response.status_code}',
                        'response_time_ms': round(response_time, 2)
                    })
                    
            except requests.exceptions.Timeout:
                test_results.append({
                    'url': test_url,
                    'success': False,
                    'error': f'Timeout after {timeout}s',
                    'response_time_ms': timeout * 1000
                })
            except requests.exceptions.ConnectionError as e:
                test_results.append({
                    'url': test_url,
                    'success': False,
                    'error': f'Connection error: {str(e)}',
                    'response_time_ms': (time.time() - start_time) * 1000
                })
            except Exception as e:
                test_results.append({
                    'url': test_url,
                    'success': False,
                    'error': f'Unexpected error: {str(e)}',
                    'response_time_ms': (time.time() - start_time) * 1000
                })
        
        # Calculate overall success rate and average response time
        successful_tests = [r for r in test_results if r['success']]
        success_rate = len(successful_tests) / len(test_results) * 100
        
        avg_response_time = 0
        if successful_tests:
            avg_response_time = sum(r['response_time_ms'] for r in successful_tests) / len(successful_tests)
        
        overall_success = success_rate >= 50  # At least 50% of tests must pass
        
        result = {
            'success': overall_success,
            'proxy': proxy,
            'success_rate': round(success_rate, 1),
            'avg_response_time_ms': round(avg_response_time, 2),
            'test_results': test_results
        }
        
        if not overall_success:
            result['error'] = f'Proxy failed connectivity test (success rate: {success_rate}%)'
        
        self.logger.info(f"Proxy test completed: {proxy} - Success: {overall_success}")
        
        return result
    
    def test_multiple_proxies(self, proxies: List[str], max_workers: int = 5) -> Dict[str, Any]:
        """
        Test multiple proxies concurrently
        
        Args:
            proxies: List of proxy URLs to test
            max_workers: Maximum concurrent tests
            
        Returns:
            Results for all tested proxies
        """
        if not proxies:
            return {
                'total_tested': 0,
                'successful': [],
                'failed': [],
                'results': []
            }
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all proxy tests
            future_to_proxy = {
                executor.submit(self.test_proxy_connection, proxy): proxy 
                for proxy in proxies
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Proxy test failed for {proxy}: {str(e)}")
                    results.append({
                        'success': False,
                        'proxy': proxy,
                        'error': f'Test execution failed: {str(e)}'
                    })
        
        # Separate successful and failed proxies
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        # Sort successful proxies by response time
        successful.sort(key=lambda x: x.get('avg_response_time_ms', float('inf')))
        
        return {
            'total_tested': len(proxies),
            'successful_count': len(successful),
            'failed_count': len(failed),
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    def get_proxy_config(self, proxy: str) -> Optional[Dict[str, str]]:
        """
        Get proxy configuration for requests library
        
        Args:
            proxy: Proxy URL
            
        Returns:
            Proxy configuration dict or None if invalid
        """
        validation = self.validate_proxy_format(proxy)
        if not validation['valid']:
            return None
        
        return {
            'http': proxy,
            'https': proxy
        }
    
    def format_proxy_url(self, protocol: str, username: str, password: str, 
                        host: str, port: int) -> str:
        """
        Format proxy components into URL
        
        Args:
            protocol: http or https
            username: Proxy username
            password: Proxy password
            host: Proxy host/IP
            port: Proxy port
            
        Returns:
            Formatted proxy URL
        """
        return f"{protocol}://{username}:{password}@{host}:{port}"
    
    def extract_proxy_info(self, proxy: str) -> Optional[Dict[str, Any]]:
        """
        Extract information from proxy URL for display purposes
        
        Args:
            proxy: Proxy URL
            
        Returns:
            Proxy information dict or None if invalid
        """
        validation = self.validate_proxy_format(proxy)
        if not validation['valid']:
            return None
        
        return {
            'protocol': validation['protocol'],
            'host': validation['host'],
            'port': validation['port'],
            'username': validation['username'],
            # Don't include password for security
            'display_url': f"{validation['protocol']}://{validation['username']}:***@{validation['host']}:{validation['port']}"
        }


class ProxyRotator:
    """
    Manages proxy rotation for high-volume requests
    """
    
    def __init__(self, proxies: List[str], proxy_manager: Optional[ProxyManager] = None):
        """
        Initialize proxy rotator
        
        Args:
            proxies: List of proxy URLs
            proxy_manager: Optional ProxyManager instance
        """
        self.proxy_manager = proxy_manager or ProxyManager()
        self.logger = logging.getLogger(__name__)
        
        # Validate and store working proxies
        self.working_proxies = []
        self.failed_proxies = []
        self.current_index = 0
        
        self._validate_proxies(proxies)
    
    def _validate_proxies(self, proxies: List[str]):
        """
        Validate all provided proxies and separate working from failed
        
        Args:
            proxies: List of proxy URLs to validate
        """
        if not proxies:
            self.logger.warning("No proxies provided to rotator")
            return
        
        self.logger.info(f"Validating {len(proxies)} proxies...")
        
        test_results = self.proxy_manager.test_multiple_proxies(proxies)
        
        self.working_proxies = [r['proxy'] for r in test_results['successful']]
        self.failed_proxies = [r['proxy'] for r in test_results['failed']]
        
        self.logger.info(f"Proxy validation complete: {len(self.working_proxies)} working, {len(self.failed_proxies)} failed")
    
    def get_next_proxy(self) -> Optional[str]:
        """
        Get next proxy in rotation
        
        Returns:
            Next proxy URL or None if no working proxies
        """
        if not self.working_proxies:
            return None
        
        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        
        return proxy
    
    def get_proxy_config(self) -> Optional[Dict[str, str]]:
        """
        Get proxy configuration for next proxy in rotation
        
        Returns:
            Proxy configuration dict or None
        """
        proxy = self.get_next_proxy()
        if not proxy:
            return None
        
        return self.proxy_manager.get_proxy_config(proxy)
    
    def get_working_proxy_count(self) -> int:
        """
        Get count of working proxies
        
        Returns:
            Number of working proxies
        """
        return len(self.working_proxies)
    
    def add_proxy(self, proxy: str) -> bool:
        """
        Add and test a new proxy
        
        Args:
            proxy: Proxy URL to add
            
        Returns:
            True if proxy was added successfully
        """
        test_result = self.proxy_manager.test_proxy_connection(proxy)
        
        if test_result['success']:
            if proxy not in self.working_proxies:
                self.working_proxies.append(proxy)
                self.logger.info(f"Added working proxy: {proxy}")
            return True
        else:
            if proxy not in self.failed_proxies:
                self.failed_proxies.append(proxy)
                self.logger.warning(f"Failed to add proxy: {proxy} - {test_result.get('error')}")
            return False