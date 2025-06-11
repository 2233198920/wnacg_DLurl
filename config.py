"""
WNACG 工具配置文件
在这里统一管理Cookie、域名等配置信息
"""
import requests
import os

# API域名配置
API_DOMAIN = "www.wnacg01.cc"

# 登录配置 - 请在这里填入你的登录信息
LOGIN_CONFIG = {
    "username": "",  # 你的用户名
    "password": "",  # 你的密码
}

# Cookie配置 - 可以手动填入，也可以留空让程序自动获取
WNACG_COOKIE = ""

# 请求配置
REQUEST_CONFIG = {
    "timeout": 10,
    "max_retries": 3,
    "delay_between_requests": 3,  # 秒
    "batch_size": 2,  # 批量处理大小
    "max_pages": 20,  # 默认最大页数
}

# User-Agent配置
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# 目录配置
DIRECTORIES = {
    "search_results": "search_results",  # 搜索结果和书架信息存储目录
    "downloads": "url",  # 下载链接存储目录
}

# 搜索配置
SEARCH_CONFIG = {
    "min_similarity": 0.3,  # 最小相似度阈值
    "page_size": 24,  # 每页结果数
}

def _login_and_get_cookie(username: str = None, password: str = None) -> str:
    """登录 WNACG 并获取 cookie"""
    # 如果没有提供用户名密码，从配置文件获取
    if username is None or password is None:
        username, password = get_login_config()
    
    data = {
        "login_name": username,
        "login_pass": password,
    }
    headers = get_headers()

    print(f"正在登录 {API_DOMAIN}...")
    
    # 发送登录请求
    resp = requests.post(f"https://{API_DOMAIN}/users-check_login.html",
                         data=data, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"登录请求失败，状态码: {resp.status_code}")

    # 解析 JSON，检查 ret 字段
    login_resp = resp.json()
    if not login_resp.get("ret"):
        raise RuntimeError(f"登录失败: {login_resp}")

    # 从响应头获取 cookie
    cookie = resp.headers.get("set-cookie")
    if not cookie:
        raise RuntimeError(f"响应中没有找到cookie: {login_resp}")

    print("✓ 登录成功，已获取cookie")
    return cookie

def get_cookie():
    """获取Cookie，优先级：配置文件 > 环境变量 > 自动登录获取"""
    
    # 1. 优先使用配置文件中的cookie
    if WNACG_COOKIE:
        return WNACG_COOKIE
    
    # 2. 尝试从环境变量获取
    env_cookie = os.environ.get('WNACG_COOKIE')
    if env_cookie:
        return env_cookie
    
    # 3. 自动登录获取cookie
    try:
        print("配置文件和环境变量中都没有找到cookie，尝试自动登录获取...")
        cookie = _login_and_get_cookie()
        
        # 提示用户可以将cookie保存到配置文件中
        print("\n" + "="*50)
        print("建议将以下cookie复制到config.py的WNACG_COOKIE变量中，避免频繁登录：")
        print(f'WNACG_COOKIE = "{cookie}"')
        print("="*50 + "\n")
        
        return cookie
    except Exception as e:
        raise ValueError(f'无法获取cookie: {e}')

def get_login_config():
    """获取登录配置"""
    import os
    
    # 优先从环境变量获取
    username = os.environ.get('WNACG_USERNAME') or LOGIN_CONFIG.get('username')
    password = os.environ.get('WNACG_PASSWORD') or LOGIN_CONFIG.get('password')
    
    if not username or not password:
        raise ValueError('请在config.py中设置LOGIN_CONFIG或设置环境变量WNACG_USERNAME和WNACG_PASSWORD')
    
    return username, password

def get_headers(referer=None):
    """获取标准请求头"""
    headers = {
        "User-Agent": USER_AGENT,
    }
    
    if referer:
        headers["referer"] = referer
    else:
        headers["referer"] = f"https://{API_DOMAIN}/"
    
    return headers

def get_request_headers_with_cookie(cookie=None):
    """获取包含Cookie的请求头"""
    if cookie is None:
        cookie = get_cookie()
    
    headers = get_headers()
    headers["cookie"] = cookie
    
    return headers

# 配置验证
def validate_config():
    """验证配置是否有效"""
    errors = []
    
    if not API_DOMAIN:
        errors.append("API_DOMAIN 不能为空")
    
    # 验证登录配置
    try:
        get_login_config()
    except ValueError as e:
        errors.append(str(e))
    
    # 验证cookie获取（这里不实际获取，只检查配置）
    if not WNACG_COOKIE and not os.environ.get('WNACG_COOKIE'):
        try:
            get_login_config()  # 确保可以登录获取
            print("⚠ 将使用自动登录获取cookie")
        except ValueError:
            errors.append("无法获取cookie：既没有配置cookie，也没有配置登录信息")
    
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True

if __name__ == "__main__":
    print("=== WNACG 配置文件检查 ===")
    print(f"API域名: {API_DOMAIN}")
    
    try:
        cookie = get_cookie()
        print(f"Cookie长度: {len(cookie)} 字符")
        print("✓ Cookie获取成功")
    except Exception as e:
        print(f"✗ Cookie获取失败: {e}")
    
    print(f"搜索结果目录: {DIRECTORIES['search_results']}")
    print(f"下载链接目录: {DIRECTORIES['downloads']}")
    
    if validate_config():
        print("✓ 配置验证通过")
    else:
        print("✗ 配置验证失败")
