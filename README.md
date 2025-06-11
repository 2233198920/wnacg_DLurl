# WNACG 工具集

一套用于获取 WNACG 网站内容的工具，包括搜索、收藏夹获取和下载链接提取功能。

## 功能模块

- **search_id.py** - 智能搜索工具，支持关键词和标签搜索
- **get_shelf_info.py** - 获取收藏夹/书架信息
- **get_url.py** - 提取漫画下载链接
- **download.py** - 批量下载工具，支持多线程异步下载
- **config.py** - 统一配置管理（支持自动登录获取Cookie）

## 快速开始

### 1. 安装依赖

```bash
pip install aiohttp beautifulsoup4 requests tqdm
```

### 2. 配置登录信息

编辑 `config.py` 文件，设置你的登录信息：

```python
LOGIN_CONFIG = {
    "username": "你的用户名",  
    "password": "你的密码",
}
```

**或者** 设置环境变量：

```bash
set WNACG_USERNAME=你的用户名
set WNACG_PASSWORD=你的密码
```

### 3. Cookie管理

本工具支持三种Cookie获取方式，按优先级排序：

1. **配置文件** - 在 `config.py` 中设置 `WNACG_COOKIE`
2. **环境变量** - 设置 `WNACG_COOKIE` 环境变量  
3. **自动登录** - 使用配置的用户名密码自动登录获取

**推荐流程：**
- 首次使用：配置用户名密码，工具会自动登录获取Cookie
- 长期使用：将获取的Cookie保存到配置文件，避免频繁登录

### 4. 使用工具

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

**批量下载漫画：**

```bash
python download.py
```

**配置检查：**

```bash
python config.py
```

## 工作流程

1. 配置登录信息或Cookie
2. 使用 `search_id.py` 或 `get_shelf_info.py` 获取漫画信息 → 保存到 `search_results/`
3. 使用 `get_url.py` 读取JSON文件并获取下载链接 → 保存到 `url/`
4. 使用 `download.py` 批量下载漫画文件 → 保存到 `downloads/`

## Cookie获取方法

### 方法1：自动获取（推荐）
1. 在 `config.py` 中配置用户名和密码
2. 运行任意工具，系统会自动登录获取Cookie
3. 根据提示将Cookie保存到配置文件以避免频繁登录

### 方法2：手动获取
1. 登录 WNACG 网站
2. 打开浏览器开发者工具（F12）
3. 刷新页面，在Network中复制任意请求的Cookie
4. 粘贴到 `config.py` 的 `WNACG_COOKIE` 变量中


## 配置说明

`config.py` 包含以下主要配置：

- `LOGIN_CONFIG` - 登录用户名和密码
- `WNACG_COOKIE` - Cookie字符串（可选，留空则自动获取）
- `REQUEST_CONFIG` - 请求配置（超时、重试、延迟等）
- `DIRECTORIES` - 文件存储目录配置
- `SEARCH_CONFIG` - 搜索相关配置

## 下载功能特性

- **智能文件选择** - 自动扫描 `url/` 目录下的JSON文件
- **多链接重试** - 单个漫画支持多个下载源，自动切换
- **异步下载** - 高效的异步下载，支持进度显示
- **断点续传** - 支持下载失败重试机制
- **安全文件名** - 自动清理非法字符，确保文件名兼容性
- **下载统计** - 详细的成功/失败统计和汇总报告

## 注意事项

- 请合理使用，避免频繁请求
- Cookie有时效性，失效后会自动重新登录获取
- 工具已内置延迟机制防止IP被封
- 支持环境变量配置，便于部署和安全管理
- 首次使用会自动登录，建议将获取的Cookie保存以提高效率
- 下载大文件时请确保网络稳定，工具会自动重试失败的下载

## 目录结构

```
├── config.py           # 配置文件（支持自动登录）
├── search_id.py        # 搜索工具
├── get_shelf_info.py   # 收藏夹获取
├── get_url.py          # 下载链接提取
├── download.py         # 批量下载工具
├── search_results/     # 搜索结果存储
├── url/               # 带下载链接的结果
├── downloads/         # 下载的漫画文件
└── README.md          # 说明文档
```

## 环境变量支持

为了更好的安全性，支持以下环境变量：

- `WNACG_USERNAME` - 用户名
- `WNACG_PASSWORD` - 密码  
- `WNACG_COOKIE` - Cookie字符串

使用环境变量可以避免在配置文件中暴露敏感信息。