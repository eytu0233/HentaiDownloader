import json
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
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_UNZIP_FAIL, STATUS_UNZIPING, \
    STATUS_UNZIP


class WNACGParser(Parser):

    def __init__(self, url, path, pool):
        super(WNACGParser, self).__init__(url, path, pool)
        self.chrome_ver = 0

    def check(self):
        match = re.match('^https?://www.wnacg.(org|com)/photos-index-(aid-\\d+)?', self.url)
        if match is not None:
            logging.info(f'parse_wnacg')
            return True
        return False

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

    def run(self):
        logging.info("start wnacg")
        self.get_chrome_version()
        # logging.info(f'chrome version = {self.chrome_ver}')

        match = re.match('https?://www.wnacg.(org|com)/photos-index(-page-\\d+)?-aid-(\\d+).html', self.url)
        if match is None:
            logging.error(f"url is not match!!")
            return None

        index = match.group(3)
        if index is None:
            logging.error(f"{index} is not match!!")
            return None
        # logging.info(f"index = {index}")

        dns = match.group(1)
        if index is None:
            logging.error(f"dns is not match!!")
            return None
        # logging.info(f"dns = {dns}")

        headers = {
            "cookie" : '_ym_uid=16557420981015354696; _ga=GA1.2.197418865.1684169065; X_CACHE_KEY=f412ba8fe04a8b141f0c02ac02bb8ce0; cf_clearance=6UTY2XRMQQuSEO.BkE3QwKiIZyyZnHE4HF95zGJGR0Q-1754831627-1.2.1.1-6GtYitsR1O0ExEcHH3zb6dYivqhUgQfGFwI0lfDFvQxE1wC1g6_kagmkyyajnzUlcLKvniypTFNxrk6cGw70ELajN3jCxmqIlDUMSZ5EcnfiiTlagBcFF2nOLUc6mMGpv7PbRU_74YmReB3lOf2glaQD84XHnPaa3IROmWkGViMzZNKB4Cz8o1vBUoehjI7aVrKFAUrTJNMoeNI3IbCt52556iVkEk8GgCvQEfJ1Ens; _ym_d=1762951844; _ym_isad=2; _gid=GA1.2.109009695.1764202043',
            "User-Agent": f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.chrome_ver}.0.0.0 Safari/537.36'
        }
        # logging.info(f"headers = {headers}")
        downloadPageUrl = f"http://www.wnacg.{dns}/download-index-aid-{index}.html"
        req = urllib.request.Request(downloadPageUrl, headers=headers)
        result = urllib.request.urlopen(req, timeout=5).read()
        if result is None:
            logging.error(f"Can't get web page from \"{downloadPageUrl}\"")
            return

        soup = BeautifulSoup(result, 'html.parser')
        # title = soup.find_all('h1')
        # logging.debug(f"title = {title}")
        # comic_name = soup.find('p', 'download_filename').text
        # comic_name = re.sub('[\\\\<>:"?*/\t|]', '', comic_name)  # 刪除非法文件名
        # comic_name = comic_name.strip()
        # # 將非ASCII的Unicode字元轉成ASCII
        # a_tag = soup.find('a', class_="down_btn ads")
        # href_str = a_tag["href"]
        # logging.debug(f'href_str = {href_str}')
        # download_url = urllib.parse.quote(f"https:{href_str}", safe=":/?")
        # logging.debug(f"download url : {download_url}")

        a_tag = soup.find('a', class_="ads")
        href_str = a_tag["href"]
        # logging.debug(f'href_str = {href_str}')
        download_url = urllib.parse.quote(f"https:{href_str}", safe=":/?")
        logging.debug(f"backup download url : {download_url}")

        script_tag = soup.find('script', text=re.compile(r'CONFIG'))
        if script_tag:
            content = script_tag.string

            # 2. 使用正規表達式提取變數值
            # 這裡的規則是抓取 鍵值: "內容" 格式
            worker_api = re.search(r'WORKER_API:\s*"(.*?)"', content).group(1)
            file_key = re.search(r'FILE_KEY:\s*"(.*?)"', content).group(1)
            file_name = re.search(r'FILE_NAME:\s*"(.*?)"', content).group(1)

            # logging.debug(f"提取成功：")
            # logging.debug(f"API 網址: {worker_api}")
            # logging.debug(f"檔案金鑰: {file_key}")
            # logging.debug(f"檔案名稱: {file_name}")

            # 3. 整合為下一步要發送的資料
            download_url = {
                "api": worker_api,
                "file_key": file_key,
                "file_name": file_name,
                "backup": download_url
            }
        else:
            logging.error("未找到包含 CONFIG 的腳本標籤")

        self.signal.parsed.emit(WNACGDownloader(self.path, file_name, self.pool, download_url))


class WNACGDownloader(Downloader):

    def __init__(self, path, name, pool, url):
        super(WNACGDownloader, self).__init__(f'{path}{self.format_name(name)}', name, pool)
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

    def get_download_link(self):
        self.get_chrome_version()

        headers = {
            "Content-Type": "application/json",
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.chrome_ver}.0.0.0 Safari/537.36'
        }

        api_url = self.url['api']
        # logging.info(f"api_url = {api_url}")

        payload = {
            "file_key": self.url['file_key'],
            "file_name": self.url['file_name']
        }

        # logging.info(f"payload = {payload}")

        try:
            # 2. 發送 POST 請求
            # logging.info("正在獲取下載鏈接...")
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))

            # 3. 解析結果
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    download_url = data.get("url")
                    # logging.info(f"獲取成功！下載連結為：\n{download_url}")
                    return download_url
                else:
                    logging.error(f"失敗：{data.get('msg', '未知錯誤')}")
                    return None
            else:
                logging.error(f"伺服器錯誤，狀態碼：{response.status_code}")
                return None

        except Exception as e:
            logging.error(f"發生錯誤：{e}")

    def run(self):
        self.get_chrome_version()

        # 檢查解壓後的目錄是否已存在且非空
        target_dir = self.remove_zip_extension(self.path)
        if self.check_directory_exists(target_dir):
            logging.info(f'Directory already exists and not empty, skipping download: \"{target_dir}\"')
            self.signal.status.emit(STATUS_UNZIP)
            self.signal.progress.emit(100)
            self.signal.finished.emit()
            return

        self.signal.status.emit(STATUS_DOWNLOADING)
        headers = {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.chrome_ver}.0.0.0 Safari/537.36'
        }
        url = self.get_download_link()
        if url is None:
            url = self.url['backup']
            # logging.info(f'Use backup url : {url}')
        response = requests.get(url, headers=headers , stream=True, verify=False)
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

