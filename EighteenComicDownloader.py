import concurrent.futures
import hashlib
import logging
import math
import os
import re
import time

import requests
from PIL import Image

import ImageReviser

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL

# 18comic CDN 圖片下載用 headers（CDN 不需要 Cloudflare cookies）
_CDN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://18comic.vip/',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}


class EighteenComicParser(Parser):

    def __init__(self, url, path, pool):
        super(EighteenComicParser, self).__init__(url, path, pool)
        self.id = 0

    def check(self):
        match = re.match(r'^https?://18comic\.(org|vip)/(photo|album)/(\d+)', self.url)
        if match is not None:
            logging.info(f'parse EighteenComic')
            logging.info(f'{match.group(1)} {match.group(2)} {match.group(3)}')
            if match.group(2) == "album":
                # album URL 轉換為 photo URL
                self.url = f'https://18comic.vip/photo/{match.group(3)}/'
            self.id = match.group(3)
            return True
        return False

    def run(self):
        """
        使用 undetected-chromedriver 繞過 Cloudflare Managed Challenge 取得頁面資訊。
        由於 18comic 已啟用 Cloudflare Bot Protection，普通 HTTP 請求會被 403 封鎖，
        必須使用真實 Chrome 瀏覽器實例通過 JS 挑戰。
        注意：Chrome 視窗會短暫出現，這是繞過 Cloudflare headless 偵測所必需的。
        """
        driver = None
        try:
            try:
                import undetected_chromedriver as uc
            except ImportError:
                logging.error("undetected-chromedriver not installed. "
                              "Please run: pip install undetected-chromedriver")
                return

            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--lang=zh-TW")
            options.add_argument("--window-size=1280,800")
            # 不使用 headless 模式：Cloudflare 會偵測並封鎖 headless Chrome

            logging.info(f'Starting Chrome to bypass Cloudflare for: {self.url}')
            driver = uc.Chrome(options=options, version_main=None)
            driver.get(self.url)

            # 等待 Cloudflare 挑戰通過（最多 30 秒）
            passed = False
            for i in range(30):
                title = driver.title
                if title and "Just a moment" not in title and "請稍候" not in title:
                    logging.info(f'Cloudflare challenge passed at {i}s')
                    passed = True
                    break
                time.sleep(1)

            if not passed:
                raise Exception("Cloudflare challenge timeout after 30s")

            page_source = driver.page_source
            logging.debug(f'Page source length: {len(page_source)}')

            driver.quit()
            driver = None

            # 以 UTF-8 解析頁面（避免終端編碼問題）
            soup = BeautifulSoup(page_source.encode('utf-8'), 'html.parser',
                                 from_encoding='utf-8')

            title_tag = soup.find('title')
            if title_tag is None:
                raise Exception("Can't find <title> tag")
            comic_name = title_tag.text
            logging.debug(f'raw title = {repr(comic_name)}')

            title_match = re.match(r'^([^|]+)([|].+)? Comics', comic_name)
            if title_match is None or title_match.group(1) is None:
                raise Exception(f"Can't parse comic_name from title: \"{comic_name}\"")
            comic_name = title_match.group(1)

            # 剔除 Windows 不合法路徑字元
            comic_name = re.sub(r'[\\<>:"?*/\t|]', '', comic_name)
            comic_name = comic_name.strip()
            logging.debug(f'comic name = "{comic_name}"')

            # 取最大頁碼
            pages = 0
            for page_span in soup.find_all('span', id='nowpage'):
                try:
                    p = int(page_span.text)
                    if p > pages:
                        pages = p
                except ValueError:
                    pass
            logging.debug(f'pages = {pages}')

            # 解析 scramble_id（決定圖片是否需要還原）
            m_scramble = re.search(r'scramble_id\s*=\s*(\d+)', page_source)
            if m_scramble is None:
                raise Exception("Can't parse scramble_id")
            scramble_id = m_scramble.group(1)
            logging.debug(f'scramble_id = {scramble_id}')

            # 解析 aid（漫畫 ID）
            m_aid = re.search(r'\baid\s*=\s*(\d+)', page_source)
            if m_aid is None:
                raise Exception("Can't parse aid")
            aid = m_aid.group(1)
            logging.debug(f'aid = {aid}')

            # aid > scramble_id 時圖片為亂序，需要還原
            is_scramble = int(aid) > int(scramble_id)
            logging.debug(f'is_scramble = {is_scramble} (aid={aid} > scramble_id={scramble_id})')

            self.signal.parsed.emit(EighteenComicDownloader(
                self.path,
                comic_name,
                self.pool,
                self.id,
                pages,
                is_scramble
            ))
            self.path = f'{self.path}{comic_name}'

        except Exception as e:
            logging.error(f'EighteenComicParser error: {e}')
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass


class EighteenComicDownloader(Downloader):

    def __init__(self, path, name, pool, id, pages, is_scramble):
        super(EighteenComicDownloader, self).__init__(f'{path}{name}', name, pool)
        self.id = id
        self.pages = pages
        self.downloaded = 0
        self.is_scramble = is_scramble
        self.file_ext = 'webp'

    def download_url(self, url, path, page):
        """下載單張圖片。CDN 不受 Cloudflare 保護，可直接用 requests 下載。"""
        resp = requests.get(url, headers=_CDN_HEADERS, timeout=30)
        resp.raise_for_status()

        with open(path, 'wb') as f:
            f.write(resp.content)

        if os.path.getsize(path) < 1:
            # 檔案為空時重試（修正原本少傳 page 參數的 bug）
            return self.download_url(url, path, page)

        if self.is_scramble:
            self.image_post_process(page)

        return True

    @staticmethod
    def revise_image(image_path, split_num):
        image = Image.open(image_path)
        width, height = image.size

        # 使用原始 mode 避免 RGB/RGBA 轉換問題
        revised_img = Image.new(image.mode, image.size)
        remainder = int(height % split_num)
        copy_width = width
        for i in range(split_num):
            copy_height = math.floor(height / split_num)
            py = copy_height * i
            y = height - (copy_height * (i + 1)) - remainder
            if i == 0:
                copy_height = copy_height + remainder
            else:
                py = py + remainder

            cropped_img = image.crop((0, y, copy_width, y + copy_height))
            revised_area = (0, py, copy_width, py + copy_height)
            revised_img.paste(cropped_img, revised_area)
        revised_img.save(image_path)

    def image_post_process(self, page):
        combine = f'{self.id}{str(page).zfill(5)}'
        md5_hash = hashlib.md5(combine.encode()).hexdigest()
        last_char = md5_hash[-1]
        ascii_value = ord(last_char)
        split_num = 2 + (ascii_value % 8) * 2
        logging.debug(f'image_post_process page={page} split_num={split_num}')

        self.revise_image(f'{self.path}\\{page}.{self.file_ext}', split_num)

    def run(self):
        logging.info(f'Downloading : "{self.path}"')

        # 檢查目錄是否已存在且非空
        if self.check_directory_exists(self.path):
            logging.info(f'Directory already exists and not empty, skipping: "{self.path}"')
            self.signal.status.emit(STATUS_DOWNLOADED)
            self.signal.progress.emit(100)
            self.signal.finished.emit()
            return

        try:
            if not os.path.exists(self.path):
                os.makedirs(self.path)

            self.signal.status.emit(STATUS_DOWNLOADING)

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_page = {
                    executor.submit(
                        self.download_url,
                        f'https://cdn-msp.18comic.org/media/photos/{self.id}/{str(page).zfill(5)}.{self.file_ext}',
                        f'{self.path}\\{page}.{self.file_ext}',
                        page
                    ): page for page in range(1, self.pages + 1)
                }

                for future in concurrent.futures.as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        if future.result():
                            self.downloaded += 1
                            self.signal.progress.emit(
                                int(self.downloaded / self.pages * 100)
                            )
                    except Exception as e:
                        logging.error(e)
                        logging.error(
                            f"Failed to download: "
                            f"https://cdn-msp.18comic.org/media/photos/"
                            f"{self.id}/{str(page).zfill(5)}.{self.file_ext}"
                        )

        except Exception as e:
            raise e
        finally:
            self.signal.status.emit(
                STATUS_DOWNLOADED if self.downloaded == self.pages else STATUS_FAIL
            )
            self.signal.finished.emit()
