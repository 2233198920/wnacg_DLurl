"""
WNACG 工具配置文件
在这里统一管理Cookie、域名等配置信息
"""

# API域名配置
API_DOMAIN = "www.wnacg01.cc"

# Cookie配置 - 请在这里填入你的Cookie
# 获取方法：
# 1. 登录 www.wnacg01.cc
# 2. 打开浏览器开发者工具 (F12)
# 3. 进入 Network 选项卡
# 4. 刷新页面
# 5. 找到任意一个请求，查看 Request Headers 中的 Cookie
# 6. 复制完整的Cookie字符串到下方
WNACG_COOKIE = "_ym_uid=1733220519349694624; _ym_d=1733220519; cf_clearance=eBvExRGla0FdDwnmQGuMytjcdWrCvznPx3wCMv7Gkh4-1743696552-1.2.1.1-XaEN1p9L2YVmDy6HHyNu9A.MODRDezlyZSLD8fmA38LFF5AJ.kGwguXVArwtDQAfmltXpMQa8ItQfIBtOSrSATm7fxzx1zNAJsFrkWlhCtKsNmrkcEwMxz3GQkaFtEbXlbzSVkJJaP5j9jXwGetfAmjN8p6S1kyUI.7Oc74S9pvAL6QoA1HPlHLEcJ2aiuUoiZxWRYLh24pmqDB4zsFnk8CBuwZlpB2PAsRVXhaeNecBN562SemtqRP53zzSr9nXExjzd7xdOv2rQyas28kvIO_TU4QgCMZBsClEE2_PjrsKkbd7E3sBB2zTjzG18rQq9YuTItFu.bUnXIC9RmQd17_eAlxYQh6.j5_UNwCQx4fNRp9htXuSWx.tdvi9U9Vv; MPIC_bnS5=ddb3ppqJ5Q1spcMqFKFSQPAeXaGp6PrHQR%2FrJk6%2FnbqTxvHf44JFirSw%2BWgXc5pXYoES3RCIJLfkWani4QSdL9FzvnY"

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

def get_cookie():
    """获取Cookie，优先从配置文件，然后从环境变量"""
    import os
    
    if WNACG_COOKIE:
        return WNACG_COOKIE
    
    env_cookie = os.environ.get('WNACG_COOKIE')
    if env_cookie:
        return env_cookie
    
    raise ValueError('请在config.py中设置WNACG_COOKIE或设置WNACG_COOKIE环境变量')

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
    
    try:
        get_cookie()
    except ValueError as e:
        errors.append(str(e))
    
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True

if __name__ == "__main__":
    print("=== WNACG 配置文件检查 ===")
    print(f"API域名: {API_DOMAIN}")
    print(f"Cookie长度: {len(get_cookie()) if get_cookie() else 0} 字符")
    print(f"搜索结果目录: {DIRECTORIES['search_results']}")
    print(f"下载链接目录: {DIRECTORIES['downloads']}")
    
    if validate_config():
        print("✓ 配置验证通过")
    else:
        print("✗ 配置验证失败")
