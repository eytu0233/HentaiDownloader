import logging
import os
import re
import ssl
import urllib.request
import winreg

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
        self.chrome_ver = 0

    @staticmethod
    def extract_number_before_dot(string):
        # 找到第一个点号的位置
        dot_index = string.find('.')

        # 如果找到了点号
        if dot_index != -1:
            # 从字符串中提取点号前面的部分
            number_string = string[:dot_index]
            # 使用isdigit()方法检查该部分是否全部由数字组成
            if number_string.isdigit():
                return int(number_string)

        # 如果找不到点号或者点号前面不是数字，则返回 None
        return None

    def get_chrome_version(self):
        # Chrome 在注册表中的路径
        reg_path = r"SOFTWARE\Google\Chrome\BLBeacon"

        if self.chrome_ver != 0:
            return None

        try:
            # 打开注册表
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            # 读取 Chrome 的版本信息
            version, _ = winreg.QueryValueEx(reg_key, "version")
            # 关闭注册表
            winreg.CloseKey(reg_key)
            self.chrome_ver = self.extract_number_before_dot(version)
            return version
        except Exception as e:
            logging.error(f'get_chrome_version {e}')
            return None

    def get_cookies_as_dict(self, domain):
        # Get cookies for the specified domain from all available browsers
        cj = browser_cookie3.chrome(domain_name=domain)

        # Convert cookies to dictionary
        cookies_dict = {}
        for cookie in cj:
            cookies_dict[cookie.name] = cookie.value

        return cookies_dict

    def run(self):
        self.get_chrome_version()
        self.signal.status.emit(STATUS_DOWNLOADING)
        headers = {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.chrome_ver}.0.0.0 Safari/537.36'
        }
        #cookies = self.get_cookies_as_dict('.wzip.download')
        #logging.info(cookies)

        # Download the resource
        #ssl._create_default_https_context = ssl._create_unverified_context
        #response = requests.get(self.url, headers=headers, cookies=cookies, stream=True, verify=False)
        response = requests.get(self.url, headers=headers , stream=True, verify=False)
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
        try:
            self.extract_deflate64_zip(self.path, self.dir_path, target_dir)
        except Exception as e:
            logging.error(e)
            self.signal.status.emit(STATUS_UNZIP_FAIL)
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
            try:
                with zipfile2.ZipFile(tempfile_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_dir)
            except Exception as e:
                raise e
            finally:
                if os.path.exists(tempfile_path):
                    os.remove(tempfile_path)

