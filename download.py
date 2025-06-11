import asyncio
import json
import os
import random
import ssl
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout, TCPConnector
from tqdm import tqdm

# === 你的其它依赖或配置 ===
from config import get_request_headers_with_cookie, REQUEST_CONFIG, DIRECTORIES

# --------------------------------------------------------------------------- #
#                                核心下载类                                   #
# --------------------------------------------------------------------------- #
class ComicDownloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.failed_downloads: List[str] = []
        self.success_count: int = 0
        self.total_count: int = 0

    # ---------- 工具函数 ---------- #
    @staticmethod
    def _clean_name(name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()

    def get_filename_from_url(self, url: str, comic_title: str, link_name: str) -> str:
        """根据 URL / 标题 / 链接别名生成安全文件名"""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        ext = (path.split(".")[-1].lower() if "." in path else "zip")
        if ext not in {"zip", "rar", "7z", "tar", "gz"}:
            ext = "zip"
        ext = f".{ext}"

        safe_title = self._clean_name(comic_title)
        safe_link_name = self._clean_name(link_name)

        if safe_link_name and safe_link_name != safe_title:
            return f"{safe_title}_{safe_link_name}{ext}"
        return f"{safe_title}{ext}"

    # ---------- 单文件下载 ---------- #
    async def download_file(
        self,
        session: aiohttp.ClientSession,
        url: str,
        filepath: Path,
    ) -> bool:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

        try:
            async with session.get(url, headers=headers, ssl=False) as resp:
                if resp.status != 200:
                    tqdm.write(f"✗ HTTP {resp.status}: {url}")
                    return False

                filepath.parent.mkdir(parents=True, exist_ok=True)
                total = int(resp.headers.get("Content-Length", 0))

                # 子进度条
                with tqdm(
                    total=total or None,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=filepath.name[:30],      # 避免过长撑爆终端
                    dynamic_ncols=True,
                    leave=False,
                ) as bar, open(filepath, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
                        bar.update(len(chunk))

            return True

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            tqdm.write(f"✗ 网络/超时错误: {e}")
            return False
        except Exception as e:
            tqdm.write(f"✗ 未知错误: {e}")
            return False

    # ---------- 下载单本漫画 ---------- #
    async def download_comic(
        self,
        session: aiohttp.ClientSession,
        comic: Dict,
        *,
        max_retries: int = 3,
    ) -> bool:
        title = comic["title"]
        links = comic.get("download_links", {})
        if not links:
            return False

        for idx, (link_name, link_info) in enumerate(links.items(), 1):
            url = link_info["url"]
            filename = self.get_filename_from_url(url, title, link_name)
            filepath = self.download_dir / filename
            tqdm.write(f"  尝试链接 {idx}: {link_name}")

            for attempt in range(1, max_retries + 1):
                success = await self.download_file(session, url, filepath)
                if success:
                    tqdm.write(f"  ✓ 成功: {filename}")
                    return True
                if attempt < max_retries:
                    wait = 2 * attempt
                    tqdm.write(f"  … 重试 {attempt}/{max_retries-1}，等待 {wait}s")
                    await asyncio.sleep(wait)

            # 当前链接所有重试均失败 → 换下一个链接
            tqdm.write(f"  ✗ 链接 {idx} 全部重试失败\n")
            await asyncio.sleep(random.uniform(3, 8))

        # 所有链接失败
        tqdm.write(f"  ✗ {title} 所有下载链接均失败")
        return False

    # ---------- 主入口：从 JSON 下载 ---------- #
    async def download_from_json(self, json_path: str) -> None:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            tqdm.write(f"读取 JSON 失败: {e}")
            return

        comics = [c for c in data.get("comics", []) if c.get("download_links")]
        if not comics:
            tqdm.write("JSON 中没有带下载链接的漫画")
            return

        self.total_count = len(comics)
        tqdm.write(f"共有 {self.total_count} 本可下载 → {self.download_dir.resolve()}\n")

        connector = TCPConnector(ssl=False, limit=100, limit_per_host=10)
        timeout = ClientTimeout(total=300, connect=30, sock_read=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            with tqdm(
                total=self.total_count,
                desc="漫画总进度",
                dynamic_ncols=True,
            ) as pbar:
                for idx, comic in enumerate(comics, 1):
                    tqdm.write(f"\n[{idx}/{self.total_count}] 开始下载: {comic['title']}")
                    ok = await self.download_comic(session, comic)
                    self.success_count += int(ok)
                    if not ok:
                        self.failed_downloads.append(comic["title"])

                    pbar.update(1)
                    pbar.set_postfix(
                        成功=self.success_count,
                        失败=len(self.failed_downloads),
                    )

                    # 非最后一本 → 随机延迟
                    if idx < self.total_count:
                        await asyncio.sleep(random.uniform(5, 10))

        self.print_summary()

    # ---------- 打印汇总 ---------- #
    def print_summary(self) -> None:
        line = "=" * 60
        tqdm.write(f"\n{line}\n下载完成总结\n{line}")
        tqdm.write(f"总计: {self.total_count} 本")
        tqdm.write(f"成功: {self.success_count} 本")
        tqdm.write(f"失败: {len(self.failed_downloads)} 本")
        if self.failed_downloads:
            tqdm.write("\n失败列表:")
            for i, t in enumerate(self.failed_downloads, 1):
                tqdm.write(f"  {i}. {t}")
        tqdm.write(f"\n文件保存在: {self.download_dir.resolve()}\n")

# --------------------------------------------------------------------------- #
#                        JSON 文件扫描 & 选择逻辑                              #
# --------------------------------------------------------------------------- #
def scan_json_files_with_downloads(url_dir: str = "url") -> List[Dict]:
    """扫描 url/ 目录下含 download_links 的 JSON"""
    p = Path(url_dir)
    if not p.exists():
        return []

    results = []
    for jf in p.glob("*.json"):
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            comics = data.get("comics", [])
            if any(c.get("download_links") for c in comics):
                results.append(
                    dict(
                        filename=jf.name,
                        filepath=str(jf),
                        total=len(comics),
                        links=sum(1 for c in comics if c.get("download_links")),
                        mtime=jf.stat().st_mtime,
                    )
                )
        except json.JSONDecodeError:
            continue

    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results


def select_download_file() -> Optional[str]:
    files = scan_json_files_with_downloads()
    if not files:
        tqdm.write("url/ 目录下没有可用 JSON，先运行 get_url.py 生成吧")
        return None

    tqdm.write("\n=== 可下载 JSON 列表 ===")
    for i, info in enumerate(files, 1):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["mtime"]))
        tqdm.write(
            f"{i}. {info['filename']}\n"
            f"   漫画总数: {info['total']} | 含下载链接: {info['links']} | 修改: {ts}"
        )

    while True:
        try:
            sel = input(f"\n请选择 (1-{len(files)})，或 q 退出: ").strip()
            if sel.lower() == "q":
                return None
            idx = int(sel) - 1
            if 0 <= idx < len(files):
                tqdm.write(f"已选择: {files[idx]['filename']}\n")
                return files[idx]["filepath"]
        except (ValueError, KeyboardInterrupt):
            tqdm.write("取消/无效输入")
            return None
        tqdm.write("输入无效，请重试")

# --------------------------------------------------------------------------- #
#                                  入口                                       #
# --------------------------------------------------------------------------- #
async def main() -> None:
    tqdm.write("=== WNACG 漫画下载工具 ===\n")
    json_file = select_download_file()
    if not json_file:
        return

    downloader = ComicDownloader()
    await downloader.download_from_json(json_file)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        tqdm.write("\n用户取消")
