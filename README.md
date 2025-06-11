# WNACG 收藏夹爬虫客户端

这是一个用于获取 WNACG 网站收藏夹内容的异步爬虫工具，支持批量获取漫画信息和下载链接。

## 功能特性

- 🚀 异步并发处理，提高爬取效率
- 📚 支持获取所有书架列表
- 📖 支持按书架分类获取收藏夹内容
- 🔗 自动获取漫画下载链接
- 💾 结果保存为 JSON 格式
- 🛡️ 内置请求限制，避免IP被封
- 📊 实时显示处理进度

## 安装依赖

```bash
pip install aiohttp beautifulsoup4
```

## 配置说明

### Cookie 配置

有两种方式配置 Cookie：

1. **直接在代码中设置**（推荐）
   ```python
   WNACG_COOKIE = "你的cookie内容"
   ```

2. **使用环境变量**
   ```bash
   # Windows
   set WNACG_COOKIE=你的cookie内容
   
   # Linux/Mac
   export WNACG_COOKIE="你的cookie内容"
   ```

### 获取 Cookie 的方法

1. 登录 WNACG 网站
2. 打开浏览器开发者工具（F12）
3. 进入 Network 选项卡
4. 刷新页面
5. 找到任意请求，复制 Request Headers 中的 Cookie 值

## 使用方法

### 基本使用

```bash
python wnacg_client.py
```

程序会自动显示可用的书架列表，让你选择要爬取的书架。

### 数据结构

程序会获取以下信息：

```json
{
  "comics": [
    {
      "id": 123456,
      "title": "漫画标题",
      "cover": "封面图片URL",
      "favorite_time": "收藏时间",
      "shelf": {
        "id": 1,
        "name": "书架名称"
      },
      "download_links": {
        "本地下载一": {
          "url": "下载链接URL",
          "text": "链接文本",
          "type": "direct_link"
        }
      }
    }
  ],
  "total_comics": 总数量
}
```

## 核心功能模块

### 1. 获取书架列表
```python
shelves = await get_shelves(session, cookie)
```

### 2. 获取收藏夹内容
```python
result = await get_favorite(session, cookie, shelf_id, page_num)
```

### 3. 获取所有页面内容
```python
all_comics = await get_all_comics_from_shelf(session, cookie, shelf_id)
```

### 4. 获取下载链接
```python
links = await get_download_links(session, cookie, comic_id)
```

## 输出文件

程序运行完成后会生成 JSON 文件，文件名格式：
```
wnacg_comics_{书架名}_{时间戳}.json
```

例如：`wnacg_comics_全部_20241201_143022.json`

## 注意事项

- ⚠️ 请合理使用，避免频繁请求导致IP被封
- 🕒 程序内置了请求延迟机制（3秒间隔）
- 📦 批处理大小设置为2个并发，可根据需要调整
- 🔐 Cookie 有效期有限，失效后需要重新获取
- 📁 非法文件名字符会自动替换为下划线

## 错误处理

- 网络请求失败会抛出异常
- 单个漫画下载链接获取失败不会影响其他漫画
- Cookie 失效会返回相应的错误信息

## 技术栈

- **Python 3.7+**
- **aiohttp**: 异步HTTP客户端
- **BeautifulSoup4**: HTML解析
- **asyncio**: 异步编程支持

## 许可证

本项目仅供学习和研究使用，请遵守相关网站的使用条款。