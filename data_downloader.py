# -*- coding: utf-8 -*-
"""
JMA Weather Desktop GUI System - Data Downloader
農業部水產試驗所 漁海況研究小組

Module for downloading HIMSST, NPRSUBT, and NPRSUBC data from JMA servers.
"""

import re
import time
import gzip
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Callable

import config


class JMADataDownloader:
    """
    Downloads and manages JMA oceanographic data files.
    Supports HIMSST, NPRSUBT, and NPRSUBC data products.
    """
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _report_progress(self, message: str, progress: float = 0):
        if self.progress_callback:
            self.progress_callback(message, progress)
        print(f"[{progress:.0%}] {message}")
    
    def _get_directories(self, base_url: str, pattern: str) -> List[str]:
        """Get list of directories matching pattern."""
        try:
            response = self.session.get(base_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            dirs = re.findall(pattern, response.text)
            return sorted(set(dirs), reverse=True)
        except Exception as e:
            self._report_progress(f"Error fetching directories: {e}")
            return []
    
    def _get_files_from_url(self, url: str, file_pattern: str) -> List[Tuple[str, str]]:
        """Get files matching pattern from URL."""
        try:
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            matches = re.findall(file_pattern, response.text)
            return [(f, f"{url}{f}") for f in set(matches)]
        except Exception as e:
            return []
    
    def _download_file(self, url: str, save_path: Path, decompress: bool = False) -> bool:
        """Download a single file with retry logic."""
        for attempt in range(config.RETRY_COUNT):
            try:
                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()
                
                if decompress and url.endswith('.gz'):
                    content = gzip.decompress(response.content)
                    save_path = save_path.with_suffix('').with_suffix('.txt')
                else:
                    content = response.content
                
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(content)
                return True
                
            except Exception as e:
                if attempt < config.RETRY_COUNT - 1:
                    time.sleep(config.RETRY_DELAY)
                else:
                    self._report_progress(f"Failed to download {url}: {e}")
                    return False
        return False
    
    def download_himsst(self, max_files: int = 10) -> List[Path]:
        """
        Download latest HIMSST data files.
        Directory structure: base_url/YYYY/him_sst_pac_DYYYYMMDD.txt
        """
        self._report_progress("正在取得 HIMSST 資料檔案列表...", 0.0)
        
        # Get year directories
        years = self._get_directories(config.HIMSST_BASE_URL, r'href="(\d{4})/"')
        if not years:
            self._report_progress("未找到 HIMSST 年份目錄", 0.0)
            return []
        
        # Collect files from recent years
        all_files = []
        file_pattern = r'href="(him_sst_pac_D\d{8}\.txt)"'
        
        for year in years:
            year_url = f"{config.HIMSST_BASE_URL}{year}/"
            files = self._get_files_from_url(year_url, file_pattern)
            all_files.extend(files)
            if len(all_files) >= max_files * 2:
                break
        
        if not all_files:
            self._report_progress("未找到 HIMSST 資料檔案", 0.0)
            return []
        
        # Sort by date descending
        def get_date(item):
            match = re.search(r'D(\d{8})', item[0])
            return match.group(1) if match else '00000000'
        
        all_files = sorted(all_files, key=get_date, reverse=True)[:max_files]
        self._report_progress(f"找到 {len(all_files)} 個 HIMSST 檔案", 0.1)
        
        downloaded = []
        for i, (filename, url) in enumerate(all_files):
            progress = 0.1 + (i + 1) / len(all_files) * 0.8
            self._report_progress(f"正在下載 HIMSST: {filename}", progress)
            
            save_path = config.HIMSST_DATA_DIR / filename
            if self._download_file(url, save_path, decompress=False):
                if save_path.exists():
                    downloaded.append(save_path)
        
        self._report_progress(f"HIMSST 下載完成: {len(downloaded)} 個檔案", 1.0)
        return downloaded
    
    def download_nprsubt(self, max_files: int = 10) -> List[Path]:
        """
        Download latest NPRSUBT data files.
        Directory structure: base_url/YYYY/MM/npr_subt_jpn_DYYYYMMDD.txt.gz
        """
        self._report_progress("正在取得 NPRSUBT 資料檔案列表...", 0.0)
        
        # Get year directories
        years = self._get_directories(config.NPRSUBT_BASE_URL, r'href="(\d{4})/"')
        if not years:
            self._report_progress("未找到 NPRSUBT 年份目錄", 0.0)
            return []
        
        all_files = []
        file_pattern = r'href="((?:re_)?npr_subt_jpn_D\d{8}\.txt\.gz)"'
        
        for year in years:
            year_url = f"{config.NPRSUBT_BASE_URL}{year}/"
            months = self._get_directories(year_url, r'href="(\d{2})/"')
            
            for month in months:
                month_url = f"{year_url}{month}/"
                files = self._get_files_from_url(month_url, file_pattern)
                all_files.extend(files)
                if len(all_files) >= max_files * 2:
                    break
            
            if len(all_files) >= max_files * 2:
                break
        
        if not all_files:
            self._report_progress("未找到 NPRSUBT 資料檔案", 0.0)
            return []
        
        def get_date(item):
            match = re.search(r'D(\d{8})', item[0])
            return match.group(1) if match else '00000000'
        
        all_files = sorted(all_files, key=get_date, reverse=True)[:max_files]
        self._report_progress(f"找到 {len(all_files)} 個 NPRSUBT 檔案", 0.1)
        
        downloaded = []
        for i, (filename, url) in enumerate(all_files):
            progress = 0.1 + (i + 1) / len(all_files) * 0.8
            self._report_progress(f"正在下載 NPRSUBT: {filename}", progress)
            
            save_path = config.NPRSUBT_DATA_DIR / filename
            if self._download_file(url, save_path, decompress=True):
                # Get the decompressed filename
                txt_path = save_path.with_suffix('').with_suffix('.txt')
                if txt_path.exists():
                    downloaded.append(txt_path)
        
        self._report_progress(f"NPRSUBT 下載完成: {len(downloaded)} 個檔案", 1.0)
        return downloaded
    
    def download_nprsubc(self, max_files: int = 10) -> List[Path]:
        """
        Download latest NPRSUBC data files.
        Directory structure: base_url/YYYY/MM/npr_subc_jpn_DYYYYMMDD.txt.gz
        """
        self._report_progress("正在取得 NPRSUBC 資料檔案列表...", 0.0)
        
        years = self._get_directories(config.NPRSUBC_BASE_URL, r'href="(\d{4})/"')
        if not years:
            self._report_progress("未找到 NPRSUBC 年份目錄", 0.0)
            return []
        
        all_files = []
        file_pattern = r'href="((?:re_)?npr_subc_jpn_D\d{8}\.txt\.gz)"'
        
        for year in years:
            year_url = f"{config.NPRSUBC_BASE_URL}{year}/"
            months = self._get_directories(year_url, r'href="(\d{2})/"')
            
            for month in months:
                month_url = f"{year_url}{month}/"
                files = self._get_files_from_url(month_url, file_pattern)
                all_files.extend(files)
                if len(all_files) >= max_files * 2:
                    break
            
            if len(all_files) >= max_files * 2:
                break
        
        if not all_files:
            self._report_progress("未找到 NPRSUBC 資料檔案", 0.0)
            return []
        
        def get_date(item):
            match = re.search(r'D(\d{8})', item[0])
            return match.group(1) if match else '00000000'
        
        all_files = sorted(all_files, key=get_date, reverse=True)[:max_files]
        self._report_progress(f"找到 {len(all_files)} 個 NPRSUBC 檔案", 0.1)
        
        downloaded = []
        for i, (filename, url) in enumerate(all_files):
            progress = 0.1 + (i + 1) / len(all_files) * 0.8
            self._report_progress(f"正在下載 NPRSUBC: {filename}", progress)
            
            save_path = config.NPRSUBC_DATA_DIR / filename
            if self._download_file(url, save_path, decompress=True):
                txt_path = save_path.with_suffix('').with_suffix('.txt')
                if txt_path.exists():
                    downloaded.append(txt_path)
        
        self._report_progress(f"NPRSUBC 下載完成: {len(downloaded)} 個檔案", 1.0)
        return downloaded
    
    def download_all(self, max_files: int = 10) -> dict:
        """Download all data types."""
        results = {
            'himsst': self.download_himsst(max_files),
            'nprsubt': self.download_nprsubt(max_files),
            'nprsubc': self.download_nprsubc(max_files),
        }
        total = sum(len(v) for v in results.values())
        self._report_progress(f"所有資料下載完成: 共 {total} 個檔案", 1.0)
        return results


def get_local_files(data_type: str) -> List[Path]:
    """Get list of locally available data files."""
    dir_map = {
        'himsst': config.HIMSST_DATA_DIR,
        'nprsubt': config.NPRSUBT_DATA_DIR,
        'nprsubc': config.NPRSUBC_DATA_DIR,
    }
    
    if data_type not in dir_map:
        return []
    
    data_dir = dir_map[data_type]
    files = list(data_dir.glob('*.txt'))
    
    def get_date(f):
        match = re.search(r'\d{8}', f.name)
        return match.group() if match else '00000000'
    
    return sorted(files, key=get_date, reverse=True)


def extract_date_from_filename(filepath: Path) -> Optional[datetime]:
    """Extract date from data filename."""
    match = re.search(r'(\d{8})', filepath.name)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y%m%d')
        except ValueError:
            return None
    return None


if __name__ == "__main__":
    downloader = JMADataDownloader()
    results = downloader.download_all(max_files=2)
    
    print("\n下載結果:")
    for data_type, files in results.items():
        print(f"\n{data_type.upper()}:")
        for f in files:
            print(f"  - {f}")
