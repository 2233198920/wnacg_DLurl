import asyncio
from dataclasses import dataclass, asdict
from typing import List
import json
import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

API_DOMAIN = "www.wnacg.com"

# 可以直接在这里设置 cookie，如果为空则使用环境变量
WNACG_COOKIE = ""

@dataclass
class Shelf:
    id: int
    name: str

@dataclass
class ComicInFavorite:
    id: int
    title: str
    cover: str
    favorite_time: str
    shelf: Shelf
    download_links: dict = None  # 添加下载链接字段

@dataclass
class GetFavoriteResult:
    comics: List[ComicInFavorite]
    current_page: int
    total_page: int
    shelf: Shelf
    # 移除 shelves 字段

async def get_favorite(session: aiohttp.ClientSession, cookie: str, shelf_id: int, page_num: int) -> GetFavoriteResult:
    url = f"https://{API_DOMAIN}/users-users_fav-page-{page_num}-c-{shelf_id}.html"
    headers = {
        "cookie": cookie,
        "referer": f"https://{API_DOMAIN}/",
    }
    async with session.get(url, headers=headers) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"Unexpected status {resp.status}: {text}")
    return parse_get_favorite(text)

def parse_get_favorite(html: str) -> GetFavoriteResult:
    soup = BeautifulSoup(html, "html.parser")
    comics = [parse_comic(div) for div in soup.select('.asTB')]

    page_span = soup.select_one('.thispage')
    current_page = int(page_span.get_text()) if page_span else 1

    page_links = soup.select('.f_left.paginator > a')
    total_page = int(page_links[-1].get_text()) if page_links else 1

    shelf = parse_shelf(soup.select_one('.cur'))

    return GetFavoriteResult(comics, current_page, total_page, shelf)

def parse_comic(div):
    a = div.select_one('.l_title > a')
    href = a['href']
    id = int(href.split('aid-')[1].split('.html')[0])
    title = a.get_text(strip=True)
    img = div.select_one('.asTBcell.thumb img')['src']
    cover = f"https:{img}"
    fav_span = div.select_one('.l_catg > span')
    favorite_time = fav_span.get_text(strip=True).replace('創建時間：', '') if fav_span else ''
    shelf = parse_shelf(div.select_one('.l_catg > a'))
    return ComicInFavorite(id, title, cover, favorite_time, shelf, {})  # 初始化下载链接为空字典

def parse_shelf(a):
    if not a:
        return Shelf(0, '')
    href = a.get('href', '')
    if not href:
        return Shelf(0, a.get_text(strip=True))
    
    # 处理不同的 href 格式
    if 'c-' in href:
        try:
            id = int(href.split('c-')[1].split('.html')[0])
        except (IndexError, ValueError):
            id = 0
    else:
        # 如果没有 c- 模式，默认为 0
        id = 0
    
    name = a.get_text(strip=True)
    return Shelf(id, name)

async def get_shelves(session: aiohttp.ClientSession, cookie: str) -> List[Shelf]:
    """获取所有书架列表"""
    url = f"https://{API_DOMAIN}/users-users_fav-page-1-c-0.html"
    headers = {
        "cookie": cookie,
        "referer": f"https://{API_DOMAIN}/",
    }
    async with session.get(url, headers=headers) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"Unexpected status {resp.status}: {text}")
    
    soup = BeautifulSoup(text, "html.parser")
    shelves = [parse_shelf(a) for a in soup.select('.nav_list > a')]
    return shelves

async def get_all_comics_from_shelf(session: aiohttp.ClientSession, cookie: str, shelf_id: int) -> List[ComicInFavorite]:
    """获取指定书架的所有书籍（所有分页）"""
    all_comics = []
    
    # 先获取第一页来确定总页数
    first_page_result = await get_favorite(session, cookie, shelf_id, 1)
    all_comics.extend(first_page_result.comics)
    total_pages = first_page_result.total_page
    
    print(f"书架 '{first_page_result.shelf.name}' 共有 {total_pages} 页")
    
    # 获取剩余页面
    if total_pages > 1:
        tasks = []
        for page in range(2, total_pages + 1):
            task = get_favorite(session, cookie, shelf_id, page)
            tasks.append(task)
        
        print(f"正在获取第 2-{total_pages} 页...")
        results = await asyncio.gather(*tasks)
        
        for result in results:
            all_comics.extend(result.comics)
    
    # 获取所有漫画的下载链接
    print(f"正在获取 {len(all_comics)} 本漫画的下载链接...")
    await get_download_links_for_comics(session, cookie, all_comics)
    
    return all_comics

async def get_download_links_for_comics(session: aiohttp.ClientSession, cookie: str, comics: List[ComicInFavorite]):
    """批量获取漫画的下载链接"""
    # 调整为一次处理2个，避免过于频繁的请求
    batch_size = 2
    for i in range(0, len(comics), batch_size):
        batch = comics[i:i + batch_size]
        tasks = []
        
        for comic in batch:
            task = get_download_links_safe(session, cookie, comic)
            tasks.append(task)
        
        # 执行当前批次
        await asyncio.gather(*tasks)
        
        # 显示进度
        progress = min(i + batch_size, len(comics))
        print(f"已处理 {progress}/{len(comics)} 本漫画的下载链接")
        
        # 增加延迟避免请求过于频繁，防止IP被封
        if i + batch_size < len(comics):
            await asyncio.sleep(3)  # 2秒延迟

async def get_download_links_safe(session: aiohttp.ClientSession, cookie: str, comic: ComicInFavorite):
    """安全地获取单个漫画的下载链接，出错时不会影响其他漫画"""
    try:
        links = await get_download_links(session, cookie, comic.id)
        comic.download_links = links
    except Exception as e:
        print(f"获取漫画 '{comic.title}' (ID: {comic.id}) 的下载链接失败: {e}")
        comic.download_links = {}

async def main(cookie: str, shelf_id: int = None, page_num: int = 1):
    async with aiohttp.ClientSession() as session:
        # 如果没有指定书架ID，先获取书架列表让用户选择
        if shelf_id is None:
            print("正在获取书架列表...")
            shelves = await get_shelves(session, cookie)
            
            print("\n可用的书架:")
            for i, shelf in enumerate(shelves):
                print(f"{i}: {shelf.name} (ID: {shelf.id})")
            
            try:
                choice = input("\n请选择书架编号 (直接回车选择'全部'): ").strip()
                if choice == "":
                    shelf_id = 0  # 默认选择全部
                else:
                    shelf_index = int(choice)
                    if 0 <= shelf_index < len(shelves):
                        shelf_id = shelves[shelf_index].id
                    else:
                        print("无效的选择，使用默认书架'全部'")
                        shelf_id = 0
            except (ValueError, KeyboardInterrupt):
                print("无效输入或取消操作，使用默认书架'全部'")
                shelf_id = 0
        
        # 获取所有书籍
        all_comics = await get_all_comics_from_shelf(session, cookie, shelf_id)
        
        # 构造结果
        result = {
            "comics": [asdict(comic) for comic in all_comics],
            "total_comics": len(all_comics)
        }
        
        # 保存到文件
        # 生成文件名，包含书架名和时间戳
        shelf_name = all_comics[0].shelf.name if all_comics else "empty"
        # 替换文件名中的非法字符
        safe_shelf_name = re.sub(r'[<>:"/\\|?*]', '_', shelf_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wnacg_comics_{safe_shelf_name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到文件: {filename}")
        print(f"共获取到 {len(all_comics)} 本漫画")

async def get_download_links(session: aiohttp.ClientSession, cookie: str, comic_id: int) -> dict:
    """获取漫画的下载链接"""
    url = f"https://{API_DOMAIN}/download-index-aid-{comic_id}.html"
    headers = {
        "cookie": cookie,
        "referer": f"https://{API_DOMAIN}/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with session.get(url, headers=headers) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"Unexpected status {resp.status}: {text}")
    
    return parse_download_links(text)

def parse_download_links(html: str) -> dict:
    """解析下载页面获取下载链接"""
    soup = BeautifulSoup(html, "html.parser")
    
    links = {}
    
    # 直接查找所有 .down_btn 元素
    download_buttons = soup.select('a.down_btn')
    
    for i, button in enumerate(download_buttons, 1):
        href = button.get('href', '')
        text = button.get_text(strip=True)
        
        if href:
            # 如果是相对协议链接（以//开头），添加https:
            if href.startswith('//'):
                full_url = f"https:{href}"
            # 如果是相对路径，添加域名
            elif href.startswith('/'):
                full_url = f"https://{API_DOMAIN}{href}"
            # 否则直接使用
            else:
                full_url = href
            
            links[text or f"下载链接{i}"] = {
                "url": full_url,
                "text": text,
                "type": "direct_link"
            }
    
    # 如果没有找到 .down_btn，尝试其他方法
    if not links:
        # 查找所有可能的下载链接
        all_links = soup.find_all('a')
        for i, link in enumerate(all_links):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 检查是否包含下载相关的关键词
            if (href and 
                ('download' in href.lower() or 
                 'wzip' in href.lower() or 
                 '.zip' in href.lower() or
                 text in ['本地下載一', '本地下載二', '本地下载一', '本地下载二'])):
                
                if href.startswith('//'):
                    full_url = f"https:{href}"
                elif href.startswith('/'):
                    full_url = f"https://{API_DOMAIN}{href}"
                else:
                    full_url = href
                
                links[text or f"下载链接{len(links)+1}"] = {
                    "url": full_url,
                    "text": text,
                    "type": "found_link"
                }
    
    return links

if __name__ == "__main__":
    import os
    # 优先使用代码中设置的 cookie，如果为空则使用环境变量
    ck = WNACG_COOKIE or os.environ.get('WNACG_COOKIE')
    if not ck:
        raise SystemExit('请在代码中设置 WNACG_COOKIE 常量或设置 WNACG_COOKIE 环境变量')
    
    # 运行主程序
    asyncio.run(main(ck))