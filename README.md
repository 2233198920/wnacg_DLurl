# WNACG 工具集

一套用于获取 WNACG 网站内容的工具，包括搜索、收藏夹获取和下载链接提取功能。

## 功能模块

- **search_id.py** - 智能搜索工具，支持关键词和标签搜索
- **get_shelf_info.py** - 获取收藏夹/书架信息
- **get_url.py** - 提取漫画下载链接
- **config.py** - 统一配置管理

## 快速开始

### 1. 安装依赖

```bash
pip install aiohttp beautifulsoup4 requests
```

### 2. 配置Cookie

编辑 `config.py` 文件，设置你的Cookie：

```python
WNACG_COOKIE = "你的cookie内容"
```

### 3. 使用工具

**搜索漫画：**

```bash
python search_id.py
```

**获取收藏夹：**

```bash
python get_shelf_info.py
```

**获取下载链接：**

```bash
python get_url.py
```

## 工作流程

1. 使用 `search_id.py` 或 `get_shelf_info.py` 获取漫画信息 → 保存到 `search_results/`
2. 使用 `get_url.py` 读取JSON文件并获取下载链接 → 保存到 `url/`

## 获取Cookie方法

1. 登录 WNACG 网站
2. 打开浏览器开发者工具（F12）
3. 刷新页面，在Network中复制任意请求的Cookie

## 注意事项

- 请合理使用，避免频繁请求
- Cookie有时效性，失效后需重新获取
- 工具已内置延迟机制防止IP被封

## 目录结构

```
d:\code\wnacg\
├── config.py           # 配置文件
├── search_id.py        # 搜索工具
├── get_shelf_info.py   # 收藏夹获取
├── get_url.py          # 下载链接提取
├── search_results/     # 搜索结果存储
└── url/               # 带下载链接的结果
```