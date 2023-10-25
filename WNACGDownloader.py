import logging
import os
import re
import urllib.request

import browser_cookie3
import requests
import zipfile2

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL, STATUS_UNZIPING, \
    STATUS_UNZIP


class WNACGParser(Parser):

    def __init__(self, url, path, pool):
        super(WNACGParser, self).__init__(url, path, pool)

    def check(self):
        match = re.match('^https?://www.wnacg.(org|com)/photos-index-(aid-\\d+)?', self.url)
        if match is not None:
            logging.info(f'parse_wnacg')
            return True
        return False

    def run(self):
        logging.info("start wnacg")
        match = re.match('https?://www.wnacg.(org|com)/photos-index(-page-\\d+)?-aid-(\\d+).html', self.url)
        if match is None:
            logging.error(f"url is not match!!")
            return None

        index = match.group(3)
        if index is None:
            logging.error(f"{index} is not match!!")
            return None
        logging.info(f"index = {index}")

        dns = match.group(1)
        if index is None:
            logging.error(f"dns is not match!!")
            return None
        logging.info(f"dns = {dns}")

        req = urllib.request.Request(f"http://www.wnacg.{dns}/download-index-aid-{index}.html", headers={'User-Agent': 'Mozilla/5.0'})
        result = urllib.request.urlopen(req, timeout=5).read()
        if result is None:
            logging.error(f"Can't get web page from \"{downloadPageUrl}\"")
            return

        soup = BeautifulSoup(result, 'html.parser')
        comic_name = soup.find('p', 'download_filename').text
        comic_name = re.sub('[\\\\<>:"?*/\t]', '', comic_name)  # 刪除非法文件名
        comic_name = comic_name.strip()
        # 將非ASCII的Unicode字元轉成ASCII
        a_tag = soup.find('a', class_="down_btn ads")
        href_str = a_tag["href"]
        logging.debug(f'href_str = {href_str}')
        download_url = urllib.parse.quote(f"https:{href_str}", safe=":/?")
        logging.debug(f"download url : {download_url}")
        self.signal.parsed.emit(WNACGDownloader(self.path, comic_name, self.pool, download_url))


class WNACGDownloader(Downloader):

    def __init__(self, path, name, pool, url):
        super(WNACGDownloader, self).__init__(f'{path}{name}', name, pool)
        self.url = url
        self.name = name
        self.dir_path = path

    def get_cookies_as_dict(self, domain):
        # Get cookies for the specified domain from all available browsers
        cj = browser_cookie3.chrome(domain_name=domain)

        # Convert cookies to dictionary
        cookies_dict = {}
        for cookie in cj:
            cookies_dict[cookie.name] = cookie.value

        return cookies_dict

    def run(self):
        self.signal.status.emit(STATUS_DOWNLOADING)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        }
        cookies = self.get_cookies_as_dict('.wzip.download')
        logging.info(cookies)

        # Download the resource
        response = requests.get(self.url, headers=headers, cookies=cookies, stream=True)
        response.raise_for_status()

        content_length = int(response.headers.get('Content-Length'))
        logging.info(f'file size = {content_length}')

        size = 0
        with open(self.path, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=8192):
                out_file.write(chunk)
                size += len(chunk)
                percent = int(size / content_length * 100)
                self.signal.progress.emit(100 if percent > 100 else percent)
        self.signal.status.emit(STATUS_DOWNLOADED)
        self.signal.finished.emit()

        target_dir = self.remove_zip_extension(self.path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        logging.info(f"path = {self.path}")
        logging.info(f"target_dir = {target_dir}")

        self.signal.status.emit(STATUS_UNZIPING)
        self.extract_deflate64_zip(self.path, self.dir_path, target_dir)
        self.signal.status.emit(STATUS_UNZIP)

    @staticmethod
    def remove_zip_extension(s):
        # 如果字符串以.zip结尾，返回去掉.zip的部分，否则返回原始字符串
        return s[:-4] if s.lower().endswith('.zip') else s

    @staticmethod
    def extract_deflate64_zip(zip_file_path, exist_dir, dest_dir):
            tempfile_path = f"{exist_dir}tmp.zip"
            os.chdir(exist_dir)
            os.rename(zip_file_path, tempfile_path)
            with zipfile2.ZipFile(tempfile_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
            if os.path.exists(tempfile_path):
                os.remove(tempfile_path)
