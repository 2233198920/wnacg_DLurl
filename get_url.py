import asyncio
from dataclasses import dataclass
from typing import List, Union
import json
import re
import os
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

# 从配置文件导入
from config import (
    API_DOMAIN, get_cookie, get_request_headers_with_cookie, 
    REQUEST_CONFIG, DIRECTORIES
)

@dataclass
class DownloadLink:
    url: str
    text: str
    type: str

async def get_download_links(session: aiohttp.ClientSession, cookie: str, comic_id: int) -> dict:
    """获取漫画的下载链接"""
    url = f"https://{API_DOMAIN}/download-index-aid-{comic_id}.html"
    headers = get_request_headers_with_cookie(cookie)
    
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

async def get_download_links_safe(session: aiohttp.ClientSession, cookie: str, comic_id: int, comic_title: str = "") -> dict:
    """安全地获取单个漫画的下载链接，出错时返回空字典"""
    try:
        links = await get_download_links(session, cookie, comic_id)
        return links
    except Exception as e:
        print(f"获取漫画 '{comic_title}' (ID: {comic_id}) 的下载链接失败: {e}")
        return {}

async def get_download_links_batch(session: aiohttp.ClientSession, cookie: str, comic_ids: List[Union[int, dict]]) -> dict:
    """批量获取漫画的下载链接"""
    results = {}
    
    # 从配置文件获取批量处理大小和延迟时间
    batch_size = REQUEST_CONFIG['batch_size']
    delay = REQUEST_CONFIG['delay_between_requests']
    
    for i in range(0, len(comic_ids), batch_size):
        batch = comic_ids[i:i + batch_size]
        tasks = []
        
        for item in batch:
            if isinstance(item, dict):
                comic_id = item.get('id')
                comic_title = item.get('title', '')
            else:
                comic_id = item
                comic_title = ""
            
            task = get_download_links_safe(session, cookie, comic_id, comic_title)
            tasks.append((comic_id, task))
        
        # 执行当前批次
        batch_results = await asyncio.gather(*[task for _, task in tasks])
        
        # 存储结果
        for (comic_id, _), links in zip(tasks, batch_results):
            results[comic_id] = links
        
        # 显示进度
        progress = min(i + batch_size, len(comic_ids))
        print(f"已处理 {progress}/{len(comic_ids)} 本漫画的下载链接")
        
        # 增加延迟避免请求过于频繁，防止IP被封
        if i + batch_size < len(comic_ids):
            await asyncio.sleep(delay)
    
    return results

def scan_json_files():
    """扫描search_results目录下的JSON文件"""
    search_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), DIRECTORIES['search_results'])
    
    if not os.path.exists(search_dir):
        return []
    
    json_files = []
    for filename in os.listdir(search_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(search_dir, filename)
            try:
                # 尝试读取JSON文件获取基本信息
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                total_comics = data.get('total_comics', 0)
                
                # 获取文件信息
                file_info = {
                    'filename': filename,
                    'filepath': filepath,
                    'total_comics': total_comics,
                    'file_size': os.path.getsize(filepath),
                    'modify_time': datetime.fromtimestamp(os.path.getmtime(filepath))
                }
                
                # 检查是否是搜索结果还是书架信息
                if 'search_metadata' in data:
                    search_meta = data['search_metadata']
                    file_info['type'] = 'search'
                    file_info['search_query'] = search_meta.get('search_query', '')
                    file_info['search_type'] = search_meta.get('search_type', '')
                elif 'shelf_metadata' in data:
                    shelf_meta = data['shelf_metadata']
                    file_info['type'] = 'shelf'
                    file_info['shelf_name'] = shelf_meta.get('shelf_name', '')
                else:
                    file_info['type'] = 'unknown'
                
                json_files.append(file_info)
                
            except (json.JSONDecodeError, KeyError, OSError) as e:
                print(f"跳过无效文件 {filename}: {e}")
                continue
    
    # 按修改时间排序，最新的在前
    json_files.sort(key=lambda x: x['modify_time'], reverse=True)
    return json_files

def display_file_list(json_files):
    """显示JSON文件列表"""
    if not json_files:
        print("search_results目录下没有找到JSON文件")
        return
    
    print("\n=== 可用的JSON文件 ===")
    for i, file_info in enumerate(json_files):
        print(f"\n{i + 1}. {file_info['filename']}")
        print(f"   类型: {'搜索结果' if file_info['type'] == 'search' else '书架信息' if file_info['type'] == 'shelf' else '未知'}")
        print(f"   漫画数量: {file_info['total_comics']}")
        print(f"   文件大小: {file_info['file_size'] / 1024:.1f} KB")
        print(f"   修改时间: {file_info['modify_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        if file_info['type'] == 'search':
            print(f"   搜索词: {file_info['search_query']}")
            print(f"   搜索类型: {file_info['search_type']}")
        elif file_info['type'] == 'shelf':
            print(f"   书架名: {file_info['shelf_name']}")

def select_json_file():
    """让用户选择JSON文件"""
    json_files = scan_json_files()
    
    if not json_files:
        print("没有找到可用的JSON文件")
        print("请先使用search_id.py或get_shelf_info.py生成JSON文件")
        return None
    
    display_file_list(json_files)
    
    while True:
        try:
            choice = input(f"\n请选择要处理的文件 (1-{len(json_files)}) 或输入 'q' 退出: ").strip()
            
            if choice.lower() == 'q':
                return None
            
            file_index = int(choice) - 1
            if 0 <= file_index < len(json_files):
                selected_file = json_files[file_index]
                print(f"\n已选择: {selected_file['filename']}")
                return selected_file['filepath']
            else:
                print("无效的选择，请重新输入")
        
        except ValueError:
            print("请输入有效的数字")
        except KeyboardInterrupt:
            print("\n操作已取消")
            return None

async def main_from_json(cookie: str, json_file: str):
    """从JSON文件读取漫画信息并获取下载链接"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        comics = data.get('comics', [])
        if not comics:
            print("JSON文件中没有找到漫画数据")
            return
        
        # 检查JSON格式类型
        is_search_result = 'search_metadata' in data
        metadata_info = ""
        
        if is_search_result:
            search_meta = data.get('search_metadata', {})
            search_query = search_meta.get('search_query', '')
            search_type = search_meta.get('search_type', '')
            metadata_info = f" (搜索结果: {search_query}, 类型: {search_type})"
        else:
            # 书架信息格式
            if 'shelf_metadata' in data:
                shelf_meta = data['shelf_metadata']
                shelf_name = shelf_meta.get('shelf_name', '未知书架')
                metadata_info = f" (书架: {shelf_name})"
            elif comics and comics[0].get('shelf'):
                shelf_name = comics[0]['shelf'].get('name', '未知书架')
                metadata_info = f" (书架: {shelf_name})"
        
        print(f"从JSON文件中读取到 {len(comics)} 本漫画{metadata_info}")
        
        async with aiohttp.ClientSession() as session:
            # 获取下载链接
            print("正在获取下载链接...")
            download_results = await get_download_links_batch(session, cookie, comics)
            
            # 更新漫画数据
            for comic in comics:
                comic_id = comic.get('id')
                if comic_id in download_results:
                    comic['download_links'] = download_results[comic_id]
            
            # 创建url目录
            url_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), DIRECTORIES['downloads'])
            os.makedirs(url_dir, exist_ok=True)
            
            # 生成输出文件名
            input_filename = os.path.basename(json_file)
            if input_filename.endswith('.json'):
                base_name = input_filename[:-5]  # 去掉.json
            else:
                base_name = input_filename
            
            output_filename = f"{base_name}_with_downloads.json"
            output_filepath = os.path.join(url_dir, output_filename)
            
            # 保持原有数据结构，只添加下载链接
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"下载链接已添加并保存到: {output_filepath}")
            
            # 统计下载链接情况
            total_with_links = sum(1 for comic in comics if comic.get('download_links'))
            print(f"成功获取下载链接的漫画: {total_with_links}/{len(comics)}")
            
    except FileNotFoundError:
        print(f"文件 {json_file} 不存在")
    except json.JSONDecodeError:
        print(f"文件 {json_file} 不是有效的JSON格式")
    except Exception as e:
        print(f"处理JSON文件时出错: {e}")

async def main_interactive():
    """交互式选择JSON文件并获取下载链接"""
    print("=== WNACG 下载链接获取工具 ===")
    print("自动扫描search_results目录下的JSON文件")
    print("支持搜索结果和书架信息两种格式")
    print()
    
    selected_file = select_json_file()
    if not selected_file:
        print("未选择文件，程序退出")
        return
    
    # 从配置文件获取cookie
    try:
        ck = get_cookie()
        await main_from_json(ck, selected_file)
    except ValueError as e:
        print(f'配置错误: {e}')
        print('请检查config.py文件中的WNACG_COOKIE设置')

async def main_single(cookie: str, comic_id: int):
    """获取单个漫画的下载链接"""
    async with aiohttp.ClientSession() as session:
        print(f"正在获取漫画 ID: {comic_id} 的下载链接...")
        links = await get_download_links_safe(session, cookie, comic_id)
        
        if links:
            print("\n下载链接:")
            for name, link_info in links.items():
                print(f"  {name}: {link_info['url']}")
        else:
            print("未找到下载链接")
        
        return links

if __name__ == "__main__":
    import os
    import sys
    
    try:
        # 从配置文件获取cookie
        ck = get_cookie()
        
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if arg.endswith('.json'):
                # 从指定JSON文件获取下载链接
                asyncio.run(main_from_json(ck, arg))
            else:
                try:
                    comic_id = int(arg)
                    # 获取单个漫画的下载链接
                    asyncio.run(main_single(ck, comic_id))
                except ValueError:
                    print("参数必须是JSON文件路径或漫画ID")
        else:
            # 交互式模式
            asyncio.run(main_interactive())
            
    except ValueError as e:
        print(f"配置错误: {e}")
        print("请检查config.py文件中的WNACG_COOKIE设置")